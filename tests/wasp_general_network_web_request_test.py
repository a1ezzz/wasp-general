# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.primitives import WIPV4SocketInfo
from wasp_general.network.web.headers import WHTTPHeaders
from wasp_general.network.web.proto import WWebSessionProto
from wasp_general.network.web.request import WWebRequest


class TestWWebRequest:

	class Session(WWebSessionProto):

		def client_address(self):
			WIPV4SocketInfo('127.0.0.1', 65000)

		def server_address(self):
			WIPV4SocketInfo('127.0.0.1', 80)

		def protocol(self):
			return 'http'

		def protocol_version(self):
			return '0.9'

		def read_request(self):
			pass

		def write_response(self, request, response):
			pass

		def session_close(self):
			pass

	def test_request(self):
		session = TestWWebRequest.Session()
		request = WWebRequest(session, 'GET', '/foo/bar')
		assert(isinstance(request, WWebRequest) is True)
		assert(request.session() == session)
		assert(request.method() == 'GET')
		assert(request.path() == '/foo/bar')
		assert(request.headers() is None)
		assert(request.request_data() is None)

		headers1 = WHTTPHeaders(header1='value1')
		request = WWebRequest(session, 'GET', '/foo/bar', headers=headers1, request_data=b'request payload')
		assert(request.headers()['header1'] == ('value1',))
		assert(request.request_data() == b'request payload')

		request.set_headers(headers=WHTTPHeaders(header1='value2'))
		assert(request.headers()['header1'] == ('value2',))
		request.set_request_data(b'payload')
		assert(request.request_data() == b'payload')

		request = WWebRequest.parse_request_line(session, 'GET /zzz')
		assert(request.method() == 'GET')
		assert(request.path() == '/zzz')

		request = WWebRequest.parse_request_line(session, 'POST /foo HTTP/1.0')
		assert(request.method() == 'POST')
		assert(request.path() == '/foo')
		pytest.raises(ValueError, WWebRequest.parse_request_line, session, 'zzz')

		request.parse_headers('Header-X: foo\r\nHeader-Y: bar\r\n')
		assert(request.headers()['Header-X'] == ('foo',))
		assert(request.headers()['Header-Y'] == ('bar',))

		ro_request = request.ro()
		assert(ro_request.method() == 'POST')
		assert(ro_request.path() == '/foo')
		assert(ro_request.headers()['Header-X'] == ('foo',))
		assert(ro_request.headers()['Header-Y'] == ('bar',))
		pytest.raises(RuntimeError, ro_request.set_headers, WHTTPHeaders())
		pytest.raises(RuntimeError, ro_request.set_request_data, b'')
		pytest.raises(RuntimeError, ro_request.parse_headers, 'Headers-X: foo\r\n')
