# -*- coding: utf-8 -*-
# wasp_general/cli.py
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
from copy import deepcopy
import re

from wasp_general.verify import verify_type, verify_value


class WConsoleHistory:
	""" Simple console history implementation
	"""
	def __init__(self):
		self.__history = []
		self.__history_position = None

	def size(self):
		""" Returns history entries count

		:return: int
		"""
		return len(self.__history)

	@verify_type(pos=(int, None))
	@verify_value(pos=lambda x: x is None or x >= 0)
	def position(self, pos=None):
		""" Get current and/or set history cursor position

		:param pos: if value is not None, then current position is set to pos and new value is returned

		:return: int or None (if position have never been changed)
		"""
		if pos is not None:
			if pos >= len(self.__history):
				raise IndexError('History position is out of bound')
			self.__history_position = pos
		return self.__history_position

	@verify_type(value=str)
	def add(self, value):
		""" Add new record to history. Record will be added to the end

		:param value: new record
		:return: int record position in history
		"""
		index = len(self.__history)
		self.__history.append(value)
		return index

	@verify_type(position=int)
	def entry(self, position):
		""" Get record from history by record position

		:param position: record position
		:return: str
		"""
		return self.__history[position]

	def update(self, value, position):
		""" Change record in this history

		:param value: new record to save
		:param position: record position to change
		:return: None
		"""
		self.__history[position] = value


class WConsoleProto(metaclass=ABCMeta):
	""" Basic class for console implementation. It has non-changeable and changeable history
	(:class:`.WConsoleHistory`). One stores previous entered rows, other one helps to entered new row by editing previous one.
	"""

	def __init__(self):
		self.__history_mode = False
		self.__history = WConsoleHistory()
		self.__editable_history = None
		self.__current_row = None

	def history(self):
		""" Return changeable history

		:return: WConsoleHistory or None
		"""
		return self.__editable_history

	@verify_type(mode_value=(bool, None))
	def history_mode(self, mode_value=None):
		""" Get and/or set current history mode.

		History mode defines what row will be changed with :meth:`.WConsoleProto.update_row` or can be got by
		:meth:`.WConsoleProto.row` call. If history mode disabled, then :meth:`.WConsoleProto.update_row` and
		:meth:`.WConsoleProto.row` affects current row prompt. If history mode is enabled, then
		:meth:`.WConsoleProto.update_row` and :meth:`.WConsoleProto.row` affects current entry in
		history :class:`.WConsoleHistory` (entry at :meth:`.WConsoleHistory.position`)

		History mode is turned off by default.

		:param mode_value: True value enables history mode. False - disables. None - do nothing
		:return: bool
		"""
		if mode_value is not None:
			self.__history_mode = mode_value
		return self.__history_mode

	def start_session(self):
		""" Start new session and prepare environment for new row editing process

		:return: None
		"""
		self.__current_row = ''
		self.__history_mode = False
		self.__editable_history = deepcopy(self.__history)
		self.refresh_window()

	def fin_session(self):
		""" Finalize current session

		:return: None
		"""
		self.__history.add(self.row())
		self.exec(self.row())

	@verify_type(value=str)
	def update_row(self, value):
		""" Change row

		:param value: new row
		:return: None
		"""
		if not self.__history_mode:
			self.__current_row = value
		else:
			self.history().update(value, self.history().position())

	def row(self):
		""" Get row

		:return: str
		"""
		if not self.__history_mode:
			return self.__current_row
		else:
			return self.history().entry(self.history().position())

	@abstractmethod
	def prompt(self):
		""" Return prompt, that would be printed before row. Prompt length must be the same
		within every session

		:return: str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def refresh_window(self):
		""" Refresh current screen. Simple clear and redraw should work

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(row=str)
	def exec(self, row):
		""" Must execute given command

		:param row: command to execute
		:return: None
		"""
		raise NotImplementedError('This method is abstract')


