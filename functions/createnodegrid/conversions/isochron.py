import os
import json
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsMessageLog, QgsVectorFileWriter, QgsProject,
                       QgsPointXY, QgsGeometry, QgsField,QgsSpatialIndex)

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.sediments_tools import SEDConversionTools
sed_tools = SEDConversionTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class ISOConversion:
    output_folder_path = base_tools.get_layer_path("Output Folder")

    def __init__(self):
        pass
    def isochron_to_nodes(self, age):
        dens_ISO_lines_layer_path = os.path.join(self.output_folder_path, f"dens_ISO_lines_{int(age)}.geojson")
        dens_ISO_layer = QgsVectorLayer(dens_ISO_lines_layer_path, "Densified Isochrons Lines", 'ogr')
        dens_ISO_layer_features = list(dens_ISO_layer.getFeatures())
        ISO_points_layer = QgsVectorLayer("Point?crs=EPSG:4326","Isochron_points_layer","memory")
        provider = ISO_points_layer.dataProvider()
        ISO_points_layer.startEditing()
        attributes = dens_ISO_layer.fields().toList()
        provider.addAttributes(attributes)
        ISO_points_layer = QgsVectorLayer("Point?crs=EPSG:4326","Isochron_points_layer","memory")
        provider = ISO_points_layer.dataProvider()
        ISO_points_layer.startEditing()
        attributes = dens_ISO_layer.fields().toList()
        provider.addAttributes(attributes)
        all_points_features = []
        for feature in dens_ISO_layer_features:
            geom = feature.geometry()
            feature_age = feature.attribute('FEAT_AGE')
            if feature_age < 0:
                pass
            else:
                z = feature.attribute('Z')
                abys_sed = feature.attribute('ABYS_SED')
                plate = feature.attribute('PLATE')
                distance = 0
                coords_list = [QgsPointXY(pt) for part in geom.parts() for pt in part]
                for coord in coords_list:
                    coords = [coord[0], coord[1]]
                    geojson_point_feature = \
                        {"type":
                             "Feature",
                         "properties":
                             {"TYPE": "ISO",
                              "FEAT_AGE": feature_age,
                              "DIST": distance,
                              "Z": z,
                              "Z_WITH_SED" : z + abys_sed,
                              "PLATE": plate
                              },
                         "geometry":
                             {"type": "Point",
                              "coordinates": coords}
                         }
                    all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,f"ISO_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({"type": "FeatureCollection","features": all_points_features}, indent=2))
        output_nodes_layer_path = os.path.join(self.output_folder_path, f"all_nodes_{int(age)}.geojson")
        feature_conversion_tools.add_nodes(age,output_points_layer_path,output_nodes_layer_path,first_build=False)
        feature_conversion_tools.add_id_nodes_setting(output_points_layer_path)
        #feature_conversion_tools.add_layer_to_group(output_points_layer_path, f"{int(age)} Ma", "ISO")
