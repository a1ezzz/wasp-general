# -*- coding: utf-8 -*-
# wasp_general/crypto/aes.py
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

import re
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.backends import default_backend
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value

from wasp_general.crypto.random import random_int
from wasp_general.crypto.cipher import WCipherProto


class WBlockPadding(metaclass=ABCMeta):
	""" Padding/reverse padding class prototype
	"""

	@abstractmethod
	@verify_type(data=bytes, block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def pad(self, data, block_size):
		""" Pad given data to given size

		:param data: data to pad
		:param block_size: size to pad
		:return: bytes
		"""
		raise NotImplementedError("This method is abstract")

	@abstractmethod
	@verify_type(data=bytes, block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def reverse_pad(self, data, block_size):
		""" Remove pads and return original data

		:param data: data to remove pads from
		:param block_size: size data aligned to
		:return: bytes
		"""
		raise NotImplementedError("This method is abstract")


class WSimplePadding(WBlockPadding):
	""" Class that pads given data with specified ASCII character
	"""

	@verify_type(padding=(int, None))
	@verify_value(padding=lambda x: x is None or (0 <= x <= 127))
	def __init__(self, padding=None):
		""" Create new padding class

		:param padding: integer code of ASCII character
		"""
		if padding is None:
			padding = 0
		self.__padding_symbol = bytes([padding])

	def padding_symbol(self):
		""" Return character with witch data is padded

		:return: bytes
		"""
		return self.__padding_symbol

	@verify_type(data=bytes, block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def pad(self, data, block_size):
		""" :meth:`.WBlockPadding.pad` method implementation
		"""
		padding_symbol = self.padding_symbol()

		blocks_count = (len(data) // block_size)
		if (len(data) % block_size) != 0:
			blocks_count += 1

		total_length = blocks_count * block_size
		return self._fill(data, total_length, padding_symbol)

	@verify_type(data=bytes, block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def reverse_pad(self, data, block_size):
		""" :meth:`.WBlockPadding.reverse_pad` method implementation
		"""
		return data.rstrip(self.padding_symbol())

	@verify_type(data=bytes, total_length=int, padding_symbol=bytes)
	@verify_value(total_length=lambda x: x > 0, padding_symbol=lambda x: len(x) == 1)
	def _fill(self, data, total_length, padding_symbol):
		""" Append padding symbol to the end of data till specified length is reached

		:param data: data to append to
		:param total_length: target length
		:param padding_symbol: symbol to pad
		:return: bytes
		"""
		return data.ljust(total_length, padding_symbol)


class WZeroPadding(WSimplePadding):
	""" Zero padding implementation (just alias for WSimplePadding() object)

	see also: https://en.wikipedia.org/wiki/Padding_(cryptography)#Zero_padding
	"""

	def __init__(self):
		""" Create new padding object
		"""
		WSimplePadding.__init__(self)


class WShiftPadding(WSimplePadding):
	""" Same as :class:`.WSimplePadding` class, but also randomly shifts original data.
	"""

	@verify_type(data=bytes, total_length=int, padding_symbol=bytes)
	@verify_value(total_length=lambda x: x > 0, padding_symbol=lambda x: len(x) == 1)
	def _fill(self, data, total_length, padding_symbol):
		""" Overridden :meth:`.WSimplePadding._fill` method. This methods adds padding symbol at the beginning
		and at the end of the specified data.

		:param data: data to append to
		:param total_length: target length
		:param padding_symbol: symbol to pad
		:return: bytes
		"""

		delta = total_length - len(data)
		return ((padding_symbol * random_int(delta)) + data).ljust(total_length, padding_symbol)

	@verify_type(data=bytes, block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def reverse_pad(self, data, block_size):
		""" :meth:`.WBlockPadding.reverse_pad` method implementation
		"""
		padding_symbol = self.padding_symbol()
		return data.lstrip(padding_symbol).rstrip(padding_symbol)


class WPKCS7Padding(WBlockPadding):
	""" PKCS7 Padding implementation

	see also: https://en.wikipedia.org/wiki/Padding_(cryptography)#PKCS7
	"""

	@verify_type(data=bytes, block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def pad(self, data, block_size):
		""" :meth:`.WBlockPadding.pad` method implementation
		"""
		pad_byte = block_size - (len(data) % block_size)
		return data + bytes([pad_byte] * pad_byte)

	@verify_type(data=bytes, block_size=int)
	@verify_value(data=lambda x: len(x) > 0, block_size=lambda x: x > 0)
	def reverse_pad(self, data, block_size):
		""" :meth:`.WBlockPadding.reverse_pad` method implementation
		"""
		pad_byte = data[-1]
		if pad_byte > block_size:
			raise ValueError('Invalid padding')

		padding = bytes([pad_byte] * pad_byte)
		if data[-pad_byte:] != padding:
			raise ValueError('Invalid padding')

		return data[:-pad_byte]


class WAESMode:
	""" This class specifies modes of AES encryption. It describes secret key (size and value), block cipher mode
	of operation, padding object (:class:`.WBlockPadding` instance), required initialization values. Note,
	padding is required if source data isn't aligned to block size.

	For byte-sequence generation (that is used as secret key and initialization values) it is possible to use
	:class:`wasp_general.crypto.kdf.WPBKDF2`. :class:`wasp_general.crypto.kdf.WPBKDF2` is a wrapper for PBKDF2
	function (KDF function that safely generates byte-sequence from the given password and salt)

	Currently, only two cipher mode of operation are implemented: 'CBC' and 'CTR'

	see also: https://en.wikipedia.org/wiki/Block_cipher_mode_of_operation
	"""

	__data_padding_length__ = int(AES.block_size / 8)
	""" Length to which data must be aligned (in bytes)
	"""
	__init_vector_length__ = int(AES.block_size / 8)
	""" Initialization vector length (in bytes)
	"""
	__counter_size__ = int(AES.block_size / 8)
	""" Initialization counter size (in bytes)
	"""

	__mode_re__ = re.compile(r'AES(\-|_)(\d+)(\-|_)(\w+)')
	""" Regular expression for parsing cipher name
	"""

	__valid_key_sizes__ = (16, 24, 32)
	""" Supported AES key sizes (in bytes)
	"""

	__modes_descriptor__ = {
		'AES-CBC': {
			'mode_code': modes.CBC,
			'requirements': {
				'initialization_vector': True,
				'counter': False
			}
		},
		'AES-CTR': {
			'mode_code': modes.CTR,
			'requirements': {
				'initialization_vector': False,
				'counter': True
			}
		}
	}
	""" Describes block cipher modes of operation and theirs requirements
	"""

	class SequenceChopper:
		""" Helper, that chops the given byte-sequence into several separate objects (like secret key,
		initialization vector or initialization counter values). The exact values depend on AES key size and
		block cipher mode of operation.

		If length of the given byte-sequence is greater then it is required, then extra bytes discard and
		this extra-bytes don't take part in any calculation
		"""

		@verify_type('paranoid', block_cipher_mode=str, key_size=int)
		@verify_type(sequence=bytes)
		@verify_value('paranoid', block_cipher_mode=lambda x: x in WAESMode.__modes_descriptor__.keys())
		def __init__(self, key_size, block_cipher_mode, sequence):
			""" Create new chopper

			:param key_size: AES secret length
			:param block_cipher_mode: name of block cipher mode of operation
			:param sequence: byte-sequence to chop
			"""
			required_length = self.required_sequence_length(key_size, block_cipher_mode)
			self.__key_size = key_size
			self.__mode = block_cipher_mode
			self.__sequence = sequence

			if required_length > 0:
				if len(self.__sequence) < required_length:
					raise ValueError(
						'Initialization byte-sequence too short. '
						'Must be at least %i bytes long' % required_length
					)

		def secret(self):
			""" Return AES secret generated from the initial byte-sequence

			:return: bytes
			"""
			return self.__sequence[:self.__key_size]

		def initialization_vector(self):
			""" Return initialization vector generated from the initial byte-sequence if it is required
			by the current block cipher mode of operation. If it doesn't require - then None is returned

			:return: bytes or None
			"""
			req = self.__requirements()
			if req['initialization_vector'] is not True:
				return None
			start_position = self.__key_size
			end_position = start_position + WAESMode.__init_vector_length__
			return self.__sequence[start_position:end_position]

		def initialization_counter_value(self):
			""" Return initialization counter value generated from the initial byte-sequence if it is
			required by the current block cipher mode of operation. If it doesn't require - then None
			is returned

			:return: int or None
			"""
			req = self.__requirements()
			if req['counter'] is not True:
				return None

			start_position = self.__key_size
			if req['initialization_vector'] is True:
				start_position += WAESMode.__init_vector_length__
			end_position = start_position + WAESMode.__counter_size__
			seq = self.__sequence[start_position:end_position]
			return seq

		def __requirements(self):
			""" Return requirements specification (just shortcut to access specific mode requirements from
			WAESMode.__modes_descriptor__)

			:return: dict
			"""
			return WAESMode.__modes_descriptor__[self.__mode]['requirements']

		@classmethod
		@verify_type(key_size=int, block_cipher_mode=str)
		@verify_value(key_size=lambda x: x in WAESMode.__valid_key_sizes__)
		@verify_value(block_cipher_mode=lambda x: x in WAESMode.__modes_descriptor__.keys())
		def required_sequence_length(cls, key_size, block_cipher_mode):
			""" Calculate required byte-sequence length

			:param key_size: AES secret length
			:param block_cipher_mode: name of block cipher mode of operation to calculate for

			:return: int
			"""
			req = WAESMode.__modes_descriptor__[block_cipher_mode]['requirements']
			result = key_size
			if req['initialization_vector'] is True:
				result += WAESMode.__init_vector_length__
			if req['counter'] is True:
				result += WAESMode.__counter_size__
			return result

	@verify_type(key_size=int, block_cipher_mode=str, padding=(None, WBlockPadding), init_sequence=bytes)
	@verify_value(key_size=lambda x: x in WAESMode.__valid_key_sizes__)
	@verify_value(block_cipher_mode=lambda x: x in WAESMode.__modes_descriptor__.keys())
	def __init__(
		self, key_size, block_cipher_mode, init_sequence, padding=None
	):
		""" Create new AES-mode.

		:param key_size: secret length
		:param block_cipher_mode: name of block cipher mode of operation
		:param padding: padding object (if required)
		:param init_sequence: AES secret with initialization vector or counter value
		"""
		self.__key_size = key_size
		self.__mode = block_cipher_mode
		self.__padding = padding
		self.__sequence_chopper = WAESMode.SequenceChopper(key_size, block_cipher_mode, init_sequence)

		if block_cipher_mode == 'AES-CBC':
			mode_code = modes.CBC(self.__sequence_chopper.initialization_vector())
		elif block_cipher_mode == 'AES-CTR':
			mode_code = modes.CTR(self.__sequence_chopper.initialization_counter_value())
		else:
			raise ValueError('Unknown block cipher mode spotted')

		self.__cipher_args = (AES(self.__sequence_chopper.secret()), mode_code)
		self.__cipher_kwargs = {'backend': default_backend()}

	def key_size(self):
		""" Return cipher secret key size

		:return: int
		"""
		return self.__key_size

	def mode(self):
		""" Return block cipher mode of operation name

		:return:
		"""
		return self.__mode

	def padding(self):
		""" Return padding object

		:return: WBlockPadding or None
		"""
		return self.__padding

	def initialization_vector(self):
		""" Return currently used initialization vector or None if vector is not used

		:return: bytes or None
		"""
		return self.__sequence_chopper.initialization_vector()

	def initialization_counter_value(self):
		""" Return currently used initialization counter value or None if counter is not used

		:return: int or None
		"""
		return self.__sequence_chopper.initialization_counter_value()

	def aes_args(self):
		""" Generate and return position-dependent arguments, that are used in :meth:`.AES.new` method

		:return: tuple
		"""
		return self.__cipher_args

	def aes_kwargs(self):
		""" Generate and return position-independent (named) arguments, that are used in :meth:`.AES.new` method

		:return: dict
		"""
		return self.__cipher_kwargs

	@classmethod
	def init_sequence_length(cls, key_size, block_cipher_mode):
		""" Return required byte-sequence length

		:param key_size: secret size
		:param block_cipher_mode: name of block cipher mode of operation

		:return: int
		"""
		return WAESMode.SequenceChopper.required_sequence_length(key_size, block_cipher_mode)

	@classmethod
	@verify_type(name=str)
	def parse_cipher_name(cls, name):
		""" Parse cipher name (name like 'aes_256_cbc' or 'AES-128-CTR'). Also this method validates If the
		cipher is supported by this class. If no - exception is raised

		:param name: name to parse

		:return: tuple where the first element is a key size in bytes (int) and the second element - block cipher mode
		of operation (str) (for example: (16, 'AES-CTR') or (24, 'AES-CBC'))
		"""
		r = cls.__mode_re__.match(name.upper())
		if r is None:
			raise ValueError('Unable to find suitable cipher for: "%s"' % name)
		key_size = int(int(r.group(2)) / 8)
		block_mode = 'AES-%s' % r.group(4)
		if key_size not in cls.__valid_key_sizes__:
			raise ValueError('Unsupported secret length: "%i"' % key_size)
		if block_mode not in cls.__modes_descriptor__.keys():
			raise ValueError('Unsupported block cipher mode of operation: "%s"' % block_mode)
		return key_size, block_mode


class WAES:
	""" PyCrypto AES-encryption wrapper
	"""

	class WAESCipher(WCipherProto):

		def __init__(self, aes_cipher):
			self.__aes_cipher = aes_cipher
			self.__encrypt_cipher = self.__aes_cipher.encryptor()
			self.__decrypt_cipher = self.__aes_cipher.decryptor()

		def block_size(self):
			return int(self.__aes_cipher.algorithm.block_size / 8)

		@verify_type(data=bytes)
		def encrypt_block(self, data):
			return self.__encrypt_cipher.update(data)

		@verify_type(data=bytes)
		def decrypt_block(self, data):
			return self.__decrypt_cipher.update(data)

	@verify_type(mode=WAESMode)
	def __init__(self, mode):
		""" Create new AES cipher with specified mode

		:param mode: AES mode
		"""

		self.__mode = mode

	def mode(self):
		""" Return AES mode

		:return: WAESMode
		"""
		return self.__mode

	def cipher(self):
		""" Generate AES-cipher

		:return: Crypto.Cipher.AES.AESCipher
		"""
		cipher = Cipher(*self.mode().aes_args(), **self.mode().aes_kwargs())
		return WAES.WAESCipher(cipher)

	@verify_type(data=(str, bytes))
	def encrypt(self, data):
		""" Encrypt the given data with cipher that is got from AES.cipher call.

		:param data: data to encrypt
		:return: bytes
		"""
		padding = self.mode().padding()
		if padding is not None:
			data = padding.pad(data, WAESMode.__data_padding_length__)

		return self.cipher().encrypt_block(data)

	@verify_type(data=bytes, decode=bool)
	def decrypt(self, data, decode=False):
		""" Decrypt the given data with cipher that is got from AES.cipher call.

		:param data: data to decrypt
		:param decode: whether to decode bytes to str or not
		:return: bytes or str (depends on decode flag)
		"""

		result = self.cipher().decrypt_block(data)

		padding = self.mode().padding()
		if padding is not None:
			result = padding.reverse_pad(result, WAESMode.__data_padding_length__)

		return result.decode() if decode else result
