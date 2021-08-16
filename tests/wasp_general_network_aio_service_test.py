
import asyncio
import pytest
import socket

from wasp_general.uri import WURI
from wasp_general.api.registry import WAPIRegistryProto
from wasp_general.network.aio_service import WAIONetworkServiceAPIRegistry, __default_network_services_collection__
from wasp_general.network.aio_service import AIONetworkServiceProto, WUDPNetworkService, WTCPNetworkService


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


class TestWUDPNetworkService:

    class UDPServer(asyncio.DatagramProtocol):

        def datagram_received(self, data, addr):
            TestWUDPNetworkService.__udp_server_received__.set_result(data)

    __udp_uri__ = WURI.parse('udp://127.0.0.1:30000')
    __udp_server_received__ = None

    @pytest.mark.asyncio
    async def test(self):
        ns = __default_network_services_collection__.network_handler(
            TestWUDPNetworkService.__udp_uri__, TestWUDPNetworkService.UDPServer
        )
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WUDPNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, event_loop):
        test_message = b'test udp message'

        TestWUDPNetworkService.__udp_server_received__ = event_loop.create_future()

        ns = __default_network_services_collection__.network_handler(
            TestWUDPNetworkService.__udp_uri__, TestWUDPNetworkService.UDPServer
        )
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        client_socket.setblocking(False)
        client_socket.sendto(
            test_message,
            (TestWUDPNetworkService.__udp_uri__.hostname(), TestWUDPNetworkService.__udp_uri__.port())
        )

        event_loop.run_until_complete(TestWUDPNetworkService.__udp_server_received__)
        assert(TestWUDPNetworkService.__udp_server_received__.result() == test_message)
        event_loop.run_until_complete(ns.stop())


class TestWTCPNetworkService:

    class TCPServer(asyncio.Protocol):

        def data_received(self, data):
            TestWTCPNetworkService.__tcp_server_received__.set_result(data)

    __tcp_uri__ = WURI.parse('tcp://127.0.0.1:30000?reuse_addr=')
    __tcp_server_received__ = None

    @pytest.mark.asyncio
    async def test(self):
        ns = __default_network_services_collection__.network_handler(
            TestWTCPNetworkService.__tcp_uri__, TestWTCPNetworkService.TCPServer
        )
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WTCPNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, event_loop):
        test_message = b'test tcp message'
        TestWTCPNetworkService.__tcp_server_received__ = event_loop.create_future()

        ns = __default_network_services_collection__.network_handler(
            TestWTCPNetworkService.__tcp_uri__, TestWTCPNetworkService.TCPServer
        )
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        client_socket.setblocking(False)

        async def tcp_client():
            await event_loop.sock_connect(
                client_socket,
                (TestWTCPNetworkService.__tcp_uri__.hostname(), TestWTCPNetworkService.__tcp_uri__.port())
            )

            await event_loop.sock_sendall(client_socket, test_message)

        event_loop.run_until_complete(
            asyncio.gather(tcp_client(), TestWTCPNetworkService.__tcp_server_received__)
        )
        assert(TestWTCPNetworkService.__tcp_server_received__.result() == test_message)
        event_loop.run_until_complete(ns.stop())
