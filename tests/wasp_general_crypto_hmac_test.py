# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.hmac import WHMAC
from wasp_general.crypto.hash import WHash


class TestWHMAC:

	def test(self):
		hmac = WHMAC()
		assert(hmac.digest_generator() == WHash.generator('SHA512'))

		hmac_sha512_result = b'\xc5\xb6\xe3{\x83\xe8A\x1a\xd6\'\x0e\xb1L\x89|a\x8eU\xb2u"\x9e\xefo'
		hmac_sha512_result += b'\xfdkPZ\xd5\x9b\xe2U\xa7\xc3\xc1\x99\xcdf~\xf6\xcbc\xd9\xf8\x9a\xe6\xf9\xe6'
		hmac_sha512_result += b'\xc64_.\xa4\x04\x9e\xac\x9a\x8f\xfe#lfBf'
		assert(hmac.hash(b'11111key2222') == hmac_sha512_result)

		hmac = WHMAC('SHA256')
		assert(hmac.digest_generator() == WHash.generator('SHA256'))
		hmac_sha256_result = b'\x0c\\\xb3\xf1\x08\x84\x18E\xc2l\xf5\xd8\xbc\x85\xd6'
		hmac_sha256_result += b'\x8f?_\xee\xfe\xd9\xf8a\xbc\xa8\x88\xb6o\xd8e\xa3\xf1'
		assert(hmac.hash(b'11111key2222') == hmac_sha256_result)

		hmac = WHMAC.hmac('HMAC-SHA1')
		assert(hmac.digest_generator() == WHash.generator('SHA1'))
		assert(WHMAC.hmac('HMAC-SHA1').digest_generator() == WHMAC.hmac('HMAC_SHA1').digest_generator())
		hmac_sha1_result = b'\xaa\xcb9\x1d\xd4\xeb\xad\xc4s\x03\x83ONN\x8en\xc8\x88I\x1c'
		assert(hmac.hash(b'11111key2222', message=b'some salt') == hmac_sha1_result)

		pytest.raises(ValueError, WHMAC, '???')
