# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.onion import WMessengerOnionBase, WMessengerOnionSessionBase
from wasp_general.network.messenger.onion import WMessengerOnionLayerBase, WMessengerOnionCoderLayerBase
from wasp_general.network.messenger.onion import WMessengerOnionLexicalLayerBase, WMessengerOnionSessionFlow
from wasp_general.network.messenger.onion import WMessengerOnionSessionBasicFlow, WMessengerOnionSessionFlowSequence
from wasp_general.network.messenger.onion import WMessengerOnionSessionReverseFlow, WMessengerOnionSessionFlexFlow
from wasp_general.network.messenger.onion import WMessengerOnionSession, WMessengerOnion


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
	pytest.raises(NotImplementedError, WMessengerOnionSessionFlow.iterator, None)

	pytest.raises(TypeError, WMessengerOnionSessionFlexFlow.MessageComparator)
	pytest.raises(NotImplementedError, WMessengerOnionSessionFlexFlow.MessageComparator.match, None)


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

	def test(self):
		pytest.raises(TypeError, WMessengerOnionSessionFlow.IteratorInfo, 'ln', 4.)

		ii = WMessengerOnionSessionFlow.IteratorInfo('layer_name', WMessengerOnionSessionFlow.Direction.immerse)
		assert(ii.layer_name() == 'layer_name')
		assert(ii.direction() == WMessengerOnionSessionFlow.Direction.immerse)

		ii = WMessengerOnionSessionFlow.IteratorInfo('ln', WMessengerOnionSessionFlow.Direction.rise)
		assert(ii.layer_name() == 'ln')
		assert(ii.direction() == WMessengerOnionSessionFlow.Direction.rise)

		pytest.raises(
			TypeError, WMessengerOnionSessionFlow.Iterator,
			'ln', WMessengerOnionSessionFlow.Direction.immerse, 7
		)

		i1 = WMessengerOnionSessionFlow.Iterator('layer', WMessengerOnionSessionFlow.Direction.immerse)
		assert(isinstance(i1, WMessengerOnionSessionFlow.Iterator) is True)
		assert(isinstance(i1, WMessengerOnionSessionFlow.IteratorInfo) is True)
		assert(i1.layer_name() == 'layer')
		assert(i1.direction() == WMessengerOnionSessionFlow.Direction.immerse)
		assert(i1.next() is None)

		i2 = WMessengerOnionSessionFlow.Iterator('layer2', WMessengerOnionSessionFlow.Direction.rise, i1)
		assert(i2.layer_name() == 'layer2')
		assert(i2.direction() == WMessengerOnionSessionFlow.Direction.rise)
		assert(i2.next() == i1)


class TestWMessengerOnionSessionBasicFlow:

	@staticmethod
	def expand(iterator=None):
		result = []
		if iterator is not None:
			result.append(
				WMessengerOnionSessionFlow.IteratorInfo(iterator.layer_name(), iterator.direction())
			)
			result.extend(TestWMessengerOnionSessionBasicFlow.expand(iterator.next()))
		return result

	def test(self):

		immerse = WMessengerOnionSessionFlow.Direction.immerse
		rise = WMessengerOnionSessionFlow.Direction.rise

		sf = WMessengerOnionSessionBasicFlow()
		assert(isinstance(sf, WMessengerOnionSessionBasicFlow) is True)
		assert(isinstance(sf, WMessengerOnionSessionFlow) is True)
		assert(sf.iterator() is None)

		i = WMessengerOnionSessionFlow.Iterator('layer', immerse)
		sf = WMessengerOnionSessionBasicFlow(i)
		assert(sf.iterator() == i)

		i1 = WMessengerOnionSessionFlow.IteratorInfo('layer', immerse)
		i2 = WMessengerOnionSessionFlow.IteratorInfo('layer2', rise)
		i3 = WMessengerOnionSessionFlow.IteratorInfo('layer3', rise)
		i4 = WMessengerOnionSessionFlow.IteratorInfo('layer4', immerse)
		i5 = WMessengerOnionSessionFlow.IteratorInfo('layer5', rise)

		result = WMessengerOnionSessionBasicFlow.sequence(i1, i2, i3, i4, i5)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(result)
		assert([x.layer_name() for x in expanded_result] == ['layer', 'layer2', 'layer3', 'layer4', 'layer5'])
		assert([x.direction() for x in expanded_result] == [immerse, rise, rise, immerse, rise])

		result = WMessengerOnionSessionBasicFlow.sequence()
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(result)
		assert(len(expanded_result) == 0)

		result = WMessengerOnionSessionBasicFlow.one_direction(immerse, 'l1', 'l2', 'l3')
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(result)
		assert([x.layer_name() for x in expanded_result] == ['l1', 'l2', 'l3'])
		assert([x.direction() for x in expanded_result] == [immerse, immerse, immerse])

		result = WMessengerOnionSessionBasicFlow.one_direction(rise, 'l1', 'l2')
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(result)
		assert([x.layer_name() for x in expanded_result] == ['l1', 'l2'])
		assert([x.direction() for x in expanded_result] == [rise, rise])


