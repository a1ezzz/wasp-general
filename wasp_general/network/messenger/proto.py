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
from enum import Enum

from wasp_general.verify import verify_type


class WMessengerOnionProto(metaclass=ABCMeta):
	""" Abstract class for onion-messenger. Messengers job is divided into onions layers. Where each layer do its
	own small job. Layers are united in a session, that is used for message parsing or generation. Each layer
	has a name, which must be unique within single onion.

	Possible layer are transport encryption layers (rsa, aes,...), data-encoding layer (base64, utf8,...),
	structure packing layers (json, pickle, ...), lexical layers (shlex, ...), authentication layers,
	authorization layers and many more.
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
	def raw(self):
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
	@verify_type(message=(WMessengerEnvelopeProto, None))
	def process(self, message):
		""" Parse message, process it and generate response

		:param message: incoming or outgoing message or nothing. This value is passed to the first layer as is.
		:return: outgoing message or nothing. In most cases, this is a server response or client request.
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionLayerProto:
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

	@verify_type(message=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def immerse(self, message, session):
		""" Parse, decrypt, decode message and go to the deepest layers. By default, returns origin message.

		:param message: message to parse/decrypt/decode. Can be any type
		:param session: related session
		:return: job result
		"""
		return message

	@verify_type(message=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def rise(self, message, session):
		""" Combine, encrypt, encode message and go to the outer layers. By default, returns origin message.

		:param message: message to combine, encrypt, encode. Can be any type
		:param session: related session
		:return: job result
		"""
		return message


class WMessengerOnionSessionFlowProto(metaclass=ABCMeta):
	""" This class is used in the following class :class:`.WMessengerOnionSessionProto` to determine layer
	execution order.
	"""

	class Direction(Enum):
		""" Defines which method must be called for the given layer
		"""
		immerse = 1
		""" Defines :meth:`.WMessengerOnionLayerProto.immerse` method
		"""
		rise = 2
		""" Defines :meth:`.WMessengerOnionLayerProto.rise` method
		"""

	class IteratorInfo:
		""" Class that describes single layer call
		"""

		@verify_type(layer_name=str)
		def __init__(self, layer_name, direction):
			""" Construct new descriptor

			:param layer_name: Layer name to be executed
			:param direction: Method to be executed (see :class:`WMessengerOnionSessionFlowProto.Direction`)
			"""
			if isinstance(direction, WMessengerOnionSessionFlowProto.Direction) is False:
				raise TypeError('Invalid type for direction argument')
			self.__layer_name = layer_name
			self.__direction = direction

		def layer_name(self):
			""" Return layer name

			:return: str
			"""
			return self.__layer_name

		def direction(self):
			""" Return layer method

			:return: WMessengerOnionSessionFlowProto.Direction
			"""
			return self.__direction

	class Iterator(IteratorInfo):
		""" Iterator that is used to determine layers call sequence. Each iterator holds information for
		current layer call (:class:`.WMessengerOnionSessionFlowProto.IteratorInfo`) and layer to be called
		next. Iterators next layer (next iterator) can be defined at a runtime.
		"""

		@verify_type(layer_name=str)
		def __init__(self, layer_name, direction, next_iterator=None):
			""" Create iterator with the specified layer call information and the layer to be called next.

			:param layer_name: same as layer_name \
			in :meth:`WMessengerOnionSessionFlowProto.IteratorInfo.__init__` method
			:param direction: same as direction \
			in :meth:`WMessengerOnionSessionFlowProto.IteratorInfo.__init__` method
			:param next_iterator: For static execution order - next layer that should be called
			"""
			WMessengerOnionSessionFlowProto.IteratorInfo.__init__(self, layer_name, direction)
			if next_iterator is not None:
				if isinstance(next_iterator, WMessengerOnionSessionFlowProto.IteratorInfo) is False:
					raise TypeError('Invalid type for next_iterator argument')
			self.__next_iterator = next_iterator

		@verify_type(message=(WMessengerEnvelopeProto, None))
		def next(self, message=None):
			""" Return next layer (iterator) to be called or None to stop execution

			:param message: message that was processed by a layer specified in this class
			:return: WMessengerOnionSessionFlowProto.Iterator or None
			"""
			# TODO: check if 'None' value is suitable here
			return self.__next_iterator

	@abstractmethod
	@verify_type(message=(WMessengerEnvelopeProto, None))
	def iterator(self, message=None):
		""" Return iterator to be used for message processing. Iterator may depend on incoming message

		:param message: original incoming message
		:return: WMessengerOnionSessionFlowProto.Iterator
		"""
		# TODO: check if 'None' value is suitable here
		raise NotImplementedError('This method is abstract')
