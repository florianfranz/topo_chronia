import os
import processing
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject,
                       QgsMessageLog,QgsCoordinateReferenceSystem,QgsProcessingFeatureSourceDefinition,
                       QgsPointXY,QgsGeometry, QgsSpatialIndex)


from ...base_tools import BaseTools
base_tools = BaseTools()

class RasterTools:
    plate_polygons_path = base_tools.get_layer_path("Plate Polygons")
    plate_polygons_layer = QgsVectorLayer(plate_polygons_path, "Plate Polygons", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    PLATE = "PLATE"
    def __init__(self):
        pass

    def perform_final_raster_interpolation(self,age):
        """
        Performs the final raster interpolation with QGIS TIN method, with the water load
        corrected elevation values.
        """
        output_folder_path = base_tools.get_layer_path("Output Folder")
        reproj_nodes_layer_path = os.path.join(output_folder_path, f"reproj_all_nodes_{int(age)}.geojson")

        reproj_nodes_layer = QgsVectorLayer(reproj_nodes_layer_path, "Nodes", "ogr")
        final_raster_path = os.path.join(output_folder_path, f"raster_final_{int(age)}.tif")
        final_filled_raster_path = os.path.join(output_folder_path, f"raster_final_filled_{int(age)}.tif")

        processing.run("qgis:tininterpolation", {
            'INTERPOLATION_DATA': f'{reproj_nodes_layer.source()}::~::0::~::6::~::0',
            'METHOD': 0,
            'EXTENT': '-20037505.459500000,20037505.424600001,-6360516.244100000,6363880.960000000 [ESRI:54034]',
            'PIXEL_SIZE': 10000, 'OUTPUT': final_raster_path})

        processing.run("gdal:fillnodata", {
            'INPUT': final_raster_path,
            'BAND': 1,
            'DISTANCE': 150,
            'ITERATIONS': 3,
            'MASK_LAYER': None,
            'OPTIONS': '', 'EXTRA': '',
            'OUTPUT': final_filled_raster_path})

    def fix_longitude(self):
        """Ensure all longitude values stay within [-180, 180]."""
        with edit(self.plate_polygons_layer):  # Start editing
            for feature in self.plate_polygons_layer.getFeatures():
                geom = feature.geometry()
                if geom.isNull():
                    pass
                else:
                    if geom.isMultipart():  # If it's a MultiPolygon
                        new_coords = []
                        for polygon in geom.asMultiPolygon():
                            fixed_polygon = []
                            for ring in polygon:
                                fixed_ring = [
                                    QgsPointXY(
                                        max(-180, min(180, point.x())),  # Clamp longitude
                                        point.y()
                                    ) for point in ring
                                ]
                                fixed_polygon.append(fixed_ring)
                            new_coords.append(fixed_polygon)
                        new_geom = QgsGeometry.fromMultiPolygonXY(new_coords)
                    else:  # If it's a single Polygon
                        new_coords = []
                        for ring in geom.asPolygon():
                            fixed_ring = [
                                QgsPointXY(
                                    max(-180, min(180, point.x())),  # Clamp longitude
                                    point.y()
                                ) for point in ring
                            ]
                            new_coords.append(fixed_ring)
                        new_geom = QgsGeometry.fromPolygonXY(new_coords)

                    # Update the feature geometry
                    self.plate_polygons_layer.changeGeometry(feature.id(), new_geom)

    def reproject_plate_polygons(self,age):
        self.fix_longitude()
        reproj_plates_path = os.path.join(self.output_folder_path, f"reproj_plate_polygons_{int(age)}.geojson")
        fixed_reproj_plates_path = reproj_plates_path.replace('.geojson','fixed.geojson')
        buffer_pos_path = reproj_plates_path.replace('.geojson','buff_pos.geojson')
        buffer_neg_path = reproj_plates_path.replace('.geojson','buff_neg.geojson')

        processing.run("native:reprojectlayer", {'INPUT': QgsProcessingFeatureSourceDefinition(
            self.plate_polygons_path , selectedFeaturesOnly=False,
            featureLimit=-1, filterExpression=f' "APPEARANCE" = {age} ',
            geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid),
                                                 'TARGET_CRS': QgsCoordinateReferenceSystem('ESRI:54034'),
                                                 'CONVERT_CURVED_GEOMETRIES': False,
                                                 'OPERATION': '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=cea +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84',
                                                 'OUTPUT': reproj_plates_path})

        processing.run("native:fixgeometries", {
            'INPUT': reproj_plates_path,
            'METHOD': 1, #Keep Structure rather than line work.
            'OUTPUT': fixed_reproj_plates_path})

        processing.run("native:buffer", {
            'INPUT': fixed_reproj_plates_path,
            'DISTANCE': 50000, 'SEGMENTS': 5, 'END_CAP_STYLE': 0, 'JOIN_STYLE': 0, 'MITER_LIMIT': 2, 'DISSOLVE': True,
            'SEPARATE_DISJOINT': False, 'OUTPUT': buffer_pos_path})

        processing.run("native:buffer", {
            'INPUT': buffer_pos_path,
            'DISTANCE': -50000, 'SEGMENTS': 5, 'END_CAP_STYLE': 0, 'JOIN_STYLE': 0, 'MITER_LIMIT': 2, 'DISSOLVE': True,
            'SEPARATE_DISJOINT': False, 'OUTPUT': buffer_neg_path})
        return buffer_neg_path


    def generate_raster_all_in_one(self,age):
        nodes_layer_path = os.path.join(self.output_folder_path,
                                        f"all_nodes_{int(age)}.geojson")
        reproj_nodes_layer_path = os.path.join(self.output_folder_path, f"reproj_all_nodes_{int(age)}.geojson")

        nodes_layer = QgsVectorLayer(nodes_layer_path,
                                     "Nodes",
                                     "ogr")
        attributes = nodes_layer.fields().toList()

        processing.run("native:reprojectlayer",
                       {'INPUT': nodes_layer.source(),
                        'TARGET_CRS': QgsCoordinateReferenceSystem('ESRI:54034'), 'CONVERT_CURVED_GEOMETRIES': False,
                        'OPERATION': '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=cea +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84',
                        'OUTPUT': reproj_nodes_layer_path})

        reproj_nodes_layer = QgsVectorLayer(reproj_nodes_layer_path,
                                            "Reproj Nodes",
                                            "ogr")
        qgis_tin_unfilled_raster_path = os.path.join(self.output_folder_path, f"qgis_tin_unfilled_{int(age)}.tif")
        qgis_tin_raster_path = os.path.join(self.output_folder_path, f"qgis_tin_raster_{int(age)}.tif")


        processing.run("qgis:tininterpolation", {
            'INTERPOLATION_DATA': f"{reproj_nodes_layer.source()}::~::0::~::3::~::0",
            'METHOD': 0,
            'EXTENT': '-20037508.4268000014126301,20045909.1961000002920628,-6372972.0028000036254525,6368285.1716000000014901 [ESRI:54034]',
            'PIXEL_SIZE': 10000,
            'OUTPUT': qgis_tin_unfilled_raster_path,
        })

        processing.run("gdal:fillnodata", {
            'INPUT': qgis_tin_unfilled_raster_path,
            'BAND': 1,
            'DISTANCE': 150,
            'ITERATIONS': 3,
            'MASK_LAYER': None,
            'OPTIONS': '', 'EXTRA': '',
            'OUTPUT': qgis_tin_raster_path})


    def generate_raster_plate_by_plate(self, age):
        """
        Generates the raster based on the all nodes layer"""

        reproj_plates_path = self.reproject_plate_polygons(age)
        reproj_plates_polygons = QgsVectorLayer(reproj_plates_path, "Reproj Plates", "ogr")
        nodes_layer_path = os.path.join(self.output_folder_path,
                                        f"all_nodes_{int(age)}.geojson")
        reproj_nodes_layer_path = os.path.join(self.output_folder_path, f"reproj_all_nodes_{int(age)}.geojson")

        nodes_layer = QgsVectorLayer(nodes_layer_path,
                                     "Nodes",
                                     "ogr")
        attributes = nodes_layer.fields().toList()


        processing.run("native:reprojectlayer",
                       {'INPUT': nodes_layer.source(),
                        'TARGET_CRS': QgsCoordinateReferenceSystem('ESRI:54034'), 'CONVERT_CURVED_GEOMETRIES': False,
                        'OPERATION': '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=cea +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84',
                        'OUTPUT': reproj_nodes_layer_path})

        reproj_nodes_layer = QgsVectorLayer(reproj_nodes_layer_path,
                                            "Reproj Nodes",
                                            "ogr")


        for plate in reproj_plates_polygons.getFeatures():
            plate_name_or = plate.attribute("PLATE")

            # Rename specific plates - Plate:Nodes
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
            distance_threshold = 0.05

            # **First Condition:** Select nodes where PLATE = plate_name
            plate_name_filter = f"{self.PLATE} = '{plate_name}'"
            nodes_plate = list(reproj_nodes_layer.getFeatures(QgsFeatureRequest().setFilterExpression(plate_name_filter)))

            # **Second Condition:** Select nodes where PLATE = "Z_DEM" AND they intersect the plate polygon
            z_dem_filter = ( f"{self.PLATE} = 'Z_DEM' OR " f"({self.PLATE} = 'UNDEFINED')")
            nodes_z_dem = [
                node for node in reproj_nodes_layer.getFeatures(QgsFeatureRequest().setFilterExpression(z_dem_filter))
                if node.geometry().intersects(plate.geometry())  # Check intersection
            ]
            nodes_other = []
            # Third condition: Select nodes that intersect the PLATE (necessary as some feature sin the PM have wrong plate names).
            other_filter = ( f"{self.PLATE} != 'Z_DEM' OR " f"({self.PLATE} != 'UNDEFINED') OR " f"({self.PLATE} != '{plate_name}')")
            spatial_index_other = QgsSpatialIndex(
                reproj_nodes_layer.getFeatures(QgsFeatureRequest().setFilterExpression(other_filter))
                )
            candidate_ids_other = spatial_index_other.intersects(bbox)
            if candidate_ids_other:
                for candidate_id in candidate_ids_other:
                    node_feature = reproj_nodes_layer.getFeature(candidate_id)
                    if node_feature.geometry().intersects(plate.geometry()):
                        nodes_other.append(node_feature)


            # **Combine both lists**
            nodes_features = nodes_plate + nodes_z_dem + nodes_other
            if len(nodes_features) == 0:
                pass
            else:
                plate_nodes_layer = QgsVectorLayer("Point?crs=ESRI:54034", f"Nodes_{plate_name}_{age}", "memory")
                provider = plate_nodes_layer.dataProvider()
                plate_nodes_layer.startEditing()
                provider.addAttributes(attributes)
                provider.addFeatures(nodes_features)
                plate_nodes_layer.commitChanges()
                QgsProject.instance().addMapLayer(plate_nodes_layer)

                self.perform_raster_interpolation_plate_by_plate(reproj_plates_polygons,
                                                                 plate_nodes_layer,
                                                                 plate_name_or,
                                                                 bbox,
                                                                 age)
                QgsProject.instance().removeMapLayer(plate_nodes_layer)

        age_output_folder = os.path.join(self.output_folder_path, str(int(age)))
        self.create_mosaic_from_rasters(age_output_folder,age)

    def create_mosaic_from_rasters(self, output_folder,age):
        filled_output_raster_path = os.path.join(self.output_folder_path,
                                                  f"qgis_tin_raster_{int(age)}.tif")
        raster_files = []

        for root, dirs, files in os.walk(output_folder):
            for file in files:
                if file.endswith(f"tin_{int(age)}_clipped.tif"):
                    raster_files.append(os.path.join(root, file))

        if not raster_files:
            QgsMessageLog.logMessage("No rasters found in the output folder.", "Create Node Grid", Qgis.Warning)
            return

        mosaic_output_path = os.path.join(output_folder, "mosaic_output.tif")

        processing.run("gdal:merge", {
            'INPUT': raster_files,
            'PCT': False,
            'SEAMLINE': None,
            'NODATA_INPUT': None,
            'NODATA_OUTPUT': -9999,
            'OUTPUT': mosaic_output_path
        })

        QgsMessageLog.logMessage(f"Mosaic created at {mosaic_output_path}", "Create Node Grid", Qgis.Info)

        processing.run("gdal:fillnodata", {
            'INPUT': mosaic_output_path,
            'BAND': 1,
            'DISTANCE': 150,
            'ITERATIONS': 3,
            'MASK_LAYER': None,
            'OPTIONS': '', 'EXTRA': '',
            'OUTPUT': filled_output_raster_path})


    def perform_raster_interpolation_plate_by_plate(self,
                                                    reprojected_plates_polygons,
                                                    plate_nodes_layer,
                                                    plate_name,
                                                    plate_extent,
                                                    age):
        """
        Performs a TIN interpolation and fills no data cells for the raster.
        """

        # Define the output folder structure: output/age/plate_name
        age_output_folder = os.path.join(self.output_folder_path, str(int(age)))  # Convert age to string
        plate_output_folder = os.path.join(age_output_folder, plate_name)

        # Create the folders if they don’t exist
        os.makedirs(plate_output_folder, exist_ok=True)

        qgis_tin_raster_path = os.path.join(plate_output_folder, f"qgis_tin_{int(age)}.tif")

        processing.run("qgis:tininterpolation", {
            'INTERPOLATION_DATA': f"{plate_nodes_layer.source()}::~::0::~::3::~::0",
            'METHOD': 0,
            'EXTENT': plate_extent,
            'PIXEL_SIZE': 10000,
            'OUTPUT': qgis_tin_raster_path,
        })
        plate_name_filter = ( f"{self.APPEARANCE} = {age} AND " f"({self.PLATE} = '{plate_name}')")
        plate_attributes = reprojected_plates_polygons.fields().toList()
        plate_features = reprojected_plates_polygons.getFeatures(QgsFeatureRequest().setFilterExpression(plate_name_filter))
        plate_polygon_layer = QgsVectorLayer("Polygon?crs=ESRI:54034", f"Polygon_{plate_name}_{age}", "memory")
        pol_provider = plate_polygon_layer.dataProvider()
        plate_polygon_layer.startEditing()
        pol_provider.addAttributes(plate_attributes)
        pol_provider.addFeatures(plate_features)
        plate_polygon_layer.commitChanges()
        QgsProject.instance().addMapLayer(plate_polygon_layer)

        clipped_raster_path = os.path.join(plate_output_folder, f"qgis_tin_{int(age)}_clipped.tif")

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
