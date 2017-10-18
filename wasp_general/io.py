# -*- coding: utf-8 -*-
# wasp_general/io.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# Wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import io
import time

from wasp_general.verify import verify_type, verify_subclass, verify_value
from wasp_general.crypto.aes import WAES
from wasp_general.crypto.hash import WHash


class WAESWriter(io.BufferedWriter):
	""" File-like writer with transparent encryption
	"""

	@verify_type(cipher=WAES)
	def __init__(self, raw, cipher):
		""" Create new encryption writer

		:param cipher: cipher to use. As written data size may differ - cipher must be constructed with
		padding object
		:param raw: target file-like object to write to
		"""
		io.BufferedWriter.__init__(self, raw)

		self.__cipher_padding = cipher.mode().padding()
		if self.__cipher_padding is None:
			raise ValueError('AES cipher must be created with "padding" option')

		self.__cipher = cipher.cipher()
		self.__cipher_block_size = cipher.mode().key_size()
		self.__buffer = b''

	@verify_type(b=(bytes, memoryview))
	def write(self, b):
		""" Encrypt and write data

		:param b: data to encrypt and write

		:return: None
		"""
		self.__buffer += bytes(b)
		bytes_written = 0
		while len(self.__buffer) >= self.__cipher_block_size:
			io.BufferedWriter.write(self, self.__cipher.encrypt(self.__buffer[:self.__cipher_block_size]))
			self.__buffer = self.__buffer[self.__cipher_block_size:]
			bytes_written += self.__cipher_block_size
		return len(b)

	def flush(self):
		if len(self.__buffer) > 0:
			data = self.__cipher_padding.pad(self.__buffer, self.__cipher_block_size)
			encrypted_data = self.__cipher.encrypt(data)
			io.BufferedWriter.write(self, encrypted_data)
		self.__buffer = b''
		io.BufferedWriter.flush(self)


class WHashCalculationWriter(io.BufferedWriter):

	@verify_type(hash_name=str)
	def __init__(self, raw, hash_name):
		io.BufferedWriter.__init__(self, raw)
		self.__hash_name = hash_name
		self.__hash_obj = WHash.generator(hash_name).new(b'')

	@verify_type(b=(bytes, memoryview))
	def write(self, b):
		self.__hash_obj.update(bytes(b))
		io.BufferedWriter.write(self, b)
		return len(b)

	def hash_name(self):
		return self.__hash_name

	def hexdigest(self):
		return self.__hash_obj.hexdigest()


class WThrottlingWriter(io.BufferedWriter):

	__default_maximum_timeout__ = 1.5

	@verify_type(write_limit=(int, float, None), maximum_timeout=(int, float, None))
	@verify_value(maximum_timeout=lambda x: x is None or x > 0)
	def __init__(self, raw, write_limit=None, maximum_timeout=None):
		io.BufferedWriter.__init__(self, raw)
		self.__write_limit = write_limit
		self.__maximum_timeout = \
			maximum_timeout if maximum_timeout is not None else self.__default_maximum_timeout__

		self.__started_at = time.time()
		self.__finished_at = None
		self.__bytes_processed = 0

	def write_limit(self):
		return self.__write_limit

	@verify_type(b=(bytes, memoryview))
	def write(self, b):
		if self.__write_limit is not None:
			current_rate = self.write_rate()
			if current_rate > self.__write_limit:
				rate_delta = current_rate - self.__write_limit
				sleep_time = self.__bytes_processed / rate_delta
				time.sleep(min(sleep_time, self.__maximum_timeout))

		io.BufferedWriter.write(self, b)
		b_l = len(b)
		self.__bytes_processed += b_l
		return b_l

	def close(self, *args, **kwargs):
		self.__finished_at = time.time()
		io.BufferedWriter.close(self, *args, **kwargs)

	def write_rate(self):
		finished_at = self.__finished_at if self.__finished_at is not None else time.time()
		return self.__bytes_processed / (finished_at - self.__started_at)


class WResponsiveWriter(io.BufferedWriter):

	class WriterTerminated(Exception):
		pass

	def __init__(self, raw, stop_event):
		io.BufferedWriter.__init__(self, raw)
		self.__event = stop_event

	@verify_type(b=(bytes, memoryview))
	def write(self, b):
		if self.__event.is_set():
			raise WResponsiveWriter.WriterTerminated('Stop event was set')
		io.BufferedWriter.write(self, b)
		return len(b)


class WWriterChainLink:

	@verify_subclass(writer_cls=io.BufferedWriter)
	def __init__(self, writer_cls, *args, **kwargs):
		self.__writer_cls = writer_cls
		self.__args = args
		self.__kwargs = kwargs

	def writer(self, raw):
		return self.__writer_cls(raw, *self.__args, **self.__kwargs)


class WWriterChain(io.BufferedWriter):

	@verify_type(links=WWriterChainLink)
	def __init__(self, last_link, *links):
		self.__chain = [last_link]

		for link in links:
			next_link = link.writer(last_link)
			self.__chain.append(next_link)
			last_link = next_link

		io.BufferedWriter.__init__(self, self.__chain[-1])

	def __iter__(self):
		chain = self.__chain.copy()
		chain.reverse()
		for link in chain:
			yield link

	def flush(self):
		io.BufferedWriter.flush(self)
		for link in self:
			link.flush()

	def close(self):
		io.BufferedWriter.close(self)
		for link in self:
			link.close()
