# -*- coding: utf-8 -*-
# pylint: disable=E1101
"""
Handler objects to interface with NRWAL equation library.
"""
import os
import numpy as np
import pytest

from NRWAL.handlers.equation_handlers import (Equation, EquationGroup,
                                              VariableGroup, EquationDirectory)

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


def test_print_eqn_dir():
    """Test the pretty printing of the EquationDirectory heirarchy"""
    obj = EquationDirectory(GOOD_DIR)
    assert len(str(obj).split('\n')) == 34


def test_print_eqn():
    """Test the pretty printing and variable name parsing of equation strs"""
    fp = os.path.join(GOOD_DIR, 'subdir/jacket.yaml')
    obj = EquationGroup(fp)

    eqn_name = 'outfitting_8MW'
    known_vars = ('depth', 'outfitting_cost')
    eqn = obj[eqn_name]
    assert len(eqn.vars) == len(known_vars)
    assert all([v in eqn.vars for v in known_vars])
    assert all([v in str(eqn) for v in known_vars])
    assert eqn_name in str(eqn)

    eqn_name = 'lattice'
    known_vars = ('turbine_capacity', 'depth', 'lattice_cost')
    eqn = obj[eqn_name]
    assert len(eqn.vars) == len(known_vars)
    assert all([v in eqn.vars for v in known_vars])
    assert all([v in str(eqn) for v in known_vars])
    assert eqn_name in str(eqn)

    eqn = obj['subgroup::eqn1']
    assert isinstance(eqn.vars, list)
    assert not eqn.vars
    assert str(eqn) == 'eqn1()'

    fp = os.path.join(GOOD_DIR, 'subdir/')
    obj = EquationDirectory(fp)
    eqn = obj['jacket::lattice']
    assert 'lattice_cost=100.0' in str(eqn)
    assert 'turbine_capacity, ' in str(eqn)
    assert 'depth, ' in str(eqn)


def test_eqn_eval():
    """Test some simple evaluations and kwargs passing"""

    fp = os.path.join(GOOD_DIR, 'subdir/jacket.yaml')
    obj = EquationGroup(fp)

    assert obj['subgroup::eqn1'].evaluate() == 100

    eqn = obj['outfitting_8MW']
    kwargs = {k: 1 for k in eqn.vars}
    assert eqn.evaluate(**kwargs) == 55.2

    eqn = obj['lattice']
    kwargs = {k: 1 for k in eqn.vars}
    assert eqn.evaluate(**kwargs) == 41.07337083665887

    eqn = obj['lattice']
    kwargs = {k: np.ones((10, 10)) for k in eqn.vars}
    truth = 41.07337083665887 * np.ones((10, 10))
    assert np.allclose(eqn.evaluate(**kwargs), truth)

    with pytest.raises(KeyError):
        eqn.evaluate()


def test_variable_setting():
    """Test the presence of a variables.yaml file in an EquationDirectory"""
    obj = EquationDirectory(GOOD_DIR)
    assert not obj.global_variables

    with pytest.raises(KeyError):
        obj['jacket::outfitting_8MW'].evaluate(depth=10)

    eqn = obj['subdir::jacket::outfitting_8MW']
    assert eqn.evaluate(depth=10) == 624.0
    assert eqn.evaluate(depth=10, outfitting_cost=20) == 1248.0
    assert eqn.evaluate(depth=10, outfitting_cost=10) == eqn.evaluate(depth=10)
    assert eqn.evaluate(depth=10, outfitting_cost=20) != eqn.evaluate(depth=10)

    with pytest.raises(KeyError):
        eqn.evaluate()

    assert obj['subdir'].global_variables['lattice_cost'] == 100
    sjacket = obj['subdir::jacket']
    assert sjacket.global_variables['lattice_cost'] == 100
    assert sjacket['outfitting_8MW'].global_variables['lattice_cost'] == 100
    assert sjacket['lattice'].global_variables['lattice_cost'] == 100
    subsub = obj['subdir::subsubdir']
    ssjacket = subsub['jacket']
    assert subsub.global_variables['lattice_cost'] == 50
    assert ssjacket.global_variables['lattice_cost'] == 50
    assert ssjacket['lattice'].global_variables['lattice_cost'] == 50
    assert ssjacket['subgroup3::eqn123'].global_variables['lattice_cost'] == 50

    eqn = obj['subdir::subsubdir::jacket::subgroup3::eqn123']
    assert eqn.global_variables['lattice_cost'] == 50
    assert eqn.global_variables['outfitting_cost'] == 10
    assert eqn.evaluate() == 95


