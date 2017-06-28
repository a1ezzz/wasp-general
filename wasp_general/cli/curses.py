# -*- coding: utf-8 -*-
# wasp_general/cli/curses.py
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

from abc import ABCMeta, abstractmethod
import curses

from wasp_general.verify import verify_type
from wasp_general.cli.cli import WConsoleWindowProto, WConsoleProto, WConsoleBase, WConsoleWindowBase
from wasp_general.cli.cli import WConsoleDrawerProto
from wasp_general.command.command import WCommandSet


class WCursesWindow(WConsoleWindowBase):

	class EmptyWindowDrawer(WConsoleDrawerProto):
		""" WConsoleWindowProto.DrawerProto implementation. Suites if there is nothing to display
		"""

		@verify_type('paranoid', window=WConsoleWindowProto, prompt_show=bool)
		def suitable(self, window, prompt_show=True):
			""" :meth:`WConsoleWindowProto.DrawerProto.suitable` method implementation
			"""
			if len(window.list_data(previous_data=True, console_row=True)) == 0:
				return True
			return False

		@verify_type('paranoid', window=WConsoleWindowProto, prompt_show=bool)
		def draw(self, window, prompt_show=True):
			""" :meth:`WConsoleWindowProto.DrawerProto.draw` method implementation
			"""
			window.set_cursor(0, 0)

	class SmallWindowDrawer(WConsoleDrawerProto):
		""" WConsoleWindowProto.DrawerProto implementation. Suites if there is content and content fits window
		width and height
		"""

		@verify_type('paranoid', window=WConsoleWindowProto, prompt_show=bool)
		def suitable(self, window, prompt_show=True):
			""" :meth:`WConsoleWindowProto.DrawerProto.suitable` method implementation
			"""
			if prompt_show is True:
				lines = len(window.list_data(previous_data=True, console_row=True))
			else:
				lines = len(window.list_data(previous_data=True))

			if 1 <= lines < (window.height() - 1):
				return True

			return False

		@verify_type('paranoid', window=WConsoleWindowProto, prompt_show=bool)
		def draw(self, window, prompt_show=True):
			""" :meth:`WConsoleWindowProto.DrawerProto.draw` method implementation
			"""
			if prompt_show is True:
				data_lines = window.list_data(previous_data=True, console_row=True)
			else:
				data_lines = window.list_data(previous_data=True)

			window.write_data(data_lines)

			if prompt_show is True:
				data_lines_to_cursor = window.list_data(
					previous_data=True, console_row_to_cursor=True
				)
				y = len(data_lines_to_cursor) - 1

				line_length = len(window.console().prompt()) + window.cursor()
				row_lines_to_cursor = window.list_data(console_row_to_cursor=True)
				line_length += (len(row_lines_to_cursor) - 1)  # append one char offset
				x = line_length % window.width()
			else:
				y = 0
				x = 0

			window.set_cursor(y, x)

	class ScrolledWindowDrawer(WConsoleDrawerProto):
		""" WConsoleWindowProto.DrawerProto implementation. Suites if content doesn't fit window width and
		height but current row fits
		"""

		@verify_type('paranoid', window=WConsoleWindowProto, prompt_show=bool)
		def suitable(self, window, prompt_show=True):
			""" :meth:`WConsoleWindowProto.DrawerProto.suitable` method implementation
			"""
			height = window.height()

			if prompt_show is True:
				lines = len(window.list_data(previous_data=True, console_row=True))
				console_row_lines = len(window.list_data(console_row=True))
				if (lines >= (height - 1)) and (console_row_lines < (height - 1)):
					return True
			else:
				lines = len(window.list_data(previous_data=True))
				if lines >= (height - 1):
					return True

			return False

		@verify_type('paranoid', window=WConsoleWindowProto, prompt_show=bool)
		def draw(self, window, prompt_show=True):
			""" :meth:`WConsoleWindowProto.DrawerProto.draw` method implementation
			"""
			height = window.height()
			if prompt_show is True:
				console_row_lines = window.list_data(console_row=True)
			else:
				console_row_lines = []

			delta = (height - (len(console_row_lines) + 1))
			previous_data = window.list_data(previous_data=True)
			delta_data = previous_data[(len(previous_data) - delta):]

			window.write_data(delta_data + console_row_lines)

			if prompt_show is True:
				lines_to_cursor = window.list_data(console_row_to_cursor=True)
				y = len(lines_to_cursor) - 1 + delta

				line_length = len(window.console().prompt()) + window.cursor()
				line_length += (len(lines_to_cursor) - 1)  # append one char offset
				x = line_length % window.width()
			else:
				y = 0
				x = 0

			window.set_cursor(y, x)

	class BigWindowDrawer(WConsoleDrawerProto):
		""" WConsoleWindowProto.DrawerProto implementation. Suites if content and even current row doesn't fit
		window width and height
		"""

		@verify_type('paranoid', window=WConsoleWindowProto, prompt_show=bool)
		def suitable(self, window, prompt_show=True):
			""" :meth:`WConsoleWindowProto.DrawerProto.suitable` method implementation
			"""
			if prompt_show is True:
				console_row_lines = len(window.list_data(console_row=True))
				if console_row_lines >= (window.height() - 1):
					return True
			return False

		@verify_type('paranoid', window=WConsoleWindowProto, prompt_show=bool)
		def draw(self, window, prompt_show=True):
			""" :meth:`WConsoleWindowProto.DrawerProto.draw` method implementation
			"""
			assert(prompt_show is True)

			height = window.height()
			lines = window.list_data(console_row=True)
			lines_to_cursor = window.list_data(console_row_to_cursor=True)
			lines_from_cursor = window.list_data(console_row_from_cursor=True)

			output_lines = []
			if len(lines_from_cursor) == 0:
				start = len(lines) - (height - 1)
				output_lines.extend(lines[start:])
				y = height - 2
			elif len(lines_from_cursor) < (height - 1):
				start = (len(lines)) - (height - 1) - (len(lines_from_cursor) - 1)
				output_lines.extend(lines[start:start + (height - 1)])
				y = (height - 1) - (len(lines) - len(lines_to_cursor)) - 1
			else:
				start = 0
				if len(lines_to_cursor) > 0:
					start = len(lines_to_cursor) - 1
				output_lines.extend(lines[start:(start + (height - 1))])
				y = 0

			window.write_data(output_lines)

			line_length = len(window.console().prompt()) + window.cursor()
			line_length += (len(lines_to_cursor) - 1)  # append one char offset
			x = line_length % window.width()
			window.set_cursor(y, x)

	@verify_type('paranoid', console=WConsoleProto)
	def __init__(self, console):
		WConsoleWindowBase.__init__(
			self, console, WCursesWindow.EmptyWindowDrawer(), WCursesWindow.SmallWindowDrawer(),
			WCursesWindow.ScrolledWindowDrawer(), WCursesWindow.BigWindowDrawer()
		)

	def width(self):
		return self.console().screen().getmaxyx()[1]

	def height(self):
		return self.console().screen().getmaxyx()[0]

	def clear(self):
		return self.console().screen().erase()

	def write_line(self, line_index, line):
		self.console().screen().addstr(line_index, 0, line)

	@verify_type('paranoid', prompt_show=bool)
	def refresh(self, prompt_show=True):
		WConsoleWindowBase.refresh(self, prompt_show=prompt_show)
		self.console().screen().refresh()

	def set_cursor(self, y, x):
		self.console().screen().move(y, x)


