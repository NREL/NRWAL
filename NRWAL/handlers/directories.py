# -*- coding: utf-8 -*-
"""
Handler objects to interface with NRWAL equation library.
"""
import copy
import os
import logging

from NRWAL.handlers.groups import EquationGroup, VariableGroup

logger = logging.getLogger(__name__)


class EquationDirectory:
    """Class to handle a directory with one or more equation files or
    a directory containing subdirectories with one or more equation files.
    """

    def __init__(self, eqn_dir, interp_extrap=False, use_nearest=False):
        """
        Parameters
        ----------
        eqn_dir : str
            Path to a directory with one or more equation files or a path to
            a directory containing subdirectories with one or more equation
            files.
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

        self._interp_extrap = interp_extrap
        self._use_nearest = use_nearest
        self._global_variables = {}
        self._base_name = os.path.basename(os.path.abspath(eqn_dir))
        self._eqns = self._parse_eqn_dir(eqn_dir, interp_extrap=interp_extrap,
                                         use_nearest=use_nearest)
        self._set_variables()

    def __add__(self, other):
        """Add another equation dir to this instance of EquationDirectory
        (self) and return a new EquationDirectory object that updates this
        instance with the new input. Note that overlapping sub directories or
        EquationGroups in the original EquationDirectory can be overwritten
        by the new input if a duplicate key exists.

        Parameters
        ----------
        other : EquationDirectory | str
            Another EquationDirectory object or path to an
            EquationDirectory to add to this instance of
            EquationDirectory (self).

        Returns
        -------
        out : EquationDirectory
            A new EquationDirectory instance with this instance of
            EquationDirectory (self) updated with the input EquationDirectory.
            Note that overlapping sub directories or EquationGroups in the
            original EquationDirectory may be overwritten by the new input if
            a duplicate key exists.
        """
        cls = self.__class__
        if isinstance(other, str):
            other = cls(other, interp_extrap=self._interp_extrap,
                        use_nearest=self._use_nearest)

        out = copy.deepcopy(self)
        out._eqns.update(other._eqns)
        out._set_variables(other._global_variables)

        return out

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
        return str(self)

    def __str__(self):
        s = ['EquationDirectory object from root directory "{}" '
             'with heirarchy:'.format(self._base_name)]

        var_groups = [v for v in self.values() if isinstance(v, VariableGroup)]
        eqn_groups = [v for v in self.values() if isinstance(v, EquationGroup)]
        dirs = [v for v in self.values() if isinstance(v, EquationDirectory)]

        for group in (var_groups, eqn_groups, dirs):
            for v in group:
                if v._base_name is not None:
                    s.append(v._base_name)
                s += ['\t' + x for x in str(v).split('\n')[1:]]

        return '\n'.join(s)

    def __contains__(self, arg):
        return arg in self.keys()

    @classmethod
    def _parse_eqn_dir(cls, eqn_dir, interp_extrap=False, use_nearest=False):
        """
        Parameters
        ----------
        eqn_dir : str
            Path to a directory with one or more equation files or a path to
            a directory containing subdirectories with one or more equation
            files.
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
                obj = cls(path, interp_extrap=interp_extrap,
                          use_nearest=use_nearest)
                if any(obj.keys()):
                    eqns[name] = obj

            elif variables_file:
                key = os.path.splitext(name)[0]
                try:
                    eqns[key] = VariableGroup(
                        path, interp_extrap=interp_extrap,
                        use_nearest=use_nearest)
                except Exception as e:
                    msg = ('Could not parse an VariableGroup from '
                           'file: "{}". Received the exception: {}'
                           .format(name, e))
                    logger.exception(msg)
                    raise RuntimeError(msg)

            elif type_check and not ignore_check:
                key = os.path.splitext(name)[0]
                try:
                    eqns[key] = EquationGroup(
                        path, interp_extrap=interp_extrap,
                        use_nearest=use_nearest)
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
