import os
import json
import processing
from qgis.core import (Qgis, QgsFeatureRequest, QgsMessageLog, QgsVectorLayer, QgsField, QgsVectorFileWriter,
                       edit, QgsSpatialIndex, QgsPointXY, QgsGeometry,QgsFeature,QgsProcessingFeatureSourceDefinition)
from qgis.PyQt.QtCore import QVariant


from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.sediments_tools import SEDConversionTools
sed_tools = SEDConversionTools()

from ..tools.rift_tools import RIBConversionTools
rib_tools = RIBConversionTools()

class LinesSelections():
    INPUT_FILE_PATH = "input_files.txt"
    plate_model_path = base_tools.get_layer_path("Plate Model")
    plate_model_layer = QgsVectorLayer(plate_model_path, "Plate Model", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    POSITION = "POSITION"
    TYPE = "TYPE"
    NAME_TERR = "NAME_TERR"
    AGE = "AGE"
    def __init__(self):
        pass

    def select_lines(self,age):
        #01: RID
        RID_filter = ( f"{self.APPEARANCE} = {age} AND " f"({self.TYPE} = 'Ridge')")
        RID_features = list(self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(RID_filter)))
        if len(RID_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.","Create Node Grid",Qgis.Info)
            pass
        ridge_layer = QgsVectorLayer("LineString?crs=EPSG:4326",f"Ridges_{age}","memory")
        provider = ridge_layer.dataProvider()
        ridge_layer.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        provider.addAttributes(attributes)
        provider.addFeatures(RID_features)
        provider.addAttributes([QgsField('FEAT_AGE', QVariant.Double), QgsField('Z', QVariant.Double)])
        ridge_layer.commitChanges()
        field_idx_fa = ridge_layer.fields().indexOf('FEAT_AGE')
        field_idx_rd = ridge_layer.fields().indexOf('Z')
        with edit(ridge_layer):
            for feature in ridge_layer.getFeatures():
                feature_abs_age = feature.attribute('AGE')
                feature_age = feature_abs_age - age
                ridge_layer.changeAttributeValue(feature.id(), field_idx_fa, feature_age)
                ridge_depth = feature_conversion_tools.get_ridge_depth(age=age)
                ridge_layer.changeAttributeValue(feature.id(), field_idx_rd, float(ridge_depth))
        ridge_layer.commitChanges()
        original_RID_lines_layer_path = os.path.join(self.output_folder_path, f"original_RID_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(ridge_layer, original_RID_lines_layer_path, 'utf-8', ridge_layer.crs(),
                                                "GeoJSON")
        dens_RID_lines_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_RID_lines_layer_path,
                                                                                      tolerance_value=1)

        #02: ISO
        ISO_filter = (f"{self.APPEARANCE} = {age} AND "f"({self.TYPE} = 'Isochron')")
        ISO_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(ISO_filter)))
        if len(ISO_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.", "Create Node Grid", Qgis.Info)
            pass
        isochron_layer = QgsVectorLayer("LineString?crs=EPSG:4326", f"ISO Lines {int(age)}", "memory")
        provider = isochron_layer.dataProvider()
        isochron_layer.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        provider.addAttributes(attributes)
        provider.addFeatures(ISO_features)
        provider.addAttributes([QgsField('FEAT_AGE', QVariant.Double), QgsField('Z', QVariant.Double),
                                QgsField('ABYS_SED', QVariant.Double), QgsField('SED_THICK', QVariant.Double),
                                QgsField('RHO_SED', QVariant.Double)])
        isochron_layer.commitChanges()
        field_idx_fa = isochron_layer.fields().indexOf('FEAT_AGE')
        field_idx_z = isochron_layer.fields().indexOf('Z')
        field_idx_as = isochron_layer.fields().indexOf('ABYS_SED')
        field_idx_st = isochron_layer.fields().indexOf('SED_THICK')
        field_idx_rs = isochron_layer.fields().indexOf('RHO_SED')
        with edit(isochron_layer):
            for feature in isochron_layer.getFeatures():
                feature_abs_age = feature.attribute('AGE')
                feature_age = feature_abs_age - age
                isochron_layer.changeAttributeValue(feature.id(), field_idx_fa, feature_age)
                ridge_depth = feature_conversion_tools.get_ridge_depth(age)
                z = feature_conversion_tools.PCM(feature_age, ridge_depth)
                isochron_layer.changeAttributeValue(feature.id(), field_idx_z, float(z))
                abys_sed = sed_tools.abyssal_sediments(age, feature_abs_age)
                isochron_layer.changeAttributeValue(feature.id(), field_idx_as, float(abys_sed))
                sed_thick = sed_tools.full_sediment_thickness(abys_sed)
                isochron_layer.changeAttributeValue(feature.id(), field_idx_st, float(sed_thick))
                rho_sediments = sed_tools.rho_sed(sed_thick)
                isochron_layer.changeAttributeValue(feature.id(), field_idx_rs, float(rho_sediments))
        isochron_layer.commitChanges()
        original_ISO_layer_path = os.path.join(self.output_folder_path, f"original_ISO_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(isochron_layer, original_ISO_layer_path, 'utf-8', isochron_layer.crs(),
                                                "GeoJSON")
        dens_ISO_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_ISO_layer_path,
                                                                                tolerance_value=1)

        #03: SUB (LWS + UPS)
        SUB_filter = (
            f"{self.APPEARANCE} = {age} AND "f"(({self.TYPE} = 'Z_Subduction') OR ({self.TYPE} = 'Active_Margin'))")
        SUB_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(SUB_filter)))
        if len(SUB_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.", "Create Node Grid", Qgis.Info)
            pass
        SUB_lines = QgsVectorLayer("LineString?crs=EPSG:4326", f"SUB Lines", "memory")
        lines_provider = SUB_lines.dataProvider()
        SUB_lines.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        lines_provider.addAttributes(attributes)
        lines_provider.addFeatures(SUB_features)
        lines_provider.addAttributes([QgsField('FEAT_AGE', QVariant.Double)])
        SUB_lines.updateFields()
        SUB_lines.commitChanges()
        field_idx_fa = SUB_lines.fields().indexOf('FEAT_AGE')
        with edit(SUB_lines):
            for feature in SUB_lines.getFeatures():
                feature_abs_age = feature.attribute('AGE')
                feature_age = feature_abs_age - age
                SUB_lines.changeAttributeValue(feature.id(), field_idx_fa, feature_age)
        SUB_lines.commitChanges()
        original_SUB_lines_layer_path = os.path.join(self.output_folder_path, f"original_SUB_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(SUB_lines, original_SUB_lines_layer_path, 'utf-8', SUB_lines.crs(),
                                                "GeoJSON")
        dens_SUB_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_SUB_lines_layer_path,
                                                                                tolerance_value=1)
        dens_SUB_lines = QgsVectorLayer(dens_SUB_layer_path, "Simplified SUB Lines", 'ogr')
        sub_multipoints = QgsVectorLayer("MultiPoint?crs=EPSG:4326", "Sub Multipoints", "memory")
        points_provider = sub_multipoints.dataProvider()
        sub_multipoints.startEditing()
        attributes = dens_SUB_lines.fields().toList()
        points_provider.addAttributes(attributes)
        points_provider.addAttributes([QgsField('Z', QVariant.Double), QgsField('Z_RASTER', QVariant.Double), QgsField('ORIG_ID', QVariant.Double)])
        sub_multipoints.updateFields()
        sub_multipoints.commitChanges()
        for feature in dens_SUB_lines.getFeatures():
            geom = feature.geometry()
            coords_list = [QgsPointXY(pt) for part in geom.parts() for pt in part]
            multipoint_geom = QgsGeometry.fromMultiPointXY(coords_list)
            new_feature = QgsFeature()
            new_feature.setGeometry(multipoint_geom)
            new_feature.setAttributes(feature.attributes())
            points_provider.addFeature(new_feature)
        sub_multipoints.commitChanges()
        lws_multipoint_path = os.path.join(self.output_folder_path, f"lws_multipoint_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(sub_multipoints, lws_multipoint_path, 'utf-8', sub_multipoints.crs(),
                                                "GeoJSON")
        ups_multipoint_path = os.path.join(self.output_folder_path, f"ups_multipoint_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(sub_multipoints, ups_multipoint_path, 'utf-8', sub_multipoints.crs(),
                                                "GeoJSON")


        #04: ABA
        ABA_filter = (f"{self.APPEARANCE} = {age} AND "f"({self.TYPE} = 'Abandoned Arc')")
        ABA_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(ABA_filter)))
        if len(ABA_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.", "Create Node Grid", Qgis.Info)
            pass
        ABA_lines = QgsVectorLayer("LineString?crs=EPSG:4326", "ABA Lines", "memory")
        lines_provider = ABA_lines.dataProvider()
        ABA_lines.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        lines_provider.addAttributes(attributes)
        lines_provider.addFeatures(ABA_features)
        ABA_lines.commitChanges()
        original_ABA_lines_layer_path = os.path.join(self.output_folder_path, f"original_ABA_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(ABA_lines, original_ABA_lines_layer_path, 'utf-8', ABA_lines.crs(),
                                                "GeoJSON")
        dens_ABA_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_ABA_lines_layer_path,
                                                                                tolerance_value=1)

        #05: PM (PMW + PMC)
        PM_filter = (f"{self.APPEARANCE} = {age} AND "f"({self.TYPE} = 'Passive_Margin')")
        PM_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(PM_filter)))
        if len(PM_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.", "Create Node Grid", Qgis.Info)
            pass
        PM_lines = QgsVectorLayer("LineString?crs=EPSG:4326", "PM Lines", "memory")
        lines_provider = PM_lines.dataProvider()
        PM_lines.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        lines_provider.addAttributes(attributes)
        lines_provider.addFeatures(PM_features)
        lines_provider.addAttributes([QgsField('FEAT_AGE', QVariant.Double)])
        PM_lines.updateFields()
        PM_lines.commitChanges()
        field_idx_fa = PM_lines.fields().indexOf('FEAT_AGE')
        with edit(PM_lines):
            for feature in PM_lines.getFeatures():
                feature_abs_age = feature.attribute('AGE')
                feature_age = feature_abs_age - age
                PM_lines.changeAttributeValue(feature.id(), field_idx_fa, feature_age)
        PM_lines.commitChanges()
        original_PM_lines_layer_path = os.path.join(self.output_folder_path, f"original_PM_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(PM_lines, original_PM_lines_layer_path, 'utf-8', PM_lines.crs(),
                                                "GeoJSON")
        dens_PM_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_PM_lines_layer_path,
                                                                               tolerance_value=1)
        dens_PM_lines = QgsVectorLayer(dens_PM_layer_path, "Dens PM Lines", 'ogr')
        PM_multipoints = QgsVectorLayer("MultiPoint?crs=EPSG:4326", "PM_multipoints", "memory")
        points_provider = PM_multipoints.dataProvider()
        PM_multipoints.startEditing()
        attributes = dens_PM_lines.fields().toList()
        points_provider.addAttributes(attributes)
        points_provider.addAttributes([QgsField('Z', QVariant.Double), QgsField('Z_RASTER', QVariant.Double),
                                       QgsField('Z_CREST', QVariant.Double), QgsField('X_CREST', QVariant.Double),
                                       QgsField('X_MAX', QVariant.Double)])
        PM_multipoints.updateFields()
        PM_multipoints.commitChanges()
        for feature in dens_PM_lines.getFeatures():
            feature_abs_age = feature.attribute('AGE')
            if feature_abs_age != 9999:
                geom = feature.geometry()
                coords_list = [QgsPointXY(pt) for part in geom.parts() for pt in part]
                multipoint_geom = QgsGeometry.fromMultiPointXY(coords_list)
                new_feature = QgsFeature()
                new_feature.setGeometry(multipoint_geom)
                new_feature.setAttributes(feature.attributes())
                points_provider.addFeature(new_feature)
        PM_multipoints.commitChanges()
        pmc_multipoint_path = os.path.join(self.output_folder_path, f"pmc_multipoint_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(PM_multipoints, pmc_multipoint_path, 'utf-8', PM_multipoints.crs(),
                                                "GeoJSON")
        pmw_multipoint_path = os.path.join(self.output_folder_path, f"pmw_multipoint_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(PM_multipoints, pmw_multipoint_path, 'utf-8', PM_multipoints.crs(),
                                                "GeoJSON")

        #06: RIB
        RIB_filter = (
            f"{self.APPEARANCE} = {age} AND "
            f"(({self.TYPE} = 'Limit_Basin') OR ({self.TYPE} = 'Rift_Margin'))"
        )
        RIB_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(RIB_filter)))
        if len(RIB_features) == 0:
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
        lines_provider.addFeatures(RIB_features)

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
        QgsVectorFileWriter.writeAsVectorFormat(RIB_lines, original_RIB_lines_layer_path, 'utf-8', RIB_lines.crs(),
                                                "GeoJSON")
        dens_RIB_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_RIB_lines_layer_path,
                                                                                tolerance_value=1)
        dens_RIB_layer = QgsVectorLayer(dens_RIB_layer_path, "Densified RIB lines", "ogr")
        all_polygons = []
        for feature in dens_RIB_layer.getFeatures():
            orig_id = feature.attribute('ORIG_ID')
            plate = feature.attribute('PLATE')
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
                                "ORIG_ID": int(orig_id),
                                "APPEARANCE": age,
                                "PLATE": plate
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
                            "ORIG_ID": int(orig_id),
                            "APPEARANCE": age,
                            "PLATE": plate
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [polygon_coords]
                        }
                    }
                    all_polygons.append(polygon_feature)

        # Write all aggregated multipolygon features to the output GeoJSON file
        RIB_polygons_path = os.path.join(self.output_folder_path, f"RIB_polygons_{int(age)}_final.geojson")
        with open(RIB_polygons_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_polygons
            }, indent=2))


        #07: CRA
        CRA_filter = (f"{self.APPEARANCE} = {age} AND "f"{self.TYPE} = 'Limit_Craton' AND "f"{self.NAME_TERR} != 'Wyoming_Craton' AND "f"{self.NAME_TERR} != 'Colorado_Craton'")
        CRA_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(CRA_filter)))
        if len(CRA_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.", "Create Node Grid", Qgis.Info)
            pass
        CRA_lines_layer = QgsVectorLayer("LineString?crs=EPSG:4326", f"CRA_lines_{age}", "memory")
        lines_provider = CRA_lines_layer.dataProvider()
        CRA_lines_layer.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        lines_provider.addAttributes(attributes)
        lines_provider.addFeatures(CRA_features)
        CRA_lines_layer.commitChanges()
        original_CRA_layer_path = os.path.join(self.output_folder_path, f"original_CRA_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(CRA_lines_layer, original_CRA_layer_path, 'utf-8',
                                                CRA_lines_layer.crs(), "GeoJSON")
        dens_CRA_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_CRA_layer_path,
                                                                                tolerance_value=1)
        dens_CRA_layer = QgsVectorLayer(dens_CRA_layer_path, "Densified CRA Lines", "ogr")
        all_craton_polygons = []
        for feature in dens_CRA_layer.getFeatures():
            feature_orig_id = feature.id()
            name_terr = feature.attribute("NAME_TERR")
            plate = feature.attribute("PLATE")
            if not name_terr:
                name_terr = "NONE"
            if feature.geometry().isMultipart():
                geom = feature.geometry().asMultiPolyline()
                for part in geom:
                    polygon_coords = []
                    for vertex in part:
                        x_coord = vertex.x()
                        if x_coord > 180:
                            x_coord = 180
                        if x_coord < -180:
                            x_coord = -180
                        y_coord = vertex.y()
                        coords = [x_coord, y_coord]
                        polygon_coords.append(coords)
                    if polygon_coords[0] != polygon_coords[-1]:
                        polygon_coords.append(polygon_coords[0])
                    geojson_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "Craton",
                            "ORIG_ID": feature_orig_id,
                            "NAME_TERR": name_terr,
                            "APPEARANCE": age,
                            "PLATE": plate
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [polygon_coords]
                        }
                    }
                    all_craton_polygons.append(geojson_feature)
            else:
                QgsMessageLog.logMessage("original line is not multipart")
        CRA_polygons_path = os.path.join(self.output_folder_path, f"CRA_polygons_{int(age)}_final.geojson")
        with open(CRA_polygons_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_craton_polygons
            }, indent=2))

        #08: OTM
        OTM_filter = (
            f"{self.APPEARANCE} = {age} AND "f"(({self.TYPE} = 'Transform_Fault') OR ({self.TYPE} = 'Z_Inversion') OR ({self.TYPE} = 'Obduct_Front'))")
        OTM_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(OTM_filter)))
        if len(OTM_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.", "Create Node Grid", Qgis.Info)
            pass
        OTM_lines = QgsVectorLayer("LineString?crs=EPSG:4326", f"OTM Lines", "memory")
        lines_provider = OTM_lines.dataProvider()
        OTM_lines.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        lines_provider.addAttributes(attributes)
        lines_provider.addFeatures(OTM_features)
        OTM_lines.commitChanges()
        original_otm_lines_layer_path = os.path.join(self.output_folder_path, f"original_OTM_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(OTM_lines, original_otm_lines_layer_path, 'utf-8', OTM_lines.crs(),
                                                "GeoJSON")
        dens_OTM_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_otm_lines_layer_path,
                                                                                tolerance_value=1)

        #09: COL
        COL_filter = (
            f"{self.APPEARANCE} = {age} AND "f"(({self.TYPE} = 'Z_Collision' AND {self.POSITION} = 'Lower') OR "f"({self.TYPE} = 'Suture'))")
        COL_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(COL_filter)))
        if len(COL_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.", "Create Node Grid", Qgis.Info)
            pass
        COL_lines = QgsVectorLayer("LineString?crs=EPSG:4326", f"COL lines", "memory")
        lines_provider = COL_lines.dataProvider()
        COL_lines.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        lines_provider.addAttributes(attributes)
        lines_provider.addFeatures(COL_features)
        lines_provider.addAttributes([QgsField('FEAT_AGE', QVariant.Double)])
        COL_lines.updateFields()
        COL_lines.commitChanges()
        field_idx_fa = COL_lines.fields().indexOf('FEAT_AGE')
        with edit(COL_lines):
            for feature in COL_lines.getFeatures():
                feature_abs_age = feature.attribute(self.AGE)
                feature_age = feature_abs_age - age
                COL_lines.changeAttributeValue(feature.id(), field_idx_fa, feature_age)
        COL_lines.commitChanges()
        original_COL_lines_layer_path = os.path.join(self.output_folder_path, f"original_COL_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(COL_lines, original_COL_lines_layer_path, 'utf-8', COL_lines.crs(),
                                                "GeoJSON")
        dens_COL_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_COL_lines_layer_path,
                                                                                tolerance_value=1)


        #010: HOT
        HOT_filter = (
            f"{self.APPEARANCE} = {age} AND  ({self.TYPE} = 'LIP' OR {self.TYPE} = 'Seamount' OR {self.TYPE} = 'Hot_Spot')")
        HOT_features = list(
            self.plate_model_layer.getFeatures(QgsFeatureRequest().setFilterExpression(HOT_filter)))
        if len(HOT_features) == 0:
            QgsMessageLog.logMessage("No features found for the selected age, skipped.", "Create Node Grid", Qgis.Info)
            pass
        HOT_lines_layer = QgsVectorLayer("LineString?crs=EPSG:4326", f"HOT Lines_{age}", "memory")
        lines_provider = HOT_lines_layer.dataProvider()
        HOT_lines_layer.startEditing()
        attributes = self.plate_model_layer.fields().toList()
        lines_provider.addAttributes(attributes)
        lines_provider.addFeatures(HOT_features)
        lines_provider.addAttributes([QgsField('FEAT_AGE', QVariant.Double)])
        HOT_lines_layer.updateFields()
        HOT_lines_layer.commitChanges()
        field_idx_fa = HOT_lines_layer.fields().indexOf('FEAT_AGE')
        with edit(HOT_lines_layer):
            for feature in HOT_lines_layer.getFeatures():
                feature_abs_age = feature.attribute(self.AGE)
                feature_age = feature_abs_age - age
                HOT_lines_layer.changeAttributeValue(feature.id(), field_idx_fa, feature_age)
        HOT_lines_layer.commitChanges()
        original_HOT_layer_path = os.path.join(self.output_folder_path, f"original_HOT_lines_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(HOT_lines_layer, original_HOT_layer_path, 'utf-8',
                                                HOT_lines_layer.crs(), "GeoJSON")
        dens_HOT_lines_layer_path = feature_conversion_tools.harmonize_lines_geometry(original_HOT_layer_path,
                                                                                tolerance_value=0.5)
        dens_HOT_layer = QgsVectorLayer(dens_HOT_lines_layer_path, "Densified HOT layer", "ogr")
        HOT_features = list(dens_HOT_layer.getFeatures())
        if len(HOT_features) == 0:
            return
        else:
            all_polygons = []
            for feature in dens_HOT_layer.getFeatures():
                feat_age = feature.attribute("AGE") - age
                orig_id = feature.id()
                plate = feature.attribute("PLATE")
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
                                    "TYPE": "HOT",
                                    "ORIG_ID": int(orig_id),
                                    "FEAT_AGE": feat_age,
                                    "PLATE": plate
                                },
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [polygon_coords]
                                }
                            }
                            all_polygons.append(polygon_feature)
                else:
                    geom = feature.geomtry().asPolyline()
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
                                "TYPE": "HOT",
                                "ORIG_ID": int(orig_id),
                                "FEAT_AGE": feat_age,
                                "APPEARANCE": age,
                                "PLATE": plate
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [polygon_coords]
                            }
                        }
                        all_polygons.append(polygon_feature)
            output_polygons_layer_path = os.path.join(self.output_folder_path, f"HOT_polygons_{int(age)}.geojson")
            fixed_polygon_layer_path = output_polygons_layer_path.replace(f"{int(age)}.geojson",
                                                                          f"{int(age)}_fixed.geojson")
            diss_polygon_layer_path = os.path.join(self.output_folder_path, f"HOT_polygons_{int(age)}_final.geojson")
            with open(output_polygons_layer_path, 'w') as output_file:
                output_file.write(json.dumps({
                    "type": "FeatureCollection",
                    "features": all_polygons
                }, indent=2))
            processing.run("native:fixgeometries",
                           {'INPUT': output_polygons_layer_path,
                            'METHOD': 1, 'OUTPUT': fixed_polygon_layer_path})
            processing.run("native:dissolve", {'INPUT': QgsProcessingFeatureSourceDefinition(
                fixed_polygon_layer_path,
                selectedFeaturesOnly=False, featureLimit=-1,
                flags=QgsProcessingFeatureSourceDefinition.FlagOverrideDefaultGeometryCheck,
                geometryCheck=QgsFeatureRequest.GeometrySkipInvalid), 'FIELD': [], 'SEPARATE_DISJOINT': True,
                'OUTPUT': diss_polygon_layer_path})