class WCursesKeyAction(metaclass=ABCMeta):

	def __init__(self, key):
		self.key = key

	@abstractmethod
	def action(self, console_meta):
		raise NotImplementedError('This method is abstract')

	def __call__(self, key, console_meta):
		if self.key == key:
			self.action(console_meta)


class WCursesKeyUp(WCursesKeyAction):

	def __init__(self):
		WCursesKeyAction.__init__(self, curses.KEY_UP)

	def action(self, console_meta):

		history = console_meta.history()
		if history.size() == 0:
			return

		if not console_meta.history_mode():
			console_meta.history_mode(True)
			history.position(history.size() - 1)
			console_meta.window().cursor(len(console_meta.row()))
		elif history.position() > 0:
			history.position(history.position() - 1)
			console_meta.window().cursor(len(console_meta.row()))
		else:
			return

		console_meta.refresh_window()


class WCursesKeyDown(WCursesKeyAction):

	def __init__(self):
		WCursesKeyAction.__init__(self, curses.KEY_DOWN)

	def action(self, console_meta):

		if not console_meta.history_mode():
			return

		history = console_meta.history()
		history_size = history.size()
		if history.position() < (history_size - 1):
			history.position(history.position() + 1)
			console_meta.window().cursor(len(console_meta.row()))
		else:
			console_meta.history_mode(False)
			console_meta.window().cursor(len(console_meta.row()))

		console_meta.refresh_window()


