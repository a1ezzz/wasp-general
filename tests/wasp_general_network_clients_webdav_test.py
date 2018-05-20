# -*- coding: utf-8 -*-

import os
import warnings
import pytest
from webdav3.client import Client
from uuid import uuid4
from io import BytesIO

from wasp_general.uri import WURI, WURIComponentVerifier
from wasp_general.network.clients.proto import WNetworkClientCapabilities
from wasp_general.network.clients.proto import WClientCapabilityError, WClientConnectionError
from wasp_general.network.clients.virtual_dir import WVirtualDirectoryClient
from wasp_general.network.clients.webdav import WWebDavClientBase, WWebDavClient, WWebDavsClient


def test_abstract():
	pytest.raises(TypeError, WWebDavClientBase)
	pytest.raises(NotImplementedError, WWebDavClientBase.scheme_name)


class TestWWebDavClientBase:

	class Base(WWebDavClientBase):

		@classmethod
		def scheme_name(cls):
			return 'test-dav'

	def test(self):
		scheme_spec = TestWWebDavClientBase.Base.scheme_specification()
		assert(scheme_spec.scheme_name() == 'test-dav')

		assert(
			[scheme_spec.verifier(x).requirement() for x in WURI.Component] == [
				WURIComponentVerifier.Requirement.required,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.required,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.unsupported
			]
		)

		uri = WURI.parse('test-dav://hostname')
		client = TestWWebDavClientBase.Base(uri, 'proto')
		assert(isinstance(client, WVirtualDirectoryClient) is True)
		assert(isinstance(client.dav_client(), Client) is True)

		assert(client.session_path() == '/')
		client.session_path('/foo')
		assert(client.session_path() == '/foo')

		uri = WURI.parse('test-dav://user:pass@hostname:8080/?remote_path=%2Fzzz')
		client = TestWWebDavClientBase.Base(uri, 'proto')
		assert(client.session_path() == '/zzz')


class TestWWebDavsClient:

	__env_variable_name__ = 'PYTEST_WEBDAV_URI'

	__invalid_uri__ = 'davs://localhost:7227'

	def test(self):
		if TestWWebDavsClient.__env_variable_name__ not in os.environ:
			warnings.warn(
				'In order to run these tests "%s" correct environment variable must be specified' %
				TestWWebDavsClient.__env_variable_name__
			)
			return

		uri = os.environ[TestWWebDavsClient.__env_variable_name__]
		assert(WWebDavsClient.scheme_name() == 'davs')
		client = WWebDavsClient(WURI.parse(uri))

		client.connect()
		client(WNetworkClientCapabilities.list_dir)

		pytest.raises(WClientCapabilityError, client, WNetworkClientCapabilities.make_dir, '/')
		test_dir = str(uuid4())
		client(WNetworkClientCapabilities.make_dir, test_dir)
		client(WNetworkClientCapabilities.change_dir, test_dir)

		assert(client(WNetworkClientCapabilities.current_dir) == ('/' + test_dir))
		assert(client(WNetworkClientCapabilities.list_dir) == tuple())

		pytest.raises(
			WClientCapabilityError, client,
			WNetworkClientCapabilities.upload_file, '/', BytesIO(b'\x00' * 32)
		)

		client(WNetworkClientCapabilities.upload_file, 'test.file', BytesIO(b'\x00' * 32))
		assert(client(WNetworkClientCapabilities.list_dir) == ('test.file',))
		pytest.raises(WClientCapabilityError, client, WNetworkClientCapabilities.remove_file, '/')
		pytest.raises(WClientCapabilityError, client, WNetworkClientCapabilities.remove_file, 'test.file111')
		pytest.raises(WClientCapabilityError, client, WNetworkClientCapabilities.remove_dir, 'test.file')
		pytest.raises(WClientCapabilityError, client, WNetworkClientCapabilities.change_dir, 'test.file')
		pytest.raises(WClientCapabilityError, client, WNetworkClientCapabilities.change_dir, '/zzz/foo/bar')
		client(WNetworkClientCapabilities.remove_file, 'test.file')

		client(WNetworkClientCapabilities.change_dir, '/')
		client(WNetworkClientCapabilities.remove_dir, test_dir)

		client.disconnect()

		faulty_client = WWebDavsClient(WURI.parse(TestWWebDavsClient.__invalid_uri__))
		pytest.raises(WClientConnectionError, faulty_client.connect)


class TestWWebDavClient:

	def test(self):
		client = WWebDavClient(WURI.parse(TestWWebDavsClient.__invalid_uri__))
		assert(isinstance(client, WWebDavClientBase) is True)
		assert(WWebDavClient.scheme_name() == 'dav')
