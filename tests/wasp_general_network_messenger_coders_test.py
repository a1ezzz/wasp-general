# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.aes import WFixedSecretAES, WAESMode
from wasp_general.crypto.rsa import WRSA

from wasp_general.network.messenger.envelope import WMessengerTextEnvelope, WMessengerBytesEnvelope
from wasp_general.network.messenger.onion import WMessengerOnionCoderLayerProto, WMessengerOnion
from wasp_general.network.messenger.proto import WMessengerOnionSessionFlowProto
from wasp_general.network.messenger.session import WMessengerOnionSessionFlow, WMessengerOnionSession

from wasp_general.network.messenger.coders import WMessengerFixedModificationLayer, WMessengerEncodingLayer
from wasp_general.network.messenger.coders import WMessengerHexLayer, WMessengerBase64Layer, WMessengerAESLayer
from wasp_general.network.messenger.coders import WMessengerRSALayer


class TestWMessengerFixedModificationLayer:

	def test_layer(self):
		assert(isinstance(WMessengerFixedModificationLayer(), WMessengerFixedModificationLayer) is True)
		assert(isinstance(WMessengerFixedModificationLayer(), WMessengerOnionCoderLayerProto) is True)

		head = WMessengerFixedModificationLayer.Target.head
		tail = WMessengerFixedModificationLayer.Target.tail
		text_envelope = WMessengerTextEnvelope('foo')
		bytes_envelope = WMessengerBytesEnvelope(b'bar')

		onion = WMessengerOnion()
		sf = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
		session = WMessengerOnionSession(onion, sf)

		layer = WMessengerFixedModificationLayer()
		result = layer.encode(text_envelope, session, target=head, modification_code='header::')
		assert(isinstance(result, WMessengerTextEnvelope) is True)
		assert(result.message() == 'header::foo')
		pytest.raises(RuntimeError, layer.encode, text_envelope, session, modification_code=b'foo')
		pytest.raises(RuntimeError, layer.decode, bytes_envelope, session, target=tail)
		pytest.raises(TypeError, layer.encode, text_envelope, session, target=head, modification_code=b'foo')
		pytest.raises(TypeError, layer.decode, bytes_envelope, session, target=tail, modification_code='f')
		pytest.raises(TypeError, layer.decode, bytes_envelope, session, target=1, modification_code='f')

		result = layer.decode(result, session, target=head, modification_code='header::')
		assert(isinstance(result, WMessengerTextEnvelope) is True)
		assert(result.message() == 'foo')

		invalid_envelope = WMessengerTextEnvelope('head::foo')
		pytest.raises(
			ValueError, layer.decode, invalid_envelope, session, target=head, modification_code='header::'
		)

		pytest.raises(
			ValueError, layer.decode, invalid_envelope, session, target=head,
			modification_code='very_long_header::'
		)

		result = layer.decode(
			layer.encode(bytes_envelope, session, target=tail, modification_code=b'::tail'),
			session, target=tail, modification_code=b'::tail'
		)
		assert(isinstance(result, WMessengerBytesEnvelope) is True)
		assert(result.message() == b'bar')

		invalid_envelope = WMessengerBytesEnvelope(b'foo::wrong_tail')
		pytest.raises(
			ValueError, layer.decode, invalid_envelope, session, target=tail, modification_code=b'::tail'
		)


class TestWMessengerEncodingLayer:

	def test(self):
		onion = WMessengerOnion()
		sf = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
		session = WMessengerOnionSession(onion, sf)
		layer = WMessengerEncodingLayer()

		assert(isinstance(layer, WMessengerEncodingLayer) is True)
		assert(isinstance(layer, WMessengerOnionCoderLayerProto) is True)

		encoded_data = layer.encode(WMessengerTextEnvelope('some text'), session)
		assert(isinstance(encoded_data, WMessengerBytesEnvelope) is True)
		assert(encoded_data.message() == b'some text')

		encoded_data = layer.encode(WMessengerTextEnvelope('some text'), session, encoding='ascii')
		assert(encoded_data.message() == b'some text')

		decoded_data = layer.decode(encoded_data, session, encoding='utf-8')
		assert(isinstance(decoded_data, WMessengerTextEnvelope) is True)
		assert(decoded_data.message() == 'some text')

		decoded_data = layer.decode(encoded_data, session)
		assert(decoded_data.message() == 'some text')


