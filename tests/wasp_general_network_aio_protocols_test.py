import asyncio
import pytest

from wasp_general.network.aio_protocols import WGeneralProtocol, WClientProtocol, WClientDatagramProtocol
from wasp_general.network.aio_protocols import WClientStreamProtocol, WServiceDatagramProtocol, WServiceStreamProtocol


def test_hierarchy():
    assert(issubclass(WClientDatagramProtocol, asyncio.DatagramProtocol))
    assert(issubclass(WClientDatagramProtocol, WClientProtocol))

    assert(issubclass(WClientStreamProtocol, asyncio.Protocol))
    assert(issubclass(WClientStreamProtocol, WClientProtocol))

    assert(issubclass(WServiceDatagramProtocol, asyncio.DatagramProtocol))
    assert(issubclass(WServiceDatagramProtocol, WGeneralProtocol))

    assert(issubclass(WServiceStreamProtocol, asyncio.Protocol))
    assert(issubclass(WServiceStreamProtocol, WGeneralProtocol))


class TestWGeneralProtocol:

    @pytest.mark.asyncio
    async def test(self):
        protocol = WGeneralProtocol()
        assert(isinstance(protocol, WGeneralProtocol) is True)
        assert(isinstance(protocol, asyncio.BaseProtocol) is True)
        assert(protocol._aio_loop is None)
        assert(protocol._transport is None)

        transport = asyncio.BaseTransport()
        protocol.connection_made(transport)
        assert(protocol._transport is transport)
        protocol.connection_lost(ValueError('!'))
        assert(protocol._transport is None)

        loop = asyncio.get_event_loop()
        protocol = WGeneralProtocol.protocol(loop)
        assert(isinstance(protocol, WGeneralProtocol) is True)
        assert(protocol._aio_loop is loop)


class TestWClientProtocol:

    @pytest.mark.asyncio
    async def test(self):
        protocol = WClientProtocol()
        assert(isinstance(protocol, WClientProtocol) is True)
        assert(isinstance(protocol, WGeneralProtocol) is True)
        assert(protocol._request_complete is None)
        assert(protocol._remote_address is None)

        loop = asyncio.get_event_loop()
        unix_skt = '/foo/bar'
        protocol = WClientProtocol.protocol(loop, remote_address=unix_skt)
        assert(isinstance(protocol, WClientProtocol) is True)
        assert(protocol._aio_loop is loop)
        assert(asyncio.isfuture(protocol._request_complete) is True)
        assert(protocol._request_complete.done() is False)
        assert(protocol._remote_address == unix_skt)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(protocol.session_complete(), 1)

        protocol = WClientProtocol.protocol(loop, remote_address=unix_skt)
        protocol._request_complete.set_result(1)
        result = await asyncio.wait_for(protocol.session_complete(), 1)
        assert(result == 1)
