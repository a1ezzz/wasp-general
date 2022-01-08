
import asyncio
import pytest
import socket

from wasp_general.uri import WURI
from wasp_general.api.registry import WAPIRegistryProto
from wasp_general.network.aio_protocols import WServiceStreamProtocol, WServiceDatagramProtocol
from wasp_general.network.aio_service import WAIONetworkServiceAPIRegistry, __default_network_services_collection__
from wasp_general.network.aio_service import WBaseNetworkService, AIONetworkServiceProto, WUDPNetworkService
from wasp_general.network.aio_service import WTCPNetworkService, WStreamedUnixNetworkService
from wasp_general.network.aio_service import WDatagramUnixNetworkService


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


class TestWBaseNetworkService:

    class Service(WBaseNetworkService):

        __supported_protocol__ = asyncio.DatagramProtocol

        async def start(self):
            pass

        async def stop(self):
            pass

    class Protocol(asyncio.DatagramProtocol):
        pass

    def test(self):
        TestWBaseNetworkService.Service(WURI.parse('raw-protocol://'), TestWBaseNetworkService.Protocol)
        with pytest.raises(TypeError):
            TestWBaseNetworkService.Service(WURI.parse('raw-protocol://'), TestWAIONetworkAPIRegistry.Protocol)


@pytest.mark.asyncio
async def test_abstract():
    pytest.raises(TypeError, AIONetworkServiceProto)

    with pytest.raises(NotImplementedError):
        await AIONetworkServiceProto.start(None)

    with pytest.raises(NotImplementedError):
        await AIONetworkServiceProto.stop(None)


class PyDatagramTestServer(WServiceDatagramProtocol):

    def datagram_received(self, data, addr):
        PyDatagramTestServer.__result__.set_result(data)

    __result__ = None


class PyStreamedTestServer(WServiceStreamProtocol):

    def data_received(self, data):
        PyStreamedTestServer.__result__.set_result(data)

    __result__ = None


class TestWUDPNetworkService:

    __udp_uri__ = WURI.parse('udp://127.0.0.1:30000')

    @pytest.mark.asyncio
    async def test(self):
        ns = __default_network_services_collection__.network_handler(TestWUDPNetworkService.__udp_uri__, PyDatagramTestServer)
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WUDPNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, event_loop):
        test_message = b'test udp message'

        PyDatagramTestServer.__result__ = event_loop.create_future()
        ns = __default_network_services_collection__.network_handler(TestWUDPNetworkService.__udp_uri__, PyDatagramTestServer)
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        client_socket.setblocking(False)
        client_socket.sendto(
            test_message,
            (TestWUDPNetworkService.__udp_uri__.hostname(), TestWUDPNetworkService.__udp_uri__.port())
        )

        result = event_loop.run_until_complete(PyDatagramTestServer.__result__)
        assert(result == test_message)
        event_loop.run_until_complete(ns.stop())


class TestWTCPNetworkService:

    __tcp_uri__ = WURI.parse('tcp://127.0.0.1:30000?reuse_addr=')

    @pytest.mark.asyncio
    async def test(self):
        ns = __default_network_services_collection__.network_handler(TestWTCPNetworkService.__tcp_uri__, PyStreamedTestServer)
        assert(isinstance(ns, AIONetworkServiceProto))
        assert(isinstance(ns, WTCPNetworkService))
        await ns.start()

        with pytest.raises(RuntimeError):
            await ns.start()
        await ns.stop()

    def test_network(self, event_loop):
        test_message = b'test tcp message'
        PyStreamedTestServer.__result__ = event_loop.create_future()

        ns = __default_network_services_collection__.network_handler(TestWTCPNetworkService.__tcp_uri__, PyStreamedTestServer)
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        client_socket.setblocking(False)

        async def tcp_client():
            await event_loop.sock_connect(
                client_socket,
                (TestWTCPNetworkService.__tcp_uri__.hostname(), TestWTCPNetworkService.__tcp_uri__.port())
            )

            await event_loop.sock_sendall(client_socket, test_message)

        _, result = event_loop.run_until_complete(asyncio.gather(tcp_client(), PyStreamedTestServer.__result__))
        assert(result == test_message)
        event_loop.run_until_complete(ns.stop())


class TestWStreamedUnixNetworkService:

    @pytest.mark.asyncio
    async def test(self, temp_dir):
        unix_socket_path = f'{temp_dir}/aio_test.socket'
        unix_uri = WURI.parse(f'unix://{unix_socket_path}')

        ns = __default_network_services_collection__.network_handler(unix_uri, PyStreamedTestServer)
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

        PyStreamedTestServer.__result__ = event_loop.create_future()
        ns = __default_network_services_collection__.network_handler(unix_uri, PyStreamedTestServer)
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM)
        client_socket.setblocking(False)

        async def unix_client():
            await event_loop.sock_connect(client_socket, unix_socket_path)
            await event_loop.sock_sendall(client_socket, test_message)

        _, result = event_loop.run_until_complete(
            asyncio.gather(unix_client(), PyStreamedTestServer.__result__)
        )
        assert(result == test_message)
        event_loop.run_until_complete(ns.stop())


class TestWDatagramUnixNetworkService:

    __udp_uri__ = WURI.parse('udp://127.0.0.1:30000')

    @pytest.mark.asyncio
    async def test(self, temp_dir):
        unix_socket_path = f'{temp_dir}/aio_test.socket?type=datagram'
        unix_uri = WURI.parse(f'unix://{unix_socket_path}')

        ns = __default_network_services_collection__.network_handler(unix_uri, PyDatagramTestServer)
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

        PyDatagramTestServer.__result__ = event_loop.create_future()
        ns = __default_network_services_collection__.network_handler(unix_uri, PyDatagramTestServer)
        event_loop.run_until_complete(ns.start())

        client_socket = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_DGRAM)
        client_socket.setblocking(False)
        client_socket.sendto(test_message, unix_socket_path)

        result = event_loop.run_until_complete(PyDatagramTestServer.__result__)
        assert(result == test_message)
        event_loop.run_until_complete(ns.stop())
