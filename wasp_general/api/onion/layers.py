# -*- coding: utf-8 -*-
# wasp_general/api/onion/layers.py
#
# Copyright (C) 2017-2019 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

import enum
import json
import asyncio
from base64 import b64encode, b64decode

from wasp_general.verify import verify_type, verify_value
from wasp_general.crypto.hex import WHex, WUnHex
from wasp_general.crypto.aes import WAES
from wasp_general.crypto.rsa import WRSA
from wasp_general.api.transformation import WTransformationRegistry, __default_transformation_registry__

from wasp_general.api.onion.proto import WOnionLayerProto, WEnvelopeProto
from wasp_general.api.onion.base import WEnvelope, register_class


@register_class
class WAsyncIOLayer(WOnionLayerProto):
	""" This layer will call a coroutine function with a single argument, which is a data from an envelope.
	Then this layer will wait for coroutine to finish and return its result to a following layer
	"""

	__layer_name__ = 'com.binblob.wasp-general.asyncio-layer'
	""" Layer name
	"""

	def __init__(self, coroutine_fn):
		""" Create new layer

		:param coroutine_fn: function to call and to wait for
		:type coroutine_fn: coroutine function
		"""
		WOnionLayerProto.__init__(self)
		if asyncio.iscoroutinefunction(coroutine_fn) is False:
			raise TypeError('The specified object is not a coroutine function')
		self.__coroutine_fn = coroutine_fn

	@verify_type('strict', envelope=WEnvelopeProto)
	async def process(self, envelope):
		""" :meth:`.WOnionLayerProto.process` method implementation
		:type envelope: WEnvelope
		:rtype: WEnvelope
		"""
		data = await self.__coroutine_fn(envelope.data())
		return WEnvelope(data, previous_meta=envelope)


# noinspection PyAbstractClass
class WOnionBaseLayerModes(WOnionLayerProto):
	""" Basic :class:`.WOnionLayerProto` class implementation that acts as a single layer but that does different
	operations. Such operations such as save and load operations or encryption or decryption operations and so on.

	Such operations (modes) that this class supports are defined as a Enum class. And for each enum entry there
	must be a method with a name of that entry and this method must have the same function signature as
	the original :meth:`.WOnionLayerProto.process`: method
	"""

	__modes__ = None
	""" This attribute must be overridden in derived classes with Enum class. Enum's entries will show
	which operations (modes) this class supports
	"""

	def __new__(cls, *args, **kwargs):
		""" Check that this class is valid (has all the required methods) and allocate it
		"""
		o = WOnionLayerProto.__new__(cls)
		if cls.__modes__ is None or issubclass(cls.__modes__, enum.Enum) is False:
			raise TypeError('Derived classes must redefine the "__modes__" attribute as an enum object')

		for i in cls.__modes__:
			if hasattr(o, i.name) is False:
				raise TypeError('Derived classes must define method for each entry in enum')
		return o

	@verify_type('strict', mode=enum.Enum)
	def __init__(self, mode):
		""" Create new layer instance

		:param mode: operation that this layer should do
		:type mode: enum.Enum
		"""
		WOnionLayerProto.__init__(self)
		if isinstance(mode, self.__modes__) is False:
			raise TypeError('The specified mode is not an entry from Enum')
		self.__mode = mode

	@verify_type('paranoid', envelope=WEnvelopeProto)
	async def process(self, envelope):
		""" :meth:`.WOnionLayerProto.process` method implementation
		:type envelope: WEnvelope
		:rtype: WEnvelope
		"""
		fn = getattr(self, self.__mode.name)
		data = await fn(envelope)
		if isinstance(data, WEnvelopeProto):
			return data
		return WEnvelope(data, previous_meta=envelope)


@enum.unique
class WLayerSerializationMode(enum.Enum):
	""" This enum may be used by layers that may serialize and deserialize some objects
	"""
	serialize = enum.auto()
	deserialize = enum.auto()


@enum.unique
class WLayerEncodingMode(enum.Enum):
	""" This enum may be used by layers that may encode and decode data
	"""
	encode = enum.auto()
	decode = enum.auto()


