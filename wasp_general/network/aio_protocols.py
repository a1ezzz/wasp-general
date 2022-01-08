# -*- coding: utf-8 -*-
# wasp_general/network/aio_protocols.py
#
# Copyright (C) 2022 the wasp-general authors and contributors
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

from wasp_general.verify import verify_type


class WGeneralProtocol(asyncio.BaseProtocol, metaclass=ABCMeta):
    """ A basic protocol for aio_* transports
    """

    def __init__(self):
        """ Create a protocol instance
        :note: A protocol instance shouldn't be created directly, use the :meth:`.WGeneralProtocol.protocol` method
        instead
        """
        asyncio.BaseProtocol.__init__(self)
        self._aio_loop = None
        self._transport = None

    @verify_type('strict', transport=asyncio.BaseTransport)
    def connection_made(self, transport):
        """ :meth:`.asyncio.BaseTransport.connection_made` implementation

        :type transport: asyncio.BaseTransport
        :rtype: None
        """
        self._transport = transport

    @verify_type('strict', exc=BaseException)
    def connection_lost(self, exc):
        """ :meth:`.asyncio.BaseTransport.connection_lost` implementation

        :type exc: BaseException
        :rtype: None
        """
        self._transport = None

    @classmethod
    def protocol(cls, *args, **kwargs):
        """ Create a new protocol instance
        :note: object is initialize within the :meth:`.WGeneralProtocol._init_protocol` method

        :type args: any
        :type kwargs: any

        :rtype: WGeneralProtocol
        """
        obj = cls()
        obj._init_protocol(*args, **kwargs)
        return obj

    @verify_type('strict', aio_loop=asyncio.AbstractEventLoop)
    def _init_protocol(self, aio_loop, **kwargs):
        """ Initialize protocol object

        :param aio_loop: a loop with which protocol will work
        :type aio_loop: asyncio.AbstractEventLoop

        :rtype: None
        """
        self._aio_loop = aio_loop


class WClientProtocol(WGeneralProtocol):
    """ A basic protocol for async client transports
    """

    def __init__(self):
        """ Create a client protocol instance
        :note: A protocol instance shouldn't be created directly, use the :meth:`.WClientProtocol.protocol` method
        instead
        """
        WGeneralProtocol.__init__(self)
        self._remote_address = None

    @abstractmethod
    async def session_complete(self):
        """ This coroutine is completed when job is done and connection should be terminated

        :return: Connection result
        :rtype: any
        """
        raise NotImplementedError('This method is abstract')

    @verify_type('strict', remote_address=(tuple, str))
    @verify_type('paranoid', aio_loop=asyncio.AbstractEventLoop)
    def _init_protocol(self, aio_loop, remote_address=None, **kwargs):
        """ :meth:`.WGeneralProtocol._init_protocol` implementation

        :param aio_loop: same as aio_loop in the :meth:`.WGeneralProtocol._init_protocol` method
        :type aio_loop: asyncio.AbstractEventLoop

        :param remote_address: A remote address this client is about to connect to. Is used for datagram transport
        mostly
        :type remote_address: tuple | str

        :rtype: None
        """
        WGeneralProtocol._init_protocol(self, aio_loop)
        self._remote_address = remote_address


# noinspection PyAbstractClass
class WClientDatagramProtocol(asyncio.DatagramProtocol, WClientProtocol):
    """ Prototype for a client protocol that is used along with UDP and UNIX-sockets
    :note: A _new_ instance for every connection
    """


# noinspection PyAbstractClass
class WClientStreamProtocol(asyncio.Protocol, WClientProtocol):
    """ Prototype for a client protocol that is used along with TCP and UNIX-sockets
    :note: A _new_ instance for every connection
    """
    pass


# noinspection PyAbstractClass
class WServiceDatagramProtocol(asyncio.DatagramProtocol, WGeneralProtocol):
    """ Prototype for a service protocol that is used along with UDP and UNIX-sockets
    :note: A _single_ instance for every connection
    """


# noinspection PyAbstractClass
class WServiceStreamProtocol(asyncio.Protocol, WGeneralProtocol):
    """ Prototype for a service protocol that is used along with TCP and UNIX-sockets
    :note: A _new_ instance for every handled connection
    """
    pass
