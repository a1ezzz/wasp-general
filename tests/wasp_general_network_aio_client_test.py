
import asyncio
import pytest
import socket

from wasp_general.api.registry import WAPIRegistryProto
from wasp_general.uri import WURI
from wasp_general.network.aio_client import WAIONetworkClientAPIRegistry, AIONetworkClientProto, WDatagramProtocol
from wasp_general.network.aio_client import WStreamProtocol, WUDPNetworkClient, WTCPNetworkClient
from wasp_general.network.aio_client import __default_network_client_collection__


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

    pytest.raises(TypeError, WStreamProtocol)
    with pytest.raises(NotImplementedError):
        await WStreamProtocol.session_complete(None)


class TestWUDPNetworkClient:

    class UDPClientOneWay(WDatagramProtocol):

        def __init__(self):
            loop = asyncio.get_event_loop()
            self.complete = loop.create_future()

        def connection_made(self, transport):
            transport.sendto(TestWUDPNetworkClient.__test_message__)
            self.complete.set_result(None)

        async def session_complete(self):
            await self.complete

    class UDPClientTwoWay(WDatagramProtocol):

        def __init__(self):
            loop = asyncio.get_event_loop()
            self.complete = loop.create_future()

        def connection_made(self, transport):
            transport.sendto(TestWUDPNetworkClient.__test_message__)

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
            TestWUDPNetworkClient.__udp_uri__, TestWUDPNetworkClient.UDPClientOneWay
        )
        assert(isinstance(nc, AIONetworkClientProto))
        assert(isinstance(nc, WUDPNetworkClient))

    def test_network(self, event_loop):
        TestWUDPNetworkClient.__udp_client_received__ = event_loop.create_future()
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        server_socket.bind(
            (TestWUDPNetworkClient.__udp_uri__.hostname(), TestWUDPNetworkClient.__udp_uri__.port())
        )
        server_socket.setblocking(False)

        nc = __default_network_client_collection__.network_handler(
            TestWUDPNetworkClient.__udp_uri__, TestWUDPNetworkClient.UDPClientOneWay
        )
        event_loop.run_until_complete(nc.connect())

        assert(
            server_socket.recv(len(TestWUDPNetworkClient.__test_message__)) ==
            TestWUDPNetworkClient.__test_message__
        )

    def test_bind_network(self, event_loop):
        TestWUDPNetworkClient.__udp_client_received__ = event_loop.create_future()
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        server_socket.bind(
            (TestWUDPNetworkClient.__udp_uri__.hostname(), TestWUDPNetworkClient.__udp_uri__.port())
        )
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.setblocking(False)

        nc = __default_network_client_collection__.network_handler(
            TestWUDPNetworkClient.__udp_uri__, TestWUDPNetworkClient.UDPClientTwoWay,
            bind_uri=TestWUDPNetworkClient.__udp_bind_uri__
        )

        async def server_coro():
            data = await event_loop.sock_recv(server_socket, 1024)
            server_socket.sendto(
                TestWUDPNetworkClient.__response_prefix__ + data,
                (
                    TestWUDPNetworkClient.__udp_bind_uri__.hostname(),
                    TestWUDPNetworkClient.__udp_bind_uri__.port()
                )
            )

        _, client_result = event_loop.run_until_complete(asyncio.gather(server_coro(), nc.connect()))

        assert(
            client_result == (
                TestWUDPNetworkClient.__response_prefix__ + TestWUDPNetworkClient.__test_message__
            )
        )


class TestWTCPNetworkClient:

    class TCPClient(WStreamProtocol):

        def __init__(self):
            loop = asyncio.get_event_loop()
            self.complete = loop.create_future()

        def connection_made(self, transport):
            transport.write(TestWTCPNetworkClient.__test_message__)

        def data_received(self, data):
            self.complete.set_result(data)

        async def session_complete(self):
            await self.complete
            return self.complete.result()

    __test_message__ = b'test tcp message'
    __response_prefix__ = b'response:'
    __tcp_uri__ = WURI.parse('tcp://127.0.0.1:30000?reuse_addr=')
    __tcp_bind_uri__ = WURI.parse('tcp://127.0.0.1:30001?reuse_addr=')

    @pytest.mark.asyncio
    async def test(self):
        nc = __default_network_client_collection__.network_handler(
            TestWTCPNetworkClient.__tcp_uri__, TestWTCPNetworkClient.TCPClient
        )
        assert(isinstance(nc, AIONetworkClientProto))
        assert(isinstance(nc, WTCPNetworkClient))

    def test_network(self, event_loop):
        TestWTCPNetworkClient.__tcp_ = event_loop.create_future()
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        server_socket.bind(
            (TestWTCPNetworkClient.__tcp_uri__.hostname(), TestWTCPNetworkClient.__tcp_uri__.port())
        )
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.listen()
        server_socket.setblocking(False)

        async def tcp_server():
            conn, client_address = await event_loop.sock_accept(server_socket)
            server_receive = await event_loop.sock_recv(conn, 1024)
            await event_loop.sock_sendall(
                conn, TestWTCPNetworkClient.__response_prefix__ + server_receive
            )

            await asyncio.wait_for(event_loop.sock_recv(conn, 1), timeout=1)  # we should wait for bytes
            # because client should close connection before the server socket does it
            # if the server closes socket first, this socket turns to 'TIME_WAIT' mode and this leads to
            # 'address already in use' error
            return client_address

        nc = __default_network_client_collection__.network_handler(
            TestWTCPNetworkClient.__tcp_uri__, TestWTCPNetworkClient.TCPClient,
            bind_uri=TestWTCPNetworkClient.__tcp_bind_uri__
        )
        address, result = event_loop.run_until_complete(
            asyncio.gather(tcp_server(), nc.connect())
        )

        assert(address[0] == (TestWTCPNetworkClient.__tcp_bind_uri__.hostname()))
        assert(address[1] == (TestWTCPNetworkClient.__tcp_bind_uri__.port()))
        assert(result == (
                TestWTCPNetworkClient.__response_prefix__ + TestWTCPNetworkClient.__test_message__
        ))
