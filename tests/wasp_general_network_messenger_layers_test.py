# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.proto import WMessengerOnionLayerProto, WMessengerOnionSessionFlowProto
from wasp_general.network.messenger.proto import WMessengerOnionProto
from wasp_general.network.messenger.envelope import WMessengerTextEnvelope
from wasp_general.network.messenger.session import WMessengerOnionSession, WMessengerOnionSessionFlow

from wasp_general.network.messenger.layers import WMessengerOnionCoderLayerProto


def test_abstract():
	envelope = WMessengerTextEnvelope('')
	onion = TestWMessengerOnionCoderLayerBase.Onion()
	session_flow = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
	session = WMessengerOnionSession(onion, session_flow)

	pytest.raises(TypeError, WMessengerOnionCoderLayerProto)
	pytest.raises(NotImplementedError, WMessengerOnionCoderLayerProto.encode, None, envelope, session)
	pytest.raises(NotImplementedError, WMessengerOnionCoderLayerProto.decode, None, envelope, session)


class TestWMessengerOnionCoderLayerBase:

	class Onion(WMessengerOnionProto):
		def __init__(self):
			self.storage = {}

		def layers_names(self):
			return self.storage.keys()

		def layer(self, layer_name):
			return self.storage[layer_name]

	class Coder(WMessengerOnionCoderLayerProto):
		state = []

		def encode(self, envelope, session, **kwargs):
			self.state.append('encoded')
			return envelope

		def decode(self, envelope, session, **kwargs):
			self.state.append('decoded')
			return envelope

	def test(self):

		c = TestWMessengerOnionCoderLayerBase.Coder('layer1')
		assert(isinstance(c, WMessengerOnionCoderLayerProto) is True)
		assert(isinstance(c, WMessengerOnionLayerProto) is True)

		envelope = WMessengerTextEnvelope('')
		onion = TestWMessengerOnionCoderLayerBase.Onion()
		sf = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
		session = WMessengerOnionSession(onion, sf)
		pytest.raises(RuntimeError, c.process, envelope, session)

		assert(TestWMessengerOnionCoderLayerBase.Coder.state == [])
		c.process(envelope, session, mode=WMessengerOnionCoderLayerProto.Mode.encode)
		assert(TestWMessengerOnionCoderLayerBase.Coder.state == ['encoded'])

		c.process(envelope, session, mode=WMessengerOnionCoderLayerProto.Mode.decode)
		assert(TestWMessengerOnionCoderLayerBase.Coder.state == ['encoded', 'decoded'])

		pytest.raises(TypeError, c.process, envelope, session, mode=1)
