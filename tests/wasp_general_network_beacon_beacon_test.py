# -*- coding: utf-8 -*-

import io
import os
import pytest
from threading import Thread, Lock
from zmq.eventloop.ioloop import IOLoop
from tempfile import mktemp


from wasp_general.network.transport import WNetworkNativeTransportProto
from wasp_general.network.beacon.beacon import WNetworkServerBeacon, WNetworkClientBeacon, WNetworkBeaconCallback
from wasp_general.network.beacon.messenger import WBeaconMessenger
from wasp_general.network.beacon.transport import WBroadcastBeaconTransport, WMulticastBeaconTransport

from wasp_general.config import WConfig
from wasp_general.network.primitives import WIPV4SocketInfo


def test_abstract():
	pytest.raises(TypeError, WNetworkBeaconCallback)
	description = WNetworkBeaconCallback.WDataDescription.request
	pytest.raises(NotImplementedError, WNetworkBeaconCallback.__call__, None, b'', WIPV4SocketInfo(), description)


class FakeBeaconTransport(WNetworkNativeTransportProto):

	__global_lock__ = Lock()

	class FakeSocket:

		def __init__(self, ro_filename, wo_filename):
			self.__ro_filename = ro_filename
			self.__wo_filename = wo_filename
			self.__file_ro = None
			self.__file_wo = None

		def open(self):
			if self.__file_ro is None:
				self.__file_ro = open(self.__ro_filename, 'r')
			if self.__file_wo is None:
				self.__file_wo = open(self.__wo_filename, 'w')

		def fileno(self):
			return self.__file_ro.fileno()

		def recvfrom(self, bytes_count):
			FakeBeaconTransport.__global_lock__.acquire()
			self.__file_ro.seek(0, io.SEEK_SET)
			data = self.__file_ro.read(bytes_count).encode()
			truncate_file = open(self.__ro_filename, 'w')
			truncate_file.seek(0, io.SEEK_SET)
			truncate_file.truncate()
			FakeBeaconTransport.__global_lock__.release()
			return data, ('fake-host', 1)

		def sendto(self, data, address):
			FakeBeaconTransport.__global_lock__.acquire()
			self.__file_wo.seek(0, io.SEEK_SET)
			self.__file_wo.write(data.decode())
			self.__file_wo.flush()
			FakeBeaconTransport.__global_lock__.release()

	def __init__(self, file_suffix):
		WNetworkNativeTransportProto.__init__(self)
		self.__file_suffix = file_suffix
		self.__server_filename = None
		self.__client_filename = None
		self.__server_file = None
		self.__client_file = None

	def tempfile(self):
		filename = mktemp(self.__file_suffix)
		with open(filename, 'w'):
			pass
		return filename

	def create_files(self):
		force_recreation = False
		if self.__server_filename is None:
			self.__server_filename = self.tempfile()
			force_recreation = True

		if self.__client_filename is None:
			self.__client_filename = self.tempfile()
			force_recreation = True

		if self.__server_file is None or force_recreation is True:
			self.__server_file = FakeBeaconTransport.FakeSocket(
				self.__server_filename, self.__client_filename
			)
		if self.__client_file is None or force_recreation is True:
			self.__client_file = FakeBeaconTransport.FakeSocket(
				self.__client_filename, self.__server_filename
			)

	def delete_files(self):
		if self.__server_file is not None:
			self.__server_file = None

		if self.__client_file is not None:
			self.__client_file = None

		if self.__server_filename is not None:
			os.unlink(self.__server_filename)
			self.__server_filename = None

		if self.__client_filename is not None:
			os.unlink(self.__client_filename)
			self.__client_filename = None

	def server_socket(self, beacon_config):
		self.__server_file.open()
		return self.__server_file

	def close_server_socket(self, beacon_config, close_fd=True):
		pass

	def client_socket(self, beacon_config):
		self.__client_file.open()
		return self.__client_file

	def close_client_socket(self, beacon_config, close_fd=True):
		pass

	def target_socket(self, beacon_config):
		return WIPV4SocketInfo('fake-host', 1)


class TestWBeacon:

	def test_beacon(self):

		class TestCallback(WNetworkBeaconCallback):
			result = []

			def __call__(self, data, source, description):
				TestCallback.result.append(str(description).encode() + b':' + data)

		fake_transport = FakeBeaconTransport('-pytest-wasp-general')
		fake_transport.create_files()
		messenger = WBeaconMessenger()
		config = WConfig()
		config.add_section('wasp-general::network::beacon')
		config['wasp-general::network::beacon']['lookup_timeout'] = '1'

		server_beacon = WNetworkServerBeacon(messenger=messenger, transport=fake_transport, callback=TestCallback())
		assert(server_beacon.handler().io_handler().process_any() is False)
		client_beacon = WNetworkClientBeacon(
			config=config, messenger=messenger, transport=fake_transport, callback=TestCallback()
		)

		assert(isinstance(server_beacon.loop(), IOLoop) is True)
		assert(isinstance(client_beacon.loop(), IOLoop) is True)

		server_thread = Thread(target=server_beacon.start)
		server_thread.start()
		client_beacon.start()
		client_beacon.stop()
		server_beacon.stop()
		server_thread.join()

		assert(TestCallback.result == [b'WDataDescription.request:HELLO', b'WDataDescription.response:HELLO'])

		assert(isinstance(WNetworkServerBeacon().handler().transport(), WBroadcastBeaconTransport) is True)
		config['wasp-general::network::beacon']['transport'] = 'multicast'
		assert(isinstance(WNetworkServerBeacon(config=config).handler().transport(), WMulticastBeaconTransport) is True)
		config['wasp-general::network::beacon']['transport'] = 'foo'
		pytest.raises(ValueError, WNetworkServerBeacon, config=config)
		config['wasp-general::network::beacon']['transport'] = 'unicast_udp'
		pytest.raises(NotImplementedError, WNetworkServerBeacon, config=config)
		config['wasp-general::network::beacon']['transport'] = 'unicast_tcp'
		pytest.raises(NotImplementedError, WNetworkServerBeacon, config=config)

		silent_messenger = WBeaconMessenger()
		silent_messenger.has_response = lambda c, r, a: False

		server_beacon = WNetworkServerBeacon(
			messenger=silent_messenger, transport=fake_transport, callback=TestCallback(),
			process_any=True
		)
		assert(server_beacon.handler().io_handler().process_any() is True)
		TestCallback.result = []
		server_thread = Thread(target=server_beacon.start)
		server_thread.start()
		client_beacon.start()
		client_beacon.stop()
		server_beacon.stop()
		server_thread.join()

		assert (TestCallback.result == [b'WDataDescription.invalid_request:HELLO'])

		fake_transport.delete_files()
