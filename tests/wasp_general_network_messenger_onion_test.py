# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.proto import WMessengerOnionLayerProto, WMessengerOnionSessionFlowProto
from wasp_general.network.messenger.proto import WMessengerOnionProto
from wasp_general.network.messenger.envelope import WMessengerEnvelope, WMessengerTextEnvelope
from wasp_general.network.messenger.session import WMessengerOnionSession, WMessengerOnionSessionFlow

from wasp_general.network.messenger.onion import WMessengerOnionCoderLayerBase, WMessengerOnion


def test_abstract():
	envelope = WMessengerTextEnvelope('')
	onion = WMessengerOnion()
	session_flow = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
	session = WMessengerOnionSession(onion, session_flow)

	pytest.raises(TypeError, WMessengerOnionCoderLayerBase)
	pytest.raises(NotImplementedError, WMessengerOnionCoderLayerBase.encode, None, envelope, session)
	pytest.raises(NotImplementedError, WMessengerOnionCoderLayerBase.decode, None, envelope, session)


class TestWMessengerOnionCoderLayerBase:

	class Coder(WMessengerOnionCoderLayerBase):
		state = []

		def encode(self, envelope, session, **kwargs):
			self.state.append('encoded')
			return envelope

		def decode(self, envelope, session, **kwargs):
			self.state.append('decoded')
			return envelope

	def test(self):

		c = TestWMessengerOnionCoderLayerBase.Coder('layer1')
		assert(isinstance(c, WMessengerOnionCoderLayerBase) is True)
		assert(isinstance(c, WMessengerOnionLayerProto) is True)

		envelope = WMessengerTextEnvelope('')
		onion = WMessengerOnion()
		sf = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
		session = WMessengerOnionSession(onion, sf)
		pytest.raises(RuntimeError, c.process, envelope, session)

		assert(TestWMessengerOnionCoderLayerBase.Coder.state == [])
		c.process(envelope, session, mode=WMessengerOnionCoderLayerBase.Mode.encode)
		assert(TestWMessengerOnionCoderLayerBase.Coder.state == ['encoded'])

		c.process(envelope, session, mode=WMessengerOnionCoderLayerBase.Mode.decode)
		assert(TestWMessengerOnionCoderLayerBase.Coder.state == ['encoded', 'decoded'])

		pytest.raises(TypeError, c.process, envelope, session, mode=1)


class TestWMessengerOnion:

	def test(self):
		assert(isinstance(WMessengerOnion(), WMessengerOnion) is True)
		assert(isinstance(WMessengerOnion(), WMessengerOnionProto) is True)

		layer1 = TestWMessengerOnionCoderLayerBase.Coder('layer1')
		layer2 = TestWMessengerOnionCoderLayerBase.Coder('layer2')

		o = WMessengerOnion(layer1, layer2)
		layers = o.layers_names()
		layers.sort()
		assert(layers == ['layer1', 'layer2'])

		pytest.raises(ValueError, o.add_layers, TestWMessengerOnionCoderLayerBase.Coder('layer1'))

		assert(o.layer('layer1') == layer1)
		assert(o.layer('layer2') == layer2)

		pytest.raises(RuntimeError, o.layer, 'layer3')
