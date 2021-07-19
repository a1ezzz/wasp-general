# -*- coding: utf-8 -*-
# wasp_general/network/beacon/beacon.py
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

# TODO: Add zeroconf beacon
# TODO: test the code

import os
from enum import Enum
from zmq.eventloop.ioloop import IOLoop
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type
from wasp_general.config import WConfig

from wasp_general.network.primitives import WIPV4SocketInfo
from wasp_general.network.transport import WNetworkNativeTransportProto
from wasp_general.network.beacon.transport import WBroadcastBeaconTransport, WMulticastBeaconTransport
from wasp_general.network.beacon.messenger import WBeaconMessengerBase, WBeaconMessenger
from wasp_general.network.service import WIOLoopService, WNativeSocketHandler, WNativeSocketDirectIOHandler
from wasp_general.network.socket import __default_socket_collection__


class WBeaconConfig(WConfig):

	__beacon_defaults__ = os.path.join(os.path.dirname(__file__), '..', '..', 'defaults.ini')
	__beacon_section_name__ = 'wasp-general::network::beacon'

	@verify_type('strict', ext_config=(WConfig, None), ext_config_section=(str, None))
	def __init__(self, ext_config=None, ext_config_section=None):
		WConfig.__init__(self)
		self.merge(self.__beacon_defaults__)
		if ext_config:
			self.merge_section(ext_config, self.__beacon_section_name__, section_from=ext_config_section)

	@verify_type('paranoid', option_name=str)
	def beacon_option(self, option_name):
		return self.get(self.__beacon_section_name__, option_name)


class WNetworkBeaconCallback(metaclass=ABCMeta):
	""" Abstract class that represent network beacon callback. Helps to interact with clients or servers. After
	beacons message received this is the place where all the beacon logic happens.
	"""

	class WDataDescription(Enum):
		""" This enum defines beacons message source
		"""
		request = 0
		""" Beacons message is request from client to server
		"""
		invalid_request = 1
		""" Beacons message is invalid request from client to server
		"""
		response = 2
		""" Beacons message is response from server to client
		"""

	@abstractmethod
	@verify_type(message=bytes, source=WIPV4SocketInfo, description=WDataDescription)
	def __call__(self, message, source, description):
		""" Method where all the magic is done.

		:param message: binary message (request or response)
		:param source: network source address (original address)
		:param description: defines whether message is a request or a response
		:return: None
		"""
		raise NotImplementedError('This method is abstract')


import asyncio

from wasp_general.network.messenger.session import WMessengerOnionSessionFlow, WMessengerOnionSession
from wasp_general.network.messenger.onion import WMessengerOnion
from wasp_general.network.messenger.envelope import WMessengerEnvelope
from wasp_general.network.messenger.proto import WMessengerOnionLayerProto, WMessengerOnionSessionFlowProto


# @verify_type('paranoid', command_tokens=str, command_context=(WContextProto, None))
# def exec(self, *command_tokens, **command_env):
# 	broker = self.__console.broker()
# 	handler = broker.handler()
# 	receive_agent = broker.receive_agent()
# 	send_agent = broker.send_agent()
#
# 	session_flow = WMessengerOnionSessionFlow.sequence_flow(
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-general.composer-packer-layer',
# 			mode=WMessengerComposerLayer.Mode.decompose,
# 			composer_factory=self.__composer_factory
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-general.json-packer-layer',
# 			mode=WMessengerOnionPackerLayerProto.Mode.pack
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-general.encoding-layer',
# 			mode=WMessengerOnionCoderLayerProto.Mode.encode
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-launcher.console-output-layer',
# 			feedback='Command is sending', refresh_window=True
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-general.send-agent-layer',
# 			send_agent=send_agent, handler=handler
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-launcher.console-output-layer',
# 			feedback='Response is awaiting', undo_previous=True, refresh_window=True
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-general.sync-receive-agent-layer',
# 			receive_agent=receive_agent
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-launcher.console-output-layer',
# 			undo_previous=True, refresh_window=True
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-general.encoding-layer',
# 			mode=WMessengerOnionCoderLayerProto.Mode.decode
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-general.json-packer-layer',
# 			mode=WMessengerOnionPackerLayerProto.Mode.unpack
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			"com.binblob.wasp-general.simple-casting-layer",
# 			from_envelope=WMessengerEnvelope, to_envelope=WMessengerDictEnvelope
# 		),
# 		WMessengerOnionSessionFlowProto.IteratorInfo(
# 			'com.binblob.wasp-general.composer-packer-layer',
# 			mode=WMessengerComposerLayer.Mode.compose,
# 			composer_factory=self.__composer_factory
# 		)
# 	)
#
# 	session = WMessengerOnionSession(self.__onion, session_flow)
# 	try:
# 		command_request = WCommandRequest(*command_tokens, **command_env)
# 		envelope = session.process(WMessengerEnvelope(command_request))
# 		return envelope.message()
# 	except TimeoutError:
# 		self.__console_output_layer.undo_feedback()
# 		broker.discard_queue_messages()
# 		return WPlainCommandResult('Error. Command completion timeout expired')


