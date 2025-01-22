import os
import processing
from qgis.core import QgsVectorLayer

from ...base_tools import BaseTools
base_tools = BaseTools()


class PreRasterTools:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"

    def __init__(self):
        pass

    def generate_temporary_raster(self, age):
        """
        Generates the preliminary raster based on the all nodes layer,
        comprising only RID + ISO nodes.
        """
        nodes_layer_path = os.path.join(self.output_folder_path,
                                        f"all_nodes_{int(age)}.geojson")

        nodes_layer = QgsVectorLayer(nodes_layer_path,
                                     "Nodes",
                                     "ogr")

        self.perform_prelim_raster_interpolation(nodes_layer,
                                          age)

    def perform_prelim_raster_interpolation(self,
                                     nodes_layer,
                                     age):
        """
        Performs a TIN interpolation and fills no data cells for the preliminary raster.
        """
        qgis_tin_unfilled_output_raster_path = os.path.join(self.output_folder_path,
                                                  f"qgis_tin_raster_unfilled_prelim_{int(age)}.tif")
        qgis_tin_output_raster_path = os.path.join(self.output_folder_path,
                                                  f"qgis_tin_raster_prelim_{int(age)}.tif")

        processing.run("qgis:tininterpolation", {
            'INTERPOLATION_DATA': f"{nodes_layer.source()}::~::0::~::3::~::0",
            'METHOD': 0,
            'EXTENT': '-180,180,-90,90 [EPSG:4326]',
            'PIXEL_SIZE': 0.1,
            'OUTPUT': qgis_tin_unfilled_output_raster_path,
        })
        processing.run("gdal:fillnodata", {
            'INPUT': qgis_tin_unfilled_output_raster_path,
            'BAND': 1,
            'DISTANCE': 100,
            'ITERATIONS': 3,
            'MASK_LAYER': None,
            'OPTIONS': '', 'EXTRA': '',
            'OUTPUT': qgis_tin_output_raster_path})

