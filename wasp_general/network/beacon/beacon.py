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
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

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


class WBeaconConfig(metaclass=ABCMeta):
	""" Abstract class that represent service discovery beacon configuration
	"""

	@verify_type(config=(WConfig, None), config_section=(str, None))
	def __init__(self, config=None, config_section=None):
		""" Merge configuration to this beacon

		:param config: configuration storage
		:param config_section: configuration section name where options are
		"""
		self.__configuration = WConfig()
		self.__configuration.merge(os.path.join(os.path.dirname(__file__), '..', '..', 'defaults.ini'))
		if config is not None:
			self.__configuration.merge_section(config, 'wasp-general::network::beacon', section_from=config_section)

	def config(self):
		""" Return beacon configuration

		:return: WConfig
		"""
		return self.__configuration


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


class WBeaconIOHandler(WNativeSocketDirectIOHandler, metaclass=ABCMeta):
	""" Basic beacon io-handler.
	"""

	message_maxsize = 1024
	""" Network messages maximum size
	"""

	@verify_type(config=WConfig, messanger=(WBeaconMessengerBase, None), callback=(WNetworkBeaconCallback, None))
	def __init__(self, config, messenger=None, callback=None):
		""" Create new io-handler for beacon

		:param config: beacon io-configuration
		:param messenger: beacon messenger (or None for :class:`.WBeaconMessenger`)
		:param callback: beacon callback (or None if it is not required)
		"""
		WNativeSocketDirectIOHandler.__init__(self)
		self.__config = config
		self.__messenger = messenger if messenger is not None else WBeaconMessenger()
		self.__callback = callback

	def messenger(self):
		""" Return beacon messenger

		:return: WBeaconMessenger
		"""
		return self.__messenger

	def max_size(self):
		""" Return maximum message size. (Minimum between this class 'message_maxsize' value and messengers
		'message_maxsize' value)

		:return: int
		"""
		return min(self.message_maxsize, self.messenger().message_maxsize)

	def config(self):
		""" Return handler`s configuration

		:return: WConfig
		"""
		return self.__config

	def callback(self):
		""" Return handler`s callback

		:return: WNetworkBeaconCallback (or None)
		"""
		return self.__callback


class WBeaconHandler(WNativeSocketHandler):
	""" Beacon's loop-handler. Is capable to create required transport (that is specified in the beacon's
	configuration) Depends on configuration value, the following classes is used:

		'broadcast' (default) - :class:`.WBroadcastBeaconTransport`
		'multicast' - :class:`.WMulticastBeaconTransport`
		'unicast_udp' - not implemented yet
		'unicast_tcp' - not implemented yet
	"""

	@verify_type('paranoid', io_handler=WBeaconIOHandler, server_mode=bool)
	@verify_type(config=WConfig, transport=(WNetworkNativeTransportProto, None))
	def __init__(self, config, io_handler, server_mode, transport=None):

		if transport is None:
			transport_cfg = config['wasp-general::network::beacon']['transport'].lower()

			if transport_cfg == 'broadcast':
				transport = WBroadcastBeaconTransport()
			elif transport_cfg == 'multicast':
				transport = WMulticastBeaconTransport()
			elif transport_cfg == 'unicast_udp':
				raise NotImplementedError("This transport doesn't implemented yet")
			elif transport_cfg == 'unicast_tcp':
				raise NotImplementedError("This transport doesn't implemented yet")
			else:
				raise ValueError('Invalid beacon transport type: "%s"' % transport_cfg)

		WNativeSocketHandler.__init__(self, transport, config, io_handler, server_mode)

	@verify_type('paranoid', io_loop=IOLoop)
	def setup_handler(self, io_loop):
		""" :meth:`.WIOLoopServiceHandler.setup_handler` implementation. When this object is in
		'non-server mode' (client mode), then beacon message is sent
		"""
		WNativeSocketHandler.setup_handler(self, io_loop)
		if self.server_mode() is False:
			self.io_handler().transport_socket().sendto(
				self.io_handler().messenger().request(self.config()),
				self.transport().target_socket(self.config()).pair()
			)


class WNetworkBeaconBase(WIOLoopService):
	""" Represent service discovery beacon that works over the network. This beacon doesn't interact with network
	services like zeroconf, but instead it does all the network discovery work itself. The real work is done
	in :class:`.WNetworkServerBeacon` and :class:`.WNetworkClientBeacon` classes.

	This service automatically creates :class:`.WBeaconHandler` object with the specified io-handler.
	"""

	@verify_type('paranoid', config=WConfig, io_handler=WBeaconIOHandler, server_mode=bool)
	@verify_type('paranoid', transport=(WNetworkNativeTransportProto, None), timeout=(int, None))
	def __init__(self, config, io_handler, server_mode, transport, timeout=None):
		""" Create new beacon service

		:param config: beacon's configuration
		:param io_handler: io-handler to use
		:param server_mode: 'server_mode' flag
		:param transport: beacon's transport
		:param timeout: same as timeout in :meth:`.WIOLoopService.__init__`
		"""
		handler = WBeaconHandler(config, io_handler, server_mode, transport)
		WIOLoopService.__init__(self, handler, timeout=timeout)


