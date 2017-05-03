# -*- coding: utf-8 -*-
# wasp_general/network/messenger/onion.py
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

# TODO: test and doc
# TODO: check transparent session switching from one set of layers to other set

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from enum import Enum
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_subclass


class WMessengerOnionBase(metaclass=ABCMeta):
	""" Abstract class for onion-messenger. Messengers job is divided into onions layers. Where each layer do its
	own small job. Layers are united in a session, that is used for message parsing and generation. Each layer
	has a name, which must be unique within single onion.

	Possible layer are transport encryption layers (rsa, aes,...), data-encoding layer (base64, utf8,...),
	dialect layers (shlex, json, pickle), authentication and authorization layers and many more.
	"""

	@abstractmethod
	@verify_type(layer_name=str)
	def layer(self, layer_name):
		""" Return messengers layer by its name

		:param layer_name: name of a layer
		:return: WMessengerOnionLayerBase instance
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def layers_names(self):
		""" Available layers names

		:return: list of str
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionSessionBase(metaclass=ABCMeta):
	""" Class represent messenger single session. Inside a onion messenger, this class process single message.
	"""

	@abstractmethod
	def onion(self):
		""" Return related onion. In most cases, it is the onion, that creates this session.
		:return: WMessengerOnionBase
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(message=(bytes, str, None))
	def process(self, message):
		""" Parse message and generate response

		:param message: incoming or outgoing message or nothing. This value is passed to the first layer as is.
		:return: outgoing message or nothing. In most cases, this is a server response or client request.
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionLayerBase:
	""" Messenger layer, that do one simple work like encryption, encoding, parsing and etc.
	"""

	@verify_type(name=str)
	def __init__(self, name):
		""" Construct new layer with given name

		:param name: name of the layer
		"""
		self.__name = name

	def name(self):
		""" Return layer name

		:return: str
		"""
		return self.__name

	@verify_type(session=WMessengerOnionSessionBase)
	def immerse(self, message, session):
		""" Parse, decrypt, decode message and go to the deepest layers. By default, returns origin message.

		:param message: message to parse/decrypt/decode. Could be any type
		:param session: related session
		:return: job result
		"""
		return message

	@verify_type(session=WMessengerOnionSessionBase)
	def rise(self, message, session):
		""" Combine, encrypt, encode message and go to the outer layers. By default, returns origin message.

		:param message: message to combine, encrypt, encode. Could be any type
		:param session: related session
		:return: job result
		"""
		return message


class WMessengerOnionCoderLayerBase(WMessengerOnionLayerBase):
	""" Class for layers, that are used for encryption/decryption, encoding/decoding. This layer class works with
	strings and bytes and as a result generates strings and bytes
	"""

	@verify_type(session=WMessengerOnionSessionBase)
	def immerse(self, message, session):
		""" :meth:`.WMessengerOnionLayerBase.immerse` method implementation. This method calls
		:meth:`WMessengerOnionCoderLayerBase.decode` instead and returns its result.
		"""
		return self.decode(message)

	@verify_type(session=WMessengerOnionSessionBase)
	def rise(self, message, session):
		""" :meth:`.WMessengerOnionLayerBase.rise` method implementation. This method calls
		:meth:`WMessengerOnionCoderLayerBase.encode` instead and returns its result.
		"""
		return self.encode(message)

	@abstractmethod
	@verify_type(message=(bytes, str))
	def encode(self, message):
		""" Encrypt/encode message

		:param message: message to encrypt/encode
		:return: str or bytes
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(message=(bytes, str))
	def decode(self, message):
		""" Decrypt/decode message

		:param message: message to decrypt/decode
		:return: str or bytes
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionLexicalLayerBase(WMessengerOnionLayerBase):
	""" Class for layers, that are used for message parsing and generating. As a parser/generato, this layer class
	works with any message types
	"""

	@verify_type(session=WMessengerOnionSessionBase)
	def immerse(self, message, session):
		""" :meth:`.WMessengerOnionLayerBase.immerse` method implementation. This method calls
		:meth:`WMessengerOnionCoderLayerBase.unpack` instead and returns its result.
		"""
		return self.unpack(message)

	@verify_type(session=WMessengerOnionSessionBase)
	def rise(self, message, session):
		""" :meth:`.WMessengerOnionLayerBase.rise` method implementation. This method calls
		:meth:`WMessengerOnionCoderLayerBase.pack` instead and returns its result.
		"""
		return self.pack(message)

	@abstractmethod
	def pack(self, message):
		""" Generate message by the given one
		:param message: original message
		:return: result can be any type
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def unpack(self, message):
		""" Parse given message
		:param message: original message
		:return: result can be any type
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionSessionFlow(metaclass=ABCMeta):
	""" This class is used in the following class :class:`.WMessengerOnionSession` for determine layer
	execution order.
	"""

	class Direction(Enum):
		""" Defines which method must be called for the given layer
		"""
		immerse = 1
		""" Defines :meth:`.WMessengerOnionLayerBase.immerse` method
		"""
		rise = 2
		""" Defines :meth:`.WMessengerOnionLayerBase.rise` method
		"""

	class Iterator:
		""" Class that describes layer, that must be executed next.
		"""

		@verify_type(layer_name=str)
		def __init__(self, layer_name, direction):
			""" Construct new descriptor

			:param layer_name: Layers name to be executed
			:param direction: Method to be executed (see :class:`WMessengerOnionSessionFlow.Direction`)
			"""
			if isinstance(direction, WMessengerOnionSessionFlow.Direction) is False:
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

			:return: WMessengerOnionSessionFlow.Direction
			"""
			return self.__direction

	@abstractmethod
	@verify_type(message=(bytes, str, None))
	def iterate(self, message=None):
		""" Iterate over layers order
		:param message: message to process (layer order may depend on message content)

		:return: WMessengerOnionSessionFlow.Iterator
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionSessionStrictFlow(WMessengerOnionSessionFlow):
	""" This is :class:`.WMessengerOnionSessionFlow` implementation, that "executes" layers in a strict order.
	At first, layers are executed in the same order, as they are defined in a class constructor
	(:meth:`.WMessengerOnionLayerBase.immerse` method is called). Then, layers are executed in reverse order
	(:meth:`.WMessengerOnionLayerBase.rise` method is called).
	"""

	@verify_type(layers=str)
	def __init__(self, *layers):
		""" Construct new iterator

		:param layers: layers names to be executed
		"""
		self.__layers = layers

	@verify_type(message=(bytes, str, None))
	def iterate(self, message=None):
		""" :meth:`.WMessengerOnionSessionFlow.__iter__` method implementation.
		"""

		for i in range(len(self.__layers)):
			yield WMessengerOnionSessionFlow.Iterator(
				self.__layers[i], WMessengerOnionSessionFlow.Direction.immerse
			)

		for i in range(len(self.__layers) - 1, -1, -1):
			yield WMessengerOnionSessionFlow.Iterator(
				self.__layers[i], WMessengerOnionSessionFlow.Direction.rise
			)


