# -*- coding: utf-8 -*-
# wasp_general/crypto/hex.py
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

from binascii import hexlify, unhexlify

from wasp_general.verify import verify_type


class WHex:
	""" binascii.hexlify wrapper. Converts bytes to hex-string
	"""

	@verify_type(byte_sequence=bytes)
	def __init__(self, byte_sequence):
		""" Create converter

		:param byte_sequence: sequence to convert
		"""

		self.__byte_sequence = byte_sequence

	def __str__(self):
		""" Return result of converting the sequence

		:return: str
		"""
		return hexlify(self.__byte_sequence).decode('ascii')


class WUnHex:
	""" binascii.unhexlify wrapper. Converts string to bytes
	"""

	@verify_type(string=(str, bytes))
	def __init__(self, string):
		""" Create converter

		:param string: hex-string to convert
		"""

		self.__string = string

	def __bytes__(self):
		""" Return result of converting the hex-string

		:return: bytes
		"""
		return unhexlify(self.__string)
