import os
import processing
from qgis.core import QgsVectorLayer,QgsFeatureRequest,QgsMessageLog, Qgis,QgsProject, QgsProcessingException

from ...base_tools import BaseTools
base_tools = BaseTools()


class PreRasterTools:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")
    plate_polygons_path = base_tools.get_layer_path("Plate Polygons")
    plate_polygons_layer = QgsVectorLayer(plate_polygons_path, "Plate Polygons", 'ogr')
    APPEARANCE = "APPEARANCE"
    PLATE = "PLATE"

    def __init__(self):
        pass

    def generate_temporary_raster_plate_by_plate(self, age):
        """
        Generates the preliminary raster based on the all nodes layer,
        comprising only RID + ISO nodes.
        """
        nodes_layer_path = os.path.join(self.output_folder_path,
                                        f"all_nodes_{int(age)}.geojson")

        nodes_layer = QgsVectorLayer(nodes_layer_path,
                                     "Nodes",
                                     "ogr")
        attributes = nodes_layer.fields().toList()

        plate_filter = f"{self.APPEARANCE} = {age}"
        plate_features = list(
            self.plate_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_filter)))
        for plate in plate_features:
            plate_name_or = plate.attribute("PLATE")

            # Rename specific plates
            plate_name_mappings = {
                "Nazca": "NAZ",
                "Tong_Ker": "TONGA_KER",
                "Fiji_N": "FIDJI_N",
                "Fiji_E": "FIDJI_E",
                "Fiji_W": "FIDJI_W",
                "Carolina": "CAROLINE",
                "India": "IND",
                "Easter": "EAST",
                "Gondwana": "GOND",
                "NixonFord": "NIXFORD",
                "Sinti-Holo": "SINTIHOLO",
                "Laurentia": "LAURUSSIA"
            }

            plate_name = plate_name_mappings.get(plate_name_or,
                                                 plate_name_or.upper())  # Default to uppercase if not mapped


            bbox = plate.geometry().boundingBox()

            # **First Condition:** Select nodes where PLATE = plate_name
            plate_name_filter = f"{self.PLATE} = '{plate_name}'"
            nodes_plate = list(nodes_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_name_filter)))

            # **Second Condition:** Select nodes where PLATE = "Z_DEM" AND they intersect the plate polygon
            z_dem_filter = f"{self.PLATE} = 'Z_DEM'"
            nodes_z_dem = [
                node for node in nodes_layer.getFeatures(QgsFeatureRequest().setFilterExpression(z_dem_filter))
                if node.geometry().intersects(plate.geometry())  # Check intersection
            ]

            # **Combine both lists**
            nodes_features = nodes_plate + nodes_z_dem
            if len(nodes_features) == 0:
                pass
            else:
                plate_nodes_layer = QgsVectorLayer("Point?crs=EPSG:4326", f"Nodes_{plate_name}_{age}", "memory")
                provider = plate_nodes_layer.dataProvider()
                plate_nodes_layer.startEditing()
                provider.addAttributes(attributes)
                provider.addFeatures(nodes_features)
                plate_nodes_layer.commitChanges()
                QgsProject.instance().addMapLayer(plate_nodes_layer)

                self.perform_prelim_raster_interpolation_plate_by_plate(plate_nodes_layer,
                                                                        plate_name_or,
                                                                        bbox,
                                                                        age)
                QgsProject.instance().removeMapLayer(plate_nodes_layer)

        age_output_folder = os.path.join(self.output_folder_path, str(int(age)))
        self.create_mosaic_from_rasters(age_output_folder,age)

    def create_mosaic_from_rasters(self, output_folder,age):
        filled_output_raster_path = os.path.join(self.output_folder_path,
                                                  f"qgis_tin_raster_prelim_{int(age)}.tif")
        raster_files = []

        # Walk through the directory structure
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                # Check if the file is a .tif (or other raster formats like .jpg, .png)
                if file.endswith('clipped.tif'):
                    # Append the full file path to the raster_files list
                    raster_files.append(os.path.join(root, file))

        if not raster_files:
            QgsMessageLog.logMessage("No rasters found in the output folder.", "Create Node Grid", Qgis.Warning)
            return

        # Create the mosaic output path
        mosaic_output_path = os.path.join(output_folder, "mosaic_output_prelim.tif")

        # Run the "gdal:merge" algorithm to merge all the rasters
        processing.run("gdal:merge", {
            'INPUT': raster_files,
            'PCT': False,
            'SEAMLINE': None,
            'NODATA_INPUT': None,
            'NODATA_OUTPUT': -9999,
            'OUTPUT': mosaic_output_path
        })

        processing.run("gdal:fillnodata", {
            'INPUT': mosaic_output_path,
            'BAND': 1,
            'DISTANCE': 10,
            'ITERATIONS': 1,
            'MASK_LAYER': None,
            'OPTIONS': '', 'EXTRA': '',
            'OUTPUT': filled_output_raster_path})

    def perform_prelim_raster_interpolation_plate_by_plate(self,
                                                           plate_nodes_layer,
                                                           plate_name,
                                                           plate_extent,
                                                           age):
        """
        Performs a TIN interpolation and fills no data cells for the preliminary raster.
        """
        plate_nodes_layer_source = plate_nodes_layer.source()
        interpolation_data = f"{plate_nodes_layer_source}::~::0::~::3::~::0"
        QgsMessageLog.logMessage(f"interpolation_data: {interpolation_data}")
        # Define the output folder structure: output/age/plate_name
        age_output_folder = os.path.join(self.output_folder_path, str(int(age)))  # Convert age to string
        plate_output_folder = os.path.join(age_output_folder, plate_name)
        QgsMessageLog.logMessage(f"plate extent: {plate_extent} ")
        # Create the folders if they don’t exist
        os.makedirs(plate_output_folder, exist_ok=True)

        qgis_tin_raster_path = os.path.join(plate_output_folder, f"qgis_tin_prelim_{int(age)}.tif")

        processing.run("qgis:tininterpolation", {
            'INTERPOLATION_DATA': interpolation_data,
            'METHOD': 0,
            'EXTENT': plate_extent,
            'PIXEL_SIZE': 0.1,
            'OUTPUT': qgis_tin_raster_path,
        })

        plate_name_filter = ( f"{self.APPEARANCE} = {age} AND " f"({self.PLATE} = '{plate_name}')")
        plate_attributes = self.plate_polygons_layer.fields().toList()
        plate_features = self.plate_polygons_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_name_filter))
        plate_polygon_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", f"Polygon_{plate_name}_{age}", "memory")
        pol_provider = plate_polygon_layer.dataProvider()
        plate_polygon_layer.startEditing()
        pol_provider.addAttributes(plate_attributes)
        pol_provider.addFeatures(plate_features)
        plate_polygon_layer.commitChanges()
        QgsProject.instance().addMapLayer(plate_polygon_layer)
        clipped_raster_path = os.path.join(plate_output_folder, f"qgis_tin_prelim_{int(age)}_clipped.tif")

        # Clip raster using plate polygon
        processing.run("gdal:cliprasterbymasklayer", {
            'INPUT': qgis_tin_raster_path,  # The interpolated raster
            'MASK': plate_polygon_layer,  # The polygon to clip with
            'SOURCE_CRS': None,  # Use input raster CRS
            'TARGET_CRS': None,  # Keep CRS the same
            'NODATA': -9999,  # NoData value
            'CROP_TO_CUTLINE': True,  # Crop to the polygon boundary
            'KEEP_RESOLUTION': True,  # Keep original resolution
            'OUTPUT': clipped_raster_path,
        })
        QgsProject.instance().removeMapLayer(plate_polygon_layer)

    def generate_temporary_raster(self, age):
        """
        Generates the preliminary raster based on the all nodes layer,
        comprising only RID + ISO nodes.
        """
        nodes_layer_path = os.path.join(self.output_folder_path,
                                        f"all_nodes_{int(age)}.geojson")

        nodes_layer = QgsVectorLayer(nodes_layer_path,
                                     "Nodes",
                                     "ogr")

        self.perform_prelim_raster_interpolation(nodes_layer,
                                          age)


    def perform_prelim_raster_interpolation(self,
                                     nodes_layer,
                                     age):
        """
        Performs a TIN interpolation and fills no data cells for the preliminary raster.
        """
        qgis_tin_unfilled_output_raster_path = os.path.join(self.output_folder_path,
                                                  f"qgis_tin_raster_unfilled_prelim_{int(age)}.tif")
        qgis_tin_output_raster_path = os.path.join(self.output_folder_path,
                                                  f"qgis_tin_raster_prelim_{int(age)}.tif")

        processing.run("qgis:tininterpolation", {
            'INTERPOLATION_DATA': f"{nodes_layer.source()}::~::0::~::3::~::0",
            'METHOD': 0,
            'EXTENT': '-180,180,-90,90 [EPSG:4326]',
            'PIXEL_SIZE': 0.1,
            'OUTPUT': qgis_tin_unfilled_output_raster_path,
        })
        processing.run("gdal:fillnodata", {
            'INPUT': qgis_tin_unfilled_output_raster_path,
            'BAND': 1,
            'DISTANCE': 100,
            'ITERATIONS': 3,
            'MASK_LAYER': None,
            'OPTIONS': '', 'EXTRA': '',
            'OUTPUT': qgis_tin_output_raster_path})

