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

    def __init__(self, func, age_values):
        super().__init__()
        self.func = func
        self.age_values = age_values

    def process(self):
        try:
            for age in self.age_values:
                self.func(age=age)
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
        self.total_steps = 4  # Total steps in the process
        self.completed_steps = 0
        selected_items = self.age_listWidget.selectedItems()
        age_values = [float(item.text().split()[0]) for item in selected_items]
        functions = [
            data_preparation.aggregate_plate_polygons_new,
            data_preparation.aggregate_continent_polygons,
            #data_preparation.set_raster_name_coll,
            data_preparation.prepare_plate_model,
            data_preparation.check_shape_length
        ]
        self.start_threads(age_values, functions)

    def convert_features(self):
        """
        Main function to start feature conversion with threads and measure elapsed time.
        """
        self.progressBar.setValue(0)
        self.total_steps = 15  # Total steps in the process
        self.completed_steps = 0
        self.start_time = time.time()  # Track start time

        # Get selected ages
        selected_items = self.age_listWidget.selectedItems()
        age_values = [float(item.text().split()[0]) for item in selected_items]
        self.age_values = age_values  # Save for later use in write_elapsed_time

        if not age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        # Pre-thread processing
        for age in age_values:
            try:
                lines_selections.select_lines(age=age)
                self.update_progress_bar()
                rid_conversion.ridge_to_nodes(age=age)
                self.update_progress_bar()
                iso_conversion.isochron_to_nodes(age=age)
                self.update_progress_bar()
                raster_tools.generate_temporary_raster(age=age)
                self.update_progress_bar()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Pre-thread processing error for age {age}:\n{str(e)}")
                return
        functions = [
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
            hot_spot_conversion.hot_spot_to_nodes,
        ]

        # Start threads for the remaining functions
        self.start_threads(age_values, functions)

    def update_progress_bar(self):
        """
        Increment the progress bar by one step.
        """
        self.completed_steps += 1
        percentage = (self.completed_steps / self.total_steps) * 100
        self.progressBar.setValue(int(percentage))

    def start_threads(self, age_values, functions):
        """
        Start threads for feature conversion tasks.
        """
        QgsMessageLog.logMessage("Starting threads...", "Processing", Qgis.Info)  # Log the start of thread processing

        for func in functions:
            try:
                # Create a thread and worker instance
                thread = QThread()
                worker = ThreadedWorker(func, age_values)

                # Log worker creation
                QgsMessageLog.logMessage(f"Worker created for function: {func.__name__}", "Processing", Qgis.Info)
                QgsMessageLog.logMessage(f"Worker signals: {dir(worker)}", "Processing",
                                         Qgis.Info)  # Log available signals

                worker.moveToThread(thread)

                # Connect worker signals to appropriate slots
                worker.finished.connect(self.check_thread_completion)
                QgsMessageLog.logMessage(f"Connected 'finished' signal for {func.__name__}.", "Processing", Qgis.Info)

                worker.error.connect(self.thread_error)
                QgsMessageLog.logMessage(f"Connected 'error' signal for {func.__name__}.", "Processing", Qgis.Info)

                worker.progress.connect(self.update_progress_bar)
                QgsMessageLog.logMessage(f"Connected 'progress' signal for {func.__name__}.", "Processing", Qgis.Info)

                thread.started.connect(worker.process)
                QgsMessageLog.logMessage(f"Connected 'started' signal for {func.__name__}.", "Processing", Qgis.Info)

                # Keep track of threads and workers
                self.threads.append((thread, worker))

                # Start the thread
                thread.start()
                QgsMessageLog.logMessage(f"Thread started for function: {func.__name__}", "Processing", Qgis.Info)

            except Exception as e:
                # Log any errors during thread initialization
                QgsMessageLog.logMessage(
                    f"Error initializing thread for {func.__name__}: {str(e)}",
                    "Processing",
                    Qgis.Critical,
                )

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
        Clean up threads after processing.
        """
        for thread, worker in self.threads:
            worker.deleteLater()
            thread.quit()
            thread.wait()
            thread.deleteLater()
        self.threads = []

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