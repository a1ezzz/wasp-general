
import pytest
import asyncio
from enum import Enum

from wasp_general.crypto.aes import WAES, WAESMode, WPKCS7Padding
from wasp_general.crypto.rsa import WRSA

from wasp_general.api.transformation import WTransformationError, WTransformationRegistry
from wasp_general.api.transformation import __default_transformation_registry__

from wasp_general.api.onion.proto import WEnvelopeProto
from wasp_general.api.onion.base import WEnvelope

from wasp_general.api.onion.layers import WAsyncIOLayer, WOnionBaseLayerModes, WLayerSerializationMode
from wasp_general.api.onion.layers import WLayerEncodingMode, WLayerEncryptionMode, WOnionJSONLayer
from wasp_general.api.onion.layers import WOnionWrappingLayer, WOnionEncodingLayer, WOnionHexLayer, WOnionBase64Layer
from wasp_general.api.onion.layers import WOnionAESLayer, WOnionRSALayer, WTransformationLayer


def test_abstract():
	pytest.raises(TypeError, WOnionBaseLayerModes)


def test_enums():
	assert(issubclass(WLayerSerializationMode, Enum))
	assert(issubclass(WLayerEncodingMode, Enum))
	assert(issubclass(WLayerEncryptionMode, Enum))


class TestWAsyncIOLayer:

	@pytest.mark.asyncio
	async def test(self):

		async def foo(i):
			return i + 1

		c = foo(0)
		pytest.raises(TypeError, WAsyncIOLayer, c)
		await c

		c = foo(0)
		pytest.raises(TypeError, WAsyncIOLayer, asyncio.get_running_loop().create_task(c))

		asyncio_layer = WAsyncIOLayer(foo)
		r = await asyncio_layer.process(WEnvelope(1))
		assert(r.data() == 2)
		r = await asyncio_layer.process(WEnvelope(8))
		assert(r.data() == 9)


class TestWOnionBaseLayerModes:

	@pytest.mark.asyncio
	async def test(self):

		class Layer1(WOnionBaseLayerModes):

			@classmethod
			def name(cls):
				return 'layer'
		pytest.raises(TypeError, Layer1)

		class Layer2(WOnionBaseLayerModes):

			class E(Enum):
				foo = 1
				bar = 2

			__modes__ = E

			@classmethod
			def name(cls):
				return 'layer'

		pytest.raises(TypeError, Layer2, Layer2.E.foo)

		class Layer3(WOnionBaseLayerModes):

			@classmethod
			def name(cls):
				return 'layer'

			# noinspection PyMethodMayBeStatic
			# noinspection PyUnusedLocal
			async def foo(self, e):
				return 'foo'

			# noinspection PyMethodMayBeStatic
			# noinspection PyUnusedLocal
			async def bar(self, e):
				return WEnvelope('bar', layer_name='layer', layer_meta=3, previous_meta=e)

		pytest.raises(TypeError, Layer3)

		class Layer4(WOnionBaseLayerModes):

			class E(Enum):
				foo = 1
				bar = 2

			__modes__ = E

			@classmethod
			def name(cls):
				return 'layer'

			# noinspection PyMethodMayBeStatic
			# noinspection PyUnusedLocal
			async def foo(self, e):
				return 'foo'

		pytest.raises(TypeError, Layer4, Layer4.E.foo)

		class Layer5(WOnionBaseLayerModes):

			class E(Enum):
				foo = 1
				bar = 2

			__modes__ = E

			@classmethod
			def name(cls):
				return 'layer'

			# noinspection PyMethodMayBeStatic
			# noinspection PyUnusedLocal
			async def bar(self, e):
				return WEnvelope('bar', layer_name='layer', layer_meta=5, previous_meta=e)

		pytest.raises(TypeError, Layer5, Layer5.E.foo)

		class Layer6(WOnionBaseLayerModes):

			class E(Enum):
				foo = 1
				bar = 2

			__modes__ = E

			@classmethod
			def name(cls):
				return 'layer'

			# noinspection PyMethodMayBeStatic
			# noinspection PyUnusedLocal
			async def foo(self, e):
				return 'foo'

			# noinspection PyMethodMayBeStatic
			# noinspection PyUnusedLocal
			async def bar(self, e):
				return WEnvelope('bar', layer_name='layer', layer_meta=6, previous_meta=e)

		layer6_foo = Layer6(Layer6.E.foo)
		pytest.raises(TypeError, Layer6, Layer5.E.foo)

		r = await layer6_foo.process(WEnvelope(1))
		assert(isinstance(r, WEnvelopeProto))
		assert(r.data() == 'foo')
		assert(tuple(r.layers()) == tuple())

		r = await layer6_foo.process(WEnvelope(1, layer_name='first_layer'))
		assert(r.data() == 'foo')
		assert(tuple(r.layers()) == (('first_layer', None),))

		layer6_bar = Layer6(Layer6.E.bar)
		r = await layer6_bar.process(WEnvelope(1))
		assert(r.data() == 'bar')
		assert(tuple(r.layers()) == (('layer', 6),))

		layer6_bar = Layer6(Layer6.E.bar)
		r = await layer6_bar.process(WEnvelope(1, layer_name='first_layer'))
		assert(r.data() == 'bar')
		assert(tuple(r.layers()) == (('first_layer', None), ('layer', 6)))


