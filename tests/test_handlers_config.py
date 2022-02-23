# -*- coding: utf-8 -*-
"""
Tests for NRWAL equation handler objects
"""
import yaml
import pandas as pd
import numpy as np
import os
import pytest

from NRWAL.handlers.config import NrwalConfig
from NRWAL.handlers.equations import Equation
from NRWAL.handlers.groups import EquationGroup

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data/')

FP_BAD_0 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_bad_0.yml')
FP_BAD_1 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_bad_1.yml')
FP_BAD_2 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_bad_2.yaml')
FP_BAD_3 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_bad_3.yaml')
FP_BAD_4 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_bad_4.yaml')

FP_GOOD_0 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_0.yml')
FP_GOOD_1 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_1.yml')
FP_GOOD_2 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_2.yml')
FP_GOOD_3 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_3.yml')
FP_GOOD_4 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_4.yaml')
FP_GOOD_5 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_5.yaml')
FP_GOOD_6 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_6.yaml')
FP_GOOD_7 = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_good_7.yaml')
FP_NP = os.path.join(TEST_DATA_DIR, 'test_configs/test_config_np.yml')


@pytest.fixture()
def test_equations_directory():
    """Temporarily set the NRWAL equations directory to the test version. """
    # Startup
    previous_dir = NrwalConfig.DEFAULT_DIR
    NrwalConfig.DEFAULT_DIR = os.path.join(TEST_DATA_DIR, 'test_eqns_dir')

    # test happens here
    yield

    # teardown (i.e. return equations directory to original dir)
    NrwalConfig.DEFAULT_DIR = previous_dir


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

    truth = (((obj.array * obj.export + obj.grid) + obj.inputs['site_input'])
             * obj.fixed_charge_rate.eval())
    assert np.allclose(outputs['lcoe'], truth)

    # test bad evaluation
    obj.inputs = None
    with pytest.raises(RuntimeError):
        obj.evaluate()


def test_cost_reductions_config():
    """Test config with cost reductions and parenthetical statements"""
    obj = NrwalConfig(FP_GOOD_1)
    k1 = 'array'
    k2 = 'osw_2015::array::fixed'
    k3 = 'osw_2015::cost_reductions::fixed::array_cable_2025'
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
    cost_red_str = 'osw_2015::cost_reductions::fixed::array_cable_{}'
    truth_1 = obj._eqn_dir[cost_red_str.format(2030)]
    truth_2 = obj._eqn_dir[cost_red_str.format(2025)]
    assert str(truth_1) in str(eqn1.full)
    assert str(truth_2) in str(eqn1.full)

    obj = NrwalConfig(FP_GOOD_2, interp_extrap_year=True,
                      use_nearest_year=True)
    k1 = 'array'
    eqn1 = obj[k1]
    truth_1 = obj._eqn_dir[cost_red_str.format(2030)]
    truth_2 = obj._eqn_dir[cost_red_str.format(2025)]
    assert str(truth_1) in str(eqn1.full)
    assert str(truth_2) not in str(eqn1.full)


def test_bad_config_nesting():
    """Test the parsing of a bad config with weird nestings"""
    with pytest.raises(TypeError):
        NrwalConfig(FP_BAD_0)


def test_bad_config_parens():
    """Test the parsing of config with multiple parenthesis (cant parse
    right now)"""
    with pytest.raises(ValueError):
        NrwalConfig(FP_BAD_1)


def test_config_math():
    """Test more complex math in config expressions"""
    obj = NrwalConfig(FP_GOOD_3)
    inputs = {k: 1 for k in obj.required_inputs}
    obj.eval(inputs)
    fcr = obj['fixed_charge_rate'].eval()
    arr = obj['array']
    exp = obj['export']
    grid = obj['grid']

    # 0 or 1 can reduce math to useless tests
    assert (fcr != 0) & (fcr != 1)
    assert (arr != 0) & (arr != 1)
    assert (exp != 0) & (exp != 1)
    assert (grid != 0) & (grid != 1)

    np.allclose(obj['math1'], arr - exp + grid)
    np.allclose(obj['math2'], arr - exp + grid - exp)
    np.allclose(obj['math3'], arr + exp - grid)
    np.allclose(obj['math4'], arr + exp - 1)
    np.allclose(obj['math5'], arr * exp - 1)
    np.allclose(obj['math6'], arr * (exp - grid) / grid)
    np.allclose(obj['math7'], arr / exp + grid)
    np.allclose(obj['math8'], arr + exp / grid)
    np.allclose(obj['math9'], arr + exp * grid)
    np.allclose(obj['math10'], arr + exp * grid ** 2)
    np.allclose(obj['math11'], arr + exp * grid ** 0.5)
    np.allclose(obj['math12'], (arr + exp) * (grid + exp))
    np.allclose(obj['math13'], ((arr + exp) * grid) ** 0.5)
    np.allclose(obj['math14'], ((arr + exp) * grid) + (grid + exp) ** 0.5)
    np.allclose(obj['math15'], (fcr - 1) * (arr + exp + grid))
    np.allclose(obj['math16'], (1 - fcr) * (obj['math4'] + exp + grid))


