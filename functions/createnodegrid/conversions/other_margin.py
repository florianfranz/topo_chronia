import os
import json
import math
from qgis.PyQt.QtCore import QVariant
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsMessageLog, QgsRasterLayer,
                       QgsVectorFileWriter, QgsField, QgsGeometry, QgsFeature, QgsPointXY, QgsProject)

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

from ..tools.sediments_tools import SEDConversionTools
sed_tools = SEDConversionTools()


class OTMConversion:
    INPUT_FILE_PATH = "input_files.txt"
    geodesic_grid_path = base_tools.get_layer_path("Geodesic Grid")
    geodesic_grid_layer = QgsVectorLayer(geodesic_grid_path, "Geodesic Grid", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")

    def __init__(self):
        pass
    def other_margin_to_nodes(self,age):
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        x_min = -25
        x_max = 51
        step_length = 100
        continent_polygons_layer_path = os.path.join(self.output_folder_path,f"continent_polygons_age_{int(age)}.geojson")
        continent_polygon_layer = QgsVectorLayer(continent_polygons_layer_path,"Aggregated Continents","ogr")
        raster_prelim_path = os.path.join(self.output_folder_path, f"qgis_tin_raster_prelim_{int(age)}.tif")
        raster_prelim = QgsRasterLayer(raster_prelim_path,"Preliminary Raster")
        dens_OTM_lines_layer_path = os.path.join(self.output_folder_path, f"dens_OTM_lines_{int(age)}.geojson")
        dens_OTM_lines = QgsVectorLayer(dens_OTM_lines_layer_path,"Densified OTM Lines", "ogr")
        OTM_multipoints = QgsVectorLayer("MultiPoint?crs=EPSG:4326", "OTM MultiPoints","memory")
        points_provider = OTM_multipoints.dataProvider()
        OTM_multipoints.startEditing()
        attributes = dens_OTM_lines.fields().toList()
        points_provider.addAttributes(attributes)
        points_provider.addAttributes([ QgsField('Z', QVariant.Double),QgsField('CONT', QVariant.Double),QgsField('OC', QVariant.Double),QgsField('FEAT_AGE', QVariant.Double)])
        OTM_multipoints.updateFields()
        OTM_multipoints.commitChanges()
        for feature in dens_OTM_lines.getFeatures():
            geom = feature.geometry()
            coords_list = [QgsPointXY(pt) for part in geom.parts() for pt in part]
            multipoint_geom = QgsGeometry.fromMultiPointXY(coords_list)
            new_feature = QgsFeature()
            new_feature.setGeometry(multipoint_geom)
            new_feature.setAttributes(feature.attributes())
            points_provider.addFeature(new_feature)
        OTM_multipoints.commitChanges()
        OTM_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","OTM Profiles","memory")
        profiles_provider = OTM_profiles.dataProvider()
        profiles_provider.addAttributes(attributes)
        OTM_profiles.updateFields()
        for other_margin_feature in OTM_multipoints.getFeatures():
            geom = other_margin_feature.geometry()
            multi_point = geom.asMultiPoint()
            if len(multi_point) < 2:
                pass
            else:
                for i in range(len(multi_point)):
                    if i < len(multi_point) - 1:
                        point1 = multi_point[i]
                        point2 = multi_point[i + 1]
                        flag = 0
                    else:
                        point1 = multi_point[i]
                        point2 = multi_point[i-1]
                        flag = 1
                    feature = QgsFeature()
                    profile_geometry = feature_conversion_tools.create_profile(point1,point2,x_min,x_max,step_length, flag, "normal")
                    if profile_geometry:
                        feature.setGeometry(profile_geometry)
                        feature.setAttributes(other_margin_feature.attributes())
                        profiles_provider.addFeature(feature)
            OTM_profiles.commitChanges()
        output_profiles_layer_path = os.path.join(self.output_folder_path,f"OTM_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(OTM_profiles,output_profiles_layer_path,'utf-8',OTM_profiles.crs(),"GeoJSON")
        all_points_features = []
        for profile_feature in OTM_profiles.getFeatures():
            feature_abs_age = profile_feature.attribute('AGE')
            feature_age = feature_abs_age - age
            geom = profile_feature.geometry()
            multi_point = geom.asMultiPoint()
            distance = 8888
            first_point = multi_point[0]
            first_point_geom = QgsGeometry.fromPointXY(first_point)
            first_point_coords = [first_point[0], first_point[1]]
            last_point = multi_point[-1]
            last_point_geom = QgsGeometry.fromPointXY(last_point)
            last_point_coords = [last_point[0], last_point[1]]
            for cont_feature in continent_polygon_layer.getFeatures():
                if cont_feature.geometry().intersects(first_point_geom) and not cont_feature.geometry().intersects(
                        last_point_geom):
                    #Case 1: first point is in continents, last point is in oceans
                    val, res = raster_prelim.dataProvider().sample(last_point, 1)
                    if math.isnan(val):
                        raster_depth = -4000
                    else:
                        raster_depth = float(val)
                    raster_age = feature_conversion_tools.inversePCM(raster_depth,ridge_depth)
                    abys_sed = sed_tools.abyssal_sediments(age,age + raster_age)
                    z_with_sed = abys_sed + raster_depth
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "OTM",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": 0,
                            "Z_WITH_SED": 0,
                            "SIDE": "CONTINENT"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": first_point_coords
                        }
                    }
                    all_points_features.append(geojson_point_feature)
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "OTM",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": raster_depth,
                            "Z_WITH_SED": z_with_sed,
                            "SIDE": "OCEAN"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": last_point_coords
                        }
                    }
                    all_points_features.append(geojson_point_feature)
                elif not cont_feature.geometry().intersects(
                    first_point_geom) and cont_feature.geometry().intersects(last_point_geom):
                    #Case 2: last point is in continents, first point is in oceans
                    val, res = raster_prelim.dataProvider().sample(first_point, 1)
                    raster_depth = float(val)
                    raster_age = feature_conversion_tools.inversePCM(raster_depth,ridge_depth)
                    abys_sed = sed_tools.abyssal_sediments(age,age + raster_age)
                    z_with_sed = abys_sed + raster_depth
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "OTM",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": raster_depth,
                            "Z_WITH_SED": z_with_sed,
                            "SIDE": "OCEAN"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": first_point_coords
                        }
                    }
                    all_points_features.append(geojson_point_feature)
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "OTM",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": 0,
                            "Z_WITH_SED": 0,
                            "SIDE": "CONTINENT"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": last_point_coords
                        }
                    }
                    all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,f"OTM_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        feature_conversion_tools.add_id_nodes_setting(age, "OTM")