class TestWMessengerOnionSessionFlowSequence:

	def test(self):
		immerse = WMessengerOnionSessionFlow.Direction.immerse
		rise = WMessengerOnionSessionFlow.Direction.rise

		i = WMessengerOnionSessionFlowSequence.FlowSequenceIterator(
			WMessengerOnionSessionFlow.IteratorInfo('layer', rise)
		)

		assert(isinstance(i, WMessengerOnionSessionFlowSequence.FlowSequenceIterator) is True)
		assert(isinstance(i, WMessengerOnionSessionFlow.Iterator) is True)
		assert(i.layer_name() == 'layer')
		assert(i.direction() == rise)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(i)
		assert(len(expanded_result) == 1)

		i11 = WMessengerOnionSessionFlow.IteratorInfo('layer1-1', immerse)
		i12 = WMessengerOnionSessionFlow.IteratorInfo('layer1-2', rise)
		f1 = WMessengerOnionSessionBasicFlow.sequence_flow(i11, i12)

		i21 = WMessengerOnionSessionFlow.IteratorInfo('layer2-1', immerse)
		i22 = WMessengerOnionSessionFlow.IteratorInfo('layer2-2', immerse)
		i23 = WMessengerOnionSessionFlow.IteratorInfo('layer2-3', rise)
		f2 = WMessengerOnionSessionBasicFlow.sequence_flow(i21, i22, i23)

		f3 = WMessengerOnionSessionBasicFlow.sequence_flow()

		i = WMessengerOnionSessionFlowSequence.FlowSequenceIterator(
			WMessengerOnionSessionFlow.IteratorInfo('layer', immerse), f1, f3, f2, f3
		)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(i)
		assert([x.layer_name() for x in expanded_result] == [
			'layer', 'layer1-1', 'layer1-2', 'layer2-1', 'layer2-2', 'layer2-3'
		])
		assert([x.direction() for x in expanded_result] == [immerse, immerse, rise, immerse, immerse, rise])

		sf = WMessengerOnionSessionFlowSequence()
		assert(isinstance(sf, WMessengerOnionSessionFlowSequence) is True)
		assert(isinstance(sf, WMessengerOnionSessionBasicFlow) is True)
		assert(sf.iterator() is None)

		sf = WMessengerOnionSessionFlowSequence(f1, f3, f2)
		result = sf.iterator()
		assert(isinstance(result, WMessengerOnionSessionFlowSequence.FlowSequenceIterator) is True)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(result)
		assert([x.layer_name() for x in expanded_result] == [
			'layer1-1', 'layer1-2', 'layer2-1', 'layer2-2', 'layer2-3'
		])
		assert([x.direction() for x in expanded_result] == [immerse, rise, immerse, immerse, rise])


