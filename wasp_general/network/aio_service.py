# -*- coding: utf-8 -*-
# wasp_general/network/aio_service.py
#
# Copyright (C) 2021 the wasp-general authors and contributors
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
from wasp_general.api.registry import WAPIRegistryProto, register_api, WAPIRegistry
from wasp_general.uri import WURI, WURIQuery
from wasp_general.network.socket import __default_socket_collection__, WUnixSocketHandler
from wasp_general.network.aio_protocols import WServiceStreamProtocol, WServiceDatagramProtocol


class WAIONetworkServiceAPIRegistry(WAPIRegistry):
    """ This registry may hold class-generated functions. Such classes will use asyncio primitives like
    "create_datagram_endpoint" for network services to work
    """

    @verify_type('strict', uri=(WURI, str), socket_collection=(WAPIRegistryProto, None))
    @verify_subclass('paranoid', protocol_cls=asyncio.BaseProtocol)
    @verify_type('paranoid', aio_loop=(asyncio.AbstractEventLoop, None))
    def network_handler(self, uri, protocol_cls, aio_loop=None, socket_collection=None):
        """ Return an instance for network service defined by a URI

        :param uri: URI with which socket is opened and with which a service is instantiated
        :type uri: WURI | str

        :param protocol_cls: protocol that do a real work
        :type protocol_cls: subclass of asyncio.BaseProtocol

        :param aio_loop: a loop with which network service will work (by default a current loop is used)
        :type aio_loop: asyncio.AbstractEventLoop | None

        :param socket_collection: collection with which socket is opened (by default the
        "wasp_general.network.socket.__default_socket_collection__" collection is used)
        :type socket_collection: WAPIRegistryProto | None

        :rtype: AIONetworkServiceProto
        """
        if isinstance(uri, str):
            uri = WURI.parse(uri)
        if socket_collection is None:
            socket_collection = __default_socket_collection__

        create_handler_fn = WAPIRegistry.get(self, uri.scheme())
        return create_handler_fn(uri, protocol_cls, aio_loop=aio_loop, socket_collection=socket_collection)


__default_network_services_collection__ = WAIONetworkServiceAPIRegistry()
""" Default collection for network services instantiation
"""


