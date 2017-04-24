# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.sha import WSHA


class TestWSHA:

	def test_available_digests(self):
		assert(WSHA.available_digests() == (20, 28, 32, 48, 64))

	def test_digest_size(self):
		pytest.raises(TypeError, WSHA.digest_size, '')
		pytest.raises(ValueError, WSHA.digest_size, 19)
		pytest.raises(ValueError, WSHA.digest_size, 65)

		assert(WSHA.digest_size(20) == 20)
		assert(WSHA.digest_size(28) == 28)
		assert(WSHA.digest_size(32) == 32)
		assert(WSHA.digest_size(48) == 48)
		assert(WSHA.digest_size(64) == 64)

	def test_hash(self):
		pytest.raises(TypeError, WSHA.hash, 1)
		pytest.raises(TypeError, WSHA.hash, '')

		assert(WSHA.hash(b'qwerty') == WSHA.hash(b'qwerty'))
		assert(WSHA.hash(b'ytrewq') != WSHA.hash(b'qwerty'))
		assert(len(WSHA.hash(b'qwerty', 20)) == 20)
		assert(len(WSHA.hash(b'qwerty', 28)) == 28)
		assert(len(WSHA.hash(b'qwerty', 32)) == 32)
		assert(len(WSHA.hash(b'qwerty', 48)) == 48)
		assert(len(WSHA.hash(b'qwerty', 64)) == 64)

		pytest.raises(ValueError, WSHA.hash, b'qwerty', 19)

		assert(WSHA.hash(b'qwerty', 20) != WSHA.hash(b'qwerty', 28)[:20])
