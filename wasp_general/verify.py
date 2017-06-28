# -*- coding: utf-8 -*-
# wasp_general/verfy.py
#
# Copyright (C) 2016 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# Wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import sys
import os
from inspect import getfullargspec, isclass, isfunction, getsource
from decorator import decorator


class Verifier:
	""" Base class for verifier implementation.

	Verifiers are classes, that generates decorators (which are later used for runtime function arguments
	checking). Derived classes (such as :class:`.TypeVerifier`, :class:`SubclassVerifier` and
	:class:`ValueVerifier`) check arguments for type and/or value validity. But each derived class uses
	its own syntax for check declaration (see :meth:`.Verifier.check`).

	Same checks can be grouped into one sentence if they are used for different arguments. Each statement can
	be marked by tag or tags for runtime disabling. If statement doesn't have tag then it always run checks.

	Checks can be simple (implemented by lambda-statements) or complex
	(implemented by standalone functions or classes). Because target function is decorated for checking it is
	possible to run checks sequentially.

	Example: ::

		@verify_type(a=int, b=str, d=(int, None), e=float)
		@verify_subclass(c=A, args=B)
		@verify_value(a=(lambda x: x > 5, lambda x: x < 10), args=lambda x: x > 0)
		@verify_value(c=lambda x: x.a == 'foo', d=lambda x: x is None or x < 0)
		def foo(a, b, c, d=None, *args, **kwargs):
			pass
	"""

	__default_environment_var__ = 'WASP_VERIFIER_DISABLE_CHECKS'
	""" Default environment variable name that is used for check bypassing. Variable must contain tags separated by \
	:attr:`.Verifier.__tags_delimiter__`. To bypass certain check all of its tags must be defined in variable.

	Currently used values:
		'paranoid' - for excess checks, like that test parameters, that doesn't processed by the specific
		function or is passing them to other function that has checks
	"""

	__tags_delimiter__ = ':'
	""" String that is used for tag separation :attr:`.Verifier.__default_environment_var__`"""

	def __init__(self, *tags, env_var=None, silent_checks=False):
		"""Construct a new :class:`.Verifier`

		:param tags: Tags to mark this checks. Now only strings are suitable.
		:param env_var: Environment variable name that is used for check bypassing. If is None, then default  \
		value is used :attr:`.Verifier.__default_environment_var__`
		:param silent_checks: If it is not True, then debug information will be printed to stderr.
		"""
		self._tags = list(tags)
		self._env_var = env_var if env_var is not None else self.__class__.__default_environment_var__
		self._silent_checks = silent_checks

	def decorate_disabled(self):
		""" Return True if this decoration must be omitted, otherwise - False.
		This class searches for tags values in environment variable
		(:attr:`.Verifier.__default_environment_var__`), Derived class can implement any logic

		:return: bool
		"""
		if self._env_var not in os.environ or len(self._tags) == 0:
			return False
		env = os.environ[self._env_var].split(self.__class__.__tags_delimiter__)
		for tag in self._tags:
			if tag not in env:
				return False
		return True

	def check(self, arg_spec, arg_name, decorated_function):
		"""Return callable object that takes single value - future argument. This callable must raise
		an exception if error occurs. It is recommended to return None if everything is OK

		:param arg_spec: specification that is used to describe check like types, lambda-functions, \
		list of types just anything (see :meth:`.Verifier.decorator`)
		:param arg_name: parameter name from decorated function
		:param decorated_function: target function (function to decorate)

		:return: None
		"""
		return lambda x: None

	def _args_checks_gen(self, decorated_function, function_spec, arg_specs):
		""" Generate checks for positional argument testing

		:param decorated_function: function decorator
		:param function_spec: function inspect information
		:param arg_specs: argument specification (same as arg_specs in :meth:`.Verifier.decorate`)

		:return: internal structure, that is used by :meth:`.Verifier._args_checks_test`
		"""
		inspected_args = function_spec.args
		args_check = {}

		for i in range(len(inspected_args)):
			arg_name = inspected_args[i]

			if arg_name in arg_specs.keys():
				args_check[arg_name] = self.check(arg_specs[arg_name], arg_name, decorated_function)
		return args_check

	def _args_checks_test(self, original_function, function_spec, checks, args, arg_specs):
		""" Test positional arguments by a generated checks

		:param original_function: original function, that was decorated
		:param function_spec: function inspect information
		:param checks: tests, that was generated by the :meth:`.Verifier._args_checks_gen`
		:param args: positional arguments to check (with varargs)
		:param arg_specs: argument specification (same as arg_specs in :meth:`.Verifier.decorate`)

		:return: None
		"""
		inspected_args = function_spec.args

		for i in range(len(inspected_args)):
			param_name = inspected_args[i]
			if param_name in checks:
				try:
					checks[param_name](args[i])
				except Exception as e:
					self.help_info(e, original_function, param_name, arg_specs[param_name])
					raise

	def _varargs_checks_gen(self, decorated_function, function_spec, arg_specs):
		""" Generate checks for positional variable argument (varargs) testing

		:param decorated_function: function decorator
		:param function_spec: function inspect information
		:param arg_specs: argument specification (same as arg_specs in :meth:`.Verifier.decorate`)

		:return: internal structure, that is used by :meth:`.Verifier._varargs_checks_test`
		"""
		inspected_varargs = function_spec.varargs

		if inspected_varargs is not None and inspected_varargs in arg_specs.keys():
			return self.check(
				arg_specs[inspected_varargs], inspected_varargs, decorated_function
			)

	def _varargs_checks_test(self, original_function, function_spec, check, args, arg_specs):
		""" Test varargs by a generated check

		:param original_function: original function, that was decorated
		:param function_spec: function inspect information
		:param check: test, that was generated by the :meth:`.Verifier._varargs_checks_gen`
		:param args: positional arguments to check (all of them)
		:param arg_specs: argument specification (same as arg_specs in :meth:`.Verifier.decorate`)

		:return: None
		"""
		inspected_args = function_spec.args
		inspected_varargs = function_spec.varargs

		if inspected_varargs is not None and check is not None:
			for i in range(len(inspected_args), len(args)):
				try:
					check(args[i])
				except Exception as e:
					self.help_info(e, original_function, inspected_varargs, arg_specs[inspected_varargs])
					raise

	def _kwargs_checks_gen(self, decorated_function, function_spec, arg_specs):
		""" Generate checks for keyword argument testing

		:param decorated_function: function decorator
		:param function_spec: function inspect information
		:param arg_specs: argument specification (same as arg_specs in :meth:`.Verifier.decorate`)

		:return: internal structure, that is used by :meth:`.Verifier._kwargs_checks_test`
		"""
		args_names = []
		args_names.extend(function_spec.args)
		if function_spec.varargs is not None:
			args_names.append(function_spec.args)

		args_check = {}

		for arg_name in arg_specs.keys():
			if arg_name not in args_names:
				args_check[arg_name] = self.check(
					arg_specs[arg_name], arg_name, decorated_function
				)
		return args_check

	def _kwargs_checks_test(self, original_function, checks, kwargs, arg_specs):
		""" Test keyword arguments by a generated checks

		:param original_function: original function, that was decorated
		:param checks: tests, that was generated by the :meth:`.Verifier._kwargs_checks_gen`
		:param kwargs: keyword arguments to check
		:param arg_specs: argument specification (same as arg_specs in :meth:`.Verifier.decorate`)

		:return: None
		"""

		for kw_key, kw_value in kwargs.items():
			if kw_key in checks.keys():
				try:
					checks[kw_key](kw_value)
				except Exception as e:
					print('!!!!!!!!!!!')
					print(str(arg_specs))
					print('!!!!!!!!!!!')
					self.help_info(e, original_function, kw_key, arg_specs[kw_key])
					raise

	def decorator(self, **arg_specs):
		""" Return decorator that can decorate target function

		:param arg_specs: dictionary where keys are parameters name and values are theirs specification.\
		Specific specification is passed as is to :meth:`Verifier.check` method with corresponding \
		parameter name.

		:return: function
		"""

		if self.decorate_disabled() is True:
			def empty_decorator(decorated_function):
				return decorated_function
			return empty_decorator

		def first_level_decorator(decorated_function):

			function_spec = getfullargspec(decorated_function)
			args_checks = self._args_checks_gen(decorated_function, function_spec, arg_specs)
			varargs_check = self._varargs_checks_gen(decorated_function, function_spec, arg_specs)
			kwargs_checks = self._kwargs_checks_gen(decorated_function, function_spec, arg_specs)

			def second_level_decorator(original_function, *args, **kwargs):
				self._args_checks_test(original_function, function_spec, args_checks, args, arg_specs)
				self._varargs_checks_test(original_function, function_spec, varargs_check, args, arg_specs)
				self._kwargs_checks_test(original_function, kwargs_checks, kwargs, arg_specs)

				return original_function(*args, **kwargs)
			return decorator(second_level_decorator)(decorated_function)
		return first_level_decorator

	def help_info(self, exc, decorated_function, arg_name, arg_spec):
		""" Print debug information to stderr. (Do nothing if object was constructed with silent_checks=True)

		:param exc: raised exception
		:param decorated_function: target function (function to decorate)
		:param arg_name: function parameter name
		:param arg_spec: function parameter specification

		:return: None
		"""
		if self._silent_checks is not True:
			print('Exception raised:', file=sys.stderr)
			print(str(exc), file=sys.stderr)
			fn_name = Verifier.function_name(decorated_function)
			print('Decorated function: %s' % fn_name, file=sys.stderr)
			if decorated_function.__doc__ is not None:
				print('Decorated function docstrings:', file=sys.stderr)
				print(decorated_function.__doc__, file=sys.stderr)
			print('Argument "%s" specification:' % arg_name, file=sys.stderr)
			if isfunction(arg_spec):
				print(getsource(arg_spec), file=sys.stderr)
			else:
				print(str(arg_spec), file=sys.stderr)
			print('', file=sys.stderr)

	@staticmethod
	def function_name(fn):
		""" Return function name in pretty style

		:param fn: source function
		:return: str
		"""
		fn_name = fn.__name__
		if hasattr(fn, '__qualname__'):
			return fn.__qualname__
		elif hasattr(fn, '__self__'):
			owner = fn.__self__
			if isclass(owner) is False:
				owner = owner.__class__
			return '%s.%s' % (owner.__name__, fn_name)
		return fn_name


