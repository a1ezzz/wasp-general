# -*- coding: utf-8 -*-
# wasp_general/command_context.py
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

# TODO: tests require

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type
from wasp_general.command import WCommandProto, WCommandResult, WCommandPrioritizedSelector, WCommandSet


class WContextProto(metaclass=ABCMeta):
	""" Represent context configuration
	"""

	@abstractmethod
	def context_name(self):
		""" Return this context name

		:return: str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def context_value(self):
		""" Return this context value (can be None)

		:return: str or None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def linked_context(self):
		""" Return link to 'parent'/'higher' context

		:return: WContextProto or None
		"""
		raise NotImplementedError('This method is abstract')

	def __len__(self):
		""" Return linked context count

		:return: int
		"""
		return len([x for x in self])

	def __iter__(self):
		"""Iterate over

		:return:
		"""
		context = self
		while context is not None:
			yield context
			context = context.linked_context()

	def __eq__(self, other):
		""" Compare two context. Two context are equal if they have the same context_name and each their own
		linked context are equal also.

		:param other: context to compare
		:return: bool
		"""
		if isinstance(other, WContextProto) is False:
			return False

		context_a = self
		context_b = other

		while context_a is not None and context_b is not None:
			if context_a.context_name() != context_b.context_name():
				return False

			context_a = context_a.linked_context()
			context_b = context_b.linked_context()

		if context_b is not None:
			return False
		return True



class WContext(WContextProto):
	""" :class:`.WContextProto` implementation
	"""

	@verify_type(context_name=str, context_value=(str, None), linked_context=(WContextProto, None))
	def __init__(self, context_name, context_value=None, linked_context=None):
		""" Create new context request

		:param context_name: context name
		:param context_value: context value
		:param linked_context: linked context
		"""
		self.__context_name = context_name
		self.__context_value = context_value
		self.__linked_context = linked_context

	def context_name(self):
		""" :meth:`.WContextProto.context_name` implementation
		"""
		return self.__context_name

	def context_value(self):
		""" :meth:`.WContextProto.context_value` implementation
		"""
		return self.__context_value

	def linked_context(self):
		""" :meth:`.WContextProto.linked_context` implementation
		"""
		return self.__linked_context

	@classmethod
	@verify_type(context=WContextProto)
	def export_context(cls, context):
		""" Export the specified context to be capable context transferring

		:param context: context to export
		:return: tuple
		"""
		result = [(x.context_name(), x.context_value()) for x in context]
		result.reverse()
		return tuple(result)

	@classmethod
	@verify_type(context=(tuple, None))
	def import_context(cls, context):
		""" Import context to corresponding WContextProto object (:meth:`WCommandContextResult.export_context`
		reverse operation)

		:param context: context to import
		:return: WContext
		"""
		if context is None or len(context) == 0:
			return

		result = WContext(context[0][0], context[0][1])
		for iter_context in context[1:]:
			result = WContext(iter_context[0], context_value=iter_context[1], linked_context=result)
		return result

	@classmethod
	@verify_type(context_specs=str)
	def specification(cls, *context_specs):
		""" Return linked context as adapter specification (is used by :class:`.WCommandContextAdapter`)

		:param context_specs: context names
		:return: WContext
		"""
		import_data = []
		for name in context_specs:
			import_data.append((name, None))
		return cls.import_context(tuple(import_data))


class WCommandContextAdapter(metaclass=ABCMeta):
	""" Adapter is used for command tokens modification
	"""

	@verify_type(context_specifications=(WContextProto, None))
	def __init__(self, context_specifications):
		""" Create adapter

		:param context_specifications: context for what this adapter works
		"""
		self.__spec = context_specifications

	def specification(self):
		""" Return adapter specification

		:return: WContextProto
		"""
		return self.__spec

	@verify_type(request_context=(WContextProto, None))
	def match(self, request_context=None):
		""" Check if context request is compatible with adapters specification. True - if compatible,
		False - otherwise

		:param request_context: context to check
		:return: bool
		"""
		spec = self.specification()
		if request_context is None and spec is None:
			return True
		elif request_context is not None and spec is not None:
			return request_context == spec
		return False

	@abstractmethod
	@verify_type(command_tokens=str, request_context=(WContextProto, None))
	def adapt(self, *command_tokens, request_context=None):
		""" Adapt the given command tokens with this adapter

		:param command_tokens: command tokens to adapt
		:param request_context: context
		:return: list of str
		"""
		raise NotImplementedError('This method is abstract')


