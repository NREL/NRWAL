# -*- coding: utf-8 -*-
# pylint: disable=E1101
"""
Handler objects to interface with NRWAL equation library.
"""
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
    obj = EquationDirectory(GOOD_DIR, interp_extrap=False, use_nearest=False)
    key1 = 'jacket::lattice'
    key2 = 'jacket::outfitting_8MW'
    key3 = 'jacket::transition_piece'
    key4 = '0.6'
    eqn1 = obj[key1]
    eqn2 = obj[key2]
    eqn3 = obj[key3]
    eqn4 = obj[key4]
    y1 = eqn1.eval(**{k: 2 for k in eqn1.vars})
    y2 = eqn2.eval(**{k: 2 for k in eqn2.vars})
    y3 = eqn3.eval(**{k: 2 for k in eqn3.vars})
    y4 = eqn4.eval()

    key_math = ''.join([key1, ' - ', key2, '+', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.vars})
    assert y1 - y2 + y3 == y_math

    key_math = ''.join([key1, ' - ', key2, ' * ', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.vars})
    assert y1 - y2 * y3 == y_math

    key_math = ''.join([key1, ' / ', key2, ' +', key3])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.vars})
    assert y1 / y2 + y3 == y_math

    key_math = ''.join([key1, ' / ', key2, ' ** ', key4])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.vars})
    assert y1 / y2 ** y4 == y_math

    key_math = ''.join([key1, ' * ', key2, ' ** ', key4])
    eqn_math = obj[key_math]
    y_math = eqn_math.eval(**{k: 2 for k in eqn_math.vars})
    assert y1 * y2 ** y4 == y_math
