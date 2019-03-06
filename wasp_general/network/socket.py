# -*- coding: utf-8 -*-
# wasp_general/network/socket.py
#
# Copyright (C) 2019 the wasp-general authors and contributors
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

from abc import abstractmethod

import socket

from wasp_general.verify import verify_subclass

from wasp_general.uri import WSchemeHandler, WSchemeSpecification, WURIComponentVerifier, WURI, WURIQueryVerifier
from wasp_general.uri import WStrictURIQuery, WSchemeCollection

from wasp_general.network.primitives import WIPV4Address, WNetworkIPV4


class WSocketHandlerProto(WSchemeHandler):
	""" Represent class that is able to create and set up socket object
	"""

	@abstractmethod
	def uri(self):
		""" Return origin URI from which socket was created

		:rtype: WURI
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def socket(self):
		""" Return created socket

		:rtype: socket.socket
		"""
		raise NotImplementedError('This method is abstract')


class WUDPSocketHandler(WSocketHandlerProto):
	""" :class:`.WSocketHandlerProto` implementation with which UDP socket may be created
	"""

	__multicast_options_spec__ = WStrictURIQuery.ParameterSpecification(
		'multicast', nullable=True, multiple=False, optional=True
	)
	""" With this option it is possible to check that a target URI has a valid multicast address
	"""

	def __init__(self, uri):
		""" Create new object (and UDP socket object also) from specification defined by an URI

		:param uri: socket specification
		:type uri: WURI
		"""
		WSocketHandlerProto.__init__(self)
		self.__uri = uri

		address = self.__uri.hostname()
		uri_query = uri.query()
		if uri_query is not None:
			uri_query = WStrictURIQuery.parse(uri_query)
			socket_opts = WStrictURIQuery(uri_query, self.__multicast_options_spec__, extra_parameters=False)

			if 'multicast' in socket_opts:
				address = socket.gethostbyname(address)
				ipv4_address = WIPV4Address(address)
				if WNetworkIPV4.is_multicast(ipv4_address) is False:
					raise ValueError(
						'The specified address: "%s" is not a multicast address' %
						str(ipv4_address)
					)
		self.__socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

	def uri(self):
		""" :meth:`.WSocketHandlerProto.uri` implementation

		:rtype: WURI
		"""
		return self.__uri

	def socket(self):
		""" :meth:`.WSocketHandlerProto.socket` implementation

		:rtype: socket.socket
		"""
		return self.__socket

	@classmethod
	def create_handler(cls, uri, **kwargs):
		""" :meth:`.WSchemeHandler.create_handler` implementation

		:type uri: WURI
		:rtype: WSocketHandlerProto
		"""
		return cls(uri)

	@classmethod
	def scheme_specification(cls):
		""" :meth:`.WSchemeHandler.scheme_specification` implementation

		:rtype: WSchemeSpecification
		"""
		return WSchemeSpecification(
			'udp',
			WURIComponentVerifier(WURI.Component.hostname, WURIComponentVerifier.Requirement.required),
			WURIComponentVerifier(WURI.Component.port, WURIComponentVerifier.Requirement.required),
			WURIQueryVerifier(
				WURIComponentVerifier.Requirement.optional,
				cls.__multicast_options_spec__,
				extra_parameters=False
			)
		)


class WTCPSocketHandler(WSocketHandlerProto):
	""" :class:`.WSocketHandlerProto` implementation with which TCP socket may be created
	"""

	def __init__(self, uri):
		""" Create new object (and TCP socket object also) from specification defined by an URI

		:param uri: socket specification
		:type uri: WURI
		"""
		WSocketHandlerProto.__init__(self)
		self.__uri = uri
		self.__socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

	def uri(self):
		""" :meth:`.WSocketHandlerProto.uri` implementation

		:rtype: WURI
		"""
		return self.__uri

	def socket(self):
		""" :meth:`.WSocketHandlerProto.socket` implementation

		:rtype: socket.socket
		"""
		return self.__socket

	@classmethod
	def create_handler(cls, uri, **kwargs):
		""" :meth:`.WSchemeHandler.create_handler` implementation

		:type uri: WURI
		:rtype: WSocketHandlerProto
		"""
		return cls(uri)

	@classmethod
	def scheme_specification(cls):
		""" :meth:`.WSchemeHandler.scheme_specification` implementation

		:rtype: WSchemeSpecification
		"""
		return WSchemeSpecification(
			'tcp',
			WURIComponentVerifier(WURI.Component.hostname, WURIComponentVerifier.Requirement.required),
			WURIComponentVerifier(WURI.Component.port, WURIComponentVerifier.Requirement.required)
		)


class WUnixSocketHandler(WSocketHandlerProto):
	""" :class:`.WSocketHandlerProto` implementation with which Unix socket may be created
	"""

	__type_options_spec__ = WStrictURIQuery.ParameterSpecification(
		'type', nullable=False, multiple=False, optional=True, reg_exp='stream|datagram'
	)
	""" This option determine the way socket will work. With "stream" value (this is a default value) target
	socket will be created with SOCK_STREAM type (and listen/bind/connect/accept socket's methods will be used).
	As the opposite variant datagram mode may be used. In this mode socket with SOCK_DGRAM type will be created
	(and bind/sendto/recv methods may be used)
	"""

	def __init__(self, uri):
		""" Create new object (and Unix socket object also) from specification defined by an URI

		:param uri: socket specification
		:type uri: WURI
		"""
		WSocketHandlerProto.__init__(self)
		self.__uri = uri

		socket_type = socket.SOCK_STREAM

		uri_query = uri.query()
		if uri_query is not None:
			uri_query = WStrictURIQuery.parse(uri_query)
			socket_opts = WStrictURIQuery(uri_query, self.__type_options_spec__, extra_parameters=False)

			if 'type' in socket_opts:
				if 'datagram' in socket_opts['type']:
					socket_type = socket.SOCK_DGRAM

		self.__socket = socket.socket(family=socket.AF_UNIX, type=socket_type)

	def uri(self):
		""" :meth:`.WSocketHandlerProto.uri` implementation

		:rtype: WURI
		"""
		return self.__uri

	def socket(self):
		""" :meth:`.WSocketHandlerProto.socket` implementation

		:rtype: socket.socket
		"""
		return self.__socket

	@classmethod
	def create_handler(cls, uri, **kwargs):
		""" :meth:`.WSchemeHandler.create_handler` implementation

		:type uri: WURI
		:rtype: WSocketHandlerProto
		"""
		return cls(uri)

	@classmethod
	def scheme_specification(cls):
		""" :meth:`.WSchemeHandler.scheme_specification` implementation

		:rtype: WSchemeSpecification
		"""
		return WSchemeSpecification(
			'unix',
			WURIComponentVerifier(WURI.Component.path, WURIComponentVerifier.Requirement.required),
			WURIQueryVerifier(
				WURIComponentVerifier.Requirement.optional,
				cls.__type_options_spec__,
				extra_parameters=False
			)
		)


class WSocketCollectionProto(WSchemeCollection):
	""" Custom :class:`.WSchemeCollection` collection suitable for :class:`.WSocketHandlerProto` handlers
	"""

	@verify_subclass(scheme_handler_cls=WSocketHandlerProto)
	def add(self, scheme_handler_cls):
		""" :meth:`.WSchemeCollection.add` method overloaded (supported classes is restricted)

		:type scheme_handler_cls: type (WSocketHandlerProto)
		:rtype: None
		"""
		WSchemeCollection.add(self, scheme_handler_cls)


__default_socket_collection__ = WSocketCollectionProto(
	WUDPSocketHandler,
	WTCPSocketHandler,
	WUnixSocketHandler
)
""" Default collection that is able to create UDP, TCP and Unix sockets 
"""
