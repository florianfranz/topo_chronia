import os
import json
from qgis.core import Qgis, QgsVectorLayer, QgsProject,QgsRasterLayer,QgsPointXY

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class CTNConversion:
    INPUT_FILE_PATH = "input_files.txt"
    geodesic_grid_path = base_tools.get_layer_path("Geodesic Grid")
    geodesic_grid_layer = QgsVectorLayer(geodesic_grid_path, "Geodesic Grid", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")

    def __init__(self):
        pass

    def continent_geode_to_nodes(self, age):
        continent_polygons_layer_path = os.path.join(self.output_folder_path,
                                                     f"continent_polygons_age_{int(age)}.geojson")
        continent_polygon_layer = QgsVectorLayer(continent_polygons_layer_path,
                                                 "Aggregated Continents, "
                                                 "'ogr'")
        cont_z = 240.38
        all_points_features = []
        int_buffer_distance = -5.5
        for continent_polygon_feature in continent_polygon_layer.getFeatures():
            int_buffered_polygon = continent_polygon_feature.geometry().buffer(int_buffer_distance, 10)
            for feature in self.geodesic_grid_layer.getFeatures():
                    point_geom = feature.geometry()
                    x = point_geom.asPoint().x()
                    y = point_geom.asPoint().y()
                    coords = [x, y]
                    if int_buffered_polygon.intersects(point_geom):
                        geojson_point_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": "CTN",
                                "FEAT_AGE": 7777,
                                "DIST": 8888,
                                "Z": cont_z,
                                "Z_WITH_SED": cont_z
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": coords
                            }
                        }
                        all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,
                                                f"CTN_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        feature_conversion_tools.add_id_nodes_setting(age, "CTN")