class TypeVerifier(Verifier):
	""" Verifier that is used for type verification. Checks parameter if it is instance of specified class or
	classes. Specification accepts type or list/tuple/set of types

	Example: ::

		@verify_type(a=int, b=str, d=(int, None), e=float)
		def foo(a, b, c, d=None, **kwargs):
			pass
	"""

	def check(self, type_spec, arg_name, decorated_function):
		""" Return callable that checks function parameter for type validity. Checks parameter if it is
		instance of specified class or classes

		:param type_spec: type or list/tuple/set of types
		:param arg_name: function parameter name
		:param decorated_function: target function
		:return: function
		"""

		def raise_exception(text_spec):
			exc_text = 'Argument "%s" for function "%s" has invalid type' % (
				arg_name, Verifier.function_name(decorated_function)
			)
			exc_text += ' (%s)' % text_spec
			raise TypeError(exc_text)

		if isinstance(type_spec, (tuple, list, set)):
			for single_type in type_spec:
				if (single_type is not None) and isclass(single_type) is False:
					raise RuntimeError(
						'Invalid specification. Must be type or tuple/list/set of types'
					)
			if None in type_spec:
				type_spec = tuple(filter(lambda x: x is not None, type_spec))
				return lambda x: None if x is None or isinstance(x, tuple(type_spec)) is True else \
					raise_exception(str((type(x))))
			else:
				return lambda x: None if isinstance(x, tuple(type_spec)) is True else \
					raise_exception(str((type(x))))
		elif isclass(type_spec):
			return lambda x: None if isinstance(x, type_spec) is True else \
				raise_exception(str((type(x))))
		else:
			raise RuntimeError('Invalid specification. Must be type or tuple/list/set of types')


