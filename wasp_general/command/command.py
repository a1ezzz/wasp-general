# -*- coding: utf-8 -*-
# wasp_general/command/command.py
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

from abc import ABCMeta, abstractmethod
import shlex

from wasp_general.verify import verify_type


class WCommandResult:
	""" Define result of a command
	"""

	@verify_type(output=(str, None))
	def __init__(self, output=None, error=None):
		""" Create new result. 'error' variable shows whether command was finished successfully. If 'error'
		variable is other than None, then 'error' variable is error code/flag/... and 'output' variable is
		error message.

		:param output: command output
		:param error: error flag
		"""
		self.output = output
		self.error = error


class WCommandProto(metaclass=ABCMeta):
	""" Prototype for a single command. Command tokens are string, where each token is a part of the command name or
	is the command parameter. Tokens are generated from a string, each token is separated by space (if space is a
	part of the token, then it must be quoted).
	"""

	@abstractmethod
	@verify_type(command_tokens=str)
	def match(self, *command_tokens):
		""" Checks whether this command can be called with the given tokens. Return True - if tokens match this
		command, False - otherwise

		:param command_tokens: command to check
		:return: bool
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(command_tokens=str)
	def exec(self, *command_tokens):
		""" Execute valid command (that represent as tokens)

		:param command_tokens: command to execute
		:return: WCommandResult
		"""
		raise NotImplementedError('This method is abstract')

	@staticmethod
	@verify_type(command_str=str)
	def split_command(command_str):
		""" Split command string into command tokens

		:param command_str: command to split
		:return: tuple of str
		"""
		return shlex.split(command_str)

	@staticmethod
	@verify_type(command_tokens=str)
	def join_tokens(*command_tokens):
		""" Join tokens into a single string

		:param command_tokens: tokens to join
		:return: str
		"""
		return ' '.join([shlex.quote(x) for x in command_tokens])


class WCommand(WCommandProto):
	""" Basic WCommandProto implementation
	"""

	@verify_type(command_tokens=str)
	def __init__(self, *command_tokens):
		""" Create new command

		:param command_tokens: tokens (command) that call this command, like 'help' or ('create', 'object')
		"""
		WCommandProto.__init__(self)
		self.__command = tuple(command_tokens)

	def command(self):
		""" Return command tokens

		:return: tuple of str
		"""
		return self.__command

	@verify_type(command_tokens=str)
	def match(self, *command_tokens):
		""" :meth:`.WCommandProto.match` implementation
		"""
		command = self.command()
		if len(command_tokens) >= len(command):
			return command_tokens[:len(command)] == command
		return False

	@abstractmethod
	@verify_type(command_tokens=str)
	def _exec(self, *command_tokens):
		""" Derived classes must implement this function, in order to do a real command work.

		:param command_tokens: command to execute
		:return: WCommandResult
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(command_tokens=str)
	def exec(self, *command_tokens):
		""" :meth:`.WCommandProto.exec` implementation

		(throws RuntimeError if tokens are invalid, and calls :meth:`.WCommand._exec` method)
		"""
		if self.match(*command_tokens) is False:
			raise RuntimeError('Command mismatch: %s' % self.join_tokens(*command_tokens))

		return self._exec(*command_tokens)


class WCommandSelector:
	""" This class store command and selects suitable command for the given tokens.
	"""

	def __init__(self):
		""" Create new storage/selector
		"""
		self.__commands = []

	@verify_type(command_obj=WCommandProto)
	def add(self, command_obj):
		""" Add command to selector

		:param command_obj: command to add
		:return: None
		"""
		self.__commands.append(command_obj)

	@verify_type(command_tokens=str)
	def select(self, *command_tokens):
		""" Select suitable command, that matches the given tokens. Each new command to check is fetched with
		this object iterator (:meth:`.WCommandSelector.__iter__`)

		:param command_tokens: command
		:return: WCommandProto
		"""
		for command_obj in self:
			if command_obj.match(*command_tokens):
				return command_obj

	def __iter__(self):
		""" Iterate over internal storage and yield next command
		"""
		for command in self.__commands:
			yield command

	def __len__(self):
		""" Return command count

		:return: int
		"""
		return len(self.__commands)


class WCommandPrioritizedSelector(WCommandSelector):
	""" This class has priority for every stored commands. Command with lower priority value will be selected first.
	"""

	@verify_type(default_priority=int)
	def __init__(self, default_priority=30):
		""" Create new selector

		:param default_priority: priority for commands, that were added via \
		:meth:`.WCommandPrioritizedSelector.add` method
		"""
		WCommandSelector.__init__(self)
		self.__default_priority = default_priority
		self.__priorities = {}

	@verify_type(command_obj=WCommandProto)
	def add(self, command_obj):
		""" :meth:`.WCommandSelector.add` redefinition (sets default priority for the given command)
		"""
		self.add_prioritized(command_obj, self.__default_priority)

	@verify_type(command_obj=WCommandProto, priority=int)
	def add_prioritized(self, command_obj, priority):
		""" Add command with the specified priority

		:param command_obj: command to add
		:param priority: command priority
		:return: None
		"""
		if priority not in self.__priorities.keys():
			self.__priorities[priority] = []

		self.__priorities[priority].append(command_obj)

	def __iter__(self):
		""" Iterate over internal storage and yield next command. Commands with lower priority will be yielded
		first
		"""
		priorities = list(self.__priorities.keys())
		priorities.sort()

		for priority in priorities:
			for command in self.__priorities[priority]:
				yield command

	def __len__(self):
		""" Return command count

		:return: int
		"""
		result = 0
		for commands in self.__priorities.values():
			result += len(commands)
		return result


class WCommandSet:
	""" Class wraps routine of execution command from a command group
	"""

	class NoCommandFound(Exception):
		""" Exception that is raised when no suitable command was found during :meth:`.WCommandSet.exec` method
		"""
		pass

	@verify_type(command_selector=(WCommandSelector, None))
	def __init__(self, command_selector=None):
		""" Create new set

		:param command_selector:
		"""
		self.__commands = command_selector if command_selector is not None else WCommandSelector()

	def commands(self):
		""" Return used command selector

		:return: WCommandSelector
		"""
		return self.__commands

	@verify_type(command_str=str)
	def exec(self, command_str):
		""" Execute the given command (command will be split into tokens, every space that is a part of a token
		must be quoted)

		:param command_str: command to execute
		:return: WCommandResult
		"""
		command_tokens = WCommandProto.split_command(command_str)
		command_obj = self.commands().select(*command_tokens)
		if command_obj is None:
			raise WCommandSet.NoCommandFound('No suitable command found: "%s"' % command_str)

		return command_obj.exec(*command_tokens)
