import subprocess
import sys
import os
from pathlib import Path


def install_dependencies():
    """Install necessary libraries for the plugin."""
    plugin_dir = Path(__file__).parent.parent  # Get plugin directory
    requirements_path = plugin_dir / "requirements.txt"  # Assuming you have a requirements.txt

    # Check if requirements.txt exists
    if not requirements_path.exists():
        raise FileNotFoundError(f"requirements.txt not found in {plugin_dir}")

    # Prepare the OSGeo environment path
    qgis_path = str(os.path.dirname(sys.executable))  # Get QGIS executable path
    o4w_env_path = os.path.join(qgis_path, "o4w_env.bat")  # The OSGeo shell script to set the environment

    # Create the bat file content
    bat_file_content = f"""
    @echo off
    call "{o4w_env_path}"
    call "py3_env"
    call python -m pip install -r "{requirements_path}"
    exit
    @echo on
    """

    bat_file_path = str(plugin_dir / "install_deps.bat")

    # Write the bat file
    with open(bat_file_path, "w") as f:
        f.write(bat_file_content)

    # Run the bat file to install dependencies
    subprocess.run([bat_file_path], check=True)

    # Remove the bat file after execution (optional)
    os.remove(bat_file_path)
