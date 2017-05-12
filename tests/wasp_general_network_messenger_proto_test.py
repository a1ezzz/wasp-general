# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.proto import WMessengerOnionProto, WMessengerEnvelopeProto
from wasp_general.network.messenger.proto import WMessengerOnionSessionProto, WMessengerOnionLayerProto
from wasp_general.network.messenger.proto import WMessengerOnionSessionFlowProto

from wasp_general.network.messenger.envelope import WMessengerEnvelope


def test_abstract():

	pytest.raises(TypeError, WMessengerOnionProto)
	pytest.raises(NotImplementedError, WMessengerOnionProto.layer, None, '')
	pytest.raises(NotImplementedError, WMessengerOnionProto.layers_names, None)

	pytest.raises(TypeError, WMessengerEnvelopeProto)
	pytest.raises(NotImplementedError, WMessengerEnvelopeProto.raw, None)

	pytest.raises(TypeError, WMessengerOnionSessionProto)
	pytest.raises(NotImplementedError, WMessengerOnionSessionProto.onion, None)
	pytest.raises(NotImplementedError, WMessengerOnionSessionProto.process, None, None)

	pytest.raises(TypeError, WMessengerOnionSessionFlowProto)
	pytest.raises(NotImplementedError, WMessengerOnionSessionFlowProto.iterator, None)


class TestEnvelopeProto:

	def test(self):
		class E(WMessengerEnvelopeProto):
			def raw(self):
				return

		e = E()
		assert(isinstance(e, E) is True)
		assert(isinstance(e, WMessengerEnvelopeProto) is True)
		assert(e.meta() == {})


class TestWMessengerOnionProto:

	class Onion(WMessengerOnionProto):

		def __init__(self):
			self.layers_storage = {}
			for l in [
				TestWMessengerOnionLayerProto.Layer('first_layer'),
				TestWMessengerOnionLayerProto.Layer('l2'),
				TestWMessengerOnionLayerProto.Layer('last')
			]:
				self.layers_storage[l] = l

		def layer(self, layer_name):
			return self.layers_storage[layer_name]

		def layers_names(self):
			return list(self.layers_storage.values())


class TestWMessengerOnionSessionProto:

	class Session(WMessengerOnionSessionProto):

		def onion(self):
			return TestWMessengerOnionProto.Onion()

		def process(self, message):
			return


class TestWMessengerOnionLayerProto:

	class Layer(WMessengerOnionLayerProto):

		def __init__(self, name):
			WMessengerOnionLayerProto.__init__(self, name)

		def rise(self, msg, session):
			return '::' + self.name() + '::' + msg

		def immerse(self, msg, session):
			return msg[len(self.name()) + 4:]

	def test(self):
		pytest.raises(TypeError, WMessengerOnionLayerProto)

		assert(isinstance(WMessengerOnionLayerProto('layer_name'), WMessengerOnionLayerProto) is True)
		assert(WMessengerOnionLayerProto('layer_name').name() == 'layer_name')
		assert(WMessengerOnionLayerProto('l2').name() == 'l2')

		session = TestWMessengerOnionSessionProto.Session()

		str_envelope = WMessengerEnvelope('msg')
		assert(WMessengerOnionLayerProto('l').immerse(str_envelope, session) == str_envelope)
		bytes_envelope = WMessengerEnvelope(b'msg')
		assert(WMessengerOnionLayerProto('l').rise(bytes_envelope, session) == bytes_envelope)


class TestWMessengerOnionSessionFlow:

	def test(self):
		pytest.raises(TypeError, WMessengerOnionSessionFlowProto.IteratorInfo, 'ln', 4.)

		immerse = WMessengerOnionSessionFlowProto.Direction.immerse
		rise = WMessengerOnionSessionFlowProto.Direction.rise

		ii = WMessengerOnionSessionFlowProto.IteratorInfo('layer_name', immerse)
		assert(ii.layer_name() == 'layer_name')
		assert(ii.direction() == immerse)

		ii = WMessengerOnionSessionFlowProto.IteratorInfo('ln', rise)
		assert(ii.layer_name() == 'ln')
		assert(ii.direction() == rise)

		pytest.raises(
			TypeError, WMessengerOnionSessionFlowProto.Iterator,
			'ln', WMessengerOnionSessionFlowProto.Direction.immerse, 7
		)

		i1 = WMessengerOnionSessionFlowProto.Iterator('layer', immerse)
		assert(isinstance(i1, WMessengerOnionSessionFlowProto.Iterator) is True)
		assert(isinstance(i1, WMessengerOnionSessionFlowProto.IteratorInfo) is True)
		assert(i1.layer_name() == 'layer')
		assert(i1.direction() == immerse)
		assert(i1.next() is None)

		i2 = WMessengerOnionSessionFlowProto.Iterator('layer2', rise, i1)
		assert(i2.layer_name() == 'layer2')
		assert(i2.direction() == rise)
		assert(i2.next() == i1)
