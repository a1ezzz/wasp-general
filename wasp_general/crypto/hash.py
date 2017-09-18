# -*- coding: utf-8 -*-
# wasp_general/<FILENAME>.py
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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod, abstractclassmethod
from Crypto.Hash import SHA as SHA1, SHA224, SHA256, SHA384, SHA512, MD5

from wasp_general.verify import verify_type


class WHashGeneratorProto(metaclass=ABCMeta):
	""" Prototype for hash-generator.

	note: there is commonly used feature that most hash generator objects have - digest_size attribute. So it is
	better to create this attribute.
	"""

	@abstractmethod
	@verify_type(data=bytes)
	def update(self, data):
		""" Update digest by hashing the specified data

		:param data: data to hash

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def digest(self):
		""" Return current digest

		:return: bytes
		"""
		raise NotImplementedError('This method is abstract')

	def hexdigest(self):
		""" Return current digest in hex-alike string

		:return: str
		"""
		return ''.join(["{:02x}".format(x).upper() for x in self.digest()])

	@abstractclassmethod
	def generator_digest_size(cls):
		""" Return generator digest size

		:return: int
		"""
		raise NotImplementedError('This method is abstract')

	@abstractclassmethod
	def generator_name(cls):
		""" Return hash-function name

		:return: str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractclassmethod
	def generator_family(cls):
		""" Return name of hash-function family (like: 'SHA')

		:return: str or None (if no available)
		"""
		raise NotImplementedError('This method is abstract')

	@abstractclassmethod
	@verify_type(data=(bytes, None))
	def new(cls, data=None):
		""" Return new generator and hash the specified data (if defined)

		:param data: data to hash

		:return: WHashGeneratorProto
		"""
		raise NotImplementedError('This method is abstract')


class WPyCryptoHashAdapter(WHashGeneratorProto):
	""" Class that adapts the specified PyCrypto hashing class to WHashGeneratorProto implementation
	"""

	__pycrypto_cls__ = None
	""" PyCrypto class to adapt. Must be override in a derived classes
	"""

	__generator_name__ = None
	""" Hash-function name (like 'SHA1' or 'MD5'). Must be override in a derived classes
	"""

	__generator_family__ = None
	""" Hash-function family name (like: 'SHA')
	"""

	def __init__(self):
		""" Create new hash generator
		"""
		WHashGeneratorProto.__init__(self)

		if self.__class__.__pycrypto_cls__ is None:
			raise ValueError('"__pycrypto_cls__" must be override in a derived class')

		self.__pycrypto_obj = self.__class__.__pycrypto_cls__.new()
		self.digest_size = self.__class__.generator_digest_size()

	@verify_type(data=bytes)
	def update(self, data):
		""" :meth:`.WHashGeneratorProto.update` implementation
		"""
		self.__pycrypto_obj.update(data)

	def digest(self):
		""" :meth:`.WHashGeneratorProto.digest` implementation
		"""
		return self.__pycrypto_obj.digest()

	def pycrypto(self):
		""" In rare cases original PyCrypto object is required. In most cases this method should be avoided,
		as it is can be removed at any time.

		One of an example of this method usage is PyCrypto HMAC (and so :class:`.WHMAC`). They require, that
		hash-generator object must have "copy" method to be implemented. But I have not found a way to make
		HMAC work.

		:return: PyCrypto Hash object
		"""
		return self.__pycrypto_obj

	@classmethod
	def generator_digest_size(cls):
		""" :meth:`.WHashGeneratorProto.generator_digest_size` implementation
		"""
		if cls.__pycrypto_cls__ is None:
			raise ValueError('"__pycrypto_cls__" must be override in a derived class')
		return cls.__pycrypto_cls__.digest_size

	@classmethod
	def generator_name(cls):
		""" :meth:`.WHashGeneratorProto.generator_name` implementation
		"""
		if cls.__generator_name__ is None:
			raise ValueError('"__generator_name__" should be override in a derived class')
		if isinstance(cls.__generator_name__, str) is False:
			raise TypeError('"__generator_name__" should be a str instance')
		return cls.__generator_name__.upper()

	@classmethod
	def generator_family(cls):
		""" :meth:`.WHashGeneratorProto.generator_family` implementation
		"""
		if cls.__generator_family__ is not None:
			if isinstance(cls.__generator_family__, str) is False:
				raise TypeError('"__generator_class__"  if defined must be a str instance')

		if cls.__generator_family__ is not None:
			return cls.__generator_family__.upper()

	@classmethod
	@verify_type(data=(bytes, None))
	def new(cls, data=None):
		""" :meth:`.WHashGeneratorProto.new` implementation
		"""
		obj = cls()
		if data is not None:
			obj.update(data)
		return obj


