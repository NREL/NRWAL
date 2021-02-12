# -*- coding: utf-8 -*-
"""
Handler objects to interface with NRWAL equation directories
"""
import copy
import os
import logging

from NRWAL.handlers.equations import Equation
from NRWAL.handlers.groups import EquationGroup, VariableGroup

logger = logging.getLogger(__name__)


class EquationDirectory:
    """Class to handle a directory with one or more equation files or
    a directory containing subdirectories with one or more equation files.


    Examples
    --------

    The NRWAL EquationDirectory object is instantiated from a directory input
    arg that contains nested equation yaml or json files.

    >>> from NRWAL import EquationDirectory
    >>>
    >>> obj = EquationDirectory('./NRWAL')
    >>>
    >>> obj
    2015
        variables.yaml
            transmission_cost: 6536
            tower_cost: 3960
            pile_cost: 2250
            monopile_tp_cost: 3230
            lattice_cost: 4680
            jacket_tp_cost: 4599
            stiffened_column_cost: 3120
            tapered_column_cost: 4220
            truss_cost: 6250
            heave_plate_cost: 5250
            outfitting_cost: 7250
            perm_ballast_cost: 150
            operations_cost: 18880383
            port_cost: 25000000
            hz_turbine_factor: 0.05
            windflip_CAPEX: 50000000
            vertical_tow_OM_equip: 13400000
            lease_price: 50000000
        array.yaml
            fixed(depth, num_turbines)
            floating(depth, num_turbines)
        ...
        turbine_install.yaml
            jacket_3MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            jacket_6MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            jacket_10MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            jacket_12MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            jacket_15MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            monopile_3MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            monopile_6MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            monopile_10MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            monopile_12MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            monopile_15MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            semi_3MW(dist_p_to_s_nolimit, floating_downtime)
            semi_6MW(dist_p_to_s_nolimit, floating_downtime)
            semi_10MW(dist_p_to_s_nolimit, floating_downtime)
            semi_12MW(dist_p_to_s_nolimit, floating_downtime)
            semi_15MW(dist_p_to_s_nolimit, floating_downtime)
            spar_3MW(dist_a_to_s, dist_p_to_a, floating_downtime)
            spar_6MW(dist_a_to_s, dist_p_to_a, floating_downtime)
            spar_10MW(dist_a_to_s, dist_p_to_a, floating_downtime)
            spar_12MW(dist_a_to_s, dist_p_to_a, floating_downtime)
            spar_15MW(dist_a_to_s, dist_p_to_a, floating_downtime)


    Nested EquationDirectory, EquationGroup, and Equation objects can be
    retrieved using the python bracket syntax similar to a python dictionary.
    Nested retrievals are delimited by two colons.

    >>> type(obj['2015'])
    NRWAL.handlers.directories.EquationDirectory

    >>> type(obj['2015::array'])
    NRWAL.handlers.groups.EquationGroup

    >>> eqn = obj['2015::array::fixed']
    >>> type(eqn)
    NRWAL.handlers.equations.Equation

    >>> eqn
    fixed(depth, num_turbines)

    NRWAL Equation objects can be evaluated using kwargs.

    >>> import numpy as np
    >>> eqn.variables
    ['depth', 'num_turbines']

    >>> eqn.eval(**{k: np.ones(2) for k in eqn.variables})
    array([1.48410044e+08, 1.48410044e+08])

    >>> eqn.eval(depth=np.ones(2), num_turbines=np.ones(2))
    array([1.48410044e+08, 1.48410044e+08])

    NRWAL Equation objects can be operated on using the usual python math
    operators. Note that the tower_cost input arg in this equation group
    is set to a default value of 3960 based on the variables.yaml file present
    in the 2015 directory. As a result, this argument does not need to be
    input in the eval() call, but can still be overwritten at runtime if
    desired.

    >>> group = obj['2015::turbine']
    >>> group
    EquationGroup object from "turbine.yaml" with heirarchy:
    rna(turbine_capacity)
    horiz_spar_rna(turbine_capacity, hz_turbine_factor=0.05)
    jacket_tower(depth, turbine_capacity, tower_cost=3960)
    monopile_tower(depth, turbine_capacity, tower_cost=3960)
    spar_tower(turbine_capacity)
    horiz_spar_tower(turbine_capacity, hz_turbine_factor=0.05)
    semi_tower(turbine_capacity)

    >>> eqn = group['rna'] + group['monopile_tower']
    >>> eqn
    (rna(turbine_capacity) + monopile_tower(depth, turbine_capacity,
        tower_cost=3960))

    >>> eqn = group['rna'] - group['monopile_tower']
    >>>  eqn
    (rna(turbine_capacity) - monopile_tower(depth, turbine_capacity,
        tower_cost=3960))

    >>>  eqn = group['rna'] * group['monopile_tower']
    >>>  eqn
    (rna(turbine_capacity) * monopile_tower(depth, turbine_capacity,
        tower_cost=3960))

    >>>  eqn = group['rna'] / group['monopile_tower']
    >>>  eqn
    (rna(turbine_capacity) / monopile_tower(depth, turbine_capacity,
        tower_cost=3960))

    >>>  eqn = group['rna'] ** group['monopile_tower']
    >>>  eqn
    (rna(turbine_capacity) ** monopile_tower(depth, turbine_capacity,
        tower_cost=3960))

    >>> eqn = group['rna'] + group['monopile_tower'] ** 2
    >>> eqn
    (rna(turbine_capacity) + (monopile_tower(depth, turbine_capacity,
        tower_cost=3960) ** 2))

    The new Equation objects resulting from math operations can be evaluated
    just like the original Equation objects.

    >>> eqn = group['rna + monopile_tower']
    >>> eqn
    (rna(turbine_capacity) + monopile_tower(depth, turbine_capacity,
        tower_cost=3960))

    >>> eqn.variables
    ['depth', 'tower_cost', 'turbine_capacity']

    >>> eqn.eval(**{k: np.ones(2) for k in eqn.variables})
    array([1037835.27761686, 1037835.27761686])

    >>> eqn.eval(depth=np.ones(2), turbine_capacity=np.ones(2))
    array([1256782.29675191, 1256782.29675191])

    The EquationDirectory object can parse power-dependent equations by
    searching for the "_10MW" string in the equation name request and the
    equations present in the directory (10 is an example and can be any
    integer). By default, only an exact match is returned, but the
    EquationDirectory object can also be set to perform interpolation +
    extrapolation or nearest neighbor lookup. Interpolation and extrapolation
    take priority over the use_nearest_power kwarg.

    >>> obj['2015::spar']
    EquationGroup object from "spar.yaml" with heirarchy:
    install_3MW(dist_p_to_a, dist_p_to_s, floating_downtime)
    install_6MW(dist_p_to_a, dist_p_to_s, floating_downtime)
    install_10MW(dist_p_to_a, dist_p_to_s, floating_downtime)
    spar_3MW(dist_a_to_s, dist_p_to_a)
    spar_6MW(dist_a_to_s, dist_p_to_a)
    spar_10MW(dist_a_to_s, dist_p_to_a)
    stiffened_column(depth, turbine_capacity, stiffened_column_cost=3120)
    tapered_column(turbine_capacity, tapered_column_cost=4220)
    outfitting(depth, turbine_capacity, outfitting_cost=7250)
    perm_ballast(turbine_capacity, perm_ballast_cost=150)
    stiffened_column_gt10MW(depth, stiffened_column_cost=3120)
    tapered_column_gt10MW(tapered_column_cost=4220)
    outfitting_gt10MW(depth, outfitting_cost=7250)
    perm_ballast_gt10MW(perm_ballast_cost=150)

    >>> obj['2015::spar::spar_3MW']
    spar_3MW(dist_a_to_s, dist_p_to_a)

    >>> obj['2015::spar::spar_4MW']
    KeyError: 'Could not retrieve equation key "2015::spar::spar_4MW"

    >>> obj = EquationDirectory('./NRWAL', use_nearest_power=True)
    >>> obj['2015::spar::spar_4MW']
    spar_3MW(dist_a_to_s, dist_p_to_a)

    >>> obj = EquationDirectory('./NRWAL', interp_extrap_power=True)
    >>> obj['2015::spar::spar_4MW']
    ((((spar_6MW(dist_a_to_s, dist_p_to_a)
        - spar_3MW(dist_a_to_s, dist_p_to_a)) * 1.0) / 3.0)
     + spar_3MW(dist_a_to_s, dist_p_to_a))
    """

    def __init__(self, eqn_dir, interp_extrap_power=False,
                 use_nearest_power=False, interp_extrap_year=False,
                 use_nearest_year=False):
        """
        Parameters
        ----------
        eqn_dir : str
            Path to a directory with one or more equation files or a path to
            a directory containing subdirectories with one or more equation
            files.
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

        self._interp_extrap_power = interp_extrap_power
        self._use_nearest_power = use_nearest_power
        self._interp_extrap_year = interp_extrap_year
        self._use_nearest_year = use_nearest_year
        self._default_variables = {}
        self._base_name = os.path.basename(os.path.abspath(eqn_dir))
        self._dir_name = os.path.dirname(os.path.abspath(eqn_dir))
        self._eqns = self._parse_eqn_dir(
            eqn_dir, interp_extrap_power=interp_extrap_power,
            use_nearest_power=use_nearest_power,
            interp_extrap_year=interp_extrap_year,
            use_nearest_year=use_nearest_year)
        self.set_default_variables()

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
            other = cls(other, interp_extrap_power=self._interp_extrap_power,
                        use_nearest_power=self._use_nearest_power,
                        interp_extrap_year=self._interp_extrap_year,
                        use_nearest_year=self._use_nearest_year)

        out = copy.deepcopy(self)
        out._eqns.update(other._eqns)
        out.set_default_variables(other._default_variables)

        return out

    def _getitem(self, key, workspace):
        """Protected method for __getitem__ with additional args for
        recursive call.

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
            The input argument can also have embedded math like
            'set_1::eqn1 + set_2::eqn2 ** 2'.
        workspace : dict | None
            Temporary workspace to hold parts of math expressions. Useful
            for extracting and caching parenthetical statements.

        Returns
        -------
        out : Equation | EquationGroup | EquationDirectory
            An object in this instance of EquationDirectory keyed by the
            input argument key.
        """

        if workspace is None:
            workspace = {}

        operators = ('+', '-', '*', '/', '^')
        if any([op in key for op in operators]):
            return EquationGroup._getitem_math(self, key, workspace)

        if key not in self and Equation.is_num(key):
            return Equation(key)

        if '::' in str(key):
            keys = key.split('::')
        else:
            keys = [key]

        keys = [str(k) if not str(k).endswith(('.json', '.yml', '.yaml'))
                else os.path.splitext(str(k))[0]
                for k in keys]

        eqns = self._eqns
        for ikey in keys:
            try:
                eqns = eqns[ikey]
            except KeyError:
                msg = ('Could not retrieve equation key "{}", '
                       'could not find "{}" in last available keys: {}'
                       .format(key, ikey, list(eqns.keys())))
                # debug log statement to avoid unnecessary stdout
                logger.debug(msg)
                raise KeyError(msg)

        return eqns

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
            The input argument can also have embedded math like
            'set_1::eqn1 + set_2::eqn2 ** 2'.

        Returns
        -------
        out : Equation | EquationGroup | EquationDirectory
            An object in this instance of EquationDirectory keyed by the
            input argument key.
        """

        return self._getitem(key, None)

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
    def _parse_eqn_dir(cls, eqn_dir, interp_extrap_power=False,
                       use_nearest_power=False, interp_extrap_year=False,
                       use_nearest_year=False):
        """Load in an equation directory and all subdirectories and files into
        a dictionary structure with nested NRWAL EquationGroup and Equation
        objects.

        Parameters
        ----------
        eqn_dir : str
            Path to a directory with one or more equation files or a path to
            a directory containing subdirectories with one or more equation
            files.
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
        for name in sorted(os.listdir(eqn_dir)):
            path = os.path.join(eqn_dir, name)

            is_directory = os.path.isdir(path)
            type_check = name.endswith(('.json', '.yml', '.yaml'))
            variables_file = (
                type_check and os.path.splitext(name)[0] == 'variables')
            ignore_check = name.startswith(('.', '__'))

            if is_directory and not ignore_check:
                obj = cls(path, interp_extrap_power=interp_extrap_power,
                          use_nearest_power=use_nearest_power,
                          interp_extrap_year=interp_extrap_year,
                          use_nearest_year=use_nearest_year)
                if any(obj.keys()):
                    eqns[name] = obj

            elif variables_file:
                key = os.path.splitext(name)[0]
                try:
                    eqns[key] = VariableGroup(
                        path, interp_extrap_power=interp_extrap_power,
                        use_nearest_power=use_nearest_power,
                        interp_extrap_year=interp_extrap_year,
                        use_nearest_year=use_nearest_year)
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
                        path, interp_extrap_power=interp_extrap_power,
                        use_nearest_power=use_nearest_power,
                        interp_extrap_year=interp_extrap_year,
                        use_nearest_year=use_nearest_year)
                except Exception as e:
                    msg = ('Could not parse an EquationGroup from '
                           'file: "{}". Received the exception: {}'
                           .format(name, e))
                    logger.exception(msg)
                    raise RuntimeError(msg)

        return eqns

    def head(self, n=5):
        """Return the first n lines of the directory string representation"""
        return '\n'.join(str(self).split('\n')[:n])

    def tail(self, n=5):
        """Return the last n lines of the directory string representation"""
        return '\n'.join(str(self).split('\n')[-1 * n:])

    def set_default_variables(self, var_group=None, force_update=False):
        """Set default variables available to this object and all
        sub-directories, sub-groups, and equations within this object.

        Parameters
        ----------
        var_group : dict | None
            Default variables namespace that will be set to the EquationGroup
            objects in this EquationDirectory unless other variables.yaml files
            are found on the local level in sub-directories. These variables
            can always be overwritten when Equation.evaluate() is called.
        force_update : bool
            Flag to force updates to local VariableGroup objects
            (variables.yaml files) contained in lower level directories.
            Default is False so that lower level directories will maintain
            their locally-defined default variables.
        """

        if var_group is None:
            var_group = {}

        if 'variables' in self.keys() and not force_update:
            # pylint: disable=E1101
            # this makes it so that VariableGroup on lower directory levels
            # will not be overwritten by the higher VariableGroup objects
            assert isinstance(self['variables'], VariableGroup)
            var_group.update(self['variables'].var_dict)

        self._default_variables.update(copy.deepcopy(var_group))

        for v in self.values():
            if isinstance(v, (EquationDirectory, EquationGroup, Equation)):
                v.set_default_variables(var_group)

    @property
    def default_variables(self):
        """Get a dictionary of default variables from a variables.yaml file
        accessible to this object

        Returns
        -------
        dict
        """
        return self._default_variables

    @property
    def all_equations(self):
        """List of all Equation objects from this object."""
        return EquationGroup._r_all_equations(self)

    def get(self, key, default_value):
        """Attempt to get a key from the EquationDirectory, return
        default_value if the key could not be retrieved"""
        try:
            return self[key]
        except KeyError:
            return default_value

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
