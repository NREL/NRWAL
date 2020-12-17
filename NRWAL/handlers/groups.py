# -*- coding: utf-8 -*-
"""
Handler objects to interface with NRWAL equation groups (files).
"""
from abc import ABC
import copy
import re
import os
import json
import yaml
import numpy as np
import logging

from NRWAL.handlers.equations import Equation

logger = logging.getLogger(__name__)


class AbstractGroup(ABC):
    """Abstract class for groupings of equations or variables in a single
    yaml or json file.
    """

    def __init__(self, group, interp_extrap=False, use_nearest=False):
        """
        Parameters
        ----------
        group : str | dict
            String filepath to a yaml or json file containing one or more
            equation strings OR a pre-extracted dictionary from a yaml or
            json file with equation strings as values.
        interp_extrap : bool
            Flag to interpolate and extrapolate power (MW) dependent equations
            based on the case-insensitive regex pattern: "_[0-9]*MW$"
            This takes preference over the use_nearest flag.
            If both interp_extrap & use_nearest are False, a KeyError will
            be raised if the exact equation name request is not found.
        use_nearest : bool
            Flag to use the nearest valid power (MW) dependent equation
            based on the case-insensitive regex pattern: "_[0-9]*MW$"
            This is second priority to the interp_extrap flag.
            If both interp_extrap & use_nearest are False, a KeyError will
            be raised if the exact equation name request is not found.
        """

        self._base_name = None
        self._dir_name = None
        if isinstance(group, str):
            self._base_name = os.path.basename(group)
            self._dir_name = os.path.dirname(group)

        self._global_variables = {}
        self._interp_extrap = interp_extrap
        self._use_nearest = use_nearest
        self._group = self._parse_group(group)

    def __add__(self, other):
        """Add another equation group to this instance of EquationGroup (self)
        and return a new EquationGroup object that updates this instance with
        the new input. Note that overlapping sub EquationGroups in the original
        EquationGroup may be overwritten by the new input if a duplicate key
        exists.

        Parameters
        ----------
        other : EquationGroup | str | dict
            Another EquationGroup object or filepath to an EquationGroup
            to add to this instance of EquationGroup (self).

        Returns
        -------
        out : EquationGroup
            A new EquationGroup instance with this instance of EquationGroup
            (self) updated with the input EquationGroup.
            Note that overlapping sub EquationGroups in the original
            EquationGroup may be overwritten by the new input if a duplicate
            key exists.
        """
        cls = self.__class__
        if isinstance(other, (str, dict)):
            other = cls(other, interp_extrap=self._interp_extrap,
                        use_nearest=self._use_nearest)

        out = copy.deepcopy(self)
        out._group.update(other._group)
        out._set_variables(other._global_variables)

        return out

    def __repr__(self):
        return str(self)

    @staticmethod
    def _getitem_math(obj, key):
        """Helper function to recusively perform math for __getitem__ method

        Parameters
        ----------
        obj : EquationGroup | EquationDirectory
            Instance of EquationGroup or EquationDirectory. This is input
            explicitly in a staticmethod instead of an instance method so that
            EquationDirectory can share the method.
        key : str
            A key or set of keys (delimited by "::") to retrieve from this
            EquationGroup instance. For example, if this EquationGroup
            has an equation 'eqn1': 'm*x + b', the the input key could be:
            'eqn1' to retrieve the Equation object that holds 'm*x + b'.
            The input argument key can also be delimited like 'set_1::eqn1'
            to retrieve eqn1 nested in a sub EquationGroup object "set_1".
            The input argument can also have embedded math like
            'set_1::eqn1 + set_2::eqn2 ** 2'.

        Returns
        -------
        out : Equation | EquationGroup
            An object in this instance of EquationGroup keyed by the
            input argument key.
        """
        key = key.replace('**', '^')
        if '+' in key:
            split_keys = key.partition('+')
            return obj[split_keys[0].strip()] + obj[split_keys[2].strip()]
        elif '-' in key:
            split_keys = key.partition('-')
            return obj[split_keys[0].strip()] - obj[split_keys[2].strip()]
        elif '*' in key:
            split_keys = key.partition('*')
            return obj[split_keys[0].strip()] * obj[split_keys[2].strip()]
        elif '/' in key:
            split_keys = key.partition('/')
            return obj[split_keys[0].strip()] / obj[split_keys[2].strip()]
        elif '^' in key:
            split_keys = key.partition('^')
            return obj[split_keys[0].strip()] ** obj[split_keys[2].strip()]

    def __getitem__(self, key):
        """Retrieve a nested Equation or EquationGroup object from this
        instance of an EquationGroup.

        Parameters
        ----------
        key : str
            A key or set of keys (delimited by "::") to retrieve from this
            EquationGroup instance. For example, if this EquationGroup
            has an equation 'eqn1': 'm*x + b', the the input key could be:
            'eqn1' to retrieve the Equation object that holds 'm*x + b'.
            The input argument key can also be delimited like 'set_1::eqn1'
            to retrieve eqn1 nested in a sub EquationGroup object "set_1".
            The input argument can also have embedded math like
            'set_1::eqn1 + set_2::eqn2 ** 2'.

        Returns
        -------
        out : Equation | EquationGroup
            An object in this instance of EquationGroup keyed by the
            input argument key.
        """

        operators = ('+', '-', '*', '/', '^')
        if any([op in key for op in operators]):
            return self._getitem_math(self, key)

        if Equation.is_num(key) and key not in self:
            return Equation(key)

        if '::' in str(key):
            keys = key.split('::')
        else:
            keys = [key]

        nearest_eqns = []
        nearest_powers = []
        keys = [str(k) for k in keys]

        out = self._group
        for i, ikey in enumerate(keys):

            if self._interp_extrap or self._use_nearest and i == len(keys) - 1:
                nearest_eqns, nearest_powers = self.find_nearest_eqns(ikey)

            if ikey in out:
                out = out[ikey]
            elif len(nearest_eqns) > 1 and self._interp_extrap:
                x2 = self._parse_power(ikey)[0]
                x1, x3 = nearest_powers[0:2]
                y1, y3 = nearest_eqns[0:2]
                out = (y3 - y1) * (x2 - x1) / (x3 - x1) + y1
            elif any(nearest_eqns) and self._use_nearest:
                out = nearest_eqns[0]
            else:
                msg = ('Could not retrieve equation key "{}", '
                       'could not find "{}" in last available keys: {}'
                       .format(key, ikey, list(out.keys())))
                logger.error(msg)
                raise KeyError(msg)

        return out

    def __contains__(self, arg):
        return arg in self.keys()

    @staticmethod
    def _parse_power(key):
        """Parse the integer power from an equation key

        Parameters
        ----------
        key : str
            A key to retrieve an equation from this EquationGroup. Should
            contain the case-insensitive regex pattern "_[0-9]*MW$". Otherwise,
            None will be returned.

        Returns
        -------
        power : float | None
            The numeric power value in key in the regex pattern "_[0-9]*MW$".
            If the pattern is not found, None is returned
        base_str : str
            Key with the regex pattern stripped out.
        """

        base_str = key
        power = re.search('_[0-9]*MW$', key, flags=re.IGNORECASE)
        if power is not None:
            base_str = key.replace(power.group(0), '')
            power = float(power.group(0).upper().replace('MW', '').lstrip('_'))

        return power, base_str

    def find_nearest_eqns(self, request):
        """Find power-based (MW) equations in this EquationGroup that match
        the request (by regex pattern "_[0-9]*MW$") and sort them by
        difference in equation power.

        For example, if the request is "eqn_a_7MW" and there are "eqn_a_4MW",
        "eqn_a_6MW", and "eqn_a_10MW" in this group, this method will return
        [eqn_a_6MW, eqn_a_10MW, eqn_a_4MW], [6, 10, 4]

        Parameters
        ----------
        request : str
            A key to retrieve an equation from this EquationGroup. Should
            contain the case-insensitive regex pattern "_[0-9]*MW$". Otherwise,
            empty lists will be returned.

        Returns
        -------
        eqns : list
            List of Equation objects that match the request key and are sorted
            by difference in the _*MW specification to the input request key.
            If the request key does not have the _*MW specification or if no
            other keys in this EquationGroup match the request then this will
            return an empty list.
        eqn_powers : list
            List of float power MW values corresponding to eqns and sorted
            by difference in the _*MW specification to the input request key.
            If the request key does not have the _*MW specification or if no
            other keys in this EquationGroup match the request then this will
            return an empty list.
        """

        eqn_keys = []
        eqn_powers = []
        req_mw, base_str = self._parse_power(request)
        if req_mw:
            for key in self.keys():
                match_mw, match_base = self._parse_power(key)
                if match_mw and base_str == match_base:
                    eqn_keys.append(key)
                    eqn_powers.append(match_mw)

            if any(eqn_keys):
                eqn_pow_diffs = np.abs(req_mw - np.array(eqn_powers))
                indices = np.argsort(eqn_pow_diffs)
                eqn_keys = list(np.array(eqn_keys)[indices])
                eqn_powers = list(np.array(eqn_powers)[indices])

        eqns = [self._group[k] for k in eqn_keys]

        return eqns, eqn_powers

    @classmethod
    def _parse_group(cls, group):
        """
        Parameters
        ----------
        group : str | dict
            String filepath to a yaml or json file containing one or more
            equation strings OR a pre-extracted dictionary from a yaml or
            json file with equation strings as values.

        Returns
        -------
        group : dict
            Loaded dictionary from a yaml or json file with equation strings
            or nested equation group dictionaries as values.
        """

        if isinstance(group, str):
            if not os.path.exists(group):
                msg = 'Cannot find equation file path: {}'.format(group)
                logger.error(msg)
                raise FileNotFoundError(msg)

            if group.endswith('.json'):
                with open(group, 'r') as f:
                    group = json.load(f)

            elif group.endswith(('.yml', '.yaml')):
                with open(group, 'r') as f:
                    group = yaml.safe_load(f)

            else:
                msg = ('Cannot load file path, must be json or yaml: {}'
                       .format(group))
                logger.error(msg)
                raise ValueError(msg)

        if not isinstance(group, dict):
            msg = 'Cannot use group of type: {}'.format(type(group))
            logger.error(msg)
            raise TypeError(msg)

        return group

    def _set_variables(self, var_dict):
        """Pass VariableGroup variable dictionaries defined within equation
        directories to adjacent and sub-level EquationGroup and Equation
        objects.

        Parameters
        ----------
        var_dict : dict | None
            Variables group dictionary from a higher level than or adjacent to
            this instance of EquationGroup. Variables from this input will be
            passed to all Equation objects in this EquationGroup. These
            variables can always be overwritten when Equation.evaluate()
            is called.
        """

        if var_dict is not None:
            self._global_variables.update(copy.deepcopy(var_dict))
            for v in self.values():
                v._set_variables(var_dict)

    @classmethod
    def _r_all_equations(cls, obj):
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
        """

        eqns = []
        for v in obj.values():
            if isinstance(v, Equation):
                eqns.append(v)
            elif not isinstance(v, (int, float, str)):
                eqns += cls._r_all_equations(v)

        return eqns

    @property
    def all_equations(self):
        """List of all Equation objects from this object."""
        return self._r_all_equations(self)

    def keys(self):
        """Get the 1st level of equation group keys, same as dict.keys()"""
        return self._group.keys()

    def items(self):
        """Get the 1st level of equation (keys, values), same as dict.items().
        """
        return self._group.items()

    def values(self):
        """Get the 1st level of equation values, same as dict.values()"""
        return self._group.values()


class EquationGroup(AbstractGroup):
    """Class to handle a single json or yaml file with multiple wind cost
    equations.
    """

    def __str__(self):
        s = ['EquationGroup object with heirarchy:']
        if self._base_name is not None:
            s = ['EquationGroup object from file "{}" with heirarchy:'
                 .format(self._base_name)]

        for k, v in self.items():
            if isinstance(v, Equation):
                s.append(str(v))
            else:
                s.append(str(k))
                s += ['\t' + x for x in str(v).split('\n')[1:]]

        return '\n'.join(s)

    @classmethod
    def _parse_group(cls, eqn_group):
        """Parse a group of equation strings defined in a yaml or json file

        Parameters
        ----------
        eqn_group : str | dict
            String filepath to a yaml or json file containing one or more
            equation strings OR a pre-extracted dictionary from a yaml or
            json file with equation strings as values.

        Returns
        -------
        eqn_group : dict
            Loaded dictionary from a yaml or json file with equation strings
            or nested equation group dictionaries as values.
        """

        eqn_group = super()._parse_group(eqn_group)

        for k, v in sorted(eqn_group.items()):
            if isinstance(v, (str, int, float)):
                eqn_group[k] = Equation(v, name=k)

            elif isinstance(v, dict):
                eqn_group[k] = cls(v)

            else:
                msg = ('Cannot use equation group value that is not a '
                       'string, float, int, or dictionary: {} ({})'
                       .format(v, type(v)))
                logger.error(msg)
                raise TypeError(msg)

        return eqn_group

    @property
    def global_variables(self):
        """Get a dictionary of global variables from a variables.yaml file
        accessible to this object

        Returns
        -------
        global_variables : dict
            Dictionary of variables accessible to all Equation, EquationGroup,
            and EquationDirectory objects within the heirarchy of this object.
        """
        return self._global_variables


class VariableGroup(AbstractGroup):
    """Class to handle a single json or yaml file with multiple numerical
    variable definitions.
    """

    def __str__(self):
        s = ['VariableGroup object with variable definitions:']
        for k, v in self.items():
            s.append('{}: {}'.format(k, v))

        return '\n'.join(s)

    @property
    def var_dict(self):
        """Get a dictionary of the variable namespace where keys are variable
        names and values are single numeric variable values.
        """
        return self._group

    def _parse_group(self, var_group):
        """Parse a group of numerical variables defined in a yaml or json file

        Parameters
        ----------
        var_group : str | dict
            String filepath to a yaml or json file containing one or more
            numerical variable definitions OR a pre-extracted dictionary
            from a yaml or json file with variable definitions.

        Returns
        -------
        var_group : dict
            Loaded dictionary from a yaml or json file with numerical
            variable definitions
        """

        var_group = super()._parse_group(var_group)

        for v in var_group.values():
            if not isinstance(v, (int, float)):
                msg = ('Cannot use variable group value that is not a '
                       'float or int: {} ({})'.format(v, type(v)))
                logger.error(msg)
                raise TypeError(msg)

        return var_group