class AsyncIOLayer(WMessengerOnionLayerProto):

	def __init__(self):
		WMessengerOnionLayerProto.__init__(self, 'asyncio_layer')

	def process(self, envelope, session, **kwargs):
		return envelope
		# if undo_previous is not None and undo_previous is True:
		# 	self.undo_feedback()
		# if feedback is not None:
		# 	self.__last_feedback_length = len(feedback)
		# 	cr = cr if cr is not None else True
		# 	if cr is True:
		# 		self.__last_feedback_length += 1
		# 	self.console().write(feedback, cr=cr)
		# if refresh_window is not None and refresh_window is True:
		# 	self.console().refresh_window()
		# return envelope


class WBeaconAIOServerProtocol(asyncio.DatagramProtocol):

	def connection_made(self, transport):
		self.transport = transport

	def datagram_received(self, data, addr):
		message = data.decode()
		print('Server Received %r from %s' % (message, addr))
		print('Server Send %r to %s' % (message, addr))
		self.transport.sendto(data, addr)

	# s = self.transport_socket()
	# messenger = self.messenger()
	# callback = self.callback()
	#
	# request, client = s.recvfrom(self.max_size())
	# original_address = WIPV4SocketInfo(client[0], client[1])
	#
	# if messenger.has_response(self.config(), request, original_address) is True:
	# 	direction = WNetworkBeaconCallback.WDataDescription.request
	#
	# 	response = messenger.response(self.config(), request, original_address)
	# 	address = messenger.response_address(self.config(), request, original_address)
	# 	if callback is not None:
	# 		callback(request, original_address, direction)
	# 	s.sendto(response, address.pair())
	# elif self.process_any() is True and callback is not None:
	# 	direction = WNetworkBeaconCallback.WDataDescription.invalid_request
	#
	# 	if messenger.valid_response(self.config(), request, original_address):
	# 		callback(request, original_address, direction)

	def error_received(self, exc):
		print('Server error received:', exc)

	def connection_lost(self, exc):
		print("Connection closed")


class WBeaconAIOClientProtocol(asyncio.DatagramProtocol):
	def __init__(self, hostname, port, loop):
		self.h = hostname
		self.p = port
		self.loop = loop
		self.transport = None
		self.on_con_lost = asyncio.Event()

	def connection_made(self, transport):
		self.transport = transport
		message = b'test'
		# message = self.messenger.request(self.config())
		# self.transport.sendto(message, addr=(self.h, self.p))
		# print('Successfuly send')

		print('Onion')
		onion = WMessengerOnion()
		onion.add_layers(AsyncIOLayer())
		session_flow = WMessengerOnionSessionFlow.sequence_flow(
			WMessengerOnionSessionFlowProto.IteratorInfo('asyncio_layer')
		)
		session = WMessengerOnionSession(onion, session_flow)
		envelope = session.process(WMessengerEnvelope(message))
		print('Onion envelope ' + str(envelope.message()))


	# ===================

	# s = self.transport_socket()
	# messenger = self.messenger()
	# callback = self.callback()
	# direction = WNetworkBeaconCallback.WDataDescription.response
	#
	# response, server = s.recvfrom(self.max_size())
	#
	# if callback is not None:
	# 	server_si = WIPV4SocketInfo(server[0], server[1])
	# 	if messenger.valid_response(self.config(), response, server_si):
	# 		callback(response, server_si, direction)

	def datagram_received(self, data, addr):
		print('Client rec addr: ' + str(addr))
		print("Client Received:", data.decode())
		print("Close the socket")
		self.transport.close()

	def error_received(self, exc):
		print('Client Error received:', exc)

	def connection_lost(self, exc):
		print("Connection closed")
		self.on_con_lost.set()


