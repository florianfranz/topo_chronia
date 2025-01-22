import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.core import QgsProject, Qgis, QgsMessageLog, QgsFeature, QgsVectorLayerEditBuffer, edit, QgsField

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'match_fields_dialog.ui'))

class MatchFieldsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(MatchFieldsDialog, self).__init__(parent)
        self.setupUi(self)

        # Keep track of MatchFields_pushButton instances
        self.match_fields_buttons = []

    def set_configuration_check_step(self, check_configuration_step):
        # Sets the name of the current step.
        self.Label_CurrentStep.setText(check_configuration_step)

    def set_selected_layer(self, selected_layer):
        """
        Sets the selected layer from the configuration check current component.
        """
        self.selected_layer = selected_layer
        self.Label_SelectedLayer.setText(selected_layer.name())

    def set_fields_names(self, expected_field_names, fields_validation_messages):
        """
        Sets field name corresponding to an existing field that has the wrong name.
        """
        # Clear any existing labels
        for i in reversed(range(self.gridLayout_Fields.count())):
            widget = self.gridLayout_Fields.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        # Create QLabel for each expected field name and its corresponding field
        row = 0
        for field_name in expected_field_names:
            label_expected = QtWidgets.QLabel(field_name)
            self.gridLayout_Fields.addWidget(label_expected, row, 0)

            # Check if the corresponding field exists in the list
            if field_name in fields_validation_messages["corresponding_fields"]:
                corresponding_field = field_name
                label_corresponding = QtWidgets.QLabel(str(corresponding_field))
                self.gridLayout_Fields.addWidget(label_corresponding, row, 1)

            else:
                # If no corresponding field, add a QLabel with "No Matching field"
                label_no_matching_field = QtWidgets.QLabel("No Matching field")
                self.gridLayout_Fields.addWidget(label_no_matching_field, row, 1)
                fields_combo_box = QtWidgets.QComboBox()
                fields_combo_box.addItem("Select Field")
                fields_combo_box.addItems(fields_validation_messages["existing_fields"])
                self.gridLayout_Fields.addWidget(fields_combo_box, row, 2)

                # Create MatchFields_pushButton and connect it to match_fields
                match_fields_button = QtWidgets.QPushButton("Match Field")
                match_fields_button.clicked.connect(lambda checked, row=row: self.match_fields(row))
                self.gridLayout_Fields.addWidget(match_fields_button, row, 3)

            row += 1
    def match_fields(self, row=None):
        """
        For all field names that are missing, allows the users to update manually update the
        corresponding field with an exiyting one. This works when the required field is not
        named correctly but exist.
        """
        if row is not None and self.selected_layer is not None:
            # Get the expected field name from the first column
            label_expected = self.gridLayout_Fields.itemAtPosition(row, 0).widget()
            expected_field_name = label_expected.text().strip()  # Remove leading/trailing spaces

            # Get the selected field from the combo box
            combo_field = self.gridLayout_Fields.itemAtPosition(row, 2).widget()  # Renamed from fields_combo_box
            selected_field_name = combo_field.currentText()

            # Get the index of the selected field from the selected_layer
            selected_field_index = self.selected_layer.fields().indexOf(selected_field_name)

            # Log the information using QgsMessageLog
            log_message = (
                f"Expected Field: {expected_field_name}\n"
                f"Selected Field: {selected_field_name}\n"
                f"Selected Field Index: {selected_field_index}"
            )
            QgsMessageLog.logMessage(log_message, "Check Configuration", Qgis.Info)

            self.selected_layer.startEditing()
            self.selected_layer.renameAttribute(selected_field_index, expected_field_name)

            # Commit changes to save the edits
            self.selected_layer.commitChanges()
            # Log the matching information
            match_log_message = (f"Success! Field: '{selected_field_name}' was updated and matched to "
                                 f"'{expected_field_name}'.")
            QgsMessageLog.logMessage(match_log_message, "Check Configuration", Qgis.Info)

            # Update the button text to "Matched!"
            match_fields_button = self.gridLayout_Fields.itemAtPosition(row, 3).widget()
            match_fields_button.setText("Matched!")

            # Update the second column label to display the expected field name
            label_no_matching_field = self.gridLayout_Fields.itemAtPosition(row, 1).widget()
            label_no_matching_field.setText(expected_field_name)


            # Rollback to exit editing mode
            self.selected_layer.rollBack()