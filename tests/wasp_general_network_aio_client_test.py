
import asyncio
import pytest
import socket

from wasp_general.api.registry import WAPIRegistryProto
from wasp_general.uri import WURI
from wasp_general.network.aio_client import WAIONetworkClientAPIRegistry, AIONetworkClientProto, WDatagramProtocol
from wasp_general.network.aio_client import WDatagramNetworkClient, __default_network_client_collection__


class TestWAIONetworkClientAPIRegistry:

    class Service:

        def __init__(self, uri, protocol_cls, bind_uri=None, aio_loop=None, socket_collection=None):
            pass

    class Protocol(asyncio.BaseProtocol):
        pass

    def test(self):
        registry = WAIONetworkClientAPIRegistry()
        assert(isinstance(registry, WAPIRegistryProto) is True)

        registry.register('raw-protocol', TestWAIONetworkClientAPIRegistry.Service)
        service = registry.network_handler(
            'raw-protocol://', TestWAIONetworkClientAPIRegistry.Protocol, bind_uri='raw-protocol://'
        )
        assert(isinstance(service, TestWAIONetworkClientAPIRegistry.Service) is True)

        assert(isinstance(__default_network_client_collection__, WAIONetworkClientAPIRegistry) is True)


@pytest.mark.asyncio
async def test_abstract():
    pytest.raises(TypeError, AIONetworkClientProto)

    with pytest.raises(NotImplementedError):
        await AIONetworkClientProto.connect(None)

    pytest.raises(TypeError, WDatagramProtocol)

    with pytest.raises(NotImplementedError):
        await WDatagramProtocol.session_complete(None)


class TestWDatagramNetworkClient:

    class UDPClientOneWay(WDatagramProtocol):

        def __init__(self):
            loop = asyncio.get_event_loop()
            self.complete = loop.create_future()

        def connection_made(self, transport):
            transport.sendto(TestWDatagramNetworkClient.__test_message__)
            self.complete.set_result(None)

        async def session_complete(self):
            await self.complete

    class UDPClientTwoWay(WDatagramProtocol):

        def __init__(self):
            loop = asyncio.get_event_loop()
            self.complete = loop.create_future()

        def connection_made(self, transport):
            transport.sendto(TestWDatagramNetworkClient.__test_message__)

        def datagram_received(self, data, addr):
            self.complete.set_result(data)

        async def session_complete(self):
            await self.complete
            return self.complete.result()

    __test_message__ = b'test udp message'
    __response_prefix__ = b'response:'
    __udp_uri__ = WURI.parse('udp://127.0.0.1:30000')
    __udp_bind_uri__ = WURI.parse('udp://127.0.0.1:30001')

    @pytest.mark.asyncio
    async def test(self):
        nc = __default_network_client_collection__.network_handler(
            TestWDatagramNetworkClient.__udp_uri__, TestWDatagramNetworkClient.UDPClientOneWay
        )
        assert(isinstance(nc, AIONetworkClientProto))
        assert(isinstance(nc, WDatagramNetworkClient))

    def test_network(self, event_loop):
        TestWDatagramNetworkClient.__udp_client_received__ = event_loop.create_future()
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        server_socket.bind(
            (TestWDatagramNetworkClient.__udp_uri__.hostname(), TestWDatagramNetworkClient.__udp_uri__.port())
        )
        server_socket.setblocking(False)

        nc = __default_network_client_collection__.network_handler(
            TestWDatagramNetworkClient.__udp_uri__, TestWDatagramNetworkClient.UDPClientOneWay
        )
        event_loop.run_until_complete(nc.connect())

        assert(
            server_socket.recv(len(TestWDatagramNetworkClient.__test_message__)) ==
            TestWDatagramNetworkClient.__test_message__
        )

    def test_bind_network(self, event_loop):
        TestWDatagramNetworkClient.__udp_client_received__ = event_loop.create_future()
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        server_socket.bind(
            (TestWDatagramNetworkClient.__udp_uri__.hostname(), TestWDatagramNetworkClient.__udp_uri__.port())
        )
        server_socket.setblocking(False)

        nc = __default_network_client_collection__.network_handler(
            TestWDatagramNetworkClient.__udp_uri__, TestWDatagramNetworkClient.UDPClientTwoWay,
            bind_uri=TestWDatagramNetworkClient.__udp_bind_uri__
        )

        async def server_coro():
            data = await event_loop.sock_recv(server_socket, 1024)
            server_socket.sendto(
                TestWDatagramNetworkClient.__response_prefix__ + data,
                (
                    TestWDatagramNetworkClient.__udp_bind_uri__.hostname(),
                    TestWDatagramNetworkClient.__udp_bind_uri__.port()
                )
            )

        _, client_result = event_loop.run_until_complete(asyncio.gather(server_coro(), nc.connect()))

        assert(
            client_result == (
                TestWDatagramNetworkClient.__response_prefix__ + TestWDatagramNetworkClient.__test_message__
            )
        )
