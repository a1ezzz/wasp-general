# -*- coding: utf-8 -*-
# wasp_general/api/check.py
#
# Copyright (C) 2019 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

import re
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value

import enum


class WArgsRestrictionError(Exception):
	""" This exception will raise if invalid arguments are specified
	"""
	pass


class WArgsRestrictionProto(metaclass=ABCMeta):
	""" Base class that is able to check that arguments are valid
	"""

	@abstractmethod
	def check(self, *args, **kwargs):
		""" Check that arguments are valid

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')


class WChainChecker(WArgsRestrictionProto):
	""" Class that may check arguments for compatibility with a set of restrictions
	"""

	@verify_type('strict', restrictions=WArgsRestrictionProto)
	def __init__(self, *restrictions):
		""" Create new checker

		:param restrictions: restrictions that arguments must be compatible with
		:type restrictions: WArgsRestrictionProto
		"""
		WArgsRestrictionProto.__init__(self)
		self.__restrictions = restrictions

	def check(self, *args, **kwargs):
		""" :meth:`.WArgsRestrictionProto.check` method implementation

		:rtype: None
		"""
		for restrictions in self.__restrictions:
			restrictions.check(*args, **kwargs)


class WConflictedArgs(WArgsRestrictionProto):
	""" This class may check that conflicted arguments are not specified together
	"""

	@verify_type('strict', arguments=str)
	def __init__(self, *arguments):
		""" Create new restriction

		:param arguments: arguments that can not be specified at the same moment
		:type arguments:  str
		"""
		WArgsRestrictionProto.__init__(self)
		self.__conflicted_arguments = set(arguments)

	def conflicted_arguments(self):
		""" Return argument's names that can not be specified at the same time

		:rtype: set[str]
		"""
		return self.__conflicted_arguments

	def check(self, *args, **kwargs):
		""" :meth:`.WArgsRestrictionProto.check` method implementation

		:rtype: None
		"""
		found_arguments = self.__conflicted_arguments.intersection(set(kwargs.keys()))
		if len(found_arguments) > 1:
			raise WArgsRestrictionError(
				'Conflicted arguments that can not be specified together was found: %s' %
				(', '.join(found_arguments))
			)


class WSupportedArgs(WArgsRestrictionProto):
	""" This class may check that all the arguments are known and there is no unknown (unsupported) arguments
	"""

	@verify_type('strict', arguments=str)
	def __init__(self, *arguments):
		""" Create new restriction

		:param arguments: arguments that are supported
		:type arguments: str
		"""
		WArgsRestrictionProto.__init__(self)
		self.__arguments = set(arguments)

	def supported_arguments(self):
		""" Return argument's names that may be specified

		:rtype: set[str]
		"""
		return self.__arguments

	def check(self, *args, **kwargs):
		""" :meth:`.WArgsRestrictionProto.check` method implementation

		:rtype: None
		"""
		found_arguments = set(kwargs.keys()).difference(self.__arguments)
		if found_arguments:
			raise WArgsRestrictionError(
				'Unsupported arguments was found: %s' % (', '.join(found_arguments))
			)


class WArgsRequirements(WArgsRestrictionProto):
	""" This class may check that at least N or exactly N or all the required arguments are specified
	"""

	@verify_type('strict', requirements=str, conditional_argument=(str, None), occurrences=(int, None))
	@verify_type('strict', exact_occurrences=bool)
	@verify_value('strict', occurrences=lambda x: x is None or x > 0)
	def __init__(self, *requirements, conditional_argument=None, occurrences=None, exact_occurrences=True):
		""" Create new restriction

		:param requirements: arguments that are required (or at least part of them are)
		:type arguments: str

		:param conditional_argument: name of a argument. If this argument is set then requirement
		should be met only if it passed as a named parameter. It may be used for setting requirements for
		an optional argument
		:type conditional_argument: str | None

		:param occurrences: if it is specified then this is a number of requirements that should be in a
		checking dictionary, like N of all requirements must be. See 'exact_occurrences' parameter also.
		:type occurrences: int | None

		:param exact_occurrences: whether exact N occurrences must be specified or at least N occurrences
		must be. This value is used only if 'occurrences' parameter is set.
		:type exact_occurrences: bool
		"""

		self.__requirements = set(requirements)
		self.__cond_argument = conditional_argument
		self.__occurrences = occurrences
		self.__exact_occurrences = exact_occurrences

		if self.__cond_argument is not None and self.__cond_argument in self.__requirements:
			raise ValueError('Conditional argument can not be specified as a requirement')

		if self.__occurrences is not None and self.__occurrences > len(self.__requirements):
			raise ValueError(
				'Requirement can not be satisfied because "occurrences" argument value is more then '
				'a number of all arguments'
			)

	def conditional_argument(self):
		""" Return conditional argument of this restriction

		:rtype: str | None
		"""
		return self.__cond_argument

	def requirements(self):
		""" Return requirements of this restriction

		:rtype: set[str]
		"""
		return self.__requirements

	def occurrences(self):
		""" Return number of argument occurrences that is specified in this restriction

		:rtype: int | None
		"""
		return self.__occurrences

	def exact_occurrences(self):
		""" Return True if number of arguments that must be specified is exact
		:meth:`.WArgsRequirements.occurrences` (nor less nor more). if
		:meth:`.WArgsRequirements.occurrences` was not set then None is returned

		:rtype: bool | None
		"""
		return self.__exact_occurrences if self.__occurrences is not None else None

	def check(self, *args, **kwargs):
		""" :meth:`.WArgsRestrictionProto.check` method implementation

		:rtype: None
		"""
		if len(self.__requirements) == 0:
			return

		if self.__cond_argument is not None and self.__cond_argument not in kwargs:
			return

		found_arguments = len(self.__requirements.intersection(set(kwargs.keys())))
		if found_arguments == 0:
			self.__raise_exc('But no required argument was specified')
		elif self.__occurrences is not None:
			args_diff = found_arguments - self.__occurrences

			if args_diff < 0:
				self.__raise_exc('But only %i arguments was specified' % found_arguments)
			elif self.__exact_occurrences is True and args_diff > 0:
				self.__raise_exc('But extra %i arguments was specified' % args_diff)
		elif found_arguments != len(self.__requirements):
			self.__raise_exc('But only %i arguments was specified' % found_arguments)

	def __raise_exc(self, msg):
		conditional_text = '"{0}" argument'.format(self.__cond_argument) if self.__cond_argument else 'It'
		if self.__occurrences is None:
			occurrences_text = 'all the following arguments'
		elif self.__exact_occurrences is True:
			occurrences_text = 'exact {0} arguments of the following'.format(self.__occurrences)
		else:
			occurrences_text = 'at least %i arguments of the following one'.format(self.__occurrences)

		raise WArgsRestrictionError(
			"{0} is required that {1} was specified: {2}. {3}".format(
				conditional_text,
				occurrences_text,
				', '.join(self.__requirements),
				msg
			)
		)


class WArgsValueRestriction(WArgsRestrictionProto):
	""" This is a base class that helps to check arguments value
	"""

	@enum.unique
	class ArgsSelection(enum.Enum):
		""" This enum defines selection of arguments that will be checked later
		"""
		none = 1  # None of the arguments will be selected
		positional_args = 2  # Positional arguments will be selected only
		kw_args = 3  # Named arguments will be selected only
		all = 4  # All the arguments will be selected

	@verify_type('strict', args_selection=ArgsSelection, extra_kw_args=str)
	def __init__(self, *extra_kw_args, args_selection=ArgsSelection.all):
		""" Create new restriction

		:param extra_kw_args: additional named arguments that will be checked
		:type extra_kw_args: str

		:param args_selection: selection filter
		:type args_selection: WArgsValueRestriction.ArgSelection
		"""
		WArgsRestrictionProto.__init__(self)
		self.__args_selection = args_selection
		self.__extra_kw_args = extra_kw_args

	def check(self, *args, **kwargs):
		""" :meth:`.WArgsRestrictionProto.check` method implementation

		:rtype: None
		"""
		selection_enum = WArgsValueRestriction.ArgsSelection

		if self.__args_selection in (selection_enum.positional_args, selection_enum.all):
			for argument in args:
				self.check_value(argument)

		if self.__args_selection in (selection_enum.kw_args, selection_enum.all):
			for name in kwargs:
				value = kwargs[name]
				self.check_value(value, name)
		elif self.__extra_kw_args is not None:
			for name in self.__extra_kw_args:
				if name in kwargs:
					value = kwargs[name]
					self.check_value(value, name)

	@abstractmethod
	@verify_type('strict', name=(str, None))
	def check_value(self, value, name=None):
		""" This check will be called for every selected argument

		:param value: value of an argument
		:type value: any

		:param name: for a named arguments this is argument's name
		:type name: str | None

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')


