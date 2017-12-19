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

from wasp_general.verify import verify_type
from wasp_general.command.proto import WCommandResultProto


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

	@classmethod
	def error(cls, message, **command_env):
		return WPlainCommandResult('Error. ' + message, **command_env)


class WExceptionResult(WCommandEnv):

	@verify_type(message=str, exception=Exception)
	def __init__(self, message, exc, traceback, **command_env):
		WCommandEnv.__init__(self, **command_env)
		self.__message = message
		self.__exception = str(exc)
		self.__traceback = traceback

	def message(self):
		return self.__message

	def exception(self):
		return self.__exception

	def traceback(self):
		return self.__traceback

	def __str__(self):
		return (
			'%s\nException was raised. %s\n%s' %
			(self.message(), self.exception(), self.traceback())
		)
