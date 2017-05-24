# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.proto import WMessengerOnionSessionFlowProto, WMessengerOnionProto
from wasp_general.network.messenger.proto import WMessengerOnionLayerProto
from wasp_general.network.messenger.envelope import WMessengerEnvelope, WMessengerTextEnvelope, WMessengerBytesEnvelope

from wasp_general.network.messenger.session import WMessengerOnionSessionFlow, WMessengerOnionSessionFlowSequence
from wasp_general.network.messenger.session import WMessengerOnionSessionFlexFlow, WMessengerOnionSession


def test_abstract():

	pytest.raises(TypeError, WMessengerOnionSessionFlexFlow.MessageComparator)
	envelope = WMessengerEnvelope(None)
	pytest.raises(NotImplementedError, WMessengerOnionSessionFlexFlow.MessageComparator.match, None, envelope)


class TestWMessengerOnionSessionFlow:

	@staticmethod
	def expand(iterator=None, envelope_data=None):
		result = []
		envelope = WMessengerEnvelope(envelope_data)
		if iterator is not None:
			result.append(
				WMessengerOnionSessionFlow.IteratorInfo(iterator.layer_name(), **iterator.layer_args())
			)
			result.extend(TestWMessengerOnionSessionFlow.expand(iterator.next(envelope)))
		return result

	def test(self):
		i = WMessengerOnionSessionFlowProto.Iterator('layer')
		sf = WMessengerOnionSessionFlow(i)

		assert(isinstance(sf, WMessengerOnionSessionFlow) is True)
		assert(isinstance(sf, WMessengerOnionSessionFlowProto) is True)
		assert(sf.iterator(WMessengerEnvelope(None)) == i)

		info = [
			WMessengerOnionSessionFlowProto.IteratorInfo('layer1', **{'a': 1, 'b': 'z'}),
			WMessengerOnionSessionFlowProto.IteratorInfo('layer2', **{'a': 2, 'b': 'zz'}),
			WMessengerOnionSessionFlowProto.IteratorInfo('layer1', **{'a': 3, 'b': 'z'})
		]

		i = WMessengerOnionSessionFlow.sequence(*info)
		assert(isinstance(i, WMessengerOnionSessionFlowProto.Iterator) is True)
		result = TestWMessengerOnionSessionFlow.expand(i)
		assert([(x.layer_name(), x.layer_args()) for x in result] == [
			('layer1', {'a': 1, 'b': 'z'}),
			('layer2', {'a': 2, 'b': 'zz'}),
			('layer1', {'a': 3, 'b': 'z'})
		])

		i = WMessengerOnionSessionFlow.sequence()
		assert(i is None)

		sf = WMessengerOnionSessionFlow.sequence_flow(*info)
		assert(isinstance(sf, WMessengerOnionSessionFlowProto) is True)
		i = sf.iterator(WMessengerEnvelope(None))
		result = TestWMessengerOnionSessionFlow.expand(i)
		assert([(x.layer_name(), x.layer_args()) for x in result] == [
			('layer1', {'a': 1, 'b': 'z'}),
			('layer2', {'a': 2, 'b': 'zz'}),
			('layer1', {'a': 3, 'b': 'z'})
		])


