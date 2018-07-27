# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.cipher import WCipherProto


def test_abstract():
	pytest.raises(TypeError, WCipherProto)
	pytest.raises(NotImplementedError, WCipherProto.block_size, None)
	pytest.raises(NotImplementedError, WCipherProto.encrypt_block, None, b'')
	pytest.raises(NotImplementedError, WCipherProto.decrypt_block, None, b'')