def test_complex_config():
    """Test the evaluation of a complex config."""
    with open(FP_GOOD_4, 'r') as f:
        config = yaml.safe_load(f)

    obj = NrwalConfig(FP_GOOD_4)

    assert not any(set(config.keys()) - set(obj.keys()))
    assert not any(set(config.keys()) - set(obj._raw_config.keys()))

    out = obj.evaluate({k: 2 for k in obj.required_inputs})
    for k, v in out.items():
        assert k in config
        assert k in obj._raw_config
        assert v is not None

    assert obj.solved
    assert np.allclose(obj['tmp'] * obj['factor'], obj['cons_financing'])


def test_config_reference_flat():
    """Test a config with reference to equations from another config"""

    obj_4 = NrwalConfig(FP_GOOD_4)
    obj_5 = NrwalConfig(FP_GOOD_5)

    assert obj_4['support'].full == obj_5['support'].full
    assert obj_4['install'].full == obj_5['install'].full
    assert obj_4['electrical'].full == obj_5['electrical'].full
    assert obj_4['subcomponents'].full == obj_5['subcomponents'].full

    out_4 = obj_4.evaluate({k: 2 for k in obj_4.required_inputs})
    out_5 = obj_5.evaluate({k: 2 for k in obj_5.required_inputs})
    for k, v in out_4.items():
        assert np.allclose(v, out_5[k])


def test_config_reference_bad():
    """Test a config with illegal reference to nested equations from
    another config"""
    with pytest.raises(AssertionError):
        _ = NrwalConfig(FP_BAD_2)


def test_bad_circular():
    """Test that NRWAL raises an error for circular equation references"""
    with pytest.raises(RuntimeError):
        NrwalConfig(FP_BAD_3)

    with pytest.raises(RuntimeError):
        NrwalConfig(FP_BAD_4)


def test_leading_negative():
    """Test config with equations that have leading negative signs or
    negative signs attached to variables"""
    obj = NrwalConfig(FP_GOOD_6)
    assert '()' not in obj['test1'].full
    assert '()' not in obj['test2'].full
    assert '()' not in obj['test3'].full
    assert '()' not in obj['test4'].full
    assert '()' not in obj['test5'].full
    assert '()' not in obj['test6'].full

    out = obj.evaluate({k: 2 for k in obj.required_inputs})
    bos = out['bos']
    install = out['install']
    pslt = out['pslt']
    turbine = out['turbine']

    assert np.allclose(obj['test1'], bos - install + pslt + turbine)
    assert np.allclose(obj['test2'], -bos - install + pslt + turbine)
    assert np.allclose(obj['test3'], install - bos + pslt + turbine)
    assert np.allclose(obj['test4'], -(bos - install) + pslt + turbine)
    assert np.allclose(obj['test5'], -(bos * install) + pslt + turbine)
    assert np.allclose(obj['test6'], -(bos * install) + pslt * -turbine)


# pylint: disable=W0613
def test_global_variables_used_for_eval(test_equations_directory):
    """Test that the global variables dict is populated and used correctly. """
    obj = NrwalConfig(FP_GOOD_7)
    assert 'an_important_constant' in obj.global_variables

    out = obj.evaluate()
    assert 'model_out' in out


def test_numpy():
    """Test numpy operations in nrwal config"""
    obj = NrwalConfig(FP_NP)

    assert len(obj['max_test'].variables) == 1
    assert obj['max_test'].variables[0] == 'input1'
    assert (obj['max_test'].eval(input1=[1, 3, 2])) == 91

    assert str(obj['max_electrical']) == 'max_electrical(array, export)'
    assert '>' not in str(obj.missing_inputs)
    assert str(obj['max_export']) == 'max_export(export)'
    assert 'axis' not in str(obj.missing_inputs)

    assert 'arr_xp' not in obj.missing_inputs
    assert 'arr_fp' not in obj.missing_inputs

    inputs = {k: 10 for k in obj.missing_inputs}
    inputs['depth'] = np.random.uniform(50, 100, 5)
    inputs['dist_s_to_l'] = np.random.uniform(50, 100, 5)
    inputs['x'] = [0.5, 1.5, 2.5]  # should interp to [1, 3, 2]

    outs = obj.eval(inputs)

    max_export = outs['max_export']
    max_electrical = outs['max_electrical']
    export = outs['export']

    assert not any(max_electrical > export)
    assert max_export == np.max(export)

    # test interp on arrays
    assert np.allclose(outs['interp'], [101, 103, 102])

    # test a list entry to a numpy function
    assert np.allclose(outs['list_entry'], [0, 1, 2, 0])
