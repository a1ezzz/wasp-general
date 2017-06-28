# -*- coding: utf-8 -*-
# wasp_general/network/messenger/layers.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import abstractmethod
from enum import Enum

from wasp_general.verify import verify_type

from wasp_general.network.messenger.proto import WMessengerEnvelopeProto
from wasp_general.network.messenger.proto import WMessengerOnionSessionProto, WMessengerOnionLayerProto

from wasp_general.network.messenger.envelope import WMessengerTextEnvelope, WMessengerBytesEnvelope


class WMessengerOnionModeLayerProto(WMessengerOnionLayerProto):
	""" Simple WMessengerOnionLayerProto implementation, that can have different message processing mechanisms
	(depends on the "mode" value). This "mode" must be always specified as
	mode argument in :meth:`.WMessengerOnionModeLayerProto.process` method. This argument must be the same type
	(or be a subclass of the type), that is specified in constructor
	"""

	@verify_type(name=str, mode_cls=type)
	def __init__(self, name, mode_cls):
		""" Construct new layer

		:param name: layer name
		:param mode_cls: layer's "mode" class
		"""
		WMessengerOnionLayerProto.__init__(self, name)
		self.__mode_cls = mode_cls

	@verify_type('paranoid', envelope=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def process(self, envelope, session, mode=None, **kwargs):
		""" :meth:`.WMessengerOnionLayerProto.process` implementation
		"""
		if mode is None:
			raise RuntimeError('"mode" argument must be specified for this object')

		if isinstance(mode, self.__mode_cls) is False:
			raise TypeError('Invalid "mode" argument')

		return self._process(envelope, session, mode, **kwargs)

	@abstractmethod
	@verify_type(envelope=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def _process(self, envelope, session, mode, **kwargs):
		""" Real processing method.

		:param envelope: original envelope
		:param session:  original session
		:param mode: specified mode
		:param kwargs: layer arguments

		:return: WMessengerEnvelopeProto
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionCoderLayerProto(WMessengerOnionModeLayerProto):
	""" Class for layers, that are used for encryption/decryption, encoding/decoding. This layer class works with
	strings and bytes and as a result generates strings and bytes
	"""

	class Mode(Enum):
		""" Specifies layers mode
		"""
		encode = 1
		""" Encryption/encoding mode
		"""
		decode = 2
		""" Decryption/decoding mode
		"""

	@verify_type(name=str)
	def __init__(self, name):
		""" Construct new layer

		:param name: layer name
		"""
		WMessengerOnionModeLayerProto.__init__(self, name, WMessengerOnionCoderLayerProto.Mode)

	@verify_type('paranoid', envelope=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def _process(self, envelope, session, mode, **kwargs):
		""" :meth:`.WMessengerOnionLayerProto.process` implementation
		"""
		if mode == WMessengerOnionCoderLayerProto.Mode.encode:
			return self.encode(envelope, session, **kwargs)
		else:  # mode == WMessengerOnionCoderLayerProto.Mode.decode
			return self.decode(envelope, session, **kwargs)

	@abstractmethod
	@verify_type(envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope), session=WMessengerOnionSessionProto)
	def encode(self, envelope, session, **kwargs):
		""" Encrypt/encode message

		:param envelope: message to encrypt/encode
		:param session: original session
		:return: WMessengerTextEnvelope or WMessengerBytesEnvelope
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope), session=WMessengerOnionSessionProto)
	def decode(self, envelope, session, **kwargs):
		""" Decrypt/decode message

		:param envelope: message to decrypt/decode
		:param session: original session
		:return: WMessengerTextEnvelope or WMessengerBytesEnvelope
		"""
		raise NotImplementedError('This method is abstract')


class WMessengerOnionPackerLayerProto(WMessengerOnionModeLayerProto):
	""" Class for layers, that are used for packing/unpacking, serializing/de-serializing. This layer class
	can pack "any" envelope and produce WMessengerTextEnvelope or WMessengerBytesEnvelope or can
	unpack WMessengerTextEnvelope (or WMessengerBytesEnvelope) to "any" object

	(not "any" but the most)
	"""

	class Mode(Enum):
		""" Specifies layers mode
		"""
		pack = 1
		""" Encryption/encoding mode
		"""
		unpack = 2
		""" Decryption/decoding mode
		"""

	@verify_type(name=str)
	def __init__(self, name):
		WMessengerOnionModeLayerProto.__init__(self, name, WMessengerOnionPackerLayerProto.Mode)

	@verify_type('paranoid', envelope=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def _process(self, envelope, session, mode, **kwargs):
		""" :meth:`.WMessengerOnionLayerProto.process` implementation
		"""
		if mode == WMessengerOnionPackerLayerProto.Mode.pack:
			return self.pack(envelope, session, **kwargs)
		else:  # mode == WMessengerOnionPackerLayerProto.Mode.unpack
			return self.unpack(envelope, session, **kwargs)

	@abstractmethod
	@verify_type(envelope=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto)
	def pack(self, envelope, session, **kwargs):
		""" Pack/serialize message

		:param envelope: message to pack/serialize
		:param session: original session
		:return: WMessengerTextEnvelope or WMessengerBytesEnvelope
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope), session=WMessengerOnionSessionProto)
	def unpack(self, envelope, session, **kwargs):
		""" Unpack/de-serialize message

		:param envelope: message to unpack/de-serialize
		:param session: original session
		:return: WMessengerEnvelopeProto
		"""
		raise NotImplementedError('This method is abstract')
