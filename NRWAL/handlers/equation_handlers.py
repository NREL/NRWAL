# -*- coding: utf-8 -*-
"""
Handler objects to interface with NRWAL equation library.
"""
from abc import ABC
import copy
import re
import os
import json
import yaml
import numpy as np
import logging


logger = logging.getLogger(__name__)


class Equation:
    """Class to handle and evaluate a single wind cost equation string."""

    # illegal substrings that cannot be in cost equations
    ILLEGAL = ('import ', 'os.', 'sys.', '.__', '__.', 'eval', 'exec')

    def __init__(self, eqn, name=None):
        """
        Parameters
        ----------
        eqn : str | int | float
            Cost equation in a string representation or a single number e.g.:
            "-34.80 * depth ** 2 + 207619.80 * depth + 221197699.89"
        name : str | None
            Optional equation name / key for string formatting
        """

        self._global_variables = {}
        self._base_name = name
        self._eqn = str(eqn)
        self._preflight()

    def _preflight(self):
        """Run preflight checks on the equation string."""
        for substr in self.ILLEGAL:
            if substr in str(self._eqn):
                msg = ('Will not evaluate string which contains "{}": {}'
                       .format(substr, self._eqn))
                logger.error(msg)
                raise ValueError(msg)

    @staticmethod
    def _check_input_args(kwargs):
        """Check that input args to equation are of expected types."""
        assert isinstance(kwargs, dict)
        for k, v in kwargs.items():
            assert isinstance(k, str)
            assert isinstance(v, (int, float, np.ndarray, list, tuple))

    def __repr__(self):
        return str(self._eqn)

    def __str__(self):
        vars_str = [v for v in self.vars if v not in self.global_variables]
        vars_str = str(vars_str).replace('[', '').replace(']', '')\
            .replace("'", '').replace('"', '')

        gvars_str = [v for v in self.vars if v in self.global_variables]
        for gvar in gvars_str:
            base_str = ', ' if bool(vars_str) else ''
            kw_str = '{}={}'.format(gvar, self.global_variables[gvar])
            vars_str += base_str + kw_str

        if self._base_name is None:
            s = 'Equation({})'.format(vars_str)
        else:
            s = '{}({})'.format(self._base_name, vars_str)

        return s

    def __contains__(self, arg):
        return arg in self._eqn

    def _set_variables(self, var_dict):
        """Pass VariableGroup variable dictionaries defined within equation
        directories to adjacent and sub-level EquationGroup and Equation
        objects.

        Parameters
        ----------
        var_dict : dict | None
            Variables group dictionary from a higher level than or adjacent to
            this instance of Equation. Variables from this input will be
            passed to the equation for evaluation. These variables can always
            be overwritten when Equation.evaluate() is called.
        """
        if var_dict is not None:
            self._global_variables.update(copy.deepcopy(var_dict))

    @staticmethod
    def _merge_vars(var_group, kwargs):
        """Create a copied namespace of input args for the Equation evaluation.
        This is the global-style variables set with the self._set_variables()
        method and the self._global_variables attribute updated with kwargs
        from the self.evaluate() method call.

        Parameters
        ----------
        var_group : dict | None
            Variables group from a higher level than or adjacent to this
            instance of Equation. Variables from this input will be
            passed to the equation for evaluation. These variables can always
            be overwritten when Equation.evaluate() is called.
        kwargs : dict
            Keyword arguments setting variables of the equation.

        Returns
        -------
        out : dict
            Copied input args from var_group updated with kwargs.
        """

        if var_group is None:
            out = {}
        else:
            out = copy.deepcopy(var_group)

        out.update(kwargs)
        return out

    @staticmethod
    def is_num(s):
        """Check if a string is a number"""
        try:
            float(s)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def is_method(s):
        """Check if a string is a numpy/pandas or python builtin method"""
        return bool(s.startswith(('np.', 'pd.')) or s in dir(__builtins__))

    @property
    def full(self):
        """Get the full equation string without any pretty formatting."""
        return self._eqn

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

    @property
    def vars(self):
        """Get a list of variable names that the Equation uses as input.

        Returns
        -------
        vars : list
            List of strings representing variable names that were parsed from
            the equation string. This will return an empty list if the equation
            has no variables.
        """
        delimiters = ('*', '/', '+', '-', ' ', '(', ')', '[', ']')
        regex_pattern = '|'.join(map(re.escape, delimiters))
        var_names = [sub for sub in re.split(regex_pattern, str(self._eqn))
                     if sub
                     and not self.is_num(sub)
                     and not self.is_method(sub)]
        var_names = list(set(var_names))
        return var_names

    def evaluate(self, **kwargs):
        """Evaluate the equation string and return the result

        Parameters
        ----------
        kwargs : dict
            Keyword arguments setting variables of the equation. Note that this
            is **kwargs so this method can be run in either of these syntaxes:
                Equation.evaluate(input1=10, input2=20)
                Equation.evaluate({'input1': 10, 'input2': 20})
        """
        self._check_input_args(kwargs)
        kwargs = self._merge_vars(self._global_variables, kwargs)

        missing = [v for v in self.vars
                   if v not in globals()
                   and v not in kwargs]
        if any(missing):
            msg = ('Cannot evaluate "{}", missing the following input args: {}'
                   .format(self, missing))
            logger.error(msg)
            raise KeyError(msg)

        return eval(str(self._eqn), globals(), kwargs)


