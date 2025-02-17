import os
import time
from qgis.PyQt import uic,QtWidgets
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer, edit
from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot, QVariant, QThread

from ..functions.createnodegrid.data_preparation import DataPreparation
data_preparation = DataPreparation()

from ..functions.base_tools import BaseTools
base_tools = BaseTools()

from ..functions.createnodegrid.tools.rasters import PreRasterTools
raster_tools = PreRasterTools()
from ..functions.createnodegrid.conversions.hot_spot import HOTConversion
hot_spot_conversion = HOTConversion()
from ..functions.createnodegrid.conversions.ridge import RIDConversion
rid_conversion = RIDConversion()
from ..functions.createnodegrid.conversions.isochron import ISOConversion
iso_conversion = ISOConversion()
from ..functions.createnodegrid.conversions.lower_subduction import LWSConversion
lws_conversion = LWSConversion()
from ..functions.createnodegrid.conversions.abandoned_arc import ABAConversion
aba_conversion = ABAConversion()
from ..functions.createnodegrid.conversions.passive_margin_wedge import PMWConversion
pmw_conversion = PMWConversion()
from ..functions.createnodegrid.conversions.continent import CTNConversion
ctn_conversion = CTNConversion()
from ..functions.createnodegrid.conversions.craton import CRAConversion
cra_conversion = CRAConversion()
from ..functions.createnodegrid.conversions.other_margin import OTMConversion
otm_conversion = OTMConversion()
from ..functions.createnodegrid.conversions.passive_margin_continent import PMCConversion
pmc_conversion = PMCConversion()
from ..functions.createnodegrid.conversions.rift import RIBConversion
rib_conversion = RIBConversion()
from ..functions.createnodegrid.conversions.upper_subduction import UPSConversion
ups_conversion = UPSConversion()
from ..functions.createnodegrid.conversions.collision import COLConversion
col_conversion = COLConversion()
from ..functions.createnodegrid.conversions.selections import LinesSelections
lines_selections = LinesSelections()
from ..functions.createnodegrid.tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'create_node_grid_dialog.ui'))


class ThreadedWorker(QObject):
    finished = pyqtSignal()  # Signal emitted when the worker finishes
    progress = pyqtSignal()  # Signal emitted with function name upon progress
    error = pyqtSignal(str)  # Signal emitted when an error occurs

    def __init__(self, func, age):
        super().__init__()
        self.func = func
        self.age = age

    def process(self):
        try:
            self.func(age=self.age)
            self.progress.emit()  # Emit progress signal
        except Exception as e:
            self.error.emit(f"{self.func.__name__}: {e}")
        else:
            self.finished.emit()


