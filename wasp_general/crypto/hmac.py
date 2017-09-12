# -*- coding: utf-8 -*-
# wasp_general/crypto/hmac.py
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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from Crypto.Hash.HMAC import HMAC
import re

from wasp_general.verify import verify_type, verify_value
from wasp_general.crypto.hash import WHash


class WHMAC:
	""" Class that wraps PyCrypto HMAC implementation

	see also https://en.wikipedia.org/wiki/Hash-based_message_authentication_code
	"""

	__default_generator_name__ = 'SHA512'
	""" Default hash generator name for HMAC
	"""

	__hmac_name_re__ = re.compile('HMAC[\-_]([a-zA-Z0-9]+)')
	""" Regular expression that selects hash generator name from HMAC name
	"""

	@verify_type(digest_generator=(str, None))
	def __init__(self, digest_generator_name=None):
		""" Create new "code-authenticator"

		:param digest_generator_name: name of hash function
		"""
		if digest_generator_name is None:
			digest_generator_name = WHMAC.__default_generator_name__
		if digest_generator_name not in WHash.available_generators():
			raise ValueError('Unknown hash generator: "%s"' % digest_generator_name)
		self.__digest_generator = WHash.generator(digest_generator_name)

	def digest_generator(self):
		""" Return hash-generator

		:return: PyCrypto class
		"""
		return self.__digest_generator

	@verify_type(key=bytes, message=(bytes, None), digest_generator=(str, None))
	def hash(self, key, message=None):
		""" Return digest of the given message and key

		:param key: secret HMAC key
		:param message: code (message) to authenticate

		:return: bytes
		"""
		generator = self.digest_generator()
		return HMAC(key, msg=message, digestmod=generator().pycrypto()).digest()

	@classmethod
	@verify_type(name=str)
	@verify_value(name=lambda x: WHMAC.__hmac_name_re__.match(x) is not None)
	def hmac(cls, name):
		""" Return new WHMAC object by the given algorithm name like 'HMAC-SHA256' or 'HMAC_SHA1'

		:param name: name of HMAC algorithm

		:return: WHMAC
		"""
		return WHMAC(cls.__hmac_name_re__.search(name).group(1))
