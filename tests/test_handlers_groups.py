# -*- coding: utf-8 -*-
# pylint: disable=E1101
"""
Tests for NRWAL equation group (file) handler objects
"""
import numpy as np
import os
import pytest

from NRWAL.handlers.equations import Equation
from NRWAL.handlers.groups import EquationGroup, VariableGroup
from NRWAL.handlers.directories import EquationDirectory

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data/')
MODULE_DIR = os.path.dirname(TEST_DIR)
EQNS_DIR = os.path.join(MODULE_DIR, 'NRWAL/')

GOOD_DIR = os.path.join(TEST_DATA_DIR, 'test_eqns_dir/')
FP_COST_REDUCTIONS = os.path.join(
    TEST_DATA_DIR, 'test_cost_reductions/cost_reductions.yaml')

BAD_DIR = os.path.join(TEST_DATA_DIR, 'bad_eqn_dir/')
BAD_FILE_TYPE = os.path.join(BAD_DIR, 'bad_file_type.txt')
BAD_EQN = os.path.join(BAD_DIR, 'bad_list_eqn.yaml')
BAD_KEYS = os.path.join(BAD_DIR, 'bad_cost_reductions.yaml')


def test_bad_file_type():
    """Test that EquationGroup raises a ValueError when passed a non
    yaml/json file."""
    with pytest.raises(ValueError):
        EquationGroup(BAD_FILE_TYPE)


def test_bad_eqn():
    """Test that EquationGroup raises a TypeError when passed an non-string
    non-numeric equation."""
    with pytest.raises(TypeError):
        EquationGroup(BAD_EQN)


def test_bad_keys():
    """Test that EquationGroup raises an error when passed numeric keys."""
    with pytest.raises(ValueError):
        EquationGroup(BAD_KEYS)


def test_eqn_group():
    """Test the equation group parsing"""
    fp = os.path.join(GOOD_DIR, 'export.yaml')
    obj = EquationGroup(fp)
    assert isinstance(obj, EquationGroup)
    assert 'fixed' in obj.keys()
    assert 'floating' in obj.keys()
    assert isinstance(obj['fixed'], Equation)
    with pytest.raises(KeyError):
        obj['bad']  # pylint: disable=W0104


def test_var_group():
    """Test variable group parsing"""
    fp = os.path.join(GOOD_DIR, 'subdir/variables.yaml')
    obj = VariableGroup(fp)
    assert isinstance(obj, VariableGroup)
    assert 'lattice_cost' in obj.keys()
    assert 'outfitting_cost' in obj.keys()
    assert isinstance(obj['lattice_cost'], float)
    assert isinstance(obj['outfitting_cost'], float)
    with pytest.raises(KeyError):
        obj['bad']  # pylint: disable=W0104


def test_print_eqn_group():
    """Test the pretty printing of the EquationGroup heirarchy"""
    fp = os.path.join(GOOD_DIR, 'subdir/jacket.yaml')
    obj = EquationGroup(fp)
    assert len(str(obj).split('\n')) == 11


def test_eqn_group_add():
    """Test the addition / merging of two EquationGroup objects"""
    dir_obj = EquationDirectory(GOOD_DIR)
    group1 = dir_obj['jacket']
    group2 = dir_obj['subdir::jacket']
    group3 = group1 + group2
    assert set(list(group1.keys()) + list(group2.keys())) == set(group3.keys())
    assert 'lattice_cost=100' in str(group3['lattice'])
    assert 'lattice_cost=100' in str(group3['subgroup::subgroup2::eqn8'])


def test_no_interp_extrap_nearest_power():
    """Negative test for power based equation without exact match and no
    interp/extrap/nearest"""
    dir_obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                                use_nearest_power=False)
    eqn_group = dir_obj['jacket']
    eqn = eqn_group['outfitting_8MW']  # pylint: disable=W0612
    with pytest.raises(KeyError):
        eqn = eqn_group['outfitting_9MW']


