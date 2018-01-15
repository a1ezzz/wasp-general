# -*- coding: utf-8 -*-
# wasp_general/command/enhanced.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

import re
from abc import abstractmethod
from enum import Enum

from wasp_general.verify import verify_type, verify_value, verify_subclass
from wasp_general.command.command import WCommandProto


class WCommandArgumentParsingError(Exception):
	pass


class WCommandArgumentDescriptor:

	class ArgumentCastingHelperProto:

		@abstractmethod
		@verify_type(argument_name=str)
		@verify_value(argument_name=lambda x: len(x) > 0)
		def cast(self, argument_name, argument_value):
			raise NotImplementedError('This method is abstract')

	class FlagArgumentCastingHelper(ArgumentCastingHelperProto):

		@verify_type(argument_name=str, argument_value=bool)
		@verify_value(argument_name=lambda x: len(x) > 0)
		def cast(self, argument_name, argument_value):
			return argument_value

	class ArgumentCastingHelper(ArgumentCastingHelperProto):

		@verify_type(error_message=(str, None))
		@verify_value(casting_fn=lambda x: x is None or callable(x))
		@verify_value(validate_fn=lambda x: x is None or callable(x))
		def __init__(self, casting_fn=None, validate_fn=None, error_message=None):
			WCommandArgumentDescriptor.ArgumentCastingHelperProto.__init__(self)
			self.__casting_fn = casting_fn
			self.__validate_fn = validate_fn
			self.__error_message = error_message

		def casting_function(self):
			return self.__casting_fn

		def validate_function(self):
			return self.__validate_fn

		def error_message(self):
			return self.__error_message

		@verify_type(argument_name=str, argument_value=str)
		@verify_value(argument_name=lambda x: len(x) > 0)
		def cast(self, argument_name, argument_value):
			casting_fn = self.casting_function()
			if casting_fn is not None:
				casted_argument_value = casting_fn(argument_value)
			else:
				casted_argument_value = argument_value
			validate_fn = self.validate_function()
			if validate_fn is not None:
				if validate_fn(casted_argument_value) is not True:
					error_message = self.error_message()
					if error_message is None:
						error_message = 'Attribute "%s" has invalid value: "%s"' % (
							argument_name, argument_value
						)
					raise WCommandArgumentParsingError(error_message)
			return casted_argument_value

	class StringArgumentCastingHelper(ArgumentCastingHelper):

		@verify_type('paranoid', error_message=(str, None))
		@verify_value('paranoid', validate_fn=lambda x: x is None or callable(x))
		def __init__(self, validate_fn=None, error_message=None):
			WCommandArgumentDescriptor.ArgumentCastingHelper.__init__(
				self, validate_fn=validate_fn, error_message=error_message
			)

	class IntegerArgumentCastingHelper(ArgumentCastingHelper):

		@verify_type('paranoid', error_message=(str, None))
		@verify_value('paranoid', validate_fn=lambda x: x is None or callable(x))
		@verify_type(base=int)
		@verify_value(base=lambda x: x > 0)
		def __init__(self, base=10, validate_fn=None, error_message=None):
			WCommandArgumentDescriptor.ArgumentCastingHelper.__init__(
				self, casting_fn=lambda x: int(x, base=base), validate_fn=validate_fn,
				error_message=error_message
			)

	class FloatArgumentCastingHelper(ArgumentCastingHelper):

		@verify_type('paranoid', error_message=(str, None))
		@verify_value('paranoid', validate_fn=lambda x: x is None or callable(x))
		def __init__(self, validate_fn=None, error_message=None):
			WCommandArgumentDescriptor.ArgumentCastingHelper.__init__(
				self, casting_fn=lambda x: float(x), validate_fn=validate_fn,
				error_message=error_message
			)

	class DataSizeArgumentHelper(ArgumentCastingHelper):

		__write_rate_re__ = re.compile('^(\d+[.\d]*)([KMGT]?)$')

		def __init__(self):
			WCommandArgumentDescriptor.ArgumentCastingHelper.__init__(
				self, casting_fn=self.cast_string
			)

		@staticmethod
		@verify_type(value=str)
		def cast_string(value):
			re_rate = WCommandArgumentDescriptor.DataSizeArgumentHelper.__write_rate_re__.search(value)
			if re_rate is None:
				raise ValueError('Invalid write rate')
			result = float(re_rate.group(1))
			if re_rate.group(2) == 'K':
				result *= (1 << 10)
			elif re_rate.group(2) == 'M':
				result *= (1 << 20)
			elif re_rate.group(2) == 'G':
				result *= (1 << 30)
			elif re_rate.group(2) == 'T':
				result *= (1 << 40)

			return result

	class EnumArgumentHelper(ArgumentCastingHelper):

		@verify_subclass(enum_cls=Enum)
		def __init__(self, enum_cls):
			WCommandArgumentDescriptor.ArgumentCastingHelper.__init__(
				self, casting_fn=self.cast_string
			)
			for item in enum_cls:
				if isinstance(item.value, str) is False:
					raise TypeError('Enum fields must bt str type')
			self.__enum_cls = enum_cls

		@verify_type(value=str)
		def cast_string(self, value):
			return self.__enum_cls(value)

	class RegExpArgumentHelper(ArgumentCastingHelper):

		@verify_type(regexp=str)
		def __init__(self, regexp):
			WCommandArgumentDescriptor.ArgumentCastingHelper.__init__(
				self, casting_fn=self.cast_string
			)
			self.__regexp = re.compile(regexp)

		def re(self):
			return self.__regexp

		def validate_function(self):
			return lambda x: x is not None

		@verify_type(value=str)
		def cast_string(self, value):
			result = self.re().match(value)
			if result is not None:
				return result.groups()

	@verify_type(argument_name=str, required=bool, flag_mode=bool, multiple_values=bool, help_info=(str, None))
	@verify_type(meta_var=(str, None), default_value=(str, None))
	@verify_value(argument_name=lambda x: len(x) > 0)
	def __init__(
		self, argument_name, required=False, flag_mode=False, multiple_values=False, help_info=None,
		meta_var=None, default_value=None, casting_helper=None
	):
		"""
		note: 'required' is useless for flag-mode attribute
		"""
		if (flag_mode is True and multiple_values is True) or \
			(flag_mode is True and default_value is not None) or \
			(multiple_values is True and default_value is not None):
				raise ValueError(
					'Argument has conflict options. "flag_mode" and "multiple_values" can not be '
					'used at the same time'
				)

		if casting_helper is not None:
			flag_helper = WCommandArgumentDescriptor.FlagArgumentCastingHelper
			general_helper = WCommandArgumentDescriptor.ArgumentCastingHelper

			if flag_mode is True and isinstance(casting_helper, flag_helper) is False:
				raise TypeError(
					'casting_helper must be an instance of '
					'WCommandArgumentDescriptor.FlagArgumentCastingHelper for flag-mode attribute'
				)
			elif flag_mode is False and isinstance(casting_helper, general_helper) is False:
				raise TypeError(
					'casting_helper must be an instance of '
					'WCommandArgumentDescriptor.ArgumentCastingHelper for every attribute except '
					'flag-mode attribute'
				)

		self.__argument_name = argument_name
		self.__flag_mode = flag_mode
		self.__multiple_values = multiple_values
		self.__default_value = default_value

		self.__required = required
		self.__help_info = help_info
		self.__meta_var = meta_var

		if casting_helper is not None:
			self.__casting_helper = casting_helper
		elif flag_mode is True:
			self.__casting_helper = WCommandArgumentDescriptor.FlagArgumentCastingHelper()
		else:
			self.__casting_helper = WCommandArgumentDescriptor.StringArgumentCastingHelper()

	def argument_name(self):
		return self.__argument_name

	def flag_mode(self):
		return self.__flag_mode

	def multiple_values(self):
		return self.__multiple_values

	def required(self):
		return self.__required

	def default_value(self):
		return self.__default_value

	def casting_helper(self):
		return self.__casting_helper

	@verify_type(argument_name=str)
	@verify_value(argument_name=lambda x: len(x) > 0)
	def cast(self, argument_name, argument_value):
		return self.casting_helper().cast(argument_name, argument_value)

	def help_info(self):
		return self.__help_info

	def meta_var(self):
		return self.__meta_var


