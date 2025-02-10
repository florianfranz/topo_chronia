import os
import json
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsMessageLog, QgsVectorFileWriter, QgsProject,
                       QgsPointXY, QgsGeometry, QgsField)

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.hot_spot_tools import HOTConversionTools
hot_tools = HOTConversionTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class RIDConversion:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")

    def __init__(self):
        pass
    def ridge_to_nodes(self, age):
        dens_RID_lines_layer_path = os.path.join(self.output_folder_path, f"dens_RID_lines_{int(age)}.geojson")
        dens_ridge_layer = QgsVectorLayer(dens_RID_lines_layer_path,"Densified Ridges Lines",'ogr')
        dens_ridge_layer_features = list(dens_ridge_layer.getFeatures())
        ridge_points_layer = QgsVectorLayer("Point?crs=EPSG:4326","Ridge_points_layer","memory")
        provider = ridge_points_layer.dataProvider()
        ridge_points_layer.startEditing()
        attributes = dens_ridge_layer.fields().toList()
        provider.addAttributes(attributes)
        all_points_features =[]
        for feature in dens_ridge_layer_features:
            geom = feature.geometry()
            feature_age = feature.attribute('FEAT_AGE')
            z = feature.attribute('Z')
            distance = 0
            coords_list = [QgsPointXY(pt) for part in geom.parts() for pt in part]
            for coord in coords_list:
                coords = [coord[0], coord[1]]
                geojson_point_feature = {"type": "Feature","properties": {"TYPE": "RID","FEAT_AGE": feature_age,"DIST": distance,"Z": z,"Z_WITH_SED": z},"geometry": {"type": "Point","coordinates": coords}}
                all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path, f"RID_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({"type": "FeatureCollection", "features": all_points_features}, indent=2))
        feature_conversion_tools.add_nodes(age, output_points_layer_path, first_build=True)
        feature_conversion_tools.add_id_nodes_setting(age, "RID")
        feature_conversion_tools.add_layer_to_group(output_points_layer_path, str(int(age)), "RID")


