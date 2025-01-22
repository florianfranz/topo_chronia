import os
import json
import processing
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsMessageLog, QgsVectorFileWriter, QgsProject,
                       QgsPointXY, QgsGeometry, QgsRasterLayer, QgsSpatialIndex,QgsProcessingFeatureSourceDefinition,
                       QgsWkbTypes)

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.hot_spot_tools import HOTConversionTools
hot_tools = HOTConversionTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class HOTConversion:
    INPUT_FILE_PATH = "input_files.txt"
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    def __init__(self):
        pass
    def hot_spot_to_nodes(self,age):
        PARAM_GENERAL_CONTINENTZ = 240.38
        PARAM_HS_ContVolcanoZMin = 293 - PARAM_GENERAL_CONTINENTZ
        PARAM_HS_ContVolcanoZMax = 1250 - PARAM_GENERAL_CONTINENTZ
        hot_crest = 1500
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        dens_HOT_lines_layer_path = os.path.join(self.output_folder_path, f"dens_HOT_lines_{int(age)}.geojson")
        dens_HOT_layer = QgsVectorLayer(dens_HOT_lines_layer_path, "Densified HOT layer", "ogr")
        HOT_features = list(dens_HOT_layer.getFeatures())
        if len(HOT_features) == 0:
            return
        else:
            all_polygons = []
            for feature in dens_HOT_layer.getFeatures():
                feat_age = feature.attribute("AGE") - age
                orig_id = feature.id()
                feature_level_coords = []
                if feature.geometry().isMultipart():
                    geom = feature.geometry().asMultiPolyline()
                    for part in geom:
                        if len(part) <= 3:
                            pass
                        else:
                            polygon_coords = []
                            for vertex in part:
                                x_coord = vertex.x()
                                y_coord = vertex.y()
                                coords = [x_coord, y_coord]
                                polygon_coords.append(coords)
                            if polygon_coords[0] != polygon_coords[-1]:
                                polygon_coords.append(polygon_coords[0])
                            polygon_feature = {
                                "type": "Feature",
                                "properties": {
                                    "TYPE": "HOT",
                                    "ORIG_ID": int(orig_id),
                                    "FEAT_AGE": feat_age
                                },
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [polygon_coords]
                                }
                            }
                            all_polygons.append(polygon_feature)
                else:
                    geom = feature.geomtry().asPolyline()
                    if len(geom) <= 3:
                        pass
                    else:
                        polygon_coords = []
                        for vertex in geom:
                            x_coord = vertex.x()
                            y_coord = vertex.y()
                            coords = [x_coord, y_coord]
                            polygon_coords.append(coords)
                        if polygon_coords[0] != polygon_coords[-1]:
                            polygon_coords.append(polygon_coords[0])
                        feature_level_coords.append(polygon_coords)
                        polygon_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": "HOT",
                                "ORIG_ID": int(orig_id),
                                "FEAT_AGE": feat_age
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [polygon_coords]
                            }
                        }
                        all_polygons.append(polygon_feature)
            output_polygons_layer_path = os.path.join(self.output_folder_path,f"HOT_polygons_{int(age)}.geojson")
            fixed_polygon_layer_path = output_polygons_layer_path.replace(f"{int(age)}.geojson", f"{int(age)}_fixed.geojson")
            diss_polygon_layer_path = output_polygons_layer_path.replace(f"{int(age)}.geojson", f"{int(age)}_diss.geojson")
            with open(output_polygons_layer_path, 'w') as output_file:
                output_file.write(json.dumps({
                    "type": "FeatureCollection",
                    "features": all_polygons
                }, indent=2))
            processing.run("native:fixgeometries",
                           {'INPUT': output_polygons_layer_path,
                            'METHOD': 1, 'OUTPUT': fixed_polygon_layer_path})
            processing.run("native:dissolve", {'INPUT': QgsProcessingFeatureSourceDefinition(
                fixed_polygon_layer_path,
                selectedFeaturesOnly=False, featureLimit=-1,
                flags=QgsProcessingFeatureSourceDefinition.FlagOverrideDefaultGeometryCheck,
                geometryCheck=QgsFeatureRequest.GeometrySkipInvalid), 'FIELD': [], 'SEPARATE_DISJOINT': True,
                                               'OUTPUT': diss_polygon_layer_path})
            HOT_polygon_layer = QgsVectorLayer(diss_polygon_layer_path, f"HOT_aggregated_{int(age)}", 'ogr')
            HOT_volcanoes_layer_path = os.path.join(self.output_folder_path,f"HOT_volcanoes_{int(age)}.geojson")
            all_HOT_features = []
            continent_filter = f"{self.APPEARANCE} = {age}"
            continent_spatial_index = QgsSpatialIndex(
                self.continent_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(continent_filter)))
            processing.run("native:pointonsurface", {'INPUT': QgsProcessingFeatureSourceDefinition(
                fixed_polygon_layer_path,
                selectedFeaturesOnly=False, featureLimit=-1,
                flags=QgsProcessingFeatureSourceDefinition.FlagOverrideDefaultGeometryCheck,
                geometryCheck=QgsFeatureRequest.GeometrySkipInvalid), 'ALL_PARTS': True, 'OUTPUT': HOT_volcanoes_layer_path})
            HOT_volcanoes = QgsVectorLayer(HOT_volcanoes_layer_path, "HOT Volcanoes", "ogr")
            for point in HOT_volcanoes.getFeatures():
                feature_geometry = point.geometry()
                if feature_geometry.wkbType() != QgsWkbTypes.Point:
                    pass
                else:
                    point_geom = point.geometry().asPoint()
                    geom = point.geometry()
                    feature_age = point.attribute("FEAT_AGE")
                    intersects = False
                    candidate_ids = continent_spatial_index.intersects(geom.boundingBox())
                    if candidate_ids:
                        for candidate_id in candidate_ids:
                            continent_feature = next(
                                self.continent_polygons_layer.getFeatures(QgsFeatureRequest(candidate_id)))
                            continent_geom = continent_feature.geometry()
                            if continent_geom.contains(point_geom):
                                intersects = True
                                break
                    if intersects:
                        location = "Continental"
                        hot_volc_z = float(
                            hot_tools.z_cont_hs(feature_age, PARAM_HS_ContVolcanoZMin, PARAM_HS_ContVolcanoZMax,
                                                ridge_depth))
                    else:
                        location = "Oceanic"
                        raster_depth = -4500
                        hs_z_value = 4500
                        hot_volc_z = raster_depth + hs_z_value
                    centroid_x = point_geom.x()
                    centroid_y = point_geom.y()
                    coords = [centroid_x, centroid_y]
                    HOT_geojson_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "HOT",
                            "ORIG_ID": point.attribute('ORIG_ID'),
                            "FEAT_AGE": point.attribute('FEAT_AGE'),
                            "PT_TYPE": "VOLCANO",
                            "Z": hot_volc_z,
                            "Z_WITH_SED": hot_volc_z,
                            "DIST": 0,
                            "LOCATION": location,
                            "ID": point.id()
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": coords
                        }
                    }
                    all_HOT_features.append(HOT_geojson_feature)

            for feature in HOT_polygon_layer.getFeatures():
                feature_geometry = feature.geometry()
                if feature_geometry.wkbType() not in (QgsWkbTypes.Polygon, QgsWkbTypes.MultiPolygon):
                    pass
                else:
                    feature_geometry_polygon = feature_geometry.asMultiPolygon()
                    centroid_point = feature_geometry.centroid().asPoint()
                    for part in feature_geometry_polygon:
                        for vertex in part[0]:
                            x_coord = vertex.x()
                            y_coord = vertex.y()
                            coords = [x_coord, y_coord]
                            vertex_xy = QgsGeometry.fromPointXY(vertex)
                            distance = feature_conversion_tools.prod_scal(centroid_point,1,vertex,1)
                            intersects = False
                            candidate_ids = continent_spatial_index.intersects(vertex_xy.boundingBox())
                            if candidate_ids:
                                for candidate_id in candidate_ids:
                                    continent_feature = next(
                                        self.continent_polygons_layer.getFeatures(QgsFeatureRequest(candidate_id)))
                                    continent_geom = continent_feature.geometry()
                                    if continent_geom.contains(vertex_xy):
                                        intersects = True
                                        break
                            if intersects:
                                location = "Continental"
                                hot_base_z = 240.38
                            else:
                                location = "Oceanic"
                                raster_depth = -4500
                                hot_base_z = raster_depth
                            HOT_geojson_feature = {
                                "type": "Feature",
                                "properties": {
                                    "TYPE": "HOT",
                                    "ORIG_ID": feature.attribute('ORIG_ID'),
                                    "FEAT_AGE": feature.attribute('FEAT_AGE'),
                                    "PT_TYPE": "BASEMENT",
                                    "Z": hot_base_z,
                                    "Z_WITH_SED": hot_base_z,
                                    "DIST": distance,
                                    "LOCATION": location,
                                    "ID": feature.id()
                                },
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": coords
                                }
                            }
                            all_HOT_features.append(HOT_geojson_feature)
                    crest_buffer = -0.2
                    crest_buffer_polygon = feature.geometry().buffer(crest_buffer, 1)
                    if crest_buffer_polygon.isMultipart():
                        crest_buffer_geometry = crest_buffer_polygon.asMultiPolygon()
                        for part in crest_buffer_geometry:
                            for vertices in part:
                                for vertex in vertices:
                                    x_coord = vertex.x()
                                    y_coord = vertex.y()
                                    coords = [x_coord, y_coord]
                                    vertex_xy = QgsGeometry.fromPointXY(vertex)
                                    distance = feature_conversion_tools.prod_scal(centroid_point,1,vertex,1)
                                    intersects = False
                                    candidate_ids = continent_spatial_index.intersects(vertex_xy.boundingBox())
                                    if candidate_ids:
                                        for candidate_id in candidate_ids:
                                            continent_feature = next(
                                                self.continent_polygons_layer.getFeatures(QgsFeatureRequest(candidate_id)))
                                            continent_geom = continent_feature.geometry()
                                            if continent_geom.contains(vertex_xy):
                                                intersects = True
                                                break
                                    if intersects:
                                        location = "Continental"
                                        hot_crest_z = 240.38
                                    else:
                                        location = "Oceanic"
                                        raster_depth= -4500
                                        hot_crest_z = raster_depth + hot_crest
                                    HOT_geojson_feature = {
                                        "type": "Feature",
                                        "properties": {
                                            "TYPE": "HOT",
                                            "ORIG_ID": feature.attribute('ORIG_ID'),
                                            "FEAT_AGE": feature.attribute('FEAT_AGE'),
                                            "PT_TYPE": "CREST",
                                            "Z": hot_crest_z,
                                            "Z_WITH_SED": hot_crest_z,
                                            "DIST": distance,
                                            "LOCATION": location,
                                            "ID": feature.id()
                                        },
                                        "geometry": {
                                            "type": "Point",
                                            "coordinates": coords
                                        }
                                    }
                                    all_HOT_features.append(HOT_geojson_feature)
                    else:
                        crest_buffer_geometry = crest_buffer_polygon.asPolygon()
                        for vertex in crest_buffer_geometry[0]:
                            x_coord = vertex.x()
                            y_coord = vertex.y()
                            coords = [x_coord, y_coord]
                            vertex_xy = QgsGeometry.fromPointXY(vertex)
                            distance = feature_conversion_tools.prod_scal(centroid_point,1,vertex,1)
                            candidate_ids = continent_spatial_index.intersects(vertex_xy.boundingBox())
                            intersects = False
                            if candidate_ids:
                                for candidate_id in candidate_ids:
                                    continent_feature = next(
                                        self.continent_polygons_layer.getFeatures(QgsFeatureRequest(candidate_id)))
                                    continent_geom = continent_feature.geometry()
                                    if continent_geom.contains(vertex_xy):
                                        intersects = True
                                        break
                            if intersects:
                                location = "Continental"
                                hot_crest_z = 240.38
                            else:
                                location = "Oceanic"
                                raster_depth = -4500
                                hot_crest_z = raster_depth + hot_crest
                            HOT_geojson_feature = {
                                "type": "Feature",
                                "properties": {
                                    "TYPE": "HOT",
                                    "ORIG_ID": feature.attribute('ORIG_ID'),
                                    "FEAT_AGE": feature.attribute('FEAT_AGE'),
                                    "PT_TYPE": "CREST",
                                    "Z": hot_crest_z,
                                    "Z_WITH_SED": hot_crest_z,
                                    "DIST": distance,
                                    "LOCATION": location,
                                    "ID": feature.id()
                                },
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": coords
                                }
                            }
                            all_HOT_features.append(HOT_geojson_feature)
            output_points_layer_path = os.path.join(self.output_folder_path, f"HOT_nodes_{int(age)}.geojson")
            with open(output_points_layer_path, 'w') as output_file:
                output_file.write(json.dumps({
                    "type": "FeatureCollection",
                    "features": all_HOT_features
                }, indent=2))
            feature_conversion_tools.add_id_nodes_setting(age, "HOT")