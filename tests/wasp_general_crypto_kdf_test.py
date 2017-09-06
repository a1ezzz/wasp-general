# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.kdf import WPBKDF2
from wasp_general.crypto.hmac import WHMAC


class TestWPBKDF2:

	def test(self):
		kdf = WPBKDF2(b'very-very-very much secret key')
		assert(kdf.salt() is not None)
		assert(len(kdf.derived_key()) == WPBKDF2.__default_derived_key_length__)

		kdf = WPBKDF2(
			'very-very-very strong password', salt=b'public salt value', derived_key_length=20, iterations_count=2000,
			hmac=WHMAC.hmac('HMAC-SHA256')
		)
		assert(kdf.derived_key() == b'\xfaup\xf6\x04\xaf\xb1z\xbc*\xa5\xafy\n\xb01\x06\xb5\x0b\x94')
