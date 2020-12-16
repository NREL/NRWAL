# -*- coding: utf-8 -*-
# pylint: disable=E1101
"""
Handler objects to interface with NRWAL equation library.
"""
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

BAD_DIR = os.path.join(TEST_DATA_DIR, 'bad_eqn_dir/')
BAD_FILE_TYPE = os.path.join(BAD_DIR, 'bad_file_type.txt')
BAD_EQN = os.path.join(BAD_DIR, 'bad_list_eqn.yaml')


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


def test_no_interp_extrap_nearest():
    """Negative test for power based equation without exact match and no
    interp/extrap/nearest"""
    dir_obj = EquationDirectory(GOOD_DIR, interp_extrap=False,
                                use_nearest=False)
    eqn_group = dir_obj['jacket']
    eqn = eqn_group['outfitting_8MW']  # pylint: disable=W0612
    with pytest.raises(KeyError):
        eqn = eqn_group['outfitting_9MW']


def test_nearest():
    """Test the lookup of power-based equations and the nearest-power
    calculation"""
    dir_obj = EquationDirectory(GOOD_DIR, interp_extrap=False,
                                use_nearest=True)
    eqn_group = dir_obj['jacket']
    eqns, powers = eqn_group.find_nearest_eqns('outfitting_9MW')
    assert powers[0] == 8.0
    assert powers[1] == 10.0
    assert 'outfitting_8MW' in str(eqns[0])
    assert 'outfitting_10MW' in str(eqns[1])
    eqn = eqn_group['outfitting_11MW']
    assert str(eqn) == 'outfitting_10MW(depth, outfitting_cost)'


def test_interp_extrap():
    """Test the interpolation and extrapolation of power-based equations."""
    dir_obj = EquationDirectory(GOOD_DIR, interp_extrap=True, use_nearest=True)
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