class TestWOnionJSONLayer:

	@pytest.mark.asyncio
	async def test(self):
		assert(issubclass(WOnionJSONLayer, WOnionBaseLayerModes))
		assert(WOnionJSONLayer.__layer_name__ is not None)
		assert(WOnionJSONLayer.__modes__ is not None)
		assert(WOnionJSONLayer.__modes__ is WLayerSerializationMode)

		serialization_layer = WOnionJSONLayer(WLayerSerializationMode.serialize)
		deserialization_layer = WOnionJSONLayer(WLayerSerializationMode.deserialize)
		r = await serialization_layer.process(WEnvelope(1))
		assert(r.data() == '1')
		r = await deserialization_layer.process(r)
		assert(r.data() == 1)

		r = await serialization_layer.process(WEnvelope('foo'))
		assert(r.data() == '"foo"')
		r = await deserialization_layer.process(r)
		assert(r.data() == 'foo')

		r = await serialization_layer.process(WEnvelope(None))
		assert(r.data() == 'null')
		r = await deserialization_layer.process(r)
		assert(r.data() is None)

		obj = [{"foo": 'zzz'}, 10]
		r = await serialization_layer.process(WEnvelope(obj))
		assert(isinstance(r.data(), str))
		r = await deserialization_layer.process(r)
		assert(r.data() == obj)

		with pytest.raises(TypeError):
			await serialization_layer.process(WEnvelope(object()))


class TestWOnionWrappingLayer:

	@pytest.mark.asyncio
	async def test(self):
		assert(issubclass(WOnionWrappingLayer, WOnionBaseLayerModes))
		assert(issubclass(WOnionWrappingLayer.Mode, Enum))
		assert(WOnionWrappingLayer.__layer_name__ is not None)
		assert(WOnionWrappingLayer.__modes__ is not None)
		assert(WOnionWrappingLayer.__modes__ is WOnionWrappingLayer.Mode)

		layer = WOnionWrappingLayer(
			WOnionWrappingLayer.Mode.append, WOnionWrappingLayer.Target.head, 'header::'
		)
		r = await layer.process(WEnvelope('foo'))
		assert(r.data() == 'header::foo')
		with pytest.raises(TypeError):
			await layer.process(WEnvelope(b'foo'))

		layer = WOnionWrappingLayer(
			WOnionWrappingLayer.Mode.append, WOnionWrappingLayer.Target.tail, '::tail'
		)
		r = await layer.process(WEnvelope('foo'))
		assert(r.data() == 'foo::tail')
		with pytest.raises(TypeError):
			await layer.process(WEnvelope(b'foo'))

		layer = WOnionWrappingLayer(
			WOnionWrappingLayer.Mode.append, WOnionWrappingLayer.Target.head, b'header::'
		)
		r = await layer.process(WEnvelope(b'foo'))
		assert(r.data() == b'header::foo')
		with pytest.raises(TypeError):
			await layer.process(WEnvelope('foo'))

		layer = WOnionWrappingLayer(
			WOnionWrappingLayer.Mode.append, WOnionWrappingLayer.Target.tail, b'::tail'
		)
		r = await layer.process(WEnvelope(b'foo'))
		assert(r.data() == b'foo::tail')
		with pytest.raises(TypeError):
			await layer.process(WEnvelope('foo'))

		layer = WOnionWrappingLayer(
			WOnionWrappingLayer.Mode.remove, WOnionWrappingLayer.Target.head, 'header::'
		)
		r = await layer.process(WEnvelope('header::foo'))
		assert(r.data() == 'foo')
		with pytest.raises(TypeError):
			await layer.process(WEnvelope(b'foo'))
		with pytest.raises(ValueError):
			await layer.process(WEnvelope('foo'))

		layer = WOnionWrappingLayer(
			WOnionWrappingLayer.Mode.remove, WOnionWrappingLayer.Target.tail, '::tail'
		)
		r = await layer.process(WEnvelope('foo::tail'))
		assert(r.data() == 'foo')
		with pytest.raises(TypeError):
			await layer.process(WEnvelope(b'foo'))
		with pytest.raises(ValueError):
			await layer.process(WEnvelope('foo'))

		layer = WOnionWrappingLayer(
			WOnionWrappingLayer.Mode.remove, WOnionWrappingLayer.Target.head, b'header::'
		)
		r = await layer.process(WEnvelope(b'header::foo'))
		assert(r.data() == b'foo')
		with pytest.raises(TypeError):
			await layer.process(WEnvelope('foo'))
		with pytest.raises(ValueError):
			await layer.process(WEnvelope(b'foo'))

		layer = WOnionWrappingLayer(
			WOnionWrappingLayer.Mode.remove, WOnionWrappingLayer.Target.tail, b'::tail'
		)
		r = await layer.process(WEnvelope(b'foo::tail'))
		assert(r.data() == b'foo')
		with pytest.raises(TypeError):
			await layer.process(WEnvelope('foo'))
		with pytest.raises(ValueError):
			await layer.process(WEnvelope(b'foo'))