@enum.unique
class WLayerEncryptionMode(enum.Enum):
	""" This enum may be used by cryptographic layers
	"""
	encrypt = enum.auto()
	decrypt = enum.auto()


@register_class
class WOnionJSONLayer(WOnionBaseLayerModes):
	""" This layer may serialize some python objects into JSON format and back
	"""

	__layer_name__ = 'com.binblob.wasp-general.json-layer'
	""" Layer name
	"""

	__modes__ = WLayerSerializationMode
	""" Supported operations
	"""

	@verify_type('strict', envelope=WEnvelopeProto)
	async def serialize(self, envelope):
		""" Serialize object from an envelop
		:type envelope: WEnvelopeProto
		:rtype: WEnvelopeProto
		"""
		return json.dumps(envelope.data())

	@verify_type('strict', envelope=WEnvelopeProto)
	async def deserialize(self, envelope):
		""" Deserialize object from an envelop
		:type envelope: WEnvelopeProto
		:rtype: WEnvelopeProto
		"""
		return json.loads(envelope.data())


@register_class
class WOnionWrappingLayer(WOnionBaseLayerModes):
	""" This layer adds (or removes) fixed block to (or from) an envelope.
	"""

	@enum.unique
	class Mode(enum.Enum):
		""" This layer operation modes
		"""
		append = enum.auto()
		remove = enum.auto()

	@enum.unique
	class Target(enum.Enum):
		""" Defines a target where a fixed block will be appended to or will be removed from
		"""
		head = enum.auto()
		""" A fixed block will be applied to a beginning 
		"""
		tail = enum.auto()
		""" A fixed block will be applied to an end 
		"""

	__layer_name__ = 'com.binblob.wasp-general.wrapping-layer'
	""" Layer name
	"""

	__modes__ = Mode
	""" Supported operations
	"""

	@verify_type('strict', mode=Mode, target=Target, block=(str, bytes))
	def __init__(self, mode, target, block):
		""" Construct new layer

		:param mode: operation mode - whether this layer will append or remove a block
		:type mode: WOnionWrappingLayer.Mode

		:param target: defines a target where a fixed block will be applied
		:type target: WOnionWrappingLayer.Target

		:param block: a fixed block this layer will be applied. This block must have the same type as
		envelopes that this layer will be processing
		:type block: str | type
		"""
		WOnionBaseLayerModes.__init__(self, mode)
		self.__target = target
		self.__block = block

	@verify_type('strict', envelope=WEnvelopeProto)
	def __check_type(self, envelope):
		""" Check if an envelope may be processed by this layer

		:param envelope: envelope to check
		:type envelope: WEnvelopeProto

		:raise TypeError: if envelope data has invalid type

		:rtype: None
		"""
		if isinstance(envelope.data(), self.__block.__class__) is False:
			raise TypeError('Data that should be modified has other type then a block')

	@verify_type('paranoid', envelope=WEnvelopeProto)
	async def append(self, envelope):
		""" Append a fixed block to an envelope

		:param envelope: envelope to which a fixed block should be added to
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		self.__check_type(envelope)
		if self.__target == WOnionWrappingLayer.Target.head:
			return self.__block + envelope.data()

		assert (self.__target == WOnionWrappingLayer.Target.tail)
		return envelope.data() + self.__block

	@verify_type('paranoid', envelope=WEnvelopeProto)
	async def remove(self, envelope):
		""" Remove a fixed block from an envelope

		:param envelope: envelope to which a fixed block should be removed from
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		self.__check_type(envelope)
		envelope_data = envelope.data()
		block_length = len(self.__block)
		if self.__target == WOnionWrappingLayer.Target.head:
			if envelope_data[:block_length] != self.__block:
				raise ValueError('The data does not have a required header')
			return envelope_data[block_length:]
		else:
			assert (self.__target == WOnionWrappingLayer.Target.tail)
			if envelope_data[-block_length:] != self.__block:
				raise ValueError('The data does not have a required tail')
			return envelope_data[:-block_length]