class WSHAFamily(WPyCryptoHashAdapter):
	""" Class that represent SHA-family hash-generators
	"""
	__generator_family__ = 'SHA'


class WSHA1(WSHAFamily):
	""" SHA1 hash-generator
	"""
	__pycrypto_cls__ = SHA1
	__generator_name__ = 'SHA1'


class WSHA224(WSHAFamily):
	""" SHA224 hash-generator
	"""
	__pycrypto_cls__ = SHA224
	__generator_name__ = 'SHA224'


class WSHA256(WSHAFamily):
	""" SHA256 hash-generator
	"""
	__pycrypto_cls__ = SHA256
	__generator_name__ = 'SHA256'


class WSHA384(WSHAFamily):
	""" SHA384 hash-generator
	"""
	__pycrypto_cls__ = SHA384
	__generator_name__ = 'SHA384'


class WSHA512(WSHAFamily):
	""" SHA512 hash-generator
	"""
	__pycrypto_cls__ = SHA512
	__generator_name__ = 'SHA512'


class WMD5(WPyCryptoHashAdapter):
	""" MD5 hash-generator
	"""
	__pycrypto_cls__ = MD5
	__generator_name__ = 'MD5'


class WHash:
	""" Class that aggregates different hash-generators. This class is should be used if there is a need to address
	digest generator by its name. As a result - generator (:class:`.WHashGeneratorProto`) is returned.
	"""

	__hash_map__ = {x.generator_name(): x for x in (WSHA1, WSHA224, WSHA256, WSHA384, WSHA512, WMD5)}
	""" Available hash generators map 'hash function name' - :class:`.WHashGeneratorProto`
	"""

	@staticmethod
	@verify_type(name=str)
	def generator(name):
		""" Return generator by its name

		:param name: name of hash-generator

		:return: WHashGeneratorProto class
		"""
		name = name.upper()
		if name not in WHash.__hash_map__.keys():
			raise ValueError('Hash generator "%s" not available' % name)
		return WHash.__hash_map__[name]

	@staticmethod
	def generator_by_digest(family, digest_size):
		""" Return generator by hash generator family name and digest size

		:param family: name of hash-generator family

		:return: WHashGeneratorProto class
		"""
		for generator_name in WHash.available_generators(family=family):
			generator = WHash.generator(generator_name)
			if generator.generator_digest_size() == digest_size:
				return generator
		raise ValueError('Hash generator is not available')

	@staticmethod
	@verify_type(family=(str, None), name=(str, None))
	def available_generators(family=None, name=None):
		""" Return names of available generators

		:param family: name of hash-generator family to select
		:param name: name of hash-generator to select (parameter may be used for availability check)

		:return: tuple of str
		"""
		generators = WHash.__hash_map__.values()

		if family is not None:
			family = family.upper()
			generators = filter(lambda x: x.generator_family() == family, generators)

		if name is not None:
			name = name.upper()
			generators = filter(lambda x: x.generator_name() == name, generators)

		return tuple([x.generator_name() for x in generators])

	@staticmethod
	@verify_type(family=(str, None), name=(str, None))
	def available_digests(family=None, name=None):
		""" Return names of available generators

		:param family: name of hash-generator family to select
		:param name: name of hash-generator to select

		:return: set of int
		"""
		generators = WHash.available_generators(family=family, name=name)
		return set([WHash.generator(x).generator_digest_size() for x in generators])
