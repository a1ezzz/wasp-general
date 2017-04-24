# -*- coding: utf-8 -*-

import pytest

from wasp_general.config import WConfig
from wasp_general.crypto.aes import WBlockPadding, WSimplePadding, WShiftPadding, WPKCS7Padding, WAESMode, WAES
from wasp_general.crypto.aes import WFixedSecretAES, WConfigSecretAES


def test_abstract_classes():
	pytest.raises(TypeError, WBlockPadding)
	pytest.raises(NotImplementedError, WBlockPadding.pad, None, b'', 1)
	pytest.raises(NotImplementedError, WBlockPadding.reverse_pad, None, b'', 1)

	pytest.raises(TypeError, WAES)
	pytest.raises(NotImplementedError, WAES.secret, None)


class TestWSimplePadding:

	def test_padding(self):
		assert(issubclass(WSimplePadding, WBlockPadding) is True)
		assert(WSimplePadding().padding_symbol() == chr(0))
		assert(WSimplePadding(23).padding_symbol() == chr(23))

		padding = WSimplePadding(23)
		assert(padding.pad('123', 3) == (b'123'))
		assert(padding.pad(b'123', 3) == (b'123'))
		assert(padding.pad('123', 7) == (b'123' + (chr(23) * 4).encode()))
		assert(padding.reverse_pad((b'123' + (chr(23) * 4).encode()), 7) == b'123')


class TestWShiftPadding:

	def test_padding(self):
		assert(issubclass(WShiftPadding, WSimplePadding) is True)

		padding = WShiftPadding(21)
		assert(padding.pad(b'123', 4) in [b'\x15123', b'123\x15'])
		assert(padding.reverse_pad(b'\x15123', 4) == b'123')
		assert(padding.reverse_pad(b'123\x15', 4) == b'123')


class TestWPKCS7Padding:

	def test_padding(self):
		assert(issubclass(WPKCS7Padding, WBlockPadding) is True)

		padding = WPKCS7Padding()
		assert(padding.pad('123', 5) == b'123\x02\x02')
		assert(padding.pad(b'123', 6) == b'123\x03\x03\x03')

		assert(padding.reverse_pad(b'123\x02\x02', 5) == b'123')
		assert(padding.reverse_pad(b'123\x03\x03\x03', 6) == b'123')

		pytest.raises(ValueError, padding.reverse_pad, b'123\x10', 4)
		pytest.raises(ValueError, padding.reverse_pad, b'123\x02', 4)


class TestWAESMode:

	def test_mode(self):

		pytest.raises(ValueError, WAESMode, 16, 'AES-CBC', padding=WPKCS7Padding())
		pytest.raises(ValueError, WAESMode, 16, 'AES-CBC', init_vector=(b'0' * 16))
		pytest.raises(ValueError, WAESMode, 16, 'AES-CTR')

		padding = WPKCS7Padding()
		cbc_mode = WAESMode(16, 'AES-CBC', padding=padding, init_vector=(b'0' * 16))
		assert(cbc_mode.key_size() == 16)
		assert(cbc_mode.mode() == 'AES-CBC')
		assert(cbc_mode.padding() == padding)
		assert(isinstance(cbc_mode.pyaes_args(), tuple) is True)
		assert(isinstance(cbc_mode.pyaes_kwargs(), dict) is True)

		ctr_mode = WAESMode(24, 'AES-CTR', init_counter_value=0)
		assert(ctr_mode.key_size() == 24)
		assert(ctr_mode.mode() == 'AES-CTR')
		assert(ctr_mode.padding() is None)

		ctr_mode = WAESMode(24, 'AES-CTR', padding=padding, init_counter_value=0)
		assert(ctr_mode.key_size() == 24)
		assert(ctr_mode.mode() == 'AES-CTR')
		assert(ctr_mode.padding() == padding)

		default_mode = WAESMode.defaults()
		assert(default_mode.key_size() == 32)
		assert(default_mode.mode() == 'AES-CBC')
		assert(isinstance(default_mode.padding(), WPKCS7Padding) is True)

		default_mode = WAESMode.defaults(block_cipher_mode='AES-CTR')
		assert(default_mode.key_size() == 32)
		assert(default_mode.mode() == 'AES-CTR')
		assert(default_mode.padding() is None)


