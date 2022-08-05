
import asyncio
import pytest
import socket

from wasp_general.uri import WURI
from wasp_general.api.registry import WAPIRegistryProto
from wasp_general.network.aio_service import WAIONetworkServiceAPIRegistry, __default_network_services_collection__
from wasp_general.network.aio_service import AIONetworkServiceProto, WUDPNetworkService, WTCPNetworkService
from wasp_general.network.aio_service import WStreamedUnixNetworkService, WDatagramUnixNetworkService


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


class PyTestServer(asyncio.Protocol, asyncio.DatagramProtocol):

    def data_received(self, data):
        PyTestServer.__result__.set_result(data)

    def datagram_received(self, data, addr):
        PyTestServer.__result__.set_result(data)

    __result__ = None


class TestWUDPNetworkService:

    __udp_uri__ = WURI.parse('udp://127.0.0.1:30000')

    @pytest.mark.asyncio
    async def test(self):
        ns = __default_network_services_collection__.network_handler(TestWUDPNetworkService.__udp_uri__, PyTestServer)
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WUDPNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, event_loop):
        test_message = b'test udp message'

        PyTestServer.__result__ = event_loop.create_future()
        ns = __default_network_services_collection__.network_handler(TestWUDPNetworkService.__udp_uri__, PyTestServer)
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        client_socket.setblocking(False)
        client_socket.sendto(
            test_message,
            (TestWUDPNetworkService.__udp_uri__.hostname(), TestWUDPNetworkService.__udp_uri__.port())
        )

        result = event_loop.run_until_complete(PyTestServer.__result__)
        assert(result == test_message)
        event_loop.run_until_complete(ns.stop())


class TestWTCPNetworkService:

    __tcp_uri__ = WURI.parse('tcp://127.0.0.1:30000?reuse_addr=')

    @pytest.mark.asyncio
    async def test(self):
        ns = __default_network_services_collection__.network_handler(TestWTCPNetworkService.__tcp_uri__, PyTestServer)
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WTCPNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, event_loop):
        test_message = b'test tcp message'
        PyTestServer.__result__ = event_loop.create_future()

        ns = __default_network_services_collection__.network_handler(TestWTCPNetworkService.__tcp_uri__, PyTestServer)
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        client_socket.setblocking(False)

        async def tcp_client():
            await event_loop.sock_connect(
                client_socket,
                (TestWTCPNetworkService.__tcp_uri__.hostname(), TestWTCPNetworkService.__tcp_uri__.port())
            )

            await event_loop.sock_sendall(client_socket, test_message)

        _, result = event_loop.run_until_complete(asyncio.gather(tcp_client(), PyTestServer.__result__))
        assert(result == test_message)
        event_loop.run_until_complete(ns.stop())


class TestWStreamedUnixNetworkService:

    @pytest.mark.asyncio
    async def test(self, temp_dir):
        unix_socket_path = f'{temp_dir}/aio_test.socket'
        unix_uri = WURI.parse(f'unix://{unix_socket_path}')

        ns = __default_network_services_collection__.network_handler(unix_uri, PyTestServer)
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WStreamedUnixNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, temp_dir, event_loop):
        unix_socket_path = f'{temp_dir}/aio_test.socket'
        unix_uri = WURI.parse(f'unix://{unix_socket_path}')
        test_message = b'test unix message'

        PyTestServer.__result__ = event_loop.create_future()
        ns = __default_network_services_collection__.network_handler(unix_uri, PyTestServer)
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM)
        client_socket.setblocking(False)

        async def unix_client():
            await event_loop.sock_connect(client_socket, unix_socket_path)
            await event_loop.sock_sendall(client_socket, test_message)

        _, result = event_loop.run_until_complete(
            asyncio.gather(unix_client(), PyTestServer.__result__)
        )
        assert(result == test_message)
        event_loop.run_until_complete(ns.stop())


class TestWDatagramUnixNetworkService:

    __udp_uri__ = WURI.parse('udp://127.0.0.1:30000')

    @pytest.mark.asyncio
    async def test(self, temp_dir):
        unix_socket_path = f'{temp_dir}/aio_test.socket?type=datagram'
        unix_uri = WURI.parse(f'unix://{unix_socket_path}')

        ns = __default_network_services_collection__.network_handler(unix_uri, PyTestServer)
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WDatagramUnixNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, temp_dir, event_loop):
        unix_socket_path = f'{temp_dir}/aio_test.socket'
        unix_uri = WURI.parse(f'unix://{unix_socket_path}?type=datagram')
        test_message = b'test unix message'

        PyTestServer.__result__ = event_loop.create_future()
        ns = __default_network_services_collection__.network_handler(unix_uri, PyTestServer)
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_DGRAM)
        client_socket.setblocking(False)
        client_socket.sendto(test_message, unix_socket_path)

        result = event_loop.run_until_complete(PyTestServer.__result__)
        assert(result == test_message)
        event_loop.run_until_complete(ns.stop())
