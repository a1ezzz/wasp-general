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
import struct
import enum

from wasp_general.verify import verify_type, verify_value
from wasp_general.uri import WURI, WURIQuery
from wasp_general.types.str_enum import WStrEnum
from wasp_general.network.primitives import WIPV4Address, WNetworkIPV4

from wasp_general.api.registry import WAPIRegistry, register_api
from wasp_general.api.uri import WURIRestriction, WURIQueryRestriction
from wasp_general.api.check import WSupportedArgs, WArgsRequirements, WArgsValueRegExp, WChainChecker
from wasp_general.api.check import WIterValueRestriction, WConflictedArgs


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


class WSocketAPIRegistry(WAPIRegistry):
	""" This is a registry for socket handlers. Such handlers as a descriptor must be a callable that accepts
	the specified URI as a first argument
	"""

	@verify_type('strict', uri=(WURI, str))
	def open(self, uri):
		""" Return socket handler by a scheme name in URI

		:param uri: URI from which a scheme name will be fetched
		:type uri: WURI | str

		:rtype: WSocketHandlerProto
		"""
		if isinstance(uri, str):
			uri = WURI.parse(uri)
		create_handler_fn = WAPIRegistry.get(self, uri.scheme())
		return create_handler_fn(uri)

	@verify_type('paranoid', uri=(WURI, str))
	def aio_socket(self, uri):
		""" Create socket by uri from a socket handler and set it non-blocking mode

		:param uri: URI by which socket should be returned
		:type uri: WURI | str

		:return: Created socket
		:rtype: socket.socket
		"""
		socket_handler = self.open(uri)
		sock = socket_handler.socket()
		sock.setblocking(False)

		return sock


__default_socket_collection__ = WSocketAPIRegistry()
""" Default collection that is able to create UDP, TCP and Unix sockets
"""


class WUDPSocketHandler(WSocketHandlerProto):
	""" :class:`.WSocketHandlerProto` implementation with which UDP socket may be created
	"""

	@enum.unique
	class QueryArg(WStrEnum):
		""" Socket options
		"""
		multicast = enum.auto()  # set up multicast socket
		broadcast = enum.auto()  # set up broadcast socket

	__uri_check__ = WURIRestriction(
		WChainChecker(
			WSupportedArgs(
				WURI.Component.scheme, WURI.Component.hostname, WURI.Component.port, WURI.Component.query
			),
			WArgsRequirements(WURI.Component.hostname, WURI.Component.port),
			WURIQueryRestriction(
				WSupportedArgs(QueryArg.multicast, QueryArg.broadcast),
				WConflictedArgs(QueryArg.multicast, QueryArg.broadcast)
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
		multicast_address = None
		broadcast_address = None
		uri_query = uri.query()
		if uri_query is not None:
			socket_opts = WURIQuery.parse(uri_query)
			if WUDPSocketHandler.QueryArg.multicast in socket_opts:
				multicast_address = socket.gethostbyname(address)
				multicast_address = WIPV4Address(multicast_address)
				if WNetworkIPV4.is_multicast(multicast_address) is False:
					raise ValueError(
						'The specified address: "%s" is not a multicast address' %
						str(multicast_address)
					)
			elif WUDPSocketHandler.QueryArg.broadcast in socket_opts:
				broadcast_address = socket.gethostbyname(address)
				broadcast_address = WIPV4Address(broadcast_address)

		self.__socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
		if multicast_address:
			group = socket.inet_aton(str(multicast_address))
			group_membership = struct.pack('4sL', group, socket.INADDR_ANY)
			self.__socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group_membership)
		elif broadcast_address:
			self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

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
	@register_api(__default_socket_collection__, 'udp')  # TODO: may be move to __init__?
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

	@enum.unique
	class QueryArg(WStrEnum):
		""" Socket options
		"""
		reuse_addr = enum.auto()  # set up multicast socket

	__uri_check__ = WURIRestriction(
		WChainChecker(
			WSupportedArgs(WURI.Component.scheme, WURI.Component.hostname, WURI.Component.port, WURI.Component.query),
			WArgsRequirements(WURI.Component.hostname, WURI.Component.port),
			WURIQueryRestriction(WSupportedArgs(QueryArg.reuse_addr))
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

		uri_query = uri.query()
		if uri_query is not None:
			socket_opts = WURIQuery.parse(uri_query)
			if WTCPSocketHandler.QueryArg.reuse_addr in socket_opts:
				self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

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
	@register_api(__default_socket_collection__, 'tcp')
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
	class QueryArg(WStrEnum):
		""" Socket options
		"""
		type = enum.auto()
		""" This option defines the way socket will work. With "stream" value (this is a default value) target
		socket will be created with SOCK_STREAM type (and listen/bind/connect/accept socket's methods will
		be used). As the opposite variant datagram mode may be used. In this mode socket with SOCK_DGRAM type
		will be created (and bind/sendto/recv methods may be used)
		"""

	__uri_check__ = WURIRestriction(
		WChainChecker(
			WSupportedArgs(WURI.Component.scheme, WURI.Component.path, WURI.Component.query),
			WArgsRequirements(WURI.Component.path),
			WURIQueryRestriction(
				WSupportedArgs(QueryArg.type),
				WIterValueRestriction(WArgsValueRegExp('stream|datagram', QueryArg.type), max_length=1)
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

			if WUnixSocketHandler.QueryArg.type in socket_opts:
				if 'datagram' in socket_opts[WUnixSocketHandler.QueryArg.type]:
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
	@register_api(__default_socket_collection__, 'unix')
	@verify_type('strict', uri=WURI)
	def create_handler(uri):
		""" Function that is registered in a default registry

		:type uri: WURI
		:rtype: WUnixSocketHandler
		"""
		return WUnixSocketHandler(uri)
