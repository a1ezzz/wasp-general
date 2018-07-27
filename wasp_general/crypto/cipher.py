# -*- coding: utf-8 -*-
# wasp_general/<FILENAME>.py
#
# Copyright (C) 2018 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import abstractmethod, ABCMeta

from wasp_general.verify import verify_type


class WCipherProto(metaclass=ABCMeta):
	""" This class is a generalization of ciphers (now it is AES cipher only)
	"""

	@abstractmethod
	def block_size(self):
		""" Return a size of a block that may be encrypted or decrypted.

		:return: int (in bytes) or None if cipher is able to encrypt/decrypt block with any length
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(data=bytes)
	def encrypt_block(self, data):
		""" Encrypt the given data

		:param data: data to encrypt. The size of the data must be multiple of :meth:`.WCipherProto.block_size`

		:return: bytes
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(data=bytes)
	def decrypt_block(self, data):
		""" Decrypt the given data

		:param data: data to decrypt. The size of the data must be multiple of :meth:`.WCipherProto.block_size`

		:return: bytes
		"""
		raise NotImplementedError('This method is abstract')
