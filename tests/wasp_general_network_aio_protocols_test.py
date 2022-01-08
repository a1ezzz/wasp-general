import asyncio
import pytest
import socket

from wasp_general.network.aio_protocols import WGeneralProtocol, WClientProtocol, WClientDatagramProtocol
from wasp_general.network.aio_protocols import WClientStreamProtocol, WServiceDatagramProtocol, WServiceStreamProtocol


@pytest.mark.asyncio
async def test_abstract():
    pytest.raises(TypeError, WClientProtocol)
    with pytest.raises(NotImplementedError):
        await WClientProtocol.session_complete(None)

    assert(issubclass(WClientDatagramProtocol, asyncio.DatagramProtocol))
    assert(issubclass(WClientDatagramProtocol, WClientProtocol))
    pytest.raises(TypeError, WClientDatagramProtocol)
    with pytest.raises(NotImplementedError):
        await WClientDatagramProtocol.session_complete(None)

    assert(issubclass(WClientStreamProtocol, asyncio.Protocol))
    assert(issubclass(WClientStreamProtocol, WClientProtocol))
    pytest.raises(TypeError, WClientStreamProtocol)
    with pytest.raises(NotImplementedError):
        await WClientStreamProtocol.session_complete(None)

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

    class Protocol(WClientProtocol):

        async def session_complete(self):
            return

    @pytest.mark.asyncio
    async def test(self):
        protocol = TestWClientProtocol.Protocol()
        assert(isinstance(protocol, WClientProtocol) is True)
        assert(isinstance(protocol, WGeneralProtocol) is True)
        assert(protocol._remote_address is None)

        loop = asyncio.get_event_loop()
        unix_skt = '/foo/bar'
        protocol = TestWClientProtocol.Protocol.protocol(loop, remote_address=unix_skt)
        assert(isinstance(protocol, WClientProtocol) is True)
        assert(protocol._aio_loop is loop)
        assert(protocol._remote_address == unix_skt)
