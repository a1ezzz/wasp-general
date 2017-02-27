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
