# -*- coding: utf-8 -*-
# wasp_general/types/bytearray.py
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
from wasp_general.types.binarray import WBinArray


class WFixedSizeByteArray:
	""" This class represent fixed-length byte-array. Where byte is WBinArray. Bytes are ordered as big-endian.
	It means that the most significant byte has index 0.

	see also https://en.wikipedia.org/wiki/Endianness
	"""

	byte_size = 8
	""" Bits in byte. Derived classed can modify this without breaking the code. Derived class can do this,
	but why?!
	"""

	@verify_type(size=int, value=(WBinArray, int, bytes, None))
	@verify_value(size=lambda x: x >= 0)
	def __init__(self, size=0, value=None):
		""" Construct new array.

		:param size: count of bytes
		:param value: value with which this sequence must be initialized (default 0)
		"""
		self.__array = []
		self.__size = size

		for i in range(self.__size):
			self.__array.append(WBinArray(0, self.__class__.byte_size))

		if value is not None:
			if isinstance(value, (WBinArray, int)) is True:
				value = WBinArray(int(value), self.__size * self.__class__.byte_size)
				value = value.split(self.__class__.byte_size)
			else:
				# isinstance(value, bytes)
				if self.__size < len(value):
					raise OverflowError('Value is out of bound')

			for i in range(len(value)):
				self.__array[i] = value[i]

	def bin_value(self):
		""" Return this sequence as single big WBinArray

		:return: WBinArray
		"""
		return WBinArray.join(*self.__array)

	def bin_array(self):
		""" Return this sequence as list of bytes (WBinArray)

		:return: list of WBinArray
		"""
		return self.__array

	def resize(self, size):
		""" Grow this array to specified length. This array can't be shrinked

		:param size: new length
		:return: None
		"""
		if size < len(self):
			raise ValueError("Value is out of bound. Array can't be shrinked")
		current_size = self.__size
		for i in range(size - current_size):
			self.__array.append(WBinArray(0, self.__class__.byte_size))
		self.__size = size

	def __len__(self):
		""" Return count of bytes

		:return: int
		"""
		return self.__size

	def __str__(self):
		""" Convert to string

		:return: str
		"""
		return str([str(x) for x in self.__array])

	def __getitem__(self, item):
		""" Return byte (WBinArray) at specified index

		:param item: item index
		:return: WBinArray
		"""
		return self.__array[item]

	@verify_type('paranoid', value=(WBinArray, int))
	@verify_type(key=int)
	def __setitem__(self, key, value):
		""" Set value for the given index. Specified value must resign within byte capability (must be non
		negative and be less then 2^<byte_size>).

		:param key: item index
		:param value: value to set
		:return: None
		"""
		if key < 0 or key >= len(self):
			raise IndexError('Index out of range')

		self.__array[key] = WBinArray(value, self.__class__.byte_size)

	def __bytes__(self):
		""" Convert to bytes

		:return: bytes
		"""
		return bytes([int(x) for x in self.__array])

	def swipe(self):
		""" Mirror current array value in reverse. Bytes that had greater index will have lesser index, and
		vice-versa. This method doesn't change this array. It creates a new one and return it as a result.

		:return: WFixedSizeByteArray
		"""
		result = WFixedSizeByteArray(len(self))
		for i in range(len(self)):
			result[len(self) - i - 1] = self[i]
		return result
