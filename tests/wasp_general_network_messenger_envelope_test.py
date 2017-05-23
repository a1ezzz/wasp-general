# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.messenger.proto import WMessengerEnvelopeProto
from wasp_general.network.messenger.envelope import WMessengerEnvelope, WMessengerTextEnvelope, WMessengerBytesEnvelope


class TestWMessengerEnvelope:

	def test(self):
		envelope = WMessengerEnvelope(1)
		assert(isinstance(envelope, WMessengerEnvelope) is True)
		assert(isinstance(envelope, WMessengerEnvelopeProto) is True)
		assert(envelope.message() == 1)
		assert(envelope.meta() == {})

		envelope = WMessengerEnvelope('zxc', meta={'a': 1, 'b': 'c'})
		assert(envelope.message() == 'zxc')
		assert(envelope.meta() == {'a': 1, 'b': 'c'})

		envelope = WMessengerEnvelope(None, meta=envelope)
		assert(envelope.message() is None)
		assert(envelope.meta() == {'a': 1, 'b': 'c'})

		envelope.add_meta('z', 0)
		assert(envelope.meta() == {'a': 1, 'b': 'c', 'z': 0})

		envelope.meta()['q'] = 'q'
		assert(envelope.meta() == {'a': 1, 'b': 'c', 'z': 0})

		class E(WMessengerEnvelopeProto):

			def message(self):
				pass

			def meta(self):
				return {}

		pytest.raises(TypeError, WMessengerEnvelope, 1, E())


class TestWMessengerTextEnvelope:

	def test(self):
		s = WMessengerTextEnvelope('q')
		assert(isinstance(s, WMessengerTextEnvelope) is True)
		assert(isinstance(s, WMessengerEnvelope) is True)

		pytest.raises(TypeError, WMessengerTextEnvelope, None)


class TestWMessengerBytesEnvelope:
	def test(self):
		s = WMessengerBytesEnvelope(b'q')
		assert (isinstance(s, WMessengerBytesEnvelope) is True)
		assert (isinstance(s, WMessengerEnvelope) is True)

		pytest.raises(TypeError, WMessengerBytesEnvelope, None)
