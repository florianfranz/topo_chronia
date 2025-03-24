import os
import json
import math

from qgis.PyQt.QtCore import QVariant
from qgis.core import (Qgis, edit, QgsVectorLayer, QgsFeatureRequest, QgsMessageLog, QgsRasterLayer,
                       QgsVectorFileWriter,QgsPointXY, QgsField, QgsGeometry, QgsFeature, QgsProject,
                       QgsSpatialIndex)

from ...base_tools import BaseTools
base_tools = BaseTools()

from ..tools.sediments_tools import SEDConversionTools
sed_tools = SEDConversionTools()

from ..tools.feature_conversion_tools import FeatureConversionTools
feature_conversion_tools = FeatureConversionTools()

class ABAConversion:
    INPUT_FILE_PATH = "input_files.txt"
    output_folder_path = base_tools.get_layer_path("Output Folder")

    def __init__(self):
        pass
    def abandoned_arc_to_nodes(self,age):
        PARAM_AA_vF = 1000
        PARAM_AA_lambdaF = 0.57
        PARAM_AA_fG = 2500
        PARAM_AA_mG = 0
        PARAM_AA_sG = 0.177
        ridge_depth = feature_conversion_tools.get_ridge_depth(age)
        gauss_norm = (1 / (PARAM_AA_sG * ((2 * math.pi) ** 0.5))) * math.exp(- ((PARAM_AA_mG - PARAM_AA_mG) ** 2)/ (2 * (PARAM_AA_sG) ** 2))
        x_min = 0
        x_max_pos = 151
        x_max_neg = 101
        step_length = 50
        dens_ABA_lines_layer_path = os.path.join(self.output_folder_path, f"dens_ABA_lines_{int(age)}.geojson")
        dens_ABA_layer = QgsVectorLayer(dens_ABA_lines_layer_path, "Simplified ABA Lines", 'ogr')
        raster_prelim_path = os.path.join(self.output_folder_path, f"qgis_tin_raster_prelim_{int(age)}.tif")
        raster_prelim = QgsRasterLayer(raster_prelim_path, "Preliminary Raster")
        attributes = dens_ABA_layer.fields().toList()
        ABA_multipoints = QgsVectorLayer("MultiPoint?crs=EPSG:4326","ABA Multipoints","memory")
        points_provider = ABA_multipoints.dataProvider()
        ABA_multipoints.startEditing()
        points_provider.addAttributes(attributes)
        points_provider.addAttributes([QgsField('LAT_DIST', QVariant.Double),QgsField('Z_RASTER', QVariant.Double),QgsField('GAUSS_FAC', QVariant.Double)])
        ABA_multipoints.updateFields()
        ABA_multipoints.commitChanges()
        spatial_index_pos_profiles = QgsSpatialIndex()
        geometry_dict_pos_profiles = {}
        spatial_index_neg_profiles = QgsSpatialIndex()
        geometry_dict_neg_profiles = {}
        for feature in dens_ABA_layer.getFeatures():
            geom = feature.geometry()
            coords_list = [QgsPointXY(pt) for part in geom.parts() for pt in part]
            multipoint_geom = QgsGeometry.fromMultiPointXY(coords_list)
            new_feature = QgsFeature()
            new_feature.setGeometry(multipoint_geom)
            new_feature.setAttributes(feature.attributes())
            points_provider.addFeature(new_feature)
        ABA_multipoints.commitChanges()
        ABA_multipoints_layer_path = os.path.join(self.output_folder_path,f"ABA_multipoints_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(ABA_multipoints, ABA_multipoints_layer_path, 'utf-8',
                                               ABA_multipoints.crs(), "GeoJSON")
        attributes = ABA_multipoints.fields().toList()
        ABA_neg_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","ABA Negative Profiles","memory")
        neg_profiles_provider = ABA_neg_profiles.dataProvider()
        neg_profiles_provider.addAttributes(attributes)
        ABA_neg_profiles.updateFields()
        ABA_pos_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","ABA Positive Profiles","memory")
        pos_profiles_provider = ABA_pos_profiles.dataProvider()
        pos_profiles_provider.addAttributes(attributes)
        ABA_pos_profiles.updateFields()
        field_idx_ld = ABA_multipoints.fields().indexOf('LAT_DIST')
        field_idx_gf = ABA_multipoints.fields().indexOf('GAUSS_FAC')
        field_idx_rd = ABA_multipoints.fields().indexOf('Z_RASTER')
        with edit(ABA_multipoints):
            for abandoned_arc_feature in ABA_multipoints.getFeatures():
                geom = abandoned_arc_feature.geometry()
                multi_point = geom.asMultiPoint()
                point_init = multi_point[0]
                middle_index = len(multi_point) // 2
                middle_point = multi_point[middle_index]
                coords = QgsPointXY(middle_point)
                val, res = raster_prelim.dataProvider().sample(coords, 1)
                if math.isnan(val):
                    raster_depth = 1.4109347442680775*ridge_depth
                else:
                    raster_depth = float(val)
                    if raster_depth < -5500:
                        raster_depth = -5500
                for i in range(len(multi_point)):
                    if i < len(multi_point) - 1:
                        point1 = multi_point[i]
                        point2 = multi_point[i + 1]
                        flag = 0
                    else:
                        point1 = multi_point[i]
                        point2 = multi_point[i - 1]
                        flag = 1
                    lat_distance = feature_conversion_tools.prod_scal(point_init, 1, point1, 1)
                    gauss_factor = PARAM_AA_vF * math.sin(
                        (lat_distance * (2 * math.pi)) / PARAM_AA_lambdaF) + PARAM_AA_fG
                    ABA_multipoints.changeAttributeValue(abandoned_arc_feature.id(), field_idx_ld, lat_distance)
                    ABA_multipoints.changeAttributeValue(abandoned_arc_feature.id(), field_idx_gf, gauss_factor)
                    ABA_multipoints.changeAttributeValue(abandoned_arc_feature.id(), field_idx_rd, raster_depth)
                    updated_feature = next(ABA_multipoints.getFeatures(QgsFeatureRequest(abandoned_arc_feature.id())))
                    feature = QgsFeature()
                    negative_profile_geometry = feature_conversion_tools.create_profile(point1,point2,x_min,x_max_neg,step_length, flag, "inverse")
                    if negative_profile_geometry:
                        final_neg_profile_geometry = feature_conversion_tools.check_profile_intersection(negative_profile_geometry, spatial_index_neg_profiles, geometry_dict_neg_profiles)
                        if final_neg_profile_geometry:
                            feature.setGeometry(final_neg_profile_geometry)
                            feature.setAttributes(updated_feature.attributes())
                            profile_points = final_neg_profile_geometry.asMultiPoint()
                            for point in profile_points:
                                point_id = len(geometry_dict_neg_profiles)
                                point_geom = QgsGeometry.fromPointXY(point)
                                geometry_dict_neg_profiles[point_id] = point_geom
                                p_feature = QgsFeature(point_id)
                                p_feature.setGeometry(point_geom)
                                spatial_index_neg_profiles.insertFeature(p_feature)
                            neg_profiles_provider.addFeature(feature)
                    feature = QgsFeature()
                    positive_profile_geometry = feature_conversion_tools.create_profile(point1,point2,x_min,x_max_pos,step_length,flag, "normal")
                    if positive_profile_geometry:
                        final_pos_profile_geometry = feature_conversion_tools.check_profile_intersection(positive_profile_geometry, spatial_index_pos_profiles,geometry_dict_pos_profiles)
                        if final_pos_profile_geometry:
                            feature.setGeometry(final_pos_profile_geometry)
                            feature.setAttributes(updated_feature.attributes())
                            profile_points = final_pos_profile_geometry.asMultiPoint()
                            for point in profile_points:
                                point_id = len(geometry_dict_pos_profiles)
                                point_geom = QgsGeometry.fromPointXY(point)
                                geometry_dict_pos_profiles[point_id] = point_geom
                                p_feature = QgsFeature(point_id)
                                p_feature.setGeometry(point_geom)
                                spatial_index_pos_profiles.insertFeature(p_feature)
                            pos_profiles_provider.addFeature(feature)
        ABA_neg_profiles.commitChanges()
        ABA_pos_profiles.commitChanges()
        output_neg_profiles_layer_path = os.path.join(self.output_folder_path,f"ABA_neg_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(ABA_neg_profiles,output_neg_profiles_layer_path,'utf-8',ABA_neg_profiles.crs(),"GeoJSON")
        output_pos_profiles_layer_path = os.path.join(self.output_folder_path,f"ABA_pos_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(ABA_pos_profiles,output_pos_profiles_layer_path,'utf-8',ABA_pos_profiles.crs(),"GeoJSON")
        all_points_features = []
        for profile in ABA_pos_profiles.getFeatures():
            gauss_factor = profile.attribute('GAUSS_FAC')
            plate = profile.attribute('PLATE')
            geom = profile.geometry()
            multi_point = geom.asMultiPoint()
            feature_abs_age = profile.attribute('AGE')
            feature_age = feature_abs_age - age
            feat_start_point = multi_point[0]
            raster_depth = feature_conversion_tools.PCM(feature_age, ridge_depth)
            for i in range(len(multi_point)):
                distance = feature_conversion_tools.prod_scal(feat_start_point,1,multi_point[i],1)
                coordinates = [multi_point[i][0], multi_point[i][1]]
                raster_age = feature_age
                abys_sed = float(sed_tools.abyssal_sediments(age,age + raster_age))
                z_profile = (gauss_factor * (1 / (PARAM_AA_sG * ((2 * math.pi) ** 0.5))) * math.exp(-((distance - PARAM_AA_mG) ** 2) / (2 * (PARAM_AA_sG ** 2))) / gauss_norm)
                if abys_sed < z_profile:
                    z = raster_depth + z_profile
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "ABA",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": z,
                            "Z_WITH_SED": z,
                            "Z_PROFILE": z_profile,
                            "H_SED": -1,
                            "RHO_SED": -1,
                            "SIDE": "Positive",
                            "Z_RAS" : raster_depth,
                            "PLATE" : plate
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": coordinates
                        }
                    }
                    all_points_features.append(geojson_point_feature)
                else:
                    z = raster_depth + z_profile
                    h_s = sed_tools.full_sediment_thickness(abys_sed - z_profile)
                    rho_sed = sed_tools.rho_sed(h_s)
                    geojson_point_feature = {
                        "type": "Feature",
                        "properties": {
                            "TYPE": "ABA",
                            "FEAT_AGE": feature_age,
                            "DIST": distance,
                            "Z": z,
                            "Z_WITH_SED": z,
                            "Z_PROFILE": z_profile,
                            "H_SED": h_s,
                            "RHO_SED": rho_sed,
                            "SIDE": "Positive",
                            "Z_RAS" : raster_depth,
                            "PLATE": plate
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": coordinates
                        }
                    }
                    all_points_features.append(geojson_point_feature)

        for profile in ABA_neg_profiles.getFeatures():
            gauss_factor = profile.attribute('GAUSS_FAC')
            plate = profile.attribute('PLATE')
            raster_depth = profile.attribute('Z_RASTER')
            geom = profile.geometry()
            multi_point = geom.asMultiPoint()
            feature_abs_age = profile.attribute('AGE')
            feature_age = feature_abs_age - age
            feat_start_point = multi_point[-1]
            for i in range(len(multi_point)):
                distance = feature_conversion_tools.prod_scal(feat_start_point,1,multi_point[i],1)
                if distance == 0:
                    pass
                else:
                    coordinates = [multi_point[i][0], multi_point[i][1]]
                    raster_age = float(feature_conversion_tools.inversePCM(raster_depth,ridge_depth))
                    abys_sed = float(sed_tools.abyssal_sediments(age,age + raster_age))
                    z_profile = (gauss_factor * (1 / (PARAM_AA_sG * ((2 * math.pi) ** 0.5))) * math.exp(-((distance - PARAM_AA_mG) ** 2) / (2 * (PARAM_AA_sG ** 2))) / gauss_norm)
                    if abys_sed < z_profile:
                        z = raster_depth + z_profile
                        geojson_point_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": "ABA",
                                "FEAT_AGE": feature_age,
                                "DIST": distance,
                                "Z": z,
                                "Z_WITH_SED": z,
                                "Z_PROFILE": z_profile,
                                "H_SED": -1,
                                "RHO_SED": -1,
                                "SIDE": "Negative",
                                "Z_RAS" : raster_depth,
                                "PLATE": plate
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": coordinates
                            }
                        }
                        all_points_features.append(geojson_point_feature)
                    else:
                        z = raster_depth + z_profile
                        h_s = sed_tools.full_sediment_thickness(abys_sed - z_profile)
                        rho_sed = sed_tools.rho_sed(h_s)
                        geojson_point_feature = {
                            "type": "Feature",
                            "properties": {
                                "TYPE": "ABA",
                                "FEAT_AGE": feature_age,
                                "DIST": distance,
                                "Z": z,
                                "Z_WITH_SED": z,
                                "Z_PROFILE": z_profile,
                                "H_SED": h_s,
                                "RHO_SED": rho_sed,
                                "SIDE": "Negative",
                                "Z_RAS" : raster_depth,
                                "PLATE": plate,
                            },
                            "geometry": {
                                "type": "Point",
                                "coordinates": coordinates
                            }
                        }
                        all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,f"ABA_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        #feature_conversion_tools.check_point_plate_intersection(age, "ABA")
        feature_conversion_tools.add_id_nodes_setting(age, "ABA")
        #feature_conversion_tools.add_layer_to_group(output_points_layer_path, f"{int(age)} Ma", "ABA")
