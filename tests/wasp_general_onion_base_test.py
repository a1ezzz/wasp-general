# -*- coding: utf-8 -*-

import pytest
import asyncio

from wasp_general.onion.proto import WEnvelopeProto, WOnionSessionFlowProto, WOnionProto, WOnionLayerProto
from wasp_general.onion.base import WEnvelope, WOnionDirectSessionFlow, WOnionConditionalSessionFlow, WOnion


def test_abstract():
	pytest.raises(TypeError, WOnionConditionalSessionFlow.FlowSelector)
	pytest.raises(NotImplementedError, WOnionConditionalSessionFlow.FlowSelector.flow, None, WEnvelope(1))


class TestWEnvelope:

	def test(self):
		envelope1 = WEnvelope(1)
		assert(isinstance(envelope1, WEnvelopeProto) is True)
		assert(envelope1.data() is 1)
		assert(tuple(envelope1.layers()) == tuple())

		envelope2 = WEnvelope(2, layer_meta='a')
		assert(envelope2.data() is 2)
		assert(tuple(envelope2.layers()) == tuple())

		envelope3 = WEnvelope(3, layer_name='foo', layer_meta='a')
		assert(envelope3.data() is 3)
		assert(tuple(envelope3.layers()) == (('foo', 'a'), ))

		envelope4 = WEnvelope(4, previous_meta=envelope3)
		assert(envelope4.data() is 4)
		assert(tuple(envelope4.layers()) == (('foo', 'a'), ))

		envelope5 = WEnvelope(5, layer_name='bar', layer_meta={'z': 7}, previous_meta=envelope4)
		assert(envelope5.data() is 5)
		assert(tuple(envelope5.layers()) == (('foo', 'a'), ('bar', {'z': 7})))

		class CustomEnvelope(WEnvelopeProto):

			def data(self):
				return 'zzz'

			def layers(self, layer_name=None):
				meta = (
					('layer-q', ('zxc', 123)),
					('layer-w', [1, 2, 3]),
					('layer-w', [1, 2, 3])
				)

				for i in meta:
					yield i

		custom_envelope = CustomEnvelope()

		envelope_object = object()
		envelope6 = WEnvelope(6, layer_name='mmm', layer_meta=envelope_object, previous_meta=custom_envelope)
		assert(envelope6.data() is 6)
		assert(tuple(envelope6.layers()) == (
			('layer-q', ('zxc', 123)),
			('layer-w', [1, 2, 3]),
			('layer-w', [1, 2, 3]),
			('mmm', envelope_object)
		))

		envelope7 = WEnvelope(envelope_object, layer_name='ooo', layer_meta=7, previous_meta=envelope6)
		assert(envelope7.data() is envelope_object)
		assert(tuple(envelope7.layers()) == (
			('layer-q', ('zxc', 123)),
			('layer-w', [1, 2, 3]),
			('layer-w', [1, 2, 3]),
			('mmm', envelope_object),
			('ooo', 7)
		))


# class TestWOnionBaseSessionFlow:
#
# 	class SessionFlow(WOnionSessionFlowProto):
#
# 		def __init__(self, *layers):
# 			self.__layers = layers
#
# 		async def iterate(self, envelope):
# 			loop = asyncio.get_event_loop()
# 			for l in self.__layers:
# 				f = loop.create_future()
# 				yield l, f
# 				z = await f
# 				assert(z == 'zzz')
#
# 	@pytest.mark.asyncio
# 	async def test(self):
# 		sf = TestWOnionBaseSessionFlow.SessionFlow('layer1', 'layer-foo', 'layer-bar')
# 		result = []
# 		async for i, j in WOnionBaseSessionFlow.iterate_inner_flow(sf, WEnvelope(1)):
# 			result.append(i)
# 			assert(asyncio.isfuture(j) is True)
# 			j.set_result('zzz')
# 		assert(result == ['layer1', 'layer-foo', 'layer-bar'])
#
#
#

