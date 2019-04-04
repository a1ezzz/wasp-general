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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from wasp_general.verify import verify_type, verify_value

# TODO: update wasp_general.command.enhanced
# TODO: update wasp_general.uri
# TODO: update wasp_general.network.socket
# TODO: update wasp_general.network.clients.*


class WArgumentRestrictionError(Exception):
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
			raise WArgumentRestrictionError(
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
			raise WArgumentRestrictionError(
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
				raise WArgumentRestrictionError(
					'The following argument can not have None value: "%s"' % argument
				)


class WArgumentRequirements(WArgumentsRestrictionProto):
	""" This class may check that at least N or exactly N or all required arguments are specified
	"""

	@verify_type('strict', arguments=str, main_argument=(str, None), occurrences=(int, None))
	@verify_type('strict', exact_occurrences=bool)
	@verify_value('strict', occurrences=lambda x: x is None or x > 0)
	def __init__(self, *requirements, main_argument=None, occurrences=None, exact_occurrences=True):
		""" Create new restriction

		:param requirements: arguments that are required (at least part of them are)
		:type arguments: str

		:param main_argument: name of a main argument. If it is set then requirement should be met only
		if this argument exists in a checking dictionary. It may be used for setting requirements for
		an optional argument
		:type main_argument: str | None

		:param occurrences: if it is specified then this is a number of requirements that should be in a
		checking dictionary, like N of all requirements must be. See 'exact_occurrences' parameter also.
		:type occurrences: int | None

		:param exact_occurrences: whether exact N occurrences must be specified or at least N occurrences
		must be. This value is used only if 'occurrences' parameter is set.
		:type exact_occurrences: bool
		"""

		self.__requirements = set(requirements)
		self.__main_argument = main_argument
		self.__occurrences = occurrences
		self.__exact_occurrences = exact_occurrences

		self.__exc_prefix = \
			'"%s" argument is required that' % self.__main_argument if self.__main_argument is not None \
				else 'It is required that'

		if self.__occurrences is None:
			self.__exc_prefix += \
				(' all the following arguments was specified: %s. ' % ', '.join(self.__requirements))
		elif self.__exact_occurrences is True:
			self.__exc_prefix += \
				' exact %i arguments of the following one was specified: %s. ' % (
					self.__occurrences, ', '.join(self.__requirements)
				)
		else:
			self.__exc_prefix += ' at least %i arguments of the following one was specified: %s. ' % (
					self.__occurrences, ', '.join(self.__requirements)
				)

	@verify_type('strict', arguments=dict)
	def check(self, arguments):
		""" :meth:`.WArgumentsRestrictionProto.check` method implementation
		:type arguments: dict[str, Object]
		:rtype: None
		"""
		if len(self.__requirements) == 0:
			return

		if self.__main_argument is not None and self.__main_argument not in arguments:
			return

		found_arguments = self.__requirements.intersection(set(arguments.keys()))
		if len(found_arguments) == 0:
			raise WArgumentRestrictionError(self.__exc_prefix + 'But no required argument was specified')
		elif self.__occurrences is not None:
			if len(found_arguments) < self.__occurrences:
				raise WArgumentRestrictionError(
					self.__exc_prefix + 'But only %i argments was specified' % len(found_arguments)
				)
			elif len(found_arguments) > self.__occurrences and self.__exact_occurrences is True:
				raise WArgumentRestrictionError(
					self.__exc_prefix + 'But extra %i arguments was specified' % (
						self.__occurrences - len(found_arguments)
					)
				)
		elif len(found_arguments) != len(self.__requirements):
			raise WArgumentRestrictionError(
				self.__exc_prefix + 'But only %i argments was specified' % len(found_arguments)
			)


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
					raise WArgumentRestrictionError(
						'An "%s" argument value can not have None value' % self.__main_argument
					)
			elif self.__re.match(value) is None:
				raise WArgumentRestrictionError(
					'An "%s" argument value does not match required pattern' % self.__main_argument
				)
		elif self.__required is True:
			raise WArgumentRestrictionError('The "%s" argument is required' % self.__main_argument)
