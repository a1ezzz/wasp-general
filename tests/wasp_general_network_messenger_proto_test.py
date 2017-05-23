# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.proto import WMessengerOnionProto, WMessengerEnvelopeProto
from wasp_general.network.messenger.proto import WMessengerOnionSessionProto, WMessengerOnionLayerProto
from wasp_general.network.messenger.proto import WMessengerOnionSessionFlowProto


def test_abstract():

	pytest.raises(TypeError, WMessengerOnionProto)
	pytest.raises(NotImplementedError, WMessengerOnionProto.layer, None, '')
	pytest.raises(NotImplementedError, WMessengerOnionProto.layers_names, None)

	pytest.raises(TypeError, WMessengerEnvelopeProto)
	pytest.raises(NotImplementedError, WMessengerEnvelopeProto.message, None)

	pytest.raises(TypeError, WMessengerOnionSessionProto)
	pytest.raises(NotImplementedError, WMessengerOnionSessionProto.onion, None)
	pytest.raises(NotImplementedError, WMessengerOnionSessionProto.process, None, None)

	envelope = TestEnvelopeProto.Envelope()
	session = TestWMessengerOnionSessionProto.Session()
	pytest.raises(TypeError, WMessengerOnionLayerProto)
	pytest.raises(NotImplementedError, WMessengerOnionLayerProto.process, None, envelope, session)

	pytest.raises(TypeError, WMessengerOnionSessionFlowProto)
	pytest.raises(NotImplementedError, WMessengerOnionSessionFlowProto.iterator, None, envelope)


class TestEnvelopeProto:

	class Envelope(WMessengerEnvelopeProto):
		def message(self):
			return

	def test(self):
		e = TestEnvelopeProto.Envelope()
		assert(isinstance(e, TestEnvelopeProto.Envelope) is True)
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

		def process(self, envelope):
			return


class TestWMessengerOnionLayerProto:

	class Layer(WMessengerOnionLayerProto):

		def process(self, envelope, session, **kwargs):
			e = TestEnvelopeProto.Envelope()
			e.message = lambda: '::' + self.name() + '::' + envelope.message() + '::'
			return e

	def test(self):
		pytest.raises(TypeError, WMessengerOnionLayerProto)

		l = TestWMessengerOnionLayerProto.Layer('layer_name')
		assert(isinstance(l, WMessengerOnionLayerProto) is True)
		assert(l.name() == 'layer_name')
		l = TestWMessengerOnionLayerProto.Layer('l2')
		assert(l.name() == 'l2')

		envelope = TestEnvelopeProto.Envelope()
		envelope.message = lambda: 'msg'
		session = TestWMessengerOnionSessionProto.Session()
		r = l.process(envelope, session)
		assert(isinstance(r, WMessengerEnvelopeProto) is True)
		assert(r.message() == '::l2::msg::')


class TestWMessengerOnionSessionFlow:

	def test(self):
		pytest.raises(TypeError, WMessengerOnionSessionFlowProto.IteratorInfo, 'ln', 4.)

		ii = WMessengerOnionSessionFlowProto.IteratorInfo('layer_name', a=1, b='code')
		assert(ii.layer_name() == 'layer_name')
		assert(ii.layer_args() == {'a': 1, 'b': 'code'})

		pytest.raises(
			TypeError, WMessengerOnionSessionFlowProto.Iterator,
			'ln', 7
		)

		envelope = TestEnvelopeProto.Envelope()

		i1 = WMessengerOnionSessionFlowProto.Iterator('layer')
		assert(isinstance(i1, WMessengerOnionSessionFlowProto.Iterator) is True)
		assert(isinstance(i1, WMessengerOnionSessionFlowProto.IteratorInfo) is True)
		assert(i1.layer_name() == 'layer')
		assert(i1.next(envelope) is None)

		i2 = WMessengerOnionSessionFlowProto.Iterator('layer2', next_iterator=i1)
		assert(i2.layer_name() == 'layer2')
		assert(i2.next(envelope) == i1)
