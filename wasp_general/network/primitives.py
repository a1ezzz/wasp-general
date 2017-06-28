# -*- coding: utf-8 -*-
# wasp_general/network/primitives.py
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

import re

from wasp_general.verify import verify_type, verify_value

from wasp_general.types.binarray import WBinArray
from wasp_general.types.bytearray import WFixedSizeByteArray


class WMACAddress:
	""" Represent Ethernet/WiFi MAC address.

	see also https://en.wikipedia.org/wiki/MAC_address
	"""

	octet_count = 6
	""" Address bytes count
	"""

	re_dash_format = re.compile(
		"^[0-9a-fA-F]{2}-[0-9a-fA-F]{2}-[0-9a-fA-F]{2}-[0-9a-fA-F]{2}-[0-9a-fA-F]{2}-[0-9a-fA-F]{2}$"
	)
	""" Regular expression for "dash"-written MAC address like '00-11-22-33-44-55'
	"""
	re_colon_format = re.compile(
		"^[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}$"
	)
	""" Regular expression for "colon"-written MAC address like '00:11:22:33:44:55'
	"""
	re_cisco_format = re.compile("^[0-9a-fA-F]{4}.[0-9a-fA-F]{4}.[0-9a-fA-F]{4}$")
	""" Regular expression for MAC address written in "Cisco" style like '0011.2233.4455'
	"""
	re_spaceless_format = re.compile("^[0-9a-fA-F]{12}$")
	""" Regular expression for MAC address written without separator like '001122334455'
	"""

	@verify_type('paranoid', address=(str, WBinArray, int, None))
	def __init__(self, address=None):
		""" Construct new address

		:param address: value with which this address is initialized (zeroes are used by default).
		"""
		self.__address = WFixedSizeByteArray(WMACAddress.octet_count)

		if address is not None:
			if isinstance(address, str):
				self.__address = WFixedSizeByteArray(
					WMACAddress.octet_count, WMACAddress.from_string(address).bin_address()
				)
			else:
				self.__address = WFixedSizeByteArray(WMACAddress.octet_count, address)

	def bin_address(self):
		""" Get this address as sequence of bits

		:return: WBinArray
		"""
		return self.__address.bin_value()

	@staticmethod
	@verify_type(address=str)
	def from_string(address):
		""" Return new object by the given MAC-address

		:param address: address to convert
		:return: WMACAddress
		"""
		str_address = None

		if WMACAddress.re_dash_format.match(address):
			str_address = "".join(address.split("-"))
		elif WMACAddress.re_colon_format.match(address):
			str_address = "".join(address.split(":"))
		elif WMACAddress.re_cisco_format.match(address):
			str_address = "".join(address.split("."))
		elif WMACAddress.re_spaceless_format.match(address):
			str_address = address

		if str_address is None:
			raise ValueError("Invalid MAC address format: " + address)

		result = WMACAddress()
		for octet_index in range(WMACAddress.octet_count):
			octet = str_address[:2]
			result.__address[octet_index] = int(octet, 16)
			str_address = str_address[2:]

		return result

	def __str__(self):
		""" Convert to string

		:return: str
		"""
		address = ["{:02x}".format(int(x)) for x in self.__address]
		return ':'.join(address)

	def __bytes__(self):
		""" Convert to bytes

		:return: bytes
		"""
		return bytes(self.__address)


