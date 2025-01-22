from qgis.core import Qgis, QgsWkbTypes, QgsMessageLog,QgsVectorLayer, QgsProject


def check_file_geometry(layer, expected_geometry_type):
    """Check if the layer's geometry type matches the expected type."""
    if layer is None:
        return "Error: No layer selected"

    # Get the geometry of the selected layer.
    geometry_type = QgsWkbTypes.geometryDisplayString(layer.geometryType())
    # Define validation message for geometry type.
    if geometry_type == expected_geometry_type:
        return "Geometry ok."
    else:
        return f"Error: The input data is {geometry_type}. A {expected_geometry_type} geometry is required."

def check_fields(layer, expected_field_names=None):
    """Check if the layer contains the fields required by the model."""
    if expected_field_names is None:
        expected_field_names = []

    # Extract field names from the QgsFields object.
    existing_field_names = [field.name() for field in layer.fields()]

    # Get all missing fields.
    missing_fields = [field_name for field_name in expected_field_names if field_name not in existing_field_names]

    corresponding_fields = [field_name for field_name in expected_field_names if field_name in existing_field_names]
    # Define validation message for missing fields.
    if not missing_fields:
        return {"message": "Fields ok.",
                "existing_fields": existing_field_names,
                "corresponding_fields": corresponding_fields,
                "missing_fields": missing_fields}
    else:
        return {"message": "Missing fields: {}".format(", ".join(missing_fields)),
                "existing_fields": existing_field_names,
                "corresponding_fields": corresponding_fields,
                "missing_fields": missing_fields}

def check_values(layer, expected_field_names=None):
    """Check if the fields required by the model do not contain blanks, none or null values."""
    if expected_field_names is None:
        expected_field_names = []

    error_messages = []

    for field_name in expected_field_names:
        values = [feature[field_name] for feature in layer.getFeatures()]

        invalid_values = [str(value).lower() for value in values if value is None or str(value).lower() == "none"]

        if invalid_values:
            error_messages.append(f"Incorrect values in field '{field_name}'. Blank, 'None', or 'NULL' values found.")

    if error_messages:
        # There were errors, return the formatted error messages as a list
        return error_messages
    else:
        # No errors, return success message
        return ["Values ok."]

def create_age_list(layer, field_name):
    """Create age list from a specified field in the layer."""
    try:
        if layer is not None:
            # Extract values from the specified field
            values = [feature[field_name] for feature in layer.getFeatures()]
            return values, "Age list ok."
        else:
            return None, "Error: No layer selected."

    except Exception as e:
        return None, f"Error creating age list: {str(e)}"