@pytest.mark.parametrize('operator', ('+', '-', '*', '**', '/'))
def test_eqn_math(operator):
    """Test the Equation object dunder math methods such as __add__ """
    obj = EquationDirectory(GOOD_DIR)
    eqn1 = obj['jacket::lattice']
    eqn2 = obj['jacket::transition_piece']

    if operator == '+':
        eqn3 = eqn1 + eqn2
        eqn4 = eqn1 + 100
    elif operator == '-':
        eqn3 = eqn1 - eqn2
        eqn4 = eqn1 - 100
    elif operator == '*':
        eqn3 = eqn1 * eqn2
        eqn4 = eqn1 * 100
    elif operator == '**':
        eqn3 = eqn1 ** eqn2
        eqn4 = eqn1 ** 100
    elif operator == '/':
        eqn3 = eqn1 / eqn2
        eqn4 = eqn1 / 100

    assert str(eqn1) in str(eqn3)
    assert str(eqn2) in str(eqn3)
    assert eqn1.full in eqn3.full
    assert eqn2.full in eqn3.full
    assert str(eqn1) in str(eqn4)
    assert eqn1.full in eqn4.full
    assert '{} (100)'.format(operator) in eqn4.full

    args1 = {k: 10 for k in eqn1.vars}
    args2 = {k: 10 for k in eqn2.vars}
    args3 = {k: 10 for k in eqn3.vars}
    assert set(eqn1.vars + eqn2.vars) == set(eqn3.vars)
    assert eqn1.vars == eqn4.vars

    assert_eqn_eval_math(eqn1, eqn2, eqn3, eqn4, args1, args2, args3, operator)


def assert_eqn_eval_math(eqn1, eqn2, eqn3, eqn4, args1, args2, args3,
                         operator):
    """Run assert statements on Equation objects that have been combined using
    arithmetic operators"""
    if operator == '+':
        assert eqn1.eval(**args1) + eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) + 100 == eqn4.eval(**args1)
    elif operator == '-':
        assert eqn1.eval(**args1) - eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) - 100 == eqn4.eval(**args1)
    elif operator == '*':
        assert eqn1.eval(**args1) * eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) * 100 == eqn4.eval(**args1)
    elif operator == '**':
        assert eqn1.eval(**args1) ** eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) ** 100 == eqn4.eval(**args1)
    elif operator == '/':
        assert eqn1.eval(**args1) / eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) / 100 == eqn4.eval(**args1)


def test_eqn_group_add():
    """Test the addition / merging of two EquationGroup objects"""
    dir_obj = EquationDirectory(GOOD_DIR)
    group1 = dir_obj['jacket']
    group2 = dir_obj['subdir::jacket']
    group3 = group1 + group2
    assert set(list(group1.keys()) + list(group2.keys())) == set(group3.keys())
    assert 'lattice_cost=100' in str(group3['lattice'])
    assert 'lattice_cost=100' in str(group3['subgroup::subgroup2::eqn8'])


def test_eqn_dir_add():
    """Test the addition / merging of two EquationDirectory objects"""
    dir_obj = EquationDirectory(GOOD_DIR)
    dir1 = dir_obj['subdir']
    dir2 = dir_obj['subdir::subsubdir']
    dir3 = dir1 + dir2
    assert 'lattice_cost=50' in str(dir3['jacket::lattice'])
    assert 'outfitting_cost=10' in str(dir3['jacket::outfitting_8MW'])