class WIPV4Address:
	""" Represent IPv4 address.

	see also https://en.wikipedia.org/wiki/IPv4#Address_representations
	"""

	octet_count = 4
	""" Address bytes count
	"""

	@verify_type('paranoid', address=(str, bytes, WBinArray, int, None))
	def __init__(self, address=None):
		""" Create new address

		:param address: value with which this address is initialized (zeroes are used by default).
		"""
		self.__address = WFixedSizeByteArray(WIPV4Address.octet_count)

		if address is not None:
			if isinstance(address, str):
				self.__address = WFixedSizeByteArray(
					WIPV4Address.octet_count, WIPV4Address.from_string(address).bin_address()
				)
			else:
				self.__address = WFixedSizeByteArray(WIPV4Address.octet_count, address)

	def bin_address(self):
		""" Convert address to WBinArray

		:return: WBinArray
		"""
		return self.__address.bin_value()

	def __bytes__(self):
		""" Convert address to bytes

		:return: bytes
		"""
		return bytes(self.__address)

	@staticmethod
	@verify_type(address=str)
	def from_string(address):
		""" Parse string for IPv4 address

		:param address: address to parse
		:return:
		"""
		address = address.split('.')
		if len(address) != WIPV4Address.octet_count:
			raise ValueError('Invalid ip address: %s' % address)

		result = WIPV4Address()
		for i in range(WIPV4Address.octet_count):
			result.__address[i] = WBinArray(int(address[i]), WFixedSizeByteArray.byte_size)
		return result

	@staticmethod
	@verify_type(dns_format=bool)
	def to_string(address, dns_format=False):
		""" Convert address to string

		:param address: WIPV4Address to convert
		:param dns_format: whether to use arpa-format or not
		:return:
		"""
		if isinstance(address, WIPV4Address) is False:
			raise TypeError('Invalid address type')

		address = [str(int(x)) for x in address.__address]
		if dns_format is False:
			return '.'.join(address)
		address.reverse()
		return ('.'.join(address) + '.in-addr.arpa')

	def __str__(self):
		return WIPV4Address.to_string(self)


class WNetworkIPV4:
	""" This class represent IPv4 network address. Depends on a flag network_address (that is passed to constructor)
	object can represent separate host address with network mask or be an address of a IP network.

	see also https://en.wikipedia.org/wiki/IPv4
	"""

	delimiter = '/'
	""" Separator that separate network address from network mask.
	"""

	@verify_type(address=(str, tuple, list, set), network_address=bool)
	@verify_value(address=lambda x: isinstance(x, (tuple, list, set)) is False or len(x) == 2)
	@verify_value(address=lambda x: isinstance(x, (tuple, list, set)) is False or isinstance(x[0], WIPV4Address))
	@verify_value(address=lambda x: isinstance(x, (tuple, list, set)) is False or isinstance(x[1], int))
	def __init__(self, address, network_address=True):
		""" Construct new network address

		:param address: address as a string or as tuple/list/set. where the first element is WIPV4Address and \
		the second one is network mask (as bits count)
		:param network_address: whether this object is host address with network mask or an address of a network
		"""

		if isinstance(address, str) is True:
			ip_address, self.__mask = address.strip().split(WNetworkIPV4.delimiter)
			self.__address = WIPV4Address(ip_address)
		else:
			self.__address = address[0]
			self.__mask = address[1]

		self.__mask = int(self.__mask)
		if self.__mask < 0 or self.__mask > len(self.__address.bin_address()):
			raise ValueError(
				'Invalid network mask: %s (network specified: %s)' % (str(self.__mask), address)
			)

		self.__network_address__ = network_address
		if network_address:
			bin_address = self.__address.bin_address()
			if int(bin_address[self.__mask:]) != 0:
				raise ValueError(
					'Invalid network mask: %s (network specified: %s)' % (str(self.__mask), address)
				)

	def address(self):
		""" Return IP address

		:return: WIPV4Address
		"""
		return self.__address

	def mask(self):
		""" Return network mask (as bits count)

		:return: int
		"""
		return self.__mask

	@verify_type(skip_network_address=bool)
	def first_address(self, skip_network_address=True):
		""" Return the first IP address of this network

		:param skip_network_address: this flag specifies whether this function returns address of the network \
		or returns address that follows address of the network (address, that a host could have)
		:return: WIPV4Address
		"""
		bin_address = self.__address.bin_address()
		bin_address_length = len(bin_address)
		if self.__mask > (bin_address_length - 2):
			skip_network_address = False

		for i in range(bin_address_length - self.__mask):
			bin_address[self.__mask + i] = 0

		if skip_network_address:
			bin_address[bin_address_length - 1] = 1

		return WIPV4Address(bin_address)

	@verify_type(skip_broadcast_address=bool)
	def last_address(self, skip_broadcast_address=True):
		""" Return the last IP address of this network

		:param skip_broadcast_address: this flag specifies whether to skip the very last address (that is \
		usually used as broadcast address) or not.
		:return: WIPV4Address
		"""
		bin_address = self.__address.bin_address()
		bin_address_length = len(bin_address)
		if self.__mask > (bin_address_length - 2):
			skip_broadcast_address = False

		for i in range(bin_address_length - self.__mask):
			bin_address[self.__mask + i] = 1

		if skip_broadcast_address:
			bin_address[bin_address_length - 1] = 0

		return WIPV4Address(bin_address)

	def iterator(self, skip_network_address=True, skip_broadcast_address=True):
		""" Return iterator, that can iterate over network addresses

		:param skip_network_address: same as skip_network_address in :meth:`.NetworkIPV4.first_address` method
		:param skip_broadcast_address: same as skip_broadcast_address in :meth:`.NetworkIPV4.last_address` \
		method
		:return: NetworkIPV4Iterator
		"""
		return WNetworkIPV4Iterator(self, skip_network_address, skip_broadcast_address)

	@verify_type(address=WIPV4Address)
	def __contains__(self, address):
		""" Check if this network contains specified IP address.

		:param address: address to check
		:return: bool
		"""
		int_value = int(address.bin_address())
		first_address = int(self.first_address().bin_address())
		last_address = int(self.last_address().bin_address())
		return int_value >= first_address and int_value <= last_address

	@staticmethod
	@verify_type(address=WIPV4Address)
	def is_multicast(address):
		""" Check if address is a multicast address.

		:param address: IP address to check
		:return: bool

		see also https://tools.ietf.org/html/rfc5771
		"""
		return address in WNetworkIPV4('224.0.0.0/4')