class WNotNullValues(WArgsValueRestriction):
	""" This class may check that arguments have values (have non-None value)
	"""

	@verify_type('paranoid', args_selection=WArgsValueRestriction.ArgsSelection)
	@verify_type('paranoid', extra_kw_args=str)
	def __init__(self, *extra_kw_args, args_selection=WArgsValueRestriction.ArgsSelection.all):
		""" Create new restriction

		:param extra_kw_args: select arguments to check (the sames as extra_kw_args parameter in
		:meth:`.WArgsValueRestriction.__init__`)
		:type extra_kw_args: str

		:param args_selection: select arguments to check (the sames as args_selection parameter in
		:meth:`.WArgsValueRestriction.__init__`)
		:type args_selection: WArgsValueRestriction.ArgSelection
		"""
		WArgsValueRestriction.__init__(self, *extra_kw_args, args_selection=args_selection)

	@verify_type('strict', name=(str, None))
	def check_value(self, value, name=None):
		""" :meth:`.WArgsValueRestriction.check_value` method implementation

		:rtype: None
		"""

		if value is None:
			if name is None:
				raise WArgsRestrictionError(
					'At least one value of positional arguments has the None value'
				)
			else:
				raise WArgsRestrictionError(
					'The following argument can not have None value: "%s"' % name
				)


