
import asyncio
import pytest
import socket

from wasp_general.uri import WURI
from wasp_general.network.aio_service import AIONetworkServiceProto, WDatagramNetworkService
from wasp_general.network.aio_network import __default_network_services_collection__


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

        event_loop = asyncio.get_event_loop()
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

        event_loop.run_until_complete(TestWDatagramNetworkService.__udp_server_received__)
        assert(TestWDatagramNetworkService.__udp_server_received__.result() == test_message)
        event_loop.run_until_complete(ns.stop())
