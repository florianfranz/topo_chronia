from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class SEDConversionTools:
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"

    def __init__(self):
            pass
    def abyssal_sediments(self, age, feature_abs_age):
        """
            Return abyssal sediment thickness according to the age of the feature relative to the age of the reconstruction.
            Abyssal Sediments are only a function of Floegel et al. work.
            """
        PARAM_ABYSS_f = 2.6
        PARAM_ABYSS_A = 0
        PARAM_ABYSS_B = 1
        if feature_abs_age == age or feature_abs_age < 0:
            return 0
        ref_slope = (self.floegelization(60) - self.floegelization(0)) / (60 - 0)
        x_slope = (self.floegelization(feature_abs_age) - self.floegelization(age)) / (feature_abs_age - age)
        c = x_slope * PARAM_ABYSS_f / ref_slope
        value = (PARAM_ABYSS_A + PARAM_ABYSS_B * (feature_abs_age - age)) * c
        return value

    def full_sediment_thickness(self, sed_t):
        """
            Get the full sediment thickness using Airy method.
            """
        ratio = (
                0.685049521505159
                - 0.000064943251967264 * sed_t
                + 0.000000000642559976389963 * (sed_t ** 2)
                + 0.000000000000552794242482484 * (sed_t ** 3)
                - 0.000000000000000169310158725139 * (sed_t ** 4)
                + 7.7202623515494E-20 * (sed_t ** 5)
                - 1.5609300540437E-23 * (sed_t ** 6)
                + 1.29798163854998E-27 * (sed_t ** 7)
                - 1.41779618223462E-32 * (sed_t ** 8)
                - 3.97804639891177E-36 * (sed_t ** 9)
                + 1.69317075125754E-40 * (sed_t ** 10)
        )
        value = sed_t * 1 / ratio
        return value

    def rho_sed(self, h_s):
        """
           Density of sediments as a function of sediment thickness,
           which is a derivative from Winterbourne et al. approach.
           """
        rho_sed = (
                1733.280042191
                + 0.10185377730746 * (h_s ** 1)
                - 0.00000754429699988986 * (h_s ** 2)
                + 0.000000000418963676022051 * (h_s ** 3)
                - 0.0000000000000185731858593553 * (h_s ** 4)
                + 6.79501168017416E-19 * (h_s ** 5)
                - 2.06288839013819E-23 * (h_s ** 6)
                + 5.04342695796056E-28 * (h_s ** 7)
                - 9.21488762443029E-33 * (h_s ** 8)
                + 1.09489366519341E-37 * (h_s ** 9)
                - 6.21135984518587E-43 * (h_s ** 10)
        )
        return rho_sed
    def floegelization(self, age):
        """
            Retrieve the sediment mass through time based on Floegel et al. 2000 sediment fluxes.
            Also in Hay et al. 2001 "Evolution of sediment fluxes and ocean salinity".
            Fit according to C.Verard.
            """
        # Polynomial fit [000 - 550]
        if age <= 550:
            return (
                    5855.85422221492
                    - 21.0099738908655 * (age ** 1)
                    + 0.540392148985822 * (age ** 2)
                    - 0.00975901696866692 * (age ** 3)
                    + 0.0000923837022411409 * (age ** 4)
                    - 0.000000511028015239932 * (age ** 5)
                    + 0.00000000174986423392087 * (age ** 6)
                    - 0.00000000000376700878679747 * (age ** 7)
                    + 0.00000000000000497144285314182 * (age ** 8)
                    - 3.68438142872613E-18 * (age ** 9)
                    + 1.17853655901538E-21 * (age ** 10)
            )
        else:
            # Linear Fit [550 - 777]
            return -3.283672651 * age + 2555.565311
