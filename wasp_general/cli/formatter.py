# -*- coding: utf-8 -*-
# wasp_general/cli/formatter.py
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
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import time
import math

from wasp_general.verify import verify_type

from wasp_general.datetime import local_datetime


def local_datetime_formatter(dt):
	return '%s%s' % (local_datetime(dt=dt).isoformat(), time.strftime('%Z'))


@verify_type(none_value=(str, None))
def na_formatter(value, str_fn=None, none_value=None):
	fn = str_fn if str_fn is not None else str
	return fn(value) if value is not None else (none_value if none_value is not None else '(not available)')


@verify_type(size=int)
def data_size_formatter(size):
	suffixes = ['bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
	suffix_index = int(math.floor(math.log2(size) / 10))
	if suffix_index >= len(suffixes):
		suffix_index = len(suffixes) - 1
	return '{:.2f} {}'.format(size / (1 << (suffix_index * 10)), suffixes[suffix_index])


class WConsoleTableFormatter:

	__default_delimiter__ = '*'

	@verify_type(table_headers=str)
	def __init__(self, *table_headers):
		self.__headers = table_headers
		self.__rows = []

		self.__cells_length = WConsoleTableFormatter.cells_length(*table_headers)

	@staticmethod
	def cells_length(*cells):
		return tuple([len(x) for x in cells])

	def add_row(self, *cells):
		self.__rows.append(cells)
		row_length = WConsoleTableFormatter.cells_length(*cells)

		min_cells, max_cells = row_length, self.__cells_length
		if len(cells) > len(max_cells):
			min_cells, max_cells = max_cells, min_cells

		result = [max(min_cells[i], max_cells[i]) for i in range(len(min_cells))]
		result.extend([max_cells[i] for i in range(len(min_cells), len(max_cells))])
		self.__cells_length = tuple(result)

	def format(self, delimiter=None):
		if delimiter is None:
			delimiter = self.__default_delimiter__

		cell_count = len(self.__cells_length)
		if cell_count == 0:
			raise RuntimeError('Empty table')

		separator_length = ((cell_count - 1) * 3) + 4
		for cell_length_iter in self.__cells_length:
			separator_length += cell_length_iter

		separator = (delimiter * separator_length) + '\n'
		left_border = '%s ' % delimiter
		int_border = ' %s ' % delimiter
		right_border = ' %s\n' % delimiter

		def render_row(*cells):
			row_result = ''
			for i in range(cell_count):
				cell_length = self.__cells_length[i]
				if i < len(cells):
					single_cell = cells[i]
					row_result += single_cell
					delta = (cell_length - len(single_cell))
				else:
					delta = cell_length
				row_result += ' ' * delta

				if i < (cell_count - 1):
					row_result += int_border

			return row_result

		result = separator
		result += left_border
		result += render_row(*self.__headers)
		result += right_border
		result += separator

		for row in self.__rows:
			result += left_border
			result += render_row(*row)
			result += right_border

		result += separator

		return result