class WCommandArgumentRelationship:

	class Relationship(Enum):
		conflict = 1
		requirement = 2
		one_of = 3

	@verify_type(argument_names=str)
	def __init__(self, relationship, *argument_names):
		if isinstance(relationship, WCommandArgumentRelationship.Relationship) is False:
			raise TypeError('Invalid relationship type')
		self.__relationship = relationship
		if len(argument_names) < 2:
			raise ValueError('Relationship can be made with 2 arguments and more')
		self.__arguments = argument_names

	def relationship(self):
		return self.__relationship

	def arguments(self):
		return self.__arguments


class WCommandArgumentParser:

	@verify_type(argument_descriptors=WCommandArgumentDescriptor, relationships=(list, tuple, set, None))
	def __init__(self, *argument_descriptors, relationships=None):
		self.__descriptors = argument_descriptors
		self.__relationships = relationships
		if self.__relationships is not None:
			for relation in self.__relationships:
				if isinstance(relation, WCommandArgumentRelationship) is False:
					raise TypeError('Invalid relationship type')
				for argument_name in relation.arguments():
					argument_found = False
					for descriptor in self.__descriptors:
						if argument_name == descriptor.argument_name():
							argument_found = True
							break
					if argument_found is False:
						raise ValueError('Relationship with unknown argument was specified')

	def descriptors(self):
		return self.__descriptors

	def relationships(self):
		return self.__relationships

	def __select_arguments(self, relation, parsed_result):
		result = []
		arguments = relation.arguments()
		for argument_name in arguments:
			if argument_name in parsed_result.keys():
				result.append(argument_name)
		return result

	def __check_conflict_relation(self, relation, parsed_result):
		conflict_arguments = self.__select_arguments(relation, parsed_result)
		if len(conflict_arguments) >= 1:
			raise WCommandArgumentParsingError(
				"Conflict arguments was found: %s" % (', '.join(conflict_arguments))
			)

	def __check_requirements_relation(self, relation, parsed_result):
		found_arguments = set(self.__select_arguments(relation, parsed_result))
		required_arguments = set(relation.arguments())

		not_found_arguments = required_arguments.difference(found_arguments)
		if len(not_found_arguments) > 0 and len(not_found_arguments) != len(required_arguments):
			raise WCommandArgumentParsingError(
				"Required arguments wasn't found: %s" % (', '.join(not_found_arguments))
			)

	def __check_one_of_relation(self, relation, parsed_result):
		found_arguments = set(self.__select_arguments(relation, parsed_result))

		if len(found_arguments) > 1:
			raise WCommandArgumentParsingError(
				"Conflict arguments was found: %s" % (', '.join(found_arguments))
			)
		elif len(found_arguments) == 0:
			arguments = relation.arguments()
			raise WCommandArgumentParsingError(
				"Required arguments was not found. It should be one of: %s" % (', '.join(arguments))
			)

	@verify_type(command_tokens=str)
	def parse(self, *command_tokens):
		descriptors = list(self.descriptors())
		command_tokens = list(command_tokens)
		result = {}
		while len(command_tokens) > 0:
			reduced_command_tokens, descriptors, next_result = \
				self.reduce_tokens(command_tokens.copy(), descriptors.copy(), previous_result=result)
			if len(reduced_command_tokens) >= len(command_tokens):
				raise WCommandArgumentParsingError("Command tokens wasn't reduce")

			command_tokens = reduced_command_tokens
			result = next_result

		relationships = self.relationships()
		if relationships is not None:
			for relation in relationships:
				relation_type = relation.relationship()
				if relation_type == WCommandArgumentRelationship.Relationship.conflict:
					self.__check_conflict_relation(relation, result)
				elif relation_type == WCommandArgumentRelationship.Relationship.requirement:
					self.__check_requirements_relation(relation, result)
				elif relation_type == WCommandArgumentRelationship.Relationship.one_of:
					self.__check_one_of_relation(relation, result)
				else:
					raise RuntimeError('Unknown relationship was specified')

		for descriptor in descriptors:
			argument_name = descriptor.argument_name()
			if descriptor.flag_mode() is True:
				result[argument_name] = descriptor.cast(argument_name, False)
			if descriptor.default_value() is not None:
				result[argument_name] = descriptor.cast(argument_name, descriptor.default_value())

		for descriptor in self.descriptors():
			if descriptor.required() is True:
				argument_name = descriptor.argument_name()
				if argument_name not in result.keys():
					raise WCommandArgumentParsingError(
						"Required argument wasn't found: %s" % argument_name
					)

		return result

	@classmethod
	@verify_type(command_tokens=list, argument_descriptors=list, previous_result=(dict, None))
	def reduce_tokens(cls, command_tokens, argument_descriptors, previous_result=None):
		argument_name = command_tokens.pop(0)

		descriptor = None
		for i in range(len(argument_descriptors)):
			descriptor_to_check = argument_descriptors[i]
			if descriptor_to_check.argument_name() == argument_name:
				descriptor = descriptor_to_check
				if descriptor_to_check.multiple_values() is False:
					argument_descriptors.pop(i)
				break
		if descriptor is None:
			if argument_name in previous_result.keys():
				raise WCommandArgumentParsingError(
					'Multiple argument ("%s") values found' % argument_name
				)
			else:
				raise WCommandArgumentParsingError('Unknown argument: "%s"' % argument_name)

		result = previous_result.copy() if previous_result is not None else {}
		if descriptor.flag_mode() is True:
			result[argument_name] = descriptor.cast(argument_name, True)
		else:
			if len(command_tokens) == 0:
				raise WCommandArgumentParsingError("Argument requires value. Value wasn't found")
			argument_value = descriptor.cast(argument_name, command_tokens.pop(0))

			if descriptor.multiple_values() is True:
				if argument_name not in result.keys():
					result[argument_name] = [argument_value]
				else:
					result[argument_name].append(argument_value)
			else:
				if argument_name not in result.keys():
					result[argument_name] = argument_value
				else:
					raise WCommandArgumentParsingError(
						'Multiple values spotted for the single argument'
					)

		return command_tokens, argument_descriptors, result

	def arguments_help(self):
		result = []
		for argument in self.descriptors():
			argument_name = argument.argument_name()
			if argument.flag_mode() is not True:
				value_name = argument.meta_var()
				if value_name is None:
					value_name = 'value'
				argument_name = '%s [%s]' % (argument_name, value_name)

			description = argument.help_info()
			if description is None:
				description = 'argument description unavailable'

			meta = []
			if argument.required() is True:
				meta.append('required')

			if argument.multiple_values() is True:
				meta.append('may have multiple values')

			default_value = argument.default_value()
			if default_value is not None:
				meta.append('default value: %s' % default_value)

			if len(meta) > 0:
				description += (' (%s)' % ', '.join(meta))

			result.append((argument_name, description))
		return tuple(result)


