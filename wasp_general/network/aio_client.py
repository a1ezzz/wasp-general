# -*- coding: utf-8 -*-
# wasp_general/network/aio_client.py
#
# Copyright (C) 2021, 2022 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# Wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

from abc import ABCMeta, abstractmethod
import asyncio

from wasp_general.verify import verify_type, verify_subclass
from wasp_general.api.registry import WAPIRegistry, WAPIRegistryProto, register_api
from wasp_general.uri import WURI, WURIQuery
from wasp_general.network.socket import __default_socket_collection__, WUnixSocketHandler
from wasp_general.network.aio_protocols import WClientDatagramProtocol, WClientStreamProtocol


class WAIONetworkClientAPIRegistry(WAPIRegistry):
    """ This registry may hold class-generated functions. Such classes will use asyncio primitives like
    "create_datagram_endpoint" for network clients to work
    """

    @verify_type('strict', uri=(WURI, str), bind_uri=(WURI, str, None), socket_collection=(WAPIRegistryProto, None))
    @verify_subclass('paranoid', protocol_cls=asyncio.BaseProtocol)
    @verify_type('paranoid', aio_loop=(asyncio.AbstractEventLoop, None))
    def network_handler(self, uri, protocol_cls, bind_uri=None, aio_loop=None, socket_collection=None):
        """ Return an instance for network client defined by a URI

        :param uri: URI with which socket is opened and with which a related client is instantiated
        :type uri: WURI | str

        :param protocol_cls: protocol that do a real work
        :type protocol_cls: subclass of asyncio.BaseProtocol

        :param bind_uri: URI with which socket should be bound to
        :type bind_uri: WURI | str | None

        :param aio_loop: a loop with which network client will work (by default a current loop is used)
        :type aio_loop: asyncio.AbstractEventLoop | None

        :param socket_collection: collection with which socket is opened (by default the
        "wasp_general.network.socket.__default_socket_collection__" collection is used)
        :type socket_collection: WAPIRegistryProto | None

        :rtype: AIONetworkClientProto
        """
        if isinstance(uri, str):
            uri = WURI.parse(uri)
        if isinstance(bind_uri, str):
            bind_uri = WURI.parse(bind_uri)
        if socket_collection is None:
            socket_collection = __default_socket_collection__

        create_handler_fn = WAPIRegistry.get(self, uri.scheme())
        return create_handler_fn(
            uri, protocol_cls, bind_uri=bind_uri, aio_loop=aio_loop, socket_collection=socket_collection
        )


__default_network_client_collection__ = WAIONetworkClientAPIRegistry()
""" Default collection for network clients instantiation
"""


class AIONetworkClientProto(metaclass=ABCMeta):
    """ Prototype for a custom network client
    """

    __supported_protocol__ = asyncio.BaseProtocol
    """ This is a protocol class, that derived classes (services) are awaiting for
    """

    @abstractmethod
    async def connect(self):
        """ Connect to a service and to a work

        :return: Connection result
        :rtype: any
        """
        raise NotImplementedError('This method is abstract')


# noinspection PyAbstractClass
class WBaseNetworkClient(AIONetworkClientProto):
    """ This class helps to implement a real network client
    """

    __supported_protocol__ = asyncio.BaseProtocol
    """ This is a protocol class, that derived classes (services) are awaiting for
    """

    @verify_type('strict', uri=WURI, bind_uri=(WURI, None), aio_loop=(asyncio.AbstractEventLoop, None))
    @verify_type('strict', socket_collection=(WAPIRegistryProto, None))
    def __init__(self, uri, protocol_cls, bind_uri=None, aio_loop=None, socket_collection=None):
        """ Create a new network client

        :param uri: URI with which socket is opened and with which a related client or service is instantiated
        :type uri: WURI

        :param protocol_cls: protocol that do a real work
        :type protocol_cls: asyncio.BaseProtocol

        :param bind_uri: URI with which socket should be bound to
        :type bind_uri: WURI | str | None

        :param aio_loop: a loop with which network service will work (by default a current loop is used)
        :type aio_loop: asyncio.AbstractEventLoop | None

        :param socket_collection: collection with which socket is opened (by default the
        "wasp_general.network.socket.__default_socket_collection__" collection is used)
        :type socket_collection: WAPIRegistryProto | None
        """
        AIONetworkClientProto.__init__(self)

        if issubclass(protocol_cls, self.__supported_protocol__) is False:
            raise TypeError(
                'Unsupported protocol spotted "%s" (use "%s" instead)' %
                (protocol_cls.__name__, self.__supported_protocol__.__name__)
            )

        self._uri = uri
        self._protocol_cls = protocol_cls
        self._bind_uri = bind_uri
        self._socket_collection = socket_collection if socket_collection else __default_socket_collection__
        self._aio_loop = aio_loop if aio_loop else asyncio.get_event_loop()
        self._transport = None