class AIONetworkServiceProto(metaclass=ABCMeta):
    """ Prototype for a custom network service
    """

    __supported_protocol__ = asyncio.BaseProtocol
    """ This is a protocol class, that derived classes (services) are awaiting for
    """

    @abstractmethod
    async def start(self):
        """ Start a network service

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')

    @abstractmethod
    async def stop(self):
        """ Stop a network service

        :rtype: None
        """
        raise NotImplementedError('This method is abstract')


# noinspection PyAbstractClass
class WBaseNetworkService(AIONetworkServiceProto):
    """ This class helps to implement a real network service
    """

    __supported_protocol__ = asyncio.BaseProtocol
    """ This is a protocol class, that derived classes (services) are awaiting for
    """

    @verify_type('strict', uri=WURI, aio_loop=(asyncio.AbstractEventLoop, None))
    @verify_type('strict', socket_collection=(WAPIRegistryProto, None))
    @verify_subclass(protocol_cls=__supported_protocol__)
    def __init__(self, uri, protocol_cls, aio_loop=None, socket_collection=None):
        """ Create a basic network service

        :param uri: URI with which socket is opened and with which a related client or service is instantiated
        :type uri: WURI

        :param protocol_cls: protocol that do a real work
        :type protocol_cls: asyncio.BaseProtocol

        :param aio_loop: a loop with which network service will work (by default a current loop is used)
        :type aio_loop: asyncio.AbstractEventLoop | None

        :param socket_collection: collection with which socket is opened (by default the
        "wasp_general.network.socket.__default_socket_collection__" collection is used)
        :type socket_collection: WAPIRegistryProto | None
        """
        AIONetworkServiceProto.__init__(self)

        if issubclass(protocol_cls, self.__supported_protocol__) is False:
            raise TypeError(
                'Unsupported protocol spotted "%s" (use "%s" instead)' %
                (protocol_cls.__name__, self.__supported_protocol__.__name__)
            )

        self._uri = uri
        self._socket_collection = socket_collection if socket_collection else __default_socket_collection__
        self._protocol_cls = protocol_cls
        self._aio_loop = aio_loop if aio_loop else asyncio.get_event_loop()
        self._transport = None


@register_api(__default_network_services_collection__, 'udp')
class WUDPNetworkService(WBaseNetworkService):
    """ Network service that runs over UDP in (obviously) datagram mode
    """

    __supported_protocol__ = WServiceDatagramProtocol
    """ This service require datagram protocol
    """

    async def start(self):
        """ :meth:`.AIONetworkServiceProto.start` implementation
        :rtype: None
        """
        if self._transport:
            raise RuntimeError('Unable to run service twice!')

        sock = self._socket_collection.aio_socket(self._uri)
        sock.bind((self._uri.hostname(), self._uri.port()))
        self._transport, _ = await self._aio_loop.create_datagram_endpoint(
            lambda: self._protocol_cls.protocol(self._aio_loop), sock=sock
        )

    async def stop(self):
        """ :meth:`.AIONetworkServiceProto.stop` implementation
        :rtype: None
        """
        if self._transport:
            self._transport.close()  # TODO: more graceful shutdown
            self._transport = None


@register_api(__default_network_services_collection__, 'tcp')
class WTCPNetworkService(WBaseNetworkService):
    """ Network service that runs over TCP in (obviously) streamed mode
    """

    __supported_protocol__ = WServiceStreamProtocol
    """ This service require stream protocol
    """

    async def start(self):
        """ :meth:`.AIONetworkServiceProto.start` implementation
        :rtype: None
        """
        if self._transport:
            raise RuntimeError('Unable to run service twice!')

        sock = self._socket_collection.aio_socket(self._uri)
        sock.bind((self._uri.hostname(), self._uri.port()))

        self._transport = await self._aio_loop.create_server(
            lambda: self._protocol_cls.protocol(self._aio_loop), sock=sock
        )
        await self._transport.start_serving()

    async def stop(self):
        """ :meth:`.AIONetworkServiceProto.stop` implementation
        :rtype: None
        """
        if self._transport:
            self._transport.close()  # TODO: more graceful shutdown
            await self._transport.wait_closed()
            self._transport = None


@register_api(__default_network_services_collection__, 'unix')
@verify_type('paranoid', uri=WURI, aio_loop=(asyncio.AbstractEventLoop, None))
@verify_type('paranoid', socket_collection=(WAPIRegistryProto, None))
@verify_subclass('paranoid', protocol_cls=asyncio.BaseProtocol)
def unix_network_service(uri, protocol_cls, aio_loop=None, socket_collection=None):
    """ Return a network service connected to a UNIX-socket specified by an URI

    :rtype: WStreamedUnixNetworkService | WDatagramUnixNetworkService
    """
    uri_query = uri.query()
    if uri_query is not None:
        socket_opts = WURIQuery.parse(uri_query)
        if WUnixSocketHandler.QueryArg.type in socket_opts:
            if 'datagram' in socket_opts[WUnixSocketHandler.QueryArg.type]:
                return WDatagramUnixNetworkService(
                    uri, protocol_cls, aio_loop=aio_loop, socket_collection=socket_collection
                )

    return WStreamedUnixNetworkService(uri, protocol_cls, aio_loop=aio_loop, socket_collection=socket_collection)


class WStreamedUnixNetworkService(WBaseNetworkService):
    """ Network service that runs over UNIX-sockets in stream mode
    """

    __supported_protocol__ = WServiceStreamProtocol
    """ This service require stream protocol
    """

    async def start(self):
        """ :meth:`.AIONetworkServiceProto.start` implementation
        :rtype: None
        """
        if self._transport:
            raise RuntimeError('Unable to run service twice!')

        sock = self._socket_collection.aio_socket(self._uri)
        sock.bind(self._uri.path())

        self._transport = await self._aio_loop.create_unix_server(
            lambda: self._protocol_cls.protocol(self._aio_loop), sock=sock
        )
        await self._transport.start_serving()

    async def stop(self):
        """ :meth:`.AIONetworkServiceProto.stop` implementation
        :rtype: None
        """
        if self._transport:
            self._transport.close()  # TODO: more graceful shutdown
            await self._transport.wait_closed()
            self._transport = None


class WDatagramUnixNetworkService(WBaseNetworkService):
    """ Network service that runs over UNIX-sockets in datagram mode
    """

    __supported_protocol__ = WServiceDatagramProtocol
    """ This service require stream protocol
    """

    async def start(self):
        """ :meth:`.AIONetworkServiceProto.start` implementation
        :rtype: None
        """
        if self._transport:
            raise RuntimeError('Unable to run service twice!')

        sock = self._socket_collection.aio_socket(self._uri)
        sock.bind(self._uri.path())

        self._transport, _ = await self._aio_loop.create_datagram_endpoint(
            lambda: self._protocol_cls.protocol(self._aio_loop), sock=sock
        )

    async def stop(self):
        """ :meth:`.AIONetworkServiceProto.stop` implementation
        :rtype: None
        """
        if self._transport:
            self._transport.close()  # TODO: more graceful shutdown
            self._transport = None