class WNetworkServerBeacon(WBeaconConfig, WNetworkBeaconBase):
	""" Server beacon that is waiting to respond on a valid request and/or process this request with
	the specified callback.
	"""

	class Handler(WBeaconIOHandler):
		""" Server's handler. Responds on a valid requests, if callback was specified, then it
		process client request. If server has received invalid request and 'process_any' flag was set, then
		callback (if available) will process this request as invalid
		"""

		@verify_type('paranoid', config=WConfig, messanger=(WBeaconMessengerBase, None))
		@verify_type('paranoid', callback=(WNetworkBeaconCallback, None))
		@verify_type(process_any=bool)
		def __init__(self, config, messenger=None, callback=None, process_any=False):
			""" Create new handler

			:param config: same as config in :meth:`.WBeaconIOHandler.__init__`
			:param messenger: same as messenger in :meth:`.WBeaconIOHandler.__init__`
			:param callback: same as callback in :meth:`.WBeaconIOHandler.__init__`
			:param process_any: should callback process invalid requests or not
			"""
			WBeaconIOHandler.__init__(self, config, messenger, callback)
			self.__process_any = process_any

		def process_any(self):
			""" Return 'process_any' flag, that is currently used

			:return: bool
			"""
			return self.__process_any

		def handler_fn(self, fd, event):
			""" :meth:`.WNativeSocketIOHandler.handler_fn` method implementation.
			"""
			s = self.transport_socket()
			messenger = self.messenger()
			callback = self.callback()

			request, client = s.recvfrom(self.max_size())
			original_address = WIPV4SocketInfo(client[0], client[1])

			if messenger.has_response(self.config(), request, original_address) is True:
				direction = WNetworkBeaconCallback.WDataDescription.request

				response = messenger.response(self.config(), request, original_address)
				address = messenger.response_address(self.config(), request, original_address)
				if callback is not None:
					callback(request, original_address, direction)
				s.sendto(response, address.pair())
			elif self.process_any() is True and callback is not None:
				direction = WNetworkBeaconCallback.WDataDescription.invalid_request

				if messenger.valid_response(self.config(), request, original_address):
					callback(request, original_address, direction)

	@verify_type('paranoid', config=(WConfig, None), config_section=(str, None))
	@verify_type('paranoid', messanger=(WBeaconMessengerBase, None), callback=(WNetworkBeaconCallback, None))
	@verify_type('paranoid', process_any=bool, transport=(WNetworkNativeTransportProto, None))
	def __init__(
		self, config=None, config_section=None, messenger=None, callback=None, process_any=False, transport=None
	):
		""" Create new server beacon

		:param config: same as config in :meth:`.WBeaconConfig.__init__`
		:param config_section: same as config_section in :meth:`.WBeaconConfig.__init__`
		:param messenger: same as messenger in :meth:`.WNetworkServerBeacon.Handler.__init__`
		:param callback: same as callback in :meth:`.WNetworkServerBeacon.Handler.__init__`
		:param process_any: same as process_any in :meth:`.WNetworkServerBeacon.Handler.__init__`
		:param transport: same as transport in :meth:`.WNetworkBeaconBase.__init__`
		"""
		WBeaconConfig.__init__(self, config=config, config_section=config_section)
		io_handler = WNetworkServerBeacon.Handler(self.config(), messenger, callback, process_any=process_any)
		WNetworkBeaconBase.__init__(self, self.config(), io_handler, True, transport)


class WNetworkClientBeacon(WBeaconConfig, WNetworkBeaconBase):
	""" Client beacon sends single request and waits for responses for a period of time. This period is specified
	in beacons configuration as 'lookup_timeout' option. Client waiting period can be interrupted by calling
	the :meth:`.WNetworkClientBeacon.stop` method.
	"""

	class Handler(WBeaconIOHandler):
		""" Client handler waits for responses and calls callback if it is available
		"""

		def handler_fn(self, fd, event):
			""" :meth:`.WNativeSocketIOHandler.handler_fn` method implementation.
			"""
			s = self.transport_socket()
			messenger = self.messenger()
			callback = self.callback()
			direction = WNetworkBeaconCallback.WDataDescription.response

			response, server = s.recvfrom(self.max_size())

			if callback is not None:
				server_si = WIPV4SocketInfo(server[0], server[1])
				if messenger.valid_response(self.config(), response, server_si):
					callback(response, server_si, direction)

	@verify_type('paranoid', config=(WConfig, None), config_section=(str, None))
	@verify_type('paranoid', messenger=(WBeaconMessengerBase, None), callback=(WNetworkBeaconCallback, None))
	@verify_type('paranoid', transport=(WNetworkNativeTransportProto, None))
	def __init__(self, config=None, config_section=None, messenger=None, callback=None, transport=None):
		""" Create new client beacon

		:param config: same as config in :meth:`.WBeaconConfig.__init__`
		:param config_section: same as config_section in :meth:`.WBeaconConfig.__init__`
		:param messenger: same as messenger in :meth:`.WNetworkClientBeacon.Handler.__init__`
		:param callback: same as callback in :meth:`.WNetworkClientBeacon.Handler.__init__`
		:param transport: same as transport in :meth:`.WNetworkBeaconBase.__init__`
		"""
		WBeaconConfig.__init__(self, config=config, config_section=config_section)
		io_handler = WNetworkClientBeacon.Handler(self.config(), messenger, callback)
		timeout = self.config().getint('wasp-general::network::beacon', 'lookup_timeout')
		WNetworkBeaconBase.__init__(self, self.config(), io_handler, False, transport, timeout)