class AbstractGroup(ABC):
    """Abstract class for groupings of equations or variables in a single
    yaml or json file.
    """

    def __init__(self, group):
        """
        Parameters
        ----------
        group : str | dict
            String filepath to a yaml or json file containing one or more
            equation strings OR a pre-extracted dictionary from a yaml or
            json file with equation strings as values.
        """
        self._base_name = None
        if isinstance(group, str):
            self._base_name = os.path.basename(group)

        self._group = self._parse_group(group)

    def __repr__(self):
        return str(self)

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
            The input argument key can also be delimited like 'eqn_set_1::eqn1'
            to retrieve eqn1 nested in a sub EquationGroup object.

        Returns
        -------
        out : Equation | EquationGroup
            An object in this instance of EquationGroup keyed by the
            input argument key.
        """

        if '::' in str(key):
            keys = key.split('::')
        else:
            keys = [key]

        keys = [str(k) for k in keys]

        eqns = self._group
        for ikey in keys:
            if ikey in eqns:
                eqns = eqns[ikey]
            else:
                msg = ('Could not retrieve equation key "{}", '
                       'could not find "{}" in last available keys: {}'
                       .format(key, ikey, list(eqns.keys())))
                logger.error(msg)
                raise KeyError(msg)

        return eqns

    def __contains__(self, arg):
        return arg in self.keys()

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

    def __init__(self, group):
        """
        Parameters
        ----------
        group : str | dict
            String filepath to a yaml or json file containing one or more
            equation strings OR a pre-extracted dictionary from a yaml or
            json file with equation strings as values.
        """
        super().__init__(group)
        self._global_variables = {}

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

        for k, v in eqn_group.items():
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

    @classmethod
    def _parse_group(cls, var_group):
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


class EquationDirectory:
    """Class to handle a directory with one or more equation files or
    a directory containing subdirectories with one or more equation files.
    """

    def __init__(self, eqn_dir):
        """
        Parameters
        ----------
        eqn_dir : str
            Path to a directory with one or more equation files or a path to
            a directory containing subdirectories with one or more equation
            files.
        """
        self._global_variables = {}
        self._base_name = os.path.basename(os.path.abspath(eqn_dir))
        self._eqns = self._parse_eqn_dir(eqn_dir)
        self._set_variables()

    def __getitem__(self, key):
        """Retrieve a nested Equation, EquationGroup, or EquationDirectory
        object from this instance of an EquationDirectory.

        Parameters
        ----------
        key : str
            A key or set of keys (delimited by "::") to retrieve from this
            EquationDirectory instance. For example, if this EquationDirectory
            has a eqns.yaml file directly in the directory, the input key could
            be 'eqns' or 'eqns.yaml' to retrieve the EquationGroup that holds
            eqns.yaml.  Alternatively, if eqns.yaml has an equation
            'eqn1': 'm*x + b', the the input key could be: 'eqns::eqn1' to
            retrieve the Equation object that holds 'm*x + b'

        Returns
        -------
        out : Equation | EquationGroup | EquationDirectory
            An object in this instance of EquationDirectory keyed by the
            input argument key.
        """

        if '::' in str(key):
            keys = key.split('::')
        else:
            keys = [key]

        keys = [str(k) if not str(k).endswith(('.json', '.yml', '.yaml'))
                else os.path.splitext(str(k))[0]
                for k in keys]

        eqns = self._eqns
        for ikey in keys:
            if ikey in eqns:
                eqns = eqns[ikey]
            else:
                msg = ('Could not retrieve equation key "{}", '
                       'could not find "{}" in last available keys: {}'
                       .format(key, ikey, list(eqns.keys())))
                logger.error(msg)
                raise KeyError(msg)

        return eqns

    def __repr__(self):
        return str(self._eqns)

    def __str__(self):
        s = ['EquationDirectory object from root directory "{}" '
             'with heirarchy:'.format(self._base_name)]

        var_groups = [v for v in self.values() if isinstance(v, VariableGroup)]
        eqn_groups = [v for v in self.values() if isinstance(v, EquationGroup)]
        dirs = [v for v in self.values() if isinstance(v, EquationDirectory)]

        for group in (var_groups, eqn_groups, dirs):
            for v in group:
                s.append(v._base_name)
                s += ['\t' + x for x in str(v).split('\n')[1:]]

        return '\n'.join(s)

    def __contains__(self, arg):
        return arg in self.keys()

    @classmethod
    def _parse_eqn_dir(cls, eqn_dir):
        """
        Parameters
        ----------
        eqn_dir : str
            Path to a directory with one or more equation files or a path to
            a directory containing subdirectories with one or more equation
            files.

        Returns
        -------
        eqns : dict
            Heirarchy of all sub directories and equations in the input
            eqn_dir organized into EquationGroup objects for the equation
            files and Equation objects for the single equations in each
            equation file. Will also contain nested EquationDirectory objects
            for nested sub directories
        """

        eqns = {}
        for name in os.listdir(eqn_dir):
            path = os.path.join(eqn_dir, name)

            is_directory = os.path.isdir(path)
            type_check = name.endswith(('.json', '.yml', '.yaml'))
            variables_file = (
                type_check and os.path.splitext(name)[0] == 'variables')
            ignore_check = name.startswith(('.', '__'))

            if is_directory and not ignore_check:
                obj = cls(path)
                if any(obj.keys()):
                    eqns[name] = obj

            elif variables_file:
                key = os.path.splitext(name)[0]
                try:
                    eqns[key] = VariableGroup(path)
                except Exception as e:
                    msg = ('Could not parse an VariableGroup from '
                           'file: "{}". Received the exception: {}'
                           .format(name, e))
                    logger.exception(msg)
                    raise RuntimeError(msg)

            elif type_check and not ignore_check:
                key = os.path.splitext(name)[0]
                try:
                    eqns[key] = EquationGroup(path)
                except Exception as e:
                    msg = ('Could not parse an EquationGroup from '
                           'file: "{}". Received the exception: {}'
                           .format(name, e))
                    logger.exception(msg)
                    raise RuntimeError(msg)

        return eqns

    def _set_variables(self, var_group=None):
        """Pass VariableGroup variable dictionaries defined within equation
        directories to adjacent and sub-level EquationGroup and Equation
        objects.

        Parameters
        ----------
        eqn_dir : EquationDirectory
            Equation directory object to set VariableGroup objects in.
        var_group : dict | None
            Variables group dictionary from a higher level in the equation
            heirarchy than eqn_dir that will be set to the EquationGroup
            objects in this EquationDirectory unless other VariableGroups are
            found on the local level in sub dirs. These variables can always
            be overwritten when Equation.evaluate() is called.
        """

        if var_group is None:
            var_group = {}

        if 'variables' in self.keys():
            assert isinstance(self['variables'], VariableGroup)
            # pylint: disable=E1101
            var_group.update(self['variables'].var_dict)

        self._global_variables.update(copy.deepcopy(var_group))

        for v in self.values():
            if isinstance(v, EquationGroup):
                v._set_variables(var_group)

            elif isinstance(v, EquationDirectory):
                v._set_variables(var_group=var_group)

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

    def keys(self):
        """Get the 1st level of equation keys, same as dict.keys()"""
        return self._eqns.keys()

    def items(self):
        """Get the 1st level of equation (keys, values), same as dict.items().
        """
        return self._eqns.items()

    def values(self):
        """Get the 1st level of equation values, same as dict.values()"""
        return self._eqns.values()
