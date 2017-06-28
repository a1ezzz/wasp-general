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
from enum import Enum

from wasp_general.verify import verify_type
from wasp_general.crypto.hex import WHex, WUnHex
from wasp_general.crypto.aes import WAES
from wasp_general.crypto.rsa import WRSA

from wasp_general.network.messenger.proto import WMessengerOnionSessionProto
from wasp_general.network.messenger.envelope import WMessengerTextEnvelope, WMessengerBytesEnvelope
from wasp_general.network.messenger.layers import WMessengerOnionCoderLayerProto


class WMessengerFixedModificationLayer(WMessengerOnionCoderLayerProto):
	""" :class:`.WMessengerOnionCoderLayerProto` class implementation. This class applies fixed modification to
	specified messages.

	In :meth:`.WMessengerFixedModificationLayer.encode` method this class appends "header" to the message start
	or appends "tail" to the message end. One of them must be specified.

	For :class:`.WMessengerTextEnvelope` envelope, "header" or "tail" must be "str" type.
	For :class:`.WMessengerBytesEnvelope` envelope, "header" or "tail" must be "bytes" type.
	"""

	__layer_name__ = "com.binblob.wasp-general.fixed-modification-layer"
	""" Layer name
	"""

	class Target(Enum):
		""" Modification mode. Specifies whether modification code must be appended to start or to the end
		of a message
		"""
		head = 1
		""" Modification code must be inserted to a message start
		"""
		tail = 2
		""" Modification code must be added to a message end
		"""

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionCoderLayerProto.__init__(self, WMessengerFixedModificationLayer.__layer_name__)

	@verify_type(envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope))
	def __args_check(self, envelope, target, modification_code):
		""" Method checks arguments, that are specified to the
		:meth:`.WMessengerFixedModificationLayer.encode` and :meth:`.WMessengerFixedModificationLayer.decode`
		methods

		:param envelope: same as envelope in :meth:`.WMessengerFixedModificationLayer.encode` and \
		:meth:`.WMessengerFixedModificationLayer.decode` methods
		:param target: same as target in :meth:`.WMessengerFixedModificationLayer.encode` and \
		:meth:`.WMessengerFixedModificationLayer.decode` methods
		:param modification_code: same as modification_code in \
		:meth:`.WMessengerFixedModificationLayer.encode` and :meth:`.WMessengerFixedModificationLayer.decode` \
		methods

		:return: None
		"""
		if target is None:
			raise RuntimeError('"target" argument must be specified for this layer')
		if modification_code is None:
			raise RuntimeError('"modification_code" argument must be specified for this layer')

		if isinstance(target, WMessengerFixedModificationLayer.Target) is False:
			raise TypeError('Invalid "target" argument')

		if isinstance(envelope, WMessengerTextEnvelope) is True:
			if isinstance(modification_code, str) is False:
				raise TypeError('Invalid "modification_code" argument for specified envelope')
		elif isinstance(modification_code, bytes) is False:
			raise TypeError('Invalid "modification_code" argument for specified envelope')

	@verify_type('paranoid', envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope))
	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	def encode(self, envelope, session, target=None, modification_code=None, **kwargs):
		""" Methods appends 'modification_code' to the specified envelope.

		:param envelope: original envelope
		:param session: original session
		:param target: flag, that specifies whether code must be appended to the start or to the end
		:param modification_code: code to append
		:param kwargs: additional arguments

		:return: WMessengerTextEnvelope or WMessengerBytesEnvelope (depends on the original envelope)
		"""
		self.__args_check(envelope, target, modification_code)

		if isinstance(envelope, WMessengerTextEnvelope):
			target_envelope_cls = WMessengerTextEnvelope
		else:  # isinstance(envelope, WMessengerBytesEnvelope)
			target_envelope_cls = WMessengerBytesEnvelope

		if target == WMessengerFixedModificationLayer.Target.head:
			return target_envelope_cls(modification_code + envelope.message(), meta=envelope)
		else:  # target == WMessengerFixedModificationLayer.Target.tail
			return target_envelope_cls(envelope.message() + modification_code, meta=envelope)

	@verify_type('paranoid', envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope))
	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	def decode(self, envelope, session, target=None, modification_code=None, **kwargs):
		""" Methods checks envelope for 'modification_code' existence and removes it.

		:param envelope: original envelope
		:param session: original session
		:param target: flag, that specifies whether code must be searched and removed at the start or at the end
		:param modification_code: code to search/remove
		:param kwargs: additional arguments

		:return: WMessengerTextEnvelope or WMessengerBytesEnvelope (depends on the original envelope)
		"""
		self.__args_check(envelope, target, modification_code)

		message = envelope.message()
		if len(message) < len(modification_code):
			raise ValueError('Invalid message length')

		if isinstance(envelope, WMessengerTextEnvelope):
			target_envelope_cls = WMessengerTextEnvelope
		else:  # isinstance(envelope, WMessengerBytesEnvelope)
			target_envelope_cls = WMessengerBytesEnvelope

		if target == WMessengerFixedModificationLayer.Target.head:
			if message[:len(modification_code)] != modification_code:
				raise ValueError('Invalid header in message')
			return target_envelope_cls(message[len(modification_code):], meta=envelope)
		else:  # target == WMessengerFixedModificationLayer.Target.tail
			if message[-len(modification_code):] != modification_code:
				raise ValueError('Invalid tail in message')
			return target_envelope_cls(message[:-len(modification_code)], meta=envelope)


