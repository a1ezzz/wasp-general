
import asyncio
import pytest
import socket

from wasp_general.uri import WURI
from wasp_general.api.registry import WAPIRegistryProto
from wasp_general.network.aio_service import WAIONetworkServiceAPIRegistry, __default_network_services_collection__
from wasp_general.network.aio_service import AIONetworkServiceProto, WDatagramNetworkService


class TestWAIONetworkAPIRegistry:

    class Service:

        def __init__(self, uri, protocol_cls, aio_loop=None, socket_collection=None):
            pass

    class Protocol(asyncio.BaseProtocol):
        pass

    def test(self):
        registry = WAIONetworkServiceAPIRegistry()
        assert(isinstance(registry, WAPIRegistryProto) is True)

        registry.register('raw-protocol', TestWAIONetworkAPIRegistry.Service)
        service = registry.network_handler("raw-protocol://", TestWAIONetworkAPIRegistry.Protocol)
        assert(isinstance(service, TestWAIONetworkAPIRegistry.Service) is True)


@pytest.mark.asyncio
async def test_abstract():
    pytest.raises(TypeError, AIONetworkServiceProto)

    with pytest.raises(NotImplementedError):
        await AIONetworkServiceProto.start(None)

    with pytest.raises(NotImplementedError):
        await AIONetworkServiceProto.stop(None)


class TestWDatagramNetworkService:

    class UDPServer(asyncio.DatagramProtocol):

        def datagram_received(self, data, addr):
            TestWDatagramNetworkService.__udp_server_received__.set_result(data)

    __udp_uri__ = WURI.parse('udp://127.0.0.1:30000')
    __udp_server_received__ = None

    @pytest.mark.asyncio
    async def test(self):
        ns = __default_network_services_collection__.network_handler(
            TestWDatagramNetworkService.__udp_uri__, TestWDatagramNetworkService.UDPServer
        )
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WDatagramNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, event_loop):
        test_message = b'test udp message'

        TestWDatagramNetworkService.__udp_server_received__ = event_loop.create_future()

        ns = __default_network_services_collection__.network_handler(
            TestWDatagramNetworkService.__udp_uri__, TestWDatagramNetworkService.UDPServer
        )
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        client_socket.sendto(
            test_message,
            (TestWDatagramNetworkService.__udp_uri__.hostname(), TestWDatagramNetworkService.__udp_uri__.port())
        )
        client_socket.setblocking(False)

        event_loop.run_until_complete(TestWDatagramNetworkService.__udp_server_received__)
        assert(TestWDatagramNetworkService.__udp_server_received__.result() == test_message)
        event_loop.run_until_complete(ns.stop())
