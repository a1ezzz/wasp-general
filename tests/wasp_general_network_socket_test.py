
import os
import pytest
import socket

from wasp_general.uri import WURI

from wasp_general.network.socket import WSocketHandlerProto, WUDPSocketHandler, WTCPSocketHandler, WUnixSocketHandler
from wasp_general.network.socket import __default_socket_collection__


def test_abstract():
	pytest.raises(TypeError, WSocketHandlerProto)
	pytest.raises(NotImplementedError, WSocketHandlerProto.uri, None)
	pytest.raises(NotImplementedError, WSocketHandlerProto.socket, None)


class TestWUDPSocketHandler:

	__message__ = b'000111222333'

	def test(self):
		assert(issubclass(WUDPSocketHandler, WSocketHandlerProto) is True)

		uri = WURI.parse("udp://127.0.0.1:3333")
		h = WUDPSocketHandler.create_handler(uri)
		assert(h.uri() == uri)
		s = h.socket()
		assert(isinstance(s, socket.socket) is True)

		uri = WURI.parse("udp://127.0.0.1:3333?multicast=")
		pytest.raises(ValueError, WUDPSocketHandler.create_handler, uri)

		uri = WURI.parse("udp://224.0.0.1:3333?multicast=")
		h = WUDPSocketHandler.create_handler(uri)

	def test_connection(self):
		uri = WURI.parse("udp://127.0.0.1:3333")
		h1 = WUDPSocketHandler.create_handler(uri)
		s1 = h1.socket()

		h2 = WUDPSocketHandler.create_handler(uri)
		s2 = h2.socket()

		s1.bind((uri.hostname(), uri.port()))

		s2.sendto(self.__message__, (uri.hostname(), uri.port()))
		m = s1.recv(len(self.__message__))
		assert(m == self.__message__)

		s1.close()
		s2.close()


class TestWTCPSocketHandler:

	__message__ = b'000111222333'

	def test(self):
		assert(issubclass(WTCPSocketHandler, WSocketHandlerProto) is True)

		uri = WURI.parse("tcp://127.0.0.1:3333")
		h = WTCPSocketHandler.create_handler(uri)
		assert(h.uri() == uri)
		s = h.socket()
		assert(isinstance(s, socket.socket) is True)

	def test_connection(self):
		uri = WURI.parse("tcp://127.0.0.1:3333")
		h1 = WTCPSocketHandler.create_handler(uri)
		s1 = h1.socket()

		h2 = WTCPSocketHandler.create_handler(uri)
		s2 = h2.socket()

		s1.bind((uri.hostname(), uri.port()))
		s1.listen(0)

		s2.connect((uri.hostname(), uri.port()))
		s2.send(self.__message__)

		client_conn, addr = s1.accept()
		m = client_conn.recv(len(self.__message__))
		assert(m == self.__message__)

		s1.close()
		s2.close()


class TestWUnixSocketHandler:

	__message__ = b'000111222333'

	def test(self):
		assert(issubclass(WUnixSocketHandler, WSocketHandlerProto) is True)

		uri = WURI.parse("unix:///")
		h = WUnixSocketHandler.create_handler(uri)
		assert(h.uri() == uri)
		s = h.socket()
		assert(isinstance(s, socket.socket) is True)

	def test_stream_connection(self, tmpdir):
		p = os.path.join(str(tmpdir.dirpath()), 'test.stream.socket')

		uri = WURI.parse("unix:///" + p)
		h1 = WUnixSocketHandler.create_handler(uri)
		s1 = h1.socket()

		h2 = WUnixSocketHandler.create_handler(uri)
		s2 = h2.socket()

		s1.bind(p)
		s1.listen(0)

		s2.connect(p)
		s2.send(self.__message__)
		client_conn, addr = s1.accept()
		m = client_conn.recv(len(self.__message__))
		assert(m == self.__message__)

		s1.detach()

		s1.close()
		s2.close()

	def test_datagram_connection(self, tmpdir):
		p = os.path.join(str(tmpdir.dirpath()), 'test.datagram.socket')

		uri = WURI.parse("unix:///%s?type=datagram" % p)
		h1 = WUnixSocketHandler.create_handler(uri)
		s1 = h1.socket()

		h2 = WUnixSocketHandler.create_handler(uri)
		s2 = h2.socket()

		s1.bind(p)

		s2.sendto(self.__message__, p)
		m = s1.recv(len(self.__message__))
		assert(m == self.__message__)

		s1.close()
		s2.close()


def test_default_collection():

	h = __default_socket_collection__.open(WURI.parse('udp://127.0.0.1:3333'))
	assert(isinstance(h, WUDPSocketHandler) is True)

	s = __default_socket_collection__.aio_socket('udp://127.0.0.1:3333')
	assert(isinstance(s, socket.socket) is True)
	assert(s.getblocking() is False)

	h = __default_socket_collection__.open(WURI.parse('tcp://127.0.0.1:3333'))
	assert(isinstance(h, WTCPSocketHandler) is True)

	s = __default_socket_collection__.aio_socket('tcp://127.0.0.1:3333')
	assert(isinstance(s, socket.socket) is True)
	assert(s.getblocking() is False)

	h = __default_socket_collection__.open(WURI.parse('unix:///'))
	assert(isinstance(h, WUnixSocketHandler) is True)

	s = __default_socket_collection__.aio_socket('unix:///')
	assert(isinstance(s, socket.socket) is True)
	assert(s.getblocking() is False)