class TestWOnionEncodingLayer:

	@pytest.mark.asyncio
	async def test(self):
		assert(issubclass(WOnionEncodingLayer, WOnionBaseLayerModes))
		assert(WOnionEncodingLayer.__layer_name__ is not None)
		assert(WOnionEncodingLayer.__modes__ is not None)
		assert(WOnionEncodingLayer.__modes__ is WLayerEncodingMode)

		layer = WOnionEncodingLayer(WLayerEncodingMode.encode)
		r = await layer.process(WEnvelope('foo'))
		assert(r.data() == b'foo')
		r = await layer.process(WEnvelope('тест'))
		assert(r.data() == b'\xd1\x82\xd0\xb5\xd1\x81\xd1\x82')

		layer = WOnionEncodingLayer(WLayerEncodingMode.encode, encoding='ascii')
		r = await layer.process(WEnvelope('foo'))
		assert(r.data() == b'foo')

		with pytest.raises(UnicodeEncodeError):
			await layer.process(WEnvelope('тест'))

		layer = WOnionEncodingLayer(WLayerEncodingMode.encode, encoding='koi8-r')
		r = await layer.process(WEnvelope('foo'))
		assert(r.data() == b'foo')
		r = await layer.process(WEnvelope('тест'))
		assert(r.data() == b'\xd4\xc5\xd3\xd4')

		layer = WOnionEncodingLayer(WLayerEncodingMode.decode)
		r = await layer.process(WEnvelope(b'foo'))
		assert(r.data() == 'foo')
		r = await layer.process(WEnvelope(b'\xd1\x82\xd0\xb5\xd1\x81\xd1\x82'))
		assert(r.data() == 'тест')

		layer = WOnionEncodingLayer(WLayerEncodingMode.decode, encoding='ascii')
		r = await layer.process(WEnvelope(b'foo'))
		assert(r.data() == 'foo')

		with pytest.raises(UnicodeDecodeError):
			await layer.process(WEnvelope(b'\xd1\x82\xd0\xb5\xd1\x81\xd1\x82'))

		layer = WOnionEncodingLayer(WLayerEncodingMode.decode, encoding='koi8-r')
		r = await layer.process(WEnvelope(b'foo'))
		assert(r.data() == 'foo')
		r = await layer.process(WEnvelope(b'\xd4\xc5\xd3\xd4'))
		assert(r.data() == 'тест')


class TestWOnionHexLayer:

	@pytest.mark.asyncio
	async def test(self):
		assert(issubclass(WOnionHexLayer, WOnionBaseLayerModes))
		assert(WOnionHexLayer.__layer_name__ is not None)
		assert(WOnionHexLayer.__modes__ is not None)
		assert(WOnionHexLayer.__modes__ is WLayerEncodingMode)

		encoding_layer = WOnionHexLayer(WLayerEncodingMode.encode)
		decoding_layer = WOnionHexLayer(WLayerEncodingMode.decode)
		r = await encoding_layer.process(WEnvelope(b'foo'))
		assert(r.data() == '666f6f')
		r = await decoding_layer.process(r)
		assert(r.data() == b'foo')


class TestWOnionBase64Layer:

	@pytest.mark.asyncio
	async def test(self):
		assert(issubclass(WOnionBase64Layer, WOnionBaseLayerModes))
		assert(WOnionBase64Layer.__layer_name__ is not None)
		assert(WOnionBase64Layer.__modes__ is not None)
		assert(WOnionBase64Layer.__modes__ is WLayerEncodingMode)

		encoding_layer = WOnionBase64Layer(WLayerEncodingMode.encode)
		decoding_layer = WOnionBase64Layer(WLayerEncodingMode.decode)
		r = await encoding_layer.process(WEnvelope(b'foo'))
		assert(r.data() == 'Zm9v')
		r = await decoding_layer.process(r)
		assert(r.data() == b'foo')


