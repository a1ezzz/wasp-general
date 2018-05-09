# -*- coding: utf-8 -*-

import os
import warnings
import pytest
from webdav3.client import Client
from uuid import uuid4
from io import BytesIO

from wasp_general.uri import WURI, WURIComponentVerifier
from wasp_general.network.clients.base import WCommonNetworkClientCapability, WBasicNetworkClientProto
from wasp_general.network.clients.webdav import WWebDavClientBase, WWebDavClient, WWebDavsClient
from wasp_general.network.clients.webdav import WWebDavClientListDirCapability, WWebDavClientMakeDirCapability
from wasp_general.network.clients.webdav import WWebDavCurrentDirCapability, WWebDavChangeDirCapability
from wasp_general.network.clients.webdav import WWebDavClientUploadFileCapability, WWebDavClientRemoveFileCapability


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

		caps = TestWWebDavClientBase.Base.agent_capabilities()
		assert(WWebDavClientListDirCapability in caps)
		assert(WWebDavClientMakeDirCapability in caps)
		assert(WWebDavCurrentDirCapability in caps)
		assert(WWebDavChangeDirCapability in caps)
		assert(WWebDavClientUploadFileCapability in caps)
		assert(WWebDavClientRemoveFileCapability in caps)

		uri = WURI.parse('test-dav://hostname')
		client = TestWWebDavClientBase.Base(uri, 'proto')
		assert(isinstance(client, WBasicNetworkClientProto) is True)
		assert(isinstance(client.dav_client(), Client) is True)

		assert(client.session_path() == '/')
		client.session_path('/foo')
		assert(client.session_path() == '/foo')

		uri = WURI.parse('test-dav://user:pass@hostname:8080/?remote_path=%2Fzzz')
		client = TestWWebDavClientBase.Base(uri, 'proto')
		assert(client.session_path() == '/zzz')

		client._close()  # this function does not do anything. check that function call gives no error


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
		assert(client.request(WCommonNetworkClientCapability.list_dir) is not None)  # just connection check

		assert(client.request(WCommonNetworkClientCapability.make_dir, '/') is False)
		test_dir = str(uuid4())
		assert(client.request(WCommonNetworkClientCapability.make_dir, test_dir) is True)
		assert(client.request(WCommonNetworkClientCapability.change_dir, test_dir) is True)

		assert(client.request(WCommonNetworkClientCapability.current_dir) == ('/' + test_dir))
		assert(client.request(WCommonNetworkClientCapability.list_dir) == tuple())
		assert(client.request(WCommonNetworkClientCapability.upload_file, '/', BytesIO(b'\x00' * 32)) is False)
		assert(client.request(WCommonNetworkClientCapability.upload_file, 'test.file', BytesIO(b'\x00' * 32)) is True)
		assert(client.request(WCommonNetworkClientCapability.list_dir) == ('test.file', ))
		assert(client.request(WCommonNetworkClientCapability.remove_file, '/') is False)
		assert(client.request(WCommonNetworkClientCapability.remove_file, 'test.file111') is False)
		assert(client.request(WCommonNetworkClientCapability.remove_dir, 'test.file') is False)
		assert(client.request(WCommonNetworkClientCapability.change_dir, 'test.file') is False)
		assert(client.request(WCommonNetworkClientCapability.remove_file, 'test.file') is True)

		assert(client.request(WCommonNetworkClientCapability.change_dir, '/') is True)
		assert(client.request(WCommonNetworkClientCapability.remove_dir, test_dir) is True)
		assert(client.request(WCommonNetworkClientCapability.remove_dir, '/') is False)
		assert(client.request(WCommonNetworkClientCapability.change_dir, '/zzz/foo/bar') is False)

		faulty_client = WWebDavsClient(WURI.parse(TestWWebDavsClient.__invalid_uri__))
		assert(faulty_client.request(WCommonNetworkClientCapability.list_dir) is None)
