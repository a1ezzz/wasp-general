# -*- coding: utf-8 -*-
# wasp_general/network/aio_network.py
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

from asyncio import BaseProtocol, AbstractEventLoop

from wasp_general.api.registry import WAPIRegistryProto, WAPIRegistry
from wasp_general.verify import verify_type, verify_subclass
from wasp_general.uri import WURI
from wasp_general.network.socket import __default_socket_collection__


class WAIONetworkAPIRegistry(WAPIRegistry):
    """ This registry may hold class-generated functions. Such classes will use asyncio primitives like
    "create_datagram_endpoint" for network clients or network services to work
    """

    @verify_type('strict', uri=(WURI, str), socket_collection=(WAPIRegistryProto, None))
    @verify_subclass('paranoid', protocol_cls=BaseProtocol)
    @verify_type('paranoid', aio_loop=(AbstractEventLoop, None))
    def network_handler(self, uri, protocol_cls, aio_loop=None, socket_collection=None):
        """ Return an instance for network client or network server defined by a URI

        :param uri: URI with which socket is opened and with which a related client or service is instantiated
        :type uri: WURI | str

        :param protocol_cls: protocol that do a real work
        :type protocol_cls: subclass of asyncio.BaseProtocol

        :param aio_loop: a loop with which network client or service will work (by default a current loop is used)
        :type aio_loop: asyncio.AbstractEventLoop | None

        :param socket_collection: collection with which socket is opened (by default the
        "wasp_general.network.socket.__default_socket_collection__" collection is used)
        :type socket_collection: WAPIRegistryProto | None

        :return: Result is different for a client or a service
        :rtype: object
        """
        if isinstance(uri, str):
            uri = WURI.parse(uri)
        if socket_collection is None:
            socket_collection = __default_socket_collection__

        create_handler_fn = WAPIRegistry.get(self, uri.scheme())
        return create_handler_fn(uri, protocol_cls, aio_loop=aio_loop, socket_collection=socket_collection)


__default_network_client_collection__ = WAIONetworkAPIRegistry()
""" Default collection for network clients instantiation
"""

__default_network_services_collection__ = WAIONetworkAPIRegistry()
""" Default collection for network services instantiation
"""
