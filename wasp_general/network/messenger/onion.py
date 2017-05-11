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

# TODO: document the code
# TODO: check transparent session switching from one set of layers to other set

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from enum import Enum
import re
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

	class IteratorInfo:
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

	class Iterator(IteratorInfo):

		@verify_type(layer_name=str)
		def __init__(self, layer_name, direction, next_iterator=None):
			WMessengerOnionSessionFlow.IteratorInfo.__init__(self, layer_name, direction)
			if next_iterator is not None:
				if isinstance(next_iterator, WMessengerOnionSessionFlow.IteratorInfo) is False:
					raise TypeError('Invalid type for next_iterator argument')
			self.__next_iterator = next_iterator

		@verify_type(message=(bytes, str, None))
		def next(self, message=None):
			return self.__next_iterator

	@abstractmethod
	@verify_type(message=(bytes, str, None))
	def iterator(self, message=None):
		raise NotImplementedError('This method is abstract')


class WMessengerOnionSessionBasicFlow(WMessengerOnionSessionFlow):

	@verify_type(iterator=(WMessengerOnionSessionFlow.IteratorInfo, None))
	def __init__(self, iterator=None):
		WMessengerOnionSessionFlow.__init__(self)
		self.__iterator = iterator

	@verify_type(message=(bytes, str, None))
	def iterator(self, message=None):
		return self.__iterator

	@classmethod
	@verify_type(iterators=WMessengerOnionSessionFlow.IteratorInfo)
	def sequence(cls, *info):
		if len(info) == 0:
			return

		info = list(info)
		info.reverse()

		result = WMessengerOnionSessionFlow.Iterator(
			info[0].layer_name(), info[0].direction()
		)

		for i in range(1, len(info)):
			result = WMessengerOnionSessionFlow.Iterator(
				info[i].layer_name(), info[i].direction(), result
			)

		return result

	@staticmethod
	@verify_type(iterators=WMessengerOnionSessionFlow.IteratorInfo)
	def sequence_flow(*info):
		return WMessengerOnionSessionBasicFlow(WMessengerOnionSessionBasicFlow.sequence(*info))

	@classmethod
	@verify_type(direction=WMessengerOnionSessionFlow.Direction, layers=str)
	def one_direction(cls, direction, *layers):
		return cls.sequence(*list(map(
			lambda name: WMessengerOnionSessionFlow.IteratorInfo(name, direction), layers
		)))

	@staticmethod
	@verify_type(direction=WMessengerOnionSessionFlow.Direction, layers=str)
	def one_direction_flow(direction, *layers):
		return WMessengerOnionSessionBasicFlow(WMessengerOnionSessionBasicFlow.one_direction(direction, *layers))


class WMessengerOnionSessionFlowSequence(WMessengerOnionSessionBasicFlow):

	class FlowSequenceIterator(WMessengerOnionSessionFlow.Iterator):
		@verify_type(info=WMessengerOnionSessionFlow.IteratorInfo, flows=WMessengerOnionSessionFlow)
		def __init__(self, info, *flows):
			WMessengerOnionSessionFlow.Iterator.__init__(self, info.layer_name(), info.direction())

			self.__flows = list(flows)
			self.__current_flow = None
			self.__iterator = None

		@verify_type(message=(bytes, str, None))
		def __next_flow(self, message=None):
			self.__current_flow = (self.__current_flow + 1) if self.__current_flow is not None else 0
			if self.__current_flow < len(self.__flows):
				self.__iterator = self.__flows[self.__current_flow].iterator(message=message)
				if self.__iterator is None:
					self.__next_flow(message)

		@verify_type(message=(bytes, str, None))
		def next(self, message=None):
			if self.__iterator is not None:
				self.__iterator = self.__iterator.next(message=message)

			if self.__iterator is None:
				self.__next_flow(message)

			if self.__iterator is not None:
				return self

		def layer_name(self):
			if self.__current_flow is None:
				return WMessengerOnionSessionFlow.Iterator.layer_name(self)
			return self.__iterator.layer_name()

		def direction(self):
			if self.__current_flow is None:
				return WMessengerOnionSessionFlow.Iterator.direction(self)
			return self.__iterator.direction()

	@verify_type(flows=WMessengerOnionSessionFlow)
	def __init__(self, *flows):
		WMessengerOnionSessionBasicFlow.__init__(self)
		self.__flows = flows

	@verify_type(direction=WMessengerOnionSessionFlow.Direction, layers=str)
	def iterator(self, message=None):
		iterator = WMessengerOnionSessionFlowSequence.FlowSequenceIterator(
			WMessengerOnionSessionFlow.IteratorInfo('', WMessengerOnionSessionFlow.Direction.immerse),
			*self.__flows
		)
		return iterator.next(message=message)


