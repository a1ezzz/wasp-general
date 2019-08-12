# -*- coding: utf-8 -*-

import pytest

from wasp_general.onion.proto import WEnvelopeProto, WOnionLayerProto, WOnionSessionFlowProto, WOnionProto


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
	pytest.raises(NotImplementedError, WOnionProto.layer, None, 'foo')
	pytest.raises(NotImplementedError, WOnionProto.layers_names, None)

	pytest.raises(TypeError, WOnionSessionFlowProto)
	pytest.raises(NotImplementedError, WOnionSessionFlowProto.next, None, Envelope())

	pytest.raises(TypeError, WOnionLayerProto)
	pytest.raises(NotImplementedError, WOnionLayerProto.name)


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
