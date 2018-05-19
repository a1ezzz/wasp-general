# -*- coding: utf-8 -*-

import pytest

from enum import Enum
from io import BytesIO

from wasp_general.capability import WCapabilitiesHolder
from wasp_general.uri import WSchemeHandler, WURI, WSchemeSpecification
from wasp_general.network.clients.proto import WClientConnectionError, WClientCapabilityError
from wasp_general.network.clients.proto import WNetworkClientCapabilities, WNetworkClientProto


def test_exceptions():
	assert(issubclass(WClientConnectionError, Exception) is True)
	assert(issubclass(WClientCapabilityError, Exception) is True)


def test_abstract():
	pytest.raises(TypeError, WNetworkClientProto)
	pytest.raises(NotImplementedError, WNetworkClientProto.scheme_specification)
	pytest.raises(NotImplementedError, WNetworkClientProto.connect, None)
	pytest.raises(NotImplementedError, WNetworkClientProto.disconnect, None)


class TestWNetworkClientCapabilities:

	def test(self):
		assert(issubclass(WNetworkClientCapabilities, Enum) is True)

		class A(WCapabilitiesHolder):

			@WNetworkClientCapabilities.capability('cap1')
			def fun_cap1(self):
				pass

			@WNetworkClientCapabilities.capability('cap2', ValueError)
			def fun_cap2(self):
				raise TypeError

			@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.list_dir, ValueError)
			def fun_cap3(self):
				raise ValueError

		a = A()
		a('cap1')
		pytest.raises(TypeError, a, 'cap2')
		pytest.raises(WClientCapabilityError, a, WNetworkClientCapabilities.list_dir.value)

		with pytest.raises(TypeError):
			class E(WCapabilitiesHolder):

				@WNetworkClientCapabilities.capability(1)
				def fun_cap1(self):
					pass


class TestWNetworkClientProto:

	class Client(WNetworkClientProto):

		@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.list_dir)
		def fun_cap1(self):
			pass

		@classmethod
		def scheme_specification(cls):
			return WSchemeSpecification('scheme')

		def connect(self):
			pass

		def disconnect(self):
			pass

	def test(self):
		uri = WURI.parse('scheme:///')
		client = TestWNetworkClientProto.Client.create_handler(uri)
		assert(isinstance(client, WSchemeHandler) is True)
		assert(isinstance(client, WCapabilitiesHolder) is True)
		assert(client.uri() == uri)
		assert(client.directory_sep() == '/')
		assert(client.has_capabilities(WNetworkClientCapabilities.list_dir.value) is True)
		assert(client.has_capabilities(WNetworkClientCapabilities.list_dir) is True)
		assert(client.has_capabilities(WNetworkClientCapabilities.make_dir) is False)
		assert(client.has_capabilities(
			WNetworkClientCapabilities.list_dir, WNetworkClientCapabilities.make_dir
		) is False)

		client(WNetworkClientCapabilities.list_dir)
		client(WNetworkClientCapabilities.list_dir.value)

		client.capability(WNetworkClientCapabilities.list_dir)
		client.capability(WNetworkClientCapabilities.list_dir.value)

		pytest.raises(NotImplementedError, client.current_directory)
		pytest.raises(NotImplementedError, client.change_directory, '/')
		pytest.raises(NotImplementedError, client.list_directory)
		pytest.raises(NotImplementedError, client.make_directory, 'dir1')
		pytest.raises(NotImplementedError, client.remove_directory, 'dir2')
		pytest.raises(NotImplementedError, client.upload_file, 'file1', BytesIO(b''))
		pytest.raises(NotImplementedError, client.remove_file, 'file2')
