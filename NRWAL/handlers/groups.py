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
import operator
from collections import OrderedDict

from NRWAL.handlers.equations import Equation
from NRWAL.utilities.utilities import find_parens

logger = logging.getLogger(__name__)


class AbstractGroup(ABC):
    """Abstract class for groupings of equations or variables in a single
    yaml or json file.
    """

    def __init__(self, group, name=None, interp_extrap_power=False,
                 use_nearest_power=False, interp_extrap_year=False,
                 use_nearest_year=False):
        """
        Parameters
        ----------
        group : str | dict
            String filepath to a yaml or json file containing one or more
            equation strings OR a pre-extracted dictionary from a yaml or
            json file with equation strings as values.
        name : str | None
            Optional name for identification and debugging if this
            AbstractGroup is being initialized with the "group" input argument
            as a pre-extracted dictionary.
        interp_extrap_power : bool
            Flag to interpolate and extrapolate power (MW) dependent equations
            based on the case-insensitive regex pattern: "_[0-9]*MW$"
            This takes preference over the use_nearest_power flag.
            If both interp_extrap_power & use_nearest_power are False, a
            KeyError will be raised if the exact equation name request is not
            found.
        use_nearest_power : bool
            Flag to use the nearest valid power (MW) dependent equation
            based on the case-insensitive regex pattern: "_[0-9]*MW$"
            This is second priority to the interp_extrap_power flag.
            If both interp_extrap_power & use_nearest_power are False, a
            KeyError will be raised if the exact equation name request is not
            found.
        interp_extrap_year : bool
            Flag to interpolate and extrapolate equations keyed by year.
            This takes preference over the use_nearest_year flag.
            If both interp_extrap_year & use_nearest_year are False, a
            KeyError will be raised if the exact equation name request is not
            found.
        use_nearest_year : bool
            Flag to use the nearest valid equation keyed by year.
            This is second priority to the interp_extrap_year flag.
            If both interp_extrap_year & use_nearest_year are False, a
            KeyError will be raised if the exact equation name request is not
            found.
        """

        self._base_name = name
        self._dir_name = None
        if isinstance(group, str):
            self._base_name = os.path.basename(group)
            self._dir_name = os.path.dirname(group)

        self._default_variables = {}
        self._interp_extrap_power = interp_extrap_power
        self._use_nearest_power = use_nearest_power
        self._interp_extrap_year = interp_extrap_year
        self._use_nearest_year = use_nearest_year
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
            other = cls(other, interp_extrap_power=self._interp_extrap_power,
                        use_nearest_power=self._use_nearest_power,
                        interp_extrap_year=self._interp_extrap_year,
                        use_nearest_year=self._use_nearest_year)

        out = copy.deepcopy(self)
        out._group.update(other._group)
        out.set_default_variables(other._default_variables)

        return out

    def __repr__(self):
        return str(self)

    @staticmethod
    def _getitem_math(obj, key, workspace):
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
        workspace : None | dict
            Temporary workspace to hold parts of math expressions. Useful
            for extracting and caching parenthetical statements.

        Returns
        -------
        out : Equation | EquationGroup
            An object in this instance of EquationGroup keyed by the
            input argument key.
        """

        # order of operator map enforces order of operations
        op_map = OrderedDict()
        op_map['+'] = operator.add
        op_map['-'] = operator.sub
        op_map['*'] = operator.mul
        op_map['/'] = operator.truediv
        op_map['^'] = operator.pow
        key = key.replace('**', '^')

        if any(c in key for c in ('[', ']', '{', '}')):
            msg = ('Cannot parse EquationGroup key with square or curly '
                   'brackets: {}'.format(key))
            logger.error(msg)
            raise ValueError(msg)

        while '(' in key:
            start_loc, end_loc = find_parens(key)[0]
            wkey = 'workspace_{}'.format(1 + len(workspace))
            assert wkey not in workspace
            pk = key[start_loc:end_loc]
            key = key.replace(pk, wkey)
            pk = pk.lstrip('(').rstrip(')')
            workspace[wkey] = obj._getitem(pk, workspace)

        if key in workspace:
            return workspace[key]

        for op_str, op_fun in op_map.items():
            if op_str in key:
                split_keys = key.partition(op_str)
                k1 = split_keys[0].strip()
                k2 = split_keys[2].strip()

                out1 = workspace.get(k1, None)
                if out1 is None:
                    out1 = obj._getitem(k1, workspace)

                out2 = workspace.get(k2, None)
                if out2 is None:
                    out2 = obj._getitem(k2, workspace)

                return op_fun(out1, out2)

    def _getitem(self, key, workspace):
        """Protected method for __getitem__ with additional args for
        recursive call.

        Parameters
        ----------
        key : str
            A key or set of keys (delimited by "::") to retrieve from this
            EquationGroup instance. For example, if this EquationGroup
            has an equation 'eqn1': 'm*x + b', the the input key could be:
            'eqn1' to retrieve the Equation object that holds 'm*x + b'.
            The input argument key can also be delimited like 'set_1::eqn1'
            to eetrieve eqn1 nested in a sub EquationGroup object "set_1".
            The input argument can also have embedded math like
            'set_1::eqn1 + set_2::eqn2 ** 2'.
        workspace : dict | None
            Temporary workspace to hold parts of math expressions. Useful
            for extracting and caching parenthetical statements.

        Returns
        -------
        out : Equation | EquationGroup
            An object in this instance of EquationGroup keyed by the
            input argument key.
        """

        if workspace is None:
            workspace = {}

        operators = ('+', '-', '*', '/', '^')
        if any(op in key for op in operators):
            return self._getitem_math(self, key, workspace)

        if key not in self and Equation.is_num(key):
            return Equation(key)

        if '::' in str(key):
            keys = key.split('::')
        else:
            keys = [key]

        keys = [str(k) for k in keys]
        out = self._group
        for eqn_key in keys:
            nn_eqns, nn_values, eqn_value = \
                self._get_nn_eqns_values(eqn_key, keys, out)

            if eqn_key in out:
                out = out[eqn_key]

            elif (self._interp_extrap_power or self._interp_extrap_year
                    and len(nn_eqns) > 1):
                x1, x3 = nn_values[0:2]
                y1, y3 = nn_eqns[0:2]
                out = (y3 - y1) * (eqn_value - x1) / (x3 - x1) + y1
                if not any(out.variables):
                    out = Equation(out.eval())

            elif any(nn_eqns):
                out = nn_eqns[0]

            else:
                msg = ('Could not retrieve equation key "{}", '
                       'could not find "{}" in last available keys: {}'
                       .format(key, eqn_key, list(out.keys())))
                logger.error(msg)
                raise KeyError(msg)

        return out

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
            to eetrieve eqn1 nested in a sub EquationGroup object "set_1".
            The input argument can also have embedded math like
            'set_1::eqn1 + set_2::eqn2 ** 2'.

        Returns
        -------
        out : Equation | EquationGroup
            An object in this instance of EquationGroup keyed by the
            input argument key.
        """

        return self._getitem(key, None)

    def __contains__(self, arg):
        return arg in self.keys()

    def _get_nn_eqns_values(self, eqn_key, keys, group):
        """Get lists of the nearest power or year dependent equations.

        Parameters
        ----------
        eqn_key
            Current equation retrieval key from the keys list
        keys : list
            List of equation strings delimited by '::'. For example, if
            retrieving "2015::eqn_group::eqn_2012", keys will be:
            ['2015', 'eqn_group', 'eqn_2012']
        group : EquationGroup
            Current group to retrieve equations from. This is typically the
            group level just before the eqn_key

        Returns
        -------
        nn_eqns : list
            List of Equation objects close to eqn_key. Empty list if eqn_key
            is not the last entry in keys.
        nn_values : list
            List of power or year values sorted by distance to eqn_key and
            corresponding to nn_eqns. Empty list if eqn_key is not the last
            entry in keys.
        eqn_value : None | int | float
            Power in MW (float) or year in YYYY format (int) from eqn_key.
            None if eqn_key is not the last entry in keys.
        """

        nn_eqns = []
        nn_values = []
        eqn_value = None
        i = keys.index(eqn_key)

        if i == (len(keys) - 1):
            # Only look for adjacent equations when were at the last
            # retrieval level in the EquationGroup
            if ((self._interp_extrap_power or self._use_nearest_power)
                    and self.is_power_eqn(eqn_key)):
                nn_eqns, nn_values = \
                    self.find_nearest_power_eqns(eqn_key, group=group)
                eqn_value = self._parse_power(eqn_key)[0]

            elif ((self._interp_extrap_year or self._use_nearest_year)
                    and self.is_year_eqn(eqn_key)):
                nn_eqns, nn_values = \
                    self.find_nearest_year_eqns(eqn_key, group=group)
                eqn_value = self._parse_year(eqn_key)[0]

        return nn_eqns, nn_values, eqn_value

    @classmethod
    def is_power_eqn(cls, key):
        """Determine if an equation key is power-based by looking for the
        case-insensitive regex pattern "_[0-9]*MW$"

        Parameters
        ----------
        key : str
            An equation key/name.

        Returns
        -------
        out : bool
            True if the regex pattern "_[0-9]*MW$" was found in key
        """

        out = False
        if cls._parse_power(key)[0] is not None:
            out = True

        return out

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

    def find_nearest_power_eqns(self, request, group=None):
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
        group : EquationGroup
            Group to be looking in for equations adjacent to the requested
            equation. Defaults to the top level self._group attribute.

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
        if group is None:
            group = self._group

        req_mw, base_str = self._parse_power(request)
        if req_mw:
            for key in group.keys():
                match_mw, match_base = self._parse_power(key)
                if match_mw and base_str == match_base:
                    eqn_keys.append(key)
                    eqn_powers.append(match_mw)

            if any(eqn_keys):
                eqn_pow_diffs = np.abs(req_mw - np.array(eqn_powers))
                indices = np.argsort(eqn_pow_diffs)
                eqn_keys = list(np.array(eqn_keys)[indices])
                eqn_powers = list(np.array(eqn_powers)[indices])

        eqns = [group[k] for k in eqn_keys]

        return eqns, eqn_powers

    @classmethod
    def is_year_eqn(cls, key):
        """Determine if an equation key is year-based by looking for
        *_YYYY in the key

        Parameters
        ----------
        key : str
            An equation key/name.

        Returns
        -------
        out : bool
            True if a year string *_YYYY is found in key
        """

        out = False
        if cls._parse_year(key)[0] is not None:
            out = True

        return out

    @staticmethod
    def _parse_year(key):
        """Parse the integer year from an equation key

        Parameters
        ----------
        key : str
            A key to retrieve an equation from this EquationGroup. Should
            have the *_YYYY pattern. Otherwise, None will be returned.

        Returns
        -------
        year : int | None
            The numeric year value in key. If the pattern is not found,
            None is returned
        base_str : str
            Key with the regex pattern stripped out.
        """

        base_str = key
        year = re.search('_[1-2][0-9]{3}$', key, flags=re.IGNORECASE)
        if year is not None:
            base_str = key.replace(year.group(0), '')
            year = int(year.group(0).lstrip('_'))

            # unlikely to be a year before 1800 or after 2200
            if year < 1800 or year > 2200:
                year = None
                base_str = key

        return year, base_str

    def find_nearest_year_eqns(self, request, group=None):
        """Find year-based (*_YYYY) equations in this EquationGroup that match
        the request difference in equation year.

        Parameters
        ----------
        request : str
            A key to retrieve an equation from this EquationGroup. Should
            have the *_YYYY pattern. Otherwise, None will be returned.
        group : EquationGroup
            Group to be looking in for equations adjacent to the requested
            equation. Defaults to the top level self._group attribute.

        Returns
        -------
        eqns : list
            List of Equation objects that match the request key and are sorted
            by difference in the YYYY specification to the input request key.
            If the request key does not have the YYYY specification or if no
            other keys in this EquationGroup match the request then this will
            return an empty list.
        eqn_years : list
            List of integer year YYYY values corresponding to eqns and sorted
            by difference in the YYYY specification to the input request key.
            If the request key does not have the YYYY specification or if no
            other keys in this EquationGroup match the request then this will
            return an empty list.
        """

        eqn_keys = []
        eqn_years = []
        if group is None:
            group = self._group

        req_yr, base_str = self._parse_year(request)
        if req_yr:
            for key in group.keys():
                match_yr, match_base = self._parse_year(key)
                if match_yr and base_str == match_base:
                    eqn_keys.append(key)
                    eqn_years.append(match_yr)

            if any(eqn_keys):
                eqn_pow_diffs = np.abs(req_yr - np.array(eqn_years))
                indices = np.argsort(eqn_pow_diffs)
                eqn_keys = list(np.array(eqn_keys)[indices])
                eqn_years = list(np.array(eqn_years)[indices])

        eqns = [group[k] for k in eqn_keys]

        return eqns, eqn_years

    @staticmethod
    def _parse_group(group):
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

        group = {str(k): v for k, v in group.items()}

        return group

    def set_default_variables(self, var_dict):
        """Set default variables available to this object and all sub-groups
        and equations within this object.

        Parameters
        ----------
        var_dict : dict | None
            Default variables namespace. Variables from this input will be
            passed to all Equation objects in this EquationGroup. These
            variables can always be overwritten when Equation.evaluate()
            is called.
        """

        if var_dict is not None:
            self._default_variables.update(copy.deepcopy(var_dict))
            for v in self.values():
                v.set_default_variables(var_dict)

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

    def head(self, n=5):
        """Return the first n lines of the group string representation"""
        return '\n'.join(str(self).split('\n')[:n])

    def tail(self, n=5):
        """Return the last n lines of the group string representation"""
        return '\n'.join(str(self).split('\n')[-1 * n:])

    @property
    def all_equations(self):
        """List of all Equation objects from this object."""
        return self._r_all_equations(self)

    def get(self, key, default_value):
        """Attempt to get a key from the EquationGroup, return
        default_value if the key could not be retrieved"""
        try:
            return self[key]
        except KeyError:
            return default_value

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
            s = ['EquationGroup object from "{}" with heirarchy:'
                 .format(self._base_name)]

        for k, v in self.items():
            if isinstance(v, Equation):
                s.append(str(v))
            else:
                s.append(str(k))
                s += ['\t' + x for x in str(v).split('\n')[1:]]

        return '\n'.join(s)

    def _parse_group(self, group):
        """Parse a group of equation strings defined in a yaml or json file

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

        group = super()._parse_group(group)

        for k, v in sorted(group.items()):
            if Equation.is_num(k):
                msg = ('You cannot use numbers as keys in group "{}"'
                       .format(self._base_name))
                logger.error(msg)
                raise ValueError(msg)

            if isinstance(v, (str, int, float)):
                group[k] = Equation(v, name=k)

            elif isinstance(v, dict):
                cls = self.__class__
                group[k] = cls(
                    v, name=k, interp_extrap_power=self._interp_extrap_power,
                    use_nearest_power=self._use_nearest_power,
                    interp_extrap_year=self._interp_extrap_year,
                    use_nearest_year=self._use_nearest_year)

            else:
                msg = ('Cannot use equation group value that is not a '
                       'string, float, int, or dictionary: {} ({})'
                       .format(v, type(v)))
                logger.error(msg)
                raise TypeError(msg)

        # if input variables for an equation are found in the same group, just
        # insert the equations corresponding to those variables
        working = True
        while working:
            working = False
            for group_key, eqn in group.items():
                if not isinstance(eqn, Equation):
                    continue
                for var in [v for v in eqn.variables if v in group]:
                    repl_str = '({})'.format(group[var].full)
                    new_eqn = eqn.full.replace(var, repl_str)
                    group[group_key] = eqn = eqn.replace_equation(new_eqn)
                    working = True

        return group

    @property
    def default_variables(self):
        """Get a dictionary of default variables from a variables.yaml file
        accessible to this object

        Returns
        -------
        dict
        """
        return self._default_variables


class VariableGroup(AbstractGroup):
    """Class to handle a single json or yaml file with multiple numerical
    variable definitions from variables.yaml files.
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

    def _parse_group(self, group):
        """Parse a group of numerical variables defined in a yaml or json file

        Parameters
        ----------
        group : str | dict
            String filepath to a yaml or json file containing one or more
            numerical variable definitions OR a pre-extracted dictionary
            from a yaml or json file with variable definitions.

        Returns
        -------
        group : dict
            Loaded dictionary from a yaml or json file with numerical
            variable definitions
        """

        group = super()._parse_group(group)

        for k, v in group.items():
            if Equation.is_num(k):
                msg = ('You cannot use numbers as keys in group "{}"'
                       .format(self._base_name))
                logger.error(msg)
                raise ValueError(msg)
            if isinstance(v, int):
                v = float(v)
                group[k] = v
            if not isinstance(v, float):
                msg = ('Cannot use variable group value that is not a '
                       'float: {} ({})'.format(v, type(v)))
                logger.error(msg)
                raise TypeError(msg)

        return group
