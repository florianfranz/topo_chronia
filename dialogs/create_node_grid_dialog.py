import os
import time
import platform
from qgis.PyQt import uic,QtWidgets
from PyQt5.QtWidgets import QApplication
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer, edit
from PyQt5.QtCore import QObject, QThreadPool, QRunnable, pyqtSignal


from ..functions.base_tools import BaseTools

from ..functions.createnodegrid.tools.rasters import PreRasterTools
from ..functions.createnodegrid.conversions.hot_spot import HOTConversion
from ..functions.createnodegrid.conversions.ridge import RIDConversion
from ..functions.createnodegrid.conversions.isochron import ISOConversion
from ..functions.createnodegrid.conversions.lower_subduction import LWSConversion
from ..functions.createnodegrid.conversions.abandoned_arc import ABAConversion
from ..functions.createnodegrid.conversions.passive_margin_wedge import PMWConversion
from ..functions.createnodegrid.conversions.continent import CTNConversion
from ..functions.createnodegrid.conversions.craton import CRAConversion
from ..functions.createnodegrid.conversions.other_margin import OTMConversion
from ..functions.createnodegrid.conversions.passive_margin_continent import PMCConversion
from ..functions.createnodegrid.conversions.rift import RIBConversion
from ..functions.createnodegrid.conversions.upper_subduction import UPSConversion
from ..functions.createnodegrid.conversions.collision import COLConversion
from ..functions.createnodegrid.conversions.selections import LinesSelections
from ..functions.createnodegrid.tools.feature_conversion_tools import FeatureConversionTools

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'create_node_grid_dialog.ui'))


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


