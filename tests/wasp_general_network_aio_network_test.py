# -*- coding: utf-8 -*-

from asyncio import BaseProtocol

from wasp_general.api.registry import WAPIRegistryProto

from wasp_general.network.aio_network import WAIONetworkAPIRegistry, __default_network_client_collection__
from wasp_general.network.aio_network import __default_network_services_collection__


class TestWAIONetworkAPIRegistry:

    class Service:

        def __init__(self, uri, protocol_cls, aio_loop=None, socket_collection=None):
            pass

    class Protocol(BaseProtocol):
        pass

    def test(self):
        registry = WAIONetworkAPIRegistry()
        assert(isinstance(registry, WAPIRegistryProto) is True)

        registry.register('raw-protocol', TestWAIONetworkAPIRegistry.Service)
        service = registry.network_handler("raw-protocol://", TestWAIONetworkAPIRegistry.Protocol)
        assert(isinstance(service, TestWAIONetworkAPIRegistry.Service) is True)

    def test_instances(self):
        assert(isinstance(__default_network_client_collection__, WAIONetworkAPIRegistry) is True)
        assert(isinstance(__default_network_services_collection__, WAIONetworkAPIRegistry) is True)
