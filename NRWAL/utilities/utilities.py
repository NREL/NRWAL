# -*- coding: utf-8 -*-
"""
NRWAL utilities module.
"""


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
            indices.append([pstack.pop(), i])

    assert not bool(pstack)

    return indices
