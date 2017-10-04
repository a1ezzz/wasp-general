# -*- coding: utf-8 -*-

import pytest
import io

from wasp_general.crypto.aes import WAESMode, WAES, WZeroPadding
from wasp_general.io import WAESWriter


class TestWAESWriter:

	def test(self):
		bytes_io = io.BytesIO()
		bytes_io.close = lambda: None  # do not really close the buffer

		secret_key = b'\x01\x01\x01\x01\x02\x02\x02\x02\x03\x03\x03\x03\x04\x04\x04\x04'
		iv = b'\x05\x05\x05\x05\x06\x06\x06\x06\x07\x07\x07\x07\x08\x08\x08\x08'
		aes_mode = WAESMode(16, 'AES-CBC', secret_key + iv)
		pytest.raises(ValueError, WAESWriter, bytes_io, WAES(aes_mode))

		aes_mode = WAESMode(16, 'AES-CBC', secret_key + iv, padding=WZeroPadding())
		aes = WAES(aes_mode)

		wr = WAESWriter(bytes_io, aes)
		assert(wr.write(b'bla-bla-bla long-long-long data very long data \x11\x11\x11\x11!!!') == 54)
		wr.close()
		bytes_io.seek(0)
		result = b'[C\xf0-\x9c\x98\x07-q\xc2?\xd8\xdeXLsn\x9cz\x00;\xa6b\x9b&_,\xfd\x91\xbe'
		result += b'\x03{\x91r(\xb0\xe7:\x81X\xf4\xe8(\x84\x9aM\x10\xc5\xf4\x01\xa9G\'\x04;`\r2\x17\x11'
		result += b'\x1b\xaf\xb4\x83'
		assert(bytes_io.read() == result)
		io.BytesIO.close(bytes_io)

		bytes_io = io.BytesIO()
		bytes_io.close = lambda: None  # do not really close the buffer
		wr = WAESWriter(bytes_io, aes)
		assert(wr.write(b'bla-bla-bla') == 11)
		wr.close()

		bytes_io.seek(0)

		result = b'\'\x16\x02\xd8\xd9\x19\x06\xaf/\x18]r\xed\x8f8\xe2'
		assert(bytes_io.read() == result)
		assert(aes.decrypt(result) == b'bla-bla-bla')

		aes_mode = WAESMode(16, 'AES-CBC', secret_key + iv)
		aes = WAES(aes_mode)
		assert(aes.decrypt(result) == b'bla-bla-bla\x00\x00\x00\x00\x00')

		io.BytesIO.close(bytes_io)
