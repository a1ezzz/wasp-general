# -*- coding: utf-8 -*-

import os
import warnings
import pytest
from uuid import uuid4
from io import BytesIO

from wasp_general.uri import WURI, WURIComponentVerifier
from wasp_general.network.clients.proto import WNetworkClientProto, WNetworkClientCapabilities
from wasp_general.network.clients.proto import WClientCapabilityError, WClientConnectionError
from wasp_general.network.clients.ftp import WFTPClient


class TestWFTPClient:

	__env_variable_name__ = 'PYTEST_FTP_URI'

	__invalid_uri__ = 'ftp://localhost:7227'

	def test_spec(self):
		scheme_spec = WFTPClient.scheme_specification()
		assert(scheme_spec.scheme_name() == 'ftp')

		assert(
			[scheme_spec.verifier(x).requirement() for x in WURI.Component] == [
				WURIComponentVerifier.Requirement.required,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.required,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported
			]
		)

	def test(self):
		if TestWFTPClient.__env_variable_name__ not in os.environ:
			warnings.warn(
				'In order to run these tests "%s" correct environment variable must be specified' %
				TestWFTPClient.__env_variable_name__
			)
			return

		uri = os.environ[TestWFTPClient.__env_variable_name__]
		uri = WURI.parse(uri)
		uri.reset_component(WURI.Component.path)  # force path to be undefined
		client = WFTPClient(uri)
		assert(isinstance(client, WNetworkClientProto) is True)

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

		faulty_client = WFTPClient(WURI.parse(TestWFTPClient.__invalid_uri__))
		pytest.raises(WClientConnectionError, faulty_client.connect)

		uri.component(WURI.Component.path, value='/zzz/foo/bar')
		faulty_client = WFTPClient(uri)
		pytest.raises(WClientConnectionError, faulty_client.connect)