class CreateNodeGridDialog(QtWidgets.QDialog, FORM_CLASS):
    output_folder_path = base_tools.get_layer_path("Output Folder")
    def __init__(self, PM_age_list, PP_age_list, CP_age_list, input_fc):
        """Constructor.
        Sets up workers, threads, ages, progress bar and connects buttons
        with respective functions.
        """
        super(CreateNodeGridDialog, self).__init__()
        self.setupUi(self)
        self.worker = None
        self.threads = []
        self.age_listWidget.clear()
        self.age_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.PM_age_list = PM_age_list
        self.PP_age_list = PP_age_list
        self.CP_age_list = CP_age_list
        self.input_fc = input_fc
        self.progressBar.setValue(0)
        self.Action_CreateAllAgeList_pushButton.clicked.connect(self.create_all_age_list)
        self.Action_PrepareData_pushButton.clicked.connect(self.prepare_data)
        self.Action_FeatureConversion_pushButton.clicked.connect(self.convert_features)
        self.Action_CleanNodes_pushButton.clicked.connect(self.clean_nodes)
        self.Action_MergeNodes_pushButton.clicked.connect(self.merge_all_nodes)

    def create_all_age_list(self):
        """
        Creates the selectable ages that are common to the plate model, plate polygons
        and continents polygons. Displays ages with their respective chronostratigraphic
        age names.
        """
        try:
            self.age_listWidget.clear()
            if self.PM_age_list is None or self.PP_age_list is None or self.CP_age_list is None:
                file_path = "pStrAge_values.txt"
                if os.path.exists(file_path):
                    with open(file_path, "r") as file:
                        all_age_list = [float(line.split()[0]) for line in file]
                else:
                    return
            else:
                pm_set = set(self.PM_age_list)
                pp_set = set(self.PP_age_list)
                cp_set = set(self.CP_age_list)
                all_age_list = sorted(list(pm_set.intersection(pp_set, cp_set)))
            if not all_age_list:
                return
            with open("pStrAge_values.txt", "w") as file:
                for i, age_value in enumerate(all_age_list, start=1):
                    pStrAge = f"{age_value} Ma - [ {base_tools.get_relative_age(age_value)} ]"
                    self.age_listWidget.addItem(pStrAge)
                    file.write(pStrAge + "\n")
            return all_age_list
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating all age list: {str(e)}", "Create Node Grid", Qgis.Critical)
            raise

    def prepare_data(self):
        """
        Prepares data before features conversion.
        """
        self.progressBar.setValue(0)
        self.total_steps = 2  # Total steps in the process
        self.completed_steps = 0
        selected_items = self.age_listWidget.selectedItems()
        age_values = [float(item.text().split()[0]) for item in selected_items]
        for age in age_values:
            data_preparation.aggregate_plate_polygons_new(age)
            data_preparation.aggregate_continent_polygons(age)


    def convert_features(self):
        """
        Start feature conversion for the first selected age and ensure sequential processing.
        """
        self.progressBar.setValue(0)
        self.total_steps = 15
        self.completed_steps = 0
        self.start_time = time.time()

        # Get selected ages
        selected_items = self.age_listWidget.selectedItems()
        self.age_values = [float(item.text().split()[0]) for item in selected_items]
        self.total_steps = 15 * len(self.age_values) # 15 steps per reconstruction

        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        self.current_age_index = 0  # Track which age we're processing
        self.process_next_age()  # Start the first age

    def process_next_age(self):
        """
        Process the next age in the list after the previous one completes.
        """
        if self.current_age_index >= len(self.age_values):
            QgsMessageLog.logMessage("All ages processed.", "Processing", Qgis.Info)
            self.write_elapsed_time()  # Log final time
            return

        age = self.age_values[self.current_age_index]
        self.threads = []  # Reset threads for this age
        self.remaining_threads = 0  # Track active threads

        QgsMessageLog.logMessage(f"Starting processing for age {age}", "Processing", Qgis.Info)

        # Run initial processing functions
        """lines_selections.select_lines(age=age)
        self.update_progress_bar()"""
        rid_conversion.ridge_to_nodes(age=age)
        self.update_progress_bar()
        iso_conversion.isochron_to_nodes(age=age)
        self.update_progress_bar()
        raster_tools.generate_temporary_raster_plate_by_plate(age=age)
        self.update_progress_bar()

        """functions = [
            lws_conversion.lower_subduction_to_nodes,
            aba_conversion.abandoned_arc_to_nodes,
            pmw_conversion.passive_margin_wedge_to_nodes,
            ctn_conversion.continent_geode_to_nodes,
            cra_conversion.craton_to_nodes,
            otm_conversion.other_margin_to_nodes,
            pmc_conversion.passive_margin_continent_to_nodes,
            rib_conversion.rift_to_nodes,
            ups_conversion.upper_subduction_to_nodes,
            col_conversion.collision_to_nodes,
            hot_spot_conversion.hot_spot_to_nodes
        ]

        self.start_threads(age, functions)"""

    def update_progress_bar(self):
        """
        Increment the progress bar by one step.
        """
        self.completed_steps += 1
        percentage = (self.completed_steps / self.total_steps) * 100
        self.progressBar.setValue(int(percentage))

    def start_threads(self, age, functions):
        """
        Start threads for feature conversion tasks and ensure they all complete before processing the next age.
        """
        QgsMessageLog.logMessage(f"Starting threads for age {age}...", "Processing", Qgis.Info)

        self.remaining_threads = len(functions)  # Track active threads

        for func in functions:
            try:
                thread = QThread()
                worker = ThreadedWorker(func, age)

                worker.moveToThread(thread)

                # Connect signals
                worker.finished.connect(self.thread_finished)
                worker.error.connect(self.thread_error)
                worker.progress.connect(self.update_progress_bar)
                thread.started.connect(worker.process)

                self.threads.append((thread, worker))
                thread.start()

            except Exception as e:
                QgsMessageLog.logMessage(f"Error initializing thread for {func.__name__}: {str(e)}", "Processing",
                                         Qgis.Critical)

    def thread_finished(self):
        """
        Called when a thread finishes. If all threads are done, start the next age.
        """
        self.remaining_threads -= 1  # Reduce active thread count

        if self.remaining_threads == 0:  # If all threads for this age are done
            QgsMessageLog.logMessage(f"All threads finished for age {self.age_values[self.current_age_index]}.",
                                     "Processing", Qgis.Info)

            #CLEAN UP THREADS BEFORE MOVING TO THE NEXT AGE
            self.cleanup_threads()

            # Move to the next age
            self.current_age_index += 1
            self.process_next_age()  # Start processing next age

    def check_thread_completion(self):
        """
        Check if all threads are completed.
        """
        if all(not thread.isRunning() for thread, _ in self.threads):
            self.cleanup_threads()
            self.write_elapsed_time()

    def log_thread_completion(self, func_name):
        """
        Log and write to file when a thread completes.
        """
        elapsed_time = time.time() - self.start_time
        try:
            # Write the completion time for the specific function
            with open("time.txt", "a") as file:
                file.write(f"Function {func_name} completed. Elapsed time: {elapsed_time:.2f} seconds\n")

            # Log progress in the QGIS Message Log
            QgsMessageLog.logMessage(
                f"Function {func_name} completed successfully. Elapsed time: {elapsed_time:.2f} seconds.",
                "Processing",
                Qgis.Info,
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error logging progress for {func_name}: {str(e)}",
                "Processing",
                Qgis.Critical,
            )

    def write_elapsed_time(self):
        """
        Logs and displays the total elapsed time.
        """
        try:
            end_time = time.time()
            elapsed_time = end_time - self.start_time

            # Write the total time to the file
            with open("time.txt", "a") as file:
                for age in self.age_values:
                    file.write(f"With threads and for age {age}, elapsed time is {elapsed_time:.2f} seconds\n")

            # Log success in the QGIS Message Log
            QgsMessageLog.logMessage(
                f"Processing completed successfully. Total elapsed time: {elapsed_time:.2f} seconds.",
                "Processing",
                Qgis.Info,
            )

            # Show success message box
            QtWidgets.QMessageBox.information(
                self,
                "Processing Complete",
                f"All processing completed successfully.\nTotal elapsed time: {elapsed_time:.2f} seconds.",
                QtWidgets.QMessageBox.Ok,
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error writing elapsed time or showing completion message: {str(e)}",
                "Processing",
                Qgis.Critical,
            )
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while writing elapsed time or displaying the message:\n{str(e)}",
            )

    def thread_error(self, error_message):
        """
        Handle thread errors and log them.
        """
        QgsMessageLog.logMessage(f"Thread error: {error_message}", "Processing", Qgis.Critical)
        QtWidgets.QMessageBox.critical(self, "Error", f"Thread error:\n{error_message}")
        self.cleanup_threads()

    def cleanup_threads(self):
        """
        Properly clean up all threads before starting a new age.
        """
        for thread, worker in self.threads:
            worker.deleteLater()  # Delete worker object
            thread.quit()  # Ask the thread to quit
            thread.wait()  # Wait for thread to fully stop
            thread.deleteLater()  # Delete thread object

        self.threads = []  # Reset thread list

    def merge_all_nodes(self):
        """
        Merges all nodes from the various settings into a single all nodes
        layer.
        """
        selected_items = self.age_listWidget.selectedItems()
        age_values = [float(item.text().split()[0]) for item in selected_items]
        for age in age_values:
           feature_conversion_tools.create_final_nodes(age)

    def clean_nodes(self):
        """
        Cleans the all nodes layer to remove nodes from different settings to
        remove incoherent (contradicting) nodes when interpolating.
        """
        selected_items = self.age_listWidget.selectedItems()
        age_values = [float(item.text().split()[0]) for item in selected_items]
        for age in age_values:
            feature_conversion_tools.clean_nodes(age)