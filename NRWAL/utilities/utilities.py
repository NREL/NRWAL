# -*- coding: utf-8 -*-
"""
NRWAL utilities module.
"""
import os
import numpy as np


NRWAL_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
NRWAL_DIR = os.path.join(NRWAL_DIR, 'NRWAL/')
NRWAL_ANALYSIS_DIR = os.path.join(NRWAL_DIR, 'analysis_library/')
NRWAL_CONFIG_DIR = os.path.join(NRWAL_DIR, 'default_configs/')


def find_parens(s):
    """Find matching parenthesis in a string

    https://stackoverflow.com/questions/29991917/
    indices-of-matching-parentheses-in-python

    Parameters
    ----------
    s : str
        String containing parentheses.

    Returns
    -------
    indices : list
        List of matching parentheses indices
        e.g. [[i_start1, i_end1], [i_start2, i_end2]]
    """
    indices = []
    pstack = []

    msg = 'Unbalanced parenthesis in: {}'.format(s)
    assert s.count('(') == s.count(')'), msg

    for i, c in enumerate(s):
        if c == '(':
            pstack.append(i)
        elif c == ')':
            indices.append([pstack.pop(), i + 1])

    assert not bool(pstack)

    return indices


def find_np_pd_methods(s):
    """Find the start and end index of the first np. or pd. function in the
    input string

    Parameters
    ----------
    s : str
        String possibly containing numpy functions like "10 + np.exp(input)"

    Returns
    -------
    start / end : int
        Starting and ending indices of the first np. or pd. method. So if
        s="10 + np.exp(input)" then s[start:end]="np.exp(input)"
    """
    start = 0
    if 'np.' not in s and 'pd.' not in s:
        return None, None
    elif 'np.' in s:
        start = s.index('np.')
    elif 'pd.' in s:
        start = s.index('pd.')

    paren_ind = find_parens(s)
    np_paren = np.argmin([x[0] for x in paren_ind])
    end = paren_ind[np_paren][1]

    return start, end
