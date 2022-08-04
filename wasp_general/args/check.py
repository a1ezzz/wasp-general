# -*- coding: utf-8 -*-
# wasp_general/args/check.py
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

from wasp_general.verify import verify_type

# TODO: update wasp_general.command.enhanced
# TODO: update wasp_general.uri
# TODO: update wasp_general.network.socket
# TODO: update wasp_general.network.clients.*


class WArgumentRestrictionException(Exception):
	""" This exception will raise if invalid arguments are specified
	"""
	pass


class WArgumentsRestrictionProto(metaclass=ABCMeta):
	""" Base class that is able to check that arguments are valid
	"""

	@abstractmethod
	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" Check that arguments are valid

		:param arguments: dictionary where keys are argument names and values - related argument values
		:type arguments: dict[str, Object]

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')


class WArgumentsChecker(WArgumentsRestrictionProto):
	""" Base class that may check arguments for compatibility with different restrictions
	"""

	@verify_type('strict', restrictions=WArgumentsRestrictionProto)
	def __init__(self, *restrictions):
		""" Create new arguments checker

		:param restrictions: restrictions that arguments must be compatible with
		:type restrictions: WArgumentsRestrictionProto
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__restrictions = restrictions

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		for restrictions in self.__restrictions:
			restrictions.check(arguments)


class WRequiredArguments(WArgumentsRestrictionProto):
	""" This class may check that all required arguments are specified
	"""

	@verify_type('strict', arguments=str)
	def __init__(self, *arguments):
		""" Create new restriction

		:param arguments: arguments that must be specified
		:type arguments: str
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__required_arguments = set(arguments)

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		not_found_arguments = self.__required_arguments.difference(set(arguments.keys()))
		if not_found_arguments:
			raise WArgumentRestrictionException(
				'The following arguments was not found: %s' % (', '.join(not_found_arguments))
			)


class WConflictedArguments(WArgumentsRestrictionProto):
	""" This class may check that conflicted arguments are not specified together
	"""

	@verify_type('strict', arguments=str)
	def __init__(self, *arguments):
		""" Create new restriction

		:param arguments: arguments that can not be specified at the same moment
		:type arguments:  str
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__conflicted_arguments = set(arguments)

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		found_arguments = self.__conflicted_arguments.intersection(set(arguments.keys()))
		if len(found_arguments) > 1:
			raise WArgumentRestrictionException(
				'Conflicted arguments that can not be specified together was found: %s' %
				(', '.join(found_arguments))
			)


class WSupportedArguments(WArgumentsRestrictionProto):
	""" This class may check that all the arguments are known and there is no unknown (unsupported) arguments
	"""

	@verify_type('strict', arguments=str)
	def __init__(self, *arguments):
		""" Create new restriction

		:param arguments: arguments that are supported
		:type arguments: str
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__arguments = set(arguments)

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		found_arguments = set(arguments.keys()).difference(self.__arguments)
		if found_arguments:
			raise WArgumentRestrictionException(
				'Unsupported arguments was found: %s' % (', '.join(found_arguments))
			)


