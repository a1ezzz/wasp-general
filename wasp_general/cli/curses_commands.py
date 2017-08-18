# -*- coding: utf-8 -*-
# wasp_general/cli/curses_commands.py
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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from wasp_general.verify import verify_type
from wasp_general.command.command import WCommand, WCommandResult
from wasp_general.cli.curses import WCursesConsole


class WExitCommand(WCommand):

	@verify_type(console=WCursesConsole)
	def __init__(self, console):
		WCommand.__init__(self)
		self.__console = console

	def console(self):
		return self.__console

	@verify_type('paranoid', command_tokens=str)
	def match(self, *command_tokens, **command_env):
		return command_tokens == ('exit',) or command_tokens == ('quit',)

	@verify_type('paranoid', command_tokens=str)
	def _exec(self, *command_tokens, **command_env):
		self.__console.stop()
		return WCommandResult('Exiting...')


class WEmptyCommand(WCommand):

	@verify_type('paranoid', command_tokens=str)
	def match(self, *command_tokens, **command_env):
		return len(command_tokens) == 0

	@verify_type('paranoid', command_tokens=str)
	def _exec(self, *command_tokens, **command_env):
		return WCommandResult()