class TestWMessengerOnionSessionFlowSequence:

	def test_iterator(self):
		i = WMessengerOnionSessionFlowSequence.FlowSequenceIterator(
			WMessengerOnionSessionFlow.IteratorInfo('layer', **{'z': 1})
		)
		assert(isinstance(i, WMessengerOnionSessionFlowSequence.FlowSequenceIterator) is True)
		assert(isinstance(i, WMessengerOnionSessionFlow.Iterator) is True)
		assert(i.layer_name() == 'layer')
		assert(i.layer_args() == {'z': 1})
		result = TestWMessengerOnionSessionFlow.expand(i)
		assert(len(result) == 1)

		i11 = WMessengerOnionSessionFlow.IteratorInfo('layer1-1')
		i12 = WMessengerOnionSessionFlow.IteratorInfo('layer1-2', **{'q': 0})
		f1 = WMessengerOnionSessionFlow.sequence_flow(i11, i12)

		i21 = WMessengerOnionSessionFlow.IteratorInfo('layer2-1')
		i22 = WMessengerOnionSessionFlow.IteratorInfo('layer2-2')
		i23 = WMessengerOnionSessionFlow.IteratorInfo('layer2-3', **{'a': 'w'})
		f2 = WMessengerOnionSessionFlow.sequence_flow(i21, i22, i23)

		f3 = WMessengerOnionSessionFlow.sequence_flow(i11)
		f3.iterator = lambda x: None

		i = WMessengerOnionSessionFlowSequence.FlowSequenceIterator(
			WMessengerOnionSessionFlow.IteratorInfo('layer', **{'0': 0}), f1, f3, f2
		)
		result = TestWMessengerOnionSessionFlow.expand(i)
		assert([(x.layer_name(), x.layer_args()) for x in result] == [
			('layer', {'0': 0}),
			('layer1-1', {}),
			('layer1-2', {'q': 0}),
			('layer2-1', {}),
			('layer2-2', {}),
			('layer2-3', {'a': 'w'}),
		])

	def test(self):
		i11 = WMessengerOnionSessionFlow.IteratorInfo('layer1')
		i12 = WMessengerOnionSessionFlow.IteratorInfo('layer2')
		f1 = WMessengerOnionSessionFlow.sequence_flow(i11, i12)

		i21 = WMessengerOnionSessionFlow.IteratorInfo('layer3')
		i22 = WMessengerOnionSessionFlow.IteratorInfo('layer4')
		i23 = WMessengerOnionSessionFlow.IteratorInfo('layer5')
		f2 = WMessengerOnionSessionFlow.sequence_flow(i21, i22, i23)

		sf = WMessengerOnionSessionFlowSequence()
		assert(isinstance(sf, WMessengerOnionSessionFlowSequence) is True)
		assert(isinstance(sf, WMessengerOnionSessionFlowProto) is True)
		assert(sf.iterator(WMessengerEnvelope(None)) is None)

		sf = WMessengerOnionSessionFlowSequence(f1, f2)
		result = sf.iterator(WMessengerEnvelope(None))
		assert(isinstance(result, WMessengerOnionSessionFlowSequence.FlowSequenceIterator) is True)
		result = TestWMessengerOnionSessionFlow.expand(result)
		assert([(x.layer_name(), x.layer_args()) for x in result] == [
			('layer1', {}),
			('layer2', {}),
			('layer3', {}),
			('layer4', {}),
			('layer5', {})
		])


