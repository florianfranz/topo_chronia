import os
import sys
import platform
from qgis.utils import iface
from qgis.core import Qgis, QgsVectorLayer, QgsProject, QgsApplication, QgsSettings, QgsMessageLog
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def base_test():
    print("TopoChronia correctly installed and functions can be called.")
    system_name = platform.system()
    print(f"Operating System: {system_name}")
    try:
        from topo_chronia.ext_libraries import geopy
        from geopy.distance import geodesic, great_circle
        from geopy.point import Point
        print("geopy correctly installed, imported geopy.distance.geodesic, geop.distance.great_circle and geopy.point.Point")
    except ImportError as e:
        print("Cannot import geopy. Please install geopy ,manually ")
        QgsMessageLog.logMessage(f"Failed to import geopy: {e}","Test", Qgis.Critical)
    return

def load_sample_data():
    plugin_tests_dir = os.path.dirname(os.path.abspath(__file__))

    PM_layer_path = os.path.join(plugin_tests_dir, 'data', 'PM_444_sample.shp')
    PP_layer_path = os.path.join(plugin_tests_dir, 'data', 'PP_444_sample.shp')
    COB_layer_path = os.path.join(plugin_tests_dir, 'data', 'COB_444_sample.shp')
    GG_layer_path = os.path.join(plugin_tests_dir, 'data', 'Geodesic_Grid_444_sample.shp')

    if not os.path.exists(PM_layer_path):
        print(f"Error: File not found at {PM_layer_path}")
        return None

    if not os.path.exists(PP_layer_path):
        print(f"Error: File not found at {PP_layer_path}")
        return None

    if not os.path.exists(COB_layer_path):
        print(f"Error: File not found at {COB_layer_path}")
        return None

    if not os.path.exists(GG_layer_path):
        print(f"Error: File not found at {GG_layer_path}")
        return None

    PM_sample = QgsVectorLayer(PM_layer_path, "PM Sample 444", "ogr")
    PP_sample = QgsVectorLayer(PP_layer_path, "PP Sample 444", "ogr")
    COB_sample = QgsVectorLayer(COB_layer_path, "COB Sample 444", "ogr")
    GG_sample = QgsVectorLayer(GG_layer_path, "GG Sample 444", "ogr")

    if not PP_sample.isValid():
        print(f"Error: Layer is not valid. Path: {PP_layer_path}")
        return None
    QgsProject.instance().addMapLayer(PP_sample)

    if not COB_sample.isValid():
        print(f"Error: Layer is not valid. Path: {COB_layer_path}")
        return None
    QgsProject.instance().addMapLayer(COB_sample)

    if not GG_sample.isValid():
        print(f"Error: Layer is not valid. Path: {GG_layer_path}")
        return None
    QgsProject.instance().addMapLayer(GG_sample)

    if not PM_sample.isValid():
        print(f"Error: Layer is not valid. Path: {PM_layer_path}")
        return None
    QgsProject.instance().addMapLayer(PM_sample)
    return PM_sample, PP_sample, COB_sample, GG_sample

