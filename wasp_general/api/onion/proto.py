# -*- coding: utf-8 -*-
# wasp_general/onion/proto.py
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

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value

from wasp_general.api.registry import WAPIRegistryProto


class WEnvelopeProto(metaclass=ABCMeta):
	""" Each real data is wrapped in this class. These object keep meta data, that may be generated/processed
	by layers
	"""

	@abstractmethod
	def data(self):
		""" Return a real data. It can be anything - string, bytes, structure...

		:rtype: any
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', layer_name=(str, None))
	@verify_value('strict', layer_name=lambda x: x is None or len(x) > 0)
	def layers(self, layer_name=None):
		""" Iterate over layer's names and theirs meta that this envelop has been processed by

		:param layer_name: name of layers, which meta data should be returned (None if all the layers are
		required)
		:type layer_name: str | None

		:rtype: generator
		"""
		raise NotImplementedError('This method is abstract')


class WOnionLayerProto(metaclass=ABCMeta):
	""" A single layer, that do one simple job like encryption, encoding, parsing and etc.
	"""

	@classmethod
	@abstractmethod
	def name(cls):
		""" Return this layer's name

		:rtype: str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', envelope=WEnvelopeProto)
	async def process(self, envelope):
		""" Parse/combine, decrypt/encrypt, decode/encode a data.

		:param envelope: a data to parse/combine/decrypt/encrypt/decode/encode
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		raise NotImplementedError('This method is abstract')


class WOnionSessionFlowProto(metaclass=ABCMeta):
	""" This class is used by the :class:`.WOnionSessionProto` class for determination of layer's execution order.
	"""

	class LayerInfo:
		""" Class that describes a single layer call
		"""

		@verify_type(layer_name=str)
		@verify_value('strict', layer_name=lambda x: len(x) > 0)
		def __init__(self, layer_name, *args, **kwargs):
			""" Construct new descriptor

			:param layer_name: Layer name to be executed
			:type layer_name: str

			:param args: Layer arguments with which exact :class:`.WOnionLayerProto` subclass object will
			be constructed
			:type args: any

			:param kwargs: Layer arguments with which exact :class:`.WOnionLayerProto` subclass object will
			be constructed
			:type kwargs: any
			"""
			self.__layer_name = layer_name
			self.__layer_args = args
			self.__layer_kwargs = kwargs

		def layer_name(self):
			""" Return layer name

			:rtype: str
			"""
			return self.__layer_name

		def layer_args(self):
			""" Return layer's positional arguments

			:rtype: tuple
			"""
			return self.__layer_args

		def layer_kwargs(self):
			""" Return layer's named arguments

			:rtype: dict
			"""
			return self.__layer_kwargs

	@abstractmethod
	@verify_type('strict', envelope=WEnvelopeProto)
	def next(self, envelope):
		""" Return a pair (tuple) of layer information (:class`.WOnionSessionFlowProto.LayerInfo`
		class) that should process the specified envelope and the next session flow
		(:class`.WOnionSessionFlowProto` class) that will define what layer will be the next one

		If a layer information is None then there is no layers left for the specified envelope.
		If a session flow is None then this is a final layer no more layer left to be used

		:param envelope: envelope that the next layer will process
		:type envelope: WEnvelopeProto

		:rtype: (WOnionSessionFlowProto.LayerInfo | None, WOnionSessionFlowProto | None)
		"""
		raise NotImplementedError('This method is abstract')


class WOnionProto(WAPIRegistryProto):
	""" Abstract class for a onion - a collection of layers and layers processor. A processing job is splitted
	into onions layers. Where each layer do it's own small job. Layers are united in a session, that manages
	job's workflow. Each layer has a name, which must be unique within a single onion.

	Possible layer are transport encryption/decryption layers (rsa, aes,...), data encoding/decoding
	layers (base64, utf8,...), structure packing/unpacking layers (json, pickle, ...),
	serialization/deserialization layers (shlex, json, pickle, ...), authentication/authorization layers and
	many more.

	All the layers this onion process are stored inside
	"""

	@verify_type('strict', layer_name=str)
	@verify_value('strict', layer_name=lambda x: len(x) > 0)
	def layer(self, layer_name):
		""" Return layer by its name. This is an alias to :meth:`.WAPIRegistryProto.get` method

		:param layer_name: name of a layer
		:type layer_name: str

		:rtype: type (subclass of WOnionLayerProto)
		"""
		return self.get(layer_name)

	def layers_names(self):
		""" Available layers names. This is an alias to :meth:`.WAPIRegistryProto.ids` method

		:rtype: generator of str
		"""
		return self.ids()

	@abstractmethod
	@verify_type('strict', session_flow=WOnionSessionFlowProto, envelope=WEnvelopeProto)
	async def process(self, session_flow, envelope):
		""" Process an input data

		:param session_flow: defines workflow of what layers and with which parameters will be called
		:type session_flow: WOnionSessionFlowProto

		:param envelope: data to process. This value is passed to the first layer as is.
		:type envelope: WEnvelopeProto

		:rtype: WEnvelopeProto
		"""
		raise NotImplementedError('This method is abstract')