@register_api(__default_network_client_collection__, 'udp')
class WUDPNetworkClient(WBaseNetworkClient):
    """ Network client that runs over UDP in (obviously) datagram mode
    """

    __supported_protocol__ = WClientDatagramProtocol
    """ This service require datagram protocol
    """

    async def connect(self):
        """ :meth:`.WDatagramProtocol.connect` implementation
        :rtype: any
        """
        sock = self._socket_collection.aio_socket(self._uri)
        if self._bind_uri:
            sock.bind((self._bind_uri.hostname(), self._bind_uri.port()))
        await self._aio_loop.sock_connect(sock, (self._uri.hostname(), self._uri.port()))

        transport, protocol = await self._aio_loop.create_datagram_endpoint(
            lambda: self._protocol_cls.protocol(self._aio_loop, sock.getpeername()),
            sock=sock
        )

        result = await protocol.session_complete()
        transport.close()
        return result


@register_api(__default_network_client_collection__, 'tcp')
class WTCPNetworkClient(WBaseNetworkClient):
    """ Network client that runs over TCP in (obviously) stream mode
    """

    __supported_protocol__ = WClientStreamProtocol
    """ This service require stream protocol
    """

    async def connect(self):
        """ :meth:`.WStreamProtocol.connect` implementation
        :rtype: any
        """
        sock = self._socket_collection.aio_socket(self._uri)
        if self._bind_uri:
            sock.bind((self._bind_uri.hostname(), self._bind_uri.port()))
        await self._aio_loop.sock_connect(sock, (self._uri.hostname(), self._uri.port()))

        transport, protocol = await self._aio_loop.create_connection(
            lambda: self._protocol_cls.protocol(self._aio_loop, sock.getpeername()),
            sock=sock
        )

        result = await protocol.session_complete()
        transport.close()
        return result


@register_api(__default_network_client_collection__, 'unix')
@verify_type('paranoid', uri=WURI, aio_loop=(asyncio.AbstractEventLoop, None))
@verify_type('paranoid', socket_collection=(WAPIRegistryProto, None))
@verify_subclass('paranoid', protocol_cls=asyncio.BaseProtocol)
def unix_network_client(uri, protocol_cls, bind_uri=None, aio_loop=None, socket_collection=None):
    """ Return a network client connected to a UNIX-socket specified by an URI (bind_uri argument is obviously ignored)

    :rtype: WStreamedUnixNetworkClient | WDatagramUnixNetworkClient
    """
    uri_query = uri.query()
    if uri_query is not None:
        socket_opts = WURIQuery.parse(uri_query)
        if WUnixSocketHandler.QueryArg.type in socket_opts:
            if 'datagram' in socket_opts[WUnixSocketHandler.QueryArg.type]:
                return WDatagramUnixNetworkClient(
                    uri, protocol_cls, bind_uri=None, aio_loop=aio_loop, socket_collection=socket_collection
                )

    return WStreamedUnixNetworkClient(
        uri, protocol_cls, bind_uri=None, aio_loop=aio_loop, socket_collection=socket_collection
    )


class WStreamedUnixNetworkClient(WBaseNetworkClient):
    """ Network client that runs over UNIX-sockets stream mode
    """

    __supported_protocol__ = WClientStreamProtocol
    """ This service require stream protocol
    """

    async def connect(self):
        """ :meth:`.WStreamProtocol.connect` implementation
        :rtype: any
        """
        sock = self._socket_collection.aio_socket(self._uri)
        await self._aio_loop.sock_connect(sock, self._uri.path())

        transport, protocol = await self._aio_loop.create_connection(
            lambda: self._protocol_cls.protocol(self._aio_loop, sock.getpeername()),
            sock=sock
        )

        result = await protocol.session_complete()
        transport.close()
        sock.close()
        return result


class WDatagramUnixNetworkClient(WBaseNetworkClient):
    """ Network client that runs over UNIX-sockets in datagram mode
    """

    __supported_protocol__ = WClientDatagramProtocol
    """ This service require stream protocol
    """

    async def connect(self):
        """ :meth:`.WDatagramProtocol.connect` implementation
        :rtype: any
        """
        sock = self._socket_collection.aio_socket(self._uri)
        await self._aio_loop.sock_connect(sock, self._uri.path())

        transport, protocol = await self._aio_loop.create_datagram_endpoint(
            lambda: self._protocol_cls.protocol(self._aio_loop, sock.getpeername()),
            sock=sock
        )

        result = await protocol.session_complete()
        transport.close()
        return result
