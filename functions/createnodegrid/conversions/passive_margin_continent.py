import os
import json
import math
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsRasterLayer, QgsMessageLog, QgsField,
                       QgsVectorFileWriter, QgsGeometry, QgsPointXY, QgsFeature, QgsProject, QgsSpatialIndex)
from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.passive_margin_tools import PMConversionTools
pm_tools = PMConversionTools()

from ..tools.sediments_tools import SEDConversionTools
sed_tools = SEDConversionTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class PMCConversion:
    INPUT_FILE_PATH = "input_files.txt"
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")

    def __init__(self):
        pass
    def passive_margin_continent_to_nodes(self,age):
        raster_prelim_path = os.path.join(self.output_folder_path, f"qgis_tin_raster_prelim_{int(age)}.tif")
        raster_prelim = QgsRasterLayer(raster_prelim_path, "Preliminary Raster")
        pmc_multipoint_path = os.path.join(self.output_folder_path, f"pmc_multipoint_{int(age)}.geojson")
        PM_multipoints = QgsVectorLayer(pmc_multipoint_path,"Densified PMC MultiPoint","ogr")
        field_idx_zc = PM_multipoints.fields().indexOf('Z_CREST')
        field_idx_xc = PM_multipoints.fields().indexOf('X_CREST')
        field_idx_zr = PM_multipoints.fields().indexOf('Z_RASTER')
        field_idx_xmax = PM_multipoints.fields().indexOf('X_MAX')
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        with edit(PM_multipoints):
            for feature in PM_multipoints.getFeatures():
                feature_age = feature.attribute("FEAT_AGE")
                z_crest = pm_tools.crest_y_passive_margin(age, feature_age)
                x_crest = pm_tools.crest_x_passive_margin(feature_age)
                PM_multipoints.changeAttributeValue(feature.id(), field_idx_zc, float(z_crest))
                PM_multipoints.changeAttributeValue(feature.id(), field_idx_xc, float(x_crest))
                geom = feature.geometry()
                multi_point = geom.asMultiPoint()
                middle_index = len(multi_point) // 2
                middle_point = multi_point[middle_index]
                coords = QgsPointXY(middle_point)
                val, res = raster_prelim.dataProvider().sample(coords, 1)
                if math.isnan(val):
                    raster_depth =1.4109347442680775*ridge_depth
                else:
                    raster_depth = float(val)
                    if raster_depth < -5500:
                        raster_depth = -5500
                PM_multipoints.changeAttributeValue(feature.id(), field_idx_zr, raster_depth)
                length = -pm_tools.wedge_x_pm_new(feature_age) * 100  # Multiply by a 100 to convert from degrees to km
                x_max = -length
                PM_multipoints.changeAttributeValue(feature.id(), field_idx_xmax, x_max)
        PM_multipoints.commitChanges()
        attributes = PM_multipoints.fields().toList()
        PMC_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","PMC Profiles","memory")
        profiles_provider = PMC_profiles.dataProvider()
        profiles_provider.addAttributes(attributes)
        PMC_profiles.updateFields()
        x_min = 0
        step_length = 50
        x_max = 550
        spatial_index_profiles = QgsSpatialIndex()
        geometry_dict_profiles = {}
        for passive_margin_feature in PM_multipoints.getFeatures():
            geom = passive_margin_feature.geometry()
            multi_point = geom.asMultiPoint()
            if len(multi_point) < 2:
                pass
            else:
                for i in range(len(multi_point)):
                    if i < len(multi_point) - 1:
                        point1 = multi_point[i]
                        point2 = multi_point[i + 1]
                        flag = 0
                    else:
                        point1 = multi_point[i]
                        point2 = multi_point[i - 1]
                        flag = 1
                    feature = QgsFeature()
                    profile_geometry = feature_conversion_tools.create_profile(point1,point2,x_min,x_max,step_length, flag, "inverse")
                    if profile_geometry:
                        cont_included_profile_geometry = feature_conversion_tools.cut_profile_spi(profile_geometry,
                                                                                                  self.continent_polygons_layer,
                                                                                                  "keep inside",
                                                                                                  "positive", age,
                                                                                                  False)
                        if cont_included_profile_geometry:
                            final_profile_geometry = feature_conversion_tools.check_profile_intersection(cont_included_profile_geometry,
                                                                                                         spatial_index_profiles,
                                                                                                         geometry_dict_profiles)

                            if final_profile_geometry:
                                feature.setGeometry(final_profile_geometry)
                                feature.setAttributes(passive_margin_feature.attributes())
                                profile_points = final_profile_geometry.asMultiPoint()
                                for point in profile_points:
                                    point_id = len(geometry_dict_profiles)
                                    point_geom = QgsGeometry.fromPointXY(point)
                                    geometry_dict_profiles[point_id] = point_geom
                                    p_feature = QgsFeature(point_id)
                                    p_feature.setGeometry(point_geom)
                                    spatial_index_profiles.insertFeature(p_feature)
                                profiles_provider.addFeature(feature)
                PMC_profiles.commitChanges()
        output_profiles_layer_path = os.path.join(self.output_folder_path, f"PMC_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(PMC_profiles,output_profiles_layer_path,'utf-8',PMC_profiles.crs(),"GeoJSON")
        all_points_features = []
        for profile in PMC_profiles.getFeatures():
            x_crest = float(profile.attribute("X_CREST"))
            z_crest = float(profile.attribute("Z_CREST"))
            plate = profile.attribute('PLATE')
            feature_age = profile.attribute("FEAT_AGE")
            x_wedge = pm_tools.wedge_x_pm_new(feature_age)
            y_wedge = pm_tools.wedge_y_pm_new(feature_age)
            ridge_depth = feature_conversion_tools.get_ridge_depth(age)
            raster_depth = float(profile.attribute('Z_RASTER'))
            geom = profile.geometry()
            continent_y = 240.38
            multi_point = geom.asMultiPoint()
            feat_start_point = multi_point[0]
            for point in multi_point:
                coords = [point[0], point[1]]
                distance = float(feature_conversion_tools.prod_scal(feat_start_point,1,point,1))
                if distance == 0:
                    pass # As we already have nodes at feature line position from the passive margin wedge, we skip it here.
                else:
                    z = pm_tools.passive_margin_profile_clean(distance, feature_age, raster_depth, ridge_depth, y_wedge,x_wedge, z_crest, x_crest, continent_y)
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "PMC",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": z,
                            "Z_WITH_SED": z,
                            "PLATE": plate
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": coords
                        }
                    }
                    all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,f"PMC_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        #feature_conversion_tools.check_point_plate_intersection(age, "PMC")
        feature_conversion_tools.add_id_nodes_setting(age, "PMC")
        feature_conversion_tools.add_layer_to_group(output_points_layer_path, f"{int(age)} Ma", "PMC")