class CreateNodeGridDialog(QtWidgets.QDialog, FORM_CLASS):

    def __init__(self, PM_age_list, PP_age_list, CP_age_list, input_fc):
        """Constructor.
        Sets up workers, threads, ages, progress bar, and connects buttons
        with respective functions.
        """
        super(CreateNodeGridDialog, self).__init__()
        self.setupUi(self)

        # Initialize input_fc and base_tools FIRST
        self.input_fc = input_fc
        self.base_tools = BaseTools(input_fc)
        self.output_folder_path = self.base_tools.get_layer_path("Output Folder")

        # Log for debugging
        QgsMessageLog.logMessage(
            f"CreateNodeGridDialog initialized with output folder: {self.output_folder_path}",
            "Create Node Grid",
            Qgis.Info
        )

        # Validate output folder exists
        if not self.output_folder_path or not os.path.exists(self.output_folder_path):
            QgsMessageLog.logMessage(
                f"Warning: Output folder does not exist or is not set: {self.output_folder_path}",
                "Create Node Grid",
                Qgis.Warning
            )
        self.raster_tools = PreRasterTools(self.base_tools)
        self.hot_spot_conversion = HOTConversion(self.base_tools)
        self.rid_conversion = RIDConversion(self.base_tools)
        self.iso_conversion = ISOConversion(self.base_tools)
        self.lws_conversion = LWSConversion(self.base_tools)
        self.aba_conversion = ABAConversion(self.base_tools)
        self.pmw_conversion = PMWConversion(self.base_tools)
        self.ctn_conversion = CTNConversion(self.base_tools)
        self.cra_conversion = CRAConversion(self.base_tools)
        self.otm_conversion = OTMConversion(self.base_tools)
        self.pmc_conversion = PMCConversion(self.base_tools)
        self.rib_conversion = RIBConversion(self.base_tools)
        self.ups_conversion = UPSConversion(self.base_tools)
        self.col_conversion = COLConversion(self.base_tools)
        self.lines_selections = LinesSelections(self.base_tools)
        self.feature_conversion_tools = FeatureConversionTools(self.base_tools)

        # Initialize attributes
        self.worker = None
        self.threads = []
        self.errors = []
        self.thread_pool = QThreadPool.globalInstance()
        self.PM_age_list = PM_age_list
        self.PP_age_list = PP_age_list
        self.CP_age_list = CP_age_list

        # Set up UI components
        self.age_listWidget.clear()
        self.age_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.progressBar.setValue(0)

        # Connect buttons to methods
        self.Action_CreateAllAgeList_pushButton.clicked.connect(self.populate_all_age_list)
        self.Action_FeatureConversion_pushButton.clicked.connect(self.convert_features)
        self.Action_CleanNodes_pushButton.clicked.connect(self.clean_nodes)
        self.Action_MergeNodes_pushButton.clicked.connect(self.merge_all_nodes)
        self.Action_ProcessEverything_pushButton.clicked.connect(self.process_everything)

    def populate_all_age_list(self):
        """
        Creates the selectable ages that are common to the plate model,
        plate polygons, and continents polygons. Displays ages with
        their respective chronostratigraphic age names.
        """
        QgsMessageLog.logMessage("Button click works", "Create Node Grid", Qgis.Info)
        system_name = platform.system()
        if system_name in ["Darwin", "Linux"]:
            file_path = os.path.expanduser("~/Desktop/pStrAge_values.txt")
        else:
            file_path = "pStrAge_values.txt"

        try:
            self.age_listWidget.clear()

            # If any age list is None, read from file
            if self.PM_age_list is None or self.PP_age_list is None or self.CP_age_list is None:
                if os.path.exists(file_path):
                    with open(file_path, "r") as file:
                        all_age_list = [float(line.split()[0]) for line in file]
                        QgsMessageLog.logMessage(f"Ages available: {all_age_list}", "Create Node Grid", Qgis.Info)
                else:
                    QgsMessageLog.logMessage(f"File not found at path {file_path}", "Create Node Grid", Qgis.Info)
                    return
            else:
                pm_set = set(self.PM_age_list or [])
                pp_set = set(self.PP_age_list or [])
                cp_set = set(self.CP_age_list or [])
                all_age_list = sorted(list(pm_set.intersection(pp_set, cp_set)))

            if not all_age_list:
                return

            for i, age_value in enumerate(all_age_list, start=1):
                pStrAge = f"{age_value} Ma - [ {self.base_tools.get_relative_age(age_value)} ]"
                self.age_listWidget.addItem(pStrAge)

            return all_age_list

        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating age list: {str(e)}", "Create Node Grid", Qgis.Critical)
            raise


    def convert_features(self):
        """Start feature conversion, ensuring sequential execution."""
        self.progressBar.setValue(0)
        self.completed_steps = 0
        self.start_time = time.time()

        selected_items = self.age_listWidget.selectedItems()
        self.age_values = [float(item.text().split()[0]) for item in selected_items]
        self.total_steps = 15 * len(self.age_values)

        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        self.current_age_index = 0
        self.process_next_age()

    def process_next_age(self):
        """Process the next age, ensuring completion before moving to the next."""
        if self.current_age_index >= len(self.age_values):
            self.write_elapsed_time()
            return

        age = self.age_values[self.current_age_index]
        QgsMessageLog.logMessage(f"Processing age {age}", "Processing", Qgis.Info)
        self.run_initial_processing(age)
        self.start_threads(age)

    def run_initial_processing(self, age):
        self.remaining_threads = 1
        worker = ThreadedWorker(self.lines_selections.select_lines, age, progress_enabled=True)
        worker.signals.finished.connect(self.thread_finished)
        worker.signals.error.connect(self.thread_error)
        worker.signals.progress.connect(self.update_progress_bar)
        self.threads.append(worker)
        QThreadPool.globalInstance().start(worker)

        while QThreadPool.globalInstance().activeThreadCount() > 0:
            QApplication.processEvents()
        self.remaining_threads = 1
        worker = ThreadedWorker(self.rid_conversion.ridge_to_nodes, age, progress_enabled=True)
        worker.signals.finished.connect(self.thread_finished)
        worker.signals.error.connect(self.thread_error)
        worker.signals.progress.connect(self.update_progress_bar)
        self.threads.append(worker)
        QThreadPool.globalInstance().start(worker)

        while QThreadPool.globalInstance().activeThreadCount() > 0:
            QApplication.processEvents()
        self.remaining_threads = 1
        worker = ThreadedWorker(self.iso_conversion.isochron_to_nodes, age, progress_enabled=True)
        worker.signals.finished.connect(self.thread_finished)
        worker.signals.error.connect(self.thread_error)
        worker.signals.progress.connect(self.update_progress_bar)
        self.threads.append(worker)
        QThreadPool.globalInstance().start(worker)
        while QThreadPool.globalInstance().activeThreadCount() > 0:
            QApplication.processEvents()
        self.raster_tools.generate_temporary_raster_plate_by_plate(age)
        self.update_progress_bar()



    def start_threads(self, age):
        """Start threaded processing after initial functions complete."""
        functions = [
            self.lws_conversion.lower_subduction_to_nodes,
            self.aba_conversion.abandoned_arc_to_nodes,
            self.pmw_conversion.passive_margin_wedge_to_nodes,
            self.ctn_conversion.continent_geode_to_nodes,
            self.cra_conversion.craton_to_nodes,
            self.otm_conversion.other_margin_to_nodes,
            self.pmc_conversion.passive_margin_continent_to_nodes,
            self.rib_conversion.rift_to_nodes,
            self.ups_conversion.upper_subduction_to_nodes,
            self.col_conversion.collision_to_nodes,
            self.hot_spot_conversion.hot_spot_to_nodes,
        ]

        self.remaining_threads = len(functions)
        for func in functions:
            worker = ThreadedWorker(func, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            worker.signals.progress.connect(self.update_progress_bar)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)


    def thread_finished(self):
        """Check if all threads are done before moving to the next age."""
        self.remaining_threads -= 1
        if self.remaining_threads == 0:
            self.current_age_index += 1
            self.process_next_age()

    def update_progress_bar(self):
        """Update progress bar."""
        self.completed_steps += 1
        percentage = (self.completed_steps / self.total_steps) * 100
        self.progressBar.setValue(int(percentage))

    def thread_error(self, error_message):
        """Handle thread errors."""
        QgsMessageLog.logMessage(f"Thread error: {error_message}", "Processing", Qgis.Critical)
        self.errors.append(error_message)

    def write_elapsed_time(self):
        """Write elapsed time and log errors if any."""
        file_path = os.path.join(self.output_folder_path, "time.txt")
        errors_path = os.path.join(self.output_folder_path, "errors.log")
        elapsed_time = time.time() - self.start_time
        with open(file_path, "a") as file:
            for age in self.age_values:
                file.write(f"Age {age} - Elapsed time: {elapsed_time:.2f} seconds\n")

        if self.errors:
            with open(errors_path, "a") as err_file:
                err_file.write("\n".join(self.errors) + "\n")
            QgsMessageLog.logMessage("Errors occurred during processing. See errors.log", "Processing", Qgis.Warning)

        #QtWidgets.QMessageBox.information(self, "Processing Complete",f"All processing completed successfully.\nTotal elapsed time: {elapsed_time:.2f} seconds.")

    def merge_all_nodes(self):
        """
        Merges all nodes from the various settings into a single all nodes layer.
        Runs in separate threads for each selected age.
        """
        selected_items = self.age_listWidget.selectedItems()
        self.age_values = [float(item.text().split()[0]) for item in selected_items]

        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        self.remaining_threads = len(self.age_values)
        self.current_age_index = 0  # Initialize current_age_index here

        self.start_time = time.time()

        # First set of threads for create_final_nodes
        for age in self.age_values:
            worker = ThreadedWorker(self.feature_conversion_tools.create_final_nodes, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)

    def clean_nodes(self):
        """
        Cleans the all nodes layer to remove nodes from different settings to
        remove incoherent (contradicting) nodes when interpolating.
        """

        selected_items = self.age_listWidget.selectedItems()
        self.age_values = [float(item.text().split()[0]) for item in selected_items]

        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return

        self.remaining_threads = len(self.age_values)
        self.current_age_index = 0  # Initialize current_age_index here

        self.start_time = time.time()

        for age in self.age_values:
            worker = ThreadedWorker(self.feature_conversion_tools.clean_nodes, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)

            while QThreadPool.globalInstance().activeThreadCount() > 0:
                QApplication.processEvents()

        for age in self.age_values:
            worker = ThreadedWorker(self.feature_conversion_tools.clean_nodes_hot_polygon, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)

    def process_everything(self):
        self.progressBar.setValue(0)
        self.completed_steps = 0
        self.start_time = time.time()

        selected_items = self.age_listWidget.selectedItems()
        self.age_values = [float(item.text().split()[0]) for item in selected_items]
        self.total_steps = 18 * len(self.age_values)
        if not self.age_values:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select at least one age.")
            return
        self.current_age_index = 0
        self.process_next_age()

        while QThreadPool.globalInstance().activeThreadCount() > 0:
            QApplication.processEvents()

        self.start_time = time.time()

        for age in self.age_values:
            worker = ThreadedWorker(self.feature_conversion_tools.create_final_nodes, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            worker.signals.progress.connect(self.update_progress_bar)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)
            while QThreadPool.globalInstance().activeThreadCount() > 0:
                QApplication.processEvents()

        self.start_time = time.time()

        for age in self.age_values:
            worker = ThreadedWorker(self.feature_conversion_tools.clean_nodes, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            worker.signals.progress.connect(self.update_progress_bar)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)

            while QThreadPool.globalInstance().activeThreadCount() > 0:
                QApplication.processEvents()
        self.start_time = time.time()

        for age in self.age_values:
            worker = ThreadedWorker(self.feature_conversion_tools.clean_nodes_hot_polygon, age, progress_enabled=True)
            worker.signals.finished.connect(self.thread_finished)
            worker.signals.error.connect(self.thread_error)
            worker.signals.progress.connect(self.update_progress_bar)
            self.threads.append(worker)
            QThreadPool.globalInstance().start(worker)