class SubclassVerifier(Verifier):
	""" Verifier that is used for type verification. Checks parameter if it is class or subclass of
	specified class or classes. Specification accepts type or list/tuple/set of types

	Example: ::

		@verify_subclass(c=A, e=(A, D))
		def foo(a, b, c, d=None, **kwargs):
			pass
	"""

	def check(self, type_spec, arg_name, decorated_function):
		""" Return callable that checks function parameter for class validity. Checks parameter if it is
		class or subclass of specified class or classes

		:param type_spec: type or list/tuple/set of types
		:param arg_name: function parameter name
		:param decorated_function: target function
		:return: function
		"""

		def raise_exception(text_spec):
			exc_text = 'Argument "%s" for function "%s" has invalid type' % (
				arg_name, Verifier.function_name(decorated_function)
			)
			exc_text += ' (%s)' % text_spec
			raise TypeError(exc_text)

		if isinstance(type_spec, (tuple, list, set)):
			for single_type in type_spec:
				if (single_type is not None) and isclass(single_type) is False:
					raise RuntimeError(
						'Invalid specification. Must be type or tuple/list/set of types'
					)
			if None in type_spec:
				type_spec = tuple(filter(lambda x: x is not None, type_spec))
				return lambda x: None if \
					x is None or (isclass(x) is True and issubclass(x, type_spec) is True) else \
					raise_exception(str(x))
			else:
				return lambda x: None if (isclass(x) is True and issubclass(x, type_spec) is True) else \
					raise_exception(str(x))
		elif isclass(type_spec):
			return lambda x: None if (isclass(x) is True and issubclass(x, type_spec) is True) else \
				raise_exception(str(x))
		else:
			raise RuntimeError('Invalid specification. Must be type or tuple/list/set of types')


