# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.hex import WHex, WUnHex


class TestWHex:
	def test___init__(self):
		pytest.raises(TypeError, WHex)
		pytest.raises(TypeError, WHex, 1)
		pytest.raises(TypeError, WHex, 'asd')
		assert(isinstance(WHex(b'asd'), WHex) is True)

		pytest.raises(TypeError, WUnHex)
		pytest.raises(TypeError, WUnHex, 1)
		assert(isinstance(WUnHex('asd'), WUnHex) is True)
		assert(isinstance(WUnHex(b'asd'), WUnHex) is True)

		assert(isinstance(str(WHex(b'a')), str) is True)
		assert(isinstance(bytes(WUnHex('61')), bytes) is True)
		assert(isinstance(bytes(WUnHex(b'61')), bytes) is True)

		assert(str(WHex(b'a')) == '61')
		assert(bytes(WUnHex('61')) == b'a')
		assert(bytes(WUnHex(b'61')) == b'a')

		assert(bytes(WUnHex(str(WHex(b'qwerty')))) == b'qwerty')