class WConsoleWindowProto(metaclass=ABCMeta):
	""" Basic class for console window implementation
	"""

	class DrawerProto(metaclass=ABCMeta):
		""" Basic class that helps displaying console content
		"""

		@abstractmethod
		@verify_type(window=WConsoleWindowProto)
		def suitable(self, window):
			""" Check if this class can display console content

			:param window: window that should be drawn
			:return: bool (True if this class can draw console content, False - if it can not)
			"""
			raise NotImplementedError()

		@abstractmethod
		@verify_type(window=WConsoleWindowProto)
		def draw(self, window):
			""" Display console content on console window

			:param window: windows to draw
			:return: None
			"""
			raise NotImplementedError()

	@verify_type(console=WConsoleProto, drawers=DrawerProto)
	def __init__(self, console, *drawers):
		""" Create new console window

		:param console: console, that this window is linked to
		:param drawers: drawers to use
		"""
		self.__console = console
		self.__previous_data = ''
		self.__cursor_position = 0
		self.__drawers = []
		self.__drawers.extend(drawers)

		if self.width() < 2:
			raise RuntimeError('Invalid width. Minimum windows width is 2')

		if self.height() < 2:
			raise RuntimeError('Invalid height. Minimum windows height is 2')

	@abstractmethod
	def width(self):
		""" Get window width. If windows width was changed - window must be refreshed via
		:meth:`.WConsoleWindowProto.refresh`

		:return: int
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def height(self):
		""" Get window height. If windows height was changed - window must be refreshed via
		:meth:`.WConsoleWindowProto.refresh`

		:return: int
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def clear(self):
		""" Clear window and remove every symbol it has

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(line_index=int, line=str)
	@verify_value(line_index=lambda x: x >= 0)
	def write_line(self, line_index, line):
		""" Write string on specified line

		:param line_index: line index to display
		:param line: string to display (must fit windows width)
		:return:
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(y=int, x=int)
	@verify_value(x=lambda x: x >= 0, y=lambda x: x >= 0)
	def set_cursor(self, y, x):
		""" Set input cursor in window to specified coordinates. 0, 0 - is top left coordinates

		:param y: vertical coordinates, 0 - top, bottom - positive value
		:param x: horizontal coordinates, 0 - left, right - positive value
		:return:
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(previous_data=bool, prompt=bool, console_row=bool, console_row_to_cursor=bool)
	@verify_type(console_row_from_cursor=bool)
	def data(
		self, previous_data=False, prompt=False, console_row=False,
		console_row_to_cursor=False, console_row_from_cursor=False
	):
		""" Return output data. Flags specifies what data to append. If no flags was specified
		nul-length string returned

		:param previous_data: If True, then previous output appends
		:param prompt: If True, then console prompt appends. If console_row or console_row_to_cursor is True, \
		then this value is omitted
		:param console_row: If True, then console prompt and current input appends.
		:param console_row_to_cursor: If True, then console prompt and current input till cursor appends.
		If console_row is True, then this value is omitted
		:param console_row_from_cursor: If True, then current input from cursor appends.
		If console_row is True, then this value is omitted
		:return: str
		"""

		result = ''

		if previous_data:
			result += self.__previous_data

		if prompt or console_row or console_row_to_cursor:
			result += self.console().prompt()

		if console_row or (console_row_from_cursor and console_row_to_cursor):
			result += self.console().row()
		elif console_row_to_cursor:
			result += self.console().row()[:self.cursor()]
		elif console_row_from_cursor:
			result += self.console().row()[self.cursor():]

		return result

	@verify_type(previous_data=bool, prompt=bool, console_row=bool, console_row_to_cursor=bool)
	@verify_type(console_row_from_cursor=bool)
	def list_data(
		self, previous_data=False, prompt=False, console_row=False,
		console_row_to_cursor=False, console_row_from_cursor=False
	):
		""" Return list of strings. Where each string is fitted to windows width. Parameters are the same as
		they are in :meth:`.WConsoleWindow.data` method

		:return: list of str
		"""
		return self.split(self.data(
			previous_data, prompt, console_row, console_row_to_cursor, console_row_from_cursor
		))

	def console(self):
		""" Return linked console

		:return: WConsoleProto
		"""
		return self.__console

	@verify_type(data=list, start_position=int)
	@verify_value(start_position=lambda x: x >= 0)
	def write_data(self, data, start_position=0):
		""" Write data from the specified line

		:param data: string to write, each one on new line
		:param start_position: starting line
		:return:
		"""
		if len(data) > self.height():
			raise ValueError('data too long (too many strings)')

		for i in range(len(data)):
			self.write_line(start_position + i, data[i])

	@verify_type(pos=(None, int))
	@verify_value(pos=lambda x: x is None or x >= 0)
	def cursor(self, pos=None):
		""" Set and/or get relative cursor position. Defines cursor position in current input row.

		:param pos: if value is not None, then current cursor position is set to this value and the same value
		is returned
		:return: int
		"""
		if pos is not None:
			self.__cursor_position = pos

		return self.__cursor_position

	def refresh(self):
		""" Refresh current window. Clear current window and redraw it with one of drawers

		:return: None
		"""
		self.clear()
		for drawer in self.__drawers:
			if drawer.suitable(self):
				drawer.draw(self)
				return

		raise RuntimeError('No suitable drawer was found')

	def commit(self):
		""" Store current input row. Keep current input row as previous output

		:return: None
		"""
		self.__previous_data += (self.data(console_row=True) + '\n')

	@verify_type(data=str)
	def split(self, data):
		""" Split data into list of string, each (self.width() - 1) length or less. If nul-length string
		specified then empty list is returned

		:param data: data to split
		:return: list of str
		"""
		line = deepcopy(data)
		line_width = (self.width() - 1)

		lines = []
		while len(line):

			new_line = line[:line_width]

			new_line_pos = new_line.find('\n')
			if new_line_pos >= 0:
				new_line = line[:new_line_pos]
				line = line[(new_line_pos + 1):]
			else:
				line = line[line_width:]

			lines.append(new_line)

		return lines

	@verify_type(feedback=str, cr=bool)
	def write_feedback(self, feedback, cr=True):
		""" Store feedback. Keep specified feedback as previous output

		:param feedback: data to store
		:param cr: whether to write carriage return to the end or not
		:return: None
		"""
		self.__previous_data += feedback
		if cr is True:
			self.__previous_data += '\n'


class WCursesWindow(WConsoleWindowProto):

	class EmptyWindowDrawer(WConsoleWindowProto.DrawerProto):
		""" WConsoleWindowProto.DrawerProto implementation. Suites if there is nothing to display
		"""

		@verify_type(window=WConsoleWindowProto)
		def suitable(self, window):
			""" :meth:`WConsoleWindowProto.DrawerProto.suitable` method implementation
			"""
			if len(window.splitted_data(previous_data=True, console_row=True)) == 0:
				return True
			return False

		@verify_type(window=WConsoleWindowProto)
		def draw(self, window):
			""" :meth:`WConsoleWindowProto.DrawerProto.draw` method implementation
			"""
			window.set_cursor(0, 0)


	class SmallWindowDrawer(WConsoleWindowProto.DrawerProto):
		""" WConsoleWindowProto.DrawerProto implementation. Suites if there is content and content fits window
		width and height
		"""

		@verify_type(window=WConsoleWindowProto)
		def suitable(self, window):
			""" :meth:`WConsoleWindowProto.DrawerProto.suitable` method implementation
			"""
			lines = len(window.splitted_data(previous_data=True, console_row=True))
			if lines >= 1 and lines < (window.height() - 1):
				return True

			return False

		@verify_type(window=WConsoleWindowProto)
		def draw(self, window):
			""" :meth:`WConsoleWindowProto.DrawerProto.draw` method implementation
			"""
			data_lines = window.splitted_data(previous_data=True, console_row=True)
			window.write_data(data_lines)

			data_lines_to_cursor = window.splitted_data(
				previous_data=True, console_row_to_cursor=True
			)
			y = len(data_lines_to_cursor) - 1

			line_length = len(window.console().prompt()) + window.cursor()
			row_lines_to_cursor = window.splitted_data(console_row_to_cursor=True)
			line_length += (len(row_lines_to_cursor) - 1)  # append one char offset
			x = line_length % window.width()

			window.set_cursor(y, x)


	class ScrolledWindowDrawer(WConsoleWindowProto.DrawerProto):
		""" WConsoleWindowProto.DrawerProto implementation. Suites if content doesn't fit window width and
		height but current row fits
		"""

		@verify_type(window=WConsoleWindowProto)
		def suitable(self, window):
			""" :meth:`WConsoleWindowProto.DrawerProto.suitable` method implementation
			"""
			'''
			@brief WindowDrawer.suitable method implementation
			'''
			height = window.height()
			lines = len(window.splitted_data(previous_data=True, console_row=True))
			console_row_lines = len(window.splitted_data(console_row=True))
			if (lines >= (height - 1)) and (console_row_lines < (height - 1)):
				return True

			return False

		@verify_type(window=WConsoleWindowProto)
		def draw(self, window):
			""" :meth:`WConsoleWindowProto.DrawerProto.draw` method implementation
			"""
			height = window.height()
			console_row_lines = window.splitted_data(console_row=True)

			delta = (height - (len(console_row_lines) + 1))
			previous_data = window.splitted_data(previous_data=True)
			delta_data = previous_data[(len(previous_data) - delta):]

			window.write_data(delta_data + console_row_lines)

			lines_to_cursor = window.splitted_data(console_row_to_cursor=True)
			y = len(lines_to_cursor) - 1 + delta

			line_length = len(window.console().prompt()) + window.cursor()
			line_length += (len(lines_to_cursor) - 1)  # append one char offset
			x = line_length % window.width()

			window.set_cursor(y, x)


	class BigWindowDrawer(WConsoleWindowProto.DrawerProto):
		""" WConsoleWindowProto.DrawerProto implementation. Suites if content and even current row doesn't fit
		window width and height
		"""

		@verify_type(window=WConsoleWindowProto)
		def suitable(self, window):
			""" :meth:`WConsoleWindowProto.DrawerProto.suitable` method implementation
			"""
			console_row_lines = len(window.splitted_data(console_row=True))
			if console_row_lines >= (window.height() - 1):
				return True
			return False

		@verify_type(window=WConsoleWindowProto)
		def draw(self, window):
			""" :meth:`WConsoleWindowProto.DrawerProto.draw` method implementation
			"""
			height = window.height()
			lines = window.splitted_data(console_row=True)
			lines_to_cursor = window.splitted_data(console_row_to_cursor=True)
			lines_from_cursor = window.splitted_data(console_row_from_cursor=True)

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

	@verify_type(console=WConsoleProto)
	def __init__(self, console, nc_screen):
		WConsoleWindowProto.__init__(
			self, console, WCursesWindow.EmptyWindowDrawer(), WCursesWindow.SmallWindowDrawer(),
			WCursesWindow.ScrolledWindowDrawer(), WCursesWindow.BigWindowDrawer()
		)
		self.__nc_screen = nc_screen

	def screen(self):
		return self.__nc_screen

	def width(self):
		return self.screen().getmaxyx()[1]

	def height(self):
		return self.screen().getmaxyx()[0]

	def clear(self):
		return self.screen().erase()

	def write_line(self, line_index, line):
		self.screen().addstr(line_index, 0, line)

	def refresh_window(self):
		WConsoleWindowProto.refresh(self)
		self.screen().refresh()

	def set_cursor(self, y, x):
		self.screen().move(y, x)