class ValueVerifier(Verifier):
	""" Verifier that is used for value verification. Checks parameter if its value passes specified restrictions.
	Specification accepts function or list/tuple/set of functions. Each function must accept one parameter and
	must return True or False if it passed restrictions or not.

	Example: ::

		@verify_value(a=(lambda x: x > 5, lambda x: x < 10))
		@verify_value(c=lambda x: x.a == 'foo', d=lambda x: x is None or x < 0)
		def foo(a, b, c, d=None, **kwargs):
		pass
	"""

	def check(self, value_spec, arg_name, decorated_function):
		""" Return callable that checks function parameter for value validity. Checks parameter if its value
		passes specified restrictions.

		:param value_spec: function or list/tuple/set of functions. Each function must accept one parameter and \
		must return True or False if it passed restrictions or not.
		:param arg_name: function parameter name
		:param decorated_function: target function
		:return: function
		"""

		def raise_exception(text_spec):
			exc_text = 'Argument "%s" for function "%s" has invalid value' % (
				arg_name, Verifier.function_name(decorated_function)
			)
			exc_text += ' (%s)' % text_spec
			raise ValueError(exc_text)

		if isinstance(value_spec, (tuple, list, set)):

			for single_value in value_spec:
				if isfunction(single_value) is False:
					raise RuntimeError(
						'Invalid specification. Must be function or tuple/list/set of functions'
					)

			def check(x):
				for f in value_spec:
					if f(x) is not True:
						raise_exception(str(x))

			return check

		elif isfunction(value_spec):
			return lambda x: None if value_spec(x) is True else raise_exception(str(x))
		else:
			raise RuntimeError('Invalid specification. Must be function or tuple/list/set of functions')


def verify_type(*tags, **type_kwargs):
	""" Shortcut for :class:`.TypeVerifier`

	:param tags: verification tags. See :meth:`.Verifier.__init__`
	:param type_kwargs: verifier specification. See :meth:`.TypeVerifier.check`
	:return: decorator (function)
	"""
	return TypeVerifier(*tags).decorator(**type_kwargs)


def verify_subclass(*tags, **type_kwargs):
	""" Shortcut for :class:`.SubclassVerifier`

	:param tags: verification tags. See :meth:`.Verifier.__init__`
	:param type_kwargs: verifier specification. See :meth:`.SubclassVerifier.check`
	:return: decorator (function)
	"""
	return SubclassVerifier(*tags).decorator(**type_kwargs)


def verify_value(*tags, **type_kwargs):
	""" Shortcut for :class:`.ValueVerifier`

	:param tags: verification tags. See :meth:`.Verifier.__init__`
	:param type_kwargs: verifier specification. See :meth:`.ValueVerifier.check`
	:return: decorator (function)
	"""
	return ValueVerifier(*tags).decorator(**type_kwargs)
