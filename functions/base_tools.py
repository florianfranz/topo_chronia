import json
import os
import platform
from qgis.core import Qgis, QgsVectorLayer, QgsRasterLayer, QgsProject, QgsMessageLog,QgsCoordinateReferenceSystem


class BaseTools:
    def __init__(self, input_fc=None):
        """
        Initialize BaseTools with optional input_fc dictionary.
        If input_fc is provided, use it directly. Otherwise, read from file.
        """
        self.input_fc = input_fc

        system_name = platform.system()
        if system_name in ["Darwin", "Linux"]:
            self.INPUT_FILE_PATH = os.path.expanduser("~/Desktop/input_files.txt")
        else:
            self.INPUT_FILE_PATH = "input_files.txt"

    def get_layer_path(self, target_layer_name):
        """
        Reads input file paths from the input file
        """
        try:
            with open(self.INPUT_FILE_PATH, "r") as file:
                file_paths = json.load(file)
        except FileNotFoundError:
            QgsMessageLog.logMessage(
                "Input files not yet defined, please configure it in the 'Check Configuration' initial step.",
                "Base Tools",
                Qgis.Warning
            )
            return None

        target_layer_path = file_paths.get(target_layer_name)

        if target_layer_path:
            QgsMessageLog.logMessage(
                f"Path to '{target_layer_name}': {target_layer_path}",
                "Base Tools",
                Qgis.Info
            )
            return target_layer_path
        else:
            QgsMessageLog.logMessage(
                f"Layer '{target_layer_name}' not found in the dictionary.",
                "Base Tools",
                Qgis.Warning
            )
            return None

    def get_relative_age(self, absolute_age):
        """
        Get the relative age based on the given absolute age.
        After International Chronographic Chart of December 2024
        International Commission on Stratigraphy
        https://stratigraphy.org/ICSchart/ChronostratChart2024-12.pdf
        """
        if absolute_age < 0.0117:
            return "Quaternary - Holocene"
        elif absolute_age < 0.129:
            return "Quaternary - Pleistocene (Upper)"
        elif absolute_age < 0.774:
            return "Quaternary - Pleistocene (Middle)"
        elif absolute_age < 1.80:
            return "Quaternary - Pleistocene (Calabrian)"
        elif absolute_age < 2.58:
            return "Quaternary - Pleistocene (Gelasian)"
        elif absolute_age < 3.6:
            return "Neogene - Pliocene (Piacenzian)"
        elif absolute_age < 5.333:
            return "Neogene - Pliocene (Zanclean)"
        elif absolute_age < 7.246:
            return "Neogene - Miocene (Messinian)"
        elif absolute_age < 11.63:
            return "Neogene - Miocene (Tortonian)"
        elif absolute_age < 13.82:
            return "Neogene - Miocene (Serravalian)"
        elif absolute_age < 15.98:
            return "Neogene - Miocene (Langhian)"
        elif absolute_age < 20.45:
            return "Neogene - Miocene (Burdigalian)"
        elif absolute_age < 23.04:
            return "Neogene - Miocene (Aquitanian)"
        elif absolute_age < 27.3:
            return "Palaeogene - Oligocene (Chattian)"
        elif absolute_age < 33.9:
            return "Palaeogene - Oligocene (Rupelian)"
        elif absolute_age < 37.71:
            return "Palaeogene - Eocene (Priabonian)"
        elif absolute_age < 41.03:
            return "Palaeogene - Eocene (Bartonian)"
        elif absolute_age < 48.07:
            return "Palaeogene - Eocene (Lutetian)"
        elif absolute_age < 56:
            return "Palaeogene - Eocene (Ypresian)"
        elif absolute_age < 59.24:
            return "Palaeogene - Palaeocene (Thanetian)"
        elif absolute_age < 61.66:
            return "Palaeogene - Palaeocene (Selandian)"
        elif absolute_age < 66:
            return "Palaeogene - Palaeocene (Danian)"
        elif absolute_age < 72.2:
            return "Cretaceous - Upper (Maastrichian)"
        elif absolute_age < 83.6:
            return "Cretaceous - Upper (Campanian)"
        elif absolute_age < 85.7:
            return "Cretaceous - Upper (Santonian)"
        elif absolute_age < 89.8:
            return "Cretaceous - Upper (Coniacian)"
        elif absolute_age < 93.9:
            return "Cretaceous - Upper (Turonian)"
        elif absolute_age < 100.5:
            return "Cretaceous - Upper (Cenomanian)"
        elif absolute_age < 113.2:
            return "Cretaceous - Lower (Albian)"
        elif absolute_age < 121.4:
            return "Cretaceous - Lower (Aptian)"
        elif absolute_age < 125.77:
            return "Cretaceous - Lower (Barremian)"
        elif absolute_age < 132.6:
            return "Cretaceous - Lower (Hauterivian)"
        elif absolute_age < 137.05:
            return "Cretaceous - Lower (Valanginian)"
        elif absolute_age < 143.1:
            return "Cretaceous - Lower (Berriasian)"
        elif absolute_age < 149.2:
            return "Jurassic - Upper (Tithonian)"
        elif absolute_age < 154.8:
            return "Jurassic - Upper (Kimmeridgian)"
        elif absolute_age < 161.5:
            return "Jurassic - Upper (Oxfordian)"
        elif absolute_age < 165.3:
            return "Jurassic - Middle (Callovian)"
        elif absolute_age < 168.2:
            return "Jurassic - Middle (Bathonian)"
        elif absolute_age < 170.9:
            return "Jurassic - Middle (Bajocian)"
        elif absolute_age < 174.7:
            return "Jurassic - Middle (Aalenian)"
        elif absolute_age < 184.2:
            return "Jurassic - Lower (Toarcian)"
        elif absolute_age < 192.9:
            return "Jurassic - Lower (Pliensbachian)"
        elif absolute_age < 199.5:
            return "Jurassic - Lower (Sinemurian)"
        elif absolute_age < 201.4:
            return "Jurassic - Lower (Hettangian)"
        elif absolute_age < 205.7:
            return "Triassic - Upper (Rhaetian)"
        elif absolute_age < 227.3:
            return "Triassic - Upper (Norian)"
        elif absolute_age < 237:
            return "Triassic - Upper (Carnian)"
        elif absolute_age < 241.464:
            return "Triassic - Middle (Ladinian)"
        elif absolute_age < 246.7:
            return "Triassic - Middle (Anisian)"
        elif absolute_age < 249.9:
            return "Triassic - Lower (Olenekian)"
        elif absolute_age < 251.902:
            return "Triassic - Lower (Induan)"
        elif absolute_age < 254.14:
            return "Permian - Lopingian (Changhsingian)"
        elif absolute_age < 259.51:
            return "Permian - Lopingian (Wuchiapingian)"
        elif absolute_age < 264.28:
            return "Permian - Guadalupian (Capitanian)"
        elif absolute_age < 266.9:
            return "Permian - Guadalupian (Wordian)"
        elif absolute_age < 274.4:
            return "Permian - Guadalupian (Roadian)"
        elif absolute_age < 283.3:
            return "Permian - Cisuralian (Kungurian)"
        elif absolute_age < 290.1:
            return "Permian - Cisuralian (Artinskian)"
        elif absolute_age < 293.52:
            return "Permian - Cisuralian (Sakmarian)"
        elif absolute_age < 298.9:
            return "Permian - Cisuralian (Asselian)"
        elif absolute_age < 303.7:
            return "Carboniferous - Pennsylvanian - Upper (Gzhelian)"
        elif absolute_age < 307:
            return "Carboniferous - Pennsylvanian - Upper (Kasimovian)"
        elif absolute_age < 315.2:
            return "Carboniferous - Pennsylvanian - Middle (Moscovian)"
        elif absolute_age < 323.4:
            return "Carboniferous - Pennsylvanian - Lower (Bashkirian)"
        elif absolute_age < 330.3:
            return "Carboniferous - Mississippian - Upper (Serpukhovian)"
        elif absolute_age < 346.7:
            return "Carboniferous - Mississippian - Middle (Visean)"
        elif absolute_age < 358.86:
            return "Carboniferous - Mississippian - Lower (Tournaisian)"
        elif absolute_age < 372.15:
            return "Devonian - Upper (Famenian)"
        elif absolute_age < 382.31:
            return "Devonian - Upper (Frasnian)"
        elif absolute_age < 387.95:
            return "Devonian - Middle (Givetian)"
        elif absolute_age < 393.47:
            return "Devonian - Middle (Eifelian)"
        elif absolute_age < 410.62:
            return "Devonian - Lower (Emsian)"
        elif absolute_age < 413.02:
            return "Devonian - Lower (Pragian)"
        elif absolute_age < 419.62:
            return "Devonian - Lower (Lochkovian)"
        elif absolute_age < 422.7:
            return "Silurian - Pridoli"
        elif absolute_age < 425:
            return "Silurian - Ludlow (Ludfordian)"
        elif absolute_age < 426.7:
            return "Silurian - Ludlow (Gorstian)"
        elif absolute_age < 430.6:
            return "Silurian - Wenlock (Homerian)"
        elif absolute_age < 432.9:
            return "Silurian - Wenlock (Sheinwoodian)"
        elif absolute_age < 438.6:
            return "Silurian - Llandovery (Telychian)"
        elif absolute_age < 440.5:
            return "Silurian - Llandovery (Aeronian)"
        elif absolute_age < 443.1:
            return "Silurian - Llandovery (Rhuddanian)"
        elif absolute_age < 445.2:
            return "Ordovician - Upper (Hirnantian)"
        elif absolute_age < 452.8:
            return "Ordovician - Upper (Katian)"
        elif absolute_age < 458.2:
            return "Ordovician - Upper (Sandbian)"
        elif absolute_age < 469.4:
            return "Ordovician - Middle (Darriwilian)"
        elif absolute_age < 471.3:
            return "Ordovician - Middle (Dapingian)"
        elif absolute_age < 477.1:
            return "Ordovician - Lower (Floian)"
        elif absolute_age < 486.85:
            return "Ordovician - Lower (Tremadocian)"
        elif absolute_age < 491:
            return "Cambrian - Furongian (Stage 10)"
        elif absolute_age < 494.2:
            return "Cambrian - Furongian (Jiangshanian)"
        elif absolute_age < 497:
            return "Cambrian - Furongian (Paibian)"
        elif absolute_age < 500.5:
            return "Cambrian - Miaolingian (Guzhangian)"
        elif absolute_age < 504.5:
            return "Cambrian - Miaolingian (Drumian)"
        elif absolute_age < 506.5:
            return "Cambrian - Miaolingian (Wuliuan)"
        elif absolute_age < 514.5:
            return "Cambrian - Series 2 (Stage 4)"
        elif absolute_age < 521:
            return "Cambrian - Series 2 (Stage 3)"
        elif absolute_age < 529:
            return "Cambrian - Terreneuvian (Stage 2)"
        elif absolute_age < 538.8:
            return "Cambrian - Terreneuvian (Fortunian)"
        elif absolute_age < 635:
            return "Ediacarian"
        elif absolute_age < 720:
            return "Cryogenian"
        elif absolute_age < 1000:
            return "Tonian"
        elif absolute_age < 1200:
            return "Stenian"
        elif absolute_age < 1400:
            return "Ectasian"
        elif absolute_age < 1600:
            return "Calymmian"
        elif absolute_age < 1800:
            return "Statherian"
        elif absolute_age < 2050:
            return "Orosirian"
        elif absolute_age < 2300:
            return






