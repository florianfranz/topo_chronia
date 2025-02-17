import os
import json
from qgis.PyQt.QtCore import QVariant
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsRasterLayer, QgsMessageLog, QgsField,
                       QgsVectorFileWriter, QgsGeometry, QgsPointXY, QgsFeature, QgsProject, QgsSpatialIndex)

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.collision_tools import COLConversionTools
col_tools = COLConversionTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class COLConversion:
    INPUT_FILE_PATH = "input_files.txt"
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")

    def __init__(self):
        pass
    def collision_to_nodes(self,age):
        profile_length = 3  # PARAM_CZ_LENGTH
        front_x_young = -0.5  # PARAM_CZ_FRONTX
        step_length = 50
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        z_up_plate = 240.38
        dens_COL_lines_layer_path = os.path.join(self.output_folder_path, f"dens_COL_lines_{int(age)}.geojson")
        dens_COL_lines = QgsVectorLayer(dens_COL_lines_layer_path,"Densified COL Lines",'ogr')
        COL_multipoints = QgsVectorLayer("MultiPoint?crs=EPSG:4326","COL multipoints","memory")
        points_provider = COL_multipoints.dataProvider()
        COL_multipoints.startEditing()
        attributes = dens_COL_lines.fields().toList()
        points_provider.addAttributes(attributes)
        points_provider.addAttributes([QgsField('Z', QVariant.Double), QgsField('FEAT_AGE', QVariant.Double), QgsField('SHIFT', QVariant.Double)])
        COL_multipoints.updateFields()
        COL_multipoints.commitChanges()
        spatial_index_int_profiles = QgsSpatialIndex()
        geometry_dict_int_profiles = {}
        for feature in dens_COL_lines.getFeatures():
            feature_abs_age = feature.attribute('AGE')
            if feature_abs_age != 9999:
                geom = feature.geometry()
                coords_list = [QgsPointXY(pt) for part in geom.parts() for pt in part]
                multipoint_geom = QgsGeometry.fromMultiPointXY(coords_list)
                new_feature = QgsFeature()
                new_feature.setGeometry(multipoint_geom)
                new_feature.setAttributes(feature.attributes())
                points_provider.addFeature(new_feature)
        COL_multipoints.commitChanges()
        field_idx_fa = COL_multipoints.fields().indexOf('FEAT_AGE')
        field_idx_sh = COL_multipoints.fields().indexOf('SHIFT')
        with edit(COL_multipoints):
            for feature in COL_multipoints.getFeatures():
                feature_abs_age = feature.attribute('AGE')
                feature_age = feature_abs_age - age
                COL_multipoints.changeAttributeValue(feature.id(),field_idx_fa,feature_age)
                shift = float(col_tools.collision_profile_shifting(feature_age,front_x_young,profile_length, ridge_depth))
                COL_multipoints.changeAttributeValue(feature.id(),field_idx_sh, shift)
        COL_multipoints.commitChanges()
        attributes = COL_multipoints.fields().toList()
        COL_int_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","COL Internal Profiles", "memory")
        int_profiles_provider = COL_int_profiles.dataProvider()
        int_profiles_provider.addAttributes(attributes)
        COL_int_profiles.updateFields()
        COL_ext_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","COL External Profiles","memory")
        ext_profiles_provider = COL_ext_profiles.dataProvider()
        ext_profiles_provider.addAttributes(attributes)
        COL_ext_profiles.updateFields()
        for collision_feature in COL_multipoints.getFeatures():
            geom = collision_feature.geometry()
            multi_point = geom.asMultiPoint()
            shift = collision_feature.attribute('SHIFT')
            x_max_int = -shift * 100
            x_max_ext = (shift + profile_length) * 100
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
                internal_profile_geometry = feature_conversion_tools.create_profile(point1,point2,0,x_max_int,step_length,flag, "inverse")
                if internal_profile_geometry:
                    cont_included_profile_geometry = feature_conversion_tools.cut_profile_spi(internal_profile_geometry,
                                                                                              self.continent_polygons_layer,
                                                                                              "keep inside",
                                                                                              "positive", age,
                                                                                              False)
                    if cont_included_profile_geometry:
                        final_int_profile_geometry = feature_conversion_tools.check_profile_intersection(cont_included_profile_geometry,spatial_index_int_profiles, geometry_dict_int_profiles)
                        if final_int_profile_geometry:
                            feature.setGeometry(final_int_profile_geometry)
                            feature.setAttributes(collision_feature.attributes())
                            profile_points = final_int_profile_geometry.asMultiPoint()
                            for point in profile_points:
                                point_id = len(geometry_dict_int_profiles)
                                point_geom = QgsGeometry.fromPointXY(point)
                                geometry_dict_int_profiles[point_id] = point_geom
                                p_feature = QgsFeature(point_id)
                                p_feature.setGeometry(point_geom)
                                spatial_index_int_profiles.insertFeature(p_feature)
                            int_profiles_provider.addFeature(feature)
                feature = QgsFeature()
                external_profile_geometry = feature_conversion_tools.create_profile(point1,point2,0,x_max_ext,step_length,flag, "normal")
                if external_profile_geometry:
                    cont_included_profile_geometry = feature_conversion_tools.cut_profile_spi(external_profile_geometry,
                                                                                              self.continent_polygons_layer,
                                                                                              "keep inside",
                                                                                              "positive", age,
                                                                                              False)
                    if cont_included_profile_geometry:
                        final_ext_profile_geometry = feature_conversion_tools.check_profile_intersection(cont_included_profile_geometry, spatial_index_int_profiles, geometry_dict_int_profiles)
                        if final_ext_profile_geometry:
                            feature.setGeometry(final_ext_profile_geometry)
                            feature.setAttributes(collision_feature.attributes())
                            profile_points = final_ext_profile_geometry.asMultiPoint()
                            for point in profile_points:
                                point_id = len(geometry_dict_int_profiles)
                                point_geom = QgsGeometry.fromPointXY(point)
                                geometry_dict_int_profiles[point_id] = point_geom
                                p_feature = QgsFeature(point_id)
                                p_feature.setGeometry(point_geom)
                                spatial_index_int_profiles.insertFeature(p_feature)
                            ext_profiles_provider.addFeature(feature)
        COL_int_profiles.commitChanges()
        COL_ext_profiles.commitChanges()
        output_int_profiles_layer_path = os.path.join(self.output_folder_path,f"COL_int_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(COL_int_profiles,output_int_profiles_layer_path,'utf-8',COL_int_profiles.crs(),"GeoJSON")
        output_ext_profiles_layer_path = os.path.join(self.output_folder_path, f"COL_ext_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(COL_ext_profiles,output_ext_profiles_layer_path,'utf-8',COL_ext_profiles.crs(),"GeoJSON")
        all_points_features = []
        for profile_feature in COL_int_profiles.getFeatures():
            plate = profile_feature.attribute('PLATE')
            geom = profile_feature.geometry()
            multi_point = geom.asMultiPoint()
            feat_start_point = multi_point[-1]
            feature_age = profile_feature.attribute('FEAT_AGE')
            shift = profile_feature.attribute("SHIFT")
            for point in multi_point:
                distance = - feature_conversion_tools.prod_scal(feat_start_point,1,point,1)
                z = col_tools.collision_profile(feature_age,distance,front_x_young,shift,ridge_depth, z_up_plate)
                coords = [point[0], point[1]]
                geojson_point_feature = {
                    "type": "Feature",
                    "properties": {
                        "TYPE": "COL",
                        "FEAT_AGE": feature_age,
                        "DIST": distance,
                        "Z": z,
                        "Z_WITH_SED": z,
                        "SIDE": "Internal",
                        "SHIFT": shift,
                        "PLATE": plate
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": coords
                    }
                }
                all_points_features.append(geojson_point_feature)
        for profile_feature in COL_ext_profiles.getFeatures():
            plate = profile_feature.attribute('PLATE')
            geom = profile_feature.geometry()
            multi_point = geom.asMultiPoint()
            feat_start_point = multi_point[0]
            feature_age = profile_feature.attribute('FEAT_AGE')
            shift = profile_feature.attribute("SHIFT")
            for point in multi_point:
                distance = feature_conversion_tools.prod_scal(feat_start_point,1,point,1)
                if distance == 0: #Skip original point as we already have a point at feature line position created from internal profile
                    pass
                else:
                    z = col_tools.collision_profile(feature_age,distance,front_x_young,shift,ridge_depth, z_up_plate)
                    coords = [point[0], point[1]]
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "COL",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": z,
                            "Z_WITH_SED": z,
                            "SIDE": "External",
                            "SHIFT": shift,
                            "PLATE": plate
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": coords
                        }
                    }
                    all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,f"COL_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        feature_conversion_tools.check_point_plate_intersection(age, "COL")
        feature_conversion_tools.add_id_nodes_setting(age, "COL")
        feature_conversion_tools.add_layer_to_group(output_points_layer_path, f"{int(age)} Ma", "COL")
