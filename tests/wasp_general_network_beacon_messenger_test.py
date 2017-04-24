# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.beacon.messenger import WBeaconMessengerBase, WBeaconMessenger, WBeaconGouverneurMessenger
from wasp_general.network.beacon.messenger import WHostgroupBeaconMessenger
from wasp_general.network.primitives import WIPV4SocketInfo
from wasp_general.config import WConfig


def test_abstract():
	pytest.raises(TypeError, WBeaconMessengerBase)
	pytest.raises(NotImplementedError, WBeaconMessengerBase.request, None, WConfig())
	pytest.raises(NotImplementedError, WBeaconMessengerBase.has_response, None, WConfig(), b'', WIPV4SocketInfo())
	pytest.raises(NotImplementedError, WBeaconMessengerBase.response, None, WConfig(), b'', WIPV4SocketInfo())
	pytest.raises(
		NotImplementedError, WBeaconMessengerBase.response_address, None, WConfig(), b'', WIPV4SocketInfo()
	)
	pytest.raises(
		NotImplementedError, WBeaconMessengerBase.valid_response, None, WConfig(), b'', WIPV4SocketInfo()
	)


class TestWBeaconMessenger:

	def test_messenger(self):
		config = WConfig()
		client1 = WIPV4SocketInfo()

		m = WBeaconMessenger()
		assert(m.request(config) == WBeaconMessenger.__beacon_hello_msg__)
		assert(m.response(config, b'zxc', client1) == b'zxc')
		assert(m.response(config, b'1qaz', client1) == b'1qaz')

		assert(m.has_response(config, b'', client1) is False)
		assert(m.has_response(config, b'zxc', client1) is True)
		assert(m.has_response(config, b'1qaz', client1) is True)

		client2 = WIPV4SocketInfo('127.0.0.0', 200)
		assert(m.response_address(config, b'', client1).pair() == ('', 0))
		assert(m.response_address(config, b'', client2).pair() == ('127.0.0.0', 200))

		assert(m.valid_response(config, b'', client1) is False)
		assert(m.valid_response(config, b'zxc', client1) is True)


class TestWBeaconGouverneurMessenger:

	def test_request(self):
		config = WConfig()
		config.add_section('wasp-general::network::beacon')
		config['wasp-general::network::beacon']['public_address'] = ''
		config['wasp-general::network::beacon']['public_port'] = ''

		assert(WBeaconGouverneurMessenger(b'hi').request(config) == b'hi')
		assert(WBeaconGouverneurMessenger(b'hello_string').request(config) == b'hello_string')
		config['wasp-general::network::beacon']['public_address'] = 'qqq'
		assert (WBeaconGouverneurMessenger(b'hi').request(config) == b'hi:qqq')
		config['wasp-general::network::beacon']['public_address'] = ':'
		pytest.raises(ValueError, WBeaconGouverneurMessenger(b'hi').request, config)
		config['wasp-general::network::beacon']['public_address'] = 'qqq'
		config['wasp-general::network::beacon']['public_port'] = '70'
		assert(WBeaconGouverneurMessenger(b'hi').request(config) == b'hi:qqq:70')
		config['wasp-general::network::beacon']['public_address'] = ''
		assert(WBeaconGouverneurMessenger(b'hi').request(config) == b'hi')

	def test_invert_hello(self):
		assert(WBeaconGouverneurMessenger(b'hi').invert_hello() is False)
		assert(WBeaconGouverneurMessenger(b'hi', invert_hello=True).invert_hello() is True)

	def test_hello_message(self):
		assert(WBeaconGouverneurMessenger(b'hi').hello_message() == b'hi')
		assert(WBeaconGouverneurMessenger(b'hi').hello_message(invert_hello=True) == b'ih')

	def test_has_response(self):
		config = WConfig()
		m1 = WBeaconGouverneurMessenger(b'hi')
		m2 = WBeaconGouverneurMessenger(b'hello_string')

		assert(m1.has_response(config, b'hi', WIPV4SocketInfo()) is True)
		assert(m1.has_response(config, b'ih', WIPV4SocketInfo()) is False)
		assert(m2.has_response(config, b'hi', WIPV4SocketInfo()) is False)
		assert(m2.has_response(config, b'hello_string', WIPV4SocketInfo()) is True)
		assert(m1.has_response(config, b'hi:foo:1', WIPV4SocketInfo()) is True)

	def test_response(self):
		config = WConfig()
		config.add_section('wasp-general::network::beacon')
		config['wasp-general::network::beacon']['public_address'] = ''
		config['wasp-general::network::beacon']['public_port'] = ''
		si = WIPV4SocketInfo('192.168.0.1', 7777)

		assert(WBeaconGouverneurMessenger(b'hi').response(config, b'req', si) == b'hi')
		assert(WBeaconGouverneurMessenger(b'hello_string').response(config, b'req', si) == b'hello_string')
		config['wasp-general::network::beacon']['public_address'] = 'qqq'
		assert (WBeaconGouverneurMessenger(b'hi').response(config, b'req', si) == b'hi:qqq')
		config['wasp-general::network::beacon']['public_address'] = ':'
		pytest.raises(ValueError, WBeaconGouverneurMessenger(b'hi').response, config, b'req', si)
		config['wasp-general::network::beacon']['public_address'] = 'qqq'
		config['wasp-general::network::beacon']['public_port'] = '70'
		assert(WBeaconGouverneurMessenger(b'hi').response(config, b'req', si) == b'hi:qqq:70')
		config['wasp-general::network::beacon']['public_address'] = ''
		assert(WBeaconGouverneurMessenger(b'hi').response(config, b'req', si) == b'hi')

	def test_response_address(self):
		config = WConfig()
		si = WIPV4SocketInfo('192.168.0.1', 7777)

		address = WBeaconGouverneurMessenger(b'hi').response_address(config, b'hi', si)
		assert(address.pair() == ('192.168.0.1', 7777))
		address = WBeaconGouverneurMessenger(b'hi').response_address(config, b'hi:127.0.0.1', si)
		assert(address.pair() == ('127.0.0.1', 7777))
		address = WBeaconGouverneurMessenger(b'hi').response_address(config, b'hi:127.0.0.1:90', si)
		assert(address.pair() == ('127.0.0.1', 90))

		pytest.raises(ValueError, WBeaconGouverneurMessenger(b'hi').response_address, config, b'hello', si)
		pytest.raises(ValueError, WBeaconGouverneurMessenger(b'hi').response_address, config, b'hi:e:l:l:o', si)

	def test_valid_response(self):
		config = WConfig()
		m = WBeaconGouverneurMessenger(b'hi')

		assert(m.valid_response(config, b'hi', WIPV4SocketInfo()) is True)
		assert(m.valid_response(config, b'ih', WIPV4SocketInfo()) is False)

		m = WBeaconGouverneurMessenger(b'hi', invert_hello=True)
		assert(m.valid_response(config, b'hi', WIPV4SocketInfo()) is False)
		assert(m.valid_response(config, b'ih', WIPV4SocketInfo()) is True)


