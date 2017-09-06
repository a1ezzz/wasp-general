# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.hash import WHash


class TestWHash:

	def test(self):
		names = WHash.available_generators()
		assert('SHA1' in names)
		assert('SHA224' in names)
		assert('SHA256' in names)
		assert('SHA384' in names)
		assert('SHA512' in names)

		sha1_result = b'^\x98\x99\xf2\x1f\xff\xa2\xee\x8b\x16\xbex\x03\x8d\xd8\x860^?\x82'
		assert(WHash.generator('SHA1').new(b'data to hash').digest() == sha1_result)

		pytest.raises(ValueError, WHash.generator, '???')
