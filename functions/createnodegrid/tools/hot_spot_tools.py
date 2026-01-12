import os
from qgis.core import (edit,Qgis, QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform,QgsProject,
                       QgsMessageLog,QgsPointXY, QgsFeature, QgsVectorLayer)
import processing

from ...base_tools import BaseTools

from ..tools.feature_conversion_tools import FeatureConversionTools


class HOTConversionTools:
    APPEARANCE = "APPEARANCE"

    def __init__(self, base_tools: BaseTools):
        self.base_tools = base_tools
        self.output_folder_path = self.base_tools.get_layer_path("Output Folder")
        self.feature_conversion_tools = FeatureConversionTools(self.base_tools)


    def z_cont_hs(self ,feature_age, z_min, z_max, ridge_depth):
        if feature_age > 330:
            z = 240.38
        else:
            PCM_330 = self.feature_conversion_tools.PCM(330, ridge_depth)
            PCM_0 = self.feature_conversion_tools.PCM(0, ridge_depth)
            PCM_feature_age = self.feature_conversion_tools.PCM(feature_age, ridge_depth)

            A = (z_min - z_max) / (PCM_330 - PCM_0)
            B = z_min - (A * PCM_330)

            z = A * PCM_feature_age + B + 240.38
        return z