class TestWHostgroupBeaconMessenger:

	def test_task(self):
		config = WConfig()
		config.add_section('wasp-general::network::beacon')
		config['wasp-general::network::beacon']['public_address'] = ''
		config['wasp-general::network::beacon']['public_port'] = ''
		si = WIPV4SocketInfo('1.1.1.1', 1)

		pytest.raises(TypeError, WHostgroupBeaconMessenger, b'HELLOMSG', b'group')
		pytest.raises(ValueError, WHostgroupBeaconMessenger, b'HELLOMSG', 'group-')

		messenger = WHostgroupBeaconMessenger(b'HELLOMSG')
		assert(isinstance(messenger, WBeaconGouverneurMessenger) is True)
		assert(messenger.hostgroups() == [])
		assert(messenger.request(config) == b'HELLOMSG')
		config['wasp-general::network::beacon']['public_address'] = 'site1.org'
		assert(messenger.request(config) == b'HELLOMSG:site1.org')
		config['wasp-general::network::beacon']['public_port'] = '10'
		assert(messenger.request(config) == b'HELLOMSG:site1.org:10')
		data = messenger._message_hostgroup_parse(b'HELLOMSG:site1.org')
		assert(data[0] == [])
		assert(str(data[1].address()) == 'site1.org')
		assert(data[1].port() is None)

		assert(messenger.has_response(config, b'HELLOMSG', si) is True)
		assert(messenger.has_response(config, b'HELLOMSG:2.2.2.2', si) is True)
		assert(messenger.has_response(config, b'HELLOMSG:2.2.2.2#server', si) is True)
		assert(messenger.has_response(config, b'HELLOMSG#users', si) is True)
		assert(messenger.has_response(config, b'HELLOMSG#g', si) is True)

		config['wasp-general::network::beacon']['public_address'] = ''
		config['wasp-general::network::beacon']['public_port'] = ''
		messenger = WHostgroupBeaconMessenger(b'HELLOMSG', 'group1', 'servers')
		assert(messenger.hostgroups() == ['group1', 'servers'])
		assert(messenger.request(config) == b'HELLOMSG#group1,servers')
		config['wasp-general::network::beacon']['public_address'] = 'site1.org'
		assert(messenger.request(config) == b'HELLOMSG:site1.org#group1,servers')
		data = messenger._message_hostgroup_parse(b'HELLOMSG:site1.org#group1,servers')
		assert(data[0] == [b'group1', b'servers'])
		assert(str(data[1].address()) == 'site1.org')
		assert(data[1].port() is None)
		config['wasp-general::network::beacon']['public_port'] = '10'
		assert(messenger.request(config) == b'HELLOMSG:site1.org:10#group1,servers')

		pytest.raises(ValueError, messenger._message_hostgroup_parse, b'HELLOMSG##group1,servers')

		assert(messenger.has_response(config, b'HELLOMSG', si) is True)
		assert(messenger.has_response(config, b'HELLOMSG:2.2.2.2', si) is True)
		assert(messenger.has_response(config, b'HELLOMSG:2.2.2.2#servers', si) is True)
		assert(messenger.has_response(config, b'HELLOMSG:2.2.2.2#servers, group1', si) is True)
		assert(messenger.has_response(config, b'HELLOMSG#users', si) is False)
		assert(messenger.has_response(config, b'HELLOMSG#g', si) is False)
		assert(messenger.has_response(config, b'HELLOMSG##servers', si) is False)

		assert(str(messenger.response_address(config, b'HELLOMSG', si).address()) == '1.1.1.1')
		assert(str(messenger.response_address(config, b'HELLOMSG:2.2.2.2', si).address()) == '2.2.2.2')
		assert(str(messenger.response_address(config, b'HELLOMSG#users', si).address()) == '1.1.1.1')
		assert(str(messenger.response_address(config, b'HELLOMSG:2.2.2.2#u', si).address()) == '2.2.2.2')