@register_class
class WOnionEncodingLayer(WOnionBaseLayerModes):
	""" This layer can encode str-object to the related encoding (to the bytes-object). Or decode bytes-object from
	the specified encoding (from bytes-object to str-object)
	"""

	__layer_name__ = 'com.binblob.wasp-general.encoding-layer'
	""" Layer name
	"""

	__modes__ = WLayerEncodingMode
	""" Supported operations
	"""

	@verify_type('strict', mode=WLayerEncodingMode, encoding=(str, None))
	def __init__(self, mode, encoding=None):
		""" Construct new layer

		:param mode: operation mode
		:type mode: WLayerEncodingMode

		:param encoding: target encoding string object will be encoded to or from which it will be
		decoded. If this values is not specified then 'utf-8' is used
		:type encoding: str | None
		"""
		WOnionBaseLayerModes.__init__(self, mode)
		self.__encoding = encoding

	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), str))
	async def encode(self, envelope):
		""" Encode a string

		:param envelope: data to encode
		:type envelope: WEnvelopeProto

		:rtype: bytes
		"""
		if self.__encoding is not None:
			return envelope.data().encode(encoding=self.__encoding)
		return envelope.data().encode()

	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), bytes))
	async def decode(self, envelope):
		""" Decode bytes to a string

		:param envelope: data to decode
		:type envelope: WEnvelopeProto

		:rtype: str
		"""
		if self.__encoding is not None:
			return envelope.data().decode(encoding=self.__encoding)
		return envelope.data().decode()


@register_class
class WOnionHexLayer(WOnionBaseLayerModes):
	""" This class translate bytes to corresponding hex-string, or decodes it back
	"""

	__layer_name__ = 'com.binblob.wasp-general.hex-layer'
	""" Layer name
	"""

	__modes__ = WLayerEncodingMode
	""" Supported operations
	"""

	# noinspection PyMethodMayBeStatic
	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), bytes))
	async def encode(self, envelope):
		""" Convert bytes to a hex-string

		:param envelope: envelope to convert
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return str(WHex(envelope.data()))

	# noinspection PyMethodMayBeStatic
	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), str))
	async def decode(self, envelope):
		""" Convert a hex-string to bytes

		:param envelope: envelope to convert
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return bytes(WUnHex(envelope.data()))


@register_class
class WOnionBase64Layer(WOnionBaseLayerModes):
	""" This class translate bytes to corresponding base64-string, or decodes it back
	"""

	__layer_name__ = 'com.binblob.wasp-general.base64-layer'
	""" Layer name
	"""

	__modes__ = WLayerEncodingMode
	""" Supported operations
	"""

	# noinspection PyMethodMayBeStatic
	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), bytes))
	async def encode(self, envelope):
		""" Convert bytes to a base64-string

		:param envelope: envelope to convert
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return b64encode(envelope.data()).decode(encoding='ascii')

	# noinspection PyMethodMayBeStatic
	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), str))
	async def decode(self, envelope):
		""" Convert a base64-string to bytes

		:param envelope: envelope to convert
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return b64decode(envelope.data())


@register_class
class WOnionAESLayer(WOnionBaseLayerModes):
	""" This class encrypts or decrypts bytes with the specified AES cipher
	"""

	__layer_name__ = 'com.binblob.wasp-general.aes-layer'
	""" Layer name
	"""

	__modes__ = WLayerEncryptionMode
	""" Supported operations
	"""

	@verify_type('strict', mode=WLayerEncryptionMode, aes_cipher=WAES)
	def __init__(self, mode, aes_cipher):
		""" Construct new layer

		:param mode: operation mode
		:type mode: WLayerEncryptionMode

		:param aes_cipher: cipher to use
		:type aes_cipher: WAES
		"""
		WOnionBaseLayerModes.__init__(self, mode)
		self.__cipher = aes_cipher

	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), bytes))
	async def encrypt(self, envelope):
		""" Encrypt bytes

		:param envelope: envelope to encrypt
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return self.__cipher.encrypt(envelope.data())

	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), bytes))
	async def decrypt(self, envelope):
		""" Decrypt bytes

		:param envelope: envelope to decrypt
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return self.__cipher.decrypt(envelope.data(), decode=False)