class WEnhancedCommand(WCommandProto):

	@verify_type('paranoid', argument_descriptors=WCommandArgumentDescriptor, relationships=(list, tuple, set, None))
	@verify_type(command=str)
	@verify_value(command=lambda x: len(x) > 0)
	def __init__(self, command, *argument_descriptors, relationships=None):
		WCommandProto.__init__(self)
		self.__command = command
		self.__arguments_descriptors = argument_descriptors
		self.__relationships = relationships
		self.__parser = WCommandArgumentParser(*self.argument_descriptors(), relationships=self.relationships())

	def command_token(self):
		return self.__command

	def argument_descriptors(self):
		return self.__arguments_descriptors

	def relationships(self):
		return self.__relationships

	def parser(self):
		return self.__parser

	@verify_type(command_tokens=str)
	def match(self, *command_tokens, **command_env):
		if len(command_tokens) > 0:
			if command_tokens[0] == self.command_token():
				return True
		return False

	@verify_type(command_tokens=str)
	def exec(self, *command_tokens, **command_env):
		if len(command_tokens) > 0:
			if command_tokens[0] == self.command_token():
				return self._exec(self.parser().parse(*command_tokens[1:]), **command_env)
		raise RuntimeError('Invalid tokens')

	@abstractmethod
	@verify_type(command_arguments=dict)
	def _exec(self, command_arguments, **command_env):
		raise NotImplementedError('This method is abstract')

	def arguments_help(self):
		return self.parser().arguments_help()

	def command_help(self):
		arguments_help = self.arguments_help()
		if len(arguments_help) == 0:
			return 'Command does not have arguments\n'

		info = 'Command arguments:\n'
		for argument_name, argument_description in arguments_help:
			info += '\t%s - %s\n' % (argument_name, argument_description)
		return info