class TestWAES:

	class SimpleAES(WAES):

		def secret(self):
			return b'0123456789abcdef' * 2

	def test_cipher(self):
		cbc_mode = WAESMode.defaults()

		a1 = TestWAES.SimpleAES(cbc_mode)
		a2 = TestWAES.SimpleAES(cbc_mode)

		a2.secret = lambda: '1111'
		pytest.raises(TypeError, a2.cipher)
		a2.secret = lambda: b'1111'
		pytest.raises(ValueError, a2.cipher)
		a2.secret = lambda: b'fedcba9876543210' * 2

		text_block = 'q' * a1.mode().key_size()

		c1 = a1.cipher()
		c2 = a2.cipher()
		assert(c1.encrypt(text_block) != text_block.encode())

		c1 = a1.cipher()
		c2 = a2.cipher()
		assert(c1.encrypt(text_block) != c2.encrypt(text_block))

		c1 = a1.cipher()
		c2 = a1.cipher()
		assert(c1.decrypt(c1.encrypt(text_block)) != text_block.encode())

		c1 = a1.cipher()
		c2 = a1.cipher()
		assert(c2.decrypt(c1.encrypt(text_block)) == text_block.encode())

		c1 = a1.cipher()
		c2 = a2.cipher()
		assert(c2.decrypt(c1.encrypt(text_block)) != text_block.encode())

		text_block = 'qwerty'
		assert(a1.encrypt(text_block) == a1.encrypt(text_block))
		assert(a1.encrypt(text_block) != text_block)
		assert(a1.decrypt(a1.encrypt(text_block)) == text_block)

		cbc_mode = WAESMode.defaults(padding=WSimplePadding())
		a1 = TestWAES.SimpleAES(cbc_mode)
		invalid_data = a1.decrypt(b'1' * 16, False)
		assert(type(invalid_data) == bytes)
		assert(len(invalid_data) == 16)
		assert(invalid_data != b'1' * 16)


class TestWFixedSecretAES:

	def test_cipher(self):

		cbc_mode = WAESMode.defaults()
		assert(isinstance(WFixedSecretAES('foo', cbc_mode), WFixedSecretAES) is True)
		assert(isinstance(WFixedSecretAES('bar', cbc_mode), WAES) is True)
		assert(WFixedSecretAES('foo', cbc_mode).secret() == (b'foo' + (b'\x1d' * (32 - 3))))
		assert(WFixedSecretAES(b'bar', cbc_mode).secret() == (b'bar' + (b'\x1d' * (32 - 3))))
		assert(WFixedSecretAES(b'1' * 36, cbc_mode).secret() == (b'1' * 32))

		aes_cbc = WFixedSecretAES(b'pass', cbc_mode)
		assert(aes_cbc.decrypt(aes_cbc.encrypt('secret_data')) == 'secret_data')

		ctr_mode = WAESMode.defaults(block_cipher_mode='AES-CTR')
		pytest.raises(ValueError, WFixedSecretAES, b'pass', ctr_mode)

		ctr_mode_encrypt = WAESMode.defaults(block_cipher_mode='AES-CTR', padding=WSimplePadding())
		ctr_mode_decrypt = WAESMode.defaults(block_cipher_mode='AES-CTR', padding=WSimplePadding())
		aes_ctr_encrypt = WFixedSecretAES(b'pass', ctr_mode_encrypt)
		aes_ctr_decrypt = WFixedSecretAES(b'pass', ctr_mode_decrypt)
		encrypted_data = aes_ctr_encrypt.encrypt('secret_data')
		assert(aes_ctr_decrypt.decrypt(encrypted_data) == 'secret_data')


class TestWConfigSecretAES:

	def test_cipher(self):
		cbc_mode = WAESMode.defaults()
		config = WConfig()
		config.add_section('aes-section')
		config['aes-section']['secret'] = 'foo'

		aes_cbc = WConfigSecretAES(config, 'foo', 'bar', cbc_mode)
		assert(isinstance(aes_cbc, WAES) is True)

		pytest.raises(KeyError, aes_cbc.secret)
		aes_cbc = WConfigSecretAES(config, 'aes-section', 'secret', cbc_mode)
		assert(aes_cbc.secret() == (b'foo' + b'\x1d' * 29))
		config['aes-section']['secret'] = 'bar'
		assert(aes_cbc.secret() == (b'bar' + b'\x1d' * 29))
		config['aes-section']['secret'] = ('3' * 36)
		assert(aes_cbc.secret() == (b'3' * 32))
		assert(aes_cbc.decrypt(aes_cbc.encrypt('secret_data')) == 'secret_data')
		config['aes-section']['secret'] = 'pass'

		ctr_mode = WAESMode.defaults(block_cipher_mode='AES-CTR')
		aes_ctr = WConfigSecretAES(config, 'aes-section', 'secret', ctr_mode)
		pytest.raises(ValueError, aes_ctr.secret)

		ctr_mode_encrypt = WAESMode.defaults(block_cipher_mode='AES-CTR', padding=WSimplePadding())
		ctr_mode_decrypt = WAESMode.defaults(block_cipher_mode='AES-CTR', padding=WSimplePadding())
		aes_ctr_encrypt = WConfigSecretAES(config, 'aes-section', 'secret', ctr_mode_encrypt)
		aes_ctr_decrypt = WConfigSecretAES(config, 'aes-section', 'secret', ctr_mode_decrypt)
		encrypted_data = aes_ctr_encrypt.encrypt('secret_data')
		assert(aes_ctr_decrypt.decrypt(encrypted_data) == 'secret_data')
