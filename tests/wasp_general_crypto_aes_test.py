# -*- coding: utf-8 -*-

import pytest
import io

from wasp_general.crypto.aes import WBlockPadding, WSimplePadding, WZeroPadding, WShiftPadding, WPKCS7Padding, WAESMode
from wasp_general.crypto.aes import WAES


def test_abstract_classes():
	pytest.raises(TypeError, WBlockPadding)
	pytest.raises(NotImplementedError, WBlockPadding.pad, None, b'', 1)
	pytest.raises(NotImplementedError, WBlockPadding.reverse_pad, None, b'', 1)


class TestWSimplePadding:

	def test_padding(self):
		assert(issubclass(WSimplePadding, WBlockPadding) is True)
		assert(WSimplePadding().padding_symbol() == b'\x00')
		assert(WSimplePadding(23).padding_symbol() == b'\x17')

		padding = WSimplePadding(23)
		assert(padding.pad(b'123', 3) == b'123')
		assert(padding.pad(b'123', 7) == b'123\x17\x17\x17\x17')
		assert(padding.reverse_pad((b'123' + (chr(23) * 4).encode()), 7) == b'123')


class TestWZeroPadding:

	def test(self):
		padding = WZeroPadding()
		assert(isinstance(padding, WZeroPadding) is True)
		assert(isinstance(padding, WSimplePadding) is True)
		assert(padding.padding_symbol() == b'\x00')


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
		assert(padding.pad(b'123', 6) == b'123\x03\x03\x03')

		assert(padding.reverse_pad(b'123\x02\x02', 5) == b'123')
		assert(padding.reverse_pad(b'123\x03\x03\x03', 6) == b'123')

		pytest.raises(ValueError, padding.reverse_pad, b'123\x10', 4)
		pytest.raises(ValueError, padding.reverse_pad, b'123\x02', 4)


class TestWAESMode:

	def test_mode(self):

		pytest.raises(ValueError, WAESMode, 16, 'AES-CBC', b'', padding=WPKCS7Padding())

		assert(WAESMode.init_sequence_length(16, 'AES-CBC') == 32)
		assert(WAESMode.init_sequence_length(24, 'AES-CTR') == 40)

		assert(WAESMode.parse_cipher_name('aes-256-cbc') == (32, 'AES-CBC'))
		assert(WAESMode.parse_cipher_name('AES_128_CTR') == (16, 'AES-CTR'))
		pytest.raises(ValueError, WAESMode.parse_cipher_name, '????')
		pytest.raises(ValueError, WAESMode.parse_cipher_name, 'AES-32-cbc')
		pytest.raises(ValueError, WAESMode.parse_cipher_name, 'AES-128-cbc2')

		init_seq_key = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
		init_seq_iv = b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
		padding = WPKCS7Padding()

		cbc_mode = WAESMode(16, 'AES-CBC', init_seq_key + init_seq_iv, padding=padding)
		assert(cbc_mode.key_size() == 16)
		assert(cbc_mode.mode() == 'AES-CBC')
		assert(cbc_mode.padding() == padding)
		assert(cbc_mode.initialization_vector() == init_seq_iv)

		assert(isinstance(cbc_mode.pyaes_args(), tuple) is True)
		assert(isinstance(cbc_mode.pyaes_kwargs(), dict) is True)

		init_seq_key = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
		init_seq_key += b'\x10\x11\x12\x13\x14\x15\x16\x17'
		init_seq_counter = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07'

		ctr_mode = WAESMode(24, 'AES-CTR', init_seq_key + init_seq_counter)
		assert(ctr_mode.key_size() == 24)
		assert(ctr_mode.mode() == 'AES-CTR')
		assert(ctr_mode.padding() is None)
		assert (ctr_mode.initialization_counter_value() == 7)


@pytest.fixture
def fake_aes_mode(request):
	modes = WAESMode.__modes_descriptor__.copy()
	WAESMode.__modes_descriptor__['TEST-AES-MODE'] = {
		'mode_code': None,
		'requirements': {
			'initialization_vector': True,
			'counter': True
		}
	}

	def fin():
		WAESMode.__modes_descriptor__ = modes
	request.addfinalizer(fin)


class TestWAES:

	def test_cipher(self):

		init_seq_key1 = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
		init_seq_iv = b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
		padding = WPKCS7Padding()

		cbc_mode1 = WAESMode(16, 'AES-CBC', init_seq_key1 + init_seq_iv, padding=padding)

		init_seq_key2 = b'\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f'
		cbc_mode2 = WAESMode(16, 'AES-CBC', init_seq_key2 + init_seq_iv, padding=padding)

		a1 = WAES(cbc_mode1)
		a2 = WAES(cbc_mode2)

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

		text_block = b'qwerty'
		assert(a1.encrypt(text_block) == a1.encrypt(text_block))
		assert(a1.encrypt(text_block) != text_block)
		assert(a1.decrypt(a1.encrypt(text_block)) == text_block)
		assert(a1.decrypt(a1.encrypt(text_block), decode=True) == text_block.decode())

	@pytest.mark.usefixtures('fake_aes_mode')
	def test_fake_mode(self):
		init_seq_key = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
		init_seq_iv = b'\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
		init_seq_counter = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08'

		fake_mode = WAESMode(16, 'TEST-AES-MODE', init_seq_key + init_seq_iv + init_seq_counter)
		assert(fake_mode.initialization_vector() == init_seq_iv)
		assert(fake_mode.initialization_counter_value() == 8)
