# -*- coding: utf-8 -*-

import pytest
import socket

from wasp_general.network.web.proto import WWebSessionProto
from wasp_general.network.web.session import WWebSessionAdapter


class TestWWebSessionAdapter:

	test_socket = ('127.0.0.1', 5454)

	def test_adapter(self):
		assert(issubclass(WWebSessionAdapter, WWebSessionProto) is True)
		pytest.raises(NotImplementedError, WWebSessionAdapter.accepted_socket, None)

		server_socket = socket.socket()
		server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		server_socket.bind(TestWWebSessionAdapter.test_socket)
		server_socket.listen(1)

		client_socket = socket.socket()
		client_socket.connect(TestWWebSessionAdapter.test_socket)

		accepted_socket = server_socket.accept()[0]

		class Adapter(WWebSessionAdapter):

			def accepted_socket(self):
				return accepted_socket

			def protocol_version(self):
				return '0.9'

			def protocol(self):
				return 'http'

			def read_request(self):
				pass

			def write_response(self, request, response):
				pass

			def session_close(self):
				pass

		adapter = Adapter()
		assert(str(adapter.server_address().address()) == '127.0.0.1')
		assert(int(adapter.server_address().port()) == 5454)
		assert(str(adapter.client_address().address()) == '127.0.0.1')
		assert(int(adapter.client_address().port()) == accepted_socket.getpeername()[1])

		accepted_socket.close()
		client_socket.close()
		server_socket.close()