class TestWMessengerOnionSessionReverseFlow:

	def test(self):
		immerse = WMessengerOnionSessionFlow.Direction.immerse
		rise = WMessengerOnionSessionFlow.Direction.rise

		base_i1 = WMessengerOnionSessionFlow.Iterator('layer', immerse)
		base_i2 = WMessengerOnionSessionFlow.Iterator('layer2', rise, base_i1)

		reverse_i = WMessengerOnionSessionReverseFlow.FlowReverseIterator(base_i1)
		assert(isinstance(reverse_i, WMessengerOnionSessionReverseFlow.FlowReverseIterator) is True)
		assert(isinstance(reverse_i, WMessengerOnionSessionFlow.Iterator) is True)

		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(reverse_i)
		assert([x.layer_name() for x in expanded_result] == ['layer', 'layer'])
		assert([x.direction() for x in expanded_result] == [immerse, rise])

		reverse_i = WMessengerOnionSessionReverseFlow.FlowReverseIterator(base_i2)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(reverse_i)
		assert([x.layer_name() for x in expanded_result] == ['layer2', 'layer', 'layer', 'layer2'])
		assert([x.direction() for x in expanded_result] == [rise, immerse, rise, immerse])

		reverse_i = WMessengerOnionSessionReverseFlow.FlowReverseIterator(base_i2, strict_direction=True)
		pytest.raises(RuntimeError, TestWMessengerOnionSessionBasicFlow.expand, reverse_i)

		base_f0 = WMessengerOnionSessionBasicFlow()
		base_f1 = WMessengerOnionSessionBasicFlow(base_i1)
		base_f2 = WMessengerOnionSessionBasicFlow(base_i2)

		flow = WMessengerOnionSessionReverseFlow(base_f0)
		assert(isinstance(flow, WMessengerOnionSessionReverseFlow) is True)
		assert(isinstance(flow, WMessengerOnionSessionBasicFlow) is True)
		assert(base_f0.iterator() is None)

		flow = WMessengerOnionSessionReverseFlow(base_f1)
		reverse_i = flow.iterator()
		assert(isinstance(reverse_i, WMessengerOnionSessionReverseFlow.FlowReverseIterator) is True)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(reverse_i)
		assert([x.layer_name() for x in expanded_result] == ['layer', 'layer'])
		assert([x.direction() for x in expanded_result] == [immerse, rise])

		flow = WMessengerOnionSessionReverseFlow(base_f2)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(flow.iterator())
		assert([x.layer_name() for x in expanded_result] == ['layer2', 'layer', 'layer', 'layer2'])
		assert([x.direction() for x in expanded_result] == [rise, immerse, rise, immerse])

		flow = WMessengerOnionSessionReverseFlow(base_f2, strict_direction=True)
		pytest.raises(RuntimeError, TestWMessengerOnionSessionBasicFlow.expand, flow.iterator())


