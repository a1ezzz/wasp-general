# -*- coding: utf-8 -*-
# wasp_general/network/transport.py
#
# Copyright (C) 2016 the wasp-general authors and contributors
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

from abc import ABCMeta, abstractmethod
import socket
import struct

from wasp_general.verify import verify_type, verify_value
from wasp_general.config import WConfig

from wasp_general.network.primitives import WIPV4SocketInfo, WIPV4Address, WNetworkIPV4


class WNetworkNativeTransportProto(metaclass=ABCMeta):
	""" This is interface for classes, that implement transport logic for network communication. "Native" means
	that these classes use socket objects directly.
	"""

	@abstractmethod
	@verify_type(config=WConfig)
	def server_socket(self, config):
		""" Return server socket. This socket is used for receiving requests and sending results. It is
		important, that the result can be polled by a IOLoop instance.

		:param config: server configuration
		:return: socket.socket
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(config=WConfig, close_fd=bool)
	def close_server_socket(self, config, close_fd=True):
		""" Close previously opened server socket. If no socket is opened - do nothing.

		:param config: server configuration
		:param close_fd: should this function close socket fd, or will it close by an external function?. It \
		is safer to pass True here.
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(config=WConfig)
	def client_socket(self, config):
		""" Return client socket. This socket is used for sending request and receiving results. It is
		important, that the result can be polled by a IOLoop instance.

		:param config: client configuration
		:return: socket.socket
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(config=WConfig, close_fd=bool)
	def close_client_socket(self, config, close_fd=True):
		""" Close previously opened client socket. If no socket is opened - do nothing.

		:param config: client configuration
		:param close_fd: should this function close socket fd, or will it close by an external function?. It \
		is safer to pass True here.
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(config=WConfig)
	def target_socket(self, config):
		""" Return socket information with server address. Mostly used for address validation.

		:param config: client configuration
		:return: WIPV4SocketInfo
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(config=WConfig)
	def bind_socket(self, config):
		""" Return socket information with address that server binds to.

		:param config: server configuration
		:return: WIPV4SocketInfo
		"""
		raise NotImplementedError('This method is abstract')


class WNetworkNativeTransportSocketConfig:
	""" Represent socket configuration settings.
	"""

	@verify_type(section=str, address_option=str, port_option=str)
	@verify_value(section=lambda x: len(x) > 0, address_option=lambda x: len(x) > 0, port_option=lambda x: len(x) > 0)
	def __init__(self, section, address_option, port_option):
		""" Construct new configuration settings

		:param section: section name
		:param address_option: address option name
		:param port_option: port option name
		"""
		self.section = section
		self.address_option = address_option
		self.port_option = port_option


class WNetworkNativeTransport(WNetworkNativeTransportProto, metaclass=ABCMeta):
	""" Basic WNetworkNativeTransportProto implementation. This class isn't ready to use, but it has general
	implementation for the most WNetworkNativeTransportProto methods.
	"""

	@verify_type(target_socket_config=WNetworkNativeTransportSocketConfig)
	@verify_type(bind_socket_config=WNetworkNativeTransportSocketConfig)
	def __init__(self, target_socket_config, bind_socket_config):
		""" Create new transport

		:param target_socket_config: configuration for client socket
		:param bind_socket_config: configuration for server socket
		"""

		self.__target_socket_config = target_socket_config
		self.__bind_socket_config = bind_socket_config

		self.__server_socket = None
		self.__client_socket = None

	@verify_type(config=WConfig)
	def target_socket(self, config):
		""" :meth:`.WNetworkNativeTransportProto.server_socket` method implementation
		"""
		address = config[self.__target_socket_config.section][self.__target_socket_config.address_option]
		port = config.getint(self.__target_socket_config.section, self.__target_socket_config.port_option)

		target = WIPV4SocketInfo(address, port)
		if target.address() is None or target.port() is None:
			raise ValueError('Invalid target address or port')
		return target

	@verify_type(config=WConfig)
	def bind_socket(self, config):
		""" :meth:`.WNetworkNativeTransportProto.bind_socket` method implementation
		"""
		address = config[self.__bind_socket_config.section][self.__bind_socket_config.address_option]
		port = config.getint(self.__bind_socket_config.section, self.__bind_socket_config.port_option)
		return WIPV4SocketInfo(address, port)

	@abstractmethod
	def _create_socket(self):
		""" Create general socket object, that can be used for client and/or server usage

		:return: socket.socket
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(config=WConfig)
	def create_server_socket(self, config):
		""" Create socket for server. (By default, same as WNetworkNativeTransport._create_socket)

		:param config: server configuration
		:return: socket.socket
		"""
		return self._create_socket()

	@verify_type(config=WConfig)
	def create_client_socket(self, config):
		""" Create socket for client. (By default, same as WNetworkNativeTransport._create_socket)

		:param config: client configuration
		:return: socket.socket
		"""
		return self._create_socket()

	@verify_type(config=WConfig)
	def server_socket(self, config):
		""" :meth:`.WNetworkNativeTransportProto.server_socket` method implementation
		"""
		if self.__server_socket is None:
			self.__server_socket = self.create_server_socket(config)
			self.__server_socket.bind(self.bind_socket(config).pair())
		return self.__server_socket

	@verify_type(config=WConfig, close_fd=bool)
	def close_server_socket(self, config, close_fd=True):
		""" :meth:`.WNetworkNativeTransportProto.close_server_socket` method implementation
		"""
		if close_fd is True:
			self.__server_socket.close()
		self.__server_socket = None

	@verify_type(config=WConfig)
	def client_socket(self, config):
		""" :meth:`.WNetworkNativeTransportProto.client_socket` method implementation
		"""
		if self.__client_socket is None:
			self.__client_socket = self.create_client_socket(config)
		return self.__client_socket

	@verify_type(config=WConfig, close_fd=bool)
	def close_client_socket(self, config, close_fd=True):
		""" :meth:`.WNetworkNativeTransportProto.close_client_socket` method implementation
		"""
		if close_fd is True:
			self.__client_socket.close()
		self.__client_socket = None


