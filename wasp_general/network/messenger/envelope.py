# -*- coding: utf-8 -*-
# wasp_general/network/messenger/envelope.py
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


# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from wasp_general.verify import verify_type

from wasp_general.network.messenger.proto import WMessengerEnvelopeProto


class WMessengerEnvelope(WMessengerEnvelopeProto):
	""" Simple :class:`.WMessengerEnvelopeProto` implementation. "Meta-dictionary" is used as is without any
	restrictions or limitations, so any further envelopes (envelopes that uses this envelope as meta) can rewrite
	or remove saved information
	"""

	@verify_type(meta=(WMessengerEnvelopeProto, dict, None))
	def __init__(self, data, meta=None):
		""" Construct new envelope

		:param data: original message
		:param meta: envelope meta-data to copy
		"""
		self.__data = data
		self.__meta = {}
		if meta is not None:
			if isinstance(meta, WMessengerEnvelopeProto) is True:
				if isinstance(meta, WMessengerEnvelope) is False:
					raise TypeError('meta must be WMessengerEnvelope (or derived classes) object')
				self.__meta = meta.meta()
			elif isinstance(meta, dict):
				self.__meta = meta.copy()

	def message(self):
		""" Return original message

		:return: any type
		"""
		return self.__data

	def meta(self):
		""" Return envelope dictionary copy

		:return: dict
		"""
		return self.__meta.copy()

	@verify_type(key=str)
	def add_meta(self, key, value):
		""" Add meta-information (value) for the given key

		:param key: meta-key
		:param value: meta-value
		:return: None
		"""
		self.__meta[key] = value


class WMessengerTextEnvelope(WMessengerEnvelope):
	""" Envelope for str-objects
	"""

	@verify_type(data=str, meta=(WMessengerEnvelopeProto, dict, None))
	def __init__(self, data, meta=None):
		WMessengerEnvelope.__init__(self, data, meta=meta)


class WMessengerBytesEnvelope(WMessengerEnvelope):
	""" Envelope for bytes-objects
	"""

	@verify_type(data=bytes, meta=(WMessengerEnvelopeProto, dict, None))
	def __init__(self, data, meta=None):
		WMessengerEnvelope.__init__(self, data, meta=meta)
