import random
import math

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class COLConversionTools:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"

    def __init__(self):
        pass
    def collision_profile(self, feature_age, distance, front_x_young, shift, ridge_depth, z_up_plate):
        pRand = random.Random()
        random_number = pRand.random()
        GaussMean1 = 1.167  # PARAM_CZ_SUM_mG1
        GaussSigma1 = 0.4  # PARAM_CZ_SUM_sG1
        GaussMean2Max = 0.5  # PARAM_CZ_SUM_mG2Max
        GaussMean2Min = 0  # PARAM_CZ_SUM_mG2Min
        GaussSigma2 = 0.2  # PARAM_CZ_SUM_sG2
        CurvatureFactor = 0.333  # PARAM_CZ_SUM_FTEMP

        PARAM_CZ_C1_mG1 = 15
        PARAM_CZ_C1_sG1 = 7
        PARAM_CZ_C1_fG1 = 1500
        PARAM_CZ_C1_mG2 = 0
        PARAM_CZ_C1_sG2 = 5
        PARAM_CZ_C1_fG2 = -2000
        PARAM_CZ_C1_FCURV = 0.333
        PARAM_CZ_C1_FPCM = 4000

        PARAM_CZ_C2_mG1 = 0
        PARAM_CZ_C2_sG1 = 1
        PARAM_CZ_C2_fG1 = 0
        PARAM_CZ_C2_mG2 = 0
        PARAM_CZ_C2_sG2 =1
        PARAM_CZ_C2_fG2 = 0
        PARAM_CZ_C2_FCURV = 1
        PARAM_CZ_C2_FPCM = -1500

        GaussFactor1 = feature_conversion_tools.composite(PARAM_CZ_C1_mG1,
                                                          PARAM_CZ_C1_sG1,
                                                          PARAM_CZ_C1_fG1,
                                                          PARAM_CZ_C1_mG2,
                                                          PARAM_CZ_C1_sG2,
                                                          PARAM_CZ_C1_fG2,
                                                          PARAM_CZ_C1_FCURV,
                                                          PARAM_CZ_C1_FPCM,
                                                          z_up_plate,
                                                          ridge_depth,
                                                          feature_age,
                                                          -15)

        GaussFactor1 = GaussFactor1 - (GaussFactor1 / 10) + random_number * ((GaussFactor1 / 10) * 2)

        GaussFactor2 = feature_conversion_tools.composite(PARAM_CZ_C2_mG1,
                                                          PARAM_CZ_C2_sG1,
                                                          PARAM_CZ_C2_fG1,
                                                          PARAM_CZ_C2_mG2,
                                                          PARAM_CZ_C2_sG2,
                                                          PARAM_CZ_C2_fG2,
                                                          PARAM_CZ_C2_FCURV,
                                                          PARAM_CZ_C2_FPCM,
                                                          240.38,
                                                          ridge_depth,
                                                          feature_age)
        PCM_min = feature_conversion_tools.PCM(0, ridge_depth)
        PCM_max = feature_conversion_tools.PCM(4.567 * 1000, ridge_depth)
        A = (1 - 0) / (PCM_min - PCM_max)
        B = 0 - A * PCM_max
        PCM_norm = A * feature_conversion_tools.PCM(CurvatureFactor * abs(feature_age - 0), ridge_depth) + B

        GaussMeanPeak = (GaussMean1 + shift) - front_x_young
        GaussMaxPeak = (1 / (GaussSigma1 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((GaussMeanPeak - GaussMeanPeak) ** 2) / (2 * (GaussSigma1 ** 2)))

        GaussMeanBasin = (GaussMean2Min - GaussMean2Max) * PCM_norm + GaussMean2Max
        GaussMaxBasin = (1 / (GaussSigma2 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((GaussMeanBasin - GaussMeanBasin) ** 2) / (2 * (GaussSigma2 ** 2)))

        Gauss1Norm = (1 / (GaussSigma1 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((distance - GaussMeanPeak) ** 2) / (2 * (GaussSigma1 ** 2))) / GaussMaxPeak
        Gauss2Norm = (1 / (GaussSigma2 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((distance - GaussMeanBasin) ** 2) / (2 * (GaussSigma2 ** 2))) / GaussMaxBasin

        z = (Gauss1Norm * GaussFactor1) + (Gauss2Norm * GaussFactor2) + z_up_plate

        return z


    def collision_profile_shifting(self, feature_age, front_x_young, profile_length, ridge_depth):
        front_x_old = - profile_length / 2
        temporal_factor = 1 / 3

        PCM_shift = feature_conversion_tools.PCM(feature_age * temporal_factor, ridge_depth)

        PCM_min = feature_conversion_tools.PCM(0, ridge_depth)
        PCM_max = feature_conversion_tools.PCM(4.567 * 1000, ridge_depth)
        A = (1 - 0) / (PCM_min - PCM_max)
        B = 0 - A * PCM_max
        PCM_shift_norm = A * PCM_shift + B

        shift = (front_x_young - front_x_old) * PCM_shift_norm + front_x_old

        return shift