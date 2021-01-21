# -*- coding: utf-8 -*-
# pylint: disable=E1101,W0104
"""
Tests for NRWAL equation directory handler objects
"""
import numpy as np
import os
import pytest

from NRWAL.handlers.equations import Equation
from NRWAL.handlers.groups import EquationGroup
from NRWAL.handlers.directories import EquationDirectory

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data/')
MODULE_DIR = os.path.dirname(TEST_DIR)
EQNS_DIR = os.path.join(MODULE_DIR, 'NRWAL/')

GOOD_DIR = os.path.join(TEST_DATA_DIR, 'test_eqns_dir/')

BAD_DIR = os.path.join(TEST_DATA_DIR, 'bad_eqn_dir/')
BAD_FILE_TYPE = os.path.join(BAD_DIR, 'bad_file_type.txt')
BAD_EQN = os.path.join(BAD_DIR, 'bad_list_eqn.yaml')

COST_REDUCTIONS_DIR = os.path.join(TEST_DATA_DIR, 'test_cost_reductions/')


def test_bad_eqn_dir():
    """Test that EquationDirectory raises a RuntimeError when passed a
    directory with bad equation files."""
    with pytest.raises(RuntimeError):
        EquationDirectory(BAD_DIR)


def test_eqn_dir_parsing():
    """Test the equation directory parsing logic and recursion"""
    obj = EquationDirectory(GOOD_DIR)
    assert isinstance(obj, EquationDirectory)
    assert isinstance(obj['jacket'], EquationGroup)
    assert isinstance(obj['jacket.yaml'], EquationGroup)

    assert isinstance(obj['subdir'], EquationDirectory)
    assert isinstance(obj['subdir::jacket'], EquationGroup)
    assert isinstance(obj['subdir::jacket::lattice'], Equation)

    assert '.ignore' not in obj.keys()
    assert '__ignore' not in obj.keys()
    assert '.ignore' not in obj['subdir'].keys()
    assert '__ignore' not in obj['subdir'].keys()
    assert 'ignore' not in str(EquationDirectory)
    assert 'empty' not in obj.keys()

    with pytest.raises(KeyError):
        obj['bad']  # pylint: disable=W0104

    with pytest.raises(KeyError):
        obj['jacket::bad']  # pylint: disable=W0104


def test_print_eqn_dir():
    """Test the pretty printing of the EquationDirectory heirarchy"""
    obj = EquationDirectory(GOOD_DIR)
    assert len(str(obj).split('\n')) == 34


def test_variable_setting():
    """Test the presence of a variables.yaml file in an EquationDirectory"""
    obj = EquationDirectory(GOOD_DIR)
    assert not obj.default_variables

    with pytest.raises(RuntimeError):
        obj['jacket::outfitting_8MW'].evaluate(depth=10)

    eqn = obj['subdir::jacket::outfitting_8MW']
    assert eqn.evaluate(depth=10) == 624.0
    assert eqn.evaluate(depth=10, outfitting_cost=20) == 1248.0
    assert eqn.evaluate(depth=10, outfitting_cost=10) == eqn.evaluate(depth=10)
    assert eqn.evaluate(depth=10, outfitting_cost=20) != eqn.evaluate(depth=10)

    with pytest.raises(RuntimeError):
        eqn.evaluate()

    assert obj['subdir'].default_variables['lattice_cost'] == 100
    sjacket = obj['subdir::jacket']
    assert sjacket.default_variables['lattice_cost'] == 100
    assert sjacket['outfitting_8MW'].default_variables['lattice_cost'] == 100
    assert sjacket['lattice'].default_variables['lattice_cost'] == 100
    subsub = obj['subdir::subsubdir']
    ssjacket = subsub['jacket']
    assert subsub.default_variables['lattice_cost'] == 50
    assert ssjacket.default_variables['lattice_cost'] == 50
    assert ssjacket['lattice'].default_variables['lattice_cost'] == 50
    x = ssjacket['subgroup3::eqn123'].default_variables['lattice_cost']
    assert x == 50

    eqn = obj['subdir::subsubdir::jacket::subgroup3::eqn123']
    assert eqn.default_variables['lattice_cost'] == 50
    assert eqn.default_variables['outfitting_cost'] == 10
    assert eqn.evaluate() == 95


def test_nearest():
    """Test the lookup of power-based equations and the nearest-power
    calculation from a dir object"""
    dir_obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                                use_nearest_power=True)
    eqn = dir_obj['jacket::outfitting_11MW']
    truth = dir_obj['jacket::outfitting_10MW']
    assert eqn == truth


def test_interp_extrap_power():
    """Test interp and extrap functionality of power-based equations
    from __getitem__ on a dir object"""
    dir_obj = EquationDirectory(GOOD_DIR, interp_extrap_power=True,
                                use_nearest_power=True)
    eqn = dir_obj['jacket::outfitting_11MW']
    truth = ('((((outfitting_8MW(depth, outfitting_cost) '
             '- outfitting_10MW(depth, outfitting_cost)) * 1.0) / -2.0) '
             '+ outfitting_10MW(depth, outfitting_cost))')
    assert str(eqn) == truth


