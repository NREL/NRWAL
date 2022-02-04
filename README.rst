*****************
Welcome to NRWAL!
*****************

.. image:: https://github.com/NREL/NRWAL/workflows/Documentation/badge.svg
    :target: https://nrel.github.io/NRWAL/

.. image:: https://github.com/NREL/NRWAL/workflows/Pytests/badge.svg
    :target: https://github.com/NREL/NRWAL/actions?query=workflow%3A%22Pytests%22

.. image:: https://github.com/NREL/NRWAL/workflows/Lint%20Code%20Base/badge.svg
    :target: https://github.com/NREL/NRWAL/actions?query=workflow%3A%22Lint+Code+Base%22

.. image:: https://img.shields.io/pypi/pyversions/NREL-NRWAL.svg
    :target: https://pypi.org/project/NREL-NRWAL/

.. image:: https://badge.fury.io/py/NREL-NRWAL.svg
    :target: https://badge.fury.io/py/NREL-NRWAL

.. image:: https://anaconda.org/nrel/nrel-NRWAL/badges/version.svg
    :target: https://anaconda.org/nrel/nrel-NRWAL

.. image:: https://anaconda.org/nrel/nrel-NRWAL/badges/license.svg
    :target: https://anaconda.org/nrel/nrel-NRWAL

.. image:: https://codecov.io/gh/nrel/NRWAL/branch/main/graph/badge.svg?token=NB29X039VU
   :target: https://codecov.io/gh/nrel/NRWAL

.. image:: https://zenodo.org/badge/319377095.svg
   :target: https://zenodo.org/badge/latestdoi/319377095

.. image:: https://mybinder.org/badge_logo.svg
    :target: https://mybinder.org/v2/gh/NREL/NRWAL/HEAD


.. inclusion-intro

The National Renewable Energy Laboratory Wind Analysis Library (NRWAL):

#. A library of offshore wind cost equations (plus new energy technologies like marine hydro!)
#. Easy equation manipulation without editing source code
#. Full continental-scale integration with the NREL Renewable Energy Potential Model (reV)
#. Ready-to-use configs for basic users
#. Dynamic python tools for intuitive equation handling
#. One seriously badass sea unicorn

To get started with NRWAL, check out the `NRWAL Config documentation <https://nrel.github.io/NRWAL/_autosummary/NRWAL.handlers.config.NrwalConfig.html#nrwal-handlers-config-nrwalconfig>`_ or the `NRWAL example notebook <https://github.com/NREL/NRWAL/blob/main/examples/example.ipynb>`_. You can also launch the notebook in an interactive jupyter shell right in your browser without any downloads or software using `binder <https://mybinder.org/v2/gh/NREL/NRWAL/HEAD>`_. 

Ready to build a model with NRWAL but don't want to contribute to the library? No problem! Check out the example getting started project `here <https://github.com/NREL/NRWAL/tree/main/getting_started>`_.

Here is the important stuff:

 - `The NRWAL Equation Library <https://github.com/NREL/NRWAL/tree/main/NRWAL/analysis_library>`_.
 - `Default NRWAL Configs <https://github.com/NREL/NRWAL/tree/main/NRWAL/default_configs>`_.

Installing NRWAL
================

Option 1: Install from PIP or Conda (recommended for analysts):
---------------------------------------------------------------

1. Create a new environment:
    ``conda create --name nrwal``

2. Activate directory:
    ``conda activate nrwal``

3. Install reVX:
    1) ``pip install NREL-NRWAL`` or
    2) ``conda install nrel-nrwal --channel=nrel``

Option 2: Clone repo (recommended for developers)
-------------------------------------------------

1. from home dir, ``git clone https://github.com/NREL/NRWAL.git``
    1) enter github username
    2) enter github password

