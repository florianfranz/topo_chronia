import os
import math
import processing
import json
from qgis.core import (Qgis, edit, QgsPoint, QgsMessageLog, QgsFeatureRequest, QgsMultiPoint, QgsGeometry, QgsPointXY,
                       QgsVectorLayer, QgsFeature, QgsVectorFileWriter, QgsProject, QgsSpatialIndex, QgsRectangle,
                       QgsField, QgsProcessingFeatureSourceDefinition)

from qgis.PyQt.QtCore import QVariant

try:
    import geopy
    has_geopy = True
    from geopy.distance import geodesic, great_circle
    from geopy.point import Point

except Exception:
    has_geopy = False

from ...base_tools import BaseTools
base_tools = BaseTools()

from .velocity_data import velocity_dict


class FeatureConversionTools:
    INPUT_FILE_PATH = "input_files.txt"
    plate_polygons_path = base_tools.get_layer_path("Plate Polygons")
    plate_polygons_layer = QgsVectorLayer(plate_polygons_path, "Plate Polygons", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")
    APPEARANCE = "APPEARANCE"
    def __init__(self):
        pass


    def get_ridge_depth(self,age):
        """
        Calculates ridge depth based on values from the velocity dictionary.
        """
        velocity = velocity_dict.get(str(int(age)))

        if velocity is None:
            raise ValueError(f"Velocity data not found for age: {age}")

        ridge_depth = -2835  # default value is -2870 but old nodes show -2835
        ridge_depth = -3.541697688 * (velocity - 27.4810932747379) + ridge_depth

        return ridge_depth

    def DI2xyz(self, point, r):
        """
        Converts a point from spherical coordinates (longitude, latitude) and a
        given radius to Cartesian (x, y, z) coordinates.
        """
        dec = point.x()
        inc = point.y()
        x = r * math.cos(math.radians(dec)) * math.cos(math.radians(inc))
        y = r * math.sin(math.radians(dec)) * math.cos(math.radians(inc))
        z = r * math.sin(math.radians(inc))
        return x, y, z

    def xyz2DI(self, x, y, z):
        """
        Converts Cartesian (x, y, z) coordinates to spherical coordinates, returning
        the radius, declination (longitude), and inclination (latitude).
        """
        r = math.sqrt(x ** 2 + y ** 2 + z ** 2)
        condition = math.sqrt(x ** 2 + y ** 2)
        if condition == 0:
            dec = 0
        else:
            dec = math.degrees(math.acos(x / condition))
            if y < 0:
                dec = -dec
        if r == 0:
            inc = 0
        else:
            inc = math.degrees(math.asin(z / r))
        R = r
        return  r, dec, inc

    def clean_nodes(self,age):
        """
        Checks nodes from each setting against others inside the all nodes layer.
        """
        all_nodes_layer_path = os.path.join(self.output_folder_path, f"all_nodes_{int(age)}.geojson")
        all_nodes_layer = QgsVectorLayer(all_nodes_layer_path, "All nodes", "ogr")
        settings = ["RID", "ISO", "LWS", "ABA", "PMW", "CTN", "CRA", "OTM", "PMC", "RIB", "UPS", "COL", "HOT"]
        param = "TYPE"

        nodes_to_delete = []
        for setting in settings:
            distance_threshold = 0.5
            settings_to_check = []
            expression_setting = f"{param} = '{setting}'"
            index = settings.index(setting)
            settings_to_check = settings[:index]
            if setting == "RID":
                settings_to_check = []
            elif setting == "ISO":
                settings_to_check = ["PMW", "HOT"]
                distance_threshold = 1.5
            elif setting == "CTN":
                settings_to_check = ["RID", "ISO", "LWS", "ABA", "PMW", "CRA", "OTM", "PMC", "RIB", "UPS", "COL", "HOT"]
            elif setting == "CRA":
                settings_to_check.remove("CTN")
            elif setting == "RIB":
                settings_to_check.remove("CTN")
                settings_to_check.remove("PMW")
            elif setting == "PMW":
                settings_to_check.remove("ISO")
                settings_to_check.append("RIB")
            elif setting == "HOT":
                settings_to_check = ["PMC", "PMW"]
                distance_threshold = 0.5
            if settings_to_check:
                values = "','".join(settings_to_check)
                expression_to_check_against =f"{param} IN ('{values}')"
                QgsMessageLog.logMessage(f"{expression_to_check_against}")
                selected_features = list(
                    all_nodes_layer.getFeatures(QgsFeatureRequest().setFilterExpression(expression_to_check_against)))
                QgsMessageLog.logMessage(f"selected features : {len(selected_features)}")
                spatial_index_other = QgsSpatialIndex(all_nodes_layer.getFeatures(QgsFeatureRequest().setFilterExpression(expression_to_check_against))
                )
                for feature in all_nodes_layer.getFeatures(QgsFeatureRequest().setFilterExpression(expression_setting)):
                    geometry = feature.geometry()
                    if feature.attribute("TYPE") == "COL" and feature.attribute("FEAT_AGE") > 330:
                        nodes_to_delete.append(feature.id())
                    bbox = geometry.boundingBox()
                    candidate_ids_other = spatial_index_other.intersects(bbox.buffered(distance_threshold))
                    for candidate_id in candidate_ids_other:
                        feature_other = all_nodes_layer.getFeature(candidate_id)
                        geometry_other = feature_other.geometry()
                        distance = geometry.distance(geometry_other)
                        if distance <= distance_threshold:
                            if feature.id() not in nodes_to_delete:
                                nodes_to_delete.append(feature.id())
        QgsMessageLog.logMessage(f"Nodes to delete: {len(nodes_to_delete)}")
        if nodes_to_delete:
            with edit(all_nodes_layer):
                all_nodes_layer.dataProvider().deleteFeatures(nodes_to_delete)
            all_nodes_layer.commitChanges()


    def cut_entire_profile(self,profile_geometry, polygon_layer):
        """
        Checks if a profile intersects a polygon. If yes, cuts the
        entire profile.
        """
        intersects = False
        spatial_index = QgsSpatialIndex()
        for feature in polygon_layer.getFeatures():
            spatial_index.addFeature(feature)

        candidate_ids = spatial_index.intersects(profile_geometry.boundingBox())
        if candidate_ids:
            for candidate_id in candidate_ids:
                polygon_feature = next(
                    polygon_layer.getFeatures(QgsFeatureRequest(candidate_id)))
                continent_geom = polygon_feature.geometry()
                if continent_geom.intersects(profile_geometry):
                    intersects = True
                    break
        if intersects:
            return True
        else:
            return False

    def cut_profile_spi(self, profile_geometry, polygon_layer, status, location, age,same_setting=False):
        """
        Iterates through each point of a profile. Depending on the condition (keep inside or keep outside),
        the profile is cut and returned when the condition is no longer met. This function is based on
        spatial index (spi) to speed up the processing.
        """
        cut_profile = QgsMultiPoint()
        profile_points = profile_geometry.asMultiPoint()
        if status == "keep inside":
            buffer_distance = 0.2
        else:
            buffer_distance = 0.05

        # Create a spatial index for the polygon features
        if same_setting == True:
            spatial_index = QgsSpatialIndex()
            for feature in polygon_layer.getFeatures():
                spatial_index.addFeature(feature)
        elif same_setting == False:
            continent_filter = f"{self.APPEARANCE} = {age}"
            spatial_index = QgsSpatialIndex(
                polygon_layer.getFeatures(QgsFeatureRequest().setFilterExpression(continent_filter))
            )

        if location == "negative":
            if status == "keep inside":
                for point in profile_points[::-1]:
                    point_geometry = QgsGeometry.fromPointXY(point)
                    # Use spatial index to find nearby polygons
                    intersecting_features = spatial_index.intersects(point_geometry.boundingBox())
                    for feature_id in intersecting_features:
                        feature = polygon_layer.getFeature(feature_id)  # Retrieve the feature by its ID
                        if feature.geometry().buffer(-buffer_distance, 5).intersects(point_geometry):
                            cut_profile.addGeometry(QgsPoint(point))
                        else:
                            return QgsGeometry(cut_profile)
            elif status == "keep outside":
                for point in profile_points[::-1]:
                    point_geometry = QgsGeometry.fromPointXY(point)
                    intersects = False
                    # Use spatial index to find nearby polygons
                    intersecting_features = spatial_index.intersects(point_geometry.boundingBox())
                    for feature_id in intersecting_features:
                        feature = polygon_layer.getFeature(feature_id)  # Retrieve the feature by its ID
                        if feature.geometry().buffer(-buffer_distance, 5).intersects(point_geometry):
                            return QgsGeometry(cut_profile)
                    if not intersects:
                        cut_profile.addGeometry(QgsPoint(point))
            else:
                QgsMessageLog.logMessage("Wrong argument as per status, must be either 'keep inside' or 'keep outside'",
                                         "Create Node Grid",
                                         Qgis.Info)
                pass
        elif location == "positive":
            if status == "keep inside":
                for point in profile_points[0:-1]:
                    point_geometry = QgsGeometry.fromPointXY(point)
                    # Use spatial index to find nearby polygons
                    intersecting_features = spatial_index.intersects(point_geometry.boundingBox())
                    for feature_id in intersecting_features:
                        feature = polygon_layer.getFeature(feature_id)  # Retrieve the feature by its ID
                        if feature.geometry().buffer(buffer_distance, 5).intersects(point_geometry):
                            cut_profile.addGeometry(QgsPoint(point))
                        else:
                            return QgsGeometry(cut_profile)
            elif status == "keep outside":
                for point in profile_points[0:-1]:
                    point_geometry = QgsGeometry.fromPointXY(point)
                    intersects = False
                    # Use spatial index to find nearby polygons
                    intersecting_features = spatial_index.intersects(point_geometry.boundingBox())
                    for feature_id in intersecting_features:
                        feature = polygon_layer.getFeature(feature_id)  # Retrieve the feature by its ID
                        if feature.geometry().buffer(-buffer_distance, 5).intersects(point_geometry):
                            return QgsGeometry(cut_profile)
                    if not intersects:
                        cut_profile.addGeometry(QgsPoint(point))
            else:
                QgsMessageLog.logMessage("Wrong argument as per status, must be either 'keep inside' or 'keep outside'",
                                         "Create Node Grid",
                                         Qgis.Info)
        else:
            QgsMessageLog.logMessage("Wrong argument as per location, must be either 'positive' or 'negative'",
                                     "Create Node Grid",
                                     Qgis.Info)

        return QgsGeometry(cut_profile)

    def check_profile_intersection(self, profile_geometry, spatial_index, geometry_dict):
        """
        Checks if a profile does not intersect another profile from the same setting. If
        intersecting, the profile is cut and returned. his function is based on spatial
        index (spi) to speed up the processing.
        """
        profile_points = profile_geometry.asMultiPoint()
        buffer_distance = 0.5
        cut_profile = QgsMultiPoint()  # Initialize the result geometry
        cut_profile.addGeometry(QgsPoint(profile_points[0]))  # Always add the first point

        # Iterate through the rest of the points in the profile
        for point in profile_points[1:]:
            point_geometry = QgsGeometry.fromPointXY(point)

            # Find the nearest point(s) in the spatial index
            nearby_ids = spatial_index.nearestNeighbor(point_geometry.asPoint(), 2)
            # Log the number of nearby points found
            # Check if this point intersects with any nearby points
            intersected = False
            for feature_id in nearby_ids:
                # Retrieve geometry from the spatial index using the feature ID
                nearby_geom = geometry_dict[feature_id]

                # Determine if the nearby geometry is a single point or a multipoint
                if nearby_geom.isMultipart():
                    # If it's a multipoint, iterate through all the points
                    for nearby_point in nearby_geom.asMultiPoint():
                        distance = point_geometry.asPoint().distance(nearby_point)
                        if distance <= buffer_distance:
                            intersected = True
                            break  # Stop further checks if we find an intersection
                else:
                    # If it's a single point, just compute the distance
                    nearby_point = nearby_geom.asPoint()  # Extract single point
                    distance = point_geometry.asPoint().distance(nearby_point)
                    if distance <= buffer_distance:
                        intersected = True
                        break

                if intersected:
                    break  # Stop checking other geometries if an intersection is found

            if intersected:
                # Stop processing the profile if an intersection is detected
                break
            else:
                # No intersection, so add the point to the profile
                cut_profile.addGeometry(QgsPoint(point))

        # Return the truncated profile (or full profile if no intersections)
        return QgsGeometry(cut_profile)


    def harmonize_lines_geometry(self,original_lines_layer_path, tolerance_value):
        """
        Harmonizes the spacing between vertices of the input lines by simplifying and
        then densifiying the lines with a specific interval.
        """
        simple_lines_layer_path =  original_lines_layer_path.replace("original_", "simple_")
        dens_lines_layer_path = original_lines_layer_path.replace("original_", "dens_")

        processing.run("native:simplifygeometries",
                       {'INPUT': original_lines_layer_path,
                        'METHOD': 0,
                        'TOLERANCE': 0.1,
                        'OUTPUT': simple_lines_layer_path
                        })

        processing.run("native:densifygeometriesgivenaninterval",
                       {
                           'INPUT': simple_lines_layer_path,
                           'INTERVAL': tolerance_value,
                           'OUTPUT': dens_lines_layer_path
                       })

        return dens_lines_layer_path

    def create_multipart_polygons(self, pre_layer_path):
        """
        Ensures that a multipart polygon is created, by converting
        all parts to single parts and then to multiparts again.
        This is done to harmonize all parts of polygons that might
        be split at antimeridian.
        """
        single_path = pre_layer_path.replace("pre_", "single_")
        multi_path = pre_layer_path.replace("pre_", "")
        processing.run("native:multiparttosingleparts", {
            'INPUT': pre_layer_path,
            'OUTPUT': single_path})

        processing.run("native:promotetomulti", {
            'INPUT': single_path,
            'OUTPUT': multi_path})

    def prod_scal(self, point1, r1, point2, r2):
        """
        Calculates the angular separation (in degrees) between two vectors
        defined by their spherical coordinates (declination, inclination,
        and radius).
        """
        x1, y1, z1 = self.DI2xyz(point1, r1)
        norme_1 = math.sqrt(x1 ** 2 + y1 ** 2 + z1 ** 2)
        x2, y2, z2 = self.DI2xyz(point2, r2)
        norme_2 = math.sqrt(x2 ** 2 + y2 ** 2 + z2 ** 2)
        if norme_1 < 0.0000000001:
            omega = 0
        else:
            if norme_2 <  0.0000000001:
                omega = 0
            else:
                if ((x1 * x2 + y1 * y2 + z1 * z2) / (norme_1 * norme_2)) >= 1:
                    omega = 0
                else:
                    val = ((x1 * x2 + y1 * y2 + z1 * z2) / (norme_1 * norme_2))
                    val = round(val, 6)
                    omega = math.acos(val)
        omega = math.degrees(omega)
        return omega

    def calculate_initial_compass_bearing(self, pointA, pointB):
        """
        Calculates the bearing between two points.
        The formula used to calculate the bearing is:
            θ = atan2(sin(Δlong).cos(lat2),
                      cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))

        :param pointA: The Point representing the latitude/longitude for the
                       first point. Latitude and longitude must be in decimal degrees
        :param pointB: The Point representing the latitude/longitude for the
                       second point. Latitude and longitude must be in decimal degrees
        :return: The bearing in degrees
        """
        lat1 = math.radians(pointA.latitude)
        lon1 = math.radians(pointA.longitude)
        lat2 = math.radians(pointB.latitude)
        lon2 = math.radians(pointB.longitude)

        diff_long = lon2 - lon1

        x = math.sin(diff_long) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diff_long))

        initial_bearing = math.atan2(x, y)

        # Convert from radians to degrees
        initial_bearing = math.degrees(initial_bearing)
        # Normalize the bearing
        compass_bearing = (initial_bearing + 360) % 360

        return compass_bearing

    def create_profile(self, point1,point2, xmin, xmax, step_length, flag, orientation):
        """
        Creates a perpendicular profile to the bearing between two points. The profile
        ranges from xmin to xmax with one point each distance specified by step_length.
        Flag allows to change the orientation for the last point (to avoid reversing
        the side when calculating the perpendicular bearing).
        """
        point1_geo = Point(point1.y(), point1.x())
        point2_geo = Point(point2.y(), point2.x())
        bearing = self.calculate_initial_compass_bearing(point1_geo, point2_geo)
        if orientation == "normal":
            if flag == 1:
                perp_bearing = (bearing + 90) % 360
            else:
                perp_bearing = (bearing - 90) % 360
        elif orientation == "inverse":
            if flag == 1:
                perp_bearing = (bearing - 90) % 360
            else:
                perp_bearing = (bearing + 90) % 360
        else:
            QgsMessageLog.logMessage("ERROR")
            return

        profile = QgsMultiPoint()
        for i in range(int(xmin), int(xmax), step_length):
            # Calculate the new point using geodesic distance
            profile_point_geo = geodesic(kilometers=i).destination(point1_geo, perp_bearing)
            profile_point = QgsPointXY(profile_point_geo.longitude, profile_point_geo.latitude)
            profile.addGeometry(QgsPoint(profile_point))
            # If we go from a negative value to 0, make sure we add the original vertex point to the profile if
            # not in the loop (might happen because length of profile if not fully covered by the steps)
            if xmin < 0:
                initial_point = QgsPointXY(point1_geo.longitude, point1_geo.latitude)
                initial_point_geom = QgsGeometry.fromPointXY(initial_point)
                profile_point_geom = QgsGeometry.fromPointXY(profile_point)
                if not initial_point_geom.equals(profile_point_geom):
                    profile.addGeometry(QgsPoint(initial_point))
        profile_geometry = QgsGeometry(profile)
        return profile_geometry

    def composite(self,GaussMean1, GaussSigma1, GaussFactor1, GaussMean2,
                  GaussSigma2, GaussFactor2,CurvatureFactor, PCMFactor,
                  ContinentY, ridge_depth, age, CompensationFactor=0):
        """
        Calculates a composite property based on PCM normalization,
        Gaussian distributions, and additional factors.
        This is used to model properties like crest height
        """

        pPCMMin = self.PCM(0, ridge_depth)
        pPCMMax = self.PCM(4.567 * 1000, ridge_depth)  # 4.568±3 Ga
        A = (1 - 0) / (pPCMMin - pPCMMax)
        B = 0 - A * pPCMMax
        pPCMNorm = A * self.PCM(CurvatureFactor *
                                abs(age - GaussMean1 - CompensationFactor),
                                ridge_depth) + B

        pGaussMax1 = (1 / (GaussSigma1 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((GaussMean1 - GaussMean1) ** 2) / (2 * (GaussSigma1 ** 2)))
        pGauss1N = (1 / (GaussSigma1 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((age - GaussMean1) ** 2) / (2 * (GaussSigma1 ** 2))) / pGaussMax1

        pGaussMax2 = (1 / (GaussSigma2 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((GaussMean2 - GaussMean2) ** 2) / (2 * (GaussSigma2 ** 2)))
        pGauss2N = (1 / (GaussSigma2 * ((2 * math.pi) ** 0.5))) * math.exp(
            -((age - GaussMean2) ** 2) / (2 * (GaussSigma2 ** 2))) / pGaussMax2

        pComposite = ((PCMFactor * pPCMNorm) + (GaussFactor1 * pGauss1N) +
                      (GaussFactor2 * pGauss2N))
        pValue = pComposite + ContinentY
        return pValue

    def PCM(self, age, ridge_depth):
        """
        Implements a Plate Cooling Model (PCM) to calculate the depth of the lithosphere
        based on its age and ridge depth, accounting for thermal contraction and density
        contrasts.
        """
        PARAM_PCM_RhoM = 3300
        PARAM_PCM_Alpha = 0.00003186206799
        PARAM_PCM_TMantle = 1380.689613
        PARAM_PCM_LithoThick = 106417.8373
        PARAM_PCM_RhoW = 1026.983
        PARAM_PCM_Kappa = 34816160.98

        # Ensure ridge_depth is negative
        if ridge_depth > 0:
            ridge_depth = -ridge_depth

        # Linear correction
        a = 1
        b = ridge_depth - (a * ridge_depth)

        depth = ridge_depth + (
                    4 * (PARAM_PCM_RhoM * PARAM_PCM_Alpha * (PARAM_PCM_TMantle - 0) * PARAM_PCM_LithoThick) / (
                        9.8696044011 * (PARAM_PCM_RhoM - PARAM_PCM_RhoW))) * (
                            -1 + math.exp(-(9.869604411 * PARAM_PCM_Kappa * age) / (PARAM_PCM_LithoThick ** 2)))
        Z = a * depth + b
        return Z

    def inversePCM(self, depth, ridge_depth):
        """
        Estimates the geological age of a lithospheric plate based on its depth and ridge
        depth by inverting the Plate Cooling Model (PCM).
        """
        PARAM_PCM_LithoThick = 106417.8373
        PARAM_PCM_Kappa = 34816160.98
        PARAM_PCM_RhoM = 3300
        PARAM_PCM_RhoW = 1026.983
        PARAM_PCM_Alpha = 0.00003186206799
        PARAM_PCM_TMantle = 1380.689613

        if ridge_depth > 1:
            ridge_depth = -ridge_depth

        A = 1
        B = ridge_depth - (A * ridge_depth)

        if type(depth) is QVariant:
            value = 0
        else:
            inverse_depth = (depth - B) / A
            value = -((PARAM_PCM_LithoThick ** 2) / (PARAM_PCM_Kappa * (math.pi ** 2))) * math.log(1 + (((math.pi ** 2) * (PARAM_PCM_RhoM - PARAM_PCM_RhoW) * (inverse_depth - ridge_depth)) / (4 * PARAM_PCM_RhoM * PARAM_PCM_Alpha * PARAM_PCM_LithoThick * (PARAM_PCM_TMantle - 0))))
            if value < 0:
                value = 0

        return value

    def move_nodes_slightly(self,age):
        """
        Moves the nodes by 0.0001° of latitude and longitude. This somehow avoids issues when
        doing the TIN inteprolation that gets stuck otherwise.
        """
        all_nodes_layer_path = os.path.join(self.output_folder_path, f"all_nodes_{int(age)}.geojson")

        with open(all_nodes_layer_path,
                  'r') as file:
            geojson_data = json.load(file)

        for feature in geojson_data['features']:
            geometry = feature['geometry']['coordinates']

            # Systematically add 0.001 to both x (longitude) and y (latitude) coordinates
            geometry[0] += 0.0001  # Shift longitude (x)
            geometry[1] += 0.0001  # Shift latitude (y)

            # Update the feature's geometry with the new coordinates
            feature['geometry']['coordinates'] = geometry
        # Save the updated GeoJSON back to the original file
        with open(all_nodes_layer_path,
                  'w') as outfile:
            json.dump(geojson_data, outfile, indent=4)

    def add_id_nodes(self,age):
        """
        Adds id to each node in the all nodes layer.
        """
        nodes_layer_path = os.path.join(self.output_folder_path, f"all_nodes_{int(age)}.geojson")
        all_nodes_layer = QgsVectorLayer(nodes_layer_path, f"All Nodes {int(age)}", "ogr")
        field_idx_id = all_nodes_layer.fields().indexOf('ID')
        with edit(all_nodes_layer):
            for feature in all_nodes_layer.getFeatures():
                node_id = int(feature.id())
                all_nodes_layer.changeAttributeValue(feature.id(), field_idx_id, node_id)
        all_nodes_layer.commitChanges()

    def create_final_nodes(self, age):
        """
        Creates the final all nodes layer. First, deletes all features (RID + ISO) that were used for
        the preliminary raster. Once merged, nodes are given an id and moved slightly.
        """
        all_nodes_layer_path = os.path.join(self.output_folder_path, f"all_nodes_{int(age)}.geojson")
        all_nodes_layer = QgsVectorLayer(all_nodes_layer_path, "All Nodes", "ogr")
        nodes_to_delete = []
        for node in all_nodes_layer.getFeatures():
            nodes_to_delete.append(node.id())

        with edit(all_nodes_layer):
            all_nodes_layer.dataProvider().deleteFeatures(nodes_to_delete)
        all_nodes_layer.commitChanges()

        settings = ["RID", "ISO", "LWS", "ABA", "PMW", "CTN", "CRA", "OTM", "PMC", "RIB", "UPS", "COL", "HOT"]
        for setting in settings:
            nodes_layer_path = os.path.join(self.output_folder_path, f"{setting}_nodes_{int(age)}.geojson")
            self.add_nodes(age, nodes_layer_path, first_build=False)
            self.add_id_nodes(age)
            self.move_nodes_slightly(age)

    def add_id_nodes_setting(self, age, setting):
        """
        Adds an id to each setting nodes layer.
        """
        nodes_layer_path = os.path.join(self.output_folder_path, f"{setting}_nodes_{int(age)}.geojson")
        nodes_layer = QgsVectorLayer(nodes_layer_path, f"{setting} Nodes {int(age)}", "ogr")
        nodes_provider = nodes_layer.dataProvider()
        nodes_provider.addAttributes([QgsField('SET_ID', QVariant.Double), QgsField('FLAG', QVariant.Double)])
        nodes_layer.updateFields()
        nodes_layer.commitChanges()
        field_idx_si = nodes_layer.fields().indexOf('SET_ID')
        field_idx_fl = nodes_layer.fields().indexOf('FLAG')
        features = list(nodes_layer.getFeatures())
        if len(features) == 0:
            return
        with edit(nodes_layer):
            for feature in nodes_layer.getFeatures():
                node_id = int(feature.id())
                nodes_layer.changeAttributeValue(feature.id(), field_idx_si, node_id)
                nodes_layer.changeAttributeValue(feature.id(), field_idx_fl, 45771972)
        nodes_layer.commitChanges()

    def add_nodes(self, age, points_layer_path, first_build = False):
        """Adds converted features to the nodes layer.
        If first build is True, only ridges and isochrons are added (initial
        creation with these two is needed for other features conversions)."""
        output_nodes_layer_path = os.path.join(self.output_folder_path, f"all_nodes_{int(age)}.geojson")
        if first_build is True:
            all_nodes_features = []
            points_layer = QgsVectorLayer(points_layer_path, f"Points_{age}", "ogr")
            new_nodes_features = list(points_layer.getFeatures())
            for new_node_feature in new_nodes_features:
                type = new_node_feature.attribute('TYPE')
                feature_age = new_node_feature.attribute('FEAT_AGE')
                distance = new_node_feature.attribute('DIST')
                z = new_node_feature.attribute('Z_WITH_SED')
                plate = new_node_feature.attribute('PLATE')
                if isinstance(z, QVariant):
                    pass
                elif not isinstance(z, float):
                    pass
                elif not z:
                    pass
                elif math.isnan(z):
                    pass
                else:
                    geom = new_node_feature.geometry()
                    x = geom.asPoint().x()
                    y = geom.asPoint().y()
                    if x > 180 or x < -180 or y > 89.5 or y < -89.5:
                        pass
                    else:
                        coords = [x,y]
                        geojson_point_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": type,
                                "FEAT_AGE": feature_age,
                                "DIST": distance,
                                "Z": z,
                                "ID": 45771972,
                                "PLATE" : plate
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": coords
                            }
                        }
                        all_nodes_features.append(geojson_point_feature)
        if first_build is False:
            with open(output_nodes_layer_path) as f:
                geojson = json.load(f)
                all_nodes_features = geojson["features"]
            points_layer = QgsVectorLayer(points_layer_path, f"Points_{age}", "ogr")
            new_nodes_features = list(points_layer.getFeatures())
            for new_node_feature in new_nodes_features:
                type = new_node_feature.attribute('TYPE')
                feature_age = new_node_feature.attribute('FEAT_AGE')
                distance = new_node_feature.attribute('DIST')
                z = new_node_feature.attribute('Z_WITH_SED')
                if 'PLATE' in new_node_feature.fields().names():
                    plate = new_node_feature.attribute('PLATE')
                    if plate is None:
                        plate = "UNDEFINED"
                else:
                    plate = "UNDEFINED"
                if isinstance(z, QVariant):
                    pass
                elif not isinstance(z, float):
                    pass
                elif not z:
                    pass
                elif math.isnan(z):
                    pass
                else:
                    geom = new_node_feature.geometry()
                    x = geom.asPoint().x()
                    y = geom.asPoint().y()
                    if x > 180 or x < -180 or y > 90 or y < -90:
                        pass
                    else:
                        coords = [x, y]
                        geojson_point_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": type,
                                "FEAT_AGE": feature_age,
                                "DIST": distance,
                                "Z": z,
                                "ID": 45771972,
                                "PLATE": plate
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": coords
                            }
                        }
                        all_nodes_features.append(geojson_point_feature)
        with open(output_nodes_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_nodes_features
            }, indent=2))

    def add_layer_to_group(self,layer_path, group_name, setting):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(group_name)
        if not group:
            group = root.addGroup(group_name)
        layer = QgsVectorLayer(layer_path, f"{setting}", "ogr")
        QgsProject.instance().addMapLayer(layer, False)
        group.addLayer(layer)

    def check_point_plate_intersection(self, age, setting):
        nodes_layer_path = os.path.join(self.output_folder_path, f"{setting}_nodes_{int(age)}.geojson")
        nodes_layer = QgsVectorLayer(nodes_layer_path, f"{setting} Nodes", "ogr")
        polygon_index = QgsSpatialIndex(self.plate_polygons_layer)
        nodes_to_delete = []
        for node in nodes_layer.getFeatures():
            node_geom = node.geometry()
            candidate_ids = polygon_index.intersects(node_geom.boundingBox())
            node_plate = node.attribute("PLATE")
            plate_names_ors = {self.plate_polygons_layer.getFeature(poly_id).attribute("PLATE") for poly_id in candidate_ids}
            plate_name_mappings = {
                "Nazca": "NAZ",
                "Tong_Ker": "TONGA_KER",
                "Fiji_N": "FIDJI_N",
                "Fiji_E": "FIDJI_E",
                "Fiji_W": "FIDJI_W",
                "Carolina": "CAROLINE",
                "India": "IND",
                "Easter": "EAST"
            }

            plate_names = {plate_name_mappings.get(plate_name_or, plate_name_or.upper()) for plate_name_or in
                           plate_names_ors}

            if node_plate in plate_names:
                matching_geometries = [
                    self.plate_polygons_layer.getFeature(poly_id).geometry()
                    for poly_id in candidate_ids
                    if plate_name_mappings.get(self.plate_polygons_layer.getFeature(poly_id).attribute("PLATE"),
                                               self.plate_polygons_layer.getFeature(poly_id).attribute(
                                                   "PLATE").upper()) == node_plate
                ]

                if matching_geometries:
                    merged_geometry = matching_geometries[0]
                    for geom in matching_geometries[1:]:
                        merged_geometry = merged_geometry.combine(geom)
                    if not node_geom.intersects(merged_geometry):
                        nodes_to_delete.append(node.id())

        QgsMessageLog.logMessage(f"{setting}: Deleted {len(nodes_to_delete)} nodes that were not intersecting their original plate", "Create Node Grid", Qgis.Info)
        with edit(nodes_layer):
            nodes_layer.dataProvider().deleteFeatures(nodes_to_delete)
        nodes_layer.commitChanges()







