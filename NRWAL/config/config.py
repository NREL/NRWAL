# -*- coding: utf-8 -*-
"""
NRWAL config framework.
"""
import logging
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

    def __init__(self, config, interp_extrap=False, use_nearest=False):
        """
        Parameters
        ----------
        config : dict | str
            NRWAL config input. Can be a string filepath to a json or yml file
            or an extracted dictionary.
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

        config, eqn_dir = self._load_config(config)
        self._eqn_dir = EquationDirectory(eqn_dir, interp_extrap=interp_extrap,
                                          use_nearest=use_nearest)
        self._global_variables = self._parse_global_variables(config)
        self._config = self._parse_config(config, self._eqn_dir,
                                          self._global_variables)

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
            out._set_variables(gvars)
        elif isinstance(out, EquationDirectory):
            out._set_variables(gvars, force_update=True)

        return out

    def __getitem__(self, key):
        """Retrieve an expression from the config.

        Parameters
        ----------
        key : str

        Returns
        -------
        out : int | float | Equation
            A numeric value if the config expression corresponding to the
            requested key is a number, or a NRWAL Equation object representing
            the expression corresponding to the requested key that is ready
            to be evaluated.
        """
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
    def global_variables(self):
        """Get a dictionary of global variables (constant numerical values)
        available within this config object.

        Returns
        -------
        dict
        """
        return self._global_variables

    @property
    def variables(self):
        """Get a unique sorted list of names of the input variables for all
        equations in this config. This will include global variables available
        within and defined in this config.

        Returns
        -------
        list
        """

        names = list(self.global_variables.keys())
        for eqn in self.values():
            if isinstance(eqn, Equation):
                names += eqn.variables

        return sorted(list(set(names)))

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