def process_sample_data():
    system_name = platform.system()
    if system_name == "Darwin":
        output_dir = os.path.expanduser("~/Desktop/topo_chronia_tests")
    else:
        output_dir = "topo_chronia_tests"

    print(f"Operating System: {system_name}")
    os.makedirs(output_dir, exist_ok=True)
    PM, PP, COB, GG = load_sample_data()
    age = 444

    from topo_chronia.functions.createnodegrid.conversions.selections import LinesSelections
    lines_selection = LinesSelections()
    from topo_chronia.functions.createnodegrid.conversions.ridge import RIDConversion
    rid_conversion = RIDConversion()
    from topo_chronia.functions.createnodegrid.conversions.isochron import ISOConversion
    iso_conversion = ISOConversion()
    from topo_chronia.functions.createnodegrid.conversions.abandoned_arc import ABAConversion
    aba_conversion = ABAConversion()
    from topo_chronia.functions.createnodegrid.conversions.lower_subduction import LWSConversion
    lws_conversion = LWSConversion()
    from topo_chronia.functions.createnodegrid.conversions.continent import CTNConversion
    ctn_conversion = CTNConversion()
    from topo_chronia.functions.createnodegrid.conversions.passive_margin_wedge import PMWConversion
    pmw_conversion = PMWConversion()
    from topo_chronia.functions.createnodegrid.conversions.passive_margin_continent import PMCConversion
    pmc_conversion = PMCConversion()
    from topo_chronia.functions.createnodegrid.conversions.upper_subduction import UPSConversion
    ups_conversion = UPSConversion()
    from topo_chronia.functions.createnodegrid.conversions.craton import CRAConversion
    cra_conversion = CRAConversion()
    from topo_chronia.functions.createnodegrid.conversions.hot_spot import HOTConversion
    hot_conversion = HOTConversion()
    from topo_chronia.functions.createnodegrid.conversions.collision import COLConversion
    col_conversion = COLConversion()
    from topo_chronia.functions.createnodegrid.conversions.rift import RIBConversion
    rib_conversion = RIBConversion()
    from topo_chronia.functions.createnodegrid.conversions.other_margin import OTMConversion
    otm_conversion = OTMConversion()
    from topo_chronia.functions.createnodegrid.tools.feature_conversion_tools import FeatureConversionTools
    feature_conversion_tools = FeatureConversionTools()


    classes = [lines_selection,rid_conversion,iso_conversion,lws_conversion,aba_conversion,
               pmw_conversion,ctn_conversion,cra_conversion,otm_conversion,pmc_conversion, rib_conversion,
               ups_conversion,col_conversion,hot_conversion, feature_conversion_tools]
    for cls in classes:
        if hasattr(cls, 'plate_model_layer'):
            cls.plate_model_layer = PM
        else:
            cls.plate_model_layer = None

        if hasattr(cls, 'plate_polygons_layer'):
            cls.plate_polygons_layer = PP
        else:
            cls.plate_polygons_layer = None

        if hasattr(cls, 'continent_polygons_layer'):
            cls.continent_polygons_layer = COB
        else:
            cls.continent_polygons_layer = None

        if hasattr(cls, 'output_folder_path'):
            cls.output_folder_path = output_dir
        else:
            cls.output_folder_path = None
    print("Processing Lines Selection...")
    try:
        lines_selection.select_lines(age)
        print("Lines Selection: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Ridges...")
    try:
        rid_conversion.ridge_to_nodes(age)
        print("Ridges Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Isochrons...")
    try:
        iso_conversion.isochron_to_nodes(age)
        print("Isochrons Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Lower Subductions...")
    try:
        lws_conversion.lower_subduction_to_nodes(age)
        print("Lower Subductions Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Abandoned Arcs...")
    try:
        aba_conversion.abandoned_arc_to_nodes(age)
        print("Abandoned Arcs Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Passive Margin Wedges...")
    try:
        pmw_conversion.passive_margin_wedge_to_nodes(age)
        print("Passive Margin Wedges Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Continents...")
    try:
        ctn_conversion.continent_geode_to_nodes(age)
        print("Continents Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Cratons...")
    try:
        cra_conversion.craton_to_nodes(age)
        print("Cratons Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Other Margins...")
    try:
        otm_conversion.other_margin_to_nodes(age)
        print("Other Margins Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Passive Margin Continents...")
    try:
        pmc_conversion.passive_margin_continent_to_nodes(age)
        print("Passive Margin Continents Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Rifts...")
    try:
        rib_conversion.rift_to_nodes(age)
        print("Rifts Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Upper Subduction...")
    try:
        ups_conversion.upper_subduction_to_nodes(age)
        print("Upper Subducitons Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Collisions...")
    try:
        col_conversion.collision_to_nodes(age)
        print("Collisions Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Processing Hot-Spots...")
    try:
        hot_conversion.hot_spot_to_nodes(age)
        print("Hot-Spots Processing: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Merging Nodes...")
    try:
        feature_conversion_tools.create_final_nodes(age)
        print("Nodes Merging: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Cleaning Nodes (1/2)...")
    try:
        feature_conversion_tools.clean_nodes(age)
        print("Nodes vs Nodes Cleaning: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Cleaning Nodes (2/2)...")
    try:
        feature_conversion_tools.clean_nodes_hot_polygon(age)
        print("Nodes inside Hot-Spots Cleaning: Success!")
    except Exception as e:
        print(f"Error: {e}")
    print("Adding cleaned nodes layer to map...")
    all_nodes_layer_path = os.path.join(output_dir, f"all_nodes_{age}.geojson")
    all_nodes_layer = QgsVectorLayer(all_nodes_layer_path, f"All Nodes {age}", "ogr")
    QgsProject.instance().addMapLayer(all_nodes_layer)

def clear_console():
    iface.mainWindow().reloadPythonConsole()