class WUDPNetworkNativeTransport(WNetworkNativeTransport, metaclass=ABCMeta):
	""" Basic UDP transport implementation
	"""

	def _create_socket(self):
		""" Create general UDP-socket

		:return: socket.socket
		"""
		return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class WTCPNetworkNativeTransport(WNetworkNativeTransport):
	""" Basic TCP transport implementation
	"""

	def _create_socket(self):
		""" Create general TCP-socket

		:return: socket.socket
		"""
		return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


class WBroadcastNetworkTransport(WUDPNetworkNativeTransport):
	""" Network transport, that uses IPv4 broadcast (UDP) communication
	"""

	@verify_type('paranoid', target_socket_config=WNetworkNativeTransportSocketConfig)
	@verify_type('paranoid', bind_socket_config=WNetworkNativeTransportSocketConfig)
	def __init__(self, target_socket_config, bind_socket_config):
		""" Create new broadcast transport
		"""
		WNetworkNativeTransport.__init__(self, target_socket_config, bind_socket_config)

	@verify_type('paranoid', config=WConfig)
	def target_socket(self, config):
		""" This method overrides :meth:`.WNetworkNativeTransport.target_socket` method. Do the same thing as
		basic method do, but also checks that the result address is IPv4 address.

		:param config: beacon configuration
		:return: WIPV4SocketInfo
		"""
		target = WNetworkNativeTransport.target_socket(self, config)
		if isinstance(target.address(), WIPV4Address) is False:
			raise ValueError('Invalid address for broadcast transport')
		return target

	@verify_type('paranoid', config=WConfig)
	def create_client_socket(self, config):
		""" Create client broadcast socket

		:param config: client configuration
		:return: socket.socket
		"""
		client_socket = WUDPNetworkNativeTransport.create_client_socket(self, config)
		client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		return client_socket


class WMulticastNetworkTransport(WUDPNetworkNativeTransport):
	""" Network transport, that uses IPv4 multicast communication
	"""

	@verify_type('paranoid', target_socket_config=WNetworkNativeTransportSocketConfig)
	@verify_type('paranoid', bind_socket_config=WNetworkNativeTransportSocketConfig)
	def __init__(self, target_socket_config, bind_socket_config):
		""" Create new multicast transport
		"""
		WUDPNetworkNativeTransport.__init__(self, target_socket_config, bind_socket_config)

	@verify_type('paranoid', config=WConfig)
	def target_socket(self, config):
		""" This method overrides :meth:`.WNetworkNativeTransport.target_socket` method. Do the same thing as
		basic method do, but also checks that the result address is IPv4 multicast address.

		:param config: beacon configuration
		:return: WIPV4SocketInfo
		"""
		target = WUDPNetworkNativeTransport.target_socket(self, config)
		if WNetworkIPV4.is_multicast(target.address()) is False:
			raise ValueError('IP multicast address not RFC compliant')
		return target

	@verify_type('paranoid', config=WConfig)
	def create_server_socket(self, config):
		""" Create server multicast socket. Socket will be joined to the multicast-group (same as it is
		specified in client configuration, same as client does)

		:param config: server configuration
		:return: socket.socket
		"""
		server_socket = WUDPNetworkNativeTransport.create_server_socket(self, config)

		group = socket.inet_aton(str(self.target_socket(config).address()))
		group_membership = struct.pack('4sL', group, socket.INADDR_ANY)
		server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group_membership)
		return server_socket