2. Create ``NRWAL`` environment and install package
    1) Create a conda env: ``conda create -n nrwal``
    2) Run the command: ``conda activate nrwal``
    3) cd into the repo cloned in 1.
    4) prior to running ``pip`` below, make sure the branch is correct (install
       from master!)
    5) Install ``NRWAL`` and its dependencies by running:
       ``pip install .`` (or ``pip install -e .`` if running a dev branch
       or working on the source code)

NRWAL Variables for Offshore Wind (OSW)
=======================================

.. list-table:: NRWAL Inputs
    :widths: auto
    :header-rows: 1

    * - Variable Name
      - Long Name
      - Source
      - Units
    * - `aeff`
      - Array Efficiency
      - `array_efficiency` input layer, computed from ORBIT
      - `%`
    * - `capex_multi`
      - CAPEX Multiplier
      - Supplied by user
      - unit-less
    * - `depth`
      - Water depth (positive values)
      - `bathymetry` input layer
      - m
    * - `dist_a_to_s`
      - Distance from assembly area to site
      - Computed from `assembly_area` input layer
      - km
    * - `dist_op_to_s`
      - Distance from operating port to site
      - `ports_operations` input layer
      - km
    * - `dist_p_to_a`
      - Distance from port (construction no-limit) to assembly area
      - `assembly_area` input layer
      - km
    * - `dist_p_to_s`
      - Distance from construction port to site
      - `ports_construction` input layer
      - km
    * - `dist_p_to_s_nolimit`
      - Distance from no-limit construction port to site
      - `ports_construction_nolimit` input layer
      - km
    * - `dist_s_to_l`
      - Distance site to nearest land
      - `dist_to_coast` input layer
      - km
    * - `fixed_downtime`
      - Average weather downtime for fixed structure turbines
      - `weather_downtime_fixed_bottom` input layer
      - fraction
    * - `floating_downtime`
      - Average weather downtime for floating structure turbines
      - `weather_downtime_floating` input layer
      - fraction
    * - `gcf`
      - Gross capacity factor
      - Computed by reV / SAM with losses == 0
      - unit-less
    * - `hs_average`
      - Significant wave height to determine weather downtime
      - `weather_downtime_mean_wave_height_buoy` input layer
      - m
    * - `num_turbines`
      - Number of turbines in array
      - Supplied by user
      - unit-less
    * - `transmission_multi`
      - Tranmission cost multiplier
      - Supplied by user
      - unit-less
    * - `turbine_capacity`
      - Capacity of each turbine in the array
      - Supplied by user
      - MW

Recommended Citation
====================

If using the NRWAL software (replace with current version and DOI):

 - Grant Buster, Jake Nunemaker, and Michael Rossol. The National Renewable Energy Laboratory Wind Analysis Libray (NRWAL). https://github.com/NREL/NRWAL (version v0.0.2), 2021. https://doi.org/10.5281/zenodo.4705961.

If using the Offshore Wind (OSW) cost equations:

 - Beiter, Philipp, Walter Musial, Aaron Smith, Levi Kilcher, Rick Damiani, Michael Maness, Senu Sirnivas, et al. “A Spatial-Economic Cost-Reduction Pathway Analysis for U.S. Offshore Wind Energy Development from 2015–2030.” National Renewable Energy Lab. (NREL), Golden, CO (United States), September 1, 2016. https://doi.org/10.2172/1324526. https://www.nrel.gov/docs/fy16osti/66579.pdf.

If using the marine energy reference model (RM) cost models:

 - https://energy.sandia.gov/programs/renewable-energy/water-power/projects/reference-model-project-rmp/
 - Jenne, D. S., Y. H. Yu, and V. Neary. “Levelized Cost of Energy Analysis of Marine and Hydrokinetic Reference Models: Preprint.” National Renewable Energy Lab. (NREL), Golden, CO (United States), April 24, 2015. https://www.osti.gov/biblio/1215196-levelized-cost-energy-analysis-marine-hydrokinetic-reference-models-preprint.