class WNetworkIPV4Iterator:
	""" This iterator iterates over IP network addresses.
	"""

	@verify_type(network=(WIPV4Address, WNetworkIPV4), skip_network_address=bool, skip_broadcast_address=bool)
	def __init__(self, network, skip_network_address=True, skip_broadcast_address=True):
		""" Create new iterator

		:param network: network to iterate. If it is WIPV4Address instance, then iterate over single address
		:param skip_network_address: same as skip_network_address in :meth:`.NetworkIPV4.first_address` method
		:param skip_broadcast_address: same as skip_broadcast_address in :meth:`.NetworkIPV4.last_address` \
		method
		"""
		if isinstance(network, WIPV4Address) is True:
			self.__network = WNetworkIPV4((network, len(network.bin_address())))
		else:
			# isinstance(network, NetworkIPV4) is True
			self.__network = network

		self.__skip_network_address = skip_network_address
		self.__skip_broadcast_address = skip_broadcast_address

	def __iter__(self):
		""" Iterate call

		:return: None
		"""
		first_address = self.__network.first_address(skip_network_address=self.__skip_network_address)
		last_address = self.__network.last_address(skip_broadcast_address=self.__skip_broadcast_address)

		for i in range(int(first_address.bin_address()), int(last_address.bin_address()) + 1):
			yield WIPV4Address(i)


class WIPPort:
	""" Represent TCP/UDP IP port

	see also:
	https://en.wikipedia.org/wiki/Transmission_Control_Protocol#TCP_ports
	https://en.wikipedia.org/wiki/User_Datagram_Protocol#Service_ports
	"""

	minimum_port_number = 1
	""" Minimum port number
	"""
	maximum_port_number = 65535
	""" Maximum port number
	"""

	@verify_type(port=int)
	@verify_value(port=lambda x: WIPPort.minimum_port_number <= x <= WIPPort.maximum_port_number)
	def __init__(self, port):
		""" Construct new IP port

		:param port: initialization value
		"""
		self.__port = port

	def __int__(self):
		""" Return port number as int
		:return: int
		"""
		return self.__port

	def __str__(self):
		""" Return port number as string
		:return: str
		"""
		return str(self.__port)