class TestWOnionAESLayer:

	@pytest.mark.asyncio
	async def test(self):
		assert(issubclass(WOnionAESLayer, WOnionBaseLayerModes))
		assert(WOnionAESLayer.__layer_name__ is not None)
		assert(WOnionAESLayer.__modes__ is not None)
		assert(WOnionAESLayer.__modes__ is WLayerEncryptionMode)

		aes = WAES(WAESMode(16, 'AES-CBC', b'0' * 32, padding=WPKCS7Padding()))

		encryption_layer = WOnionAESLayer(WLayerEncryptionMode.encrypt, aes)
		decryption_layer = WOnionAESLayer(WLayerEncryptionMode.decrypt, aes)
		r = await encryption_layer.process(WEnvelope(b'foo'))
		data = r.data()
		assert(len(data) == 16)
		r = await decryption_layer.process(r)
		assert(r.data() == b'foo')


class TestWOnionRSALayer:

	@pytest.mark.asyncio
	async def test(self):
		assert(issubclass(WOnionRSALayer, WOnionBaseLayerModes))
		assert(WOnionRSALayer.__layer_name__ is not None)
		assert(WOnionRSALayer.__modes__ is not None)
		assert(WOnionRSALayer.__modes__ is WLayerEncryptionMode)

		rsa = WRSA()
		rsa.generate_private_key(key_size=2048)

		encryption_layer = WOnionRSALayer(WLayerEncryptionMode.encrypt, rsa)
		decryption_layer = WOnionRSALayer(WLayerEncryptionMode.decrypt, rsa)
		encrypted_envelope = await encryption_layer.process(WEnvelope(b'foo'))
		data = encrypted_envelope.data()
		assert(len(data) == 256)
		decrypted_envelope = await decryption_layer.process(encrypted_envelope)
		assert(decrypted_envelope.data() == b'foo')

		pytest.raises(ValueError, WOnionRSALayer, WLayerEncryptionMode.encrypt, WRSA())

		invalid_rsa = WRSA()
		invalid_rsa.import_public_key(rsa.export_public_key())
		pytest.raises(ValueError, WOnionRSALayer, WLayerEncryptionMode.decrypt, invalid_rsa)


class TestWTransformationLayer:

	@pytest.mark.asyncio
	async def test(self):
		assert(issubclass(WTransformationLayer, WOnionBaseLayerModes))
		assert(WTransformationLayer.__layer_name__ is not None)
		assert(WTransformationLayer.__modes__ is not None)
		assert(WTransformationLayer.__modes__ is WLayerSerializationMode)

		serialization_layer = WTransformationLayer(WLayerSerializationMode.serialize)
		deserialization_layer = WTransformationLayer(WLayerSerializationMode.deserialize)

		class A:
			def __init__(self, i):
				self.i = i

			def __eq__(self, other):
				return self.i == other.i

		plain_obj = {'1': 'a', 2: 'b', 3: None, 4: 4.}

		serialized_obj = await serialization_layer.process(WEnvelope(plain_obj))
		serialized_obj = serialized_obj.data()
		deserialized_obj = await deserialization_layer.process(WEnvelope(serialized_obj))

		assert(deserialized_obj.data() == plain_obj)

		non_default_obj = plain_obj.copy()
		non_default_obj['z'] = A(7)

		with pytest.raises(WTransformationError):
			await serialization_layer.process(WEnvelope(non_default_obj))

		registry = WTransformationRegistry(fallback_registry=__default_transformation_registry__)
		registry.register_function(
			A, WTransformationRegistry.RegFunctionType.compose_fn, lambda x, r: A(x)
		)
		registry.register_function(
			A, WTransformationRegistry.RegFunctionType.dismantle_fn, lambda x, r: x.i
		)

		serialization_layer = WTransformationLayer(
			WLayerSerializationMode.serialize, transformation_registry=registry
		)
		deserialization_layer = WTransformationLayer(
			WLayerSerializationMode.deserialize, transformation_registry=registry
		)

		serialized_obj = await serialization_layer.process(WEnvelope(non_default_obj))
		serialized_obj = serialized_obj.data()
		deserialized_obj = await deserialization_layer.process(WEnvelope(serialized_obj))

		assert(deserialized_obj.data() == non_default_obj)