def test_nearest():
    """Test the lookup of power-based equations and the nearest-power
    calculation"""
    dir_obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                                use_nearest_power=True)
    eqn_group = dir_obj['jacket']
    eqns, powers = eqn_group.find_nearest_power_eqns('outfitting_9MW')
    assert powers[0] == 8.0
    assert powers[1] == 10.0
    assert 'outfitting_8MW' in str(eqns[0])
    assert 'outfitting_10MW' in str(eqns[1])
    eqn = eqn_group['outfitting_11MW']
    assert str(eqn) == 'outfitting_10MW(depth, outfitting_cost)'


def test_interp_extrap_power():
    """Test the interpolation and extrapolation of power-based equations."""
    dir_obj = EquationDirectory(GOOD_DIR, interp_extrap_power=True,
                                use_nearest_power=True)
    eqn_group = dir_obj['jacket']
    eqn = eqn_group['outfitting_11MW']
    truth = ('((((outfitting_8MW(depth, outfitting_cost) '
             '- outfitting_10MW(depth, outfitting_cost)) * 1.0) / -2.0) '
             '+ outfitting_10MW(depth, outfitting_cost))')
    assert str(eqn) == truth
    args = {'depth': 1, 'outfitting_cost': 1}
    y1 = eqn_group['outfitting_8MW'].eval(**args)
    y3 = eqn_group['outfitting_10MW'].eval(**args)
    x1, x2, x3 = 8, 11, 10
    out = (y3 - y1) * (x2 - x1) / (x3 - x1) + y1
    assert out == eqn.eval(**args)
    assert eqn.eval(**args) == 70.2

    eqn = eqn_group['outfitting_9MW']
    truth = ('((((outfitting_10MW(depth, outfitting_cost) '
             '- outfitting_8MW(depth, outfitting_cost)) * 1.0) / 2.0) '
             '+ outfitting_8MW(depth, outfitting_cost))')
    assert str(eqn) == truth
    args = {'depth': 1, 'outfitting_cost': 1}
    y1 = eqn_group['outfitting_8MW'].eval(**args)
    y3 = eqn_group['outfitting_10MW'].eval(**args)
    x1, x2, x3 = 8, 9, 10
    out = (y3 - y1) * (x2 - x1) / (x3 - x1) + y1
    assert out == eqn.eval(**args)
    assert eqn.eval(**args) == 60.2