class WMessengerOnionSessionReverseFlow(WMessengerOnionSessionBasicFlow):

	class FlowReverseIterator(WMessengerOnionSessionFlow.Iterator):
		@verify_type(iterator=WMessengerOnionSessionFlow.Iterator, strict_direction=bool)
		def __init__(self, iterator, strict_direction=False):
			WMessengerOnionSessionFlow.Iterator.__init__(self, iterator.layer_name(), iterator.direction())

			self.__iterator = iterator
			self.__main_direction = iterator.direction() if strict_direction is True else None
			self.__index = -1
			self.__info = []
			self.__save_iterator(iterator)

		@verify_type(iterator=WMessengerOnionSessionFlow.Iterator)
		def __save_iterator(self, iterator):
			direction = iterator.direction()
			if self.__main_direction is not None and direction != self.__main_direction:
				raise RuntimeError('Multiple direction spotted')
			self.__info.append(
				WMessengerOnionSessionFlow.IteratorInfo(iterator.layer_name(), direction)
			)

		@verify_type(message=(bytes, str, None))
		def next(self, message=None):
			if self.__iterator is not None:
				self.__iterator = self.__iterator.next(message=message)
				if self.__iterator is not None:
					self.__save_iterator(self.__iterator)
				return self
			elif abs(self.__index) < len(self.__info):
				self.__index -= 1
				return self

		def layer_name(self):
			return self.__info[self.__index].layer_name()

		def direction(self):
			base_direction = self.__info[self.__index].direction()
			if self.__iterator is not None:
				return base_direction
			elif base_direction == WMessengerOnionSessionFlow.Direction.immerse:
				return WMessengerOnionSessionFlow.Direction.rise
			else:  # base_direction == WMessengerOnionSessionFlow.Direction.rise:
				return WMessengerOnionSessionFlow.Direction.immerse

	@verify_type(flow=WMessengerOnionSessionFlow, strict_direction=bool)
	def __init__(self, flow, strict_direction=False):
		WMessengerOnionSessionBasicFlow.__init__(self)
		self.__flow = flow
		self.__strict_direction = strict_direction

	@verify_type(message=(bytes, str, None))
	def iterator(self, message=None):
		iterator = self.__flow.iterator(message)
		if iterator is not None:
			return WMessengerOnionSessionReverseFlow.FlowReverseIterator(
				iterator, strict_direction=self.__strict_direction
			)


class WMessengerOnionSessionFlexFlow(WMessengerOnionSessionBasicFlow):

	class MessageComparator(metaclass=ABCMeta):

		@abstractmethod
		@verify_type(message=(bytes, str, None))
		def match(self, message=None):
			raise NotImplementedError('This method is abstract')

	class ReComparator(MessageComparator):

		@verify_type(pattern=(str, bytes))
		def __init__(self, pattern):
			WMessengerOnionSessionFlexFlow.MessageComparator.__init__(self)
			self.__re = re.compile(pattern)

		@verify_type(message=(bytes, str, None))
		def match(self, message=None):
			return message is not None and (self.__re.match(message) is not None)

	class FlowComparatorPair:

		@verify_type(flow=WMessengerOnionSessionFlow)
		def __init__(self, comparator, flow):
			if isinstance(comparator, WMessengerOnionSessionFlexFlow.MessageComparator) is False:
				raise TypeError('Invalid type for comparator argument')

			self.__comparator = comparator
			self.__flow = flow

		def comparator(self):
			return self.__comparator

		def flow(self):
			return self.__flow

	@verify_type(default_flow=(WMessengerOnionSessionFlow, None))
	def __init__(self, *flow_comparator_pairs, default_flow=None):
		WMessengerOnionSessionBasicFlow.__init__(self)
		self.__pairs = []
		for pair in flow_comparator_pairs:
			if isinstance(pair, WMessengerOnionSessionFlexFlow.FlowComparatorPair) is False:
				raise TypeError('Invalid type for flow-comparator pair argument')
			self.__pairs.append(pair)
		self.__default_flow = default_flow

	@verify_type(message=(bytes, str, None))
	def iterator(self, message=None):
		for pair in self.__pairs:
			if pair.comparator().match(message) is True:
				return pair.flow().iterator(message)

		if self.__default_flow is not None:
			return self.__default_flow.iterator(message)


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

		def process_single_layer(iter_message, iter_obj):
			layer_direction = iter_obj.direction()
			layer = self.onion().layer(iter_obj.layer_name())

			if layer_direction == WMessengerOnionSessionFlow.Direction.immerse:
				return layer.immerse(iter_message, self)
			elif layer_direction == WMessengerOnionSessionFlow.Direction.rise:
				return layer.rise(iter_message, self)
			else:
				raise RuntimeError('Unknown direction')

		iterator = self.session_flow().iterator()
		if iterator is not None:
			while iterator is not None:
				message = process_single_layer(message, iterator)
				iterator = iterator.next(message)
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
