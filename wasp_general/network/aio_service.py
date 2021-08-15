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
from wasp_general.uri import WURI
from wasp_general.network.socket import __default_socket_collection__


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


@register_api(__default_network_services_collection__, 'udp')
class WDatagramNetworkService(AIONetworkServiceProto):
    """ Network service that runs over UDP in (obviously) datagram mode
    """

    @verify_type('strict', uri=WURI, aio_loop=(asyncio.AbstractEventLoop, None))
    @verify_type('strict', socket_collection=(WAPIRegistryProto, None))
    @verify_subclass(protocol_cls=asyncio.DatagramProtocol)
    def __init__(self, uri, protocol_cls, aio_loop=None, socket_collection=None):
        """ Create a new network service

        :param uri: URI with which socket is opened and with which a related client or service is instantiated
        :type uri: WURI

        :param protocol_cls: protocol that do a real work
        :type protocol_cls: asyncio.DatagramProtocol

        :param aio_loop: a loop with which network service will work (by default a current loop is used)
        :type aio_loop: asyncio.AbstractEventLoop | None

        :param socket_collection: collection with which socket is opened (by default the
        "wasp_general.network.socket.__default_socket_collection__" collection is used)
        :type socket_collection: WAPIRegistryProto | None
        """
        AIONetworkServiceProto.__init__(self)
        self.__uri = uri
        self.__socket_collection = socket_collection if socket_collection else __default_socket_collection__
        self.__protocol_cls = protocol_cls
        self.__aio_loop = aio_loop
        self.__transport = None

    async def start(self):
        """ :meth:`.AIONetworkServiceProto.start` implementation

        :rtype: None
        """
        if self.__transport:
            raise RuntimeError('Unable to run service twice!')

        socket_handler = self.__socket_collection.open(self.__uri)
        sock = socket_handler.socket()
        sock.bind((self.__uri.hostname(), self.__uri.port()))
        sock.setblocking(False)

        loop = self.__aio_loop if self.__aio_loop else asyncio.get_event_loop()
        self.__transport, _ = await loop.create_datagram_endpoint(self.__protocol_cls, sock=sock)

    async def stop(self):
        """ :meth:`.AIONetworkServiceProto.stop` implementation

        :rtype: None
        """
        if self.__transport:
            self.__transport.close()  # TODO: more graceful shutdown
            self.__transport = None
