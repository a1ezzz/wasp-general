# -*- coding: utf-8 -*-

import pytest
from uuid import uuid4
from io import BytesIO

from wasp_general.uri import WURI, WURIComponentVerifier
from wasp_general.network.clients.proto import WNetworkClientCapabilities
from wasp_general.network.clients.proto import WClientCapabilityError, WClientConnectionError
from wasp_general.network.clients.file import WLocalFileClient


class TestWLocalFileClient:

	def test_spec(self):
		scheme_spec = WLocalFileClient.scheme_specification()
		assert(scheme_spec.scheme_name() == 'file')

		assert(
			[scheme_spec.verifier(x).requirement() for x in WURI.Component] == [
				WURIComponentVerifier.Requirement.required,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported
			]
		)

	def test(self, temp_dir):
		uri = 'file:///' + temp_dir

		client = WLocalFileClient(WURI.parse(uri))

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

		faulty_client = WLocalFileClient(WURI.parse('file:///tmp/foo/bar/zzz'))
		pytest.raises(WClientConnectionError, faulty_client.connect)
