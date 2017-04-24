# -*- coding: utf-8 -*-
# wasp_general/network/messenger/talker.py
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

# TODO: document the code
# TODO: write tests for the code
# TODO: core and common IOLoop functionality may be selected from this and WNetworkBeacon classes to a separate module

from zmq.eventloop.ioloop import IOLoop


class WNetworkTalker:

	def __init__(self, server_mode=True):
		self.__loop = IOLoop()
		self.__server_mode = server_mode

	def server_mode(self):
		""" Return whether this is a server or client. (True if this is a server, False if client)

		:return: bool
		"""
		return self.__server_mode

	def start(self):

		#max_message_size = min(self.message_maxsize, self.__messenger.message_maxsize)

		if self.server_mode() is True:
			s = self.transport().server_socket(self.config())

			def server_handler(fd, event):
				request, client = s.recvfrom(max_message_size)
				original_address = WIPV4SocketInfo(client[0], client[1])

				if self.__messenger.has_response(self.config(), request, original_address) is True:
					response = self.__messenger.response(self.config(), request, original_address)
					address = self.__messenger.response_address(
						self.config(), request, original_address
					)

					if self.__callback is not None:
						description = WNetworkBeaconCallback.WDataDescription.request
						self.__callback(request, original_address, description)

					s.sendto(response, address.pair())
				elif self.__server_receives is True and self.__callback is not None:
					if self.__messenger.valid_response(self.config(), request, original_address):
						description = WNetworkBeaconCallback.WDataDescription.response
						self.__callback(request, original_address, description)

			self.__loop.add_handler(s.fileno(), server_handler, self.__loop.READ)
			self.__loop.start()
			self.transport().close_server_socket(self.config())
		else:
			pass
			'''
			s = self.transport().client_socket(self.config())
			timeout = self.config().getint('wasp-network::beacon', 'lookup_timeout')

			def client_handler(fd, event):
				response, server = s.recvfrom(max_message_size)

				if self.__callback is not None:
					server_si = WIPV4SocketInfo(server[0], server[1])
					if self.__messenger.valid_response(self.config(), response, server_si):
						description = WNetworkBeaconCallback.WDataDescription.response
						self.__callback(response, server_si, description)

			def client_lookup_fin():
				self.__loop.stop()

			self.__loop.add_handler(s.fileno(), client_handler, self.__loop.READ)
			self.__loop.add_timeout(timedelta(0, timeout), client_lookup_fin)
			s.sendto(self.__messenger.request(
				self.config()), self.transport().target_socket(self.config()).pair()
			)
			self.__loop.start()
			self.transport().close_client_socket(self.config())
			'''

	def stop(self):
		self.__loop.stop()

	def loop(self):
		""" Return IOLoop object

		:return: IOLoop
		"""
		return self.__loop

