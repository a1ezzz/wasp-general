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

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac
import re

from wasp_general.verify import verify_type, verify_value


class WHMAC:
	""" Class that wraps Cryptography io HMAC implementation

	see also https://en.wikipedia.org/wiki/Hash-based_message_authentication_code
	"""

	__default_hash_fn_name__ = 'SHA512'
	""" Default hash function name for HMAC
	"""

	__hmac_name_re__ = re.compile('HMAC[\-_]([a-zA-Z0-9]+)')
	""" Regular expression that selects hash function name from HMAC name
	"""

	@verify_type(hash_fn_name=(str, None))
	@verify_value(hash_fn_name=lambda x: x is None or hasattr(hashes, x))
	def __init__(self, hash_fn_name=None):
		""" Create new "code-authenticator"

		:param hash_fn_name: a name of hash function
		"""

		self.__hash_fn_name = \
			hash_fn_name if hash_fn_name is not None else self.__class__.__default_hash_fn_name__
		self.__digest_generator = getattr(hashes, self.__hash_fn_name)()

	def hash_function_name(self):
		""" Return hash-generator name

		:return: str
		"""

		return self.__hash_fn_name

	@verify_type(key=bytes, message=(bytes, None))
	def hash(self, key, message=None):
		""" Return digest of the given message and key

		:param key: secret HMAC key
		:param message: code (message) to authenticate

		:return: bytes
		"""
		hmac_obj = hmac.HMAC(key, self.__digest_generator, backend=default_backend())
		if message is not None:
			hmac_obj.update(message)
		return hmac_obj.finalize()

	@classmethod
	@verify_type(name=str)
	@verify_value(name=lambda x: WHMAC.__hmac_name_re__.match(x) is not None)
	def hmac(cls, name):
		""" Return new WHMAC object by the given algorithm name like 'HMAC-SHA256' or 'HMAC_SHA1'

		:param name: name of HMAC algorithm

		:return: WHMAC
		"""
		return WHMAC(cls.__hmac_name_re__.search(name).group(1))
