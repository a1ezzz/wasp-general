# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.rsa import WRSA


class TestWRSA:

	def test_generate_private(self):
		assert(WRSA.generate_private() is not None)
		assert(WRSA.generate_private(2048).size() == 2047)
		assert(WRSA.generate_private(1280).size() == 1279)
		assert(WRSA.generate_private(1024).size() == 1023)

	def test_export_key(self):
		pk = WRSA.generate_private(1024)
		assert(isinstance(WRSA.export_key(pk), bytes) is True)
		assert(WRSA.export_key(pk) == WRSA.export_key(pk))
		assert(WRSA.export_key(pk, 'foo') != WRSA.export_key(pk, 'foo'))
		assert(WRSA.export_key(pk, b'foo') != WRSA.export_key(pk, b'foo'))
		pytest.raises(TypeError, WRSA.export_key, pk, 1)

		pytest.raises(TypeError, WRSA.import_key, 1)
		pytest.raises(TypeError, WRSA.import_key, WRSA.export_key(pk), 1)
		assert(WRSA.import_key(WRSA.export_key(pk)) == pk)
		assert(WRSA.import_key(WRSA.export_key(pk, 'foo'), 'foo') == pk)
		pytest.raises(ValueError, WRSA.import_key, WRSA.export_key(pk, 'foo'))
		assert(WRSA.import_key(WRSA.export_key(pk), 'foo') == pk)

		pk = WRSA.generate_public(pk)
		assert(WRSA.export_key(pk) == WRSA.export_key(pk))
		assert(WRSA.export_key(pk, 'foo') == WRSA.export_key(pk, 'foo'))
		assert(WRSA.export_key(pk, b'foo') == WRSA.export_key(pk, b'foo'))
		assert(WRSA.export_key(pk, b'foo') == WRSA.export_key(pk, 'bar'))
		assert(WRSA.import_key(WRSA.export_key(pk)) == pk)

	def test_generate_public(self):
		pytest.raises(TypeError, WRSA.generate_public, 'bla-bla')

		assert(WRSA.generate_public(WRSA.generate_private(1024)).size() == 1023)
		assert(WRSA.generate_public(WRSA.generate_private(2048)).size() == 2047)
		assert(WRSA.generate_public(WRSA.generate_private(1280)).size() == 1279)
		pk = WRSA.generate_private(1024)
		pk = WRSA.generate_public(pk)
		assert(pk is not None)
		assert(pk == WRSA.generate_public(pk))
		assert(WRSA.export_key(pk) == WRSA.export_key(WRSA.generate_public(pk)))

	def test_encrypt(self):
		pk = WRSA.generate_private(1024)
		pytest.raises(TypeError, WRSA.encrypt)
		pytest.raises(TypeError, WRSA.encrypt, b'')
		pytest.raises(TypeError, WRSA.encrypt, '', pk)

		pytest.raises(TypeError, WRSA.decrypt)
		pytest.raises(TypeError, WRSA.decrypt, b'')
		pytest.raises(TypeError, WRSA.decrypt, '', pk)

		assert(WRSA.encrypt('qwerty'.encode(), pk) != WRSA.encrypt('qwerty'.encode(), pk))
		assert(WRSA.encrypt('qwerty'.encode(), pk) != WRSA.encrypt('qwerty'.encode(), WRSA.generate_public(pk)))
		assert(WRSA.decrypt(WRSA.encrypt('qwerty'.encode(), pk), pk) == b'qwerty')
		assert(WRSA.decrypt(WRSA.encrypt('qwerty'.encode(), WRSA.generate_public(pk)), pk) == b'qwerty')

	def test_string_encrypt(self):
		pk = WRSA.generate_private(1024)
		pytest.raises(TypeError, WRSA.string_encrypt)
		pytest.raises(TypeError, WRSA.string_encrypt, '')
		pytest.raises(TypeError, WRSA.string_encrypt, b'')
		pytest.raises(TypeError, WRSA.string_encrypt, b'', pk)

		assert(WRSA.string_encrypt('qwerty', WRSA.generate_public(pk)) != WRSA.encrypt('qwerty'.encode(), pk))

		pytest.raises(TypeError, WRSA.string_decrypt)
		pytest.raises(TypeError, WRSA.string_decrypt, b'')
		pytest.raises(TypeError, WRSA.string_decrypt, '')
		pytest.raises(TypeError, WRSA.string_decrypt, '', pk)
		assert(WRSA.string_decrypt(WRSA.string_encrypt('qwerty', pk), pk) == 'qwerty')

		koi_string = WRSA.encrypt('халё'.encode('koi8-r'), pk)
		assert(WRSA.string_decrypt(koi_string, pk, text_encoding='koi8-r') == 'халё')
		pytest.raises(TypeError, WRSA.string_decrypt, koi_string, pk, text_encoding=1)
