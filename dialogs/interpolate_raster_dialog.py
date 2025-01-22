import os
import re
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer, edit, QgsRasterLayer, QgsProject

from ..functions.base_tools import BaseTools
base_tools = BaseTools()

from ..functions.interpolatetoraster.tools.sea_level_tools import SeaLevel
sea_level_tools = SeaLevel()

from ..functions.interpolatetoraster.tools.rasters_tools import RasterTools
raster_tools = RasterTools()
# Load the .ui file and generate the corresponding class
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'interpolate_raster_dialog.ui'))

# Create the dialog class using the generated class
class InterpolateRasterDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self):
        """Constructor.
        Connects buttons to respective functions.
        """
        super(InterpolateRasterDialog, self).__init__()
        self.setupUi(self)
        self.nodes_age_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.Action_CreateNodesAgeList_pushButton.clicked.connect(self.create_available_age_list)
        self.Action_InterpolateRaster_pushButton.clicked.connect(self.interpolate_raster)
        self.Action_CorrectWaterLoad_pushButton.clicked.connect(self.correct_water_load)
        self.Action_FinalRaster_pushButton.clicked.connect(self.interpolate_final_raster)

    def create_available_age_list(self):
        """
        Creates list of available ages for interpolation based on all nodes layer in the
        output directory. The available ages are displayed with their respective
        chronostratigraphic names.
        """
        self.nodes_age_listWidget.clear()
        output_folder_path = base_tools.get_layer_path("Output Folder")
        pattern = r'all_nodes_(\d+)\.geojson'

        # Define ages list
        ages = []
        for file in os.listdir(output_folder_path):
            match = re.match(pattern, file)
            if match:
                # Extract the age and add it to the list
                age = int(match.group(1))
                ages.append(age)
        ages.sort()

        for age_value in ages:
            pStrAge = f"{age_value} Ma - [ {base_tools.get_relative_age(age_value)} ]"
            self.nodes_age_listWidget.addItem(pStrAge)

        QgsMessageLog.logMessage(f"ListWidget Items: {self.nodes_age_listWidget.count()}", "Interpolate Raster", Qgis.Info)

    def interpolate_raster(self):
        """
        Interpolates a raster using the QGIS TIN method. Interpolation is done using
        a World Cylindrical Equal Area (WCEA) to avoid unnecessary added proparation
        of error that would arise if we were to convert an EPSG:4326 raster into a WCEA
        projection.
        """
        selected_items = self.nodes_age_listWidget.selectedItems()
        age_values = [float(item.text().split()[0]) for item in selected_items]

        for age in age_values:
            raster_tools.perform_raster_interpolation_wcea(age)

    def correct_water_load(self):
        """
        Calculates oceanic volume (volume below z=0m) and compare it to the present
        day reference volume. Calculates the necessary sea-level rise/decrease needed
        to reach full reference volume. Take into consideration subsidence after water
        load is added.
        """
        selected_items = self.nodes_age_listWidget.selectedItems()
        age_values = [float(item.text().split()[0]) for item in selected_items]
        for age in age_values:
            sea_level_tools.correct_water_load_TM_simple(age)

    def interpolate_final_raster(self):
        """
        Performs the final raster interpolation using the water load corrected
        elevation values.
        """
        selected_items = self.nodes_age_listWidget.selectedItems()
        age_values = [float(item.text().split()[0]) for item in selected_items]
        for age in age_values:
            raster_tools.perform_final_raster_interpolation(age)