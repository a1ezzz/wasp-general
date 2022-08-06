# -*- coding: utf-8 -*-

import pytest
import socket

from wasp_general.config import WConfig

from wasp_general.network.transport import WNetworkNativeTransportProto, WNetworkNativeTransport
from wasp_general.network.transport import WNetworkNativeTransportSocketConfig, WUDPNetworkNativeTransport
from wasp_general.network.transport import WMulticastNetworkTransport, WTCPNetworkNativeTransport
from wasp_general.network.transport import WBroadcastNetworkTransport
from wasp_general.network.primitives import WIPV4SocketInfo


def test_abstract():
	pytest.raises(TypeError, WNetworkNativeTransportProto)
	pytest.raises(NotImplementedError, WNetworkNativeTransportProto.server_socket, None, WConfig())
	pytest.raises(NotImplementedError, WNetworkNativeTransportProto.close_server_socket, None, WConfig())
	pytest.raises(NotImplementedError, WNetworkNativeTransportProto.client_socket, None, WConfig())
	pytest.raises(NotImplementedError, WNetworkNativeTransportProto.close_client_socket, None, WConfig())
	pytest.raises(NotImplementedError, WNetworkNativeTransportProto.target_socket, None, WConfig())
	pytest.raises(NotImplementedError, WNetworkNativeTransportProto.bind_socket, None, WConfig())

	pytest.raises(TypeError, WNetworkNativeTransport)
	pytest.raises(NotImplementedError, WNetworkNativeTransport._create_socket, None)


class TestWNetworkNativeTransportSocketConfig:

	def test_config(self):
		c = WNetworkNativeTransportSocketConfig('section1', 'option1', 'option2')
		assert(c.section == 'section1')
		assert(c.address_option == 'option1')
		assert(c.port_option == 'option2')


class TestNetworkTransport:

	class NativeTransport(WNetworkNativeTransport):

		def _create_socket(self):
			return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	def test_bind_socket(self):
		config = WConfig()
		config.add_section('section')
		config['section']['server_address'] = ''
		config['section']['server_port'] = ''
		config['section']['client_address'] = ''
		config['section']['client_port'] = ''

		assert(issubclass(WNetworkNativeTransport, WNetworkNativeTransportProto) is True)

		t = TestNetworkTransport.NativeTransport(
			WNetworkNativeTransportSocketConfig('section', 'client_address', 'client_port'),
			WNetworkNativeTransportSocketConfig('section', 'server_address', 'server_port')
		)

		pytest.raises(ValueError, t.bind_socket, config)
		config['section']['server_address'] = 'site1.org'
		pytest.raises(ValueError, t.bind_socket, config)
		config['section']['server_address'] = ''
		config['section']['server_port'] = '70'
		assert(isinstance(t.bind_socket(config), WIPV4SocketInfo) is True)
		assert(t.bind_socket(config).pair() == ('', 70))

		config['section']['server_address'] = 'site1.org'
		assert(t.bind_socket(config).pair() == ('site1.org', 70))

		config['section']['server_address'] = '192.192.192.192'
		assert (t.bind_socket(config).pair() == ('192.192.192.192', 70))

		pytest.raises(ValueError, t.target_socket, config)
		config['section']['client_address'] = 'site1.org'
		pytest.raises(ValueError, t.target_socket, config)
		config['section']['client_address'] = ''
		config['section']['client_port'] = '9999'
		pytest.raises(ValueError, t.target_socket, config)

		config['section']['client_address'] = 'site1.org'
		assert(isinstance(t.target_socket(config), WIPV4SocketInfo) is True)
		assert(t.target_socket(config).pair() == ('site1.org', 9999))

		config['section']['client_address'] = '4.4.4.4'
		assert(isinstance(t.target_socket(config), WIPV4SocketInfo) is True)
		assert(t.target_socket(config).pair() == ('4.4.4.4', 9999))

	def test_socket(self):

		config = WConfig()
		config.add_section('section')
		config['section']['server_address'] = ''
		config['section']['server_port'] = '20202'
		config['section']['client_address'] = '127.0.0.1'
		config['section']['client_port'] = '20202'

		t = TestNetworkTransport.NativeTransport(
			WNetworkNativeTransportSocketConfig('section', 'client_address', 'client_port'),
			WNetworkNativeTransportSocketConfig('section', 'server_address', 'server_port')
		)
		s1 = t.server_socket(config)
		assert(isinstance(s1, socket.socket) is True)
		assert(s1.getsockname() == ('0.0.0.0', 20202))
		assert(s1 == t.server_socket(config))
		t.close_server_socket(config)

		config['section']['server_address'] = '127.0.0.1'
		s2 = t.server_socket(config)
		assert(s2.getsockname() == ('127.0.0.1', 20202))
		assert(s2 != s1)
		t.close_server_socket(config)

		s1 = t.client_socket(config)
		assert(isinstance(s1, socket.socket) is True)
		assert(s1 == t.client_socket(config))
		t.close_client_socket(config)

		s2 = t.client_socket(config)
		assert(s2 != s1)
		t.close_client_socket(config)


