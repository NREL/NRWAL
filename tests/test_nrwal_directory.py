# -*- coding: utf-8 -*-
"""
Tests to validate all equations in the NRWAL directory can be
parsed and evaluated.
"""
import os
import pytest

from NRWAL.utilities.utilities import NRWAL_ANALYSIS_DIR
from NRWAL.handlers.equations import Equation
from NRWAL.handlers.directories import EquationDirectory

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, 'data/')
IGNORE_DIRS = ('handlers', )
EQN_DIR_NAMES = [dirname for dirname in os.listdir(NRWAL_ANALYSIS_DIR)
                 if os.path.isdir(os.path.join(NRWAL_ANALYSIS_DIR, dirname))
                 and not dirname.startswith(('__', '.'))
                 and dirname not in IGNORE_DIRS]


def get_equations(obj):
    """Recusively retrieve all Equation objects from an EquationGroup or
    EquationDirectory object

    Parameters
    ----------
    obj : EquationGroup | EquationDirectory
        Group or directory of equations to recusively search for base
        Equation objects.

    Returns
    -------
    eqns : list
        List of all Equation objects extracted from the input object.
    groups : list
        List of all groups corresonding to the eqns outputs.
    """

    eqns = []
    groups = []
    for v in obj.values():
        if isinstance(v, Equation):
            eqns.append(v)
            groups.append(obj)
        elif not isinstance(v, (int, float, str)):
            i_eqns, i_groups = get_equations(v)
            eqns += i_eqns
            groups += i_groups

    return eqns, groups


@pytest.mark.parametrize('dirname', EQN_DIR_NAMES)
def test_nrwal_directory(dirname):
    """Test that all equations in a NRWAL directory can be parsed and
    evaluated by the NRWAL handlers."""
    bad_eqn_i = []
    eqn_dir_path = os.path.join(NRWAL_ANALYSIS_DIR, dirname)
    dir_obj = EquationDirectory(eqn_dir_path)
    eqns, groups = get_equations(dir_obj)
    for i, eqn in enumerate(eqns):
        try:
            eqn.eval(**{k: 2 for k in eqn.variables})
        except Exception:
            bad_eqn_i.append(i)

    if any(bad_eqn_i):
        msg = ('These equations in "{}" could not be evaluated: '
               .format(dirname))
        for i in bad_eqn_i:
            msg += '\n\t - {} {}'.format(groups[i]._base_name, eqns[i])

        raise RuntimeError(msg)