class WBeaconAIOServer:

	def __init__(self, loop=None, timeout=None):
		self.__loop = loop if loop else asyncio.get_running_loop()
		self.__timeout = timeout
		self.__config = WBeaconConfig()
		self.__protocol = WBeaconAIOServerProtocol()
		self.__stop_event = asyncio.Event(loop=self.__loop)

	async def start(self):
		socket_uri = self.__config.beacon_option('server_uri').lower()
		s_h = __default_socket_collection__.open(socket_uri)
		s = s_h.socket()
		u = s_h.uri()
		s.bind((u.hostname(), u.port()))
		# TODO: set socket as non blocked

		transport, protocol = await self.__loop.create_datagram_endpoint(
			lambda: self.__protocol, sock=s
		)

		if self.__timeout:
			self.__loop.call_later(self.__timeout, self.stop)

		try:
			await self.__stop_event.wait()
		finally:
			transport.close()

	def stop(self):
		print('Stop!!')
		self.__stop_event.set()


class WBeaconAIOClient:

	def __init__(self, loop=None):
		self.__loop = loop if loop else asyncio.get_running_loop()
		self.__config = WBeaconConfig()

	async def connect(self):
		socket_uri = self.__config.beacon_option('client_uri').lower()
		s_h = __default_socket_collection__.open(socket_uri)
		s = s_h.socket()
		u = s_h.uri()

		# TODO: set socket as non blocked

		return await self.__loop.create_datagram_endpoint(
			lambda: WBeaconAIOClientProtocol(
				u.hostname(), u.port(), self.__loop
			),
			sock=s
		)