class WNotNullArguments(WArgumentsRestrictionProto):
	""" This class may check that arguments have values (have non-None value)
	"""

	@verify_type('strict', arguments=str)
	def __init__(self, *arguments):
		""" Create new restriction

		:param arguments: arguments that can not have None value
		:type arguments:  str
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__arguments = arguments

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		for argument in self.__arguments:
			if argument in arguments and arguments[argument] is None:
				raise WArgumentRestrictionException(
					'The following argument can not have None value: "%s"' % argument
				)


class WOneOfArgument(WArgumentsRestrictionProto):
	""" This class may check that at least one (or exactly one) argument is specified
	"""

	@verify_type('strict', arguments=str, exact_one=bool)
	def __init__(self, *arguments, exact_one=False):
		""" Create new restriction

		:param arguments: arguments from which at least one (or exactly one) argument must be specified
		:type arguments: str

		:param exact_one: whether at least one or exactly one argument must be specified (at least one by
		default)
		:type exact_one: bool
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__arguments = set(arguments)
		self.__exact_one = exact_one

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		if len(self.__arguments) == 0:
			return

		found_arguments = self.__arguments.intersection(set(arguments.keys()))
		if len(found_arguments) == 0:
			if self.__exact_one:
				raise WArgumentRestrictionException(
					'One of the following arguments must be specified: %s' %
					(', '.join(self.__arguments))
				)
			raise WArgumentRestrictionException(
				'At least one of the following arguments must be specified: %s' %
				(', '.join(self.__arguments))
			)
		elif len(found_arguments) > 1 and self.__exact_one:
			raise WArgumentRestrictionException(
				'Only one of the following arguments must be specified: %s' %
				(', '.join(self.__arguments))
			)


class WArgumentDependency(WArgumentsRestrictionProto):
	""" This class may check that required arguments are specified only if a main argument is specified
	"""

	@verify_type('strict', main_argument=str)
	@verify_type('paranoid', required_arguments=str)
	def __init__(self, main_argument, *required_arguments):
		""" Create new restriction

		:param main_argument: if this argument is specified in check, then all other arguments must be
		specified also
		:type main_argument: str

		:param required_arguments: arguments that must be specified if main argument is specified
		:type required_arguments: str
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__main_argument = main_argument
		self.__dependency_check = WRequiredArguments(*required_arguments)

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		if self.__main_argument in arguments:
			self.__dependency_check.check(arguments)


class WArgumentOneOfDependency(WArgumentsRestrictionProto):
	""" This class may check that at least one (or exactly one) argument is specified only if a main argument
	is specified
	"""

	@verify_type('strict', main_argument=str)
	@verify_type('paranoid', arguments=str, exact_one=bool)
	def __init__(self, main_argument, *arguments, exact_one=False):
		""" Create new restriction

		:param main_argument: if this argument is specified in check, then at least one (or exactly one)
		arguments is specified also
		:type main_argument: str

		:param arguments: arguments from which at least one (or exactly one) argument must be specified
		:type arguments: str

		:param exact_one: whether at least one or exactly one argument must be specified (at least one by
		default)
		:type exact_one: bool
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__main_argument = main_argument
		self.__dependency_check = WOneOfArgument(*arguments, exact_one=exact_one)

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		if self.__main_argument in arguments:
			self.__dependency_check.check(arguments)


class WArgumentRERestriction(WArgumentsRestrictionProto):
	""" This class may check that string value of argument matches regular expression
	"""

	@verify_type('strict', main_argument=str, re_sentence=str, required=bool, nullable=bool)
	def __init__(self, main_argument, re_sentence, required=False, nullable=False):
		""" Create new restriction

		:param main_argument: argument which value is checked
		:type main_argument: str

		:param re_sentence: regular expression that value must match to
		:type re_sentence: str

		:param required: whether argument is optional - may not be specified (is optional by default).
		:type required: bool

		:param nullable: whether argument may have None value (by default argument must have value that is a
		str instance).
		:type nullable: bool
		"""
		WArgumentsRestrictionProto.__init__(self)
		self.__main_argument = main_argument
		self.__re = re.compile(re_sentence)
		self.__required = required
		self.__nullable = nullable

	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		if self.__main_argument in arguments:
			value = arguments[self.__main_argument]
			if value is None:
				if self.__nullable is False:
					raise WArgumentRestrictionException(
						'An "%s" argument value can not have None value' % self.__main_argument
					)
			elif self.__re.match(value) is None:
				raise WArgumentRestrictionException(
					'An "%s" argument value does not match required pattern' % self.__main_argument
				)
		elif self.__required is True:
			raise WArgumentRestrictionException('The "%s" argument is required' % self.__main_argument)
