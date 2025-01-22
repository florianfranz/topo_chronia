import os
import processing
from qgis.core import Qgis, QgsVectorLayer, QgsRasterLayer, QgsProject, QgsMessageLog,QgsCoordinateReferenceSystem

from ...base_tools import BaseTools
base_tools = BaseTools()

class RasterTools:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    def __init__(self):
        pass

    def perform_raster_interpolation_wcea(self,age):
        """
        Performs raster interpolation using the QGIS TIN method,in ESRI:54034 projection -
        World Cylindrical Equal Area (WCEA).
        This is the main interpolation, on which the oceanic volume and sea-level
        are calculated. the use of WCEA is made to lower the uncertainties created
        when converting an interpolated raster from EPSG:4326 to an WCEA.
        Duplicate geometries (nodes) are deleted to avoid confusion befor einterpolation.
        No data cells are filled.
        """
        output_folder_path = base_tools.get_layer_path("Output Folder")
        nodes_layer_path = os.path.join(output_folder_path, f"all_nodes_{int(age)}.geojson")
        reproj_nodes_layer_path = os.path.join(output_folder_path, f"reproj_all_nodes_{int(age)}.geojson")
        output_raster_path = os.path.join(output_folder_path, f"raster_{int(age)}.tif")
        filled_output_raster_path = output_raster_path.replace(".tif", "_filled.tif")
        nodes_layer_path_nodup = os.path.join(output_folder_path, f"all_nodes_{int(age)}_nodup.geojson")
        processing.run("native:deleteduplicategeometries",
                       {'INPUT': nodes_layer_path,
                        'OUTPUT': nodes_layer_path_nodup})
        nodes_layer_nodup = QgsVectorLayer(nodes_layer_path_nodup, "All Nodes No Duplicates", "ogr")
        processing.run("native:reprojectlayer",
                       {'INPUT': nodes_layer_nodup.source(),
                        'TARGET_CRS': QgsCoordinateReferenceSystem('ESRI:54034'), 'CONVERT_CURVED_GEOMETRIES': False,
                        'OPERATION': '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=cea +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84',
                        'OUTPUT': reproj_nodes_layer_path})
        reproj_nodes_layer = QgsVectorLayer(reproj_nodes_layer_path, "Reproj all nodes", "ogr")
        processing.run("qgis:tininterpolation", {
            'INTERPOLATION_DATA': f'{reproj_nodes_layer.source()}::~::0::~::3::~::0',
            'METHOD': 0,
            'EXTENT': '-20037505.459500000,20037505.424600001,-6360516.244100000,6363880.960000000 [ESRI:54034]',
            'PIXEL_SIZE': 10000, 'OUTPUT': output_raster_path})

        processing.run("gdal:fillnodata", {
            'INPUT': output_raster_path,
            'BAND': 1,
            'DISTANCE': 150,
            'ITERATIONS': 3,
            'MASK_LAYER': None,
            'OPTIONS': '', 'EXTRA': '',
            'OUTPUT': filled_output_raster_path})

    def perform_final_raster_interpolation(self,age):
        """
        Performs the final raster interpolation with QGIS TIN method, with the water load
        corrected elevation values.
        """
        output_folder_path = base_tools.get_layer_path("Output Folder")
        reproj_nodes_layer_path = os.path.join(output_folder_path, f"reproj_all_nodes_{int(age)}.geojson")

        reproj_nodes_layer = QgsVectorLayer(reproj_nodes_layer_path, "Nodes", "ogr")
        final_raster_path = os.path.join(output_folder_path, f"raster_final_{int(age)}.tif")
        final_filled_raster_path = os.path.join(output_folder_path, f"raster_final_filled_{int(age)}.tif")

        processing.run("qgis:tininterpolation", {
            'INTERPOLATION_DATA': f'{reproj_nodes_layer.source()}::~::0::~::5::~::0',
            'METHOD': 0,
            'EXTENT': '-20037505.459500000,20037505.424600001,-6360516.244100000,6363880.960000000 [ESRI:54034]',
            'PIXEL_SIZE': 10000, 'OUTPUT': final_raster_path})

        processing.run("gdal:fillnodata", {
            'INPUT': final_raster_path,
            'BAND': 1,
            'DISTANCE': 150,
            'ITERATIONS': 3,
            'MASK_LAYER': None,
            'OPTIONS': '', 'EXTRA': '',
            'OUTPUT': final_filled_raster_path})