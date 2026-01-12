---
title: 'TopoChronia: A QGIS plugin for the creation of fully quantified palaeogeographic maps'
tags:
  - Python
  - QGIS
  - tectonics
  - palaeogeography
  - palaeotopography
authors:
  - name: Florian Franziskakis
    orcid: 0000-0001-6855-0269
    affiliation: 1
  - name: Christian Vérard
    orcid: 0000-0001-9560-6969
    affiliation: 2
  - name: Sébastien Castelltort
    orcid: 0000-0002-6405-4038
    affiliation: 2
  - name: Grégory Giuliani
    orcid: 0000-0002-1825-8865
    affiliation: 1


affiliations:
 - name: enviroSPACE group, Institute for Environmental Sciences, University of Geneva
   index: 1
 - name: Earth Surface Dynamics group, Department of Earth Sciences, University of Geneva
   index: 2

date: 14 April 2025
bibliography: paper.bib
---

## Summary

Reconstructing the palaeogeography and palaeotopography of the Earth has been a challenge since the advent of the plate 
tectonics theory in the 1960s. With the development of geographic information systems (GIS), many plate tectonics models have 
been created and allowed researchers to reconstruct the movements of plates back in time (up to 1 billion years for 
some models), based on geological evidence found in the present-day Earth.

We present `TopoChronia`, a QGIS plugin that converts input data from plate tectonic models into quantified and synthetic 
topography. This plugin is optimized to work with the PANALESIS model, because it is the only one currently providing 
sufficient information in terms of geological features to reconstruct a fully quantified topography.

## Statement of need

Most of the plate tectonic models and reconstructions use the standalone GPlates software [@gurnis2012],
which allows users to move plates in time steps and export geospatial data layers. These layers can later be used in 
GIS software, such as the QGIS plugin `TerraAntiqua` [@aminov2023], to reconstruct 
palaeotopography. Other models such as PANALESIS [@verard2019], are created and have processing functionalities that use commercial 
GIS software (ArcGIS). A preliminary version of the code to generate topography of the Earth based on PANALESIS past was developed 
as an ArcGIS extension, written in Visual Basic .NET but never published. It is now fully updated as a QGIS plugin in 
Python.

Constraining the palaeotopography is critical in fields such as climate and mantle dynamics modelling, as the elevation 
of land and bathymetry of oceans are used to set the initial conditions of models [@bello2015;
@ragon2023]. 
Quantifying the Earth’s topography and its evolution also allows to estimate the volume of rocks being eroded, for instance 
through sediment discharge [@lyster2020], as weathering or silicate rocks is a key controlling 
factor of CO2 concentration in the atmosphere over geological time scales [@molnar1990;
@macdonaldArccontinentCollisionsTropics2019].

The traditional method to create palaeotopographic maps [@scotese2021] is to use present-day
geological evidence, rotate them back to their past location and derive semi-quantitative elevation typical of the environment they depict.
Another method is to take the present-day Earth topography of an area of 
interest as it is, and rotate it back in time to its past location [@aminov2023]. 
These methods have limitations, including that present-day features are the result of millions of years of plate movements and 
cannot be “copy-pasted” as such, and that one time step might not be coherent with the previous and next ones.

We provide here an open-source plugin to reconstruct palaeotopography and palaeogeography "from scratch" using the
PANALESIS model, which is based on present-day geological evidence and uses a dual-control approach, meaning that one
reconstruction is based on the state of the Earth in the previous time-step, and influences the next step. 
Synthetic values for elevations are generated in nodes (points) related to geological settings and based on their 
present-day counterparts [@verard2017]. The output maps of `TopoChronia` can be used for 
modelling purposes and to reconstruct sea-level curves, over the Phanerozoic and beyond [@verard2015;@franziskakis2025a].

## Functionalities

`TopoChronia` is divided into three main parts:

1. Check Configuration
  - Assess input data files (geometry, field names, values)
  - Perform manual corrections if necessary, for wrongly named fields
  - Define output folder path
  - Extract available reconstruction ages  

2. Create Node Grid  
  - Select input lines from plate model file
  - Convert mid-oceanic ridge and isochron features and interpolate a preliminary raster for oceans
  - Convert all other features (abandoned arcs, continents, cratons, lower subduction, upper subduction, passive margin wedges,  
      continent sides, hot-spots, other margins, rifts, and collision zones)
  - Merge all nodes and clean to avoid clashing between features  

3. Interpolate to Raster
  - Interpolate global raster
  - Calculate oceanic volume under sea-level (elevation below 0m)
  - Calculate required sea-level increase to match present-day oceanic volume
  - Correct water load using Airy's model to adjust for sea-level increase
  - Perform final raster interpolation with new sea-level  

Each reconstruction will yield the following outputs:

- A palaeogeographic map in geotiff format with cylindrical equal-area projection (ESRI:54034): `raster_final_filled_{age}.tif`
- A text file summarizing sea-level information **before** water load correction (initial volume and area, added water column, sea-level increase and subsidence): `water_load_correction_summary.txt`
- A text file summarizing sea-level information **after** water load correction: `water_load_correction_summary_f.txt`
- All nodes both in EPSG:4326 and ESRI:54034 projections: `all_nodes_{age}.geojson` and `reproj_all_nodes_{age}.geojson` 
- All other processing products from line to points for each setting.

## Acknowledgements

The authors acknowledge financial support from the Swiss National Science Foundation (SNSF) under 
[Sinergia grant #213539](https://data.snf.ch/grants/grant/213539): _Long-term evolution of the Earth from the base of the mantle to the top of the atmosphere: 
Understanding the mechanisms leading to ‘greenhouse’ and ‘icehouse’ regimes._

The authors would like to thank Niklas Werner, Felipe Carlos and Bastien Deriaz for their help in testing the plugin.

## References