class TestWMessengerOnionSessionFlexFlow:
	class CMP(WMessengerOnionSessionFlexFlow.MessageComparator):
		def match(self, envelope):
			return len(envelope.message()) % 2 == 0

	class Dummy(WMessengerOnionSessionFlexFlow.MessageComparator):

		def __init__(self, value):
			self.__value = value

		def match(self, envelope):
			return self.__value

	def test_comparator_pair(self):
		cmp = TestWMessengerOnionSessionFlexFlow.CMP()

		assert(isinstance(cmp, WMessengerOnionSessionFlexFlow.MessageComparator) is True)

		f = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlow.IteratorInfo('layer'))
		pytest.raises(TypeError, WMessengerOnionSessionFlexFlow.FlowComparatorPair, 1, f)
		p = WMessengerOnionSessionFlexFlow.FlowComparatorPair(cmp, f)
		assert(p.comparator() == cmp)
		assert(p.flow() == f)

		re_cmp = WMessengerOnionSessionFlexFlow.ReComparator('^zxc.+11$')
		assert(re_cmp.match(WMessengerTextEnvelope('zxc11')) is not True)
		assert(re_cmp.match(WMessengerTextEnvelope('zxc_11')) is True)

		re_cmp = WMessengerOnionSessionFlexFlow.ReComparator(b'zxc_11')
		assert(re_cmp.match(WMessengerBytesEnvelope(b'zxc_11')) is True)
		assert(re_cmp.match(WMessengerBytesEnvelope(b'zxc')) is not True)

	def test(self):

		cmp = TestWMessengerOnionSessionFlexFlow.CMP()
		f1 = WMessengerOnionSessionFlow(WMessengerOnionSessionFlow.Iterator('layer0'))
		p1 = WMessengerOnionSessionFlexFlow.FlowComparatorPair(cmp, f1)

		dummy_true_cmp = TestWMessengerOnionSessionFlexFlow.Dummy(True)
		f2 = WMessengerOnionSessionFlow.sequence_flow(
			WMessengerOnionSessionFlowProto.IteratorInfo('layer1'),
			WMessengerOnionSessionFlowProto.IteratorInfo('layer2')
		)
		p2 = WMessengerOnionSessionFlexFlow.FlowComparatorPair(dummy_true_cmp, f2)

		ff = WMessengerOnionSessionFlexFlow(p1, p2)
		expanded_result = TestWMessengerOnionSessionFlow.expand(ff.iterator(WMessengerTextEnvelope('q')))
		assert([x.layer_name() for x in expanded_result] == ['layer1', 'layer2'])
		expanded_result = TestWMessengerOnionSessionFlow.expand(ff.iterator(WMessengerTextEnvelope('qq')))
		assert([x.layer_name() for x in expanded_result] == ['layer0'])

		f3 = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer4'))

		ff = WMessengerOnionSessionFlexFlow(p1, default_flow=f3)
		expanded_result = TestWMessengerOnionSessionFlow.expand(ff.iterator(WMessengerTextEnvelope('q')))
		assert([x.layer_name() for x in expanded_result] == ['layer4'])
		expanded_result = TestWMessengerOnionSessionFlow.expand(ff.iterator(WMessengerTextEnvelope('qq')))
		assert([x.layer_name() for x in expanded_result] == ['layer0'])

		pytest.raises(TypeError, WMessengerOnionSessionFlexFlow, 4)


class TestWMessengerOnionSession:

	def test(self):

		class Onion(WMessengerOnionProto):

			def __init__(self):
				self.storage = {}

			def layers_names(self):
				return self.storage.keys()

			def layer(self, layer_name):
				return self.storage[layer_name]

		class Layer(WMessengerOnionLayerProto):

			def process(self, envelope, session, **kwargs):
				return WMessengerEnvelope(envelope.message() + '<' + self.name() + '>::')

		class CustomSessionFlow(WMessengerOnionSessionFlowProto):

			def __init__(self):
				WMessengerOnionSessionFlowProto.__init__(self)

				self.__items = WMessengerOnionSessionFlow.Iterator(
					'layer1', WMessengerOnionSessionFlow.Iterator(
						'layer2', WMessengerOnionSessionFlow.Iterator(
							'layer1', WMessengerOnionSessionFlow.Iterator(
								'l3'
							)
						)
					)
				)

			def iterator(self, envelope):
				return self.__items

		onion = Onion()
		session_flow = CustomSessionFlow()
		onion_session = WMessengerOnionSession(onion, session_flow)

		layers = [Layer('layer'), Layer('layer2'), Layer('last_layer'), Layer('l3'), Layer('layer1')]
		for l in layers:
			onion.storage[l.name()] = l

		assert(onion_session.onion() == onion)
		assert(onion_session.session_flow() == session_flow)
		result = onion_session.process(WMessengerEnvelope('msg'))
		assert(isinstance(result, WMessengerEnvelope) is True)
		assert(result.message() == 'msg<layer1>::<layer2>::<layer1>::<l3>::')
