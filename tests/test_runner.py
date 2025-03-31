import importlib
import sys
import os


def run_test(function_name):
    """Loads test_plugin, runs a function, and resets the environment afterwards."""
    original_sys_path = list(sys.path)

    existing_modules = set(sys.modules.keys())

    try:
        test_plugin = importlib.import_module("topo_chronia.tests.test_plugin")
        if hasattr(test_plugin, function_name):
            getattr(test_plugin, function_name)()
        else:
            print(f"Error: Function '{function_name}' not found in test_plugin.")

    except Exception as e:
        print(f"Error running test: {e}")

    finally:
        new_modules = set(sys.modules.keys()) - existing_modules
        for mod in new_modules:
            del sys.modules[mod]
        sys.path = original_sys_path
        try:
            import topo_chronia
            import topo_chronia.dialogs
        except ModuleNotFoundError:
            print("Warning: topo_chronia was removed from memory, reloading it...")
            importlib.import_module("topo_chronia")
        import gc
        gc.collect()