class WFQDN:
	""" Represent single fully qualified domain name (FQDN).

	see also https://en.wikipedia.org/wiki/Fully_qualified_domain_name
	"""

	re_label = re.compile('^[a-zA-Z0-9\-]{1,63}$')
	""" Regular expression for FQDN label (sequence between dots) as is specified in ....
	"""

	maximum_fqdn_length = 253

	@verify_type(address=(str, list, tuple, set, None))
	def __init__(self, address=None):
		""" Construct new FQDN. If no address is specified, then this FQDN represent root node, which is '.'

		:param address: FQDN address in string or in list/tuple/set of labels
		"""
		self._labels = []

		if isinstance(address, str) is True:
			self._labels = WFQDN.from_string(address)._labels
		elif isinstance(address, (list, tuple, set)) is True:
			self._labels = WFQDN.from_string('.'.join(address))._labels

	@staticmethod
	@verify_type(address=str)
	def from_string(address):
		""" Convert doted-written FQDN address to WFQDN object

		:param address: address to convert
		:return: WFQDN
		"""
		if len(address) == 0:
			return WFQDN()

		if address[-1] == '.':
			address = address[:-1]

		if len(address) > WFQDN.maximum_fqdn_length:
			raise ValueError('Invalid address')

		result = WFQDN()
		for label in address.split('.'):
			if isinstance(label, str) and WFQDN.re_label.match(label):
				result._labels.append(label)
			else:
				raise ValueError('Invalid address')

		return result

	@staticmethod
	@verify_type(leading_dot=bool)
	def to_string(address, leading_dot=False):
		""" Return doted-written address by the given WFQDN object

		:param address: address to convert
		:param leading_dot: whether this function place leading dot to the result or not
		:return: str
		"""

		if isinstance(address, WFQDN) is False:
			raise TypeError('Invalid type for FQDN address')

		result = '.'.join(address._labels)
		return result if leading_dot is False else (result + '.')

	def __str__(self):
		""" Return string

		:return: str
		"""
		return WFQDN.to_string(self)

	@staticmethod
	@verify_type(idn_fqdn=str)
	def punycode(idn_fqdn):
		""" Create WFQDN from IDN (Internationalized domain name) by reverting it to punycode

		:param idn_fqdn: internationalized domain name to convert
		:return: WFQDN

		see also https://en.wikipedia.org/wiki/Internationalized_domain_name
		see also https://en.wikipedia.org/wiki/Punycode
		"""
		return WFQDN(idn_fqdn.encode('idna').decode('ascii'))


class WIPV4SocketInfo:
	""" Represent socket information - IP address (or domain name) and port number. Mainly used for python socket
	module.

	see :meth:`.WIPV4SocketInfo.pair`
	"""

	@verify_type('paranoid', address=(WFQDN, WIPV4Address, str, WBinArray, int, None), port=(WIPPort, int, None))
	def __init__(self, address=None, port=None):
		""" Construct new pair

		:param address: associated IP address
		:param port: associated IP port
		"""
		self.__address = None
		if address is not None:
			if isinstance(address, (WFQDN, WIPV4Address)) is True:
				self.__address = address
			elif isinstance(address, (WBinArray, int)) is True:
				self.__address = WIPV4Address(address)
			else:
				self.__address = WIPV4SocketInfo.parse_address(address)

		self.__port = None
		if port is not None:
			self.__port = port if isinstance(port, WIPPort) else WIPPort(port)

	def address(self):
		""" Return associated IP address or None if not available

		:return: WIPV4Address or WFQDN
		"""
		return self.__address

	def port(self):
		""" Return associated IP port or None if not available

		:return: WIPPort
		"""
		return self.__port

	def pair(self):
		""" Return tuple (address, port), where address is a string (empty string if self.address() is None) and
		port is an integer (zero if self.port() is None). Mainly, this tuple is used with python socket module
		(like in bind method)

		:return: 2 value tuple of str and int.
		"""
		address = str(self.__address) if self.__address is not None else ''
		port = int(self.__port) if self.__port is not None else 0
		return address, port

	@staticmethod
	@verify_type(address=str)
	def parse_address(address):
		""" Parse string and return :class:`.WIPV4Address` object if an IP address is specified,
		:class:`.WFQDN` if domain name is specified and None if the string is empty.

		:param address: string to parse
		:return: WIPV4Address or WFQDN or None
		"""

		if len(address) == 0:
			return None

		try:
			return WIPV4Address(address)
		except ValueError:
			pass

		try:
			return WFQDN(address)
		except ValueError:
			pass

		raise ValueError('Unable to parse address string. It must be an IP address or FQDN')
