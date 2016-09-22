# -*- coding: utf-8 -*-
# wasp_general/types/binarray.py
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

from wasp_general.verify import verify_type, verify_value


class WBinArray:
	""" This type represent sequence of bit. Bits are ordered as MSB does (most significant bit has index 0).
	If size is specified, then array became fixed-length array. All actions beyond the limit will be omitted or
	exception will be raised.

	see also https://en.wikipedia.org/wiki/Bit_numbering
	"""

	@verify_type(size=(int, None))
	@verify_value(value=lambda x: int(x) >= 0, size=lambda x: x is None or x >= 0)
	def __init__(self, value=0, size=None):
		""" Create new bit sequence.

		:param value: value with which this sequence must be initialized.
		:param size: sequence fixed size (number of bits).
		"""
		if isinstance(value, (int, WBinArray)) is False:
			raise TypeError('Invalid array type')
		self.__value = int(value)
		self.__size = size
		if self.__size is not None:
			if self.__value > ((2 ** self.__size) - 1):
				raise ValueError('Value is out of bound')

	def __len__(self):
		""" Return size if array has fixed size, otherwise return bits count

		:return: int
		"""
		if self.__size is not None:
			return self.__size
		elif self.__value == 0:
			return 1
		else:
			return self.__value.bit_length()

	@verify_type(item=(int, slice))
	def __getitem__(self, item):
		""" Return bit value for specified index or array part defined by the slice

		:param item: index or slice object
		:return: int for single item, WBinArray for slice
		"""
		if isinstance(item, int):
			if item >= self.__len__() or item < 0:
				raise IndexError('Index out of range')
			mask = 1 << (len(self) - item - 1)
			return 1 if (self.__value & mask) > 0 else 0
		else:
			# isinstance(item, slice):
			start = item.start if item.start is not None else 0
			if start > len(self):
				raise IndexError('Index out of range')

			stop = item.stop if item.stop is not None else len(self)
			stop = stop if stop <= len(self) else len(self)

			step = item.step if item.step is not None else 1

			iterator = range(start, stop, step)
			result = WBinArray(0, len(iterator))
			for key in iterator:
				result[key - start] = self[key]

			return result

	@verify_type(key=int)
	@verify_value(value=lambda x: int(x) >= 0)
	def __setitem__(self, key, value):
		""" Set value for the given index. If value is greater then 1 or value is a WBinArray with length
		greater then 1, then all the bits are copied from original value to this array starting by the key
		index.

		:param key: starting position
		:param value: value to set
		:return: None
		"""

		if isinstance(value, (int, WBinArray)) is False:
			raise TypeError('Invalid type for value')
		value = int(value)

		if self.__size is not None:
			if key < 0 or key >= len(self):
				raise IndexError('Index out of range')
			length = len(WBinArray(value))
			if (key + length - 1) >= len(self):
				raise OverflowError('Value is bigger then array')

		if value == 0:
			mask = ~(1 << (len(self) - key - 1))
			self.__value = (self.__value & mask)
		else:
			# value > 0
			mask = (1 << (len(self) - key - 1))
			self.__value = (self.__value | mask)

	def __int__(self):
		""" Convert to integer

		:return: int
		"""
		if self.__size is None:
			return self.__value
		else:
			mask = ((2 ** self.__size) - 1)
			return self.__value & mask

	def __str__(self):
		""" Convert to string

		:return: str
		"""
		format_str = "{:0%ib}" % len(self)
		return format_str.format(self.__int__())

	def __add__(self, other):
		""" Return addition of two objects

		:param other: second summand
		:return: int
		"""
		return self.__int__() + other.__int__()

	def __sub__(self, other):
		""" Return subtraction of two objects

		:param other: subtrahend
		:return: int
		"""
		return self.__int__() - other.__int__()

	@verify_type(size=(int, None))
	@verify_value(size=lambda x: x >= 0)
	def resize(self, size):
		""" Resize current array. If size is None, then array became nonfixed-length array. If new size is
		less then current size and value, then value will be truncated (lesser significant bits will be
		truncated).

		:param size:
		:return:
		"""
		if size is not None:
			self.__value = int(WBinArray(self.__value)[:size])
		self.__size = size

	@verify_type(bits_count=int)
	@verify_value(bits_count=lambda x: x > 0)
	def split(self, bits_count):
		""" Split array into smaller parts. Each small array is fixed-length WBinArray (length of that array is
		bits_count).

		:param bits_count: array length
		:return: list of WBinArray
		"""
		result = []
		array = WBinArray(self.__value, self.__size)

		if (len(array) % bits_count) > 0:
			array.resize(len(array) + (bits_count - (len(array) % bits_count)))

		while len(array):
			result.append(WBinArray(array[:bits_count], bits_count))
			array = array[bits_count:]
		return result

	def concat(self, array):
		""" Return new fixed-length array, that is made by creating new array with length of sum of two arrays
		(this array and the given one). In newly created array the most significant bit of the given array
		will have an index lesser then an index of the least significant bit of this array.

		:param array: array to concatenate with
		:return: WBinArray
		"""
		if isinstance(array, WBinArray) is False:
			raise TypeError('Invalid array type')
		value = ((int(self) << len(array)) | int(array))
		return WBinArray(value, len(self) + len(array))

	def rconcat(self, array):
		""" 'Reverse' concatenation. Works the same as :meth:`.WBinArray.concat`, but in newly created array
		the most significant bit of the given array will have an index greater then an index of the least
		significant bit of this array

		:param array: array to concatenate with
		:return: WBinArray
		"""
		if isinstance(array, WBinArray) is False:
			raise TypeError('Invalid array type')
		return array.concat(self)

	def extend(self, *array_list):
		""" Concatenate this array with the given arrays. This method doesn't modify current array. Instead,
		it creates new one, that have all of arrays. (see :meth:`.WBinArray.concat` method)

		:param array_list: list of WBinArray
		:return: newly created WBinArray
		"""
		result = WBinArray(int(self), len(self))
		for array in array_list:
			result = result.concat(array)
		return result

	def swipe(self):
		""" Mirror current array value in reverse. Bits that had greater index will have lesser index, and
		vice-versa. This method doesn't change this array. It creates a new one and return it as a result.

		:return: WBinArray
		"""
		result = WBinArray(0, len(self))
		for i in range(len(self)):
			result[len(self) - i - 1] = self[i]
		return result

	@staticmethod
	def join(*args):
		""" Concatenate all of the given arrays. (see :meth:`.WBinArray.concat` method)

		:param args: list of WBinArray
		:return: WBinArray
		"""
		if len(args) == 0:
			return

		result = WBinArray(int(args[0]), len(args[0]))
		if len(args) == 1:
			return result
		else:
			result = result.extend(*(args[1:]))
		return result
