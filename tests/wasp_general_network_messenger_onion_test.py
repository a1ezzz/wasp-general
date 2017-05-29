# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.proto import WMessengerOnionProto, WMessengerOnionLayerProto

from wasp_general.network.messenger.onion import WMessengerOnion


class TestWMessengerOnion:

	class Layer(WMessengerOnionLayerProto):
		def process(self, envelope, session, **kwargs):
			pass

	def test(self):
		assert(isinstance(WMessengerOnion(), WMessengerOnion) is True)
		assert(isinstance(WMessengerOnion(), WMessengerOnionProto) is True)

		layer1 = TestWMessengerOnion.Layer('layer1')
		layer2 = TestWMessengerOnion.Layer('layer2')

		o = WMessengerOnion(layer1, layer2)
		layers = o.layers_names()
		layers.sort()
		assert(layers == ['layer1', 'layer2'])

		pytest.raises(ValueError, o.add_layers, TestWMessengerOnion.Layer('layer1'))

		assert(o.layer('layer1') == layer1)
		assert(o.layer('layer2') == layer2)

		pytest.raises(RuntimeError, o.layer, 'layer3')
