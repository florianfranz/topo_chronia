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
            dem_path = os.path.join(self.output_folder_path, f"raster_{int(age)}_filled.tif")
        else:
            dem_path = os.path.join(self.output_folder_path, f"raster_{int(age)}_filled.tif")

        results = processing.run("native:rastersurfacevolume",
                                 {'BAND': 1,
                                  'INPUT': dem_path,
                                  'LEVEL': z,
                                  'METHOD': 1
                                  })
        volume = results["VOLUME"]
        volume = -volume
        return volume

    def adjust_sea_level(self, age, corrected):
        """
        Calculates the sea-level adjustment required to reach the reference oceanic volume.
        """
        ref_oc_volume = -self.etopo_volume
        z = 0
        # Coarse adjustment with 50m steps
        volume = self.calculate_volume(age, z, corrected)
        initial_volume = volume
        QgsMessageLog.logMessage(f"Initial volume is {initial_volume}", "Interpolate Raster", Qgis.Info)
        while volume > ref_oc_volume:
            z -= 50
            volume = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Decreasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        while volume < ref_oc_volume:
            z += 50
            volume = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Increasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)

        # Medium adjustment with 10m steps
        volume = self.calculate_volume(age, z, corrected)
        while volume > ref_oc_volume:
            z -= 10
            volume = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Decreasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        while volume < ref_oc_volume:
            z += 10
            volume = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Increasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)

        # Fine adjustment with 5m steps
        volume = self.calculate_volume(age, z, corrected)
        while volume > ref_oc_volume:
            z -= 5
            volume = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Decreasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        while volume < ref_oc_volume:
            z += 5
            volume = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Increasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)

        # Final adjustment with 1m steps
        volume = self.calculate_volume(age, z, corrected)
        while volume > ref_oc_volume:
            z -= 1
            volume = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Decreasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        while volume < ref_oc_volume:
            z += 1
            volume = self.calculate_volume(age, z, corrected)
            QgsMessageLog.logMessage(f"Increasing elevation to {z}, calculated volume: {volume}", "Interpolate Raster", Qgis.Info)
        QgsMessageLog.logMessage(f"final corrected z is {z}", "Interpolate Raster", Qgis.Info)
        sea_level = z

        return sea_level, initial_volume

    def update_all_nodes_wlc(self, z_water_load_corrected, age):
        """
        Updates the all nodes layer with the water load corrected elevation value.
        """
        output_folder_path = base_tools.get_layer_path("Output Folder")
        all_nodes_layer_path = os.path.join(output_folder_path, f"reproj_all_nodes_{int(age)}.geojson")
        all_nodes_layer = QgsVectorLayer(all_nodes_layer_path, f"All Nodes {int(age)}", "ogr")
        all_nodes_provider = all_nodes_layer.dataProvider()
        all_nodes_provider.addAttributes([QgsField('Z_WLC', QVariant.Double)])
        all_nodes_layer.updateFields()
        all_nodes_layer.commitChanges()

        field_idx_zwlc = all_nodes_layer.fields().indexOf('Z_WLC')
        with edit(all_nodes_layer):
            for node in all_nodes_layer.getFeatures():
                if node.attribute("Z"):
                    original_z = node.attribute('Z')
                    if original_z > z_water_load_corrected:
                        final_z = original_z
                    else:
                        final_z = original_z - z_water_load_corrected
                    all_nodes_layer.changeAttributeValue(node.id(), field_idx_zwlc, final_z)
                else:
                    pass
        all_nodes_layer.commitChanges()

    def correct_water_load_TM_simple(self,age):
        """
        Calculates the required sea-level adjustment and corrects for water load based on
        Airy model.
        """
        rho_m = 3300
        rho_w = 1027
        z_full_volume, initial_volume = self.adjust_sea_level(age, corrected=0)
        z_after_subsidence = (1 - (rho_w / rho_m)) * z_full_volume
        factor = 0.55*z_full_volume
        self.update_all_nodes_wlc(factor, age)
        output_file_path = os.path.join(self.output_folder_path, "water_load_correction_summary.txt")
        with open(output_file_path, 'a') as file:
            if file.tell() == 0:
                file.write("age, initial_volume, z_full_volume, z_after_subsidence, airy corrected sea level\n")
            file.write(f"{int(age)}, {initial_volume}, {z_full_volume},{z_after_subsidence}, {abs(factor)}\n")



