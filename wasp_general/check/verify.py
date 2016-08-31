# -*- coding: utf-8 -*-
# wasp_general/check/verfy.py
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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import sys
import os
from inspect import getargspec, isclass, isfunction, getsource
from decorator import decorator


class Verificator:

	__default_environment_var__ = 'WASP_VERIFICATOR_DISABLE_CHECKS'
	__tags_delimiter__ = ':'

	def __init__(self, *tags, env_var=None, silent_checks=False):
		self._tags = list(tags)
		self._env_var = env_var if env_var is not None else self.__class__.__default_environment_var__
		self._silent_checks = silent_checks

	def check_disabled(self):
		if self._env_var not in os.environ or len(self._tags) == 0:
			return False
		env = os.environ[self._env_var].split(self.__class__.__tags_delimiter__)
		for tag in self._tags:
			if tag not in env:
				return False
		return True

	def check(self, arg_spec, arg_name, decorated_function):
		return lambda x: None

	def decorator(self, **arg_specs):

		if self.check_disabled() is True:
			def empty_decorator(decorated_function):
				return decorated_function
			return empty_decorator

		def first_level_decorator(decorated_function):

			inspected_args = getargspec(decorated_function).args
			args_check = {}

			for i in range(len(inspected_args)):
				arg_name = inspected_args[i]

				if arg_name not in arg_specs.keys():
					args_check[arg_name] = lambda x: None
					continue

				args_check[arg_name] = self.check(arg_specs[arg_name], arg_name, decorated_function)

			for arg_name in arg_specs.keys():
				if arg_name not in args_check.keys():
					args_check[arg_name] = \
						self.check(arg_specs[arg_name], arg_name, decorated_function)

			def second_level_decorator(decorated_function, *args, **kwargs):
				for i in range(len(args)):
					arg_name = inspected_args[i]
					try:
						args_check[arg_name](args[i])
					except Exception as e:
						self.help_info(e, decorated_function, arg_name, arg_specs[arg_name])
						raise

				for kw_key in kwargs.keys():
					if kw_key in args_check.keys():
						try:
							args_check[kw_key](kwargs[kw_key])
						except Exception as e:
							self.help_info(e, decorated_function, kw_key, arg_specs[kw_key])
							raise

				return decorated_function(*args, **kwargs)
			return decorator(second_level_decorator)(decorated_function)
		return first_level_decorator

	def help_info(self, exc, decorated_function, arg_name, arg_spec):
		if self._silent_checks is not True:
			print('Exception raised:', file=sys.stderr)
			print(str(exc), file=sys.stderr)
			print('Decorated function: %s' % decorated_function.__name__, file=sys.stderr)
			if decorated_function.__doc__ is not None:
				print('Decorated function docstrings:', file=sys.stderr)
				print(decorated_function.__doc__, file=sys.stderr)
			print('Argument "%s" specification:' % arg_name, file=sys.stderr)
			if isfunction(arg_spec):
				print(getsource(arg_spec), file=sys.stderr)
			else:
				print(str(arg_spec), file=sys.stderr)

			print('', file=sys.stderr)


class TypeVerificator(Verificator):

	def raise_exception(self, exc_text, *args, **kwargs):
		raise TypeError(exc_text)

	def check(self, type_spec, arg_name, decorated_function):
		exc_text = 'Argument "%s" for function "%s" has invalid type' % (arg_name, decorated_function.__name__)
		exc_text += ' (%s)'

		if isinstance(type_spec, (tuple, list, set)):
			for single_type in type_spec:
				if (single_type is not None) and isclass(single_type) is False:
					raise RuntimeError('Invalid specification. Must be type or tuple/list/set of types')
			if None in type_spec:
				type_spec = tuple(filter(lambda x: x is not None, type_spec))
				return lambda x: None if x is None or isinstance(x, tuple(type_spec)) is True else \
					self.raise_exception(exc_text % str((type(x))))
			else:
				return lambda x: None if isinstance(x, tuple(type_spec)) is True else \
					self.raise_exception(exc_text % str((type(x))))
		elif isclass(type_spec):
			return lambda x: None if isinstance(x, type_spec) is True else \
				self.raise_exception(exc_text % str((type(x))))
		else:
			raise RuntimeError('Invalid specification. Must be type or tuple/list/set of types')


class SubclassVerificator(Verificator):

	def raise_exception(self, exc_text, *args, **kwargs):
		raise TypeError(exc_text)

	def check(self, type_spec, arg_name, decorated_function):
		exc_text = 'Argument "%s" for function "%s" has invalid type' % (arg_name, decorated_function.__name__)
		exc_text += ' (%s)'

		if isinstance(type_spec, (tuple, list, set)):
			for single_type in type_spec:
				if (single_type is not None) and isclass(single_type) is False:
					raise RuntimeError('Invalid specification. Must be type or tuple/list/set of types')
			if None in type_spec:
				type_spec = tuple(filter(lambda x: x is not None, type_spec))
				return lambda x: None if x is None or (isclass(x) is True and issubclass(x, type_spec) is True) else \
					self.raise_exception(exc_text % str(x))
			else:
				return lambda x: None if (isclass(x) is True and issubclass(x, type_spec) is True) else \
					self.raise_exception(exc_text % str(x))
		elif isclass(type_spec):
			return lambda x: None if (isclass(x) is True and issubclass(x, type_spec) is True) else \
				self.raise_exception(exc_text % str(x))
		else:
			raise RuntimeError('Invalid specification. Must be type or tuple/list/set of types')


class ValueVerificator(Verificator):

	def raise_exception(self, exc_text, *args, **kwargs):
		raise ValueError(exc_text)

	def check(self, value_spec, arg_name, decorated_function):

		exc_text = 'Argument "%s" for function "%s" has invalid value' % (arg_name, decorated_function.__name__)
		exc_text += ' (%s)'

		if isinstance(value_spec, (tuple, list, set)):

			for single_value in value_spec:
				if isfunction(single_value) is False:
					raise RuntimeError('Invalid specification. Must be function or tuple/list/set of functions')

			def check(x):
				for f in value_spec:
					if f(x) is not True:
						self.raise_exception(exc_text % str(x))

			return check

		elif isfunction(value_spec):
			return lambda x: None if value_spec(x) is True else self.raise_exception(exc_text % str(x))
		else:
			raise RuntimeError('Invalid specification. Must be function or tuple/list/set of functions')


def verify_type(*tags, **type_kwargs):
	return (TypeVerificator(*tags).decorator(**type_kwargs))


def verify_subclass(*tags, **type_kwargs):
	return (SubclassVerificator(*tags).decorator(**type_kwargs))


def verify_value(*tags, **type_kwargs):
	return (ValueVerificator(*tags).decorator(**type_kwargs))