# class WBeaconConfig(metaclass=ABCMeta):
# 	""" Abstract class that represent service discovery beacon configuration
# 	"""
#
# 	@verify_type(config=(WConfig, None), config_section=(str, None))
# 	def __init__(self, config=None, config_section=None):
# 		""" Merge configuration to this beacon
#
# 		:param config: configuration storage
# 		:param config_section: configuration section name where options are
# 		"""
# 		self.__configuration = WConfig()
# 		self.__configuration.merge(os.path.join(os.path.dirname(__file__), '..', '..', 'defaults.ini'))
# 		if config is not None:
# 			self.__configuration.merge_section(config, 'wasp-general::network::beacon', section_from=config_section)
#
# 	def config(self):
# 		""" Return beacon configuration
#
# 		:return: WConfig
# 		"""
# 		return self.__configuration
#
#
# class WBeaconHandler(WNativeSocketHandler):
# 	""" Beacon's loop-handler. Is capable to create required transport (that is specified in the beacon's
# 	configuration) Depends on configuration value, the following classes is used:
#
# 		'broadcast' (default) - :class:`.WBroadcastBeaconTransport`
# 		'multicast' - :class:`.WMulticastBeaconTransport`
# 		'unicast_udp' - not implemented yet
# 		'unicast_tcp' - not implemented yet
# 	"""
#
# 	@verify_type('paranoid', io_handler=WBeaconIOHandler, server_mode=bool)
# 	@verify_type(config=WConfig, transport=(WNetworkNativeTransportProto, None))
# 	def __init__(self, config, io_handler, server_mode, transport=None):
#
# 		if transport is None:
# 			transport_cfg = config['wasp-general::network::beacon']['transport'].lower()
#
# 			if transport_cfg == 'broadcast':
# 				transport = WBroadcastBeaconTransport()
# 			elif transport_cfg == 'multicast':
# 				transport = WMulticastBeaconTransport()
# 			elif transport_cfg == 'unicast_udp':
# 				raise NotImplementedError("This transport doesn't implemented yet")
# 			elif transport_cfg == 'unicast_tcp':
# 				raise NotImplementedError("This transport doesn't implemented yet")
# 			else:
# 				raise ValueError('Invalid beacon transport type: "%s"' % transport_cfg)
#
# 		WNativeSocketHandler.__init__(self, transport, config, io_handler, server_mode)
#
# 	@verify_type('paranoid', io_loop=IOLoop)
# 	def setup_handler(self, io_loop):
# 		""" :meth:`.WIOLoopServiceHandler.setup_handler` implementation. When this object is in
# 		'non-server mode' (client mode), then beacon message is sent
# 		"""
# 		WNativeSocketHandler.setup_handler(self, io_loop)
# 		if self.server_mode() is False:
# 			self.io_handler().transport_socket().sendto(
# 				self.io_handler().messenger().request(self.config()),
# 				self.transport().target_socket(self.config()).pair()
# 			)
#
# class WNetworkBeaconBase(WIOLoopService):
# 	""" Represent service discovery beacon that works over the network. This beacon doesn't interact with network
# 	services like zeroconf, but instead it does all the network discovery work itself. The real work is done
# 	in :class:`.WNetworkServerBeacon` and :class:`.WNetworkClientBeacon` classes.
#
# 	This service automatically creates :class:`.WBeaconHandler` object with the specified io-handler.
# 	"""
#
# 	@verify_type('paranoid', config=WConfig, io_handler=WBeaconIOHandler, server_mode=bool)
# 	@verify_type('paranoid', transport=(WNetworkNativeTransportProto, None), timeout=(int, None))
# 	def __init__(self, config, io_handler, server_mode, transport, timeout=None):
# 		""" Create new beacon service
#
# 		:param config: beacon's configuration
# 		:param io_handler: io-handler to use
# 		:param server_mode: 'server_mode' flag
# 		:param transport: beacon's transport
# 		:param timeout: same as timeout in :meth:`.WIOLoopService.__init__`
# 		"""
# 		handler = WBeaconHandler(config, io_handler, server_mode, transport)
# 		WIOLoopService.__init__(self, handler, timeout=timeout)
#
#
#
# class WBeaconIOHandler(WNativeSocketDirectIOHandler, metaclass=ABCMeta):
# 	""" Basic beacon io-handler.
# 	"""
#
# 	message_maxsize = 1024
# 	""" Network messages maximum size
# 	"""
#
# 	@verify_type(config=WConfig, messanger=(WBeaconMessengerBase, None), callback=(WNetworkBeaconCallback, None))
# 	def __init__(self, config, messenger=None, callback=None):
# 		""" Create new io-handler for beacon
#
# 		:param config: beacon io-configuration
# 		:param messenger: beacon messenger (or None for :class:`.WBeaconMessenger`)
# 		:param callback: beacon callback (or None if it is not required)
# 		"""
# 		WNativeSocketDirectIOHandler.__init__(self)
# 		self.__config = config
# 		self.__messenger = messenger if messenger is not None else WBeaconMessenger()
# 		self.__callback = callback
#
# 	def messenger(self):
# 		""" Return beacon messenger
#
# 		:return: WBeaconMessenger
# 		"""
# 		return self.__messenger
#
# 	def max_size(self):
# 		""" Return maximum message size. (Minimum between this class 'message_maxsize' value and messengers
# 		'message_maxsize' value)
#
# 		:return: int
# 		"""
# 		return min(self.message_maxsize, self.messenger().message_maxsize)
#
# 	def config(self):
# 		""" Return handler`s configuration
#
# 		:return: WConfig
# 		"""
# 		return self.__config
#
# 	def callback(self):
# 		""" Return handler`s callback
#
# 		:return: WNetworkBeaconCallback (or None)
# 		"""
# 		return self.__callback
#
#
# #class WNetworkServerBeacon(WBeaconConfig, WNetworkBeaconBase):
# class WNetworkServerBeacon(WBeaconConfig):
# 	""" Server beacon that is waiting to respond on a valid request and/or process this request with
# 	the specified callback.
# 	"""
#
# 	class Handler(WBeaconIOHandler):
# 		""" Server's handler. Responds on a valid requests, if callback was specified, then it
# 		process client request. If server has received invalid request and 'process_any' flag was set, then
# 		callback (if available) will process this request as invalid
# 		"""
#
# 		@verify_type('paranoid', config=WConfig, messanger=(WBeaconMessengerBase, None))
# 		@verify_type('paranoid', callback=(WNetworkBeaconCallback, None))
# 		@verify_type(process_any=bool)
# 		def __init__(self, config, messenger=None, callback=None, process_any=False):
# 			""" Create new handler
#
# 			:param config: same as config in :meth:`.WBeaconIOHandler.__init__`
# 			:param messenger: same as messenger in :meth:`.WBeaconIOHandler.__init__`
# 			:param callback: same as callback in :meth:`.WBeaconIOHandler.__init__`
# 			:param process_any: should callback process invalid requests or not
# 			"""
# 			WBeaconIOHandler.__init__(self, config, messenger, callback)
# 			self.__process_any = process_any
#
# 		def process_any(self):
# 			""" Return 'process_any' flag, that is currently used
#
# 			:return: bool
# 			"""
# 			return self.__process_any
#
# 		def handler_fn(self, fd, event):
# 			""" :meth:`.WNativeSocketIOHandler.handler_fn` method implementation.
# 			"""
# 			s = self.transport_socket()
# 			messenger = self.messenger()
# 			callback = self.callback()
#
# 			request, client = s.recvfrom(self.max_size())
# 			original_address = WIPV4SocketInfo(client[0], client[1])
#
# 			if messenger.has_response(self.config(), request, original_address) is True:
# 				direction = WNetworkBeaconCallback.WDataDescription.request
#
# 				response = messenger.response(self.config(), request, original_address)
# 				address = messenger.response_address(self.config(), request, original_address)
# 				if callback is not None:
# 					callback(request, original_address, direction)
# 				s.sendto(response, address.pair())
# 			elif self.process_any() is True and callback is not None:
# 				direction = WNetworkBeaconCallback.WDataDescription.invalid_request
#
# 				if messenger.valid_response(self.config(), request, original_address):
# 					callback(request, original_address, direction)
#
# 	@verify_type('paranoid', config=(WConfig, None), config_section=(str, None))
# 	@verify_type('paranoid', messanger=(WBeaconMessengerBase, None), callback=(WNetworkBeaconCallback, None))
# 	@verify_type('paranoid', process_any=bool, transport=(WNetworkNativeTransportProto, None))
# 	def __init__(
# 		self, config=None, config_section=None, messenger=None, callback=None, process_any=False, transport=None
# 	):
# 		""" Create new server beacon
#
# 		:param config: same as config in :meth:`.WBeaconConfig.__init__`
# 		:param config_section: same as config_section in :meth:`.WBeaconConfig.__init__`
# 		:param messenger: same as messenger in :meth:`.WNetworkServerBeacon.Handler.__init__`
# 		:param callback: same as callback in :meth:`.WNetworkServerBeacon.Handler.__init__`
# 		:param process_any: same as process_any in :meth:`.WNetworkServerBeacon.Handler.__init__`
# 		:param transport: same as transport in :meth:`.WNetworkBeaconBase.__init__`
# 		"""
# 		WBeaconConfig.__init__(self, config=config, config_section=config_section)
# 		io_handler = WNetworkServerBeacon.Handler(self.config(), messenger, callback, process_any=process_any)
# 		WNetworkBeaconBase.__init__(self, self.config(), io_handler, True, transport)
#
#
# #class WNetworkClientBeacon(WBeaconConfig, WNetworkBeaconBase):
# class WNetworkClientBeacon(WBeaconConfig):
#
# 	""" Client beacon sends single request and waits for responses for a period of time. This period is specified
# 	in beacons configuration as 'lookup_timeout' option. Client waiting period can be interrupted by calling
# 	the :meth:`.WNetworkClientBeacon.stop` method.
# 	"""
#
# 	class Handler(WBeaconIOHandler):
# 		""" Client handler waits for responses and calls callback if it is available
# 		"""
#
# 		def handler_fn(self, fd, event):
# 			""" :meth:`.WNativeSocketIOHandler.handler_fn` method implementation.
# 			"""
# 			s = self.transport_socket()
# 			messenger = self.messenger()
# 			callback = self.callback()
# 			direction = WNetworkBeaconCallback.WDataDescription.response
#
# 			response, server = s.recvfrom(self.max_size())
#
# 			if callback is not None:
# 				server_si = WIPV4SocketInfo(server[0], server[1])
# 				if messenger.valid_response(self.config(), response, server_si):
# 					callback(response, server_si, direction)
#
# 	@verify_type('paranoid', config=(WConfig, None), config_section=(str, None))
# 	@verify_type('paranoid', messenger=(WBeaconMessengerBase, None), callback=(WNetworkBeaconCallback, None))
# 	@verify_type('paranoid', transport=(WNetworkNativeTransportProto, None))
# 	def __init__(self, config=None, config_section=None, messenger=None, callback=None, transport=None):
# 		""" Create new client beacon
#
# 		:param config: same as config in :meth:`.WBeaconConfig.__init__`
# 		:param config_section: same as config_section in :meth:`.WBeaconConfig.__init__`
# 		:param messenger: same as messenger in :meth:`.WNetworkClientBeacon.Handler.__init__`
# 		:param callback: same as callback in :meth:`.WNetworkClientBeacon.Handler.__init__`
# 		:param transport: same as transport in :meth:`.WNetworkBeaconBase.__init__`
# 		"""
# 		WBeaconConfig.__init__(self, config=config, config_section=config_section)
# 		io_handler = WNetworkClientBeacon.Handler(self.config(), messenger, callback)
# 		timeout = self.config().getint('wasp-general::network::beacon', 'lookup_timeout')
# 		WNetworkBeaconBase.__init__(self, self.config(), io_handler, False, transport, timeout)
