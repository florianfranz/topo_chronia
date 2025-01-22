import os
import json
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsProject, QgsFeatureRequest, QgsMessageLog, QgsVectorFileWriter,
                       QgsPointXY, QgsGeometry, QgsFeature,QgsSpatialIndex)

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class CRAConversion:
    INPUT_FILE_PATH = "input_files.txt"
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    geodesic_grid_path = base_tools.get_layer_path("Geodesic Grid")
    geodesic_grid_layer = QgsVectorLayer(geodesic_grid_path, "Geodesic Grid", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    def __init__(self):
        pass
    def craton_to_nodes(self, age):
        crat_z_value = 500
        cont_z_value = 240.38
        craton_polygons_path = os.path.join(self.output_folder_path, f"CRA_aggreg_polyg_{int(age)}.geojson")
        CRA_polygons = QgsVectorLayer(craton_polygons_path,f"CRA aggreg polygons {int(age)}","ogr")
        continent_filter = f"{self.APPEARANCE} = {age}"
        continent_spatial_index = QgsSpatialIndex(
            self.continent_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(continent_filter)))
        all_points_features = []
        for polygon in CRA_polygons.getFeatures():
            polygon_geom = polygon.geometry().asPolygon()
            for vertices in polygon_geom:
                for vertex in vertices:
                    x_coord = vertex.x()
                    y_coord = vertex.y()
                    coords = [x_coord, y_coord]
                    vertex_xy = QgsGeometry.fromPointXY(vertex)
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
                        geojson_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": "CRA",
                                "FEAT_AGE": 9999,
                                "DIST": 0,
                                "Z": crat_z_value,
                                "Z_WITH_SED": crat_z_value,
                                "SIDE": "Border"
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": coords
                            }
                        }
                        all_points_features.append(geojson_feature)
        for polygon in CRA_polygons.getFeatures():
            polygon_geom = polygon.geometry()
            int_buffered_polygon = polygon_geom.buffer(-0.1, 1)
            for point in self.geodesic_grid_layer.getFeatures():
                geom = point.geometry()
                point_geom = point.geometry().asPoint()
                x = point_geom.x()
                y = point_geom.y()
                coords = [x, y]
                vertex_xy = QgsGeometry.fromPointXY(point_geom)
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
                    if int_buffered_polygon.intersects(geom):
                        geojson_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": "CRA",
                                "FEAT_AGE": 9999,
                                "DIST": 8888,
                                "Z": crat_z_value,
                                "Z_WITH_SED": crat_z_value,
                                "SIDE": "Internal"
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": coords
                            }
                        }
                        all_points_features.append(geojson_feature)
        for polygon in CRA_polygons.getFeatures():
            polygon_geom = polygon.geometry()
            ext_buffered_polygon = polygon_geom.buffer(0.75, 1)
            if ext_buffered_polygon.isMultipart():
                ext_buffered_polygon_geom = ext_buffered_polygon.asMultiPolygon()
                for part in ext_buffered_polygon_geom:
                    for vertices in part:
                        for vertex in vertices:
                            x_coord = vertex.x()
                            y_coord = vertex.y()
                            coords = [x_coord, y_coord]
                            vertex_xy = QgsGeometry.fromPointXY(vertex)
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
                                geojson_feature = {
                                    "type": "Feature",
                                    "properties": {
                                        "TYPE": "CRA",
                                        "FEAT_AGE": 9999,
                                        "DIST": 0,
                                        "Z": cont_z_value,
                                        "Z_WITH_SED": cont_z_value,
                                        "SIDE": "External"
                                    },
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": coords
                                    }
                                }
                                all_points_features.append(geojson_feature)
            else:
                ext_buffered_polygon_geom = ext_buffered_polygon.asPolygon()
                for vertices in ext_buffered_polygon_geom:
                    for vertex in vertices:
                        x_coord = vertex.x()
                        y_coord = vertex.y()
                        coords = [x_coord, y_coord]
                        vertex_xy = QgsGeometry.fromPointXY(vertex)
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
                            geojson_feature = {
                                "type": "Feature",
                                "properties": {
                                    "TYPE": "CRA",
                                    "FEAT_AGE": 9999,
                                    "DIST": 0,
                                    "Z": cont_z_value,
                                    "Z_WITH_SED": cont_z_value,
                                    "SIDE": "External"
                                },
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": coords
                                }
                            }
                            all_points_features.append(geojson_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,f"CRA_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        feature_conversion_tools.add_id_nodes_setting(age, "CRA")