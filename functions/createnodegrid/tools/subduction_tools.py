import math
from qgis.core import Qgis, QgsMessageLog

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class SUBConversionTools:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"

    def __init__(self):
        pass

    def subduction_profile(self, setting, distance, ridge_depth, raster_depth, z_up_plate, lat_distance):

        PARAM_AM_C_FFLEX = 8
        PARAM_IOS_vF = 1000
        PARAM_IOS_lambdaF = 0.57
        PARAM_IOS_Exp_Add = 0.5
        PARAM_IOS_Exp_Pow = 5
        PARAM_IOS_Exp_CurvMax = 2500
        PARAM_IOS_Exp_CurvMin = -500
        PARAM_IOS_LENGTH = 3.5
        PARAM_IOS_C_mG1 = 2.1
        PARAM_IOS_C_sG1 = 0.077
        PARAM_IOS_C_mG2 = 1.8
        PARAM_IOS_C_sG2 = 0.5
        PARAM_IOS_C_ArcYMax = 350
        PARAM_IOS_C_ArcYMin = -350
        PARAM_IOS_C_BulgeMax = 2000
        PARAM_IOS_C_BulgeMin = 1500

        PARAM_AM_Exp_Add = 0.5
        PARAM_AM_Exp_Pow = 5
        PARAM_AM_Exp_CurvMax = 250
        PARAM_AM_Exp_CurvMin = -1500
        PARAM_AM_LENGTH = 5.5
        PARAM_AM_C_mG1 = 2.6
        PARAM_AM_C_sG1 = 0.333
        PARAM_AM_C_mG2 = 3.5
        PARAM_AM_C_sG2 = 1
        PARAM_AM_C_ArcYMax = 5000
        PARAM_AM_C_ArcYMin = 1500
        PARAM_AM_C_BulgeMax = 1500
        PARAM_AM_C_BulgeMin = 1000
        if setting == 'Z_Subduction':
            pExpAdd = PARAM_IOS_Exp_Add
            pExpPower = PARAM_IOS_Exp_Pow
            pCurvMax = PARAM_IOS_Exp_CurvMax
            pCurvMin = PARAM_IOS_Exp_CurvMin
            pProfileLength = PARAM_IOS_LENGTH
            GaussMean1 = PARAM_IOS_C_mG1
            GaussSigma1 = PARAM_IOS_C_sG1
            GaussMean2 = PARAM_IOS_C_mG2
            GaussSigma2 = PARAM_IOS_C_sG2
            pArcYMax = PARAM_IOS_C_ArcYMax
            pArcYMin = PARAM_IOS_C_ArcYMin
            pBulgeYMax = PARAM_IOS_C_BulgeMax
            pBulgeYMin = PARAM_IOS_C_BulgeMin
        elif setting == 'Active_Margin':
            pExpAdd = PARAM_AM_Exp_Add
            pExpPower = PARAM_AM_Exp_Pow
            pCurvMax = PARAM_AM_Exp_CurvMax
            pCurvMin = PARAM_AM_Exp_CurvMin
            pProfileLength = PARAM_AM_LENGTH
            GaussMean1 = PARAM_AM_C_mG1
            GaussSigma1 = PARAM_AM_C_sG1
            GaussMean2 = PARAM_AM_C_mG2
            GaussSigma2 = PARAM_AM_C_sG2
            pArcYMax = PARAM_AM_C_ArcYMax
            pArcYMin = PARAM_AM_C_ArcYMin
            pBulgeYMax = PARAM_AM_C_BulgeMax
            pBulgeYMin = PARAM_AM_C_BulgeMin
        else:
            QgsMessageLog.logMessage(f"Setting is not of proper type. Value is {setting}", "Create Node Grid",
                                     Qgis.Info)

        PCM_min = feature_conversion_tools.PCM(0, ridge_depth)
        PCM_max = feature_conversion_tools.PCM(4567, ridge_depth)
        A = (1 - 0) / (PCM_min - PCM_max)
        B = 0 - A * PCM_max
        PCM_norm = A * raster_depth + B

        low_trench_depth = self.trench_depth(raster_depth, ridge_depth)

        A = (pCurvMax - pCurvMin) / (1 - 0)
        B = pCurvMin
        up_trench_depth = A * PCM_norm + B
        A = (pArcYMax - pArcYMin) / (1 - 0)
        B = pArcYMin
        arc_y = A * PCM_norm + B

        A = (pBulgeYMax - pBulgeYMin) / (1 - 0)
        B = pBulgeYMin
        GaussFactor2 = A * PCM_norm + B

        PCM_trench_y = feature_conversion_tools.PCM(0 * PARAM_AM_C_FFLEX, ridge_depth)
        PCM_oc_y = feature_conversion_tools.PCM(pProfileLength * PARAM_AM_C_FFLEX, ridge_depth)
        A = (1 - 0) / (PCM_trench_y - PCM_oc_y)
        B = 0 - A * PCM_oc_y
        PCM_up_norm = A * feature_conversion_tools.PCM(GaussMean1 * PARAM_AM_C_FFLEX, ridge_depth) + B

        A = (pCurvMax - pCurvMin) / (1 - 0)
        B = pCurvMin
        flex_arc_up = A * (PCM_norm * PCM_up_norm) + B

        arc_gauss_2y = 1 * GaussFactor2

        GaussFactor1 = -z_up_plate - (arc_gauss_2y + flex_arc_up) + arc_y
        sin_value = math.sin(lat_distance * (2 * math.pi) / PARAM_IOS_lambdaF)
        GaussFactor1 += PARAM_IOS_vF * sin_value

        exp_t_gauss_2N = (1 / (GaussSigma2 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((0 - GaussMean2) ** 2) / (2 * (GaussSigma2 ** 2))) / (1 / (GaussSigma2 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((GaussMean2 - GaussMean2) ** 2) / (2 * (GaussSigma2 ** 2)))
        exp_t_gauss_2Y = exp_t_gauss_2N * GaussFactor2
        exp_trench = (low_trench_depth - up_trench_depth - exp_t_gauss_2Y) - z_up_plate

        if distance < 1.5:
            exp_0 = (-1 / math.exp((0 + pExpAdd) ** pExpPower))
            A = (0 - (-1)) / (0 - exp_0)
            B = 0 - A * 0
            exp_z = A * (-1 / math.exp((distance + pExpAdd) ** pExpPower))
        else:
            exp_z = 0

        Gauss1 = (1 / (GaussSigma1 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((distance - GaussMean1) ** 2) / (2 * (GaussSigma1 ** 2))) / (1 / (GaussSigma1 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((GaussMean1 - GaussMean1) ** 2) / (2 * (GaussSigma1 ** 2)))
        Gauss2 = (1 / (GaussSigma2 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((distance - GaussMean2) ** 2) / (2 * (GaussSigma2 ** 2))) / (1 / (GaussSigma2 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((GaussMean2 - GaussMean2) ** 2) / (2 * (GaussSigma2 ** 2)))


        A = (1 - 0) / (PCM_trench_y - PCM_oc_y)
        B = 0 - A * PCM_oc_y
        PCM_N = A * feature_conversion_tools.PCM(distance * PARAM_AM_C_FFLEX, ridge_depth) + B

        z = (-exp_trench * exp_z) + (GaussFactor1 * Gauss1) + (GaussFactor2 * Gauss2) + (
                    up_trench_depth * PCM_N) + z_up_plate

        return z

    def trench_depth(self, raster_depth, ridge_depth):
        """trench depth, WITH Abyssal sediments (C. Verard linear regression on present day stats includes sediments)"""

        trench_depth = 1.763608593 * raster_depth + 2234.900592 + (
                    ridge_depth - (1.763608593 * ridge_depth + 2234.900592))

        return trench_depth