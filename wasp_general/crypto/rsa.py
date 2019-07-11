# -*- coding: utf-8 -*-
# wasp_general/crypto/rsa.py
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

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

from wasp_general.verify import verify_type, verify_value


class WRSA:
	""" Wraps Cryptography io RSA implementation
	"""

	__default_oaep_hash_function_name__ = 'SHA512'
	""" Default hash function that is used with RSA-OAEP encryption/decryption
	"""

	__default_mgf1_hash_function_name__ = 'SHA512'
	""" Default hash function that is used with RSA-OAEP encryption/decryption for MGF1 padding.
	"""

	def __init__(self):
		""" Create  object for RSA cryptography
		"""
		self.__private_key = None
		self.__public_key = None

	def __set_private_key(self, pk):
		""" Internal method that sets the specified private key
		:param pk: private key to set
		:return: None
		"""
		self.__private_key = pk
		self.__public_key = pk.public_key()

	def __set_public_key(self, pk):
		""" Internal method that sets the specified public key
		:param pk: public key to set
		:return: None
		"""
		self.__private_key = None
		self.__public_key = pk

	def private_key_size(self):
		""" Return private key size

		:return: int
		"""
		if self.__private_key is None:
			raise ValueError('Unable to call this method. Private key must be set')

		return self.__private_key.key_size

	def has_private_key(self):
		""" Check if this object has a private key

		:return: bool
		"""
		return self.__private_key is not None

	def has_public_key(self):
		""" Check if this object has a public key

		:return: bool
		"""
		return self.__public_key is not None

	@verify_type(key_size=int, public_exponent=int)
	@verify_value(key_size=lambda x: ((x % 256) == 0) and x >= 1024, public_exponent=lambda x: x > 0)
	def generate_private_key(self, key_size=2048, public_exponent=65537):
		""" Generate a private (and a corresponding public) key

		:return: None
		"""
		self.__set_private_key(
			rsa.generate_private_key(
				public_exponent=public_exponent, key_size=key_size, backend=default_backend()
			)
		)

	@verify_type(password=(str, bytes, None))
	def export_private_key(self, password=None):
		""" Export a private key in PEM-format

		:param password: If it is not None, then result will be encrypt with given password
		:return: bytes
		"""

		if self.__private_key is None:
			raise ValueError('Unable to call this method. Private key must be set')

		if password is not None:
			if isinstance(password, str) is True:
				password = password.encode()
			return self.__private_key.private_bytes(
				encoding=serialization.Encoding.PEM,
				format=serialization.PrivateFormat.PKCS8,
				encryption_algorithm=serialization.BestAvailableEncryption(password)
			)
		return self.__private_key.private_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PrivateFormat.TraditionalOpenSSL,
			encryption_algorithm=serialization.NoEncryption()
		)

	def export_public_key(self):
		""" Export a public key in PEM-format

		:return: bytes
		"""
		if self.__public_key is None:
			raise ValueError('Unable to call this method. Public key must be set')

		return self.__public_key.public_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PublicFormat.SubjectPublicKeyInfo
		)

	@verify_type(pem_text=(str, bytes), password=(str, bytes, None))
	def import_private_key(self, pem_text, password=None):
		""" Import a private key from data in PEM-format

		:param pem_text: text with private key
		:param password: If it is not None, then result will be decrypt with the given password
		:return: None
		"""
		if isinstance(pem_text, str) is True:
			pem_text = pem_text.encode()
		if password is not None and isinstance(password, str) is True:
			password = password.encode()

		self.__set_private_key(
			serialization.load_pem_private_key(pem_text, password=password, backend=default_backend())
		)

	@verify_type(pem_text=(str, bytes))
	def import_public_key(self, pem_text):
		""" Import a public key from data in PEM-format
		:param pem_text: text with public key
		:return: None
		"""
		if isinstance(pem_text, str) is True:
			pem_text = pem_text.encode()
		self.__set_public_key(
			serialization.load_pem_public_key(pem_text, backend=default_backend())
		)

	@verify_type(data=bytes, oaep_hash_fn_name=(str, None), mgf1_hash_fn_name=(str, None))
	@verify_value(oaep_hash_fn_name=lambda x: x is None or hasattr(hashes, x))
	@verify_value(mgf1_hash_fn_name=lambda x: x is None or hasattr(hashes, x))
	def encrypt(self, data, oaep_hash_fn_name=None, mgf1_hash_fn_name=None):
		""" Encrypt a data with PKCS1 OAEP protocol

		:param data: data to encrypt
		:param oaep_hash_fn_name: hash function name to use with OAEP
		:param mgf1_hash_fn_name: hash function name to use with MGF1 padding
		:return: bytes
		"""

		if self.__public_key is None:
			raise ValueError('Unable to call this method. Public key must be set')

		if oaep_hash_fn_name is None:
			oaep_hash_fn_name = self.__class__.__default_oaep_hash_function_name__

		if mgf1_hash_fn_name is None:
			mgf1_hash_fn_name = self.__class__.__default_mgf1_hash_function_name__

		oaep_hash_cls = getattr(hashes, oaep_hash_fn_name)
		mgf1_hash_cls = getattr(hashes, mgf1_hash_fn_name)

		return self.__public_key.encrypt(
			data,
			padding.OAEP(
				mgf=padding.MGF1(algorithm=mgf1_hash_cls()),
				algorithm=oaep_hash_cls(),
				label=None
			)
		)

	@verify_type(data=bytes, oaep_hash_fn_name=(str, None), mgf1_hash_fn_name=(str, None))
	@verify_value(oaep_hash_fn_name=lambda x: x is None or hasattr(hashes, x))
	@verify_value(mgf1_hash_fn_name=lambda x: x is None or hasattr(hashes, x))
	def decrypt(self, data, oaep_hash_fn_name=None, mgf1_hash_fn_name=None):
		""" Decrypt a data that used PKCS1 OAEP protocol

		:param data: data to decrypt
		:param oaep_hash_fn_name: hash function name to use with OAEP
		:param mgf1_hash_fn_name: hash function name to use with MGF1 padding
		:return: bytes
		"""

		if self.__private_key is None:
			raise ValueError('Unable to call this method. Private key must be set')

		if oaep_hash_fn_name is None:
			oaep_hash_fn_name = self.__class__.__default_oaep_hash_function_name__

		if mgf1_hash_fn_name is None:
			mgf1_hash_fn_name = self.__class__.__default_mgf1_hash_function_name__

		oaep_hash_cls = getattr(hashes, oaep_hash_fn_name)
		mgf1_hash_cls = getattr(hashes, mgf1_hash_fn_name)

		return self.__private_key.decrypt(
			data,
			padding.OAEP(
				mgf=padding.MGF1(algorithm=mgf1_hash_cls()),
				algorithm=oaep_hash_cls(),
				label=None
			)
		)