@register_class
class WOnionRSALayer(WOnionBaseLayerModes):
	""" This class encrypts or decrypts bytes with the specified RSA cipher
	"""

	__layer_name__ = 'com.binblob.wasp-general.rsa-layer'
	""" Layer name
	"""

	__modes__ = WLayerEncryptionMode
	""" Supported operations
	"""

	@verify_type('strict', mode=WLayerEncryptionMode, rsa=WRSA, oaep_hash_fn_name=(str, None))
	@verify_type('strict', mgf1_hash_fn_name=(str, None))
	def __init__(self, mode, rsa, oaep_hash_fn_name=None, mgf1_hash_fn_name=None):
		""" Construct new layer

		:param mode: operation mode
		:type mode: WLayerEncryptionMode

		:param rsa: cipher to use
		:type rsa: WRSA

		:param oaep_hash_fn_name: encryption and decryption options. Some details are here - :class:`.WRSA`
		:type oaep_hash_fn_name: str | None

		:param mgf1_hash_fn_name: encryption and decryption options. Some details are here - :class:`.WRSA`
		:type mgf1_hash_fn_name: str | None
		"""
		WOnionBaseLayerModes.__init__(self, mode)

		if mode == WLayerEncryptionMode.encrypt and rsa.has_public_key() is False:
			raise ValueError('A public key must be specified for encryption')

		if mode == WLayerEncryptionMode.decrypt and rsa.has_private_key() is False:
			raise ValueError('A private key must be specified for decryption')

		self.__rsa = rsa
		self.__oaep_fn_name = oaep_hash_fn_name
		self.__mgf1_fn_name = mgf1_hash_fn_name

	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), bytes))
	async def encrypt(self, envelope):
		""" Encrypt bytes

		:param envelope: envelope to encrypt
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return self.__rsa.encrypt(
			envelope.data(), oaep_hash_fn_name=self.__oaep_fn_name, mgf1_hash_fn_name=self.__mgf1_fn_name
		)

	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x.data() is not None and isinstance(x.data(), bytes))
	async def decrypt(self, envelope):
		""" Decrypt bytes

		:param envelope: envelope to decrypt
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return self.__rsa.decrypt(
			envelope.data(), oaep_hash_fn_name=self.__oaep_fn_name, mgf1_hash_fn_name=self.__mgf1_fn_name
		)


@register_class
class WTransformationLayer(WOnionBaseLayerModes):
	""" This layer may "transform" object into with :class:`.WTransformationRegistry`. This layer may be used
	as a helper for serialization/deserialization layers
	"""

	__layer_name__ = 'com.binblob.wasp-general.transformation-layer'
	""" Layer name
	"""

	__modes__ = WLayerSerializationMode
	""" Supported operations
	"""

	@verify_type('strict', mode=WLayerSerializationMode, transformation_registry=(WTransformationRegistry, None))
	def __init__(self, mode, transformation_registry=None):
		""" Construct new layer

		:param mode: operation mode
		:type mode: WLayerSerializationMode

		:param transformation_registry: registry to use. or default one if variable is not set
		:type transformation_registry: WTransformationRegistry | None
		"""
		WOnionBaseLayerModes.__init__(self, mode)
		if transformation_registry is None:
			transformation_registry = __default_transformation_registry__
		self.__registry = transformation_registry

	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x is None or isinstance(x, object))
	async def serialize(self, envelope):
		""" "Dismantle" object into smaller parts

		:param envelope: object to "dismantle"
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return self.__registry.dismantle(envelope.data())

	@verify_type('strict', envelope=WEnvelopeProto)
	@verify_value('strict', envelope=lambda x: x is None or isinstance(x, object))
	async def deserialize(self, envelope):
		""" "Compile" object from smaller parts

		:param envelope: object to "compile"
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		return self.__registry.compose(envelope.data())
