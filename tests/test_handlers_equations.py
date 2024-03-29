# -*- coding: utf-8 -*-
# pylint: disable=E1101
"""
Tests for NRWAL equation handler objects
"""
import os
import numpy as np
import pytest

from NRWAL.handlers.equations import Equation
from NRWAL.handlers.groups import EquationGroup
from NRWAL.handlers.directories import EquationDirectory

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data/')
MODULE_DIR = os.path.dirname(TEST_DIR)
EQNS_DIR = os.path.join(MODULE_DIR, 'NRWAL/')

GOOD_DIR = os.path.join(TEST_DATA_DIR, 'test_eqns_dir/')

NP_EQNS = os.path.join(GOOD_DIR, 'numpy_eqns.yaml')

BAD_DIR = os.path.join(TEST_DATA_DIR, 'bad_eqn_dir/')
BAD_FILE_TYPE = os.path.join(BAD_DIR, 'bad_file_type.txt')
BAD_EQN = os.path.join(BAD_DIR, 'bad_list_eqn.yaml')


def test_print_eqn():
    """Test the pretty printing and variable name parsing of equation strs"""
    fp = os.path.join(GOOD_DIR, 'subdir/jacket.yaml')
    obj = EquationGroup(fp)

    eqn_name = 'outfitting_8MW'
    known_vars = ('depth', 'outfitting_cost')
    eqn = obj[eqn_name]
    assert len(eqn.variables) == len(known_vars)
    assert all(v in eqn.variables for v in known_vars)
    assert all(v in str(eqn) for v in known_vars)
    assert eqn_name in str(eqn)

    eqn_name = 'lattice'
    known_vars = ('turbine_capacity', 'depth', 'lattice_cost')
    eqn = obj[eqn_name]
    assert len(eqn.variables) == len(known_vars)
    assert all(v in eqn.variables for v in known_vars)
    assert all(v in str(eqn) for v in known_vars)
    assert eqn_name in str(eqn)

    eqn = obj['subgroup::eqn1']
    assert isinstance(eqn.variables, list)
    assert not eqn.variables
    assert str(eqn) == '100'

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
    kwargs = {k: 1 for k in eqn.variables}
    assert eqn.evaluate(**kwargs) == 55.2

    eqn = obj['lattice']
    kwargs = {k: 1 for k in eqn.variables}
    assert eqn.evaluate(**kwargs) == 41.07337083665887

    eqn = obj['lattice']
    kwargs = {k: np.ones((10, 10)) for k in eqn.variables}
    truth = 41.07337083665887 * np.ones((10, 10))
    assert np.allclose(eqn.evaluate(**kwargs), truth)

    with pytest.raises(RuntimeError):
        eqn.evaluate()


@pytest.mark.parametrize('operator', ('+', '-', '*', '**', '/'))
def test_eqn_math(operator):
    """Test the Equation object dunder math methods such as __add__ """
    obj = EquationDirectory(GOOD_DIR)
    eqn1 = obj['jacket::lattice']
    eqn2 = obj['jacket::transition_piece']

    if operator == '+':
        eqn3 = eqn1 + eqn2
        eqn4 = eqn1 + 3
    elif operator == '-':
        eqn3 = eqn1 - eqn2
        eqn4 = eqn1 - 3
    elif operator == '*':
        eqn3 = eqn1 * eqn2
        eqn4 = eqn1 * 3
    elif operator == '**':
        eqn3 = eqn1 ** eqn2
        eqn4 = eqn1 ** 3
    elif operator == '/':
        eqn3 = eqn1 / eqn2
        eqn4 = eqn1 / 3

    assert str(eqn1) in str(eqn3)
    assert str(eqn2) in str(eqn3)
    assert eqn1.full in eqn3.full
    assert eqn2.full in eqn3.full
    assert str(eqn1) in str(eqn4)
    assert eqn1.full in eqn4.full
    assert '{} 3'.format(operator) in eqn4.full

    args1 = {k: 2 for k in eqn1.variables}
    args2 = {k: 2 for k in eqn2.variables}
    args3 = {k: 2 for k in eqn3.variables}
    assert set(eqn1.variables + eqn2.variables) == set(eqn3.variables)
    assert eqn1.variables == eqn4.variables

    assert_eqn_eval_math(eqn1, eqn2, eqn3, eqn4, args1, args2, args3, operator)


def assert_eqn_eval_math(eqn1, eqn2, eqn3, eqn4, args1, args2, args3,
                         operator):
    """Run assert statements on Equation objects that have been combined using
    arithmetic operators"""
    if operator == '+':
        assert eqn1.eval(**args1) + eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) + 3 == eqn4.eval(**args1)
    elif operator == '-':
        assert eqn1.eval(**args1) - eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) - 3 == eqn4.eval(**args1)
    elif operator == '*':
        assert eqn1.eval(**args1) * eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) * 3 == eqn4.eval(**args1)
    elif operator == '**':
        assert eqn1.eval(**args1) ** eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) ** 3 == eqn4.eval(**args1)
    elif operator == '/':
        assert eqn1.eval(**args1) / eqn2.eval(**args2) == eqn3.eval(**args3)
        assert eqn1.eval(**args1) / 3 == eqn4.eval(**args1)


def test_numpy_eqns():
    """Test NRWAL equations with numpy operations"""
    obj = EquationGroup(NP_EQNS)

    eqn = obj['test_exp']
    assert len(eqn.variables) == 1
    assert eqn.variables[0] == 'inp'
    assert eqn.eval(inp=2) == np.exp(2)

    eqn = obj['test_max']
    assert len(eqn.variables) == 1
    assert eqn.variables[0] == 'inp'
    assert eqn.eval(inp=[3, 2, 4, 5, 0]) == 5

    eqn = obj['test_interp']
    x = [0.25, 0.5, 1]
    xp = [0, 2]
    fp = np.array([0, 2])
    truth = 2 + 10 * np.array([0.25, 0.5, 1])
    assert np.allclose(eqn.eval(x=x, xp=xp, fp=fp), truth)
    fp *= 2
    truth = 2 + 10 * 2 * np.array([0.25, 0.5, 1])
    assert np.allclose(eqn.eval(x=x, xp=xp, fp=fp), truth)


@pytest.mark.parametrize(
    'bad_fp', ('bad_self_ref_eqn.yaml', 'bad_deep_self_ref_eqn.yaml')
)
def test_self_referential_eq(bad_fp):
    """Test self-referential equations. """
    fp = os.path.join(BAD_DIR, bad_fp)
    with pytest.raises(ValueError) as excinfo:
        EquationGroup(fp)

    assert "Self-referencing is not allowed!" in str(excinfo.value)


def test_sci_not():
    """Test that numbers with scientific notation dont get parsed as variables
    """
    eqn = Equation('1e-4 + x-e*y*43.5E23/z-4.54e6')
    assert len(eqn.variables) == 4
    assert all(x in eqn.variables for x in ('x', 'e', 'y', 'z'))
