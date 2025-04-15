---
title: 'TopoChronia: A QGIS Plugin to Create Topographic and Geographic Maps of the Earth Geological Past from the PANALESIS Plate Tectonic Model'
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

Most of the plate tectonic models and reconstructions use the standalone GPlates software (@gurnisPlateTectonicReconstructions2012),
which allows users to move plates in time steps and export geospatial data layers. These layers can later be used in 
GIS software, such as the QGIS plugin `TerraAntiqua` (@aminovPaleogeographicReconstructionsUsing2023), to reconstruct 
palaeotopography. Other models, such as PANALESIS (@verardPanalesisGlobalSynthetic2019a), are created and have processing functionalities that use commercial 
GIS software (ArcGIS). A preliminary version of the code to generate topography of the Earth based on PANALESIS past was developed 
as an ArcGIS extension, written in Visual Basic .NET but never published. It is now fully updated as a QGIS plugin in 
Python.

Constraining the palaeotopography is critical in fields such as climate and mantle dynamics modelling, as the elevation 
of land and bathymetry of oceans are used to set the initial conditions of models (@belloAssessingRoleSlab2015,
@ragonAlternativeClimaticSteady2023). 
Quantifying the Earth’s topography and its evolution also allows to estimate the volume of rocks being eroded, for instance 
through sediment discharge (@lysterPredictingSedimentDischarges2020), as weathering or silicate rocks is a key controlling 
factor of CO₂ concentration in the atmosphere over geological time scales (@molnarLateCenozoicUplift1990,
@macdonaldArccontinentCollisionsTropics2019).

The traditional method to generate palaeotopographic maps is to take the present-day Earth topography of an area of 
interest as it is, and rotate it back in time to its past location. This has limitations, including that present-day 
features are the result of millions of years of plate movements and cannot be “copy-pasted”. Moreover, most of the models 
on which these reconstructions are based only use a single-control approach, which does not provide time-consistent 
reconstructions.

We provide here an open-source plugin to reconstruct palaeotopography and palaeogeography "from scratch". 
Synthetic values for elevations are generated in nodes (points) related to geological settings and based on their 
present-day counterparts (@verardStatisticsEarthsTopography2017). The output maps of `TopoChronia` can be used for 
modelling purposes and to reconstruct sea-level curves, over the Phanerozoic and beyond (@verard3DPalaeogeographicReconstructions2015)

## Functionalities

`TopoChronia` is divided into three main parts:

1.	Check Configuration → Assesses the input data files (geometry, fields, values) and allow manual corrections if 
necessary.
2.	Create Node Grid → Converts input data (lines and polygons) into points containing elevation values, based on the 
age of various types of geological settings, including mid-oceanic ridges, 
isochrons, abandoned arcs, continents, cratons, lower subduction, upper subduction, passive margin wedges and continents 
sides, hot-spots, other margins, rifts and collision zones. Once processed, all nodes are merged and cleaned to avoid
clashing between features.
3.	Interpolate to Raster → Creates a raster layer by interpolating the elevation values form the nodes, including 
post-processing steps such as correcting for water load added to match the reference volume.


## Acknowledgements

The authors acknowledge financial support from the Swiss National Science Foundation (SNSF) under 
[Sinergia grant #213539](https://data.snf.ch/grants/grant/213539): _Long-term evolution of the Earth from the base of the mantle to the top of the atmosphere: 
Understanding the mechanisms leading to ‘greenhouse’ and ‘icehouse’ regimes._

The authors would like to thank Niklas Werner, Felipe Carlos and Bastien Deriaz for their help in testing the plugin.

## References