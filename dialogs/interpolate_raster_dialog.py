import os
import re
import time
import platform
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, QThreadPool, QRunnable, pyqtSignal

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



class WorkerSignals(QObject):
    """Signal-emitting object for the threaded worker."""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal()


class ThreadedWorker(QRunnable):
    """Worker that runs a function in a separate thread."""

    def __init__(self, func, age, progress_enabled=True):
        super().__init__()
        self.func = func
        self.age = age
        self.progress_enabled = progress_enabled
        self.signals = WorkerSignals()


    def run(self):
        try:
            self.func(age=self.age)
            if self.progress_enabled:
                self.signals.progress.emit()
        except Exception as e:
            self.signals.error.emit(f"{self.func.__name__}: {e}")
        finally:
            self.signals.finished.emit()

# Create the dialog class using the generated class
class InterpolateRasterDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self):
        """Constructor.
        Connects buttons to respective functions.
        """
        super(InterpolateRasterDialog, self).__init__()
        self.workers = None
        self.threads = []
        self.errors = []
        self.setupUi(self)
        self.nodes_age_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.Action_CreateNodesAgeList_pushButton.clicked.connect(self.create_available_age_list)
        self.Action_InterpolateRaster_pushButton.clicked.connect(self.interpolate_raster)
        self.Action_CorrectWaterLoad_pushButton.clicked.connect(self.correct_water_load)
        self.Action_FinalRaster_pushButton.clicked.connect(self.interpolate_final_raster)
        self.Action_ProcessEverything_pushButton.clicked.connect(self.process_everything)


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
        self.age_values = [float(item.text().split()[0]) for item in selected_items]

        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        self.remaining_threads = len(self.age_values)
        self.current_age_index = 0  # Initialize current_age_index here

        self.start_time = time.time()

        # First set of threads for create_final_nodes
        for age in self.age_values:
            worker = ThreadedWorker(raster_tools.generate_raster_all_in_one, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)

    def thread_finished(self):
        """Check if all threads are done before moving to the next age."""
        self.remaining_threads -= 1
        if self.remaining_threads == 0:
            self.current_age_index += 1
            self.process_next_age()

    def thread_error(self, error_message):
        """Handle thread errors."""
        QgsMessageLog.logMessage(f"Thread error: {error_message}", "Processing", Qgis.Critical)
        self.errors.append(error_message)

    def process_next_age(self):
        """Process the next age, ensuring completion before moving to the next."""
        if self.current_age_index >= len(self.age_values):
            self.write_elapsed_time()
            return

        age = self.age_values[self.current_age_index]
        QgsMessageLog.logMessage(f"Processing age {age}", "Processing", Qgis.Info)
        self.run_initial_processing(age)
        self.start_threads(age)

    def write_elapsed_time(self):
        """Write elapsed time and log errors if any."""
        system_name = platform.system()
        if system_name in ["Darwin", "Linux"]:
            file_path = os.path.expanduser("~/Desktop/time.txt")
            errors_path = os.path.expanduser("~/Desktop/errors.log")
        else:
            file_path = "time.txt"
            errors_path = "errors.log"
        elapsed_time = time.time() - self.start_time
        with open(file_path, "a") as file:
            for age in self.age_values:
                file.write(f"Age {age} - Elapsed time: {elapsed_time:.2f} seconds\n")

        if self.errors:
            with open(errors_path, "a") as err_file:
                err_file.write("\n".join(self.errors) + "\n")
            QgsMessageLog.logMessage("Errors occurred during processing. See errors.log", "Processing", Qgis.Warning)

    def correct_water_load(self):
        """
        Calculates oceanic volume (volume below z=0m) and compare it to the present
        day reference volume. Calculates the necessary sea-level rise/decrease needed
        to reach full reference volume. Take into consideration subsidence after water
        load is added.
        """
        selected_items = self.nodes_age_listWidget.selectedItems()
        self.age_values = [float(item.text().split()[0]) for item in selected_items]

        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        self.remaining_threads = len(self.age_values)
        self.current_age_index = 0  # Initialize current_age_index here

        self.start_time = time.time()

        # First set of threads for create_final_nodes
        for age in self.age_values:
            worker = ThreadedWorker(sea_level_tools.correct_water_load_newest, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)

    def interpolate_final_raster(self):
        """
        Performs the final raster interpolation using the water load corrected
        elevation values.
        """
        output_folder_path = base_tools.get_layer_path("Output Folder")
        output_file_path = os.path.join(output_folder_path, "water_load_correction_summary_f.txt")
        selected_items = self.nodes_age_listWidget.selectedItems()
        self.age_values = [float(item.text().split()[0]) for item in selected_items]

        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        self.remaining_threads = len(self.age_values)
        self.current_age_index = 0  # Initialize current_age_index here

        self.start_time = time.time()

        for age in self.age_values:
            worker = ThreadedWorker(raster_tools.perform_final_raster_interpolation, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)

            while QThreadPool.globalInstance().activeThreadCount() > 0:
                QApplication.processEvents()

            z_full_volume, area_full_volume, initial_volume, initial_area = sea_level_tools.adjust_sea_level(age,
                                                                                                             corrected=1)
            with open(output_file_path, 'a') as file:
                file.write(
                    f"For age {age}, after correction, full volume is reached by changing the sea-level by {z_full_volume}m\n")

    def process_everything(self):
        output_folder_path = base_tools.get_layer_path("Output Folder")
        output_file_path = os.path.join(output_folder_path, "water_load_correction_summary_f.txt")
        self.completed_steps = 0
        selected_items = self.nodes_age_listWidget.selectedItems()
        self.age_values = [float(item.text().split()[0]) for item in selected_items]
        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        self.remaining_threads = len(self.age_values)
        self.current_age_index = 0  # Initialize current_age_index here

        self.start_time = time.time()

        # First set of threads for create_final_nodes
        for age in self.age_values:
            worker = ThreadedWorker(raster_tools.generate_raster_all_in_one, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)
            while QThreadPool.globalInstance().activeThreadCount() > 0:
                QApplication.processEvents()

        self.start_time = time.time()

        # First set of threads for create_final_nodes
        for age in self.age_values:
            worker = ThreadedWorker(sea_level_tools.correct_water_load_newest, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)
            
            while QThreadPool.globalInstance().activeThreadCount() > 0:
                QApplication.processEvents()

        for age in self.age_values:
            worker = ThreadedWorker(raster_tools.perform_final_raster_interpolation, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)

            while QThreadPool.globalInstance().activeThreadCount() > 0:
                QApplication.processEvents()

            z_full_volume, area_full_volume, initial_volume, initial_area = sea_level_tools.adjust_sea_level(age,
                                                                                                             corrected=1)
            with open(output_file_path, 'a') as file:
                file.write(
                    f"For age {age}, after correction, full volume is reached by changing the sea-level by {z_full_volume}m\n")
