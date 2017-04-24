# -*- coding: utf-8 -*-
# wasp_general/crypto/random.py
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


from Crypto.Random.random import getrandbits
import math

from wasp_general.verify import verify_type, verify_value


@verify_type(bits_count=int)
@verify_value(bits_count=lambda x: x >= 0)
def random_bits(bits_count):
	""" Random generator (PyCrypto getrandbits wrapper). The result is a non-negative value.

	:param bits_count: random bits to generate
	:return: int
	"""
	return getrandbits(bits_count)


@verify_type(maximum_value=int)
@verify_value(maximum_value=lambda x: x >= 0)
def random_int(maximum_value):
	""" Random generator (PyCrypto getrandbits wrapper). The result is a non-negative value.

	:param maximum_value: maximum integer value
	:return: int
	"""
	if maximum_value == 0:
		return 0
	elif maximum_value == 1:
		return random_bits(1)

	bits = math.floor(math.log2(maximum_value))
	result = random_bits(bits) + random_int(maximum_value - ((2 ** bits) - 1))
	return result


@verify_type(bytes_count=int)
@verify_value(bytes_count=lambda x: x >= 0)
def random_bytes(bytes_count):
	""" Generate random bytes sequence. (PyCrypto getrandbits wrapper)

	:param bytes_count: sequence length
	:return: bytes
	"""

	return bytes([getrandbits(8) for x in range(bytes_count)])
