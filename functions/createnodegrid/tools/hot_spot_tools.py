import os
from qgis.core import (edit,Qgis, QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform,QgsProject,
                       QgsMessageLog,QgsPointXY, QgsFeature, QgsVectorLayer)
import processing

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class HOTConversionTools:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"

    def __init__(self):
        pass

    def z_cont_hs(self ,feature_age, z_min, z_max, ridge_depth):
        if feature_age > 330:
            z = 240.38
        else:
            PCM_330 = feature_conversion_tools.PCM(330, ridge_depth)
            PCM_0 = feature_conversion_tools.PCM(0, ridge_depth)
            PCM_feature_age = feature_conversion_tools.PCM(feature_age, ridge_depth)

            A = (z_min - z_max) / (PCM_330 - PCM_0)
            B = z_min - (A * PCM_330)

            z = A * PCM_feature_age + B + 240.38
        return z


