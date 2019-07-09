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

from abc import ABCMeta, abstractmethod
import socket
import enum

from wasp_general.verify import verify_type, verify_value

from wasp_general.uri import WURI, WURIQuery

from wasp_general.network.primitives import WIPV4Address, WNetworkIPV4

from wasp_general.api.uri import WURIRestriction, WURIQueryRestriction, WURIAPIRegistry, register_scheme_handler
from wasp_general.api.check import WSupportedArgs, WArgsRequirements, WNotNullValues, WArgsValueRegExp, WChainChecker
from wasp_general.api.check import WIterValueRestriction


class WSocketHandlerProto(metaclass=ABCMeta):
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


class WSocketAPIRegistry(WURIAPIRegistry):
	""" This is a registry for socket handlers. Such handlers as a descriptor must be a callable that accepts
	the specified URI as a first argument
	"""

	@verify_type('paranoid', uri=(WURI, str))
	def open(self, uri):
		""" Return socket handler by a scheme name in URI

		:param uri: URI from which a scheme name will be fetched
		:type uri: WURI | str

		:rtype: WSocketHandlerProto
		"""
		create_handler_fn = WURIAPIRegistry.open(self, uri)
		return create_handler_fn(uri)


__default_socket_collection__ = WSocketAPIRegistry()
""" Default collection that is able to create UDP, TCP and Unix sockets
"""


class WUDPSocketHandler(WSocketHandlerProto):
	""" :class:`.WSocketHandlerProto` implementation with which UDP socket may be created
	"""

	@enum.unique
	class QueryArg(enum.Enum):
		""" Socket options
		"""
		multicast = 'multicast'  # set up multicast socket

	__uri_check__ = WURIRestriction(
		WChainChecker(
			WSupportedArgs(
				WURI.Component.scheme.value,
				WURI.Component.hostname.value,
				WURI.Component.port.value,
				WURI.Component.query.value
			),
			WArgsRequirements(
				WURI.Component.hostname.value,
				WURI.Component.port.value
			),
			WURIQueryRestriction(
				WSupportedArgs(QueryArg.multicast.value),
				WNotNullValues(QueryArg.multicast.value)
			)
		)
	)  # URI compatibility check

	@verify_type('strict', uri=WURI)
	@verify_value(uri=lambda x: WUDPSocketHandler.__uri_check__.check(x) or True)
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
			socket_opts = WURIQuery.parse(uri_query)

			if WUDPSocketHandler.QueryArg.multicast.value in socket_opts:
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

	@staticmethod
	@register_scheme_handler(__default_socket_collection__, 'udp')
	@verify_type('strict', uri=WURI)
	def create_handler(uri):
		""" Function that is registered in a default registry

		:type uri: WURI
		:rtype: WUDPSocketHandler
		"""
		return WUDPSocketHandler(uri)


class WTCPSocketHandler(WSocketHandlerProto):
	""" :class:`.WSocketHandlerProto` implementation with which TCP socket may be created
	"""

	__uri_check__ = WURIRestriction(
		WChainChecker(
			WSupportedArgs(
				WURI.Component.scheme.value,
				WURI.Component.hostname.value,
				WURI.Component.port.value
			),
			WArgsRequirements(
				WURI.Component.hostname.value,
				WURI.Component.port.value
			),
		)
	)  # URI compatibility check

	@verify_type('strict', uri=WURI)
	@verify_value(uri=lambda x: WTCPSocketHandler.__uri_check__.check(x) or True)
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

	@staticmethod
	@register_scheme_handler(__default_socket_collection__, 'tcp')
	@verify_type('strict', uri=WURI)
	def create_handler(uri):
		""" Function that is registered in a default registry

		:type uri: WURI
		:rtype: WTCPSocketHandler
		"""
		return WTCPSocketHandler(uri)


class WUnixSocketHandler(WSocketHandlerProto):
	""" :class:`.WSocketHandlerProto` implementation with which Unix socket may be created
	"""

	@enum.unique
	class QueryArg(enum.Enum):
		""" Socket options
		"""
		type = 'type'
		""" This option defines the way socket will work. With "stream" value (this is a default value) target
		socket will be created with SOCK_STREAM type (and listen/bind/connect/accept socket's methods will
		be used). As the opposite variant datagram mode may be used. In this mode socket with SOCK_DGRAM type
		will be created (and bind/sendto/recv methods may be used)
		"""

	__uri_check__ = WURIRestriction(
		WChainChecker(
			WSupportedArgs(
				WURI.Component.scheme.value,
				WURI.Component.path.value,
				WURI.Component.query.value
			),
			WArgsRequirements(
				WURI.Component.path.value
			),
			WURIQueryRestriction(
				WSupportedArgs(QueryArg.type.value),
				WIterValueRestriction(
					WArgsValueRegExp('stream|datagram', QueryArg.type.value), max_length=1
				)
			),
		)
	)  # URI compatibility check

	@verify_type('strict', uri=WURI)
	@verify_value(uri=lambda x: WUnixSocketHandler.__uri_check__.check(x) or True)
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
			socket_opts = WURIQuery.parse(uri_query)

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

	@staticmethod
	@register_scheme_handler(__default_socket_collection__, 'unix')
	@verify_type('strict', uri=WURI)
	def create_handler(uri):
		""" Function that is registered in a default registry

		:type uri: WURI
		:rtype: WUnixSocketHandler
		"""
		return WUnixSocketHandler(uri)