class TestWOnionDirectSessionFlow:

	class SessionFlow(WOnionSessionFlowProto):

		def __init__(self, *layers):
			self.__layers = layers

		def next(self, envelope):
			if self.__layers:
				return (
					WOnionSessionFlowProto.LayerInfo(self.__layers[0]),
					TestWOnionDirectSessionFlow.SessionFlow(*(self.__layers[1:]))
				)
			return None, None

	def test(self):
		sf = WOnionDirectSessionFlow()
		assert(isinstance(sf, WOnionSessionFlowProto) is True)

		sf = WOnionDirectSessionFlow(
			WOnionSessionFlowProto.LayerInfo('layer-qaz1'),
			TestWOnionDirectSessionFlow.SessionFlow('foo-layer', 'bar-layer'),
			WOnionSessionFlowProto.LayerInfo('layer-qaz2'),
			WOnionSessionFlowProto.LayerInfo('layer-qaz3')
		)

		def test_iter(flow, *envelopes):
			iter_result = []
			envelopes = [WEnvelope(x) for x in envelopes]

			for e in envelopes:
				if not flow:
					break
				next_layer, flow = flow.next(e)
				iter_result.append(next_layer)

			return iter_result

		result = test_iter(sf, None, 1, 'zzz', 'zzz', None)
		for i in result:
			assert(isinstance(i, WOnionSessionFlowProto.LayerInfo) is True)

		expected_result = ['layer-qaz1', 'foo-layer', 'bar-layer', 'layer-qaz2', 'layer-qaz3']
		assert([x.layer_name() for x in result] == expected_result)

		result = test_iter(sf, None, 1, 'zzz', 'zzz', 7, None, 'a')
		assert([(x.layer_name() if x else None) for x in result] == (expected_result + [None]))

		class SFlow(WOnionSessionFlowProto):

			def next(self, envelope):
				return WOnionDirectSessionFlow.LayerInfo('mmm-layer'), None

		sf = WOnionDirectSessionFlow(
			SFlow(), WOnionDirectSessionFlow.LayerInfo('zzz-layer')
		)
		result = test_iter(sf, None, 1, 2)
		assert([(x.layer_name() if x else None) for x in result] == ['mmm-layer', 'zzz-layer', None])

		sf = WOnionDirectSessionFlow(
			WOnionDirectSessionFlow.LayerInfo('zzz-layer'), SFlow()
		)
		result = test_iter(sf, None, 1, 2)
		assert([(x.layer_name() if x else None) for x in result] == ['zzz-layer', 'mmm-layer', None])

		sf = WOnionDirectSessionFlow(
			WOnionDirectSessionFlow(
				WOnionSessionFlowProto.LayerInfo('zzz-layer'),
				WOnionSessionFlowProto.LayerInfo('foo-layer')
			),
			WOnionDirectSessionFlow(
				WOnionSessionFlowProto.LayerInfo('zzz-layer'),
				WOnionSessionFlowProto.LayerInfo('bar-layer'),
				WOnionSessionFlowProto.LayerInfo('mmm-layer')
			)
		)

		result = test_iter(sf, None, 1, 2, 3, 4, 5, 6)
		expected_result = ['zzz-layer', 'foo-layer', 'zzz-layer', 'bar-layer', 'mmm-layer', None]
		assert([(x.layer_name() if x else None) for x in result] == expected_result)


class TestWOnionConditionalSessionFlow:

	def test(self):
		sf = WOnionConditionalSessionFlow(
			WOnionConditionalSessionFlow.ReComparator(
				'^qaz$', WOnionDirectSessionFlow(
					WOnionSessionFlowProto.LayerInfo('layer-qaz1')
				)
			),
			WOnionConditionalSessionFlow.ReComparator(
				'^wsx$', WOnionDirectSessionFlow(
					WOnionSessionFlowProto.LayerInfo('layer-wsx1'),
					WOnionConditionalSessionFlow(
						WOnionConditionalSessionFlow.ReComparator(
							'^foo$', WOnionDirectSessionFlow(
								WOnionSessionFlowProto.LayerInfo('layer-foo1'),
								WOnionSessionFlowProto.LayerInfo('layer-foo2')
							)
						),
						WOnionConditionalSessionFlow.ReComparator(
							'^bar$', WOnionDirectSessionFlow(
								WOnionSessionFlowProto.LayerInfo('layer-bar1')
							)
						)
					)
				)
			),
			default_flow=WOnionDirectSessionFlow(
				WOnionSessionFlowProto.LayerInfo('layer-default1'),
				WOnionSessionFlowProto.LayerInfo('layer-default2')
			)
		)

		def test_iter(flow, *envelopes):
			iter_result = []
			envelopes = [WEnvelope(x) for x in envelopes]

			for e in envelopes:
				if not flow:
					break
				next_layer, flow = flow.next(e)
				iter_result.append(next_layer)

			return iter_result

		layers = test_iter(sf, 'wsx', 'foo', 'foo', 'foo')

		assert(len(layers) == 4)
		assert([(x.layer_name() if x else None) for x in layers] == ['layer-wsx1', 'layer-foo1', 'layer-foo2', None])

		layers = test_iter(sf, 'qaz', 'foo')
		assert([(x.layer_name() if x else None) for x in layers] == ['layer-qaz1', None])

		layers = test_iter(sf, 'mmm', 'mmm', 'mmm')
		assert([(x.layer_name() if x else None) for x in layers] == ['layer-default1', 'layer-default2', None])

		sf = WOnionConditionalSessionFlow(
			WOnionConditionalSessionFlow.ReComparator(
				'^qaz$', WOnionDirectSessionFlow(
					WOnionSessionFlowProto.LayerInfo('layer-qaz1')
				)
			)
		)
		layers = test_iter(sf, 'zzz')
		assert(layers == [None])