class WCursesKeyLeft(WCursesKeyAction):

	def __init__(self):
		WCursesKeyAction.__init__(self, curses.KEY_LEFT)

	def action(self, console_meta):
		cursor_position = console_meta.window().cursor()
		if cursor_position > 0 and len(console_meta.row()):
			cursor_position -= 1
			console_meta.window().cursor(cursor_position)
			console_meta.refresh_window()


class WCursesKeyRight(WCursesKeyAction):

	def __init__(self):
		WCursesKeyAction.__init__(self, curses.KEY_RIGHT)

	def action(self, console_meta):
		cursor_position = console_meta.window().cursor()
		if cursor_position < len(console_meta.row()):
			cursor_position += 1
			console_meta.window().cursor(cursor_position)
			console_meta.refresh_window()


class WCursesKeyBackspace(WCursesKeyAction):

	def __init__(self):
		WCursesKeyAction.__init__(self, curses.KEY_BACKSPACE)

	def action(self, console_meta):
		position = console_meta.window().cursor()

		command = console_meta.row()
		if 0 < position <= len(command):
			command = command[:(position - 1)] + command[position:]
			console_meta.window().cursor(position - 1)
			console_meta.update_row(command)
		console_meta.refresh_window()


class WCursesKeyDelete(WCursesKeyAction):

	def __init__(self):
		WCursesKeyAction.__init__(self, curses.KEY_DC)

	def action(self, console_meta):
		position = console_meta.window().cursor()
		command = console_meta.row()
		if 0 <= position < len(command):
			command = command[:position] + command[(position + 1):]
			console_meta.update_row(command)
		console_meta.refresh_window()


class WCursesKeyResize(WCursesKeyAction):

	def __init__(self):
		WCursesKeyAction.__init__(self, curses.KEY_RESIZE)

	def action(self, console_meta):
		console_meta.refresh_window()


class WCursesConsole(WConsoleBase):

	@verify_type('paranoid', command_set=(WCommandSet, None))
	def __init__(self, command_set=None):
		WConsoleBase.__init__(self, command_set=command_set)

		self.__screen = curses.initscr()
		self.__screen.keypad(True)
		self.__window = WCursesWindow(self)
		self.__key_actions = [
			WCursesKeyUp(), WCursesKeyDown(), WCursesKeyLeft(), WCursesKeyRight(), WCursesKeyBackspace(),
			WCursesKeyDelete(), WCursesKeyResize()
		]

		self.__stop_flag = True

	def window(self):
		return self.__window

	def screen(self):
		return self.__screen

	def stop(self):
		self.__stop_flag = True

	def start(self):

		self.__stop_flag = False
		while self.__stop_flag is False:
			self.start_session()

			while True:
				pressed_key = self.screen().get_wch()

				if isinstance(pressed_key, str):
					if pressed_key == '\n':
						break

					command = self.row()
					position = self.window().cursor()
					command = command[:position] + pressed_key + command[position:]
					self.update_row(command)
					self.window().cursor(position + 1)
					self.refresh_window()

				elif isinstance(pressed_key, int):
					for action in self.__key_actions:
						action(pressed_key, self)

			self.fin_session()

	def __del__(self):
		curses.endwin()