class WMessengerOnionSession(WMessengerOnionSessionBase):
	""" :class:`.WMessengerOnionSessionBase` class implementation. This class executes layers from onion in order
	they described in :class:`.WMessengerOnionSessionFlow` class
	"""

	@verify_type(onion=WMessengerOnionBase, session_flow=WMessengerOnionSessionFlow)
	def __init__(self, onion, session_flow):
		""" Construct new session.

		:param onion: related onion
		:param session_flow: defines layers order to be executed
		"""
		self.__onion = onion
		self.__session_flow = session_flow

	def onion(self):
		""" :meth:`.WMessengerOnionSessionBase.onion` method implementation.
		"""
		return self.__onion

	def session_flow(self):
		""" Return related :class:`.WMessengerOnionSessionFlow` object
		:return: WMessengerOnionSessionFlow
		"""
		return self.__session_flow

	@verify_type(message=(bytes, str, None))
	def process(self, message):
		""" :meth:`.WMessengerOnionSessionBase.process` method implementation.
		"""
		for layer_iter in self.session_flow().iterate(message):
			layer = self.onion().layer(layer_iter.layer_name())
			if layer_iter.direction() == WMessengerOnionSessionFlow.Direction.immerse:
				message = layer.immerse(message, self)
			elif layer_iter.direction() == WMessengerOnionSessionFlow.Direction.rise:
				message = layer.rise(message, self)
			else:
				raise RuntimeError('Unknown direction')
		return message


class WMessengerOnion(WMessengerOnionBase):
	""" :class:`.WMessengerOnionBase` implementation. This class creates session
	(:class:`WMessengerOnionSession` class) that can be used for message processing.
	"""

	@verify_type(layers=WMessengerOnionLayerBase)
	@verify_subclass(session_cls=(WMessengerOnionSession, None))
	def __init__(self, *layers, session_cls=None):
		""" Construct new onion

		:param layers: layers to store
		:param session_cls: class that is used for session generation
		"""
		self.__layers = {}
		self.add_layers(*layers)
		self.__session_cls = session_cls if session_cls is not None else WMessengerOnionSession

	def layers_names(self):
		""" :meth:`.WMessengerOnionBase.layer_names` method implementation.
		"""
		return list(self.__layers.keys())

	@verify_type(layer_name=str)
	def layer(self, layer_name):
		""" :meth:`.WMessengerOnionBase.layer` method implementation.
		"""
		try:
			return self.__layers[layer_name]
		except KeyError:
			raise ValueError('Invalid layer name')

	@verify_type(layer=WMessengerOnionLayerBase)
	def add_layers(self, *layers):
		""" Append given layers to this onion

		:param layers: layer to add
		:return: None
		"""
		for layer in layers:
			if layer.name() in self.__layers.keys():
				raise ValueError('Layer "%s" already exists' % layer.name())
			self.__layers[layer.name()] = layer

	@verify_type(session_flow=WMessengerOnionSessionFlow)
	def create_session(self, session_flow):
		""" Generate session with the given session flow

		:param session_flow: object that is used to construct :class:`.WMessengerOnionSession` object
		:return: WMessengerOnionSession
		"""
		return self.__session_cls(self, session_flow)
