# -*- coding: utf-8 -*-
# wasp_general/network/beacon/beacon.py
#
# Copyright (C) 2016, 2021, 2022 the wasp-general authors and contributors
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

import asyncio
import functools
import json

from wasp_general.verify import verify_type
from wasp_general.network.aio_protocols import WClientDatagramProtocol, WServiceDatagramProtocol
from wasp_general.api.onion import WOnionSession, WOnionSequenceFlow
from wasp_general.api.serialize import WJSONEncoder


class WBeaconServerProtocol(WServiceDatagramProtocol):
	""" Server-side protocol of a simple "beacon" service. Use along with wasp.general.aio_service
	"""

	# noinspection PyMethodMayBeStatic
	def _beacon_response(self, request):
		""" Generate response for a client request

		:param request: request from a client
		:type request: any

		:rtype: any
		"""
		import asyncio

		return {'request': request}

	def datagram_received(self, data, addr):
		""" The :meth:`.asyncio.DatagramProtocol.datagram_received` method implementation

		Receive client request, process it and response

		:param data: client's request
		:type data: bytes

		:param addr: client's address
		:type addr: tuple | str

		:rtype: None
		"""
		sf = WOnionSequenceFlow(
			lambda x: x.decode(),                             # bytes -> str
			json.loads,                                       # json-to-objects
			self._beacon_response,                            # generate response by an object-request
			functools.partial(json.dumps, cls=WJSONEncoder),  # object -> str (as JSON)
			lambda x: x.encode('ascii'),                      # str -> bytes
			lambda x: self._transport.sendto(x, addr),        # bytes -> UDP send
		)
		response = WOnionSession(sf).process(data)
		self._aio_loop.create_task(response)


class WBeaconClientProtocol(WClientDatagramProtocol):
	""" Client-side protocol of a simple "beacon" service. Use along with wasp.general.aio_client
	"""

	def __init__(self):
		""" Create a new protocol instance
		"""
		WClientDatagramProtocol.__init__(self)
		self._server_response = None

	@verify_type('paranoid', remote_address=(tuple, str))
	@verify_type('paranoid', aio_loop=asyncio.AbstractEventLoop)
	def _init_protocol(self, aio_loop, remote_address=None, **kwargs):
		""" The :meth:`.WClientDatagramProtocol._init_protocol` method implementation

		:param aio_loop: as aio_loop in the :meth:`.WClientDatagramProtocol._init_protocol`
		:type aio_loop: asyncio.AbstractEventLoop

		:param remote_address: as remote_address in the :meth:`.WClientDatagramProtocol._init_protocol`
		:type remote_address: tuple | str

		:param kwargs: as kwargs in the :meth:`.WClientDatagramProtocol._init_protocol`

		:rtype: None
		"""
		WClientDatagramProtocol._init_protocol(self, aio_loop, remote_address=remote_address, **kwargs)
		self._server_response = self._aio_loop.create_future()

	# noinspection PyMethodMayBeStatic
	def beacon_request(self):
		""" Service request

		:rtype: any
		"""
		return {}

	def connection_made(self, transport):
		""" The :meth:`.asyncio.DatagramProtocol.connection_made` method implementation

		Connect to the server, wait for the response and save server's response

		:param transport: transport that is used within a connection
		:type transport: asyncio.DatagramTransport

		# TODO: add a timeout for a server response!
		"""
		WClientDatagramProtocol.connection_made(self, transport)

		sf = WOnionSequenceFlow(
			lambda x: self.beacon_request(),                            # -> object
			functools.partial(json.dumps, cls=WJSONEncoder),            # object -> str (as JSON)
			lambda x: x.encode('ascii'),                                # str -> bytes
			lambda x: self._transport.sendto(x, self._remote_address),  # bytes -> UDP send
			lambda x: self._server_response,                            # wait for UDP response
			lambda x: x.decode(),                                       # bytes -> str
			json.loads,                                                 # str (as JSON) -> object
			lambda x: self._request_complete.set_result(x),             # save response as a result
		)
		response = WOnionSession(sf).process(None)
		self._aio_loop.create_task(response)


	def datagram_received(self, data, addr):
		""" The :meth:`.asyncio.DatagramProtocol.datagram_received` method implementation

		Receive server's response

		:param data: server's response
		:type data: bytes

		:param addr: server's address
		:type addr: tuple | str

		:rtype: None
		"""
		self._server_response.set_result(data)
