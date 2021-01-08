# -*- coding: utf-8 -*-
"""
Tests for NRWAL equation handler objects
"""
import os

from NRWAL.config.config import NrwalConfig
from NRWAL.handlers.equations import Equation
from NRWAL.handlers.groups import EquationGroup

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data/')

FP_GOOD = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_00_good.yml')


def test_good_config_parsing():
    """Test the parsing of a good config."""
    obj = NrwalConfig(FP_GOOD)

    assert isinstance(obj['num_turbines'], float)
    assert isinstance(obj['array'], Equation)
    assert isinstance(obj['monopile'], EquationGroup)
    assert isinstance(obj['monopile_costs'], Equation)
    assert isinstance(obj['electrical'], Equation)
    assert isinstance(obj['lcoe'], Equation)

    assert str(obj['electrical']) == str(obj['electrical_duplicate'])
    assert id(obj['electrical']) != id(obj['electrical_duplicate'])
