from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import (FeatureConversionTools)
feature_conversion_tools = FeatureConversionTools()

class RIBConversionTools:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"

    def __init__(self):
        pass

    def rift_profile(self, distance, crest_z, through_y, feature_age, age):
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        if distance < 0:
            A = (crest_z - through_y) / (0 - (-1.5))
            B = crest_z - A * 0
            z = A * distance + B
        else:
            flex_age = 8  # PARAM_PM_C1_FFLEX default value
            continent_x = 5.5
            continent_y = 240.38
            crest_x = 0

            PCM_dist = feature_conversion_tools.PCM((flex_age * distance + feature_age), ridge_depth)
            PCM_crest_x = feature_conversion_tools.PCM((flex_age * crest_x + feature_age), ridge_depth)
            PCM_cont_x = feature_conversion_tools.PCM((flex_age * continent_x + feature_age), ridge_depth)

            A = (crest_z - continent_y) / (PCM_crest_x - PCM_cont_x)
            B = continent_y - A * PCM_cont_x
            z = A * PCM_dist + B

        return z

    def crest_y_rift(self, age, feature_age):
        PARAM_RB_C1_mG1 = 12
        PARAM_RB_C1_sG1 = 8
        PARAM_RB_C1_fG1 = 2000
        PARAM_RB_C1_mG2 = 50
        PARAM_RB_C1_sG2 = 111
        PARAM_RB_C1_fG2 = -300
        PARAM_RB_C1_FCURV = 1
        PARAM_RB_C1_FPCM = 500

        ridge_depth = feature_conversion_tools.get_ridge_depth(age)

        crest_height_rift = feature_conversion_tools.composite(PARAM_RB_C1_mG1,
                                      PARAM_RB_C1_sG1,
                                      PARAM_RB_C1_fG1,
                                      PARAM_RB_C1_mG2,
                                      PARAM_RB_C1_sG2,
                                      PARAM_RB_C1_fG2,
                                      PARAM_RB_C1_FCURV,
                                      PARAM_RB_C1_FPCM,
                                      240.28,
                                      ridge_depth,
                                      feature_age)
        return crest_height_rift

    def through_y_rift(self, age, feature_age):
        PARAM_RB_C2_mG1 = 10
        PARAM_RB_C2_sG1 = 5
        PARAM_RB_C2_fG1 = -1000
        PARAM_RB_C2_mG2 = 10
        PARAM_RB_C2_sG2 = 150
        PARAM_RB_C2_fG2 = -500
        PARAM_RB_C2_FCURV = 1
        PARAM_RB_C2_FPCM = -500

        ridge_depth = feature_conversion_tools.get_ridge_depth(age)

        through_y_rift = feature_conversion_tools.composite(PARAM_RB_C2_mG1,
                                        PARAM_RB_C2_sG1,
                                        PARAM_RB_C2_fG1,
                                        PARAM_RB_C2_mG2,
                                        PARAM_RB_C2_sG2,
                                        PARAM_RB_C2_fG2,
                                        PARAM_RB_C2_FCURV,
                                        PARAM_RB_C2_FPCM,
                                        240.38,
                                        ridge_depth,
                                        feature_age)
        return through_y_rift