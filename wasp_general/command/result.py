# -*- coding: utf-8 -*-
# wasp_general/command/result.py
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
# along with wasp-general. If not, see <http://www.gnu.org/licenses/>.

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod

from wasp_general.command.proto import WCommandResultProto
from wasp_general.verify import verify_type, verify_value


# noinspection PyAbstractClass
class WCommandEnv(WCommandResultProto):

	def __init__(self, **command_env):
		WCommandResultProto.__init__(self)
		self.__command_env = command_env

	def environment(self):
		return self.__command_env.copy()


class WPlainCommandResult(WCommandEnv):

	@verify_type(result=str)
	def __init__(self, result, **command_env):
		WCommandEnv.__init__(self, **command_env)
		self.__result = result

	def __str__(self):
		return self.__result


class WCommandResultEntryProto(metaclass=ABCMeta):

	@verify_type(entry_tag=(str, None))
	@verify_value(entry_tag=lambda x: x is None or len(x) > 0)
	def __init__(self, entry_tag=None):
		self.__entry_tag = entry_tag

	@abstractmethod
	def __str__(self):
		raise NotImplementedError('This method is abstract')

	def entry_tag(self):
		return self.__entry_tag


class WCommandResultEntry(WCommandResultEntryProto):

	@verify_type('paranoid', entry_tag=(str, None))
	@verify_value('paranoid', entry_tag=lambda x: x is None or len(x) > 0)
	@verify_type(result=str)
	def __init__(self, result, entry_tag=None):
		WCommandResultEntryProto.__init__(self, entry_tag=entry_tag)
		self.__result = result

	def __str__(self):
		return self.__result


class WDetailedCommandResult(WCommandEnv):

	__default_joining_str__ = '\n'

	@verify_type(entries=(str, WCommandResultEntryProto))
	def __init__(self, *entries, **command_env):
		WCommandEnv.__init__(self, **command_env)
		self.__entries = []
		for entry in entries:
			if isinstance(entry, str) is True:
				entry = WCommandResultEntry(entry)
			self.__entries.append(entry)

	def entries(self):
		return self.__entries

	def join_by(self):
		return self.__default_joining_str__

	def __str__(self):
		return self.join_by().join([str(x) for x in self.__entries])