class TestWMessengerOnionSessionFlexFlow:

	class CMP(WMessengerOnionSessionFlexFlow.MessageComparator):
		def match(self, message=None):
			return message is not None and (len(message) % 2 == 0)

	class Dummy(WMessengerOnionSessionFlexFlow.MessageComparator):

		def __init__(self, value):
			self.__value = value

		def match(self, message=None):
			return self.__value

	def test_comparator_pair(self):
		immerse = WMessengerOnionSessionFlow.Direction.immerse
		cmp = TestWMessengerOnionSessionFlexFlow.CMP()

		assert(isinstance(cmp, WMessengerOnionSessionFlexFlow.MessageComparator) is True)

		f = WMessengerOnionSessionBasicFlow(WMessengerOnionSessionFlow.Iterator('layer', immerse))
		pytest.raises(TypeError, WMessengerOnionSessionFlexFlow.FlowComparatorPair, 1, f)
		p = WMessengerOnionSessionFlexFlow.FlowComparatorPair(cmp, f)
		assert(p.comparator() == cmp)
		assert(p.flow() == f)

		re_cmp = WMessengerOnionSessionFlexFlow.ReComparator('^zxc.+11$')
		assert(re_cmp.match(None) is not True)
		assert(re_cmp.match('zxc11') is not True)
		assert(re_cmp.match('zxc_11') is True)

		re_cmp = WMessengerOnionSessionFlexFlow.ReComparator(b'zxc_11')
		assert(re_cmp.match(None) is not True)
		assert(re_cmp.match(b'zxc_11') is True)
		assert(re_cmp.match(b'zxc') is not True)

	def test(self):

		immerse = WMessengerOnionSessionFlow.Direction.immerse
		rise = WMessengerOnionSessionFlow.Direction.rise

		cmp = TestWMessengerOnionSessionFlexFlow.CMP()
		f1 = WMessengerOnionSessionBasicFlow(WMessengerOnionSessionFlow.Iterator('layer0', immerse))
		p1 = WMessengerOnionSessionFlexFlow.FlowComparatorPair(cmp, f1)

		dummy_true_cmp = TestWMessengerOnionSessionFlexFlow.Dummy(True)
		f2 = WMessengerOnionSessionBasicFlow.one_direction_flow(rise, 'layer1', 'layer2')
		p2 = WMessengerOnionSessionFlexFlow.FlowComparatorPair(dummy_true_cmp, f2)

		ff = WMessengerOnionSessionFlexFlow(p1, p2)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(ff.iterator('q'))
		assert([x.layer_name() for x in expanded_result] == ['layer1', 'layer2'])
		assert([x.direction() for x in expanded_result] == [rise, rise])
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(ff.iterator('qq'))
		assert([x.layer_name() for x in expanded_result] == ['layer0'])
		assert([x.direction() for x in expanded_result] == [immerse])

		f3 = WMessengerOnionSessionBasicFlow.one_direction_flow(rise, 'layer4')

		ff = WMessengerOnionSessionFlexFlow(p1, default_flow=f3)
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(ff.iterator('q'))
		assert([x.layer_name() for x in expanded_result] == ['layer4'])
		assert([x.direction() for x in expanded_result] == [rise])
		expanded_result = TestWMessengerOnionSessionBasicFlow.expand(ff.iterator('qq'))
		assert([x.layer_name() for x in expanded_result] == ['layer0'])
		assert([x.direction() for x in expanded_result] == [immerse])

		pytest.raises(TypeError, WMessengerOnionSessionFlexFlow, 4)


class TestWMessengerOnionSession:

	def test_session(self):
		immerse = WMessengerOnionSessionFlow.Direction.immerse
		rise = WMessengerOnionSessionFlow.Direction.rise

		class CustomSessionFlow(WMessengerOnionSessionFlow):

			def __init__(self):
				WMessengerOnionSessionFlow.__init__(self)

				self.__items = WMessengerOnionSessionFlow.Iterator(
					'layer1', immerse,
					WMessengerOnionSessionFlow.Iterator(
						'layer2', rise,
						WMessengerOnionSessionFlow.Iterator(
							'layer1', immerse,
							WMessengerOnionSessionFlow.Iterator(
								'layer1', rise
							)
						)
					)
				)

			def iterator(self, message=None):
				return self.__items

		onion = TestWMessengerOnionBase.Onion()
		session_flow = CustomSessionFlow()
		session = WMessengerOnionSession(onion, session_flow)

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

		class CorruptedSessionFlowIterator(WMessengerOnionSessionFlow.Iterator):

			def direction(self):
				return 4

		flow = WMessengerOnionSessionBasicFlow(CorruptedSessionFlowIterator('layer', immerse))
		session = WMessengerOnionSession(onion, flow)

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

		immerse = WMessengerOnionSessionFlow.Direction.immerse
		flow = WMessengerOnionSessionReverseFlow(WMessengerOnionSessionBasicFlow(
			WMessengerOnionSessionBasicFlow.one_direction(immerse, 'layer2', 'layer')
		))

		s = o.create_session(flow)
		assert(isinstance(s, WMessengerOnionSession) is True)

		flow = WMessengerOnionSessionReverseFlow(WMessengerOnionSessionBasicFlow(
			WMessengerOnionSessionBasicFlow.one_direction(immerse, 'invalid layer')
		))
		s = o.create_session(flow)
		pytest.raises(ValueError, s.process, 'msg')
