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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__


from Crypto.Cipher import AES as pyAES
from Crypto.Util import Counter
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value
from wasp_general.config import WConfig

from wasp_general.crypto.random import random_int


class WBlockPadding(metaclass=ABCMeta):
	""" Padding/reverse padding class prototype
	"""

	@abstractmethod
	@verify_type(data=(str, bytes), block_size=int)
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
	@verify_value(padding=lambda x: x is None or (x >= 0 and x <= 127))
	def __init__(self, padding=None):
		""" Create new padding class

		:param padding: integer code of ASCII character
		"""
		self.__padding_symbol = chr(0) if padding is None else chr(padding)

	@verify_type(byte=bool)
	def padding_symbol(self, byte=False):
		""" Return character with witch data is padded

		:param byte: whether to return character as str or bytes object
		:return: str or bytes (depends on byte value)
		"""
		return self.__padding_symbol if byte is False else self.__padding_symbol.encode('ascii')

	@verify_type(data=(str, bytes), block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def pad(self, data, block_size):
		""" :meth:`.WBlockPadding.pad` method implementation
		"""
		if isinstance(data, str):
			data = data.encode()

		padding_symbol = self.padding_symbol(isinstance(data, bytes))

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
		return data.rstrip(self.padding_symbol(True))

	@verify_type(data=(str, bytes), total_length=int, padding_symbol=(str, bytes))
	@verify_value(total_length=lambda x: x > 0, padding_symbol=lambda x: len(x) == 1)
	def _fill(self, data, total_length, padding_symbol):
		""" Append padding symbol to the end of data till specified length is reached

		:param data: data to append to
		:param total_length: target length
		:param padding_symbol: symbol to pad
		:return: str or bytes (same as source data type)
		"""
		return data.ljust(total_length, padding_symbol)


class WShiftPadding(WSimplePadding):
	""" Same as :class:`.WSimplePadding` class, but also randomly shifts original data.
	"""

	@verify_type(data=(str, bytes), total_length=int, padding_symbol=(str, bytes))
	@verify_value(total_length=lambda x: x > 0, padding_symbol=lambda x: len(x) == 1)
	def _fill(self, data, total_length, padding_symbol):
		""" Overridden :meth:`.WSimplePadding._fill` method. This methods adds padding symbol at the beginning
		and at the end of the specified data.

		:param data: data to append to
		:param total_length: target length
		:param padding_symbol: symbol to pad
		:return: str or bytes (same as source data type)
		"""

		delta = total_length - len(data)
		return ((padding_symbol * random_int(delta)) + data).ljust(total_length, padding_symbol)

	@verify_type(data=bytes, block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def reverse_pad(self, data, block_size):
		""" :meth:`.WBlockPadding.reverse_pad` method implementation
		"""
		padding_symbol = self.padding_symbol(True)
		return data.lstrip(padding_symbol).rstrip(padding_symbol)


class WPKCS7Padding(WBlockPadding):
	""" PKCS7 Padding implementation

	see also: https://en.wikipedia.org/wiki/Padding_(cryptography)#PKCS7
	"""

	@verify_type(data=(str, bytes), block_size=int)
	@verify_value(block_size=lambda x: x > 0)
	def pad(self, data, block_size):
		""" :meth:`.WBlockPadding.pad` method implementation
		"""
		if isinstance(data, str):
			data = data.encode()

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
	""" This class specifies modes of AES encryption. It describes key size, block cipher mode of operation,
	padding object (:class:`.WBlockPadding` instance). Note, padding is required if source data or secret key
	isn't aligned on block size.

	Currently, there are implemented only two cipher mode of operation: 'CBC' and 'CTR'

	see also: https://en.wikipedia.org/wiki/Block_cipher_mode_of_operation
	"""

	__data_padding_length__ = pyAES.block_size
	""" Length to which data must be aligned (in bytes)
	"""
	__init_vector_length__ = pyAES.block_size
	""" Initialization vector length (in bytes)
	"""
	__init_counter_size__ = pyAES.block_size * 8
	""" Initialization counter size (in bits)
	"""

	__modes_descriptor__ = {
		'AES-CBC': {
			'mode_code': pyAES.MODE_CBC,
			'requirements': {
				'padding': True,
				'initialization_vector': True,
				'counter': False
			}
		},
		'AES-CTR': {
			'mode_code': pyAES.MODE_CTR,
			'requirements': {
				'padding': False,
				'initialization_vector': False,
				'counter': True
			}
		}
	}
	""" Describes block cipher modes of operation and theirs requirements
	"""

	@verify_type(key_size=int, block_cipher_mode=str, padding=(None, WBlockPadding))
	@verify_type(init_vector=(None, bytes), init_counter_value=(None, int))
	@verify_value(key_size=lambda x: x in (16, 24, 32))
	@verify_value(block_cipher_mode=lambda x: x is None or x in WAESMode.__modes_descriptor__.keys())
	@verify_value(init_vector=lambda x: x is None or len(x) == WAESMode.__init_vector_length__)
	@verify_value(init_counter_value=lambda x: x is None or x >= 0 and x < (2 ** WAESMode.__init_counter_size__))
	def __init__(
		self, key_size, block_cipher_mode, padding=None, init_vector=None, init_counter_value=None
	):
		""" Create new AES-mode.

		:param key_size: secret length
		:param block_cipher_mode: block cipher mode of operation
		:param padding: padding object
		:param init_vector: initialization vector
		:param init_counter_value: initialization counter value
		"""
		self.__key_size = key_size
		self.__cipher_args = ()
		self.__cipher_kwargs = {}
		self.__padding = padding
		self.__mode = block_cipher_mode

		cipher_descriptor = WAESMode.__modes_descriptor__[block_cipher_mode]
		self.__cipher_kwargs['mode'] = cipher_descriptor['mode_code']

		cipher_requirement = cipher_descriptor['requirements']
		if cipher_requirement['padding'] is True:
			if padding is None:
				raise ValueError('Padding must be set for "%s" cipher' % block_cipher_mode)
		if cipher_requirement['initialization_vector'] is True:
			if init_vector is None:
				raise ValueError(
					'Initialization vector must be set for "%s" cipher' % block_cipher_mode
				)
			self.__cipher_kwargs['IV'] = init_vector
		if cipher_requirement['counter'] is True:
			if init_counter_value is None:
				raise ValueError(
					'Initialization counter value must be set for "%s" cipher' % block_cipher_mode
				)
			self.__cipher_kwargs['counter'] = Counter.new(
				WAESMode.__init_counter_size__, initial_value=init_counter_value
			)

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

	def pyaes_args(self):
		""" Generate and return position-dependent arguments, that are used in :meth:`.AES.new` method

		:return: tuple
		"""
		return self.__cipher_args

	def pyaes_kwargs(self):
		""" Generate and return position-independent (named) arguments, that are used in :meth:`.AES.new` method

		:return: dict
		"""
		return self.__cipher_kwargs

	@classmethod
	@verify_type(key_size=int, block_cipher_mode=(None, str), padding=(None, WBlockPadding))
	@verify_type(init_vector=(None, bytes), init_counter_value=(None, int))
	@verify_value(key_size=lambda x: x in (16, 24, 32))
	@verify_value(block_cipher_mode=lambda x: x is None or x in WAESMode.__modes_descriptor__.keys())
	def defaults(cls, key_size=32, block_cipher_mode=None, padding=None, init_vector=None, init_counter_value=None):
		""" Generate mode, where every parameter is optional. Defaults are:
		Key (secret) size - 32
		Block cipher mode of operation - 'CBC'
		Padding (if required) - :class:`.WPKCS7Padding`
		Initialization vector (if required) - b'\x00\x00\x00'...'\x00\x00'
		Initialization counter value (if required) - 0

		:param key_size: same as key_size in :meth:`WAESMode.__init__` method
		:param block_cipher_mode: same as block_cipher_mode in :meth:`WAESMode.__init__` method
		:param padding: same as padding in :meth:`WAESMode.__init__` method
		:param init_vector: same as init_vector in :meth:`WAESMode.__init__` method
		:param init_counter_value: same as init_counter_value in :meth:`WAESMode.__init__` method
		:return: WAESMode
		"""
		if block_cipher_mode is None:
			block_cipher_mode = 'AES-CBC'

		cipher_requirements = WAESMode.__modes_descriptor__[block_cipher_mode]['requirements']

		if cipher_requirements['padding'] is True and padding is None:
			padding = WPKCS7Padding()

		if cipher_requirements['initialization_vector'] is True and init_vector is None:
			init_vector = b'\x00' * WAESMode.__init_vector_length__

		if cipher_requirements['counter'] is True and init_counter_value is None:
			init_counter_value = 0

		return WAESMode(
			key_size=key_size, block_cipher_mode=block_cipher_mode, padding=padding,
			init_vector=init_vector, init_counter_value=init_counter_value
		)


class WAES(metaclass=ABCMeta):
	""" PyCrypto AES-encryption wrapper. Derived classes must override AES.secret method
	"""

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

		secret = self.secret()
		if isinstance(secret, bytes) is False:
			raise TypeError('Invalid secret type')
		if len(secret) != self.mode().key_size():
			raise ValueError('Invalid secret length')

		cipher = pyAES.new(secret, *self.mode().pyaes_args(), **self.mode().pyaes_kwargs())
		return cipher

	@abstractmethod
	def secret(self):
		""" Abstract method. Return cipher key. This method is called from AES.cipher for AES-cipher creation

		:return: bytes
		"""
		raise NotImplementedError("This method is abstract")

	@verify_type(data=(str, bytes))
	def encrypt(self, data):
		""" Encrypt given data with cipher that is got from AES.cipher call.

		:param data: data to encrypt
		:return: bytes
		"""
		padding = self.mode().padding()
		if padding is not None:
			data = padding.pad(data, WAESMode.__data_padding_length__)

		return self.cipher().encrypt(data)

	@verify_type(data=bytes, decode=bool)
	def decrypt(self, data, decode=True):
		""" Decrypt given data with cipher that is got from AES.cipher call.

		:param data: data to decrypt
		:param decode: whether to decode bytes to str or not
		:return: bytes or str (depends on decode flag)
		"""

		result = self.cipher().decrypt(data)

		padding = self.mode().padding()
		if padding is not None:
			result = padding.reverse_pad(result, WAESMode.__data_padding_length__)

		return result.decode() if decode else result


class WFixedSecretAES(WAES):
	""" AES implementation with fixed static secret key
	"""

	@verify_type(secret=(str, bytes), mode=WAESMode)
	def __init__(self, secret, mode):
		""" Create new cipher

		:param secret: fixed cipher key. If key isn't aligned to cipher key size, then padding object from \
		AES mode is used (if there is no padding object ValueError is raised).
		:param mode: AES mode
		"""
		WAES.__init__(self, mode)

		secret = secret if isinstance(secret, bytes) else secret.encode()

		key_size = self.mode().key_size()
		padding = self.mode().padding()
		if len(secret) >= key_size:
			secret = secret[:key_size]
		elif padding is not None:
			secret = padding.pad(secret, key_size)
		else:
			raise ValueError('Invalid secret length (or there is no padding)')

		self.__secret_string = secret

	def secret(self):
		""" :meth:`.WAES.secret` method implementation. Returns secret key given in constructor

		:return: str or bytes (depends on original secret key)
		"""
		return self.__secret_string


class WConfigSecretAES(WAES):
	""" AES implementation with secret key specified in given configuration. (Secret key is always str object)
	"""

	@verify_type(config=WConfig, section=str, option=str, mode=WAESMode)
	def __init__(self, config, section, option, mode):
		""" Construct new AES cipher

		:param config: configuration with secret key
		:param section: section name with secret key
		:param option: option name where secret key is
		:param mode: AES mode
		"""

		WAES.__init__(self, mode)
		self.__config = config
		self.__config_section = section
		self.__config_option = option

	def secret(self):
		""" :meth:`.WAES.secret` method implementation. Returns secret key from configuration If key isn't
		aligned to cipher key size, then padding object from AES mode is used (if there is no padding
		object ValueError is raised).

		:return: str
		"""

		secret = self.__config[self.__config_section][self.__config_option].strip().encode()

		key_size = self.mode().key_size()
		padding = self.mode().padding()
		if len(secret) >= key_size:
			secret = secret[:key_size]
		elif padding is not None:
			secret = padding.pad(secret, key_size)
		else:
			raise ValueError('Invalid secret length (or there is no padding)')

		return secret
