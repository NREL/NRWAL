# -*- coding: utf-8 -*-
"""
Handler objects to interface with NRWAL equation library.
"""
import os
import json
import yaml
import logging


logger = logging.getLogger(__name__)


class Equation:
    """Class to handle and evaluate a single wind cost equation string."""

    # illegal substrings that cannot be in cost equations
    ILLEGAL = ('import ', 'os.', 'sys.', '.__', '__.')

    def __init__(self, eqn_str, preflight=True):
        """
        Parameters
        ----------
        eqn_str : str
            Cost equation in a string representation e.g.:
            "-34.80 * depth ** 2 + 207619.80 * depth + 221197699.89"
        preflight : bool
            Flag to run preflight checks on the equation string.
        """
        self._eqn_str = eqn_str
        if preflight:
            self._preflight()

    def _preflight(self):
        """Run preflight checks on the equation string."""
        for substr in self.ILLEGAL:
            if substr in str(self._eqn_str):
                msg = ('Will not evaluate string which contains "{}": {}'
                       .format(substr, self._eqn_str))
                logger.error(msg)
                raise ValueError(msg)

    def __repr__(self):
        return str(self._eqn_str)

    def __str__(self):
        return str(self._eqn_str)

    def __contains__(self, arg):
        return arg in self._eqn_str

    def evaluate(self):
        """Evaluate the equation string and return the result"""
        return eval(self._eqn_str)


class EquationGroup:
    """Class to handle a single json or yaml file with multiple wind cost
    equations.
    """

    def __init__(self, eqn_group):
        """
        Parameters
        ----------
        eqn_group : str | dict
            String filepath to a yaml or json file containing one or more
            equation strings OR a pre-extracted dictionary from a yaml or
            json file with equation strings as values.
        """
        self._base_name = None
        if isinstance(eqn_group, str):
            self._base_name = os.path.basename(eqn_group)

        self._eqn_group = self._parse_eqn_group(eqn_group)

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

        eqns = self._eqn_group
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
        return str(self)

    def __str__(self):
        s = ['EquationGroup object with heirarchy:']
        if self._base_name is not None:
            s = ['EquationGroup object from file "{}" with heirarchy:'
                 .format(self._base_name)]

        for k, v in self.items():
            s.append(str(k))
            if isinstance(v, Equation):
                str_eq = str(v) if len(str(v)) < 50 else str(v)[:50] + '...'
                s.append('\t' + str_eq)
            else:
                s += ['\t' + x for x in str(v).split('\n')[1:]]

        return '\n'.join(s)

    def __contains__(self, arg):
        return arg in self.keys()

    @classmethod
    def _parse_eqn_group(cls, eqn_group):
        """
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

        if isinstance(eqn_group, str):
            if not os.path.exists(eqn_group):
                msg = 'Cannot find equation file path: {}'.format(eqn_group)
                logger.error(msg)
                raise FileNotFoundError(msg)

            if eqn_group.endswith('.json'):
                with open(eqn_group, 'r') as f:
                    eqn_group = json.load(f)

            elif eqn_group.endswith(('.yml', '.yaml')):
                with open(eqn_group, 'r') as f:
                    eqn_group = yaml.safe_load(f)

            else:
                msg = ('Cannot load file path, must be json or yaml: {}'
                       .format(eqn_group))
                logger.error(msg)
                raise ValueError(msg)

        if not isinstance(eqn_group, dict):
            msg = 'Cannot use eqn_group of type: {}'.format(type(eqn_group))
            logger.error(msg)
            raise TypeError(msg)

        for k, v in eqn_group.items():
            if isinstance(v, (str, int, float)):
                eqn_group[k] = Equation(v)

            elif isinstance(v, dict):
                eqn_group[k] = cls(v)

            else:
                msg = ('Cannot use equation group value that is not a '
                       'string, float, int, or dictionary: {} ({})'
                       .format(v, type(v)))
                logger.error(msg)
                raise TypeError(msg)

        return eqn_group

    def keys(self):
        """Get the 1st level of equation group keys, same as dict.keys()"""
        return self._eqn_group.keys()

    def items(self):
        """Get the 1st level of equation (keys, values), same as dict.items().
        """
        return self._eqn_group.items()

    def values(self):
        """Get the 1st level of equation values, same as dict.values()"""
        return self._eqn_group.values()


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
        self._base_name = os.path.basename(os.path.abspath(eqn_dir))
        self._eqns = self._parse_eqn_dir(eqn_dir)

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
        s = ['EquationDirectory object from base directory "{}" '
             'with heirarchy:'.format(self._base_name)]

        for v in self.values():
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
            type_check = name.endswith(('.json', '.yml', '.yaml'))
            ignore_check = name.startswith(('.', '__'))

            if os.path.isdir(path) and not ignore_check:
                obj = cls(path)
                if any(obj.keys()):
                    eqns[name] = obj

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
