# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.hash import WHashGeneratorProto, WPyCryptoHashAdapter, WHash, WSHA512


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

	def test(self):

		assert(issubclass(WPyCryptoHashAdapter, WHashGeneratorProto) is True)

		class PyCryptoGenerator:

			def __init__(self):
				self.__digest = (b'\x00' * self.digest_size())

			def update(self, data):
				self.__digest = b''
				for i in range(min(len(data), self.digest_size())):
					self.__digest += bytes([data[i] - 1])
				for i in range(min(len(data), self.digest_size()), self.digest_size()):
					self.__digest += b'\x00'

			def digest(self):
				return self.__digest

			@classmethod
			def digest_size(cls):
				return 13

			@classmethod
			def new(cls, data=None):
				obj = cls()
				if data is not None:
					obj.update(data)
				return obj

		class BuggyPyCryptoAdapter(WPyCryptoHashAdapter):
			pass

		pytest.raises(ValueError, BuggyPyCryptoAdapter)
		pytest.raises(ValueError, BuggyPyCryptoAdapter.generator_digest_size)

		class PyCryptoAdapter(WPyCryptoHashAdapter):
			__pycrypto_cls__ = PyCryptoGenerator

		a = PyCryptoAdapter()
		assert(a.digest_size() == 13)
		assert(a.digest() == b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
		a.update(b'12345')
		assert(a.digest() == b'01234\x00\x00\x00\x00\x00\x00\x00\x00')

		assert(a.pycrypto() is not None)
		assert(isinstance(a.pycrypto(), PyCryptoGenerator) is True)

		pytest.raises(ValueError, PyCryptoAdapter.generator_name)
		PyCryptoAdapter.__generator_name__ = 1
		pytest.raises(TypeError, PyCryptoAdapter.generator_name)
		PyCryptoAdapter.__generator_name__ = 'foo'
		assert(PyCryptoAdapter.generator_name() == 'FOO')

		assert(PyCryptoAdapter.generator_family() is None)
		PyCryptoAdapter.__generator_family__ = 1
		pytest.raises(TypeError, PyCryptoAdapter.generator_family)
		PyCryptoAdapter.__generator_family__ = 'bar'
		assert(PyCryptoAdapter.generator_family() == 'BAR')


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

		sha1_result = b'^\x98\x99\xf2\x1f\xff\xa2\xee\x8b\x16\xbex\x03\x8d\xd8\x860^?\x82'
		assert(WHash.generator('SHA1').new(b'data to hash').digest() == sha1_result)

		assert(WHash.generator_by_digest('SHA', 64) == WSHA512)
		pytest.raises(ValueError, WHash.generator_by_digest, '???', 1)

		pytest.raises(ValueError, WHash.generator, '???')

		digests = WHash.available_digests('SHA')
		assert(digests == {20, 28, 32, 48, 64})
