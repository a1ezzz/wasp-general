# -*- coding: utf-8 -*-
# wasp_general/network/messenger/coders.py
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

from base64 import b64encode, b64decode

from wasp_general.verify import verify_type, verify_value
from wasp_general.crypto.hex import WHex, WUnHex
from wasp_general.crypto.aes import WAES
from wasp_general.crypto.rsa import WRSA
from wasp_general.crypto.sha import WSHA

from wasp_general.network.messenger.onion import WMessengerOnionCoderLayerBase


class WMessengerFixedModificationLayer(WMessengerOnionCoderLayerBase):
	""" :class:`.WMessengerOnionCoderLayerBase` class implementation. This class applies fixed modification to
	specified messages.

	In :meth:`.WMessengerFixedModificationLayer.encode` method this class appends "header" to the message start
	(if specified) and appends "tail" to the message end (if specified). If no header or tail are specified -
	this class does nothing.
	"""

	@verify_type(header=(bytes, str, None), tail=(bytes, str, None))
	def __init__(self, layer_name, header=None, tail=None):
		""" Construct new layer

		:param layer_name: layer name
		:param header: header to apply
		:param tail: tail to apply
		"""
		WMessengerOnionCoderLayerBase.__init__(self, layer_name)
		self.__header = header
		self.__tail = tail

		if self.__header is not None and self.__tail is not None:
			if self.__header.__class__ != self.__tail.__class__:
				raise TypeError('Headed and tail must be the same type')

	@verify_type(message=(bytes, str))
	def encode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.encode` method implementation.

		:param message: source message (must be the same type as header and tail)
		:return: result type is the same as header and tail are
		"""
		if self.__header is None and self.__tail is None:
			return message

		msg_class = self.__header.__class__ if self.__header is not None else self.__tail.__class__

		if isinstance(message, msg_class) is False:
			raise TypeError('Message must be must be the same type as headed and tail')

		header = self.__header if self.__header is not None else msg_class()
		tail = self.__tail if self.__tail is not None else msg_class()

		return header + message + tail

	@verify_type(message=(bytes, str))
	def decode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.decode` method implementation.

		:param message: source message (must be the same type as header and tail)
		:return: result type is the same as header and tail are
		"""
		if self.__header is None and self.__tail is None:
			return message

		msg_class = self.__header.__class__ if self.__header is not None else self.__tail.__class__
		if isinstance(message, msg_class) is False:
			raise TypeError('Message must be must be the same type as headed and tail')

		header = self.__header if self.__header is not None else msg_class()
		tail = self.__tail if self.__tail is not None else msg_class()

		if len(message) < (len(header) + len(tail)):
			raise ValueError('Invalid message length')

		if len(header) > 0:
			if message[:len(header)] != header:
				raise ValueError('Invalid header')
			message = message[len(header):]

		if len(tail) > 0:
			if message[-len(tail):] != tail:
				raise ValueError('Invalid tail')

			message = message[:-len(tail)]

		return message


class WMessengerHexLayer(WMessengerOnionCoderLayerBase):
	""" :class:`.WMessengerOnionCoderLayerBase` class implementation. This class translate message to corresponding
	hex-string, or decodes it from hex-string to original binary representation.
	"""

	__layer_name__ = "com.binblob.wasp-general.hex-layer"
	""" Layer name
	"""

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionCoderLayerBase.__init__(self, WMessengerHexLayer.__layer_name__)

	@verify_type(message=(bytes, str))
	def encode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.encode` method implementation.

		:param message: source message (if message is a string, then message will be translated to binary first)
		:return: str
		"""
		return str(WHex(message if isinstance(message, bytes) else message.encode()))

	@verify_type(message=(bytes, str))
	def decode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.decode` method implementation.

		:param message: source message (if message is a bytes, then message will be translated to string first)
		:return: bytes
		"""
		return bytes(WUnHex(message if isinstance(message, str) else message.decode()))


class WMessengerBase64Layer(WMessengerOnionCoderLayerBase):
	""" :class:`.WMessengerOnionCoderLayerBase` class implementation. This class translate message to corresponding
	base64-string, or decodes it from base64-string to original binary representation.
	"""

	__layer_name__ = "com.binblob.wasp-general.base64-layer"
	""" Layer name
	"""

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionCoderLayerBase.__init__(self, WMessengerBase64Layer.__layer_name__)

	@verify_type(message=(bytes, str))
	def encode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.encode` method implementation.

		:param message: source message (if message is a string, then message will be translated to binary first)
		:return: str
		"""
		if isinstance(message, str):
			message = message.encode()
		return b64encode(message)

	@verify_type(message=(bytes, str))
	def decode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.decode` method implementation.

		:param message: source message
		:return: bytes
		"""
		return b64decode(message)


class WMessengerAESLayer(WMessengerOnionCoderLayerBase):
	""" :class:`.WMessengerOnionCoderLayerBase` class implementation. This class encrypts/decrypts message with
	specified AES cipher
	"""

	@verify_type(aes_cipher=WAES)
	def __init__(self, layer_name, aes_cipher):
		""" Construct new layer

		:param layer_name: layer name
		:param aes_cipher: cipher to encrypt/decrypt
		"""
		WMessengerOnionCoderLayerBase.__init__(self, layer_name)
		self.__cipher = aes_cipher

	@verify_type(message=(bytes, str))
	def encode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.encode` method implementation.

		:param message: message to encrypt
		:return: bytes
		"""
		return self.__cipher.encrypt(message)

	@verify_type(message=bytes)
	def decode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.decode` method implementation.

		:param message: message to decrypt
		:return: bytes
		"""
		return self.__cipher.decrypt(message, decode=False)


class WMessengerRSALayer(WMessengerOnionCoderLayerBase):
	""" :class:`.WMessengerOnionCoderLayerBase` class implementation. This class encrypts/decrypts message with
	specified RSA cipher
	"""

	@verify_type(public_key=WRSA.wrapped_class, private_key=WRSA.wrapped_class, sha_digest_size=int)
	@verify_value(sha_digest_size=lambda x: x in WSHA.available_digests())
	def __init__(self, layer_name, public_key, private_key, sha_digest_size=32):
		""" Construct new layer

		:param layer_name: layer name
		:param public_key: public key to encrypt
		:param private_key: private key to decrypt
		:param sha_digest_size: hash-size
		"""
		WMessengerOnionCoderLayerBase.__init__(self, layer_name)

		self.__public_key = public_key
		self.__private_key = private_key
		self.__sha_digest_size = sha_digest_size

	@verify_type(message=(bytes, str))
	def encode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.encode` method implementation.

		:param message: message to encrypt
		:return: bytes
		"""
		if isinstance(message, bytes) is False:
			message = message.encode()
		return WRSA.encrypt(message, self.__public_key, sha_digest_size=self.__sha_digest_size)

	@verify_type(message=bytes)
	def decode(self, message):
		""" :meth:`.WMessengerOnionCoderLayerBase.decode` method implementation.

		:param message: message to decrypt
		:return: bytes
		"""
		return WRSA.decrypt(message, self.__private_key, sha_digest_size=self.__sha_digest_size)
