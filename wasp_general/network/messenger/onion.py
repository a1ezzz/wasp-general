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

from abc import abstractmethod
from enum import Enum

from wasp_general.verify import verify_type

from wasp_general.network.messenger.proto import WMessengerOnionProto, WMessengerEnvelopeProto
from wasp_general.network.messenger.proto import WMessengerOnionSessionProto, WMessengerOnionLayerProto
from wasp_general.network.messenger.proto import WMessengerOnionSessionFlowProto

from wasp_general.network.messenger.envelope import WMessengerTextEnvelope, WMessengerBytesEnvelope
from wasp_general.network.messenger.session import WMessengerOnionSession


class WMessengerOnionCoderLayerBase(WMessengerOnionLayerProto):
	""" Class for layers, that are used for encryption/decryption, encoding/decoding. This layer class works with
	strings and bytes and as a result generates strings and bytes
	"""

	class Mode(Enum):
		""" Specifies layers mode
		"""
		encode = 1
		""" Encryption/encoding mode
		"""
		decode = 2
		""" Decryption/decoding mode
		"""

	@verify_type(envelope=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def process(self, envelope, session, **kwargs):
		""" :meth:`.WMessengerOnionLayerProto.process` implementation
		"""
		if 'mode' not in kwargs:
			raise RuntimeError('"mode" argument must be specified for this object')

		mode = kwargs['mode']
		if isinstance(mode, WMessengerOnionCoderLayerBase.Mode) is False:
			raise TypeError('Invalid "mode" argument')

		if mode == WMessengerOnionCoderLayerBase.Mode.encode:
			return self.encode(envelope, session, **kwargs)
		else:  # mode == WMessengerOnionCoderLayerBase.Mode.decode
			return self.decode(envelope, session, **kwargs)

	@abstractmethod
	@verify_type(envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope), session=WMessengerOnionSessionProto)
	def encode(self, envelope, session, **kwargs):
		""" Encrypt/encode message

		:param envelope: message to encrypt/encode
		:param session: original session
		:return: WMessengerTextEnvelope or WMessengerBytesEnvelope
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope), session=WMessengerOnionSessionProto)
	def decode(self, envelope, session, **kwargs):
		""" Decrypt/decode message

		:param envelope: message to decrypt/decode
		:param session: original session
		:return: WMessengerTextEnvelope or WMessengerBytesEnvelope
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnion(WMessengerOnionProto):
	""" :class:`.WMessengerOnionProto` implementation. This class holds layers
	(:class:`WMessengerOnionLayerProto` class) that can be used for message processing.
	"""

	@verify_type(layers=WMessengerOnionLayerProto)
	def __init__(self, *layers):
		""" Construct new onion

		:param layers: layers to store
		"""
		self.__layers = {}
		self.add_layers(*layers)

	def layers_names(self):
		""" :meth:`.WMessengerOnionProto.layer_names` method implementation.
		"""
		return list(self.__layers.keys())

	@verify_type(layer_name=str)
	def layer(self, layer_name):
		""" :meth:`.WMessengerOnionProto.layer` method implementation.
		"""
		try:
			return self.__layers[layer_name]
		except KeyError:
			raise RuntimeError('Invalid layer name')

	@verify_type(layer=WMessengerOnionLayerProto)
	def add_layers(self, *layers):
		""" Append given layers to this onion

		:param layers: layer to add
		:return: None
		"""
		for layer in layers:
			if layer.name() in self.__layers.keys():
				raise ValueError('Layer "%s" already exists' % layer.name())
			self.__layers[layer.name()] = layer
