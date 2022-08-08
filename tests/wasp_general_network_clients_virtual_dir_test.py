# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.clients.proto import WNetworkClientProto
from wasp_general.network.clients.virtual_dir import WVirtualDirectoryClient
from wasp_general.uri import WURI, WSchemeSpecification


def test_abstract():
	pytest.raises(TypeError, WVirtualDirectoryClient)
	pytest.raises(NotImplementedError, WVirtualDirectoryClient.scheme_specification)
	pytest.raises(NotImplementedError, WVirtualDirectoryClient.connect, None)
	pytest.raises(NotImplementedError, WVirtualDirectoryClient.disconnect, None)


class TestWVirtualDirectoryClient:

	class Client(WVirtualDirectoryClient):

		@classmethod
		def scheme_specification(cls):
			return WSchemeSpecification('scheme')

		def connect(self):
			pass

		def disconnect(self):
			pass

	def test(self):
		client = TestWVirtualDirectoryClient.Client(WURI())
		assert(isinstance(client, WVirtualDirectoryClient) is True)
		assert(isinstance(client, WNetworkClientProto) is True)

		assert(client.start_path() == client.directory_sep())
		assert(client.normalize_path('//tmp/foo//bar///') == '/tmp/foo/bar/')
		assert(client.normalize_path('/tmp/foo/bar') == '/tmp/foo/bar')
		assert(client.join_path('/', '/tmp/', '//foo/bar/zzz//') == '/tmp/foo/bar/zzz/')

		assert(client.session_path() == '/')
		assert(client.full_path() == '/')

		assert(client.session_path('foo'))
		assert(client.session_path() == '/foo')
		assert(client.full_path() == '/foo')

		assert(client.session_path('bar/'))
		assert(client.session_path() == '/foo/bar/')
		assert(client.full_path() == '/foo/bar/')

		assert(client.session_path('zzz'))
		assert(client.session_path() == '/foo/bar/zzz')
		assert(client.full_path() == '/foo/bar/zzz')

		assert(client.session_path('/tmp'))
		assert(client.session_path() == '/tmp')
		assert(client.full_path() == '/tmp')

		client = TestWVirtualDirectoryClient.Client(WURI(), start_path='/tmp/foo//bar/')
		assert(client.start_path() == '/tmp/foo/bar/')
		assert(client.session_path() == '/')
		assert(client.full_path() == '/tmp/foo/bar/')

		assert(client.session_path('foo'))
		assert(client.session_path() == '/foo')
		assert(client.full_path() == '/tmp/foo/bar/foo')

		assert(client.session_path('bar/'))
		assert(client.session_path() == '/foo/bar/')
		assert(client.full_path() == '/tmp/foo/bar/foo/bar/')

		assert(client.session_path('zzz'))
		assert(client.session_path() == '/foo/bar/zzz')
		assert(client.full_path() == '/tmp/foo/bar/foo/bar/zzz')

		assert(client.session_path('/tmp'))
		assert(client.session_path() == '/tmp')
		assert(client.full_path() == '/tmp/foo/bar/tmp')
