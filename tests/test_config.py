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

FP_GOOD_0 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_0.yml')
FP_GOOD_1 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_1.yml')
FP_GOOD_2 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_2.yml')
FP_BAD_1 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_bad_0.yml')


def test_good_config_parsing():
    """Test the parsing of a good config."""
    obj = NrwalConfig(FP_GOOD_0)

    assert isinstance(obj['num_turbines'], Equation)
    assert isinstance(obj['num_turbines'].eval(), (int, float))
    assert isinstance(obj['array'], Equation)
    assert isinstance(obj['monopile'], EquationGroup)
    assert isinstance(obj['monopile_costs'], Equation)
    assert isinstance(obj['electrical'], Equation)
    assert isinstance(obj['lcoe'], Equation)
    str_dup = str(obj['electrical_duplicate']).replace('_duplicate', '')
    assert str(obj['electrical']) == str_dup
    assert id(obj['electrical']) != id(obj['electrical_duplicate'])
    assert obj.required_inputs == obj.missing_inputs
    assert len(obj.required_inputs) == 8
    assert 'site_input' in obj.required_inputs
    assert 'site_input' in obj.missing_inputs
    assert not obj.solvable

    # test input arg
    obj = NrwalConfig(FP_GOOD_0, inputs={'depth': 2 * np.ones(10)})
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 8
    assert len(obj.missing_inputs) == 7
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()

    # test input arg as dataframe
    inputs = {'depth': 2 * np.ones(10)}
    obj = NrwalConfig(FP_GOOD_0, inputs=pd.DataFrame(inputs))
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 8
    assert len(obj.missing_inputs) == 7
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()

    # test input arg setting
    obj.inputs = {'dist_p_to_s': 2 * np.ones(10)}
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 8
    assert len(obj.missing_inputs) == 6
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()
    assert (obj.inputs['dist_p_to_s'] == 2).all()

    # test input arg setting with update
    obj.inputs = pd.DataFrame({'dist_p_to_s': 3 * np.ones(10)})
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 8
    assert len(obj.missing_inputs) == 6
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()
    assert (obj.inputs['dist_p_to_s'] == 3).all()

    # test input arg setting for a single input entry through inputs property
    obj.inputs['dist_p_to_s'] = 4 * np.ones(10)
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 8
    assert len(obj.missing_inputs) == 6
    assert not obj.solvable
    assert (obj.inputs['depth'] == 2).all()
    assert (obj.inputs['dist_p_to_s'] == 4).all()

    # test setting the rest of the inputs
    obj.inputs = pd.DataFrame({k: np.ones(10) for k in obj.missing_inputs})
    assert len(obj.required_inputs) > len(obj.missing_inputs)
    assert len(obj.required_inputs) == 8
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


def test_cost_reductions_config():
    """Test config with cost reductions and parenthetical statements"""
    obj = NrwalConfig(FP_GOOD_1)
    k1 = 'array'
    k2 = '2015::array::fixed'
    k3 = '2015::cost_reductions::fixed::array_cable_2025'
    eqn1 = obj[k1]
    eqn2 = obj._eqn_dir[k2]
    eqn3 = obj._eqn_dir[k3]
    out1 = eqn1.evaluate(**{k: 1 for k in eqn1.variables})
    out2 = eqn2.evaluate(**{k: 1 for k in eqn2.variables})
    out3 = eqn3.evaluate(**{k: 1 for k in eqn3.variables})
    assert out1 == (out2 * (1 - out3))
    assert out1 != (out2 * 1 - out3)


def test_cost_reductions_interp_nearest():
    """Test config with interpolated cost reductions"""
    with pytest.raises(KeyError):
        obj = NrwalConfig(FP_GOOD_2, interp_extrap_year=False,
                          use_nearest_year=False)

    obj = NrwalConfig(FP_GOOD_2, interp_extrap_year=False,
                      use_nearest_year=True)
    k1 = 'array'
    eqn1 = obj[k1]
    truth_1 = obj._eqn_dir['2015::cost_reductions::fixed::array_cable_2030']
    truth_2 = obj._eqn_dir['2015::cost_reductions::fixed::array_cable_2025']
    assert str(truth_1) in str(eqn1.full)
    assert str(truth_2) in str(eqn1.full)

    obj = NrwalConfig(FP_GOOD_2, interp_extrap_year=True,
                      use_nearest_year=True)
    k1 = 'array'
    eqn1 = obj[k1]
    truth_1 = obj._eqn_dir['2015::cost_reductions::fixed::array_cable_2030']
    truth_2 = obj._eqn_dir['2015::cost_reductions::fixed::array_cable_2025']
    assert str(truth_1) in str(eqn1.full)
    assert str(truth_2) not in str(eqn1.full)


def test_bad_config_nesting():
    """Test the parsing of a bad config with weird nestings"""
    with pytest.raises(TypeError):
        NrwalConfig(FP_BAD_1)
