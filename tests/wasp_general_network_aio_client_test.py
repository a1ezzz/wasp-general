
import asyncio
import pytest
import socket

from wasp_general.uri import WURI
from wasp_general.network.aio_client import AIONetworkClientProto, WDatagramProtocol, WDatagramNetworkClient
from wasp_general.network.aio_network import __default_network_client_collection__


@pytest.mark.asyncio
async def test_abstract():
    pytest.raises(TypeError, AIONetworkClientProto)

    with pytest.raises(NotImplementedError):
        await AIONetworkClientProto.connect(None)

    pytest.raises(TypeError, WDatagramProtocol)

    with pytest.raises(NotImplementedError):
        await WDatagramProtocol.session_complete(None)


class TestWDatagramNetworkClient:

    class UDPClient(WDatagramProtocol):

        def __init__(self):
            loop = asyncio.get_event_loop()
            self.complete = loop.create_future()

        def connection_made(self, transport):
            transport.sendto(TestWDatagramNetworkClient.__test_message__)
            self.complete.set_result(None)

        async def session_complete(self):
            await self.complete

    __test_message__ = b'test udp message'
    __udp_uri__ = WURI.parse('udp://127.0.0.1:30000')

    @pytest.mark.asyncio
    async def test(self):
        nc = __default_network_client_collection__.network_handler(
            TestWDatagramNetworkClient.__udp_uri__, TestWDatagramNetworkClient.UDPClient
        )
        assert(isinstance(nc, AIONetworkClientProto))
        assert(isinstance(nc, WDatagramNetworkClient))

    def test_network(self, event_loop):
        TestWDatagramNetworkClient.__udp_client_received__ = event_loop.create_future()
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        server_socket.bind(
            (TestWDatagramNetworkClient.__udp_uri__.hostname(), TestWDatagramNetworkClient.__udp_uri__.port())
        )

        nc = __default_network_client_collection__.network_handler(
            TestWDatagramNetworkClient.__udp_uri__, TestWDatagramNetworkClient.UDPClient
        )
        event_loop.run_until_complete(nc.connect())

        assert(
            server_socket.recv(len(TestWDatagramNetworkClient.__test_message__)) ==
            TestWDatagramNetworkClient.__test_message__
        )
