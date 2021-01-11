# -*- coding: utf-8 -*-
"""
Tests for NRWAL equation handler objects
"""
import pandas as pd
import numpy as np
import os
import pytest

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
    assert obj.required_inputs == obj.missing_inputs
    assert len(obj.required_inputs) == 7
    assert not obj.solvable

    # test input arg
    obj = NrwalConfig(FP_GOOD, inputs={'depth': 2 * np.ones(10)})
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 7
    assert len(obj.missing_inputs) == 6
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()

    # test input arg as dataframe
    obj = NrwalConfig(FP_GOOD, inputs=pd.DataFrame({'depth': 2 * np.ones(10)}))
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 7
    assert len(obj.missing_inputs) == 6
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()

    # test input arg setting
    obj.inputs = {'dist_p_to_s': 2 * np.ones(10)}
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 7
    assert len(obj.missing_inputs) == 5
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()
    assert (obj.inputs['dist_p_to_s'] == 2).all()

    # test input arg setting with update
    obj.inputs = pd.DataFrame({'dist_p_to_s': 3 * np.ones(10)})
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 7
    assert len(obj.missing_inputs) == 5
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()
    assert (obj.inputs['dist_p_to_s'] == 3).all()

    # test input arg setting for a single input entry through inputs property
    obj.inputs['dist_p_to_s'] = 4 * np.ones(10)
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 7
    assert len(obj.missing_inputs) == 5
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()
    assert (obj.inputs['dist_p_to_s'] == 4).all()

    # test setting the rest of the inputs
    obj.inputs = pd.DataFrame({k: np.ones(10) for k in obj.missing_inputs})
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 7
    assert not obj.missing_inputs
    assert obj.solvable

    # test evaluation
    assert not obj.outputs
    outputs = obj.evaluate()
    assert isinstance(outputs, dict)
    assert 'monopile' not in outputs
    assert 'num_turbines' not in outputs
    assert isinstance(outputs['lcoe'], np.ndarray)
    assert len(outputs['lcoe']) == 10
    assert np.allclose(outputs['lcoe'], 1.35261086e15 * np.ones(10))

    # test bad evaluation
    obj.inputs = None
    with pytest.raises(RuntimeError):
        obj.evaluate()
