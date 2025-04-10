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

class PMWConversion:
    continent_polygons_path = base_tools.get_layer_path("Continent Polygons")
    continent_polygons_layer = QgsVectorLayer(continent_polygons_path, "Continent Polygons", 'ogr')
    output_folder_path = base_tools.get_layer_path("Output Folder")

    def __init__(self):
        pass
    def passive_margin_wedge_to_nodes(self,age):
        x_min = 0
        step_length = 50
        raster_prelim_path = os.path.join(self.output_folder_path,f"qgis_tin_raster_prelim_{int(age)}.tif")
        raster_prelim = QgsRasterLayer(raster_prelim_path,"Preliminary Raster")
        pmw_multipoint_path = os.path.join(self.output_folder_path, f"pmw_multipoint_{int(age)}.geojson")
        PM_multipoints = QgsVectorLayer(pmw_multipoint_path, "Densified PMC MultiPoint", "ogr")
        spatial_index_profiles = QgsSpatialIndex()
        geometry_dict_profiles = {}
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
                PM_multipoints.changeAttributeValue(feature.id(),field_idx_zc,float(z_crest))
                PM_multipoints.changeAttributeValue(feature.id(),field_idx_xc,float(x_crest))
                geom = feature.geometry()
                multi_point = geom.asMultiPoint()
                middle_index = len(multi_point) // 2
                middle_point = multi_point[middle_index]
                coords = QgsPointXY(middle_point)
                val, res = raster_prelim.dataProvider().sample(coords, 1)
                if math.isnan(val):
                    raster_depth = 1.4109347442680775* ridge_depth
                else:
                    raster_depth = float(val)
                    if raster_depth < -5500:
                        raster_depth = -5500
                PM_multipoints.changeAttributeValue(feature.id(),field_idx_zr,raster_depth)
                length = -pm_tools.wedge_x_pm_new(feature_age)* 100 #Multiply by a 100 to convert from degrees to km
                x_max = -length
                PM_multipoints.changeAttributeValue(feature.id(),field_idx_xmax,x_max)
        PM_multipoints.commitChanges()
        attributes = PM_multipoints.fields().toList()
        PMW_profiles = QgsVectorLayer("MultiPoint?crs=EPSG:4326","PMW Profiles","memory")
        profiles_provider = PMW_profiles.dataProvider()
        profiles_provider.addAttributes(attributes)
        PMW_profiles.updateFields()
        for passive_margin_feature in PM_multipoints.getFeatures():
            x_max = float(passive_margin_feature.attribute('X_MAX'))
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
                    profile_geometry = feature_conversion_tools.create_profile(point1,point2,x_min,-x_max,step_length, flag, "normal")
                    if profile_geometry:
                        cont_included_profile_geometry = feature_conversion_tools.cut_profile_spi(profile_geometry, self.continent_polygons_layer, "keep outside", "positive", age, False)
                        if cont_included_profile_geometry:
                            final_profile_geometry = feature_conversion_tools.check_profile_intersection(cont_included_profile_geometry,spatial_index_profiles, geometry_dict_profiles)
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
                PMW_profiles.commitChanges()
        output_profiles_layer_path = os.path.join(self.output_folder_path,f"PMW_profiles_{int(age)}.geojson")
        QgsVectorFileWriter.writeAsVectorFormat(PMW_profiles,output_profiles_layer_path,'utf-8',PMW_profiles.crs(),"GeoJSON")
        all_points_features = []
        continent_y = 240.38
        for profile_feature in PMW_profiles.getFeatures():
            feature_abs_age = profile_feature.attribute('AGE')
            plate = profile_feature.attribute('PLATE')
            ridge_depth = feature_conversion_tools.get_ridge_depth(age)

            feature_age = feature_abs_age - age
            geom = profile_feature.geometry()
            multi_point = geom.asMultiPoint()
            feat_start_point = multi_point[0]
            for point in multi_point:
                distance = -feature_conversion_tools.prod_scal(feat_start_point,1,point,1)
                x_crest = float(profile_feature.attribute('X_CREST'))
                y_crest = float(profile_feature.attribute('Z_CREST'))
                x_wedge = pm_tools.wedge_x_pm_new(feature_age)
                y_wedge = pm_tools.wedge_y_pm_new(feature_age)
                coords = QgsPointXY(point)
                val, res = raster_prelim.dataProvider().sample(coords, 1)
                if math.isnan(val):
                    raster_depth = 1.4109347442680775 * ridge_depth
                else:
                    raster_depth = float(val)
                raster_age = feature_conversion_tools.inversePCM(raster_depth, ridge_depth)
                coords = [point[0], point[1]]
                abys_sed = sed_tools.abyssal_sediments(age,age + raster_age)
                z_with_sed = pm_tools.passive_margin_profile_clean(distance,feature_age,raster_depth,ridge_depth,y_wedge,x_wedge,y_crest,x_crest,continent_y)
                wedge_sed_thick = z_with_sed - raster_depth
                if wedge_sed_thick < abys_sed:
                    wedge_sed_thick = abys_sed
                else:
                    wedge_sed_thick = wedge_sed_thick
                z_with_sed = raster_depth + wedge_sed_thick
                h_sed = sed_tools.full_sediment_thickness(wedge_sed_thick)
                rho_sed = sed_tools.rho_sed(h_sed)
                geojson_point_feature = {
                    "type": "Feature",
                    "properties": {
                        "TYPE": "PMW",
                        "FEAT_AGE": feature_age,
                        "DIST": distance,
                        "Z": raster_depth,
                        "Z_WITH_SED": z_with_sed,
                        "H_SED": h_sed,
                        "RHO_SED": rho_sed,
                        "PLATE": plate,
                        "Z_RASTER": raster_depth
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": coords
                    }
                }
                all_points_features.append(geojson_point_feature)
        output_points_layer_path = os.path.join(self.output_folder_path,f"PMW_nodes_{int(age)}.geojson")
        with open(output_points_layer_path, 'w') as output_file:
            output_file.write(json.dumps({
                "type": "FeatureCollection",
                "features": all_points_features
            }, indent=2))
        #feature_conversion_tools.check_point_plate_intersection(age, "PMW")
        feature_conversion_tools.add_id_nodes_setting(output_points_layer_path)
        #feature_conversion_tools.add_layer_to_group(output_points_layer_path, f"{int(age)} Ma", "PMW")
