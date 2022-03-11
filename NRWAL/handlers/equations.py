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

    def __init__(self, eqn, name=None, default_variables=None):
        """
        Parameters
        ----------
        eqn : str | int | float
            Cost equation in a string representation or a single number e.g.:
            "-34.80 * depth ** 2 + 207619.80 * depth + 221197699.89"
        name : str | None
            Optional equation name / key for string formatting
        default_variables : dict
            Optional dictionary of default variables accessible to this
            Equation object. These inputs can still be overwritten at runtime.
        """

        self._default_variables = default_variables
        if self._default_variables is None:
            self._default_variables = {}

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

        self.verify_no_self_reference()

    def verify_no_self_reference(self):
        """Verify that the equation does not reference itself.

        Raises
        ------
        ValueError
            If a reference to the equation name is found in its variables.
        """
        if self._base_name in self.variables:
            msg = ("Self-referencing is not allowed! Please change "
                   "either the equation name or the name of the dependent "
                   "variable in the following input equation: {} = {}"
                   .format(self._base_name, self._eqn))
            logger.error(msg)
            raise ValueError(msg)

    @staticmethod
    def _check_input_args(kwargs):
        """Check that input args to equation are of expected types."""
        assert isinstance(kwargs, dict), 'Equation inputs must be a dict!'
        for k, v in kwargs.items():
            msg = 'Input keys must be strings but received: {}'.format(k)
            assert isinstance(k, str), msg
            msg = ('Input data must be one of (int, float, np.ndarray, list, '
                   'tuple), but received: {}'.format(type(v)))
            is_num = (isinstance(v, (int, float, np.ndarray, list, tuple))
                      | np.issubdtype(type(v), np.number))
            assert is_num, msg

            if isinstance(v, np.ndarray):
                if np.issubdtype(v.dtype, np.integer):
                    kwargs[k] = v.astype(np.float32)
            elif isinstance(v, int):
                kwargs[k] = float(v)

        return kwargs

    def replace_equation(self, new_eqn):
        """Replace the expression of this equation with a new one.

        This method returns a new `Equation` instance that replaces
        the existing equation expression with the new one supplied by the
        user, keeping the equation name and default variables unchanged.

        Parameters
        ----------
        new_eqn : str
            String representation of the new `Equation` instance.

        Returns
        -------
        `Equation`
            A new `Equation` instance with the same name and
            default values as the old `Equation` but with the new
            equation expression.
        """

        return self.__class__(
            new_eqn, name=self._base_name,
            default_variables=self.default_variables
        )

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

        arg1 = self._eqn
        arg2 = other._eqn
        if not self.is_num(arg1) and not self.is_variable(arg1):
            arg1 = '({})'.format(arg1)
        if not self.is_num(arg2) and not self.is_variable(arg2):
            arg2 = '({})'.format(arg2)

        new_eqn = '{} {} {}'.format(arg1, operator, arg2)
        new_str = '({} {} {})'.format(self, operator, other)
        def_vars = copy.deepcopy(self._default_variables)
        def_vars.update(other._default_variables)
        out = cls(new_eqn, default_variables=def_vars)
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
            if self.is_num(self._eqn) and not any(self.variables):
                self._str = str(self._eqn)

            else:
                vars_str = [v for v in self.variables
                            if v not in self.default_variables]
                vars_str = str(vars_str).replace('[', '').replace(']', '')\
                    .replace("'", '').replace('"', '')

                gvars_str = [v for v in self.variables
                             if v in self.default_variables]
                for gvar in gvars_str:
                    base_str = ', ' if bool(vars_str) else ''
                    kw_str = '{}={}'.format(gvar, self.default_variables[gvar])
                    vars_str += base_str + kw_str

                if self._base_name is None:
                    self._str = 'Equation({})'.format(vars_str)
                else:
                    self._str = '{}({})'.format(self._base_name, vars_str)

        return self._str

    def __contains__(self, arg):
        return arg in self._eqn

    def set_default_variables(self, var_dict):
        """Set default variables available to this Equation object.

        Parameters
        ----------
        var_dict : dict | None
            Default variables namespace. These variables can always be
            overwritten when Equation.evaluate() is called.
        """
        if var_dict is not None:
            self._default_variables.update(copy.deepcopy(var_dict))

    @staticmethod
    def _merge_vars(var_group, kwargs):
        """Create a copied namespace of input args for the Equation evaluation.
        This is the default-style variables set with the self._set_variables()
        method and the self._default_variables attribute updated with kwargs
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
            float(str(s))
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def is_method(s):
        """Check if a string is a numpy/pandas or python builtin method"""
        return bool(s.startswith(('np.', 'pd.')) or s in dir(__builtins__))

    @classmethod
    def is_variable(cls, s):
        """Check if a string is a variable name without any constants,
        operators, or arithmetic expressions"""
        flags = ('(', ')', '[', ']', '{', '}', '+', '-', '/', '*', '^', ' ',
                 '<', '>', '=', '\\', '|', '&', '$', '@', '-')
        if cls.is_num(s):
            return False
        elif any(f in s for f in flags):
            return False
        else:
            return True

    @property
    def full(self):
        """Get the full equation string without any pretty formatting."""
        return self._eqn

    @property
    def default_variables(self):
        """Get a dictionary of default variables from a variables.yaml file
        accessible to this object

        Returns
        -------
        dict
        """
        return self._default_variables

    @classmethod
    def parse_variables(cls, expression):
        """Parse variable names from an expression string."""

        # finds and replaces all scientific notation numbers
        re_num = re.compile(r'[0-9]+\.?[0-9]*[eE][-+]?[0-9]*')
        nums = re.findall(re_num, str(expression))
        for num in nums:
            expression = expression.replace(num, '-1')

        delimiters = ('*', '/', '+', '-', ' ', '(', ')', '[', ']', '>', '<')
        regex_pattern = '|'.join(map(re.escape, delimiters))
        variables = [sub.strip(',')
                     for sub in re.split(regex_pattern, str(expression))
                     if sub.strip(',')
                     and cls.is_variable(sub)
                     and not cls.is_num(sub.strip(','))
                     and not cls.is_method(sub)]
        variables = sorted(list(set(variables)))
        return variables

    @property
    def variables(self):
        """Get a unique sorted list names of all input variables that the
        Equation needs. This will return an empty list if the equation has
        no variables.

        Returns
        -------
        list
        """
        return self.parse_variables(self._eqn)

    @classmethod
    def is_equation(cls, expression):
        """Check if an expression is an equation to be handled by this
        framework.

        Parameters
        ----------
        expression : str | int | float
            Expression to be checked as an equation or not.

        Returns
        -------
        check : bool
            True if the expression is an equation that can be handled by this
            framework.
        """
        check = False
        operators = ('*', '/', '+', '-', '^')

        if not isinstance(expression, (str, int, float)):
            check = False
        elif cls.is_num(expression):
            check = True
        elif any(x in str(expression) for x in operators):
            check = True

        return check

    def eval(self, **kwargs):
        """Alias for evaluate()."""
        return self.evaluate(**kwargs)

    def evaluate(self, **kwargs):
        """Evaluate the equation string and return the result

        Parameters
        ----------
        kwargs : dict
            Keyword arguments setting variables of the equation. Note that this
            is **kwargs so this method can be run in either of these syntaxes:
                Equation.evaluate(input1=10, input2=20)
                Equation.evaluate(**{'input1': 10, 'input2': 20})

        Returns
        -------
        out : float | np.ndarray
            Evaluated output of this equation object.
        """
        kwargs = self._check_input_args(kwargs)
        kwargs = self._merge_vars(self._default_variables, kwargs)

        missing = [v for v in self.variables
                   if v not in globals()
                   and v not in kwargs]
        if any(missing):
            msg = ('Cannot evaluate "{}", missing the following input args: {}'
                   .format(self, missing))
            logger.error(msg)
            raise RuntimeError(msg)

        try:
            out = eval(str(self._eqn), globals(), kwargs)
        except Exception as e:
            msg = ('Could not evaluate NRWAL Equation {}, received error: {}'
                   .format(self, e))
            logger.exception(msg)
            raise RuntimeError(msg) from e

        return out
