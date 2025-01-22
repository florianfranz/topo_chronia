<table>
  <tr>
    <td style="width: 40%; text-align: center;">
      <img src="PAN_logo.svg" alt="PAN" width="200"/>
    </td>
    <td style="width: 60%;">
      <h1>TopoChronia: Digital Elevation Models of the Earth Past based on the PANALESIS Plate Tectonic Model</h1>
    </td>
  </tr>
</table>



The TopoChronia Plugin is a free open source plugin 
for QGIS that converts plate tectonics input features into fully quantified 
maps of the Earth past topography (palaeotopography) and geography (palaeogeography),
using the PANALESIS plate tectonic model.

TopoChronia uses a unique approach to create a synthetic topography for selected
geological settings described in PANALESIS, including mid-oceanic ridges, isochrons,
passive margins, active margins, cratons, hot-spots, abandoned arcs, continents, rifts,
basins and other margins.

Input features (lines) are converted into an irregular grid of nodes with elevation
values, from which a Digital Elevation Model (DEM) is interpolated using the QGIS 
Triangulated Irregular Network (TIN). The oceanic volume of this DEM is then compared 
to the present-day volume, in order to assess the difference of sea-level.

![workflow](workflow.png)
## Installation

TopoChronia runs as a QGIS plugin. It can be used on QGIS version 3.36 or higher.

There are two ways to install the plugin:

* [WIP] : Directly from QGIS:
  - Open QGIS → Plugins → Manage and Install Plugins → All → Search for 'TopoChronia' → Install
* Manual installation:
  - Go to the [releases folder](./releases) and download the desired version as a .zip file. 
  - Open QGIS → Plugins → Manage and Install Plugins → Install from .zip
  - Select the downloaded .zip folder and click on "Install".

Apart from native QGIS python libraries, the plugin also requires the following Python packages: `geopy`, `pandas`,
`processing`,`PyQt5`. For more information, about versions are available in the  [requirements.txt](./requirements.txt).  These libraries will be automatically installed alongside the plugin itself.

Once installed, the plugin should be listed under the "Plugin", and there should be three icons appearing on the QGIS 
toolbar as in the picture below:

![img.png](img.png)

Each of these icons allows to access the three main phases required by TopoChronia to process plate tectonics features 
from PANALESIS into palaeotopographic and palaeogeographic maps:

1. Phase 0: Check Configuration
2. Phase I: Create Node Grid
3. Phase II: Interpolate Raster

More details about each phase are provided in the "Functionalities" section below.

## Functionalities

For higher modularity, TopoChronia is divided into three main phases:

### Phase 0: Check Configuration
This first phase checks that all files required for processing are loaded in QGIS and fulfill requirements 
(geometry, fields, values).

TopoChronia requires the following input files from PANALESIS:
- Plate Model (PM): Lines describing the model features (see more details below).
- Plate Polygons (PP): Polygons describing the tectonic plates
- Continent-Ocean Boundary (COB): Polygons describing the boundary between continental and oceanic crust
- Geodesic Grid: Grid of points equally distant from one another.
- Accretion Rates: Table with plate veolicities and accretion rates for each of the PANALESIS ages.

If all input files pass the check, this initial phase yields two outputs:
- A list of common reconstruction ages to all input files to base further processing.
- A dictionary of all input files location used later in the processing.

Should any check fail, the user will be informed about the issues. For fields that are not found, if the issue is linked
to the field names, a dialog will open and allow the user to assign the correct field and change its name.

Please note that if you wish to change the input files, you need to do all checks again.

### Phase 1: Create Node Grid

Once the checks are passed, the nodes conversion phase can start. The user can select one or more reconstruction age(s).
The processing steps are the following:

* Prepare data: All PP and COB are aggregated for the reconstruction age.
* Convert features: All settings are converted from the PM (lines) into points with synthetic topographic values.
* Merge nodes: Nodes from all settings are merged into a single nodes file.
* Clean nodes: To avoid clash between different settings at the same location, nodes are cleaned.

![PAN_nodes.png](PAN_nodes.png)
The picture above shows an example of the nodes distribution for the present-day PANALESIS reconstruction.

### Phase 2: Interpolate Raster

The final phase consists of interpolating a raster from the clean nodes layer. We use the QGIS
Triangulated Network (TIN) as it is the best open-source method to render topography and estimate oceans
volumes (Franziskakis et al., in prep).

This last phase is also divided into the following steps:

* Interpolate raster: perform the initial interpolation with synthetic topographic values.
* Correct water load: calculates oceanic volume, and performs corrections using the present-day volume as a reference. Adjust sea-level based on corrections.
* Interpolate final raster: Apply sea-level correction to nodes elevation values and interpolate a final raster with the corrected values.


## Documentation


## Contributing to the development


## Authors

* **Florian Franziskakis** *florian.franziskakis@unige.ch*
* **Christian Vérard**
* **Grégory Giuliani**

## License
This plugin is licensed under the GNU General Public License, version 2 or later (GPLv2+). 
You can view the full license text in the [LICENSE.txt](./LICENSE.txt).

## How to cite

JOSS reference



