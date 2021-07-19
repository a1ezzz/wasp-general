# -*- coding: utf-8 -*-
# wasp_general/api/command/proto.py
#
# Copyright (C) 2017-2019 the wasp-general authors and contributors
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
# TODO: test the code

from abc import ABCMeta, abstractmethod



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



class WCommandResultProto(metaclass=ABCMeta):

	@abstractmethod
	def __str__(self):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def environment(self):
		raise NotImplementedError('This method is abstract')
