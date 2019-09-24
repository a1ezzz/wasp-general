# -*- coding: utf-8 -*-

import pytest

from wasp_general.api.registry import WAPIRegistryProto, WAPIRegistry, WNoSuchAPIIdError

from wasp_general.api.onion.proto import WEnvelopeProto, WOnionLayerProto, WOnionSessionFlowProto, WOnionProto


class Envelope(WEnvelopeProto):

	def data(self):
		pass

	def layers(self, layer_name=None):
		pass

	def meta(self, layer_name):
		pass


class SessionFlow(WOnionSessionFlowProto):

	def next(self, envelope):
		pass


def test_abstract():
	pytest.raises(TypeError, WEnvelopeProto)
	pytest.raises(NotImplementedError, WEnvelopeProto.data, None)
	pytest.raises(NotImplementedError, WEnvelopeProto.layers, None)

	pytest.raises(TypeError, WOnionProto)
	pytest.raises(NotImplementedError, WOnionProto.get, None, None)
	pytest.raises(NotImplementedError, WOnionProto.ids, None)
	pytest.raises(NotImplementedError, WOnionProto.register, None, 'proto', WOnionLayerProto)

	pytest.raises(TypeError, WOnionSessionFlowProto)
	pytest.raises(NotImplementedError, WOnionSessionFlowProto.next, None, Envelope())

	pytest.raises(TypeError, WOnionLayerProto)


@pytest.mark.asyncio
async def test_asyncio_abstract():
	with pytest.raises(NotImplementedError):
		await WOnionLayerProto.process(None, Envelope())

	with pytest.raises(NotImplementedError):
		await WOnionProto.process(None, SessionFlow(), Envelope())


class TestWOnionSessionFlow:

	def test_layer_info(self):
		li = WOnionSessionFlowProto.LayerInfo('layer_name', 'foo', 7, a=1, b='code')
		assert(li.layer_name() == 'layer_name')
		assert(li.layer_args() == ('foo', 7))
		assert(li.layer_kwargs() == {'a': 1, 'b': 'code'})

		li = WOnionSessionFlowProto.LayerInfo('name2')
		assert(li.layer_name() == 'name2')
		assert(li.layer_args() == tuple())
		assert(li.layer_kwargs() == dict())


class TestWOnionProto:

	def test(self):
		assert(issubclass(WOnionProto, WAPIRegistryProto) is True)

		class Onion(WOnionProto, WAPIRegistry):

			async def process(self, session_flow, envelope):
				return envelope

			def register(self, api_id, api_descriptor):
				WAPIRegistry.register(self, api_id, api_descriptor)

		class L1:
			pass

		class L2:
			pass

		onion = Onion()
		assert(tuple(onion.layers_names()) == tuple())
		pytest.raises(WNoSuchAPIIdError, onion.layer, 'l1')
		pytest.raises(WNoSuchAPIIdError, onion.layer, 'l2')

		onion.register('l1', L1)
		assert(tuple(onion.layers_names()) == ('l1', ))
		assert(onion.layer('l1') is L1)
		pytest.raises(WNoSuchAPIIdError, onion.layer, 'l2')

		onion.register('l2', L2)
		layers = tuple(onion.layers_names())
		assert(len(layers) == 2)
		assert('l1' in layers)
		assert('l2' in layers)
		assert(onion.layer('l1') is L1)
		assert(onion.layer('l2') is L2)
