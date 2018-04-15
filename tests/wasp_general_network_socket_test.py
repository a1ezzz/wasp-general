# -*- coding: utf-8 -*-

import pytest
import socket

from wasp_general.config import WConfig
from wasp_general.network.socket import WSocketFactoryItemProto, WTCPUDPSocketFactoryItem, WTCPSocketFactoryItem
from wasp_general.network.socket import WUDPSocketFactoryItem, WSocketFactory
from wasp_general.uri import WURI, WSchemeHandler, WSchemeSpecification, WSchemeCollection


def test_abstract():

	pytest.raises(TypeError, WSocketFactoryItemProto)
	pytest.raises(NotImplementedError, WSocketFactoryItemProto.create_handler, WURI())

	pytest.raises(TypeError, WTCPUDPSocketFactoryItem)
	pytest.raises(NotImplementedError, WTCPUDPSocketFactoryItem.protocol)
	pytest.raises(NotImplementedError, WTCPUDPSocketFactoryItem.socket_type)


class TestWSocketFactoryItemProto:

	class FactoryItem(WSocketFactoryItemProto):

		@classmethod
		def create_handler(cls, uri, *args, config_selection=None, socket_obj=None, **kwargs):
			return cls(socket_obj if socket_obj is not None else socket.socket())

		@classmethod
		def scheme_specification(cls):
			return

	def test(self):
		s = socket.socket()
		factory_item = TestWSocketFactoryItemProto.FactoryItem.create_handler(WURI(), socket_obj=s)
		assert(isinstance(factory_item, WSocketFactoryItemProto) is True)
		assert(isinstance(factory_item, WSchemeHandler) is True)
		assert(factory_item.socket() == s)


class TestWTCPUDPSocketFactoryItem:

	class FactoryItem(WTCPUDPSocketFactoryItem):

		@classmethod
		def protocol(cls):
			return 'tcp'

		@classmethod
		def socket_type(cls):
			return socket.SOCK_STREAM

	class EnhancedFactoryItem(FactoryItem):

		@classmethod
		def default_port(cls):
			return 20202

	def test(self):
		assert(WTCPUDPSocketFactoryItem.default_port() == -1)

		scheme_spec = TestWTCPUDPSocketFactoryItem.FactoryItem.scheme_specification()
		assert(isinstance(scheme_spec, WSchemeSpecification) is True)
		assert(scheme_spec.scheme_name() == 'tcp')
		assert(
			[x for x in scheme_spec] == [
				(WURI.Component.scheme, WSchemeSpecification.ComponentDescriptor.required),
				(WURI.Component.username, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.password, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.hostname, WSchemeSpecification.ComponentDescriptor.optional),
				(WURI.Component.port, WSchemeSpecification.ComponentDescriptor.optional),
				(WURI.Component.path, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.query, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.fragment, WSchemeSpecification.ComponentDescriptor.unsupported)
			]
		)

		factory_item = TestWTCPUDPSocketFactoryItem.FactoryItem.create_handler(WURI())
		assert(isinstance(factory_item, WTCPUDPSocketFactoryItem) is True)
		assert(isinstance(factory_item, WSocketFactoryItemProto) is True)

		sock = factory_item.socket()
		assert(isinstance(sock, socket.socket) is True)
		assert(sock.type == socket.SOCK_STREAM)
		assert(sock.getsockname() == ('0.0.0.0', 0))
		assert(sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 0)

		factory_item = TestWTCPUDPSocketFactoryItem.FactoryItem.create_handler(WURI.parse('tcp://127.0.0.1'))
		sock = factory_item.socket()
		assert(sock.getsockname() == ('0.0.0.0', 0))

		factory_item = TestWTCPUDPSocketFactoryItem.FactoryItem.create_handler(
			WURI.parse('tcp://127.0.0.1:10101')
		)
		assert(factory_item.socket().getsockname() == ('127.0.0.1', 10101))

		factory_item = TestWTCPUDPSocketFactoryItem.EnhancedFactoryItem.create_handler(
			WURI.parse('tcp://127.0.0.1:20202')
		)
		assert(factory_item.socket().getsockname() == ('127.0.0.1', 20202))

		factory_item = TestWTCPUDPSocketFactoryItem.FactoryItem.create_handler(WURI.parse('tcp://:10101'))
		assert(factory_item.socket().getsockname() == ('0.0.0.0', 10101))

		cfg = WConfig()
		cfg.add_section('section')
		cfg['section']['sock.reuseaddr'] = 'yes'

		factory_item = TestWTCPUDPSocketFactoryItem.FactoryItem.create_handler(
			WURI(), config_selection=cfg.select_options('section', 'sock')
		)
		assert(factory_item.socket().getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 1)


class TestWTCPSocketFactoryItem:

	def test(self):
		assert(issubclass(WTCPSocketFactoryItem, WTCPUDPSocketFactoryItem) is True)
		assert(WTCPSocketFactoryItem.protocol() == 'tcp')
		assert(WTCPSocketFactoryItem.socket_type() == socket.SOCK_STREAM)


class TestWUDPSocketFactoryItem:

	def test(self):
		assert(issubclass(WUDPSocketFactoryItem, WTCPUDPSocketFactoryItem) is True)
		assert(WUDPSocketFactoryItem.protocol() == 'udp')
		assert(WUDPSocketFactoryItem.socket_type() == socket.SOCK_DGRAM)


class TestWSocketFactory:

	def test(self):
		pytest.raises(NotImplementedError, WSocketFactory.open, None, WURI())

		socket_factory = WSocketFactory()
		assert(isinstance(socket_factory, WSocketFactory) is True)
		assert(isinstance(socket_factory, WSchemeCollection) is True)

		factory_item = socket_factory.create_socket(WURI.parse('tcp://'))
		assert(isinstance(factory_item, WTCPSocketFactoryItem) is True)

		factory_item = socket_factory.create_socket(WURI.parse('udp://'))
		assert(isinstance(factory_item, WUDPSocketFactoryItem) is True)
