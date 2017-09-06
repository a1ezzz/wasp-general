# -*- coding: utf-8 -*-
# wasp_general/crypto/sha.py
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

from Crypto.Hash import SHA as SHA1, SHA224, SHA256, SHA384, SHA512

from wasp_general.verify import verify_type, verify_value


__sha_functions__ = {
	'SHA1': SHA1,
	'SHA224': SHA224,
	'SHA256': SHA256,
	'SHA384': SHA384,
	'SHA512': SHA512
}
""" Hashing functions map 'SHA hash function name' - 'PyCrypto hash class'
"""


class WSHA:
	""" PyCrypto SHA-hashing wrapper
	"""

	__hash_functions__ = {x.digest_size: x for x in __sha_functions__.values()}
	""" Hashing functions map 'digest size in bytes' - 'PyCrypto hash class'
	"""

	__digest_size_by_name__ = {x: y.digest_size for x, y in __sha_functions__.items()}
	""" Hashing functions map 'SHA hash function name' - 'digest size in bytes'
	"""

	__default_digest_size__ = SHA512.digest_size
	""" Default hash digest size
	"""

	@staticmethod
	def available_digests():
		""" Return available digests size

		:return: tuple of int
		"""
		digests = list(WSHA.__hash_functions__.keys())
		digests.sort()
		return tuple(digests)

	@staticmethod
	def available_names():
		""" Return names of SHA-generators

		:return: tuple of str
		"""
		return tuple(WSHA.__digest_size_by_name__.keys())

	@staticmethod
	@verify_type(digest_size=int)
	@verify_value(digest_size=lambda x: x in WSHA.__hash_functions__.keys())
	def validate_digest_size(digest_size=__default_digest_size__):
		""" Validate digest size or return default value. If digest size is ok then same value is returned.

		:param digest_size: digest size in bytes to check
		:return: int
		"""
		return digest_size

	@staticmethod
	@verify_type(fn_name=str)
	@verify_value(fn_name=lambda x: x in WSHA.__digest_size_by_name__.keys())
	def digest_size(fn_name):
		""" Return digest size for the given name of generator

		:param fn_name: generator name

		:return: int
		"""
		fn_name = fn_name.upper()
		return WSHA.__digest_size_by_name__[fn_name]

	@staticmethod
	@verify_type(digest_size=int)
	@verify_value(digest_size=lambda x: x in WSHA.__hash_functions__.keys())
	def hash_generator(digest_size=__default_digest_size__):
		""" Return PyCrypto SHA class by given digest size

		:param digest_size: digest size of hash object
		:return: related class
		"""
		return WSHA.__hash_functions__[digest_size]

	@staticmethod
	@verify_type(data=bytes, digest_size=int)
	@verify_value(digest_size=lambda x: x in WSHA.__hash_functions__.keys())
	def hash(data, digest_size=__default_digest_size__):
		""" Return hash for given data

		:param data: data to generate hash for
		:param digest_size: hash size
		:return: bytes
		"""
		return WSHA.hash_generator(digest_size).new(data).digest()