class TestWUDPNetworkTransport:

	def test_socket(self):

		config = WConfig()
		config.add_section('section')
		config['section']['server_address'] = ''
		config['section']['server_port'] = '20202'
		config['section']['client_address'] = '127.0.0.1'
		config['section']['client_port'] = '20202'

		t = WUDPNetworkNativeTransport(
			WNetworkNativeTransportSocketConfig('section', 'client_address', 'client_port'),
			WNetworkNativeTransportSocketConfig('section', 'server_address', 'server_port')
		)
		s = t._create_socket()
		assert(isinstance(s, socket.socket) is True)
		assert(s.type == socket.SOCK_DGRAM)


class TestWTCPNetworkTransport:

	def test_socket(self):

		config = WConfig()
		config.add_section('section')
		config['section']['server_address'] = ''
		config['section']['server_port'] = '20202'
		config['section']['client_address'] = '127.0.0.1'
		config['section']['client_port'] = '20202'

		t = WTCPNetworkNativeTransport(
			WNetworkNativeTransportSocketConfig('section', 'client_address', 'client_port'),
			WNetworkNativeTransportSocketConfig('section', 'server_address', 'server_port')
		)
		s = t._create_socket()
		assert(isinstance(s, socket.socket) is True)
		assert(s.type == socket.SOCK_STREAM)


class TestWBroadcastNetworkTransport:

	def test_target_socket(self):
		config = WConfig()
		config.add_section('section')
		config['section']['server_address'] = ''
		config['section']['server_port'] = ''
		config['section']['client_address'] = ''
		config['section']['client_port'] = ''

		t = WBroadcastNetworkTransport(
			WNetworkNativeTransportSocketConfig('section', 'client_address', 'client_port'),
			WNetworkNativeTransportSocketConfig('section', 'server_address', 'server_port')
		)
		pytest.raises(ValueError, t.target_socket, config)
		config['section']['client_address'] = 'site1.org'
		pytest.raises(ValueError, t.target_socket, config)
		config['section']['client_address'] = ''
		config['section']['client_port'] = '9999'
		pytest.raises(ValueError, t.target_socket, config)

		config['section']['client_address'] = 'site1.org'
		pytest.raises(ValueError, t.target_socket, config)

		config['section']['client_address'] = '4.4.4.4'
		assert(isinstance(t.target_socket(config), WIPV4SocketInfo) is True)
		assert(t.target_socket(config).pair() == ('4.4.4.4', 9999))

	def test_client_socket(self):
		config = WConfig()
		config.add_section('section')
		config['section']['server_address'] = ''
		config['section']['server_port'] = ''
		config['section']['client_address'] = '4.4.4.4'
		config['section']['client_port'] = '9999'

		t = WBroadcastNetworkTransport(
			WNetworkNativeTransportSocketConfig('section', 'client_address', 'client_port'),
			WNetworkNativeTransportSocketConfig('section', 'server_address', 'server_port')
		)

		s = t.create_client_socket(config)
		assert(isinstance(s, socket.socket) is True)
		assert(s.type == socket.SOCK_DGRAM)
		assert(s.getsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST) == 1)


class TestWMulticastNetworkTransport:

	def test_transport(self):
		config = WConfig()
		config.add_section('section')
		config['section']['server_address'] = ''
		config['section']['server_port'] = '7070'
		config['section']['client_address'] = '127.0.0.1'
		config['section']['client_port'] = '7070'

		transport = WMulticastNetworkTransport(
			WNetworkNativeTransportSocketConfig('section', 'client_address', 'client_port'),
			WNetworkNativeTransportSocketConfig('section', 'server_address', 'server_port')
		)

		pytest.raises(ValueError, transport.target_socket, config)
		config['section']['client_address'] = '239.200.1.2'
		assert(isinstance(transport.target_socket(config), WIPV4SocketInfo) is True)

		s1 = transport.server_socket(config)
		assert(isinstance(s1, socket.socket) is True)
		assert(s1.type == socket.SOCK_DGRAM)

		transport.close_server_socket(config)
		s2 = transport.server_socket(config)
		assert(isinstance(s2, socket.socket) is True)
		assert(s1 != s2)