class TestWOnion:

	# noinspection PyAbstractClass
	class BaseLayer(WOnionLayerProto):

		def __init__(self, envelope):
			WOnionLayerProto.__init__(self)
			self.__result = envelope

		async def process(self, envelope):
			return self.__result

	@pytest.mark.asyncio
	async def test(self):
		onion = WOnion()
		assert(isinstance(onion, WOnionProto) is True)
		assert(onion.layers_names() == tuple())
		pytest.raises(ValueError, onion.layer, 'foo')

		input_e = WEnvelope(1)
		sf = WOnionDirectSessionFlow()
		output_e = await onion.process(sf, input_e)
		assert(input_e is output_e)

		class CustomLayer1(TestWOnion.BaseLayer):

			@classmethod
			def name(cls):
				return 'custom-layer-1'

		class CustomLayer2(TestWOnion.BaseLayer):

			@classmethod
			def name(cls):
				return 'custom-layer-2'

		onion.add_layers(CustomLayer1, CustomLayer2)
		layers = onion.layers_names()
		assert(len(layers) == 2)
		assert('custom-layer-1' in layers)
		assert('custom-layer-2' in layers)

		pytest.raises(ValueError, onion.add_layers, CustomLayer1)

		class CustomLayer3(TestWOnion.BaseLayer):

			@classmethod
			def name(cls):
				return 'custom-layer-3'

		onion.add_layers(CustomLayer3)
		layers = onion.layers_names()
		assert(len(layers) == 3)
		assert('custom-layer-1' in layers)
		assert('custom-layer-2' in layers)
		assert('custom-layer-3' in layers)

		foo_envelope = WEnvelope('foo')
		bar2_envelope = WEnvelope('bar2')
		sf = WOnionConditionalSessionFlow(
			WOnionConditionalSessionFlow.ReComparator(
				'^qaz$', WOnionDirectSessionFlow(
					WOnionSessionFlowProto.LayerInfo('custom-layer-1', foo_envelope)
				)
			),
			WOnionConditionalSessionFlow.ReComparator(
				'^wsx$', WOnionDirectSessionFlow(
					WOnionSessionFlowProto.LayerInfo('layer-wsx1'),
					WOnionConditionalSessionFlow(
						WOnionConditionalSessionFlow.ReComparator(
							'^bar$', WOnionDirectSessionFlow(
								WOnionSessionFlowProto.LayerInfo('layer-bar1')
							)
						)
					)
				)
			),
			default_flow=WOnionDirectSessionFlow(
				WOnionSessionFlowProto.LayerInfo('custom-layer-1', WEnvelope('bar')),
				WOnionConditionalSessionFlow(
					WOnionConditionalSessionFlow.ReComparator(
						'^bar$', WOnionDirectSessionFlow(
							WOnionSessionFlowProto.LayerInfo(
								'custom-layer-3', bar2_envelope
							)
						)
					)
				)
			)
		)

		output_e = await onion.process(sf, WEnvelope('qaz'))
		assert(output_e is foo_envelope)

		with pytest.raises(ValueError):
			await onion.process(sf, WEnvelope('wsx'))

		output_e = await onion.process(sf, WEnvelope("1"))
		assert(output_e is bar2_envelope)

		onion = WOnion(CustomLayer2, CustomLayer3)
		layers = onion.layers_names()
		assert(len(layers) == 2)
		assert('custom-layer-2' in layers)
		assert('custom-layer-3' in layers)
