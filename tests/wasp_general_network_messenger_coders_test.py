# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.aes import WFixedSecretAES, WAESMode
from wasp_general.crypto.rsa import WRSA

from wasp_general.network.messenger.onion import WMessengerOnionCoderLayerBase
from wasp_general.network.messenger.coders import WMessengerFixedModificationLayer, WMessengerHexLayer
from wasp_general.network.messenger.coders import WMessengerBase64Layer, WMessengerAESLayer, WMessengerRSALayer


class TestWMessengerFixedModificationLayer:

	def test_layer(self):
		assert(isinstance(WMessengerFixedModificationLayer('l'), WMessengerFixedModificationLayer) is True)
		assert(isinstance(WMessengerFixedModificationLayer('l'), WMessengerOnionCoderLayerBase) is True)

		pytest.raises(TypeError, WMessengerFixedModificationLayer, 'layer', '', b'')

		m0 = WMessengerFixedModificationLayer('layer')
		assert (m0.encode('foo') == 'foo')
		assert (m0.decode('foo') == 'foo')
		assert (m0.decode('') == '')

		m1 = WMessengerFixedModificationLayer('layer', 'header::')
		assert (m1.encode('foo') == 'header::foo')
		pytest.raises(TypeError, m1.encode, b'foo')
		pytest.raises(TypeError, m1.decode, b'f')
		pytest.raises(ValueError, m1.decode, 'f')
		pytest.raises(ValueError, m1.decode, 'footer::foo')
		assert (m1.decode('header::foo') == 'foo')

		m2 = WMessengerFixedModificationLayer('layer', b'header::', b'::footer')
		assert (m2.encode(b'foo') == b'header::foo::footer')
		pytest.raises(TypeError, m2.encode, 'foo')
		assert (m2.decode(b'header::bar::footer') == b'bar')
		pytest.raises(ValueError, m2.decode, b'header::bar::header')


class TestWMessengerHexLayer:

	def test_layer(self):
		assert(isinstance(WMessengerHexLayer(), WMessengerHexLayer) is True)
		assert(isinstance(WMessengerHexLayer(), WMessengerOnionCoderLayerBase) is True)

		l = WMessengerHexLayer()
		assert(l.encode('msg1') == '6d736731')
		assert(l.encode(b'msg1') == '6d736731')

		assert(l.decode('7365636f6e64206d7367') == b'second msg')
		assert(l.decode(b'7365636f6e64206d7367') == b'second msg')


class TestWMessengerBase64Layer:

	def test_layer(self):
		assert(isinstance(WMessengerBase64Layer(), WMessengerBase64Layer) is True)
		assert(isinstance(WMessengerBase64Layer(), WMessengerOnionCoderLayerBase) is True)

		l = WMessengerBase64Layer()
		assert(l.encode('msg1') == b'bXNnMQ==')
		assert(l.encode(b'msg1') == b'bXNnMQ==')

		assert(l.decode(b'c2Vjb25kIG1zZw==') == b'second msg')
		assert(l.decode('c2Vjb25kIG1zZw==') == b'second msg')


class TestWMessengerAESLayer:

	def test_layer(self):
		aes_mode = WAESMode.defaults()
		aes1 = WFixedSecretAES('password', aes_mode)
		aes2 = WFixedSecretAES('secret password', aes_mode)

		l1 = WMessengerAESLayer('l', aes1)
		l2 = WMessengerAESLayer('l', aes2)

		assert(isinstance(l1, WMessengerAESLayer) is True)
		assert(isinstance(l2, WMessengerOnionCoderLayerBase) is True)

		assert(l1.encode('msg1') == b'w^2\x1f\xbcPV\xa7\xe2#\xa9\xa3\xeb_\xd7Y')
		assert(l2.encode(b'second msg') == b'7z\x0fH\x94\x98\x96ix\xc1\xb7=\xcf\xd7\xb1\x03')

		assert(l1.decode(b'g\x1a\x9ed\x83\x83\x18\xca\xeaW\xc9\xc5ae\xa0\xe8') == b'second msg')
		assert(l2.decode(b'\xdb\xbd\xd7\x19\x9e\xb4T\xd42\xe5\xec\xb1\x89\x9d\xf2\x96') == b'msg1')


class TestWMessengerRSALayer:

	def test_layer(self):

		rsa_pk1 = WRSA.generate_private(1024)
		rsa_pk2 = WRSA.generate_private(1024)

		l1 = WMessengerRSALayer('l', rsa_pk1, rsa_pk1)
		l2 = WMessengerRSALayer('l', rsa_pk2, rsa_pk2)

		assert(isinstance(l1, WMessengerRSALayer) is True)
		assert(isinstance(l2, WMessengerOnionCoderLayerBase) is True)

		assert(l1.decode(l1.encode('msg1')) == b'msg1')
		pytest.raises(ValueError, l2.decode, l1.encode('msg1'))

		assert(l2.decode(l2.encode(b'second message')) == b'second message')
		pytest.raises(ValueError, l1.decode, l2.encode(b'second message'))
