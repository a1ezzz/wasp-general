# -*- coding: utf-8 -*-
# wasp_general/network/service.py
#
# Copyright (C) 2016 the wasp-general authors and contributors
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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from datetime import timedelta
from abc import abstractmethod, ABCMeta

from zmq import Context as ZMQContext
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

from wasp_general.verify import verify_type, verify_subclass
from wasp_general.config import WConfig

from wasp_general.network.transport import WNetworkNativeTransportProto


class WIOLoopServiceHandler(metaclass=ABCMeta):
	""" Represent service (or service client) handler that works with tornado IOLoop and do the work.
	"""

	@abstractmethod
	@verify_type(io_loop=IOLoop)
	def setup_handler(self, io_loop):
		""" Set up this handler with the specified IOLoop

		:param io_loop: service (or service client) loop to use with
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	def loop_stopped(self):
		""" Method is called when previously set up loop was stopped

		:return: None
		"""
		pass


class WIOLoopService(metaclass=ABCMeta):
	""" Represent service (or service client) that works over tornado IOLoop
	"""

	@verify_type(handler=WIOLoopServiceHandler, loop=(IOLoop, None), timeout=(int, None))
	def __init__(self, handler, loop=None, timeout=None):
		""" Create new service (or service client)

		:param handler: handler that do the work
		:param loop: loop to use (or None for internal one)
		:param timeout: timeout after which this loop will be stopped
		"""
		self.__loop = IOLoop() if loop is None else loop
		self.__handler = handler
		self.__timeout = timeout

	def loop(self):
		""" Return service loop object

		:return: IOLoop
		"""
		return self.__loop

	def handler(self):
		""" Return service handler

		:return: WIOLoopServiceHandler
		"""
		return self.__handler

	def timeout(self):
		""" Return service timeout. (None for endless loop)

		:return: int or None
		"""
		return self.__timeout

	def start(self):
		""" Set up handler and start loop

		:return: None
		"""
		timeout = self.timeout()
		if timeout is not None and timeout > 0:
			self.__loop.add_timeout(timedelta(0, timeout), self.stop)
		self.handler().setup_handler(self.loop())
		self.loop().start()
		self.handler().loop_stopped()

	def stop(self):
		""" Stop loop

		:return: None
		"""
		self.loop().stop()


class WNativeSocketIOHandler(metaclass=ABCMeta):
	""" Handler prototype for loops that work with :class:`.WNetworkNativeTransportProto` transports. It is used by
	:class:`.WBasicNativeSocketHandler` handler and do all the work for this class.
	"""

	@abstractmethod
	def handler_fn(self, fd, event):
		""" Process (handle) specified event

		:param fd: integer file descriptor or a file-like object with a fileno() method
		:param event: IOLoop event
		:return: None
		"""
		raise NotImplementedError('This method is abstract')


class WBasicNativeSocketHandler(WIOLoopServiceHandler, metaclass=ABCMeta):
	""" Basic :class:`.WIOLoopServiceHandler` implementation. Since some :class:`.WNetworkNativeTransportProto`
	methods are required :class:`.WConfig` object, then that kind of object is required for this class
	instantiation
	"""

	@verify_type(transport=WNetworkNativeTransportProto, config=WConfig, io_handler=WNativeSocketIOHandler)
	def __init__(self, transport, config, io_handler):
		""" Create new socket handler

		:param transport: transport to use
		:param config: configuration to be used with transport
		:param io_handler: handler that do the real work
		"""
		WIOLoopServiceHandler.__init__(self)
		self.__transport = transport
		self.__config = config
		self.__io_handler = io_handler

	def transport(self):
		""" Return currently used transport
		:return: WNetworkNativeTransportProto
		"""
		return self.__transport

	def config(self):
		""" Return handler configuration

		:return: WConfig
		"""
		return self.__config

	def io_handler(self):
		""" Return IO-handler

		:return: WNativeSocketIOHandler
		"""
		return self.__io_handler


class WNativeSocketDirectIOHandler(WNativeSocketIOHandler, metaclass=ABCMeta):
	""" This type of IO-handler has access to low-level socket object
	"""

	def __init__(self):
		""" Create new IO-handler

		"""
		WNativeSocketIOHandler.__init__(self)
		self.__transport_socket = None

	def transport_socket(self, new_socket=None):
		""" Save and/or return currently used socket object

		:param new_socket: new socket to save
		:return: socket object (any type, None if socket wasn't set)
		"""
		if new_socket is not None:
			self.__transport_socket = new_socket
		return self.__transport_socket


class WNativeSocketHandler(WBasicNativeSocketHandler):
	""" Enhanced variant of :class:`.WBasicNativeSocketHandler` class. This class support 'server_mode' flag and
	is capable to set up the specified IO-handler with :class:`.WIOLoopService` service
	"""

	@verify_type(server_mode=bool, transport=WNetworkNativeTransportProto, config=WConfig)
	@verify_type(io_handler=WNativeSocketIOHandler)
	def __init__(self, transport, config, io_handler, server_mode):
		""" Create new loop-handler

		:param transport: transport to use
		:param config: configuration to use (in the most cases it is used by transport object only)
		:param io_handler: io-handler to use
		:param server_mode: set 'server_mode' flag for correct transport configuration
		"""
		WBasicNativeSocketHandler.__init__(self, transport, config, io_handler)
		self.__server_mode = server_mode

	def server_mode(self):
		""" Return current mode. True if this handler works as a server, otherwise - False

		:return: bool
		"""
		return self.__server_mode

	@verify_type(io_loop=IOLoop)
	def setup_handler(self, io_loop):
		""" :meth:`.WIOLoopServiceHandler.setup_handler` implementation.
		If :class:`.WNativeSocketDirectIOHandler` is used as a io-handler, then socket object is saved
		to this handler before loop starting

		:param io_loop: io_loop to use
		:return: None
		"""

		if self.server_mode() is True:
			s = self.transport().server_socket(self.config())
		else:
			s = self.transport().client_socket(self.config())

		io_handler = self.io_handler()
		if isinstance(io_handler, WNativeSocketDirectIOHandler) is True:
			io_handler.transport_socket(s)
		io_loop.add_handler(s.fileno(), io_handler.handler_fn, io_loop.READ)

	def loop_stopped(self):
		""" Terminate socket connection because of stopping loop

		:return: None
		"""
		transport = self.transport()
		if self.server_mode() is True:
			transport.close_server_socket(self.config())
		else:
			transport.close_client_socket(self.config())


class WZMQHandler(WIOLoopServiceHandler, metaclass=ABCMeta):

	@verify_type(context=ZMQContext, socket_type=int, connection=str)
	def __init__(self, context, socket_type, connection):
		self.__socket_type = socket_type
		self.__context = context
		self.__connection = connection
		self.__socket = None
		self.__stream = None

	def socket_type(self):
		return self.__socket_type

	def connection(self):
		return self.__connection

	def socket(self):
		return self.__socket

	def create_socket(self):
		self.__socket = self.__context.socket(self.socket_type())
		return self.__socket

	def stream(self):
		return self.__stream

	@verify_type(io_loop=IOLoop)
	def setup_handler(self, io_loop):
		s = self.create_socket()
		self.__stream = ZMQStream(s, io_loop=io_loop)
		self.__stream.on_recv(self.on_recv)

	@abstractmethod
	def on_recv(self, msg):
		raise NotImplementedError('This method is abstract')


class WZMQBindHandler(WZMQHandler, metaclass=ABCMeta):

	def create_socket(self):
		s = WZMQHandler.create_socket(self)
		s.bind(self.connection())
		return s


class WZMQConnectHandler(WZMQHandler, metaclass=ABCMeta):

	def create_socket(self):
		s = WZMQHandler.create_socket(self)
		s.connect(self.connection())
		return s


class WZMQService(WIOLoopService):

	@verify_type(socket_type=int, connection=str, loop=(IOLoop, None), timeout=(int, None))
	@verify_type(context=(ZMQContext, None))
	@verify_subclass(handler_cls=WZMQHandler)
	def __init__(self, socket_type, connection, handler_cls, loop=None, timeout=None, context=None):
		self.__context = context if context is not None else ZMQContext()
		handler = handler_cls(self.__context, socket_type, connection)
		WIOLoopService.__init__(self, handler, loop=loop, timeout=timeout)

	def context(self):
		return self.__context