class WArgsValueRegExp(WArgsValueRestriction):
	""" This class may check that string value matches regular expression
	"""

	@verify_type('strict', re_sentence=str, nullable=bool)
	@verify_type('paranoid', args_selection=WArgsValueRestriction.ArgsSelection, extra_kw_args=str)
	def __init__(
		self, re_sentence, *extra_kw_args, nullable=False,
		args_selection=WArgsValueRestriction.ArgsSelection.all
	):
		""" Create new restriction

		:param re_sentence: regular expression that value must match to
		:type re_sentence: str

		:param extra_kw_args: select arguments to check (the sames as extra_kw_args parameter in
		:meth:`.WArgsValueRestriction.__init__`)
		:type extra_kw_args: str

		:param nullable: whether argument may have None value (by default argument must have value that is a
		str instance).
		:type nullable: bool

		:param args_selection: select arguments to check (the sames as args_selection parameter in
		:meth:`.WArgsValueRestriction.__init__`)
		:type args_selection: WArgsValueRestriction.ArgSelection
		"""
		WArgsValueRestriction.__init__(self, *extra_kw_args, args_selection=args_selection)
		self.__re = re.compile(re_sentence)
		self.__nullable = nullable

	@verify_type('strict', value=(str, None), name=(str, None))
	def check_value(self, value, name=None):
		""" :meth:`.WArgsValueRestriction.check_value` method implementation

		:rtype: None
		"""
		if value is None:
			if self.__nullable is False:
				if name is None:
					raise WArgsRestrictionError(
						'Positional argument value can not have None value'
					)
				raise WArgsRestrictionError(
					'The "%s" argument value can not have None value' % str(name)
				)
		elif self.__re.match(value) is None:
			if name is None:
				raise WArgsRestrictionError(
					'Positional argument value does not match a specified pattern'
				)
			raise WArgsRestrictionError(
				'The "%s" argument value does not match a specified pattern' % str(name)
			)


class WIterValueRestriction(WArgsValueRestriction):
	""" This restriction applies a :class:`.WArgsValueRestriction` restriction on each element of iterable
	objects
	"""

	@verify_type('strict', restriction=WArgsValueRestriction, min_length=int, max_length=(int, None))
	@verify_type('paranoid', args_selection=WArgsValueRestriction.ArgsSelection, extra_kw_args=str)
	@verify_value('strict', min_length=lambda x: x >= 0, max_length=lambda x: x is None or x >= 0)
	def __init__(
		self, restriction, *extra_kw_args, min_length=0, max_length=None,
		args_selection=WArgsValueRestriction.ArgsSelection.all,
	):
		""" Create new restriction

		:param restriction: a restriction that will be applied on each element of selected iterable objects
		:type restriction: WArgsValueRestriction

		:param extra_kw_args: select arguments to check (the sames as extra_kw_args parameter in
		:meth:`.WArgsValueRestriction.__init__`)
		:type extra_kw_args: str

		:param min_length: restricts an iterable to have this number of items at least
		:type min_length: int

		:param max_length: restricts an iterable not to have items more than this value
		:type max_length: int | None

		:param args_selection: select arguments to check (the sames as args_selection parameter in
		:meth:`.WArgsValueRestriction.__init__`)
		:type args_selection: WArgsValueRestriction.ArgsSelection
		"""
		WArgsValueRestriction.__init__(self, *extra_kw_args, args_selection=args_selection)
		self.__restriction = restriction
		self.__min_length = min_length
		self.__max_length = max_length

	def min_length(self):
		""" Return minimum number of items in a selected iterable object (is 0 by default)

		:rtype: int
		"""
		return self.__min_length

	def max_length(self):
		""" Return maximum number of items in a selected iterable object or None if limit is not set (is None
		by default)

		:rtype: int | None
		"""
		return self.__max_length

	@verify_type('paranoid', name=(str, None))
	def check_value(self, value, name=None):
		""" :meth:`.WArgsValueRestriction.check_value` method implementation

		:rtype: None
		"""
		value_l = len(value)
		min_l = self.min_length()
		max_l = self.max_length()

		if value_l < min_l:
			raise WArgsRestrictionError(
				'Number of items in iterable object (%i) is less then a minimum (%i)' % (value_l, min_l)
			)
		if max_l is not None and value_l > max_l:
			raise WArgsRestrictionError(
				'Number of items in iterable object (%i) is more then a maximum (%i)' % (value_l, max_l)
			)

		for i in value:
			self.__restriction.check_value(i, name=name)
