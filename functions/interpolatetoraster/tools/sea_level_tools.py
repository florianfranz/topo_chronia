import os
import processing
from qgis.core import QgsProject, Qgis, edit, QgsRasterLayer, QgsCoordinateReferenceSystem, QgsMessageLog, QgsVectorLayer,QgsField
from qgis.PyQt.QtCore import QVariant

from ...base_tools import BaseTools
base_tools = BaseTools()

class SeaLevel:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    old_TM_oceanic_volume_ref = -1333639062341560000
    PARAM_SL_OceanicVolume = -1336303570654071600 #Raster surface volume of ETOPO 2022 Ice Surface below z=0 (outside continents).
    TM_0_ref_volume = -1342794490468920000 #Updated 20.11.2024
    TM_0_ref_volume_TQ = -1313655214706870000
    TM_0_ref_volume_MIN = -1338960926044010000
    TM_0_ref_area = 509690400000000
    cpan_0_oceanic_volume = -1341988658050636000
    etopo_volume = -1336642930960120000 #Raster surface volume of ETOPO 2022 Ice Surface for entire Earth below z=0.
    etopo_area = 510061060208755 #Earth surface are in square meters

    def __init__(self):
        pass

    def calculate_volume(self,age,z,count):
        """
        Calculates the volume under a given z value.
        """
        if count == 0:
            dem_path = os.path.join(self.output_folder_path, f"qgis_tin_raster_{int(age)}.tif")
        else:
            dem_path = os.path.join(self.output_folder_path, f"raster_final_filled_{int(age)}.tif")

        results = processing.run("native:rastersurfacevolume",
                                 {'BAND': 1,
                                  'INPUT': dem_path,
                                  'LEVEL': z,
                                  'METHOD': 1
                                  })
        volume = results["VOLUME"]
        area = results["AREA"]
        volume = -volume
        return volume, area

    def adjust_sea_level(self, age, corrected):
        """
        Calculates the sea-level adjustment required to reach the reference oceanic volume.
        """
        ref_oc_volume = -self.etopo_volume
        z = 0
        # Coarse adjustment with 50m steps
        volume,area = self.calculate_volume(age, z, corrected)
        initial_volume = volume
        initial_area = area
        QgsMessageLog.logMessage(f"Initial volume is {initial_volume}", "Interpolate Raster", Qgis.Info)
        while volume > ref_oc_volume:
            z -= 50
            volume,area = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Decreasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        while volume < ref_oc_volume:
            z += 50
            volume,area = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Increasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)

        # Medium adjustment with 10m steps
        volume,area = self.calculate_volume(age, z, corrected)
        while volume > ref_oc_volume:
            z -= 10
            volume,area = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Decreasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        while volume < ref_oc_volume:
            z += 10
            volume,area = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Increasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)

        # Fine adjustment with 5m steps
        volume,area = self.calculate_volume(age, z, corrected)
        while volume > ref_oc_volume:
            z -= 5
            volume,area = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Decreasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        while volume < ref_oc_volume:
            z += 5
            volume,area = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Increasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)

        # Final adjustment with 1m steps
        volume,area = self.calculate_volume(age, z, corrected)
        while volume > ref_oc_volume:
            z -= 1
            volume,area = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Decreasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        while volume < ref_oc_volume:
            z += 1
            volume,area = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Increasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        QgsMessageLog.logMessage(f"final corrected z is {z}", "Interpolate Raster", Qgis.Info)
        sea_level = z

        return sea_level, area, initial_volume, initial_area


    def correct_water_load_newest(self,age):
        z_full_volume, area_full_volume, initial_volume, initial_area = self.adjust_sea_level(age, corrected=0)
        dSL, subsidence = self.update_all_nodes_wlc_newest(z_full_volume,age)
        output_file_path = os.path.join(self.output_folder_path, "water_load_correction_summary.txt")
        with open(output_file_path, 'a') as file:
            if file.tell() == 0:
                file.write("age, initial_volume, initial_area, z_full_volume, area_full_volume dSL, subsidence\n")
            file.write(f"{int(age)}, {initial_volume}, {initial_area}, {z_full_volume}, {area_full_volume}, {dSL}, {subsidence}\n")


    def update_all_nodes_wlc_newest(self, z_full_volume,age):
        output_folder_path = base_tools.get_layer_path("Output Folder")
        all_nodes_layer_path = os.path.join(output_folder_path, f"reproj_all_nodes_{int(age)}.geojson")
        rho_m = 3300
        rho_w = 1027
        dSL = ((rho_m - rho_w) * z_full_volume) / rho_m
        buoy_fac = (rho_m - rho_w) / rho_w
        subsidence = dSL / buoy_fac


        all_nodes_layer = QgsVectorLayer(all_nodes_layer_path, f"All Nodes {int(age)}", "ogr")
        all_nodes_provider = all_nodes_layer.dataProvider()
        all_nodes_provider.addAttributes([QgsField('Z_WLC', QVariant.Double),
                                          QgsField('DSL', QVariant.Double),
                                          QgsField('SUBS', QVariant.Double),
                                          QgsField('OWH', QVariant.Double)])

        all_nodes_layer.updateFields()
        all_nodes_layer.commitChanges()

        field_idx_zwlc = all_nodes_layer.fields().indexOf('Z_WLC')
        field_idx_dsl = all_nodes_layer.fields().indexOf('DSL')
        field_idx_subs = all_nodes_layer.fields().indexOf('SUBS')
        field_idx_owh = all_nodes_layer.fields().indexOf('OWH')
        with edit(all_nodes_layer):
            for node in all_nodes_layer.getFeatures():
                if node.attribute("Z"):
                    z_initial = node.attribute('Z')
                    if z_initial >= 0:
                        water_column = 0
                    else:
                        water_column = -z_initial
                    z_with_dSL = z_initial - dSL
                    if z_with_dSL >= 0:
                        subsidence_cor = 0
                        dSL_cor = 0
                    elif 0 > z_with_dSL >= -dSL:
                        subsidence_cor = z_with_dSL / buoy_fac
                        dSL_cor = - z_with_dSL
                    elif z_with_dSL < - dSL:
                        subsidence_cor = -subsidence
                        dSL_cor = -(z_with_dSL - z_initial)
                    else:
                        subsidence_cor = 45771972
                        dSL_cor = 894728
                    z_wlc = z_with_dSL + subsidence_cor
                    all_nodes_layer.changeAttributeValue(node.id(), field_idx_zwlc, z_wlc)
                    all_nodes_layer.changeAttributeValue(node.id(), field_idx_dsl, dSL_cor)
                    all_nodes_layer.changeAttributeValue(node.id(), field_idx_subs,-subsidence_cor)
                    all_nodes_layer.changeAttributeValue(node.id(), field_idx_owh, water_column)
        all_nodes_layer.commitChanges()
        return dSL, subsidence
