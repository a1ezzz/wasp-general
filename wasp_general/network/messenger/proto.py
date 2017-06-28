# -*- coding: utf-8 -*-
# wasp_general/network/messenger/proto.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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


# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type


class WMessengerOnionProto(metaclass=ABCMeta):
	""" Abstract class for onion-messenger. Messengers job is divided into onions layers. Where each layer do its
	own small job. Layers are united in a session, that is used for message parsing or generation. Each layer
	has a name, which must be unique within single onion.

	Possible layer are transport encryption/decryption layers (rsa, aes,...), data encoding/decoding
	layers (base64, utf8,...), structure packing/unpacking layers (json, pickle, ...),
	lexical layers (shlex, json, pickle, ...), authentication/authorization layers and many more.
	"""

	@abstractmethod
	@verify_type(layer_name=str)
	def layer(self, layer_name):
		""" Return messengers layer by its name

		:param layer_name: name of a layer
		:return: WMessengerOnionLayerProto instance
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def layers_names(self):
		""" Available layers names

		:return: list of str
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerEnvelopeProto(metaclass=ABCMeta):
	""" Each real processed message is wrapped in this class. This helps in object type checking (layers can
	check if message is a subclass of some envelope subclass) and helps to keep meta data, that may be
	generated/processed by layers
	"""

	@abstractmethod
	def message(self):
		""" Return real message. It can be anything - string, bytes, structure...

		:return: any-type object or None
		"""
		raise NotImplementedError('This method is abstract')

	def meta(self):
		""" Return message meta data (dictionary object). For dictionary keys, values usage scenario
		see current implementation (:class:`.WMessengerEnvelope`)

		:return: dict
		"""
		return {}


class WMessengerOnionSessionProto(metaclass=ABCMeta):
	""" Class represent messenger single session. Inside a onion messenger, this class process single message.
	"""

	@abstractmethod
	def onion(self):
		""" Return related onion. In most cases, it is the onion, that creates this session.
		:return: WMessengerOnionProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(envelope=(WMessengerEnvelopeProto, None))
	def process(self, envelope):
		""" Parse message, process it and generate response

		:param envelope: incoming or outgoing message or nothing. This value is passed to the first layer as is.
		:return: outgoing message or nothing. In most cases, this is a server response or client request.
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionLayerProto(metaclass=ABCMeta):
	""" Messenger layer, that do one simple job like encryption, encoding, parsing and etc.
	"""

	@verify_type(name=str)
	def __init__(self, name):
		""" Construct new layer with the given name

		:param name: name of the layer
		"""
		self.__name = name

	def name(self):
		""" Return the layer name

		:return: str
		"""
		return self.__name

	@abstractmethod
	@verify_type(envelope=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def process(self, envelope, session, **kwargs):
		""" Parse/combine, decrypt/encrypt, decode/encode message.

		:param envelope: message to parse/combine/decrypt/encrypt/decode/encode
		:param session: related session
		:param kwargs: arguments that help to customize a layer (they are set in \
		:class:`.WMessengerOnionSessionFlowProto.IteratorInfo` objects)

		:return: WMessengerEnvelopeProto
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionSessionFlowProto(metaclass=ABCMeta):
	""" This class is used in the following class :class:`.WMessengerOnionSessionProto` to determine layer
	execution order.
	"""

	class IteratorInfo:
		""" Class that describes single layer call
		"""

		@verify_type(layer_name=str)
		def __init__(self, layer_name, **kwargs):
			""" Construct new descriptor

			:param layer_name: Layer name to be executed
			:param kwargs: layer arguments. see :meth:`.WMessengerOnionLayerProto.process` method
			"""
			self.__layer_name = layer_name
			self.__layer_kwargs = kwargs

		def layer_name(self):
			""" Return layer name

			:return: str
			"""
			return self.__layer_name

		def layer_args(self):
			""" Return layer arguments

			:return: dict
			"""
			return self.__layer_kwargs

	class Iterator(IteratorInfo):
		""" Iterator that is used to determine layers call sequence. Each iterator holds information for
		current layer call (:class:`.WMessengerOnionSessionFlowProto.IteratorInfo`) and layer to be called
		next. Iterators next layer (next iterator) can be defined at a runtime.
		"""

		@verify_type('paranoid', layer_name=str)
		def __init__(self, layer_name, next_iterator=None, **kwargs):
			""" Create iterator with the specified layer call information and the layer to be called next.

			:param layer_name: same as layer_name \
			in :meth:`WMessengerOnionSessionFlowProto.IteratorInfo.__init__` method
			:param next_iterator: For static execution order - next layer that should be called
			"""
			WMessengerOnionSessionFlowProto.IteratorInfo.__init__(self, layer_name, **kwargs)
			if next_iterator is not None:
				if isinstance(next_iterator, WMessengerOnionSessionFlowProto.IteratorInfo) is False:
					raise TypeError('Invalid type for next_iterator argument')
			self.__next_iterator = next_iterator

		@verify_type('paranoid', envelope=WMessengerEnvelopeProto)
		def next(self, envelope):
			""" Return next layer (iterator) to be called or None to stop execution

			:param envelope: message that was processed by a layer specified in this class
			:return: WMessengerOnionSessionFlowProto.Iterator or None
			"""
			return self.__next_iterator

	@abstractmethod
	@verify_type(envelope=WMessengerEnvelopeProto)
	def iterator(self, envelope):
		""" Return iterator to be used for message processing. Iterator may depend on incoming message

		:param envelope: original incoming message
		:return: WMessengerOnionSessionFlowProto.Iterator or None if there is no way to create session for the \
		given message
		"""
		raise NotImplementedError('This method is abstract')