def test_group_math_retrieval():
    """Test the group __getitem__ method with embedded math"""
    obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                            use_nearest_power=False)
    obj = obj['jacket']
    key1 = 'lattice'
    key2 = 'outfitting_8MW'
    key3 = 'transition_piece'
    key4 = '0.5'
    eqn1 = obj[key1]
    eqn2 = obj[key2]
    eqn3 = obj[key3]
    eqn4 = obj[key4]
    y1 = eqn1.eval(**{k: 2 for k in eqn1.variables})
    y2 = eqn2.eval(**{k: 2 for k in eqn2.variables})
    y3 = eqn3.eval(**{k: 2 for k in eqn3.variables})
    y4 = eqn4.eval()

    assert (y1 != 0) & (y1 != 1)
    assert (y2 != 0) & (y2 != 1)
    assert (y3 != 0) & (y3 != 1)

    key_math = ''.join([key1, ' + ', key2, '+', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 + y2 + y3 == y_math

    key_math = ''.join([key1, ' - ', key2, '+', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 - y2 + y3 == y_math

    key_math = ''.join([key1, ' + ', key2, ' * ', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 + y2 * y3 == y_math

    key_math = ''.join([key1, ' / ', key2, ' - ', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 / y2 - y3 == y_math

    key_math = ''.join([key1, ' - ', key2, ' / ', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 - y2 / y3 == y_math

    key_math = ''.join([key1, ' / ', key2, ' ** ', key4])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 / y2 ** y4 == y_math

    key_math = ''.join([key1, ' * ', key2, ' ** ', key4])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 * y2 ** y4 == y_math


def test_cost_reductions():
    """Test the extraction / parsing of cost reduction files which look a
    little different than normal files but should be handled similarly."""

    obj = EquationGroup(FP_COST_REDUCTIONS)
    assert isinstance(obj, EquationGroup)
    assert isinstance(obj['fixed'], EquationGroup)
    assert isinstance(obj['fixed::turbine_install_2015'], Equation)
    assert isinstance(obj['fixed::turbine_install_2020'], Equation)
    assert isinstance(obj['fixed::turbine_install_2025'], Equation)
    assert isinstance(obj['fixed::turbine_install_2015'].eval(), float)
    assert isinstance(obj['fixed::turbine_install_2020'].eval(), float)
    assert isinstance(obj['fixed::turbine_install_2025'].eval(), float)


def test_cost_reductions_interp():
    """Test interp/extrap/nearest on cost reduction year."""
    obj = EquationGroup(FP_COST_REDUCTIONS)
    with pytest.raises(KeyError):
        _ = obj['fixed::turbine_install::2030']
    with pytest.raises(KeyError):
        _ = obj['fixed::turbine_install_2030']

    obj = EquationGroup(FP_COST_REDUCTIONS, use_nearest_year=True)
    eqn1 = obj['fixed::turbine_install_2030']
    eqn2 = obj['fixed::turbine_install_2025']
    assert eqn1 == eqn2

    obj = EquationGroup(FP_COST_REDUCTIONS, interp_extrap_year=True,
                        use_nearest_year=True)
    eqn1 = obj['fixed::turbine_install_2023']
    eqn2 = obj['fixed::turbine_install_2020']
    eqn3 = obj['fixed::turbine_install_2025']
    assert (3 / 5) * (eqn3.eval() - eqn2.eval()) + eqn2.eval() == eqn1.eval()

    eqn4 = obj['fixed::turbine_install_2023 * 1000']
    assert 1000 * eqn1.eval() == eqn4.eval()


def test_group_parenthesis_retrieval():
    """Test parenthetical math expression retrieval from group object"""
    obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                            use_nearest_power=False)
    obj = obj['jacket']
    lattice = 'lattice'
    outfitting = 'outfitting_8MW'
    tpiece = 'transition_piece'

    lattice_val = obj[lattice]
    outfit_val = obj[outfitting]
    tpiece_val = obj[tpiece]
    lattice_val = lattice_val.eval(**{k: 2 for k in lattice_val.variables})
    outfit_val = outfit_val.eval(**{k: 2 for k in outfit_val.variables})
    tpiece_val = tpiece_val.eval(**{k: 2 for k in tpiece_val.variables})

    assert (lattice_val != 0) & (lattice_val != 1)
    assert (outfit_val != 0) & (outfit_val != 1)
    assert (tpiece_val != 0) & (tpiece_val != 1)

    key = '2 * ({} - {} + {})'.format(tpiece, lattice, outfitting)
    eqn = obj[key]
    out = eqn.eval(**{k: 2 for k in eqn.variables})
    assert np.allclose(out, 2 * (tpiece_val - lattice_val + outfit_val))

    key = '(2 * ({} / ({} + {})))'.format(tpiece, lattice, outfitting)
    eqn = obj[key]
    out = eqn.eval(**{k: 2 for k in eqn.variables})
    assert np.allclose(out, 2 * (tpiece_val / (lattice_val + outfit_val)))

    key = '(2 * ({} - ({} + {})))'.format(tpiece, lattice, outfitting)
    eqn = obj[key]
    out = eqn.eval(**{k: 2 for k in eqn.variables})
    assert np.allclose(out, 2 * (tpiece_val - (lattice_val + outfit_val)))

    key = '(2 * ({} - {}) * (4 + {}))'.format(tpiece, lattice, outfitting)
    eqn = obj[key]
    out = eqn.eval(**{k: 2 for k in eqn.variables})
    assert np.allclose(out, 2 * (tpiece_val - lattice_val) * (4 + outfit_val))

    key = '(2 * ((({} - {}) ** 2) + {}))'.format(tpiece, lattice, outfitting)
    eqn = obj[key]
    out = eqn.eval(**{k: 2 for k in eqn.variables})
    assert np.allclose(out, 2 * (((tpiece_val - lattice_val) ** 2)
                                 + outfit_val))


def test_group_bad_parenthesis_retrieval():
    """Test errors in parenthetical statements"""
    obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                            use_nearest_power=False)
    # pylint: disable=W0104
    with pytest.raises(ValueError):
        obj['2 * [lattice + transition_piece]']
    with pytest.raises(ValueError):
        obj['2 * {lattice + transition_piece}']
    with pytest.raises(AssertionError):
        obj['2 * (lattice + transition_piece']
