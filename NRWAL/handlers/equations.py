# -*- coding: utf-8 -*-
"""
Handler objects to interface with single NRWAL equation strings.
"""
import copy
import re
import numpy as np
import logging


logger = logging.getLogger(__name__)


class Equation:
    """Class to handle and evaluate a single wind cost equation string."""

    # illegal substrings that cannot be in cost equations
    ILLEGAL = ('import ', 'os.', 'sys.', '.__', '__.', 'eval', 'exec')

    def __init__(self, eqn, name=None, global_variables=None):
        """
        Parameters
        ----------
        eqn : str | int | float
            Cost equation in a string representation or a single number e.g.:
            "-34.80 * depth ** 2 + 207619.80 * depth + 221197699.89"
        name : str | None
            Optional equation name / key for string formatting
        global_variables : dict
            Optional dictionary of variables accessible to this Equation
            object. These inputs can still be overwritten at runtime.
        """

        self._global_variables = global_variables
        if self._global_variables is None:
            self._global_variables = {}

        self._str = None
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

    def __eqn_math(self, other, operator):
        """Perform arithmetic with this instance of Equation (self) and an
        input "other" Equation and return a new Equation object that evaluates
        the arithmetic operation of the two equations

        Parameters
        ----------
        other : Equation | str | int | float
            Another Equation object or simple string representation of an
            equation
        operator : str
            An arithmetic operator in a python string such as: + - / * ** %

        Returns
        -------
        out : Equation
            A new Equation instance with this instance of Equation (self)
            operated on by the input Equation.
        """

        cls = self.__class__
        if not isinstance(other, Equation):
            other = cls(other)

        new_eqn = '({}) {} ({})'.format(self._eqn, operator, other._eqn)
        new_str = '({} {} {})'.format(self, operator, other)
        gvars = copy.deepcopy(self._global_variables)
        gvars.update(other._global_variables)
        out = cls(new_eqn, global_variables=gvars)
        out._str = new_str
        return out

    def __add__(self, other):
        """Add another equation to this instance of Equation (self) and return
        a new Equation object that evaluates the sum of the two equations

        Parameters
        ----------
        other : Equation | str | int | float
            Another Equation object or simple string representation of an
            equation to add to this instance of Equation (self).

        Returns
        -------
        out : Equation
            A new Equation instance with this instance of Equation (self)
            summed with the input Equation.
        """
        return self.__eqn_math(other, '+')

    def __sub__(self, other):
        """Subtract another equation from this instance of Equation (self) and
        return a new Equation object that evaluates the difference of the two
        equations

        Parameters
        ----------
        other : Equation | str | int | float
            Another Equation object or simple string representation of an
            equation to subtract from this instance of Equation (self).

        Returns
        -------
        out : Equation
            A new Equation instance with this instance of Equation (self)
            subtracted by the input Equation.
        """
        return self.__eqn_math(other, '-')

    def __mul__(self, other):
        """Multiply another equation by this instance of Equation (self) and
        return a new Equation object that evaluates the product of the two
        equations

        Parameters
        ----------
        other : Equation | str | int | float
            Another Equation object or simple string representation of an
            equation to multiply by this instance of Equation (self).

        Returns
        -------
        out : Equation
            A new Equation instance with this instance of Equation (self)
            multiplied by the input Equation.
        """
        return self.__eqn_math(other, '*')

    def __pow__(self, other):
        """Raise this instance of Equation (self) by the output of another
        equation and return a new Equation object that evaluates this power
        function

        Parameters
        ----------
        other : Equation | str | int | float
            Another Equation object or simple string representation of an
            equation to raise this instance of Equation (self) to the power of.

        Returns
        -------
        out : Equation
            A new Equation instance with this instance of Equation (self)
            raise to the power of the output of the input Equation.
        """
        return self.__eqn_math(other, '**')

    def __div__(self, other):
        """Divide this instance of Equation (self) by another Equation and
        return a new Equation object that evaluates the division of the two
        equations.

        Parameters
        ----------
        other : Equation | str | int | float
            Another Equation object or simple string representation of an
            equation to divide this instance of Equation (self) by.

        Returns
        -------
        out : Equation
            A new Equation instance with this instance of Equation (self)
            divided by the input Equation.
        """
        return self.__eqn_math(other, '/')

    def __truediv__(self, other):
        """Divide this instance of Equation (self) by another Equation and
        return a new Equation object that evaluates the division of the two
        equations.

        Parameters
        ----------
        other : Equation | str | int | float
            Another Equation object or simple string representation of an
            equation to divide this instance of Equation (self) by.

        Returns
        -------
        out : Equation
            A new Equation instance with this instance of Equation (self)
            divided by the input Equation.
        """
        return self.__eqn_math(other, '/')

    def __repr__(self):
        return str(self)

    def __str__(self):
        if self._str is None:
            if self.is_num(self._eqn) and not any(self.vars):
                self._str = str(self._eqn)

            else:
                vars_str = [v for v in self.vars
                            if v not in self.global_variables]
                vars_str = str(vars_str).replace('[', '').replace(']', '')\
                    .replace("'", '').replace('"', '')

                gvars_str = [v for v in self.vars
                             if v in self.global_variables]
                for gvar in gvars_str:
                    base_str = ', ' if bool(vars_str) else ''
                    kw_str = '{}={}'.format(gvar, self.global_variables[gvar])
                    vars_str += base_str + kw_str

                if self._base_name is None:
                    self._str = 'Equation({})'.format(vars_str)
                else:
                    self._str = '{}({})'.format(self._base_name, vars_str)

        return self._str

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
        var_names = sorted(list(set(var_names)))
        return var_names

    def eval(self, **kwargs):
        """Abbreviated alias for evaluate()."""
        return self.evaluate(**kwargs)

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