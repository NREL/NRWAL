# -*- coding: utf-8 -*-
"""
Handler objects to interface with NRWAL equation library.
"""
import os
import pytest

from NRWAL.handlers.equation_handlers import (Equation, EquationGroup,
                                              EquationDirectory)

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


def test_print_eqn_group():
    """Test the pretty printing of the EquationGroup heirarchy"""
    fp = os.path.join(GOOD_DIR, 'subdir/jacket.yaml')
    obj = EquationGroup(fp)
    assert len(str(obj).split('\n')) == 19


def test_print_eqn_dir():
    """Test the pretty printing of the EquationDirectory heirarchy"""
    obj = EquationDirectory(GOOD_DIR)
    assert len(str(obj).split('\n')) == 37


if __name__ == '__main__':
    fp = os.path.join(GOOD_DIR, 'subdir/jacket.yaml')
    obj = EquationGroup(fp)
    print(obj)
