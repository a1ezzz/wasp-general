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

