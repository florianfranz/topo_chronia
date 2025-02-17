import os
import json
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsRasterLayer, QgsMessageLog, QgsField,
                       QgsVectorFileWriter, QgsGeometry, QgsPointXY, QgsFeature, QgsProject, QgsSpatialIndex)
from qgis.PyQt.QtCore import QVariant

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.rift_tools import RIBConversionTools
rib_tools = RIBConversionTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class RIBConversion:
    INPUT_FILE_PATH = "input_files.txt"
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    def __init__(self):
        pass

    def rift_to_nodes(self, age):
        step_length = 50
        x_min = 0
        x_max_ext = 551
        x_max_int = 201
        continent_polygons_layer_path = os.path.join(self.output_folder_path,f"continent_polygons_age_{int(age)}.geojson")
        agg_continent_polygon_layer = QgsVectorLayer(continent_polygons_layer_path, "Aggregated Continents", "ogr")
        basins_polygons_path = os.path.join(self.output_folder_path, f"RIB_polygons_{int(age)}_final.geojson")
        basins_polygon_layer = QgsVectorLayer(basins_polygons_path, "Aggregated Basins", "ogr")
        dens_RIB_layer_path = os.path.join(self.output_folder_path, f"dens_RIB_lines_{int(age)}.geojson")
        dens_RIB_lines = QgsVectorLayer(dens_RIB_layer_path, "Densified RIB Lines", 'ogr')
        RIB_multipoints = QgsVectorLayer("MultiPoint?crs=EPSG:4326", "RIB Multipoints", "memory")
        points_provider = RIB_multipoints.dataProvider()
        RIB_multipoints.startEditing()
        attributes = dens_RIB_lines.fields().toList()
        points_provider.addAttributes(attributes)
        points_provider.addAttributes([QgsField('Z', QVariant.Double)])
        RIB_multipoints.updateFields()
        RIB_multipoints.commitChanges()
        continent_feature = next(agg_continent_polygon_layer.getFeatures())
        continent_geometry = continent_feature.geometry()
        spatial_index_int_profiles = QgsSpatialIndex()
        geometry_dict_int_profiles = {}
        spatial_index_polygons = QgsSpatialIndex()
        for polygon in basins_polygon_layer.getFeatures():
            spatial_index_polygons.insertFeature(polygon)
        for feature in dens_RIB_lines.getFeatures():
            feature_abs_age = feature.attribute('AGE')
            if feature_abs_age != 9999:
                geom = feature.geometry()
                if geom.intersects(continent_geometry):
                    if geom.isMultipart():
                        coords_list = []
                        multi_line = geom.asMultiPolyline()
                        for line in multi_line:
                            coords_list.extend([QgsPointXY(pt) for pt in line])
                    else:
                        coords_list = [QgsPointXY(pt) for pt in geom.asPolyline()]
                    multipoint_geom = QgsGeometry.fromMultiPointXY(coords_list)
                    new_feature = QgsFeature()
                    new_feature.setGeometry(multipoint_geom)
                    new_feature.setAttributes(feature.attributes())
                    points_provider.addFeature(new_feature)
        RIB_multipoints.commitChanges()
        RIB_internal_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326", "Rift Internal Profiles", "memory")
        internal_profiles_provider = RIB_internal_profiles.dataProvider()
        internal_profiles_provider.addAttributes(attributes)
        RIB_internal_profiles.updateFields()
        RIB_external_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326", "Rift External Profiles", "memory")
        external_profiles_provider = RIB_external_profiles.dataProvider()
        external_profiles_provider.addAttributes(attributes)
        RIB_external_profiles.updateFields()
        for rift_feature in RIB_multipoints.getFeatures():
            geom = rift_feature.geometry()
            multi_point = geom.asMultiPoint()
            if len(multi_point) <= 2:
                pass
            else:
                for i in range(len(multi_point)):
                    point1 = multi_point[i]
                    if i < len(multi_point) - 1:
                        point2 = multi_point[i + 1]
                        flag = 0
                    else:
                        point2 = multi_point[i - 1]
                        flag = 1
                    feature = QgsFeature()
                    internal_profiles_geometry = feature_conversion_tools.create_profile(point1, point2, x_min, x_max_int,step_length, flag, "normal")
                    if internal_profiles_geometry:
                        bas_included_profile_geometry = feature_conversion_tools.cut_profile_spi(internal_profiles_geometry, basins_polygon_layer, "keep inside", "positive", age, True)
                        if bas_included_profile_geometry:
                            cont_excluded_profile_geometry = feature_conversion_tools.cut_profile_spi(bas_included_profile_geometry, self.continent_polygons_layer, "keep inside", "positive", age, False)
                            if cont_excluded_profile_geometry:
                                final_int_profile_geometry = feature_conversion_tools.check_profile_intersection(
                                        cont_excluded_profile_geometry, spatial_index_int_profiles,
                                        geometry_dict_int_profiles)
                                if final_int_profile_geometry:
                                    feature.setGeometry(final_int_profile_geometry)
                                    feature.setAttributes(rift_feature.attributes())
                                    profile_points = final_int_profile_geometry.asMultiPoint()
                                    for point in profile_points:
                                        point_id = len(geometry_dict_int_profiles)
                                        point_geom = QgsGeometry.fromPointXY(point)
                                        geometry_dict_int_profiles[point_id] = point_geom
                                        p_feature = QgsFeature(point_id)
                                        p_feature.setGeometry(point_geom)
                                        spatial_index_int_profiles.insertFeature(p_feature)
                                    internal_profiles_provider.addFeature(feature)
                    feature = QgsFeature()
                    external_profile_geometry = feature_conversion_tools.create_profile(point1, point2, x_min, x_max_ext,step_length, flag, "inverse")
                    if external_profile_geometry:
                        bas_excluded_profile_geometry = feature_conversion_tools.cut_profile_spi(external_profile_geometry, basins_polygon_layer, "keep outside", "positive", age, True)
                        if bas_excluded_profile_geometry:
                            cont_excluded_profile_geometry = feature_conversion_tools.cut_profile_spi(bas_excluded_profile_geometry, self.continent_polygons_layer, "keep inside", "positive", age, False)
                            if cont_excluded_profile_geometry:
                                final_ext_profile_geometry = feature_conversion_tools.check_profile_intersection(
                                    cont_excluded_profile_geometry, spatial_index_int_profiles,
                                    geometry_dict_int_profiles)
                                if final_ext_profile_geometry:
                                    feature.setGeometry(final_ext_profile_geometry)
                                    feature.setAttributes(rift_feature.attributes())
                                    profile_points = final_ext_profile_geometry.asMultiPoint()
                                    for point in profile_points:
                                        point_id = len(geometry_dict_int_profiles)
                                        point_geom = QgsGeometry.fromPointXY(point)
                                        geometry_dict_int_profiles[point_id] = point_geom
                                        p_feature = QgsFeature(point_id)
                                        p_feature.setGeometry(point_geom)
                                        spatial_index_int_profiles.insertFeature(p_feature)
                                    external_profiles_provider.addFeature(feature)
        RIB_internal_profiles.commitChanges()
        output_profiles_layer_path = os.path.join(self.output_folder_path, f"RIB_internal_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(RIB_internal_profiles, output_profiles_layer_path, 'utf-8',
                                                RIB_internal_profiles.crs(), "GeoJSON")
        RIB_external_profiles.commitChanges()
        output_profiles_layer_path = os.path.join(self.output_folder_path, f"RIB_external_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(RIB_external_profiles, output_profiles_layer_path, 'utf-8',
                                                RIB_external_profiles.crs(), "GeoJSON")

        all_points_features = []
        for int_profile in RIB_internal_profiles.getFeatures():
            crest_z = int_profile.attribute("Z_CREST")
            through_y = int_profile.attribute("TYR")
            feature_age = int_profile.attribute("FEAT_AGE")
            geom = int_profile.geometry()
            multi_point = geom.asMultiPoint()
            feat_start_point = multi_point[0]
            for point in multi_point:
                distance = feature_conversion_tools.prod_scal(feat_start_point, 1, point, 1)
                if distance == 0:
                    side = "Rift"
                else:
                    side = "Internal"
                distance = distance * -1
                x_coord = point[0] + 0.001
                y_coord = point[1] + 0.001
                coords = [x_coord, y_coord]
                z = float(rib_tools.rift_profile(distance, crest_z, through_y, feature_age, age))
                geojson_RIB_feature = {
                    "type": "Feature",
                    "properties": {
                        "TYPE": "RIB",
                        "FEAT_AGE": feature_age,
                        "DIST": distance,
                        "Z": z,
                        "Z_WITH_SED": z,
                        "CREST_Z": crest_z,
                        "SIDE": side
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": coords
                    }
                }
                all_points_features.append(geojson_RIB_feature)
        for ext_profile in RIB_external_profiles.getFeatures():
            crest_z = ext_profile.attribute("Z_CREST")
            through_y = ext_profile.attribute("TYR")
            feature_age = ext_profile.attribute("FEAT_AGE")
            geom = ext_profile.geometry()
            multi_point = geom.asMultiPoint()
            feat_start_point = multi_point[0]
            for point in multi_point:
                distance = feature_conversion_tools.prod_scal(feat_start_point, 1, point, 1)
                if distance == 0:
                    pass
                if point[0] > 180 or point[0] < -180 or point[1] > 86.5 or point[1] < -86.5:
                    pass
                else:
                    x_coord = point[0] + 0.001
                    y_coord = point[1] + 0.001
                    coords = [x_coord, y_coord]
                    z = float(rib_tools.rift_profile(distance, crest_z, through_y, feature_age, age))
                    geojson_RIB_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "RIB",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": z,
                            "Z_WITH_SED": z,
                            "CREST_Z": crest_z,
                            "SIDE": "External"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": coords
                        }
                    }
                    all_points_features.append(geojson_RIB_feature)
        output_points_layer_path = os.path.join(self.output_folder_path, f"RIB_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        feature_conversion_tools.add_id_nodes_setting(age, "RIB")
        feature_conversion_tools.add_layer_to_group(output_points_layer_path, f"{int(age)} Ma", "RIB")
