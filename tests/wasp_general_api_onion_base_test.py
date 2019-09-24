# -*- coding: utf-8 -*-

import pytest
import asyncio

from wasp_general.api.registry import WNoSuchAPIIdError, WAPIRegistry

from wasp_general.api.onion.proto import WEnvelopeProto, WOnionSessionFlowProto, WOnionProto, WOnionLayerProto
from wasp_general.api.onion.base import WEnvelope, WOnionDirectSessionFlow, WOnionConditionalSessionFlow, WOnion
from wasp_general.api.onion.base import __default_onion_registry__, register_class


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


@pytest.fixture
def default_registry_wrap(request):
	default_ids = set(__default_onion_registry__.ids())

	def fin():
		registered_ids = set(__default_onion_registry__.ids())
		for api_id in registered_ids.difference(default_ids):
			__default_onion_registry__.unregister(api_id)

	request.addfinalizer(fin)


class TestWOnion:

	# noinspection PyAbstractClass
	class BaseLayer(WOnionLayerProto):

		def __init__(self, envelope):
			WOnionLayerProto.__init__(self)
			self.__result = envelope

		async def process(self, envelope):
			return self.__result

	@pytest.mark.usefixtures('default_registry_wrap')
	@pytest.mark.asyncio
	async def test(self):
		onion = WOnion()
		assert(isinstance(onion, WOnionProto) is True)
		assert(isinstance(onion, WAPIRegistry) is True)
		assert(tuple(onion.layers_names()) == tuple())
		pytest.raises(WNoSuchAPIIdError, onion.layer, 'foo')

		input_e = WEnvelope(1)
		sf = WOnionDirectSessionFlow()
		output_e = await onion.process(sf, input_e)
		assert(input_e is output_e)

		class CustomLayer1(TestWOnion.BaseLayer):
			pass

		onion.register('custom-layer-1', CustomLayer1)

		@register_class(registry=onion)
		class CustomLayer2(TestWOnion.BaseLayer):
			__layer_name__ = 'custom-layer-2'

		layers = tuple(onion.layers_names())
		assert(len(layers) == 2)
		assert('custom-layer-1' in layers)
		assert('custom-layer-2' in layers)

		@register_class(registry=onion, layer_name='custom-layer-3')
		class CustomLayer3(TestWOnion.BaseLayer):
			pass

		layers = tuple(onion.layers_names())
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

		with pytest.raises(WNoSuchAPIIdError):
			await onion.process(sf, WEnvelope('wsx'))

		output_e = await onion.process(sf, WEnvelope("1"))
		assert(output_e is bar2_envelope)

	@pytest.mark.usefixtures('default_registry_wrap')
	def test_default(self):
		assert(isinstance(__default_onion_registry__, WOnion) is True)

		layers_names = tuple(__default_onion_registry__.layers_names())

		# predefined layers
		assert('com.binblob.wasp-general.asyncio-layer' in layers_names)
		assert('com.binblob.wasp-general.json-layer' in layers_names)
		assert('com.binblob.wasp-general.wrapping-layer' in layers_names)
		assert('com.binblob.wasp-general.encoding-layer' in layers_names)
		assert('com.binblob.wasp-general.hex-layer' in layers_names)

		assert('com.binblob.wasp-general.base64-layer' in layers_names)
		assert('com.binblob.wasp-general.aes-layer' in layers_names)
		assert('com.binblob.wasp-general.rsa-layer' in layers_names)
		assert('com.binblob.wasp-general.transformation-layer' in layers_names)

		assert('custom-layer-1' not in layers_names)
		assert('custom-layer-2' not in layers_names)
		assert('custom-layer-3' not in layers_names)

		@register_class(layer_name='custom-layer-1')
		class CustomLayer1(TestWOnion.BaseLayer):
			pass

		layers_names = tuple(__default_onion_registry__.layers_names())
		assert('custom-layer-1' in layers_names)
		assert('custom-layer-2' not in layers_names)
		assert('custom-layer-3' not in layers_names)
		assert(__default_onion_registry__.layer('custom-layer-1') is CustomLayer1)

		@register_class()
		class CustomLayer2(TestWOnion.BaseLayer):
			__layer_name__ = 'custom-layer-2'

		layers_names = tuple(__default_onion_registry__.layers_names())
		assert('custom-layer-1' in layers_names)
		assert('custom-layer-2' in layers_names)
		assert('custom-layer-3' not in layers_names)
		assert(__default_onion_registry__.layer('custom-layer-1') is CustomLayer1)
		assert(__default_onion_registry__.layer('custom-layer-2') is CustomLayer2)

		@register_class
		class CustomLayer3(TestWOnion.BaseLayer):
			__layer_name__ = 'custom-layer-3'

		layers_names = tuple(__default_onion_registry__.layers_names())
		assert('custom-layer-1' in layers_names)
		assert('custom-layer-2' in layers_names)
		assert('custom-layer-3' in layers_names)
		assert(__default_onion_registry__.layer('custom-layer-1') is CustomLayer1)
		assert(__default_onion_registry__.layer('custom-layer-2') is CustomLayer2)
		assert(__default_onion_registry__.layer('custom-layer-3') is CustomLayer3)

	@pytest.mark.usefixtures('default_registry_wrap')
	def test_exceptions(self):
		with pytest.raises(TypeError):
			@register_class
			class CustomLayer(TestWOnion.BaseLayer):
				pass

		with pytest.raises(TypeError):
			@register_class
			class CustomLayer(TestWOnion.BaseLayer):
				__layer_name__ = 1

		with pytest.raises(TypeError):
			@register_class
			class CustomLayer(TestWOnion.BaseLayer):
				__layer_name__ = ''
