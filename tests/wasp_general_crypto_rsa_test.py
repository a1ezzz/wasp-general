# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.rsa import WRSA


class TestWRSA:

	def test(self):

		print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
		import cryptography.hazmat.backends.openssl
		import os
		with open(os.path.join(os.path.dirname(cryptography.hazmat.backends.openssl.__file__), 'backend.py'), 'r') as f:
			print(f.read())
		print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

		rsa = WRSA()
		assert(rsa.has_private_key() is False)
		assert(rsa.has_public_key() is False)
		pytest.raises(ValueError, rsa.private_key_size)
		pytest.raises(ValueError, rsa.export_private_key)
		pytest.raises(ValueError, rsa.export_public_key)
		pytest.raises(ValueError, rsa.encrypt, b'')
		pytest.raises(ValueError, rsa.decrypt, b'')

		rsa.generate_private_key()
		assert(rsa.has_private_key() is True)
		assert(rsa.has_public_key() is True)
		assert(rsa.private_key_size() == 2048)
		rsa.generate_private_key(4096)
		assert(rsa.private_key_size() == 4096)
		rsa.generate_private_key(1024)
		assert(rsa.private_key_size() == 1024)

		rsa.generate_private_key()
		private_key_pem_var1 = rsa.export_private_key()
		encrypted_private_key_pem_var2 = rsa.export_private_key(b'secret')
		encrypted_private_key_pem_var3 = rsa.export_private_key('secret')
		public_key_pem = rsa.export_public_key()

		data = b'data to encrypt'
		rsa = WRSA()
		rsa.import_public_key(public_key_pem)
		assert(rsa.has_private_key() is False)
		assert(rsa.has_public_key() is True)
		encrypted_data = rsa.encrypt(data)

		rsa = WRSA()
		rsa.import_private_key(private_key_pem_var1)
		assert(rsa.has_private_key() is True)
		assert(rsa.has_public_key() is True)
		assert(rsa.decrypt(encrypted_data) == data)

		rsa = WRSA()
		pytest.raises(TypeError, rsa.import_private_key, encrypted_private_key_pem_var2)
		rsa.import_private_key(encrypted_private_key_pem_var2, 'secret')
		assert(rsa.decrypt(encrypted_data) == data)

		rsa = WRSA()
		pytest.raises(TypeError, rsa.import_private_key, encrypted_private_key_pem_var3)
		rsa.import_private_key(encrypted_private_key_pem_var3, b'secret')
		assert(rsa.decrypt(encrypted_data) == data)

		rsa.import_public_key(public_key_pem.decode())
		encrypted_data = rsa.encrypt(data)
		rsa.import_private_key(private_key_pem_var1.decode())
		assert(rsa.decrypt(encrypted_data) == data)
