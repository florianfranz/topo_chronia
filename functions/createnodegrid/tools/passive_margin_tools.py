from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

from .sediments_tools import SEDConversionTools
sed_tools = SEDConversionTools()

class PMConversionTools:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"

    def __init__(self):
        pass

    def passive_margin_profile_clean(self,distance, feature_age, raster_depth, ridge_depth, wedge_y, wedge_x, crest_y,
                                     crest_x, continent_y):
        if crest_x == 0:
            crest_x = 0.1
        COB = 0
        continent_x = 5.5
        if distance <= wedge_x:  # AFTER WEDGE
            z = raster_depth
            return z
        elif distance > wedge_x and distance < crest_x:  # BETWEEN CREST AND WEDGE
            if crest_x < COB:  # crest is positioned after COB e.g. in the oceans = old PM
                sed_thick = self.calculate_sediment_thickness(distance, raster_depth, wedge_x, wedge_y, crest_x, crest_y)
                z = raster_depth + sed_thick
                if z > crest_y:
                    z = crest_y
                return z
            elif crest_x > COB:  # crest is positioned before COB e.g. in the continent = young PM
                if distance >= COB:
                    if crest_x - COB == 0:
                        A = 0
                    else:
                        A = (crest_y - (raster_depth + wedge_y)) / (crest_x - COB)
                    B = (raster_depth + wedge_y) - A * COB
                    if (A * distance + B) > crest_y:
                        z = crest_y
                    else:
                        z = A * distance + B
                    return z
                else:
                    sed_thick = self.calculate_sediment_thickness(distance, raster_depth, wedge_x, wedge_y, crest_x, crest_y)
                    z = raster_depth + sed_thick
                    if z > crest_y:
                        z = crest_y
                    return z
        elif distance >= crest_x and distance <= continent_x:  # BETWEEN CREST AND CONTINENT END
            flex_age = 8
            PCM_dist = feature_conversion_tools.PCM((flex_age * distance + feature_age), ridge_depth)
            PCM_crest_x = feature_conversion_tools.PCM((flex_age * crest_x + feature_age), ridge_depth)
            PCM_cont_x = feature_conversion_tools.PCM((flex_age * continent_x + feature_age), ridge_depth)
            A = (crest_y - continent_y) / (PCM_crest_x - PCM_cont_x)
            B = continent_y - A * PCM_cont_x
            z = A * PCM_dist + B
            return z
        elif distance > continent_x:  # AFTER CONTINENT END
            z = continent_y
            return z

    def calculate_sediment_thickness(self,distance, raster_depth, wedge_x, wedge_y, crest_x, crest_y):
        COB = 0
        if distance < 0:
            if distance < wedge_x:
                sediment_thickness = 0
            else:
                x = 1 / -wedge_x * distance + 1
                sediment_thickness = (
                                             0.003071916714
                                             - 0.2311114699 * (x ** 1)
                                             + 4.976127975 * (x ** 2)
                                             - 24.42160092 * (x ** 3)
                                             + 58.5398904 * (x ** 4)
                                             - 63.4336469 * (x ** 5)
                                             + 25.567269 * (x ** 6)
                                     ) * (wedge_y)
        elif 0 <= distance < crest_x:
            A = (crest_y - (raster_depth + wedge_y)) / (crest_x - COB)
            B = (raster_depth + wedge_y) - A * COB
            sediment_thickness = A * distance + B
        else:
            sediment_thickness = "_"
        return sediment_thickness

    def wedge_y_pm_new(self, feature_age):
        age_max = 187
        wedge_y_max = -5602.732
        wedge_y = -(feature_age * wedge_y_max) / age_max
        return wedge_y

    def wedge_x_pm_new(self,feature_age):
        age_max = 187
        wedge_x_max = -12.5
        wedge_x = (feature_age * wedge_x_max) / age_max
        return wedge_x

    def wedge_y(self,age, feature_age, feature_abs_age, ridge_depth, remove_abys_sed = False):
        age_ref = 225
        ref_0 = sed_tools.floegelization(0)
        ref_age_ref = sed_tools.floegelization(age_ref)
        ref_abs_age = sed_tools.floegelization(feature_abs_age)
        ref_age_recon = sed_tools.floegelization(age)
        thick_ref = - feature_conversion_tools.PCM(age_ref, ridge_depth)
        if remove_abys_sed is False:
            a = 2
        else:
            abys_sed = sed_tools.abyssal_sediments(age, feature_abs_age)
            thick_ref = thick_ref - abys_sed
        axe_y_max = thick_ref * (6000 - ref_age_ref) / (ref_0 - ref_age_ref)
        axe_y_min = thick_ref * (0 - ref_age_ref) / (ref_0 - ref_age_ref)

        val = (( thick_ref - (((axe_y_max - axe_y_min) / (6000 - 0)) * ref_abs_age + axe_y_min)) -
               (thick_ref - (((axe_y_max - axe_y_min) / (6000 - 0)) * (ref_age_recon + axe_y_min))))
        scaling_ratio = self.wedge_scaling(feature_age, ridge_depth)
        val = val * scaling_ratio

        return val

    def wedge_x(self, age, feature_age, feature_abs_age, ridge_depth):
        age_ref = 225
        ref_0 = sed_tools.floegelization(0)
        ref_age_ref = sed_tools.floegelization(age_ref)
        flog_abs_age = sed_tools.floegelization(feature_abs_age)
        flog_age_recon = sed_tools.floegelization(age)
        length_ref = 8 # PARAM_PM_WedgeXMax default value

        axe_x_max = length_ref * (6000 - ref_age_ref) / (ref_0 - ref_age_ref)
        axe_x_min = length_ref * (0 - ref_age_ref) / (ref_0 - ref_age_ref)

        wedge_x = (length_ref -((( axe_x_max - axe_x_min) / (6000 - 0)) * (flog_abs_age) + axe_x_min)) - (length_ref -((( axe_x_max - axe_x_min) / (6000 - 0)) * (flog_age_recon) + axe_x_min))

        scaling_ratio = self.wedge_scaling(feature_age, ridge_depth)
        wedge_x = wedge_x * scaling_ratio

        return float(wedge_x)

    def wedge_scaling(self, feature_age, ridge_depth):
        age_ref = 225
        sum_ref = 0
        sum_age = 0
        PARAM_PM_C2_mG1 = 5
        PARAM_PM_C2_sG1 = 3
        PARAM_PM_C2_fG1 = 1200
        PARAM_PM_C2_mG2 = 50
        PARAM_PM_C2_sG2 = 111
        PARAM_PM_C2_fG2 = 0
        PARAM_PM_C2_FCURV =  1
        PARAM_PM_C2_FPCM = 500
        for i in range(age_ref):
            sum_ref = sum_ref + feature_conversion_tools.composite(PARAM_PM_C2_mG1,PARAM_PM_C2_sG1,
                                     PARAM_PM_C2_fG1, PARAM_PM_C2_mG2,
                                    PARAM_PM_C2_sG2, PARAM_PM_C2_fG2,
                                     PARAM_PM_C2_FCURV, PARAM_PM_C2_FPCM,
                                    240.38, ridge_depth, i)

        for j in range(int(feature_age)):
            sum_age = sum_age + feature_conversion_tools.composite(PARAM_PM_C2_mG1,PARAM_PM_C2_sG1,
                                     PARAM_PM_C2_fG1, PARAM_PM_C2_mG2,
                                    PARAM_PM_C2_sG2, PARAM_PM_C2_fG2,
                                     PARAM_PM_C2_FCURV, PARAM_PM_C2_FPCM,
                                    240.38, ridge_depth, j)

        ratio = sum_age / sum_ref
        return ratio

    def crest_x_passive_margin(self, feature_age):
        crest_x_max = 2
        crest_x_min = 0
        age_max = 225
        age_min = 0

        A = (crest_x_min - crest_x_max) / (age_max - age_min)
        B = crest_x_max - A * age_min

        crest_x = A * feature_age + B

        return crest_x

    def crest_y_passive_margin(self, age, feature_age):
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        PARAM_PM_C1_mG1 = 12
        PARAM_PM_C1_sG1 = 8
        PARAM_PM_C1_fG1 = 2000
        PARAM_PM_C1_mG2 = 50
        PARAM_PM_C1_sG2 = 111
        PARAM_PM_C1_fG2 = -780
        PARAM_PM_C1_FCURV = 1
        PARAM_PM_C1_FPCM = 500
        PARAM_GENERAL_CONTINENTZ = 240.38
        crest_height = float(feature_conversion_tools.composite(PARAM_PM_C1_mG1,
                                      PARAM_PM_C1_sG1,
                                      PARAM_PM_C1_fG1,
                                      PARAM_PM_C1_mG2,
                                      PARAM_PM_C1_sG2,
                                      PARAM_PM_C1_fG2,
                                      PARAM_PM_C1_FCURV,
                                      PARAM_PM_C1_FPCM,
                                      PARAM_GENERAL_CONTINENTZ,
                                      ridge_depth,
                                      feature_age))
        return crest_height
