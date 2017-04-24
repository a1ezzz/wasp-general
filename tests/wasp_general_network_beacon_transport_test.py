# -*- coding: utf-8 -*-

import pytest
import socket

from wasp_general.config import WConfig

from wasp_general.network.primitives import WIPV4SocketInfo
from wasp_general.network.beacon.transport import WBroadcastBeaconTransport, WMulticastBeaconTransport


class TestWBroadcastBeaconTransport:

	def test_target_socket(self):
		config = WConfig()
		config.add_section('wasp-general::network::beacon')
		config['wasp-general::network::beacon']['address'] = ''
		config['wasp-general::network::beacon']['port'] = ''

		t = WBroadcastBeaconTransport()
		pytest.raises(ValueError, t.target_socket, config)
		config['wasp-general::network::beacon']['address'] = 'site1.org'
		pytest.raises(ValueError, t.target_socket, config)
		config['wasp-general::network::beacon']['address'] = ''
		config['wasp-general::network::beacon']['port'] = '9999'
		pytest.raises(ValueError, t.target_socket, config)

		config['wasp-general::network::beacon']['address'] = 'site1.org'
		pytest.raises(ValueError, t.target_socket, config)

		config['wasp-general::network::beacon']['address'] = '4.4.4.4'
		assert(isinstance(t.target_socket(config), WIPV4SocketInfo) is True)
		assert(t.target_socket(config).pair() == ('4.4.4.4', 9999))

	def test_server_socket(self):
		config = WConfig()
		config.add_section('wasp-general::network::beacon')
		config['wasp-general::network::beacon']['bind_address'] = ''
		config['wasp-general::network::beacon']['port'] = '20202'

		t = WBroadcastBeaconTransport()
		s1 = t.server_socket(config)
		assert(isinstance(s1, socket.socket) is True)
		assert(s1.getsockname() == ('0.0.0.0', 20202))
		assert(s1 == t.server_socket(config))
		t.close_server_socket(config)

		config['wasp-general::network::beacon']['bind_address'] = '127.0.0.1'
		s2 = t.server_socket(config)
		assert(s2.getsockname() == ('127.0.0.1', 20202))
		assert(s2 != s1)
		t.close_server_socket(config)

	def test_client_socket(self):
		config = WConfig()
		config.add_section('wasp-general::network::beacon')
		config['wasp-general::network::beacon']['address'] = '127.0.0.1'
		config['wasp-general::network::beacon']['port'] = '20202'

		t = WBroadcastBeaconTransport()
		s1 = t.client_socket(config)
		assert(isinstance(s1, socket.socket) is True)
		assert(s1 == t.client_socket(config))
		t.close_client_socket(config)

		s2 = t.client_socket(config)
		assert(s2 != s1)
		t.close_client_socket(config)


class TestWMulticastBeaconTransport:

	def test_transport(self):
		config = WConfig()
		config.add_section('wasp-general::network::beacon')
		config['wasp-general::network::beacon']['bind_address'] = ''
		config['wasp-general::network::beacon']['address'] = '127.0.0.1'
		config['wasp-general::network::beacon']['port'] = '7070'
		transport = WMulticastBeaconTransport()

		pytest.raises(ValueError, transport.target_socket, config)
		config['wasp-general::network::beacon']['address'] = '239.200.1.2'
		assert(isinstance(transport.target_socket(config), WIPV4SocketInfo) is True)

		s1 = transport.server_socket(config)
		assert(isinstance(s1, socket.socket) is True)
		transport.close_server_socket(config)
		s2 = transport.server_socket(config)
		assert(isinstance(s2, socket.socket) is True)
		assert(s1 != s2)