class TestWMessengerHexLayer:

	def test_layer(self):

		onion = WMessengerOnion()
		sf = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
		session = WMessengerOnionSession(onion, sf)
		layer = WMessengerHexLayer()

		assert(isinstance(layer, WMessengerHexLayer) is True)
		assert(isinstance(layer, WMessengerOnionCoderLayerProto) is True)

		result = layer.encode(WMessengerBytesEnvelope(b'msg1'), session)
		assert(isinstance(result, WMessengerTextEnvelope) is True)
		assert(result.message() == '6d736731')

		result = layer.decode(WMessengerTextEnvelope('7365636f6e64206d7367'), session)
		assert(isinstance(result, WMessengerBytesEnvelope) is True)
		assert(result.message() == b'second msg')


class TestWMessengerBase64Layer:

	def test_layer(self):

		onion = WMessengerOnion()
		sf = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
		session = WMessengerOnionSession(onion, sf)
		layer = WMessengerBase64Layer()

		assert(isinstance(layer, WMessengerBase64Layer) is True)
		assert(isinstance(layer, WMessengerOnionCoderLayerProto) is True)

		result = layer.encode(WMessengerBytesEnvelope(b'msg1'), session)
		assert(isinstance(result, WMessengerBytesEnvelope) is True)
		assert(result.message() == b'bXNnMQ==')

		result = layer.decode(WMessengerBytesEnvelope(b'c2Vjb25kIG1zZw=='), session)
		assert(isinstance(result, WMessengerBytesEnvelope) is True)
		assert(result.message() == b'second msg')


class TestWMessengerAESLayer:

	def test_layer(self):

		onion = WMessengerOnion()
		sf = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
		session = WMessengerOnionSession(onion, sf)
		layer = WMessengerAESLayer()

		aes_mode = WAESMode.defaults()
		aes_cipher = WFixedSecretAES('password', aes_mode)

		assert(isinstance(layer, WMessengerAESLayer) is True)
		assert(isinstance(layer, WMessengerOnionCoderLayerProto) is True)

		result = layer.encode(WMessengerBytesEnvelope(b'msg1'), session, aes_cipher=aes_cipher)
		assert(isinstance(result, WMessengerBytesEnvelope) is True)
		assert(result.message() == b'w^2\x1f\xbcPV\xa7\xe2#\xa9\xa3\xeb_\xd7Y')

		result = layer.decode(
			WMessengerBytesEnvelope(b'g\x1a\x9ed\x83\x83\x18\xca\xeaW\xc9\xc5ae\xa0\xe8'),
			session, aes_cipher=aes_cipher
		)
		assert(isinstance(result, WMessengerBytesEnvelope) is True)
		assert(result.message() == b'second msg')


class TestWMessengerRSALayer:

	def test_layer(self):

		onion = WMessengerOnion()
		sf = WMessengerOnionSessionFlow.sequence_flow(WMessengerOnionSessionFlowProto.IteratorInfo('layer'))
		session = WMessengerOnionSession(onion, sf)
		layer = WMessengerRSALayer()

		rsa_pk = WRSA.generate_private(1024)

		assert(isinstance(layer, WMessengerRSALayer) is True)
		assert(isinstance(layer, WMessengerOnionCoderLayerProto) is True)

		result = layer.encode(WMessengerBytesEnvelope(b'msg1'), session, public_key=rsa_pk)
		assert(isinstance(result, WMessengerBytesEnvelope) is True)
		assert(len(result.message()) == (1024 / 8))

		result = layer.decode(result, session, private_key=rsa_pk)
		assert(isinstance(result, WMessengerBytesEnvelope) is True)
		assert(result.message() == b'msg1')
