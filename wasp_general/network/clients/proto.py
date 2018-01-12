# -*- coding: utf-8 -*-
# wasp_general/network/clients/proto.py
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

from abc import ABCMeta, abstractmethod, abstractclassmethod

from wasp_general.verify import verify_type
from wasp_general.uri import WURI


class WNetworkClientCapabilityProto(metaclass=ABCMeta):

	@abstractmethod
	def capability_id(self):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def request(self, *args, **kwargs):
		"""

		:param args:
		:param kwargs:
		:return: anything
		"""
		raise NotImplementedError('This method is abstract')


class WNetworkClientProto(metaclass=ABCMeta):

	class ConnectionError(Exception):
		pass

	@abstractclassmethod
	def is_capable(cls, capability_id):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def request(self, capability_id, *args, **kwargs):
		"""

		:param capability_id:
		:param args:
		:param kwargs:
		:return: anything
		"""
		raise NotImplementedError('This method is abstract')

	@abstractclassmethod
	def scheme(cls):
		raise NotImplementedError('This method is abstract')

	@abstractclassmethod
	@verify_type(uri=WURI)
	def open(cls, uri):
		"""

		:param uri:

		:return: WNetworkClientProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def close(self):
		raise NotImplementedError('This method is abstract')