def test_eqn_dir_add():
    """Test the addition / merging of two EquationDirectory objects"""
    dir_obj = EquationDirectory(GOOD_DIR)
    dir1 = dir_obj['subdir']
    dir2 = dir_obj['subdir::subsubdir']
    dir3 = dir1 + dir2
    assert 'lattice_cost=50' in str(dir3['jacket::lattice'])
    assert 'outfitting_cost=10' in str(dir3['jacket::outfitting_8MW'])


def test_dir_math_retrieval():
    """Test the group and directory __getitem__ method with embedded math"""
    obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                            use_nearest_power=False)
    key1 = 'jacket::lattice'
    key2 = 'jacket::outfitting_8MW'
    key3 = 'jacket::transition_piece'
    key4 = '0.6'
    eqn1 = obj[key1]
    eqn2 = obj[key2]
    eqn3 = obj[key3]
    eqn4 = obj[key4]
    y1 = eqn1.eval(**{k: 2 for k in eqn1.variables})
    y2 = eqn2.eval(**{k: 2 for k in eqn2.variables})
    y3 = eqn3.eval(**{k: 2 for k in eqn3.variables})
    y4 = eqn4.eval()

    key_math = ''.join([key1, ' - ', key2, '+', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 - y2 + y3 == y_math

    key_math = ''.join([key1, ' - ', key2, ' * ', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 - y2 * y3 == y_math

    key_math = ''.join([key1, ' / ', key2, ' +', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 / y2 + y3 == y_math

    key_math = ''.join([key1, ' / ', key2, ' ** ', key4])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 / y2 ** y4 == y_math

    key_math = ''.join([key1, ' * ', key2, ' ** ', key4])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.variables})
    assert y1 * y2 ** y4 == y_math


def test_bad_math_retrieval():
    """Test that attempting math in __getitem__ between an EquationGroup and
    an Equation raises a TypeError"""
    obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                            use_nearest_power=False)
    key1 = 'jacket'
    key2 = 'jacket::outfitting_8MW'

    key_math = ''.join([key1, ' - ', key2])
    with pytest.raises(TypeError):
        obj[key_math]


def test_dir_parenthesis_retrieval():
    """Test parenthetical math expression retrieval from directory object"""
    obj = EquationDirectory(GOOD_DIR, interp_extrap_power=False,
                            use_nearest_power=False)
    key1 = 'jacket::lattice'
    key2 = 'jacket::outfitting_8MW'
    key = '2 * ({} + {})'.format(key1, key2)
    eqn = obj[key]
    truth = ('(2 * (lattice(depth, lattice_cost, turbine_capacity) '
             '+ outfitting_8MW(depth, outfitting_cost)))')
    assert str(eqn) == truth
    truth = ('(2) * (((np.exp(3.7136 + 0.00176 * turbine_capacity '
             '** 2.5 + 0.645 * np.log(depth))) * lattice_cost) '
             '+ ((40 + (0.8 * (18 + depth))) * outfitting_cost))')
    assert eqn.full == truth
    inputs = {k: np.ones(3) for k in eqn.variables}
    out = eqn.eval(**inputs)
    assert isinstance(out, np.ndarray)
    assert np.allclose(out, 192.54674167 * np.ones(3))
    eqn1 = obj[key1]
    eqn2 = obj[key2]
    out1 = eqn1.evaluate(**inputs)
    out2 = eqn2.evaluate(**inputs)
    assert np.allclose(out, 2 * (out1 + out2))
    assert ~np.allclose(out, 2 * out1 + out2)


def test_cost_reductions_directory():
    """Test interp/extrap/nearest on cost reduction year from the
    directory object."""

    obj = EquationDirectory(COST_REDUCTIONS_DIR, use_nearest_year=True)
    eqn1 = obj['cost_reductions::fixed::turbine_install_2030']
    eqn2 = obj['cost_reductions::fixed::turbine_install_2025']
    assert eqn1 == eqn2

    obj = EquationDirectory(COST_REDUCTIONS_DIR, interp_extrap_year=True,
                            use_nearest_year=True)
    eqn1 = obj['cost_reductions::fixed::turbine_install_2030']
    eqn2 = obj['cost_reductions::fixed::turbine_install_2020']
    eqn3 = obj['cost_reductions::fixed::turbine_install_2025']
    assert (eqn3.eval() - eqn2.eval()) + eqn3.eval() == eqn1.eval()

    eqn1 = obj['cost_reductions::fixed::turbine_install_2023']
    eqn2 = obj['cost_reductions::fixed::turbine_install_2020']
    eqn3 = obj['cost_reductions::fixed::turbine_install_2025']
    assert (3 / 5) * (eqn3.eval() - eqn2.eval()) + eqn2.eval() == eqn1.eval()
