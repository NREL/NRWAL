# -*- coding: utf-8 -*-
"""
The National Renewable energy laboratory Wind Analysis Library (NRWAL)
"""
from __future__ import print_function, division, absolute_import
import os

from NRWAL.utilities.utilities import (NRWAL_DIR, NRWAL_ANALYSIS_DIR,
                                       NRWAL_CONFIG_DIR)
from NRWAL.version import __version__
from NRWAL.handlers.config import NrwalConfig
from NRWAL.handlers.equations import Equation
from NRWAL.handlers.groups import EquationGroup, VariableGroup
from NRWAL.handlers.directories import EquationDirectory

__author__ = """Jacob Nunemaker"""
__email__ = "jacob.nunemaker@nrel.gov"
