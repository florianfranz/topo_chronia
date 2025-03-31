import os
import json
import math
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsMessageLog, QgsRasterLayer,
                       QgsVectorFileWriter, QgsField, QgsGeometry, QgsPointXY, QgsFeature, QgsProject,
                       QgsSpatialIndex)

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.subduction_tools import SUBConversionTools
sub_tools = SUBConversionTools()

from ..tools.sediments_tools import SEDConversionTools
sed_tools = SEDConversionTools()


from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class LWSConversion:
    INPUT_FILE_PATH = "input_files.txt"
    plate_polygons_path = base_tools.get_layer_path("Plate Polygons")
    plate_polygons_layer = QgsVectorLayer(plate_polygons_path, "Plate Polygons", 'ogr')
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    geodesic_grid_path = base_tools.get_layer_path("Geodesic Grid")
    geodesic_grid_layer = QgsVectorLayer(geodesic_grid_path, "Geodesic Grid", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    POSITION = "POSITION"
    def __init__(self):
        pass
    def lower_subduction_to_nodes(self,age):
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        x_min = 0
        step_length = 100
        x_max = 201
        raster_prelim_path = os.path.join(self.output_folder_path,f"qgis_tin_raster_prelim_{int(age)}.tif")
        raster_prelim = QgsRasterLayer(raster_prelim_path,"Preliminary Raster")
        lws_multipoint_path = os.path.join(self.output_folder_path, f"lws_multipoint_{int(age)}.geojson")
        lws_multipoint = QgsVectorLayer(lws_multipoint_path, "LWS MultiPoint", "ogr")
        attributes = lws_multipoint.fields().toList()
        LWS_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","LWS Profiles","memory")
        profiles_provider = LWS_profiles.dataProvider()
        profiles_provider.addAttributes(attributes)
        LWS_profiles.updateFields()
        field_idx_oid = lws_multipoint.fields().indexOf('ORIG_ID')
        field_idx_rd = lws_multipoint.fields().indexOf('Z_RASTER')
        spatial_index_profiles = QgsSpatialIndex()
        geometry_dict_profiles = {}
        with edit(lws_multipoint):
            for lower_subduction_feature in lws_multipoint.getFeatures():
                geom = lower_subduction_feature.geometry()
                multi_point = geom.asMultiPoint()
                if len(multi_point) < 3:
                    pass
                else:
                    middle_index = len(multi_point) // 2
                    middle_point = multi_point[middle_index]
                    coords = QgsPointXY(middle_point)
                    val, res = raster_prelim.dataProvider().sample(coords, 1)

                    if not isinstance(val, (int, float)) or math.isnan(val):
                        raster_depth = 1.4109347442680775*ridge_depth
                    elif val is None:
                        raster_depth = 1.4109347442680775*ridge_depth
                    else:
                        raster_depth = float(val)
                        if raster_depth < -5500:
                            raster_depth = -5500
                    orig_id = lower_subduction_feature.id()
                    lws_multipoint.changeAttributeValue(lower_subduction_feature.id(),field_idx_oid,orig_id)
                    lws_multipoint.changeAttributeValue(lower_subduction_feature.id(), field_idx_rd, raster_depth)
        lws_multipoint.commitChanges()
        for lower_subduction_feature in lws_multipoint.getFeatures():
            geom = lower_subduction_feature.geometry()
            multi_point = geom.asMultiPoint()
            if lower_subduction_feature.attribute('POSITION') == "Upper":
                pass
            elif lower_subduction_feature.attribute('POSITION') == "No Position":
                pass
            else:
                for i in range(len(multi_point)):
                    if i < len(multi_point) - 1:
                        point1 = multi_point[i]
                        point2 = multi_point[i + 1]
                        flag = 0
                    else:
                        point1 = multi_point[i]
                        point2 = multi_point[i - 1]
                        flag = 1
                    feature = QgsFeature()
                    profile_geometry = feature_conversion_tools.create_profile(point1,point2,x_min,x_max,step_length,flag, "inverse")
                    if profile_geometry:
                        cont_excluded_profile_geometry = feature_conversion_tools.cut_profile_spi(profile_geometry, self.continent_polygons_layer, "keep outside", "positive", age, False)
                        if cont_excluded_profile_geometry:
                            final_profile_geometry = feature_conversion_tools.check_profile_intersection(cont_excluded_profile_geometry, spatial_index_profiles, geometry_dict_profiles)
                            if final_profile_geometry:
                                feature.setGeometry(final_profile_geometry)
                                feature.setAttributes(lower_subduction_feature.attributes())
                                profile_points = final_profile_geometry.asMultiPoint()
                                for point in profile_points:
                                    point_id = len(geometry_dict_profiles)
                                    point_geom = QgsGeometry.fromPointXY(point)
                                    geometry_dict_profiles[point_id] = point_geom
                                    p_feature = QgsFeature(point_id)
                                    p_feature.setGeometry(point_geom)
                                    spatial_index_profiles.insertFeature(p_feature)
                                profiles_provider.addFeature(feature)

        LWS_profiles.commitChanges()
        output_profiles_layer_path = os.path.join(self.output_folder_path,f"LWS_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(LWS_profiles,output_profiles_layer_path,'utf-8',LWS_profiles.crs(),"GeoJSON")

        all_points_features = []
        continent_filter = f"{self.APPEARANCE} = {age}"
        continent_spatial_index = QgsSpatialIndex(
            self.continent_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(continent_filter))
        )
        for profile_feature in LWS_profiles.getFeatures():
            feature_abs_age = profile_feature.attribute('AGE')
            if feature_abs_age == 999:
                feature_abs_age = age
            feature_age = feature_abs_age - age
            plate = profile_feature.attribute('PLATE')
            try:
                raster_depth = float(profile_feature.attribute('Z_RASTER'))
            except (TypeError, ValueError):
                raster_depth = 1.4109347442680775*ridge_depth
            if not profile_feature.hasGeometry():
                continue
            geom = profile_feature.geometry()
            multi_point = geom.asMultiPoint()
            feat_start_point = multi_point[0]
            for vertex in multi_point:
                vertex_xy = QgsGeometry.fromPointXY(vertex)
                candidate_ids = continent_spatial_index.intersects(vertex_xy.boundingBox())
                intersects = False
                if candidate_ids:
                    for candidate_id in candidate_ids:
                        continent_feature = next(
                            self.continent_polygons_layer.getFeatures(QgsFeatureRequest(candidate_id)))
                        continent_geom = continent_feature.geometry().buffer(-0.05, 5)
                        if continent_geom.contains(vertex_xy):
                            intersects = True
                            break
                if not intersects:
                    point = QgsPointXY(vertex[0], vertex[1])
                    distance = feature_conversion_tools.prod_scal(feat_start_point, 1, point, 1)
                    coords = [vertex[0], vertex[1]]
                    if distance == 0:
                        z = float(sub_tools.trench_depth(raster_depth, ridge_depth))
                        z_with_sed = z
                        position = "Trench"
                        abys_sed = 0
                    else:
                        abys_sed = sed_tools.abyssal_sediments(age, feature_abs_age)
                        z = raster_depth
                        z_with_sed = raster_depth + abys_sed
                        position = "Profile"
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "LWS",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": z,
                            "Z_WITH_SED": z_with_sed,
                            "POSITION": position,
                            "PLATE": plate,
                            "Z_RASTER": raster_depth,
                            "ABYS_SED": abys_sed
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": coords
                        }
                    }
                    all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,
                                                f"LWS_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        #feature_conversion_tools.check_point_plate_intersection(age, "LWS")
        feature_conversion_tools.add_id_nodes_setting(output_points_layer_path)
        #feature_conversion_tools.add_layer_to_group(output_points_layer_path, f"{int(age)} Ma", "LWS")


