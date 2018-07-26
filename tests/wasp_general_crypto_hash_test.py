# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.hash import WHashGeneratorProto, WHash, WSHA1, WSHA224, WSHA384, WSHA512, WMD5
from wasp_general.crypto.hash import WPyCryptographyHashAdapter


def test_abstract():
	pytest.raises(TypeError, WHashGeneratorProto)
	pytest.raises(NotImplementedError, WHashGeneratorProto.update, None, b'')
	pytest.raises(NotImplementedError, WHashGeneratorProto.digest, None)
	pytest.raises(NotImplementedError, WHashGeneratorProto.generator_digest_size)
	pytest.raises(NotImplementedError, WHashGeneratorProto.generator_name)
	pytest.raises(NotImplementedError, WHashGeneratorProto.generator_family)
	pytest.raises(NotImplementedError, WHashGeneratorProto.new)


class TestWHashGeneratorProto:

	def test(self):
		class Dummy(WHashGeneratorProto):

			def update(self, data):
				pass

			def digest(self):
				return b'\x01\x02\x03\xff'

			@classmethod
			def generator_digest_size(cls):
				return 4

			@classmethod
			def generator_family(cls):
				return None

			@classmethod
			def generator_name(cls):
				return 'dummy'

			@classmethod
			def new(cls, data=None):
				return cls()

		assert(Dummy().hexdigest() == '010203FF')


class TestWPyCryptoHashAdapter:

	test_data = [
		(
			b'data to hash',
			WSHA1,
			b'^\x98\x99\xf2\x1f\xff\xa2\xee\x8b\x16\xbex\x03\x8d\xd8\x860^?\x82'
		),
		(
			b'data to hash',
			WSHA224,
			b'0\xb5bj\xef\x8c%{\xab\x87\xeakX\xc30\xd5\xd2\x80\x07\x7f\xd5\x84\x12\xa1\x9c\xe6r\xb7'
		),
		(
			b'data to hash',
			WSHA384,
			b'1\x1e\xd6\x16\xc2\xdb\xfa\xce\x15\xde}\xd6\xdf\xe8\xb3\xe6;,\xd2\xa0\t\x8c\xa35\xd1\xeb\xea'
			b'\x1d\x8fi\xe5\xb4\xff`g"\xf0\xe4\xbc\x99\x0f\xe2\xec@|\xcc@G'
		),
		(
			b'data to hash',
			WSHA512,
			b'\xd9\x8f\x94_\xeel\x90UY/\xa8\xf3\x98\x95;;|\xf3:G\xcf\xc5\x05f|\xbc\xa1\xad\xb3D\xff\x18'
			b'\xa4\xf4Bu\x88\x10\x18o\xb4\x80\xda\x89\xbc\x9d\xfa3(\t=\xb3K\xd9\xe4\xe4\xc3\x94\xae\xc0'
			b'\x83\xe1w:'
		),
		(
			b'data to hash',
			WMD5,
			b'\xe4\xc5c\x99\xc1\x95C\xc4\xeb\xb5=\x92[\xfc\xba\x18'
		)
	]

	@pytest.mark.parametrize("data_to_hash, cls, expected_hash", test_data)
	def test(self, data_to_hash, cls, expected_hash):
		obj = cls()
		obj.update(data_to_hash)
		assert(obj.digest() == expected_hash)

	def test_adapter(self):

		class E1(WPyCryptographyHashAdapter):
			pass

		pytest.raises(ValueError, E1)
		pytest.raises(ValueError, E1.generator_digest_size)
		pytest.raises(ValueError, E1.generator_name)

		class E2(WPyCryptographyHashAdapter):
			__generator_family__ = 1
			__generator_name__ = 1

		pytest.raises(TypeError, E2.generator_family)
		pytest.raises(TypeError, E2.generator_name)


class TestWHash:

	def test(self):
		names = WHash.available_generators()
		assert('SHA1' in names)
		assert('SHA224' in names)
		assert('SHA256' in names)
		assert('SHA384' in names)
		assert('SHA512' in names)

		names = WHash.available_generators(name='SHA1')
		assert('SHA1' in names)

		origin_data = b'data to hash'
		sha1_result = b'^\x98\x99\xf2\x1f\xff\xa2\xee\x8b\x16\xbex\x03\x8d\xd8\x860^?\x82'
		sha1_obj = WSHA1()
		sha1_obj.update(origin_data)
		assert(sha1_obj.digest() == sha1_result)
		assert(WHash.generator('SHA1').new(origin_data).digest() == sha1_result)

		assert(WHash.generator_by_digest('SHA', 64) == WSHA512)
		pytest.raises(ValueError, WHash.generator_by_digest, '???', 1)

		pytest.raises(ValueError, WHash.generator, '???')

		digests = WHash.available_digests('SHA')
		assert(digests == {20, 28, 32, 48, 64})
