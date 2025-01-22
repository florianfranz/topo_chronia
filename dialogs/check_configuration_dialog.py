import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'check_configuration_dialog.ui'))

class CheckConfigurationDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(CheckConfigurationDialog, self).__init__(parent)
        self.setupUi(self)







