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
    """Config framework for NRWAL"""

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
                    out = op_fun(
                        cls._parse_expression(v0, config, eqn_dir, gvars),
                        cls._parse_expression(v1, config, eqn_dir, gvars))

        elif '::' in expression and expression.split('::')[0] in config:
            config_key, _, sub_key = expression.partition('::')
            temp = cls._parse_expression(config_key, config, eqn_dir, gvars)
            out = temp[sub_key]

        else:
            out = eqn_dir[expression]

        if isinstance(out, (Equation, EquationGroup)):
            out.set_default_variables(gvars)
        elif isinstance(out, EquationDirectory):
            out.set_default_variables(gvars, force_update=True)

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

    def __getattr__(self, attr):
        """Retrieve data from the NrwalConfig, prioritizing outputs, then
        expressions from the input config, then from the object itself.

        Parameters
        ----------
        attr : str
            Requested attribute from the NrwalConfig.

        Returns
        -------
        out : int | float | np.ndarray | Equation
            Requested data prioritized from the outputs, then the config,
            then from the object itself.
        """
        if attr in self._outputs:
            return self._outputs[attr]
        elif attr in self._config:
            return self._config[attr]
        else:
            try:
                return super().__getattr__(attr)  # pylint: disable-msg=E1101
            except AttributeError as e:
                msg = ('Could not get attribute "{}" from NrwalConfig.'
                       .format(attr))
                logger.error(msg)
                raise AttributeError(msg) from e

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
