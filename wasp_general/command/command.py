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
from wasp_general.command.proto import WCommandResultProto


class WCommandProto(metaclass=ABCMeta):
	""" Prototype for a single command. Command tokens are string, where each token is a part of the command name or
	is the command parameter. Tokens are generated from a string, each token is separated by space (if space is a
	part of the token, then it must be quoted). Any command may require some additional parameters that are
	generated from environment with which this command will be checked and/or called. This extra parameters
	calls command environment
	"""

	@abstractmethod
	@verify_type(command_tokens=str)
	def match(self, *command_tokens, **command_env):
		""" Checks whether this command can be called with the given tokens. Return True - if tokens match this
		command, False - otherwise

		:param command_tokens: command to check
		:param command_env: command environment
		:return: bool
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(command_tokens=str)
	def exec(self, *command_tokens, **command_env):
		""" Execute valid command (that represent as tokens)

		:param command_tokens: command to execute
		:param command_env: command environment
		:return: WCommandResultProto
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
	def match(self, *command_tokens, **command_env):
		""" :meth:`.WCommandProto.match` implementation
		"""
		command = self.command()
		if len(command_tokens) >= len(command):
			return command_tokens[:len(command)] == command
		return False

	@abstractmethod
	@verify_type('paranoid', command_tokens=str)
	def _exec(self, *command_tokens, **command_env):
		""" Derived classes must implement this function, in order to do a real command work.

		:param command_tokens: command to execute
		:param command_env: command environment
		:return: WCommandResultProto
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(command_tokens=str)
	def exec(self, *command_tokens, **command_env):
		""" :meth:`.WCommandProto.exec` implementation

		(throws RuntimeError if tokens are invalid, and calls :meth:`.WCommand._exec` method)
		"""
		if self.match(*command_tokens, **command_env) is False:
			raise RuntimeError('Command mismatch: %s' % self.join_tokens(*command_tokens))

		return self._exec(*command_tokens, **command_env)


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
	def select(self, *command_tokens, **command_env):
		""" Select suitable command, that matches the given tokens. Each new command to check is fetched with
		this object iterator (:meth:`.WCommandSelector.__iter__`)

		:param command_tokens: command
		:param command_env: command environment
		:return: WCommandProto
		"""
		for command_obj in self:
			if command_obj.match(*command_tokens, **command_env):
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
	""" Class wraps routine of execution command from a command group. This class is able to keep command
	environment variables from previous commands results to use them in a future commands calls. Only
	those variables whose names were specified in a constructor will be kept.
	"""

	class NoCommandFound(Exception):
		""" Exception that is raised when no suitable command was found during :meth:`.WCommandSet.exec` method
		"""
		pass

	@verify_type(command_selector=(WCommandSelector, None), follow_vars=(list, tuple, set, None))
	def __init__(self, command_selector=None, tracked_vars=None):
		""" Create new set

		:param command_selector: selector (storage) for commands to use
		:param tracked_vars: if it is specified - tuple/list/set of variables names, that must be kept \
		between commands calls
		"""
		self.__commands = command_selector if command_selector is not None else WCommandSelector()
		self.__tracked_vars = tuple(tracked_vars) if tracked_vars is not None else tuple()
		self.__vars = {}

	def commands(self):
		""" Return used command selector

		:return: WCommandSelector
		"""
		return self.__commands

	def tracked_vars(self):
		""" Return variables names that are kept (tracked) by this command set

		:return: tuple of str
		"""
		return self.__tracked_vars

	def has_var(self, var_name):
		""" Return True - if a environment variable with a specified name is kept by this command set.
		Otherwise - False is returned

		:param var_name: variable name to check

		:return: bool
		"""
		return var_name in self.__vars.keys()

	def var_value(self, var_name):
		""" Return value of environment variable that is kept by this command set.

		:note: No checks are made if there is a such variable. It implies that there is a such variable.
		For any doubt - use :meth:`.WCommandSet.has_var` method

		:param var_name: target variable name

		:return: anything
		"""
		return self.__vars[var_name]

	@verify_type('paranoid', command_str=str)
	def exec(self, command_str, **command_env):
		""" Execute the given command (command will be split into tokens, every space that is a part of a token
		must be quoted)

		:param command_str: command to execute
		:param command_env: command environment
		:return: WCommandResultProto
		"""
		env = self.__vars.copy()
		env.update(command_env)

		command_tokens = WCommandProto.split_command(command_str)
		command_obj = self.commands().select(*command_tokens, **env)
		if command_obj is None:
			raise WCommandSet.NoCommandFound('No suitable command found: "%s"' % command_str)

		result = command_obj.exec(*command_tokens, **env)
		self.__track_vars(result)
		return result

	@verify_type(command_result=WCommandResultProto)
	def __track_vars(self, command_result):
		""" Check if there are any tracked variable inside the result. And keep them for future use.

		:param command_result: command result tot check

		:return:
		"""
		command_env = command_result.environment()
		for var_name in self.tracked_vars():
			if var_name in command_env.keys():
				self.__vars[var_name] = command_env[var_name]


class WCommandAlias(WCommandProto):
	""" Prototype for command, that doesn't do anything useful itself, but it helps to run a modified command
	and to return its result. For getting any useful result a :class:`.WCommandSelector` object is used.
	"""

	@verify_type(selector=WCommandSelector)
	def __init__(self, selector):
		""" Create new command alias

		:param selector: selector that has commands, that will be run from this one
		"""
		WCommandProto.__init__(self)
		self.__selector = selector

	def selector(self):
		""" Return original command selector

		:return: WCommandSelector
		"""
		return self.__selector

	@abstractmethod
	def mutate_command_tokens(self, *command_tokens):
		""" Modify the input command so it can be called from the command selector

		:param command_tokens:
		:return:
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(command_tokens=str)
	def match(self, *command_tokens, **command_env):
		""" :meth:`.WCommandProto.match` implementation
		"""
		mutated_command_tokens = self.mutate_command_tokens(*command_tokens)
		if mutated_command_tokens is None:
			return False
		return self.selector().select(*mutated_command_tokens, **command_env) is not None

	@verify_type(command_tokens=str)
	def exec(self, *command_tokens, **command_env):
		""" :meth:`.WCommandProto.exec` implementation
		"""
		mutated_command_tokens = self.mutate_command_tokens(*command_tokens)
		if mutated_command_tokens is not None:
			command = self.selector().select(*mutated_command_tokens, **command_env)
			if command is not None:
				return command.exec(*mutated_command_tokens, **command_env)

		raise RuntimeError('Command mismatch: %s' % self.join_tokens(*command_tokens))


class WReduceCommand(WCommandAlias):
	""" Command that creates subsection from a command selector. The command will be matched to command tokens only
	if the first token matches to one of reduce tokens (section name/aliases) and the command selector has command
	for remaining tokens. Command execution works the same way. The command will be executed from the command
	selector without the first token and only if the first token matches to one of reduce tokens.
	"""

	@verify_type('paranoid', selector=WCommandSelector)
	@verify_type(reduce_tokens=str)
	def __init__(self, selector, *reduce_tokens):
		""" Create new command

		:param selector: selector to use
		:param reduce_tokens: section names (aliases)
		"""
		WCommandAlias.__init__(self, selector)
		if len(reduce_tokens) == 0:
			raise RuntimeError('No reduce tokens are specified')
		self.__reduce_tokens = reduce_tokens

	def reduce_tokens(self):
		""" Return section names (aliases)

		:return: tuple of str
		"""
		return self.__reduce_tokens

	def mutate_command_tokens(self, *command_tokens):
		""" :meth:`.WCommandAlias.mutate_command_tokens` implementation
		"""
		if len(command_tokens) > 0:
			if command_tokens[0] in self.reduce_tokens():
				return command_tokens[1:]
