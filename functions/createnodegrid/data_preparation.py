import os
import json
from qgis.core import (QgsProject, edit,QgsMessageLog, QgsFeatureRequest, QgsWkbTypes, QgsGeometry, QgsFeature,
                       QgsFields,QgsProcessingFeatureSourceDefinition, QgsProcessingContext, QgsVectorLayer,
                       QgsMessageLog, Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometryCollection,
                       QgsJsonExporter, QgsMultiPolygon, QgsProcessingException, QgsProcessingOutputVectorLayer,
                       QgsPolygon, QgsField, QgsPointXY, QgsVectorFileWriter)

from qgis.PyQt.QtCore import QVariant

from ..base_tools import BaseTools
base_tools = BaseTools()

from .tools.rift_tools import RIBConversionTools
rib_tools = RIBConversionTools()

from .tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class DataPreparation:
    INPUT_FILE_PATH = "input_files.txt"
    plate_model_path = base_tools.get_layer_path("Plate Model")
    plate_model_layer = QgsVectorLayer(plate_model_path, "Plate Model", 'ogr')
    plate_polygons_path = base_tools.get_layer_path("Plate Polygons")
    plate_polygons_layer = QgsVectorLayer(plate_polygons_path, "Plate Polygons", 'ogr')
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    PLATE = "PLATE"
    TYPE = "TYPE"
    COB_LIMIT = "COB_LIMIT"

    def get_unique_values(self, layer, field_name, order, qf):
        unique_values = set()
        for feature in layer.getFeatures(qf):
            unique_values.add(feature[field_name])
        return sorted(list(unique_values),
                      reverse=(order == "Descending"))

    def get_valid_output_raster_name(self, p_name, b_warning, max_length):
        """
        Check if the target feature already exists and modify the name accordingly.
        """
        # Check if the target feature already exists
        i = 0
        p_tmp_name = p_name[:max_length]

        while os.path.exists(os.path.join(self.output_folder_path, p_tmp_name)):
            # Already exists
            i += 1

            if b_warning:
                # Add Warning to QgsMessageLog
                QgsMessageLog.logMessage(
                    f"Already existing raster. Name changed: {p_tmp_name} --> {p_name[:max_length]}{i}",
                    "Create Node Grid", Qgis.Warning)

            p_tmp_name = p_name[:max_length] + str(i)

        # Return Value
        return p_tmp_name


    def copy_data(self,input_feature, output_feature):
        """
        Copy data from input_feature to output_feature for fields with matching names.

        Parameters:
        - input_feature: Input feature
        - output_feature: Output feature (must have the same fields as input_feature)
        """
        try:
            # Loop through Fields and copy data if field names correspond
            for i in range(input_feature.fields().fieldCount()):
                if not input_feature.value(i) is None:
                    input_field = input_feature.fields().field(i)
                    if input_field.isEditable():
                        output_feature[i] = input_feature.value(i)
        except Exception as ex:
            QgsMessageLog.logMessage(str(ex), 'Create Node Grid', QgsMessageLog.CRITICAL)

    def aggregate_plate_polygons(self, age):
            if self.plate_polygons_layer.isValid():
                qf = QgsFeatureRequest().setFilterExpression(f"{self.APPEARANCE} = {age}")
                coll = self.get_unique_values(self.plate_polygons_layer, self.PLATE, "Ascending", qf)

                if len(coll) == 0:
                    # No polygons to aggregate
                    no_polygons_message = f"No Plate Polygons found for age {age}"
                    QgsMessageLog.logMessage(no_polygons_message, "Create Node Grid", Qgis.Warning)
                else:
                    # Create a new memory layer for the aggregated polygons
                    aggregated_layer = QgsVectorLayer("Polygon?crs=" + self.plate_polygons_layer.crs().authid(),
                                                      f"plate_polygons_age_{int(age)}", "memory")
                    aggregated_provider = aggregated_layer.dataProvider()
                    aggregated_layer.startEditing()

                    # Add attributes to the new layer based on the input layer
                    attributes = self.plate_polygons_layer.fields().toList()
                    aggregated_provider.addAttributes(attributes)

                    for short_name in coll:
                        qf = QgsFeatureRequest().setFilterExpression(
                            f"{self.APPEARANCE} = {age} AND {self.PLATE} = '{short_name}'")
                        features = list(self.plate_polygons_layer.getFeatures(qf))
                        QgsMessageLog.logMessage(f"Iterating: {short_name}",
                                                 "Create Node Grid",
                                                 Qgis.Info)

                        # Iterate through features and union polygons if needed
                        if len(features) > 1:
                            # Initialize unioned_polygon to None
                            unioned_polygon = None

                            # Iterate through features and union polygons
                            for feature in features:
                                geom = feature.geometry()

                                if unioned_polygon is None:
                                    unioned_polygon = geom
                                else:
                                    unioned_polygon = unioned_polygon.combine(geom)

                            # Create a new feature
                            new_feature = QgsFeature()

                            # Set the geometry and attributes for the new feature
                            new_feature.setGeometry(unioned_polygon)
                            new_feature.setAttributes(features[0].attributes())

                            # Add the new feature to the layer
                            success = aggregated_provider.addFeature(new_feature)
                            if not success:
                                QgsMessageLog.logMessage(
                                    f"Error adding feature {feature.id()} to the layer",
                                    "Create Node Grid",
                                    Qgis.Info
                                )
                        else:
                            # If only one feature, add it directly to the aggregated_layer
                            single_feature = features[0]
                            success = aggregated_provider.addFeature(single_feature)
                            if not success:
                                QgsMessageLog.logMessage(
                                    f"Error adding feature {single_feature.id()} to the layer",
                                    "Create Node Grid",
                                    Qgis.Info
                                )

                    # Commit changes to the aggregated layer
                    aggregated_layer.commitChanges()

                    # Clear filters from the input layer
                    self.plate_polygons_layer.removeSelection()
                    self.plate_polygons_layer.setSubsetString('')

                    # Define output layer path
                    output_layer_path = os.path.join(self.output_folder_path,
                                                     f"plate_polygons_age_{int(age)}.geojson")

                    # Save the layer as ESRI GeoJSON
                    QgsVectorFileWriter.writeAsVectorFormat(aggregated_layer,
                                                            output_layer_path,
                                                            "utf-8",
                                                            aggregated_layer.crs(),
                                                            "GeoJSON")

    def aggregate_plate_polygons_new(self, age):
        agg_plate_polygon_layer = QgsVectorLayer("Polygon?crs=EPSG:4326",
                                                 "Aggregated Continent Polygon",
                                                 "memory")

        agg_plate_polygon_layer_provider = agg_plate_polygon_layer.dataProvider()

        plate_filter = (
            f"{self.APPEARANCE} = {age}"
        )
        plate_features =  list(
            self.plate_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_filter))
        )

        if len(plate_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.",
                                     "Create Node Grid",
                                     Qgis.Info)
            return
        multipolygon_coords = []
        for feature in plate_features:
            if feature.geometry().isMultipart():
                geom = feature.geometry().asMultiPolygon()
                for part in geom:
                    polygon_coords = []
                    for vertex in part[0]:
                        x_coord = vertex.x()
                        y_coord = vertex.y()
                        coords = [x_coord,y_coord]
                        polygon_coords.append(coords)
                    if polygon_coords[0] != polygon_coords[-1]:
                        polygon_coords.append(polygon_coords[0])
                    multipolygon_coords.append(polygon_coords)

            else:
                if feature.geometry().isEmpty():
                    pass
                else:
                    geom = feature.geometry().asPolygon()
                    polygon_coords = []
                    for vertex in geom:
                        x_coord = vertex.x()
                        y_coord = vertex.y()
                        coords = [x_coord, y_coord]
                        polygon_coords.append(coords)
                    if polygon_coords[0] != polygon_coords[-1]:
                        polygon_coords.append(polygon_coords[0])
                    multipolygon_coords.append(polygon_coords)
        multi_polygon_feature = [{
            "type": "Feature",
            "properties": {
                "TYPE": "Plates"
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [multipolygon_coords]
            }
        }]
        # Write all aggregated multipolygon features to the output GeoJSON file
        plate_multipolygons_path = os.path.join(self.output_folder_path,
                                                 f"plates_multipolygons_{int(age)}.geojson")
        with open(plate_multipolygons_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": multi_polygon_feature
            }, indent=2))



    def aggregate_continent_polygons(self, age):
        agg_cont_polygon_layer = QgsVectorLayer("Polygon?crs=EPSG:4326",
                                             "Aggregated Continent Polygon",
                                             "memory")
        agg_cont_polygon_provider = agg_cont_polygon_layer.dataProvider()
        continent_filter = (
            f"{self.APPEARANCE} = {age}"
        )
        continent_features = list(
            self.continent_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(continent_filter))
        )
        QgsMessageLog.logMessage(f"For age {age}, COB has {len(continent_features)}")
        if len(continent_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.",
                                     "Create Node Grid",
                                     Qgis.Info)
            return
        union_polygon = None
        for feature in continent_features:
            geom = feature.geometry()
            if union_polygon is None:
                union_polygon = geom
            else:
                union_polygon.combine(geom)
        new_feature = QgsFeature()
        new_feature.setGeometry(union_polygon)
        agg_cont_polygon_provider.addFeature(new_feature)
        agg_cont_polygon_layer.commitChanges()

        # Define output layer path
        output_layer_path = os.path.join(self.output_folder_path,
                                         f"continent_polygons_age_{int(age)}.geojson")

        # Save the layer as GeoJSON
        QgsVectorFileWriter.writeAsVectorFormat(agg_cont_polygon_layer,
                                                output_layer_path,
                                                "utf-8",
                                                agg_cont_polygon_layer.crs(),
                                                "GeoJSON")


    def set_raster_name_coll(self, age):
        """
        This method reads the name of the plates stored in the plate polygons FC to prepare the output
        names of the rasters that will be created during the grid creation.
        """
        if self.plate_polygons_layer.isValid():
            # Clear Collections
            self.raster_short_names = []
            self.plates_short_names = []


            qf = QgsFeatureRequest().setFilterExpression(f"{self.APPEARANCE} = {age}")
            # Loop through plate names
            plate_features = list(self.plate_polygons_layer.getFeatures(qf))

            if len(plate_features) == 0:
                # No plates found for the given age
                no_plates_message = f"No Plate Polygons found for age {age}"
                QgsMessageLog.logMessage(no_plates_message,
                                         "Create Node Grid",
                                         Qgis.Info)
            else:
                # Log plate names
                plate_names = [feature.attribute(self.PLATE) for feature in plate_features]
                QgsMessageLog.logMessage(f"Plate names: {', '.join(plate_names)}",
                                         "Create Node Grid",
                                         Qgis.Info)

                # Generate raster names
                p_str = ""
                for i, plate_feature in enumerate(plate_features, start=1):
                    # Get stored short name
                    p_short_name = plate_feature.attribute(self.PLATE)

                    # Shorten the name
                    p_name = p_short_name[:5]
                    p_tmp_name = p_name
                    p_cnt = 0

                    # Check if the name already exists. If yes, add a number
                    while p_str.find(p_name) != -1:
                        p_cnt += 1
                        p_name = p_tmp_name + str(p_cnt)

                    p_str += "/" + p_name
                    p_name = self.get_valid_output_raster_name(p_name,
                                                               False,
                                                               9)

                    # Put in the collection
                    self.raster_short_names.append(p_name)
                    # Write raster_short_names to a file
                    try:
                        output_file_path = f"raster_short_names_{int(age)}.txt"
                        with open(output_file_path, "w") as output_file:
                            for name in self.raster_short_names:
                                output_file.write(name + "\n")

                        QgsMessageLog.logMessage(f"Raster short names written to: {output_file_path}",
                                                 "Create Node Grid",
                                                 Qgis.Info)

                    except Exception as e:
                        QgsMessageLog.logMessage(f"Error writing raster short names to file: {str(e)}",
                                                 "Create Node Grid",
                                                 Qgis.Warning)

                # Log success message
                success_message = f"Set Raster Names completed successfully for age {age}"
                QgsMessageLog.logMessage(success_message,
                                         "Create Node Grid",
                                         Qgis.Info)

    def prepare_plate_model(self, age):
        """
        Loop through plates and check if intersecting features have the proper plate name value.
        If not, the feature is split according to the plate polygons and the proper value is stored.
        """

        APPEARANCE = "APPEARANCE"
        TYPE = "TYPE"
        PLATE = "PLATE"
        COB_LIMIT = "COB_LIMIT"

        # Clear existing subset or filter for Plate Model layer
        self.plate_model_layer.setSubsetString('')

        # Set Filter Expression for Plate Model layer
        plate_model_filter = (
            f"{self.APPEARANCE} = {age} AND "
            f"({self.TYPE} != 'Hot_Spot' AND {self.TYPE} != 'Seamount' AND self.{TYPE} != 'LIP') AND "
            f"{self.COB_LIMIT} = 'Yes'"
        )

        # Use QgsFeatureRequest to filter Plate Model layer
        plate_model_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_model_filter))
        )

        QgsMessageLog.logMessage(f"Found {len(plate_model_features)} features in Plate Model layer.",
                                 "Create Node Grid",
                                 Qgis.Info)

        # Clear existing subset or filter for Plate Polygons layer
        self.plate_polygons_layer.setSubsetString('')

        # Set Filter Expression for Plate Polygons layer
        plate_polygons_filter = f"{self.APPEARANCE} = {age}"

        # Use QgsFeatureRequest to filter Plate Polygons layer
        plate_polygons_features = list(
            self.plate_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_polygons_filter))
        )

        QgsMessageLog.logMessage(f"Found {len(plate_polygons_features)} features in Plate Polygons layer.",
                                 "Create Node Grid",
                                 Qgis.Info)

        # Loop through features in plate_polygons_layer
        for plate_feature in plate_polygons_features:
            # Get plate shortname
            short_name = plate_feature.attribute(PLATE)

            # Get Features intersecting the plate boundary
            qf_intersect = QgsFeatureRequest().setFilterExpression(
                f"{self.APPEARANCE} = {age} AND "
                f"({self.TYPE} != 'Hot_Spot' AND {self.TYPE} != 'LIP' AND {self.TYPE} != 'Seamount' AND "
                f"{self.PLATE} != '{short_name}'"
            )
            intersecting_features = list(self.plate_model_layer.getFeatures(qf_intersect))

            QgsMessageLog.logMessage(f"Found {len(intersecting_features)} intersecting features in Plate Model layer.",
                                     "Create Node Grid",
                                     Qgis.Info)

            # Loop through intersecting features
            for plate_model_feature in intersecting_features:
                QgsMessageLog.logMessage(
                    f"Processing feature in Plate Model layer. Age: {age}, Short Name: {short_name}",
                    "Create Node Grid",
                    Qgis.Info)
                # Get intersecting polyline
                topo_op = plate_model_feature.geometry().intersection(plate_feature.geometry())

                # Loop through parts
                for i in range(topo_op.geometryCount()):
                    # Convert into polyline
                    if topo_op.geometry(i).type() == QgsWkbTypes.LineGeometry:
                        polyline = topo_op.geometry(i)
                    else:
                        polyline = QgsGeometry.fromPolyline(topo_op.geometry(i).asPolyline())

                    # Update Shape
                    out_feat = QgsFeature()
                    out_feat.setGeometry(polyline)
                    self.copy_data(plate_model_feature,
                                   out_feat)
                    out_feat.setAttribute(self.PLATE,
                                          plate_feature.attribute(self.PLATE))
                    self.plate_model_layer.addFeature(out_feat)

                    # Clear Memory
                    del out_feat

        QgsMessageLog.logMessage("Processing complete.",
                                 "Create Node Grid",
                                 Qgis.Info)
        # Clear existing subset or filter for Plate Polygons layer
        self.plate_polygons_layer.setSubsetString('')

    def check_shape_length(self, age):
        """
        Check polyline length for features in the Plate Model layer and delete features with length < 0.1.
        """

        # Clear existing subset or filter for Plate Model layer
        self.plate_model_layer.setSubsetString('')

        # Set Filter Expression for Plate Model layer
        plate_model_filter = f"{self.APPEARANCE} = {age}"

        # Use QgsFeatureRequest to filter Plate Model layer
        plate_model_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_model_filter))
        )

        QgsMessageLog.logMessage(f"Found {len(plate_model_features)} features in Plate Model layer.",
                                 "Create Node Grid",
                                 Qgis.Info)

        pCnt = 0  # Initialize pCnt
        # Loop through features
        for plate_model_feature in plate_model_features:
            try:
                # Check polyline length
                polyline = plate_model_feature.geometry()

                # If length < 0.1°, delete feature
                if polyline.length() < 0.1:
                    QgsMessageLog.logMessage(
                        f"Deleting feature with ID {plate_model_feature.id()} due to length < 0.1.",
                        "Create Node Grid",
                        Qgis.Info)
                    self.plate_model_layer.startEditing()
                    self.plate_model_layer.deleteFeature(plate_model_feature.id())
                    self.plate_model_layer.commitChanges()

                    # Progress Bar
                    pCnt += 1
                # Update your progress bar here
            except Exception as e:
                QgsMessageLog.logMessage(f"Error processing feature: {str(e)}",
                                         "Create Node Grid",
                                         Qgis.Info)

        # Check if any features were deleted
        if pCnt == 0:
            QgsMessageLog.logMessage("No features smaller than 0.1°. No edits were necessary.",
                                     "Create Node Grid",
                                     Qgis.Info)
        else:
            QgsMessageLog.logMessage(f"{pCnt} features were processed.",
                                     "Create Node Grid",
                                     Qgis.Info)

    def aggregate_basins(self, age):
        plate_model_filter = (
            f"{self.APPEARANCE} = {age} AND "
            f"(({self.TYPE} = 'Limit_Basin') OR ({self.TYPE} = 'Rift_Margin'))"
        )
        plate_model_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_model_filter)))
        if len(plate_model_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.",
                                     "Create Node Grid",
                                     Qgis.Info)
            return

        RIB_lines = QgsVectorLayer("LineString?crs=EPSG:4326",
                                   "RIB Lines",
                                   "memory")
        lines_provider = RIB_lines.dataProvider()
        RIB_lines.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        lines_provider.addAttributes(attributes)
        lines_provider.addFeatures(plate_model_features)

        lines_provider.addAttributes([
            QgsField('FEAT_AGE', QVariant.Double),
            QgsField('Z_CREST', QVariant.Double),
            QgsField('TYR', QVariant.Double),
            QgsField('ORIG_ID', QVariant.Double)
        ])
        RIB_lines.updateFields()
        RIB_lines.commitChanges()

        field_idx_fa = RIB_lines.fields().indexOf('FEAT_AGE')
        field_idx_zc = RIB_lines.fields().indexOf('Z_CREST')
        field_idx_tyr = RIB_lines.fields().indexOf('TYR')
        field_idx_oid = RIB_lines.fields().indexOf('ORIG_ID')

        with edit(RIB_lines):
            for feature in RIB_lines.getFeatures():
                feat_id = feature.id()
                RIB_lines.changeAttributeValue(feature.id(),
                                               field_idx_oid,
                                               feat_id)
                feature_abs_age = feature.attribute('AGE')
                feature_age = feature_abs_age - age
                RIB_lines.changeAttributeValue(feature.id(),
                                               field_idx_fa,
                                               feature_age)

                z_crest = float(rib_tools.crest_y_rift(age, feature_age))
                RIB_lines.changeAttributeValue(feature.id(),
                                               field_idx_zc,
                                               z_crest)

                through_y_rift = float(rib_tools.through_y_rift(age,
                                                                feature_age))
                RIB_lines.changeAttributeValue(feature.id(),
                                               field_idx_tyr,
                                               through_y_rift)
        RIB_lines.commitChanges()
        original_RIB_lines_layer_path = os.path.join(self.output_folder_path,
                                                     f"original_RIB_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(RIB_lines,original_RIB_lines_layer_path,'utf-8',RIB_lines.crs(), "GeoJSON")
        dens_RIB_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_RIB_lines_layer_path, tolerance_value=1)
        dens_RIB_layer = QgsVectorLayer(dens_RIB_layer_path, "Densified RIB lines", "ogr")
        all_polygons = []
        for feature in dens_RIB_layer.getFeatures():
            orig_id = feature.attribute('ORIG_ID')
            feature_level_coords = []
            if feature.geometry().isMultipart():
                geom = feature.geometry().asMultiPolyline()
                for part in geom:
                    if len(part) <= 3:
                        pass
                    else:
                        polygon_coords = []
                        for vertex in part:
                            x_coord = vertex.x()
                            y_coord = vertex.y()
                            coords = [x_coord, y_coord]
                            polygon_coords.append(coords)
                        if polygon_coords[0] != polygon_coords[-1]:
                            polygon_coords.append(polygon_coords[0])
                        polygon_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": "Basin",
                                "ORIG_ID": int(orig_id)
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [polygon_coords]
                            }
                        }
                        all_polygons.append(polygon_feature)
            else:
                geom = feature.geometry().asPolyline()
                if len(geom) <= 3:
                    pass
                else:
                    polygon_coords = []
                    for vertex in geom:
                        x_coord = vertex.x()
                        y_coord = vertex.y()
                        coords = [x_coord, y_coord]
                        polygon_coords.append(coords)
                    if polygon_coords[0] != polygon_coords[-1]:
                        polygon_coords.append(polygon_coords[0])
                    feature_level_coords.append(polygon_coords)
                    polygon_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "Basin",
                            "ORIG_ID": int(orig_id)
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [polygon_coords]
                        }
                    }
                    all_polygons.append(polygon_feature)


        # Write all aggregated multipolygon features to the output GeoJSON file
        pre_basins_multipolygons_path = os.path.join(self.output_folder_path, f"pre_basins_multipolygons_{int(age)}.geojson")
        with open(pre_basins_multipolygons_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_polygons
            }, indent=2))
        basins_multipolygons_path = os.path.join(self.output_folder_path, f"basins_multipolygons_{int(age)}.geojson")

