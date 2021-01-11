# -*- coding: utf-8 -*-
"""
NRWAL config framework.
"""
import logging
import pandas as pd
import yaml
import json
import os
import operator
from collections import OrderedDict

from NRWAL.handlers.equations import Equation
from NRWAL.handlers.groups import EquationGroup
from NRWAL.handlers.directories import EquationDirectory

logger = logging.getLogger(__name__)


class NrwalConfig:
    """Config framework for NRWAL.

    Examples
    --------

    The NrwalConfig object can be instantiated from a config yaml file for
    from a python dictionary. The config is based on a NRWAL equation directory
    that can be specified by the "equation_directory" key in the config or will
    be defaulted to the NRWAL repository equation directory. Please note that
    the test config used in this example is completely fictitious and is
    for demonstration purposes only.

    >>> from NRWAL import NrwalConfig
    >>> obj = NrwalConfig('./tests/data/test_configs/test_config_00_good.yml')
    >>> obj
    NrwalConfig object with equation directory: /home/gbuster/code/NRWAL/NRWAL
    num_turbines
            6.0
    fixed_charge_rate
            0.096
    array
            fixed(depth, num_turbines=6.0)
    export
            fixed(dist_s_to_l)
    grid
            grid_connection(dist_l_to_ts, transmission_multi, turbine_capacity,
                            num_turbines=6.0, transmission_cost=6536.67)
    monopile
            EquationGroup object from "monopile.yaml" with heirarchy:
            pslt_3MW(depth, dist_p_to_s)
            pslt_6MW(depth, dist_p_to_s)
            pslt_10MW(depth, dist_p_to_s)
            pslt_12MW(depth, dist_p_to_s)
            pslt_15MW(depth, dist_p_to_s)
            install_3MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            install_6MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            install_10MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            install_12MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
            install_15MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
    monopile_costs
            (pslt_12MW(depth, dist_p_to_s) + install_12MW(depth, dist_p_to_s,
             fixed_downtime, turbine_capacity))
    electrical
            (fixed(depth, num_turbines=6.0) * (fixed(dist_s_to_l)
             + grid_connection(dist_l_to_ts, transmission_multi,
             turbine_capacity, num_turbines=6.0, transmission_cost=6536.67)))
    electrical_duplicate
            (fixed(depth, num_turbines=6.0) * (fixed(dist_s_to_l)
             + grid_connection(dist_l_to_ts, transmission_multi,
             turbine_capacity, num_turbines=6.0, transmission_cost=6536.67)))
    capex
            (fixed(depth, num_turbines=6.0) * (fixed(dist_s_to_l)
             + grid_connection(dist_l_to_ts, transmission_multi,
             turbine_capacity, num_turbines=6.0, transmission_cost=6536.67)))
    lcoe
            ((fixed(depth, num_turbines=6.0) * (fixed(dist_s_to_l)
             + grid_connection(dist_l_to_ts, transmission_multi,
             turbine_capacity, num_turbines=6.0, transmission_cost=6536.67)))
             * 0.096)

    Objects can be retrieved from the NrwalConfig object using the python
    bracket syntax similar to a python dictionary. You can see here how
    values in the config object correspond to: global variables defined in
    the config (e.g. 'num_turbines'), NRWAL EquationGroup objects that
    organize the equations found in the equation directory (e.g. 'monopile'),
    or single NRWAL Equation objects that will output numerical data when
    evaluated (e.g. 'monopile_costs').

    >>> type(obj['num_turbines'])
    float
    >>> obj['num_turbines']
    6.0

    >>> type(obj['monopile'])
    NRWAL.handlers.groups.EquationGroup
    >>> obj['monopile']
    EquationGroup object from "monopile.yaml" with heirarchy:
    pslt_3MW(depth, dist_p_to_s)
    pslt_6MW(depth, dist_p_to_s)
    pslt_10MW(depth, dist_p_to_s)
    pslt_12MW(depth, dist_p_to_s)
    pslt_15MW(depth, dist_p_to_s)
    install_3MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
    install_6MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
    install_10MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
    install_12MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)
    install_15MW(depth, dist_p_to_s, fixed_downtime, turbine_capacity)

    >>> type(obj['monopile_costs'])
    NRWAL.handlers.equations.Equation
    >>> obj['monopile_costs']
    (pslt_12MW(depth, dist_p_to_s) + install_12MW(depth, dist_p_to_s, fixed_...

    There are a number of helpful properties that show what variables are
    available or required for all of the Equation objects in the config. Note
    that the global variables are passed into each of the Equation objects
    defined in the NrwalConfig, although these can always be overwritten by
    the NrwalConfig inputs.

    >>> obj.global_variables
    {'num_turbines': 6.0, 'fixed_charge_rate': 0.096}

    >>> obj.all_variables
    ['depth',
     'dist_l_to_ts',
     'dist_p_to_s',
     'dist_s_to_l',
     'fixed_charge_rate',
     'fixed_downtime',
     'num_turbines',
     'transmission_cost',
     'transmission_multi',
     'turbine_capacity']

    >>> obj.required_inputs
    ['depth',
     'dist_l_to_ts',
     'dist_p_to_s',
     'dist_s_to_l',
     'fixed_downtime',
     'transmission_multi',
     'turbine_capacity']

    >>> obj.solvable
    False

    The NrwalConfig object can take a dictionary or DataFrame of inputs that
    will be provided to all of the Equation objects. Inputs can be passed to
    the NrwalConfig constructor or later to the NrwalConfig inputs property.
    Note that passing new data to the inputs property will update the inputs
    dictionary, not overwrite it. Inputs can also be passed to the NrwalConfig
    object at runtime via the evaluate() method.

    >>> obj.inputs
    {}

    >>> obj.inputs = {'depth': np.ones(3)}
    >>> obj.inputs
    {'depth': array([1., 1., 1.])}

    >>> obj.inputs['depth'] = 2 * np.ones(3)
    >>> obj.inputs
    {'depth': array([2., 2., 2.])}

    >>> obj.inputs = {'dist_p_to_s': np.ones(3)}
    >>> obj.inputs
    {'depth': array([2., 2., 2.]), 'dist_p_to_s': array([1., 1., 1.])}

    >>> obj.missing_inputs
    ['dist_l_to_ts',
     'dist_s_to_l',
     'fixed_downtime',
     'transmission_multi',
     'turbine_capacity']

    >>> obj.solvable
    False

    Finally, the NrwalConfig object can be evaluated, which really means that
    every Equation object in the NrwalConfig will be evaluated. Here you can
    see the evaluate function being called with all remaining missing inputs
    defined in the input argument (all the inputs that were not already passed
    into the config inputs). The output is a dictionary of data with the keys
    from the input config that map directly to Equations. Note that keys from
    the input config like "num_turbines" and "monopile" map to global variables
    and EquationGroups respectively, and so are not included in the outputs.
    The outputs will also be saved to the NrwalConfig.outputs property.

    >>> obj.evaluate(inputs={k: np.ones(3) for k in obj.missing_inputs})
    {'array': array([1.52304188e+08, 1.52304188e+08, 1.52304188e+08]),
     'export': array([92471016.757, 92471016.757, 92471016.757]),
     'grid': array([39220., 39220., 39220.]),
     'monopile_costs': array([inf, inf, inf]),
     'electrical': array([1.40896965e+16, 1.40896965e+16, 1.40896965e+16]),
     'electrical_duplicate': array([1.40896965e+16, 1.40896965e+16,
                                    1.40896965e+16]),
     'capex': array([1.40896965e+16, 1.40896965e+16, 1.40896965e+16]),
     'lcoe': array([1.35261086e+15, 1.35261086e+15, 1.35261086e+15])}
    """

    DEFAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def __init__(self, config, inputs=None, interp_extrap=False,
                 use_nearest=False):
        """
        Parameters
        ----------
        config : dict | str
            NRWAL config input. Can be a string filepath to a json or yml file
            or an extracted dictionary.
        inputs : dict | pd.DataFrame | None
            Optional namespace of input data to make available for the
            evaluation of the NrwalConfig. This can be set at any time after
            config initialization by setting the .inputs attribute.
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

        # parse inputs arg with inputs setter function
        self._inputs = {}
        self.inputs = inputs

        config, eqn_dir = self._load_config(config)
        self._eqn_dir = EquationDirectory(eqn_dir, interp_extrap=interp_extrap,
                                          use_nearest=use_nearest)
        self._global_variables = self._parse_global_variables(config)
        self._config = self._parse_config(config, self._eqn_dir,
                                          self._global_variables)

        self._outputs = {}

    @classmethod
    def _load_config(cls, config):
        """Load a config dictionary from filepath.

        Parameters
        ----------
        config : dict | str
            NRWAL config input. Can be a string filepath to a json or yml file
            or an extracted dictionary.

        Returns
        -------
        config : dict
            Loaded dictionary from a yaml or json file with NRWAL config.
        eqn_dir : str
            Equation directory path to be used for this config.
        """

        if isinstance(config, str):
            if not os.path.exists(config):
                msg = 'Cannot find config file path: {}'.format(config)
                logger.error(msg)
                raise FileNotFoundError(msg)

            if config.endswith('.json'):
                with open(config, 'r') as f:
                    config = json.load(f)

            elif config.endswith(('.yml', '.yaml')):
                with open(config, 'r') as f:
                    config = yaml.safe_load(f)

            else:
                msg = ('Cannot load file path, must be json or yaml: {}'
                       .format(config))
                logger.error(msg)
                raise ValueError(msg)

        if not isinstance(config, dict):
            msg = 'Cannot use config of type: {}'.format(type(config))
            logger.error(msg)
            raise TypeError(msg)

        if 'equation_directory' not in config:
            msg = ('NrwalConfig using default "equation_directory": {}'
                   .format(cls.DEFAULT_DIR))
            logger.info(msg)
            config['equation_directory'] = cls.DEFAULT_DIR

        eqn_dir = config.pop('equation_directory')

        return config, eqn_dir

    @staticmethod
    def _parse_global_variables(config):
        """Parse out the global variables (constant numerical values)
        available within this config object.

        Parameters
        ----------
        config : dict
            NRWAL config dictionary mapping names (str) to expressions (str)

        Returns
        -------
        gvars : dict
            Dictionary of global variables (constant numerical values)
            available within this config object.
        """

        gvars = {}
        for k, v in config.items():
            if Equation.is_num(v):
                gvars[k] = float(v)

        return gvars

    @classmethod
    def _parse_config(cls, config, eqn_dir, gvars):
        """Parse a config mapping of names-to-string-expressions into a
        mapping of names-to-Equation where Equation is either a constant
        numerical value (global variable) or a NRWAL Equation handler object.

        Parameters
        ----------
        config : dict
            NRWAL config dictionary mapping names (str) to expressions (str)
        eqn_dir : EquationDirectory
            EquationDirectory object holding Equation objects available to
            this config.
        gvars : dict
            Dictionary of global variables (constant numerical values)
            available within this config object.

        Returns
        -------
        out : dict
            Final parsed config dictionary mapping names (str) to either
            numeric values (global variables) or NRWAL Equation objects
            that are ready to be evaluated.
        """

        out = {}
        for name, expression in config.items():
            if not isinstance(expression, (int, float, str)):
                msg = ('Cannot parse NrwalConfig expression for "{}", must be '
                       'one of (int, float, str) but received type "{}": {}'
                       .format(name, type(expression), expression))
                logger.error(msg)
                raise TypeError(msg)

            out[name] = cls._parse_expression(expression, config, eqn_dir,
                                              gvars)
        return out

    @classmethod
    def _parse_expression(cls, expression, config, eqn_dir, gvars):
        """Parse a config expression that can be a number, an EquationDirectory
        retrieval string, a key referencing a config entry, or a mathematical
        expression combining these options.

        Parameters
        ----------
        expression : str
            A string entry in the config, can be a number, an EquationDirectory
            retrieval string, a key referencing a config entry, or a
            mathematical expression combining these options.
        config : dict
            NRWAL config dictionary mapping names (str) to expressions (str)
        eqn_dir : EquationDirectory
            EquationDirectory object holding Equation objects available to
            this config.
        gvars : dict
            Dictionary of global variables (constant numerical values)
            available within this config object.

        Returns
        -------
        out : int | float | Equation
            A numeric value if expression is a number, or a NRWAL Equation
            object representing the input expression and containing the global
            variables input. This Equation is ready to be evaluated.
        """

        if Equation.is_num(expression):
            out = float(expression)

        elif expression in config:
            out = cls._parse_expression(config[expression], config,
                                        eqn_dir, gvars)

        elif Equation.is_equation(expression):
            out = cls._parse_equation(expression, config, eqn_dir, gvars)

        elif '::' in expression and expression.split('::')[0] in config:
            config_key, _, sub_key = expression.partition('::')
            temp = cls._parse_expression(config_key, config, eqn_dir, gvars)
            out = temp[sub_key]

        else:
            try:
                out = eqn_dir[expression]
            except KeyError as e:
                msg = ('Could not parse unknown expression "{}". Must be an '
                       'equation key in the EquationDirectory or a locally '
                       'defined variable.'.format(expression))
                logger.error(msg)
                raise ValueError(msg) from e

        if isinstance(out, (Equation, EquationGroup)):
            out.set_default_variables(gvars)
        elif isinstance(out, EquationDirectory):
            out.set_default_variables(gvars, force_update=True)

        return out

    @classmethod
    def _parse_equation(cls, expression, config, eqn_dir, gvars):
        """Special parsing logic for expressions that are equations
        (contain operators).

        Parameters
        ----------
        expression : str
            A string entry in the config containing operators.
        config : dict
            NRWAL config dictionary mapping names (str) to expressions (str)
        eqn_dir : EquationDirectory
            EquationDirectory object holding Equation objects available to
            this config.
        gvars : dict
            Dictionary of global variables (constant numerical values)
            available within this config object.

        Returns
        -------
        out : Equation
            NRWAL Equation object representing the input equation
        """

        assert Equation.is_equation(expression)

        # order of operator map enforces order of operations
        op_map = OrderedDict()
        op_map['+'] = operator.add
        op_map['-'] = operator.sub
        op_map['*'] = operator.mul
        op_map['/'] = operator.truediv
        op_map['^'] = operator.pow
        expression = expression.replace('**', '^')
        for op_str, op_fun in op_map.items():
            if op_str in expression:
                split = expression.partition(op_str)
                v0, v1 = split[0].strip(), split[2].strip()
                out = op_fun(cls._parse_expression(v0, config, eqn_dir, gvars),
                             cls._parse_expression(v1, config, eqn_dir, gvars))

        return out

    def __getitem__(self, key):
        """Retrieve data from the NrwalConfig, prioritizing outputs, then
        expressions from the input config.

        Parameters
        ----------
        key : str
            Requested key from the NrwalConfig.

        Returns
        -------
        out : int | float | np.ndarray | Equation
            Requested data prioritized from the outputs then the config.
        """
        if key in self._outputs:
            return self._outputs[key]
        else:
            return self._config[key]

    def __str__(self):
        s = ['NrwalConfig object with equation directory: "{}"'
             .format(os.path.join(self._eqn_dir._dir_name,
                                  self._eqn_dir._base_name))]
        for name, expression in self.items():
            s.append(str(name))
            lines = str(expression).split('\n')
            s += ['\t' + line for line in lines]

        return '\n'.join(s)

    def __repr__(self):
        return str(self)

    @property
    def inputs(self):
        """Get the inputs dictionary.

        Returns
        -------
        dict
        """
        return self._inputs

    @inputs.setter
    def inputs(self, arg):
        """Set the inputs dictionary or update it if inputs are already present

        Parameters
        ----------
        arg : dict | pd.DataFrame | None
            Namespace of input data to make available for the evaluation of
            the NrwalConfig. If inputs have been previously defined, they
            will be updated with data from this arg. None will clear all
            previously defined inputs.
        """

        if arg is None:
            self._inputs = {}
        elif isinstance(arg, dict):
            self._inputs.update(arg)
        elif isinstance(arg, pd.DataFrame):
            self._inputs.update({k: arg[k].values.flatten()
                                 for k in arg.columns.values})
        else:
            msg = ('Cannot set inputs as datatype "{}". '
                   'Requires a dict or DataFrame.'.format(type(arg)))
            logger.error(msg)
            raise TypeError(msg)

        Equation._check_input_args(self._inputs)

    @property
    def outputs(self):
        """Get the outputs dictionary.

        Returns
        -------
        dict
        """
        return self._outputs

    @property
    def global_variables(self):
        """Get a dictionary of global variables (constant numerical values)
        available within this config object.

        Returns
        -------
        dict
        """
        return self._global_variables

    @property
    def all_variables(self):
        """Get a sorted list of unique names of the input variables for all
        equations in this config. This will include global variables defined
        in this config and default variables defined in the equation
        directories.

        Returns
        -------
        list
        """

        names = list(self.global_variables.keys())
        for eqn in self.values():
            if isinstance(eqn, Equation):
                names += eqn.variables

        return sorted(list(set(names)))

    @property
    def required_inputs(self):
        """Get a list of unique variable names required in the input namespace.
        This considers variables set in the config or in variables.yaml files
        to not be required, although these can still be overwritten in the
        config "inputs" attribute.

        Returns
        -------
        list
        """

        names = []
        for eqn in self.values():
            if isinstance(eqn, Equation):
                names += [v for v in eqn.variables
                          if v not in self.global_variables
                          and v not in eqn.default_variables]

        return sorted(list(set(names)))

    @property
    def missing_inputs(self):
        """Get a list of unique variables names that are required to evaluate
        the equations in the config but are still missing from the inputs.

        Returns
        -------
        list
        """
        names = [x for x in self.required_inputs
                 if x not in self.global_variables
                 and x not in self.inputs]
        return sorted(list(set(names)))

    @property
    def solvable(self):
        """Are all required inputs defined?

        Returns
        -------
        bool
        """
        return not any(self.missing_inputs)

    def get(self, key, default_value):
        """Attempt to get a key from the NrwalConfig, return
        default_value if the key could not be retrieved"""
        try:
            return self[key]
        except KeyError:
            return default_value

    def keys(self):
        """Get the 1st level of config keys, same as dict.keys()"""
        return self._config.keys()

    def items(self):
        """Get the 1st level of config (keys, values), same as dict.items().
        """
        return self._config.items()

    def values(self):
        """Get the 1st level of config values, same as dict.values()"""
        return self._config.values()

    def eval(self, inputs=None):
        """Alias for evaluate()."""
        return self.evaluate(inputs=inputs)

    def evaluate(self, inputs=None):
        """Evaluate the equations in the NrwalConfig, set the output to the
        outputs attribute, and return the output.

        Parameters
        ----------
        inputs : dict | pd.DataFrame | None
            Optional namespace of input data to make available for the
            evaluation of the NrwalConfig. This will update any previously
            set inputs.

        Returns
        -------
        outputs : dict
            Dictionary of outputs with the same keys as the input config but
            with int, float, or np.ndarray outputs as values.
        """

        if inputs is not None:
            self.inputs = inputs

        if not self.solvable:
            msg = ('Cannot evaluate NrwalConfig, missing the following '
                   'input args: {}'.format(self.missing_inputs))
            logger.error(msg)
            raise RuntimeError(msg)

        for k, v in self.items():
            if (isinstance(v, (EquationGroup, EquationDirectory))
                    or Equation.is_num(v)):
                pass
            elif isinstance(v, Equation):
                self._outputs[k] = v.evaluate(**self.inputs)
            else:
                msg = ('Cannot evaluate "{}" with unexpected type: {}'
                       .format(k, type(v)))
                logger.error(msg)
                raise TypeError(msg)

        return self._outputs
