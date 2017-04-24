# -*- coding: utf-8 -*-
# wasp_general/network/beacon/transport.py
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

from wasp_general.network.transport import WNetworkNativeTransportSocketConfig, WBroadcastNetworkTransport
from wasp_general.network.transport import WMulticastNetworkTransport


server_configuration = WNetworkNativeTransportSocketConfig('wasp-general::network::beacon', 'bind_address', 'port')
"""
Server side use 'bind_address' options to set up listening socket. Server will be able to receive requests
only at this address. Default is '' (empty string) that works as '0.0.0.0' address, in this case server will
be able to receive requests at any address defined in the system.
"""

client_configuration = WNetworkNativeTransportSocketConfig('wasp-general::network::beacon', 'address', 'port')
"""
Mainly. 'address' and 'port' options are used on client side for destination definition (for server
destination). This options can be used for address validation on server side also. For example,
in :class:`.WMulticastBeaconTransport` class 'address' checks if it is a valid multicast address,
in :class:`.WBroadcastBeaconTransport` class 'address' checks if it is a IPv4 address.
"""


class WBroadcastBeaconTransport(WBroadcastNetworkTransport):
	""" Network beacon transport, that uses IPv4 broadcast communication
	"""

	def __init__(self):
		""" Create new broadcast transport
		"""
		WBroadcastNetworkTransport.__init__(self, client_configuration, server_configuration)


class WMulticastBeaconTransport(WMulticastNetworkTransport):
	""" Network beacon transport, that uses IPv4 multicast communication
	"""

	def __init__(self):
		""" Create new multicast transport
		"""
		WMulticastNetworkTransport.__init__(self, client_configuration, server_configuration)