class WCommandContext(WCommandProto):
	""" Command that can be adapt by a context
	"""

	@verify_type(command=WCommandProto, context_adapter=WCommandContextAdapter)
	def __init__(self, base_command, context_adapter):
		""" Create new command

		:param base_command: basic command that does real magic
		:param context_adapter: adapter for command tokens modification
		"""
		WCommandProto.__init__(self)
		self.__command = base_command
		self.__adapter = context_adapter

	def original_command(self):
		""" Return source command

		:return: WCommandProto
		"""
		return self.__command

	def adapter(self):
		""" Return command adapter

		:return: WCommandAdapter
		"""
		return self.__adapter

	@verify_type(command_tokens=str)
	def match(self, *command_tokens):
		""" Match original command like if no context specified

		:param command_tokens: command tokens to check
		:return: bool
		"""
		return self.match_context(*command_tokens)

	@verify_type(command_tokens=str, request_context=(WContextProto, None))
	def match_context(self, *command_tokens, request_context=None):
		""" Checks whether this command (modified original one) can be called with the given tokens and
		the given context. Return True - if match, False - otherwise

		:param command_tokens: tokens to check
		:param request_context: context for adapter
		:return: bool
		"""
		if self.adapter().match(request_context) is False:
			return False

		command_tokens = self.adapter().adapt(*command_tokens, request_context=request_context)
		return self.original_command().match(*command_tokens)

	@verify_type(command_tokens=str)
	def exec(self, *command_tokens):
		""" Execute original command like if no context specified

		:param command_tokens: command tokens to execute
		:return: WCommandResult
		"""
		return self.exec_context(*command_tokens)

	@verify_type(command_tokens=str, request_context=(WContextProto, None))
	def exec_context(self, *command_tokens, request_context=None):
		""" Execute this command (modified original one) and return result

		:param command_tokens: command tokens to execute
		:param request_context: context for adapter
		:return: WCommandResult
		"""
		if self.adapter().match(request_context) is False:
			cmd = WCommandProto.join_tokens(*command_tokens)
			spec = self.adapter().specification()
			if spec is not None:
				spec = [x.context_name() for x in spec]
				spec.reverse()
				spec = ','.join(spec)
			raise RuntimeError('Command mismatch: %s (context: %s)' % (cmd, spec))

		command_tokens = self.adapter().adapt(*command_tokens, request_context=request_context)
		return self.original_command().exec(*command_tokens)


class WCommandContextResult(WCommandResult):
	""" This is modified version of command result, that can return target context. Can be used for context
	switching as a result of some command execution
	"""

	@verify_type(output=(str, None), context=(WContextProto, None))
	def __init__(self, output=None, error=None, context=None):
		""" Create new result

		:param output: same as output in :meth:`.WCommandResult.__init__`
		:param error: same as error in :meth:`.WCommandResult.__init__`
		:param context: context to set
		"""
		WCommandResult.__init__(self, output, error)
		self.context = context.export_context(context) if context is not None else None


class WCommandContextSelector(WCommandPrioritizedSelector):
	""" This is modified version of prioritized selector that can select WCommandContext commands via
	:meth:`.WCommandContext.match_context` call
	"""

	@verify_type(command_tokens=str, request_context=(WContextProto, None))
	def select(self, *command_tokens, request_context=None):
		""" Select command from internal storage, that matches the given tokens and the given context

		:param command_tokens: tokens to find
		:param request_context: context to use
		:return: WCommandProto or None
		"""
		for command_obj in self:
			if isinstance(command_obj, WCommandContext) is True:
				if command_obj.match_context(*command_tokens, request_context=request_context) is True:
					return command_obj
			elif command_obj.match(*command_tokens):
				return command_obj


class WCommandContextSet(WCommandSet):
	""" Class that handles normal and context-oriented command execution.

	All the command can be separated by the answer - "how does they work with context?". And so there are:
	- Commands that work in any context. Ordinary command (like :class:`.WCommand`) that behave the same
	way everywhere. For example: 'quit', 'exit' and 'help' (if help message is the same all the time)
	- Commands that work in specific context. It can be commands that can be executed in a single context only,
	or commands, that behaves differently in the different context like 'list' or 'help' (if help message is
	different in different context)

	Depends on adapters specification commands can also be:
	- Commands that works only if no context specified. This is :class:`.WCommandContext` object, but with adapter
	that has empty list specification. These are commands, which can be executed at top-level and can't be executed
	inside any context.
	- Commands that works with specific context. Common :class:`.WCommandContext` object
	"""

	@verify_type(command_selector=(WCommandContextSelector, None))
	def __init__(self, command_selector=None):
		""" Create new command set

		:param command_selector: command selector to use
		"""
		if command_selector is None:
			command_selector = WCommandContextSelector()
		WCommandSet.__init__(self, command_selector=command_selector)
		self.__context = None

	def context(self):
		""" Return current context

		:return: WContextProto
		"""
		return self.__context

	@verify_type(command_str=str, request_context=(WContextProto, None))
	def exec_context(self, command_str, request_context=None):
		""" Execute command with context (if specified). If command result will set context, this context will
		be set to this object for future use

		:param command_str: command to execute
		:param request_context: context to use
		:return: WCommandResult
		"""
		command_tokens = WCommandProto.split_command(command_str)
		command_obj = self.commands().select(*command_tokens, request_context=request_context)
		if command_obj is None:
			raise WCommandSet.NoCommandFound('No suitable command found: "%s"' % command_str)

		if isinstance(command_obj, WCommandContext) is True:
			result = command_obj.exec_context(*command_tokens, request_context=request_context)
		else:
			result = command_obj.exec(*command_tokens)

		if isinstance(result, WCommandContextResult) is True:
			self.__context = WContext.import_context(result.context)

		return result
