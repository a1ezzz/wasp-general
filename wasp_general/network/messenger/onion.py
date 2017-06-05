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

# TODO: write tests

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from wasp_general.verify import verify_type

from wasp_general.network.messenger.proto import WMessengerOnionProto
from wasp_general.network.messenger.proto import WMessengerOnionLayerProto

from wasp_general.network.messenger.coders import WMessengerFixedModificationLayer, WMessengerEncodingLayer
from wasp_general.network.messenger.coders import WMessengerHexLayer, WMessengerBase64Layer, WMessengerAESLayer
from wasp_general.network.messenger.coders import WMessengerRSALayer

from wasp_general.network.messenger.packers import WMessengerJSONPacker

from wasp_general.network.messenger.transport import WMessengerSendAgentLayer, WMessengerSyncReceiveAgentLayer


class WMessengerOnion(WMessengerOnionProto):
	""" :class:`.WMessengerOnionProto` implementation. This class holds layers
	(:class:`WMessengerOnionLayerProto` class) that can be used for message processing.
	"""

	__builtin_layers__ = {x.name(): x for x in [
		WMessengerFixedModificationLayer(), WMessengerEncodingLayer(), WMessengerHexLayer(),
		WMessengerBase64Layer(), WMessengerAESLayer(), WMessengerRSALayer(), WMessengerJSONPacker(),
		WMessengerSendAgentLayer(), WMessengerSyncReceiveAgentLayer()
	]}
	""" Builtin layers
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
		return list(self.__class__.__builtin_layers__.keys()) + list(self.__layers.keys())

	@verify_type(layer_name=str)
	def layer(self, layer_name):
		""" :meth:`.WMessengerOnionProto.layer` method implementation.
		"""
		if layer_name in self.__layers.keys():
			return self.__layers[layer_name]
		elif layer_name in self.__class__.__builtin_layers__:
			return self.__class__.__builtin_layers__[layer_name]

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
