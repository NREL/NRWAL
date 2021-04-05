*************************************
Welcome to the NRWAL default configs!
*************************************

`Equation Library <https://github.com/NREL/NRWAL/tree/main/NRWAL/analysis_library>`_.

`Default NRWAL Configs <https://github.com/NREL/NRWAL/tree/main/NRWAL/default_configs>`_.

`NRWAL Code Base <https://github.com/NREL/NRWAL/tree/master/NRWAL>`_.

Default Configurations
======================

The files in this directory represent complete NRWAL configurations that can be
used as examples or templates for building new configurations. NRWAL currently
includes recreations of the ORCA model and the folders "2015" and "2019"
correspond to original version of ORCA and the updated version, respectively. 

Examples
========

Simple Configuration File
-------------------------

The file `./2015/jacket_10MW_2015.yaml` is a simple example of running NRWAL
without any cost reductions. The file is broken into sections:

.. code-block::

   # Parameters
   fixed_charge_rate:
     0.071
   
   # CapEx Equations
   turbine:
     2015::turbine::jacket_tower + 2015::turbine::rna  <--- NRWAL equations

   # CapEx Aggregation
   support:
     ./standard_aggregation.yaml::support  <--- External equation reference
                                                See 'standard_aggregation.yaml'

   ...

   lcoe:
     ./standard_aggregation.yaml::lcoe

Cost Reductions
---------------

The file `./2019/monopile_15MW_2025.yaml` includes cost reductions applied at
the subcomponent level:

.. code-block::

   # CapEx Equations
   cost_reductions:
     2019::cost_reductions::fixed
   turbine:
     2019::turbine::tower + 2019::turbine::rna * (1 - cost_reductions::rna_2025)

Interpolation
-------------

NRWAL can interpolate between turbine sizes and cost reduction years. An
example of this is seen in file `./2019/jacket_8MW_2017.yaml`.

.. code-block::

   # CapEx Equations
   turbine_install:
     2019::turbine_install::jacket_8MW  <--- NRWAL will interpolate between
                                             'jacket_6MW' and 'jacket_10MW'