class WMessengerEncodingLayer(WMessengerOnionCoderLayerProto):
	""" This layer can encode str-object to the related encoding (to the bytes-object). Or decode bytes-object from
	the specified encoding (from bytes-object to str-object)
	"""

	__layer_name__ = "com.binblob.wasp-general.encoding-layer"
	""" Layer name
	"""

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionCoderLayerProto.__init__(self, WMessengerEncodingLayer.__layer_name__)

	@verify_type('paranoid', envelope=WMessengerTextEnvelope, session=WMessengerOnionSessionProto)
	@verify_type(encoding=(str, None))
	def encode(self, envelope, session, encoding=None, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.encode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param encoding: encoding to use (default is 'utf-8')
		:param kwargs: additional arguments

		:return: WMessengerBytesEnvelope
		"""
		message = envelope.message()
		message = message.encode() if encoding is None else message.encode(encoding)
		return WMessengerBytesEnvelope(message, meta=envelope)

	@verify_type('paranoid', envelope=WMessengerBytesEnvelope, session=WMessengerOnionSessionProto)
	@verify_type(encoding=(str, None))
	def decode(self, envelope, session, encoding=None, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.decode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param encoding: encoding to use (default is 'utf-8')
		:param kwargs: additional arguments

		:return: WMessengerTextEnvelope
		"""
		message = envelope.message()
		message = message.decode() if encoding is None else message.decode(encoding)
		return WMessengerTextEnvelope(message, meta=envelope)


class WMessengerHexLayer(WMessengerOnionCoderLayerProto):
	""" :class:`.WMessengerOnionCoderLayerProto` class implementation. This class translate message to corresponding
	hex-string, or decodes it from hex-string to original binary representation.
	"""

	__layer_name__ = "com.binblob.wasp-general.hex-layer"
	""" Layer name
	"""

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionCoderLayerProto.__init__(self, WMessengerHexLayer.__layer_name__)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerBytesEnvelope)
	def encode(self, envelope, session, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.encode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param kwargs: additional arguments

		:return: WMessengerTextEnvelope
		"""
		return WMessengerTextEnvelope(str(WHex(envelope.message())), meta=envelope)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerTextEnvelope)
	def decode(self, envelope, session, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.decode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param kwargs: additional arguments

		:return: WMessengerBytesEnvelope
		"""
		return WMessengerBytesEnvelope(bytes(WUnHex(envelope.message())), meta=envelope)


class WMessengerBase64Layer(WMessengerOnionCoderLayerProto):
	""" :class:`.WMessengerOnionCoderLayerProto` class implementation. This class translate binary message
	to the corresponding base64 encoded bytes, or decodes it from base64 encoded bytes to the original binary
	representation.
	"""

	__layer_name__ = "com.binblob.wasp-general.base64-layer"
	""" Layer name
	"""

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionCoderLayerProto.__init__(self, WMessengerBase64Layer.__layer_name__)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerBytesEnvelope)
	def encode(self, envelope, session, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.encode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param kwargs: additional arguments

		:return: WMessengerBytesEnvelope
		"""
		return WMessengerBytesEnvelope(b64encode(envelope.message()), meta=envelope)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerBytesEnvelope)
	def decode(self, envelope, session, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.decode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param kwargs: additional arguments

		:return: WMessengerBytesEnvelope
		"""
		return WMessengerBytesEnvelope(b64decode(envelope.message()), meta=envelope)


class WMessengerAESLayer(WMessengerOnionCoderLayerProto):
	""" :class:`.WMessengerOnionCoderLayerProto` class implementation. This class encrypts/decrypts message with
	the specified AES cipher
	"""

	__layer_name__ = "com.binblob.wasp-general.aes-layer"
	""" Layer name
	"""

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionCoderLayerProto.__init__(self, WMessengerAESLayer.__layer_name__)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerBytesEnvelope)
	@verify_type(aes_cipher=WAES)
	def encode(self, envelope, session, aes_cipher=None, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.encode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param aes_cipher: cipher to use
		:param kwargs: additional arguments

		:return: WMessengerBytesEnvelope
		"""
		return WMessengerBytesEnvelope(aes_cipher.encrypt(envelope.message()), meta=envelope)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerBytesEnvelope)
	@verify_type(aes_cipher=WAES)
	def decode(self, envelope, session, aes_cipher=None, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.decode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param aes_cipher: cipher to use
		:param kwargs: additional arguments

		:return: WMessengerBytesEnvelope
		"""
		return WMessengerBytesEnvelope(aes_cipher.decrypt(envelope.message(), decode=False), meta=envelope)


class WMessengerRSALayer(WMessengerOnionCoderLayerProto):
	""" :class:`.WMessengerOnionCoderLayerProto` class implementation. This class encrypts/decrypts message with
	specified RSA cipher
	"""

	__layer_name__ = "com.binblob.wasp-general.rsa-layer"
	""" Layer name
	"""

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionCoderLayerProto.__init__(self, WMessengerRSALayer.__layer_name__)

	@verify_type('paranoid', session=WMessengerOnionSessionProto, public_key=WRSA.wrapped_class, sha_digest_size=int)
	@verify_type(envelope=WMessengerBytesEnvelope)
	def encode(self, envelope, session, public_key=None, sha_digest_size=32, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.encode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param public_key: public key to encrypt
		:param sha_digest_size: SHA digest size to use
		:param kwargs: additional arguments

		:return: WMessengerBytesEnvelope
		"""
		message = WRSA.encrypt(envelope.message(), public_key, sha_digest_size=sha_digest_size)
		return WMessengerBytesEnvelope(message, meta=envelope)

	@verify_type('paranoid', session=WMessengerOnionSessionProto, private_key=WRSA.wrapped_class)
	@verify_type('paranoid', sha_digest_size=int)
	@verify_type(envelope=WMessengerBytesEnvelope)
	def decode(self, envelope, session, private_key=None, sha_digest_size=32, **kwargs):
		""" :meth:`.WMessengerOnionCoderLayerProto.decode` method implementation.

		:param envelope: original envelope
		:param session: original session
		:param private_key: private key to decrypt
		:param sha_digest_size: SHA digest size to use
		:param kwargs: additional arguments

		:return: WMessengerBytesEnvelope
		"""
		message = WRSA.decrypt(envelope.message(), private_key, sha_digest_size=sha_digest_size)
		return WMessengerBytesEnvelope(message, meta=envelope)
