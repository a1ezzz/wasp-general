# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.onion import WMessengerOnionBase, WMessengerOnionSessionBase
from wasp_general.network.messenger.onion import WMessengerOnionLayerBase, WMessengerOnionCoderLayerBase
from wasp_general.network.messenger.onion import WMessengerOnionLexicalLayerBase, WMessengerOnionSessionFlow
from wasp_general.network.messenger.onion import WMessengerOnionSessionStrictFlow, WMessengerOnionSession
from wasp_general.network.messenger.onion import WMessengerOnion


def test_abstract():

	pytest.raises(TypeError, WMessengerOnionBase)
	pytest.raises(NotImplementedError, WMessengerOnionBase.layer, None, '')
	pytest.raises(NotImplementedError, WMessengerOnionBase.layers_names, None)

	pytest.raises(TypeError, WMessengerOnionSessionBase)
	pytest.raises(NotImplementedError, WMessengerOnionSessionBase.onion, None)
	pytest.raises(NotImplementedError, WMessengerOnionSessionBase.process, None, None)

	assert(issubclass(WMessengerOnionCoderLayerBase, WMessengerOnionLayerBase) is True)
	pytest.raises(TypeError, WMessengerOnionCoderLayerBase)
	pytest.raises(NotImplementedError, WMessengerOnionCoderLayerBase.encode, None, '')
	pytest.raises(NotImplementedError, WMessengerOnionCoderLayerBase.decode, None, '')

	assert(issubclass(WMessengerOnionLexicalLayerBase, WMessengerOnionLayerBase) is True)
	pytest.raises(TypeError, WMessengerOnionLexicalLayerBase)
	pytest.raises(NotImplementedError, WMessengerOnionLexicalLayerBase.pack, None, '')
	pytest.raises(NotImplementedError, WMessengerOnionLexicalLayerBase.unpack, None, '')

	pytest.raises(TypeError, WMessengerOnionSessionFlow)
	pytest.raises(NotImplementedError, WMessengerOnionSessionFlow.__iter__, None)


class TestWMessengerOnionBase:

	class Onion(WMessengerOnionBase):

		def __init__(self):
			self.layers_storage = {}
			for l in [
				TestWMessengerOnionLayerBase.Layer('first_layer'),
				TestWMessengerOnionLayerBase.Layer('l2'),
				TestWMessengerOnionLayerBase.Layer('last')
			]:
				self.layers_storage[l] = l

		def layer(self, layer_name):
			return self.layers_storage[layer_name]

		def layers_names(self):
			return list(self.layers_storage.values())


class TestWMessengerOnionSessionBase:

	class Session(WMessengerOnionSessionBase):

		def onion(self):
			return TestWMessengerOnionBase.Onion()

		def process(self, message):
			return


class TestWMessengerOnionLayerBase:

	class Layer(WMessengerOnionLayerBase):

		def __init__(self, name):
			WMessengerOnionLayerBase.__init__(self, name)

		def rise(self, msg, session):
			return '::' + self.name() + '::' + msg

		def immerse(self, msg, session):
			return msg[len(self.name()) + 4:]

	def test(self):
		pytest.raises(TypeError, WMessengerOnionLayerBase)

		assert(isinstance(WMessengerOnionLayerBase('layer_name'), WMessengerOnionLayerBase) is True)
		assert(WMessengerOnionLayerBase('layer_name').name() == 'layer_name')
		assert(WMessengerOnionLayerBase('l2').name() == 'l2')

		session = TestWMessengerOnionSessionBase.Session()

		assert(WMessengerOnionLayerBase('l').immerse('msg', session) == 'msg')
		assert(WMessengerOnionLayerBase('l').rise(b'msg', session) == b'msg')


class TestWMessengerOnionCoderLayerBase:

	def test(self):
		class Coder(WMessengerOnionCoderLayerBase):

			def encode(self, message):
				return 'encoded message'

			def decode(self, message):
				return 'decoded message'

		session = TestWMessengerOnionSessionBase.Session()

		assert(Coder('l').immerse('msg', session) == 'decoded message')
		assert(Coder('l').rise(b'msg', session) == 'encoded message')


class TestWMessengerOnionLexicalLayerBase:

	def test(self):
		class Lex(WMessengerOnionLexicalLayerBase):

			def pack(self, message):
				return 'packed message'

			def unpack(self, message):
				return 'unpacked message'

		session = TestWMessengerOnionSessionBase.Session()

		assert(Lex('l').immerse('msg', session) == 'unpacked message')
		assert(Lex('l').rise(b'msg', session) == 'packed message')


