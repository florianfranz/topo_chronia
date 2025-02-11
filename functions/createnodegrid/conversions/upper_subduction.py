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

class UPSConversion:
    INPUT_FILE_PATH = "input_files.txt"
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    geodesic_grid_path = base_tools.get_layer_path("Geodesic Grid")
    geodesic_grid_layer = QgsVectorLayer(geodesic_grid_path, "Geodesic Grid", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    POSITION = "POSITION"
    def __init__(self):
        pass
    def upper_subduction_to_nodes(self,age):
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        PARAM_AM_STEP = 50
        PARAM_AM_LENGTH = 550
        x_min = 0
        step_length = PARAM_AM_STEP
        PARAM_IOS_LENGTH = 350
        raster_prelim_path = os.path.join(self.output_folder_path,f"qgis_tin_raster_prelim_{int(age)}.tif")
        raster_prelim = QgsRasterLayer(raster_prelim_path,"Preliminary Raster")
        ups_multipoint_path = os.path.join(self.output_folder_path, f"ups_multipoint_{int(age)}.geojson")
        ups_multipoint = QgsVectorLayer(ups_multipoint_path, "UPS MultiPoint", "ogr")
        attributes = ups_multipoint.fields().toList()
        UPS_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","UPS Profiles","memory")
        profiles_provider = UPS_profiles.dataProvider()
        profiles_provider.addAttributes(attributes)
        UPS_profiles.updateFields()
        field_idx_oid = ups_multipoint.fields().indexOf('ORIG_ID')
        spatial_index_profiles = QgsSpatialIndex()
        geometry_dict_profiles = {}
        with edit(ups_multipoint):
            for upper_subduction_feature in ups_multipoint.getFeatures():
                orig_id = upper_subduction_feature.id()
                ups_multipoint.changeAttributeValue(upper_subduction_feature.id(),field_idx_oid,orig_id)
        ups_multipoint.commitChanges()
        for upper_subduction_feature in ups_multipoint.getFeatures():
            geom = upper_subduction_feature.geometry()
            multi_point = geom.asMultiPoint()
            if upper_subduction_feature.attribute('POSITION') == "Lower":
                pass
            elif upper_subduction_feature.attribute('POSITION') == "No Position":
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
                    if upper_subduction_feature.attribute("TYPE") == 'Z_Subduction':
                        x_max = PARAM_IOS_LENGTH
                        profile_geometry = feature_conversion_tools.create_profile(point1,point2,x_min,x_max,step_length,flag, "normal")
                        if profile_geometry:
                            cont_excluded_profile_geometry = feature_conversion_tools.cut_profile_spi(profile_geometry, self.continent_polygons_layer, "keep outside", "positive", age, False)
                            if cont_excluded_profile_geometry:
                                final_profile_geometry = feature_conversion_tools.check_profile_intersection(cont_excluded_profile_geometry, spatial_index_profiles, geometry_dict_profiles)
                                if final_profile_geometry:
                                    feature.setGeometry(final_profile_geometry)
                                    feature.setAttributes(upper_subduction_feature.attributes())
                                    profile_points = final_profile_geometry.asMultiPoint()
                                    for point in profile_points:
                                        point_id = len(geometry_dict_profiles)
                                        point_geom = QgsGeometry.fromPointXY(point)
                                        geometry_dict_profiles[point_id] = point_geom
                                        p_feature = QgsFeature(point_id)
                                        p_feature.setGeometry(point_geom)
                                        spatial_index_profiles.insertFeature(p_feature)
                                    profiles_provider.addFeature(feature)
                    elif upper_subduction_feature.attribute("TYPE") == 'Active_Margin':
                        x_max = PARAM_AM_LENGTH
                        profile_geometry = feature_conversion_tools.create_profile(point1,point2,x_min,x_max,step_length, flag, "normal")
                        if profile_geometry:
                            cont_excluded_profile_geometry = feature_conversion_tools.cut_profile_spi(
                                profile_geometry, self.continent_polygons_layer, "keep inside", "positive", age,
                                False)
                            if cont_excluded_profile_geometry:
                                final_profile_geometry = feature_conversion_tools.check_profile_intersection(cont_excluded_profile_geometry, spatial_index_profiles, geometry_dict_profiles)
                                if final_profile_geometry:
                                    feature.setGeometry(final_profile_geometry)
                                    feature.setAttributes(upper_subduction_feature.attributes())
                                    profile_points = final_profile_geometry.asMultiPoint()
                                    for point in profile_points:
                                        point_id = len(geometry_dict_profiles)
                                        point_geom = QgsGeometry.fromPointXY(point)
                                        geometry_dict_profiles[point_id] = point_geom
                                        p_feature = QgsFeature(point_id)
                                        p_feature.setGeometry(point_geom)
                                        spatial_index_profiles.insertFeature(p_feature)
                                    profiles_provider.addFeature(feature)
        UPS_profiles.commitChanges()
        output_profiles_layer_path = os.path.join(self.output_folder_path,f"UPS_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(UPS_profiles,output_profiles_layer_path,'utf-8',UPS_profiles.crs(),"GeoJSON")
        all_points_features = []
        for profile_feature in UPS_profiles.getFeatures():
            feature_abs_age = profile_feature.attribute('AGE')
            feature_age = feature_abs_age - age
            setting = profile_feature.attribute('TYPE')
            orig_id_profile = profile_feature.attribute('ORIG_ID')
            geom = profile_feature.geometry()
            multi_point = geom.asMultiPoint()
            if len(multi_point) == 0:
                pass
            else:
                for sub_multipoint_feature in ups_multipoint.getFeatures():
                    if sub_multipoint_feature.attribute('ORIG_ID') == orig_id_profile:
                        sub_multipoint_base_geom = sub_multipoint_feature.geometry()
                        sub_multipoint_geom = sub_multipoint_base_geom.asMultiPoint()
                        initial_sub_multipoint_vertex = sub_multipoint_geom[0]
                        feat_start_point = multi_point[0]
                        feat_end_point = multi_point[-1]
                        lat_distance = feature_conversion_tools.prod_scal(initial_sub_multipoint_vertex,1,feat_start_point,1)
                        coords = QgsPointXY(feat_end_point)
                        val, res = raster_prelim.dataProvider().sample(coords, 1)
                        if math.isnan(val):
                            raster_depth = -4000
                        else:
                            raster_depth = float(val)
                        for point in multi_point:
                            distance = feature_conversion_tools.prod_scal(feat_start_point,1,point,1)
                            if distance == 0:
                                pass  # As we already have nodes at feature line position from the LWS, we skip it here.
                            else:
                                if setting == "Active_Margin":
                                    z_up_plate = 240.38
                                else:
                                    z_up_plate = raster_depth
                                coords = [point[0], point[1]]

                                z = sub_tools.subduction_profile(setting,distance,ridge_depth,raster_depth,z_up_plate,lat_distance)
                                PCM_age = feature_conversion_tools.inversePCM(raster_depth,ridge_depth)
                                abys_sed = sed_tools.abyssal_sediments(age,age + PCM_age)
                                if distance >= 2.5:
                                    if raster_depth + abys_sed < z:
                                        geojson_point_feature = {
                                            "type": "Feature",
                                            "properties": {
                                                "TYPE": "UPS",
                                                "FEAT_AGE": feature_age,
                                                "DIST": distance,
                                                "Z": z,
                                                "Z_WITH_SED": z,
                                                "Z_UP": z_up_plate,
                                                "LAT_DIST": lat_distance,
                                                "SETTING": setting,
                                                "SED_HEIGHT": 0,
                                                "ABYS_SED": 0,
                                                "RHO_S": 0,
                                                "RAST_DEPTH": raster_depth
                                            },
                                            "geometry": {
                                                "type": "Point",
                                                "coordinates": coords
                                            }
                                        }
                                        all_points_features.append(geojson_point_feature)
                                    else:
                                        h_s = sed_tools.full_sediment_thickness(abys_sed + raster_depth - z)
                                        rho_sed = sed_tools.rho_sed(h_s)
                                        geojson_point_feature = {
                                            "type": "Feature",
                                            "properties": {
                                                "TYPE": "UPS",
                                                "FEAT_AGE": feature_age,
                                                "DIST": distance,
                                                "Z": z,
                                                "Z_WITH_SED": raster_depth,
                                                "Z_UP": z_up_plate,
                                                "LAT_DIST": lat_distance,
                                                "SETTING": setting,
                                                "SED_HEIGHT": h_s,
                                                "ABYS_SED": abys_sed,
                                                "RHO_S": rho_sed,
                                                "RAST_DEPTH": raster_depth
                                            },
                                            "geometry": {
                                                "type": "Point",
                                                "coordinates": coords
                                            }
                                        }
                                        all_points_features.append(geojson_point_feature)
                                else:
                                    geojson_point_feature = {
                                        "type": "Feature",
                                        "properties": {
                                            "TYPE": "UPS",
                                            "FEAT_AGE": feature_age,
                                            "DIST": distance,
                                            "Z": z,
                                            "Z_WITH_SED": z,
                                            "Z_UP": z_up_plate,
                                            "LAT_DIST": lat_distance,
                                            "SETTING": setting,
                                            "SED_HEIGHT": 0,
                                            "ABYS_SED": 0,
                                            "RHO_S": 0,
                                            "RAST_DEPTH": raster_depth
                                        },
                                        "geometry": {
                                            "type": "Point",
                                            "coordinates": coords
                                        }
                                    }
                                    all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,f"UPS_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        continent_filter = f"{self.APPEARANCE} = {age}"
        continent_spatial_index = QgsSpatialIndex(
            self.continent_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(continent_filter)))
        UPS_nodes_layer_path = os.path.join(self.output_folder_path,f"UPS_nodes_{int(age)}.geojson")
        UPS_nodes_layer = QgsVectorLayer(UPS_nodes_layer_path, "UPS Nodes", "ogr")
        field_idx_zws = UPS_nodes_layer.fields().indexOf('Z_WITH_SED')
        field_idx_z = UPS_nodes_layer.fields().indexOf('Z')
        with edit(UPS_nodes_layer):
            for feature in UPS_nodes_layer.getFeatures():
                if feature.attribute("SETTING") == "Active_Margin":
                    geom = feature.geometry().asPoint()
                    vertex_xy = QgsGeometry.fromPointXY(geom)
                    candidate_ids = continent_spatial_index.intersects(vertex_xy.boundingBox())
                    if candidate_ids:
                        for candidate_id in candidate_ids:
                            continent_feature = next(
                                self.continent_polygons_layer.getFeatures(QgsFeatureRequest(candidate_id)))
                            continent_geom = continent_feature.geometry()
                            if not continent_geom.contains(vertex_xy):
                                UPS_nodes_layer.changeAttributeValue(feature.id(), field_idx_zws,
                                                                     feature.attribute('RAST_DEPTH'))
                                UPS_nodes_layer.changeAttributeValue(feature.id(), field_idx_z,
                                                                    feature.attribute('RAST_DEPTH'))
        UPS_nodes_layer.commitChanges()
        feature_conversion_tools.add_id_nodes_setting(age, "UPS")
        feature_conversion_tools.add_layer_to_group(output_points_layer_path, f"{int(age)} Ma", "UPS")


