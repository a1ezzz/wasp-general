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


class WHashIO:

	def __init__(self, hash_name):
		self.__hash_name = hash_name
		self.__hash_obj = WHash.generator(hash_name).new(b'')

	@verify_type(b=bytes)
	def update_hash(self, b):
		self.__hash_obj.update(b)

	def hash_name(self):
		return self.__hash_name

	def hexdigest(self):
		return self.__hash_obj.hexdigest()


class WResponsiveIO:

	class IOTerminated(Exception):
		pass

	def __init__(self, stop_event):
		self.__stop_event = stop_event

	def stop_event(self):
		return self.__stop_event


class WIOChainLink:

	def __init__(self, io_cls, *args, **kwargs):
		self.__io_cls = io_cls
		self.__args = args
		self.__kwargs = kwargs

	def io_cls(self):
		return self.__io_cls

	def io_obj(self, raw):
		return self.io_cls()(raw, *self.__args, **self.__kwargs)


class WIOChain:

	@verify_type(links=WIOChainLink)
	def __init__(self, last_io_obj, *links):
		self.__chain = [last_io_obj]

		for link in links:
			next_io_obj = link.io_obj(last_io_obj)
			self.__chain.append(next_io_obj)
			last_io_obj = next_io_obj

	def first_io(self):
		return self.__chain[-1]

	def instance(self, io_cls):
		for io_obj in self:
			if isinstance(io_obj, io_cls) is True:
				return io_obj

	def __iter__(self):
		chain = self.__chain.copy()
		chain.reverse()
		for io_obj in chain:
			yield io_obj


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


class WHashCalculationWriter(io.BufferedWriter, WHashIO):

	@verify_type(hash_name=str)
	def __init__(self, raw, hash_name):
		io.BufferedWriter.__init__(self, raw)
		WHashIO.__init__(self, hash_name)

	@verify_type('paranoid', b=(bytes, memoryview))
	def write(self, b):
		self.update_hash(bytes(b))
		io.BufferedWriter.write(self, b)
		return len(b)


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


class WResponsiveWriter(io.BufferedWriter, WResponsiveIO):

	def __init__(self, raw, stop_event):
		io.BufferedWriter.__init__(self, raw)
		WResponsiveIO.__init__(self, stop_event)

	@verify_type(b=(bytes, memoryview))
	def write(self, b):
		if self.stop_event().is_set():
			raise WResponsiveIO.IOTerminated('Stop event was set')
		io.BufferedWriter.write(self, b)
		return len(b)


class WWriterChainLink(WIOChainLink):

	@verify_subclass(writer_cls=io.BufferedWriter)
	def __init__(self, writer_cls, *args, **kwargs):
		WIOChainLink.__init__(self, writer_cls, *args, **kwargs)


class WWriterChain(WIOChain, io.BufferedWriter):

	@verify_type(links=WWriterChainLink)
	def __init__(self, last_io_obj, *links):
		WIOChain.__init__(self, last_io_obj, *links)
		io.BufferedWriter.__init__(self, self.first_io())

	def flush(self):
		io.BufferedWriter.flush(self)
		for link in self:
			link.flush()

	def close(self):
		io.BufferedWriter.close(self)
		for link in self:
			link.close()


class WBufferedIOReader(io.BufferedReader):

	def __init__(self, raw):
		io.BufferedReader.__init__(self, raw)

	def writable(self, *args, **kwargs):
		return False

	def read(self, size=-1):
		if size == 0:
			return self.read_chunk(size)

		result = b''
		chunk_size = io.DEFAULT_BUFFER_SIZE
		read_chunk = True
		while read_chunk is True:
			next_chunk = self.read_chunk(chunk_size)

			if size > 0:
				if chunk_size >= size:
					read_chunk = False
				size -= chunk_size
			elif next_chunk == b'':
				read_chunk = False

			result += next_chunk

		return result

	def read_chunk(self, size):
		return self.raw.read(size)


class WHashCalculationReader(WBufferedIOReader, WHashIO):

	@verify_type(hash_name=str)
	def __init__(self, raw, hash_name):
		WBufferedIOReader.__init__(self, raw)
		WHashIO.__init__(self, hash_name)

	def read_chunk(self, size):
		result = WBufferedIOReader.read_chunk(self, size)
		self.update_hash(result)
		return result


class WResponsiveReader(WBufferedIOReader, WResponsiveIO):

	def __init__(self, raw, stop_event):
		WBufferedIOReader.__init__(self, raw)
		WResponsiveIO.__init__(self, stop_event)

	def read_chunk(self, size):
		if self.stop_event().is_set():
			raise WResponsiveIO.IOTerminated('Stop event was set')
		return WBufferedIOReader.read_chunk(self, size)


class WReaderChainLink(WIOChainLink):

	@verify_subclass(reader_cls=io.BufferedReader)
	def __init__(self, reader_cls, *args, **kwargs):
		WIOChainLink.__init__(self, reader_cls, *args, **kwargs)


class WReaderChain(WIOChain, io.BufferedReader):

	@verify_type(links=WReaderChainLink)
	def __init__(self, last_io_obj, *links):
		WIOChain.__init__(self, last_io_obj, *links)
		io.BufferedReader.__init__(self, self.first_io())

	def close(self):
		io.BufferedReader.close(self)
		for link in self:
			link.close()