class TestWMessengerOnionSessionFlow:

	def test_iterator(self):
		pytest.raises(TypeError, WMessengerOnionSessionFlow.Iterator, 'ln', 4.)

		sf = WMessengerOnionSessionFlow.Iterator('layer_name', WMessengerOnionSessionFlow.Direction.immerse)
		assert(sf.layer_name() == 'layer_name')
		assert(sf.direction() == WMessengerOnionSessionFlow.Direction.immerse)

		sf = WMessengerOnionSessionFlow.Iterator('ln', WMessengerOnionSessionFlow.Direction.rise)
		assert(sf.layer_name() == 'ln')
		assert(sf.direction() == WMessengerOnionSessionFlow.Direction.rise)


class TestWMessengerOnionSessionStrictFlow:

	def test(self):
		assert(isinstance(WMessengerOnionSessionStrictFlow(), WMessengerOnionSessionStrictFlow) is True)
		assert(isinstance(WMessengerOnionSessionStrictFlow(), WMessengerOnionSessionFlow) is True)

		immerse = WMessengerOnionSessionFlow.Direction.immerse
		rise = WMessengerOnionSessionFlow.Direction.rise

		sf = WMessengerOnionSessionStrictFlow('layer1', 'layer2')
		assert([x.layer_name() for x in sf] == ['layer1', 'layer2', 'layer2', 'layer1'])
		assert([x.direction() for x in sf] == [immerse, immerse, rise, rise])

		sf = WMessengerOnionSessionStrictFlow('l1', 'layer', 'last_layer')
		assert(
			[x.layer_name() for x in sf] ==
			['l1', 'layer', 'last_layer', 'last_layer', 'layer', 'l1']
		)
		assert([x.direction() for x in sf] == [immerse, immerse, immerse, rise, rise, rise])


class TestWMessengerOnionSession:

	def test_session(self):

		class CustomSessionFlow(WMessengerOnionSessionFlow):
			def __iter__(self):
				for i in [
					WMessengerOnionSessionFlow.Iterator(
						'layer1', WMessengerOnionSessionFlow.Direction.immerse
					),
					WMessengerOnionSessionFlow.Iterator(
						'layer2', WMessengerOnionSessionFlow.Direction.rise
					),
					WMessengerOnionSessionFlow.Iterator(
						'layer1', WMessengerOnionSessionFlow.Direction.immerse
					),
					WMessengerOnionSessionFlow.Iterator(
						'layer1', WMessengerOnionSessionFlow.Direction.rise
					)
				]:
					yield i

		onion = TestWMessengerOnionBase.Onion()
		session_flow = CustomSessionFlow()
		session = WMessengerOnionSession(
			onion, session_flow,
		)

		layers = [
			TestWMessengerOnionLayerBase.Layer('layer'),
			TestWMessengerOnionLayerBase.Layer('layer2'),
			TestWMessengerOnionLayerBase.Layer('last_layer'),
			TestWMessengerOnionLayerBase.Layer('l3'),
			TestWMessengerOnionLayerBase.Layer('layer1')
		]
		onion.layers_storage.clear()
		for l in layers:
			onion.layers_storage[l.name()] = l

		assert(session.onion() == onion)
		assert(session.session_flow() == session_flow)

		for layer in layers:
			layer_name = layer.name()

			def patched_immerse(layer_name):
				return lambda m, s: ':immerse ' + layer_name + ':' + m + ':immerse ' + layer_name + ':'

			def patched_rise(layer_name):
				return lambda m, s: ':rise ' + layer_name + ':' + m + ':rise ' + layer_name + ':'

			layer.immerse = patched_immerse(layer_name)
			layer.rise = patched_rise(layer_name)

		result = session.process('msg')
		assert(
			result == ':rise layer1::immerse layer1::rise layer2::immerse layer1:msg:immerse layer1'
			'::rise layer2::immerse layer1::rise layer1:'
		)

		class CorruptedSessionFlow(WMessengerOnionSessionFlow):
			def __iter__(self):

				class I:
					def layer_name(self):
						return 'layer'

					def direction(self):
						return 4

				yield I()

		session = WMessengerOnionSession(onion, CorruptedSessionFlow())

		pytest.raises(RuntimeError, session.process, 'msg')


class TestWMessengerOnion:

	def test_onion(self):
		assert(isinstance(WMessengerOnion(), WMessengerOnion) is True)
		assert(isinstance(WMessengerOnion(), WMessengerOnionBase) is True)

		o = WMessengerOnion(
			TestWMessengerOnionLayerBase.Layer('layer'),
			TestWMessengerOnionLayerBase.Layer('layer2')
		)
		layers = o.layers_names()
		layers.sort()
		assert(layers == ['layer', 'layer2'])

		pytest.raises(ValueError, o.add_layers, TestWMessengerOnionLayerBase.Layer('layer'))

		s = o.create_session(WMessengerOnionSessionStrictFlow('layer2', 'layer'))
		assert(isinstance(s, WMessengerOnionSession) is True)

		s = o.create_session(WMessengerOnionSessionStrictFlow('invalid layer'))
		pytest.raises(ValueError, s.process, 'msg')
