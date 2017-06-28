# -*- coding: utf-8 -*-
# wasp_general/network/beacon/messenger.py
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

# TODO: Merge with wasp_general.network.messenger

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import re
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value
from wasp_general.config import WConfig

from wasp_general.network.primitives import WIPV4SocketInfo, WIPPort


class WBeaconMessengerBase(metaclass=ABCMeta):
	""" This is interface for classes, that implement communication (messaging) logic for beacons

	see also: :class:`.WNetworkBeacon`
	"""
	message_maxsize = 512

	@abstractmethod
	@verify_type(beacon_config=WConfig)
	def request(self, beacon_config):
		""" Generate client request for beacon. It is calling from client side.

		:param beacon_config: client beacon configuration.
		:return: bytes
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(beacon_config=WConfig, request=bytes, client_address=WIPV4SocketInfo)
	def has_response(self, beacon_config, request, client_address):
		""" Whether this messenger has response or it must skip the request. Return True if there is a response,
		otherwise - False. If this method returns False, then calling a :meth:`.WBeaconMessengerBase.response`
		method treats as error.

		:param beacon_config:
		:param request:
		:param client_address:
		:return: bool
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(beacon_config=WConfig, request=bytes, client_address=WIPV4SocketInfo)
	def response(self, beacon_config, request, client_address):
		""" Generate server response for clients request. Obviously, it is calling from server side

		:param beacon_config: server beacon configuration
		:param request: client request message
		:param client_address: client address
		:return: bytes
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(beacon_config=WConfig, request=bytes, client_address=WIPV4SocketInfo)
	def response_address(self, beacon_config, request, client_address):
		""" Return client address where server must send response. It is Possible, that address where server
		must send response is different then the origin address. In that case, client address
		is encoded in request message.

		:param beacon_config: server configuration
		:param request: client request message
		:param client_address: original client address
		:return: WIPV4SocketInfo
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(beacon_config=WConfig, response=bytes, server_address=WIPV4SocketInfo)
	def valid_response(self, beacon_config, response, server_address):
		""" Return True if server response isn't junk.

		:param beacon_config: client beacon configuration
		:param response: server response
		:param server_address: original server address
		:return: bool
		"""
		raise NotImplementedError('This method is abstract')


class WBeaconMessenger(WBeaconMessengerBase):
	""" Simple. Demo/debug messenger. Server side just return original hello message to the sender.
	"""

	__beacon_hello_msg__ = b'HELLO'
	""" Client request
	"""

	@verify_type('paranoid', beacon_config=WConfig)
	def request(self, beacon_config):
		""" :meth:`.WBeaconMessengerBase.request` method implementation.
		Sends :attr:`.WBeaconMessenger.__beacon_hello_msg__` to a server
		"""
		return self.__beacon_hello_msg__

	@verify_type('paranoid', beacon_config=WConfig, client_address=WIPV4SocketInfo)
	@verify_type(request=bytes)
	def has_response(self, beacon_config, request, client_address):
		""" :meth:`.WBeaconMessengerBase.has_response` method implementation. This class has a response only if
		the request wasn't empty
		"""
		return True if len(request) > 0 else False

	@verify_type('paranoid', beacon_config=WConfig, client_address=WIPV4SocketInfo)
	@verify_type(request=bytes)
	def response(self, beacon_config, request, client_address):
		""" :meth:`.WBeaconMessengerBase.response` method implementation.
		In response sends the same data as server has got
		"""
		return request

	@verify_type('paranoid', beacon_config=WConfig, request=bytes)
	@verify_type(client_address=WIPV4SocketInfo)
	def response_address(self, beacon_config, request, client_address):
		""" :meth:`.WBeaconMessengerBase.request` method implementation.
		Return the same address, that server detects (assume that clients address is correct)
		"""
		return client_address

	@verify_type('paranoid', beacon_config=WConfig, response=bytes, server_address=WIPV4SocketInfo)
	@verify_type(response=bytes)
	def valid_response(self, beacon_config, response, server_address):
		""" :meth:`.WBeaconMessengerBase.valid_response` method implementation. Response is valid if it has
		anything.
		"""
		return True if len(response) > 0 else False


class WBeaconGouverneurMessenger(WBeaconMessengerBase):
	""" Basic and real messenger implementation. Request and response are generated the same way, but have different
	meaning. Messages are generated the following way:
	[Message header]<:[Address<:TCP/UDP port>]>
	"Message header" is the first part of the message and it must be exactly the same for client or server.
	If server has got message with header that doesn't match its own header, such messages will be omitted.
	Next parts are "Address" and "TCP/UDP port". These parts are separated
	by the :attr:`.WBeaconGouverneurMessenger.__message_splitter__` separator. "TCP/UDP port" can't be specified
	without an "Address" An "Address" field can be an IP address or a domain name.

	For the client "Address" and "UDP Port" are treated as address where server must send the response.
	But for the server, they are treated as the address, that the server publish. For both type of messages
	"Address" and "TCP/UDP port" are generated from a configuration. Options are located
	in 'wasp-general::network::beacon' section. Configuration option "public_address" is used as "Address"
	value and option "public_port" is used as "UDP Port"
	"""

	__message_splitter__ = b':'
	""" Delimiter, that is used for header, IP address and port separation.
	"""

	@verify_type(hello_message=bytes, invert_hello=bool)
	@verify_value(hello_message=lambda x: len(x.decode('ascii')) >= 0)
	@verify_value(hello_message=lambda x: WBeaconGouverneurMessenger.__message_splitter__ not in x)
	def __init__(self, hello_message, invert_hello=False):
		""" Construct new messenger

		:param hello_message: Message header
		:param invert_hello: this flag defines whether response will have the original header \
		('hello_message' value) or it will have reversed value. For example, when this flag is set to True \
		and 'hello_message' is b'sample', then response will have b'elpmas' header.
		"""
		WBeaconMessengerBase.__init__(self)
		self.__gouverneur_message = hello_message
		self.__invert_hello = invert_hello

	def invert_hello(self):
		""" Return whether this messenger was constructed with 'invert_hello' or not.

		:return: bool
		"""
		return self.__invert_hello

	@verify_type(invert_hello=bool)
	def hello_message(self, invert_hello=False):
		""" Return message header.

		:param invert_hello: whether to return the original header (in case of False value) or reversed \
		one (in case of True value).
		:return: bytes
		"""
		if invert_hello is False:
			return self.__gouverneur_message

		hello_message = []
		for i in range(len(self.__gouverneur_message) - 1, -1, -1):
			hello_message.append(self.__gouverneur_message[i])
		return bytes(hello_message)

	@verify_type('paranoid', beacon_config=WConfig, invert_hello=bool)
	def _message(self, beacon_config, invert_hello=False):
		""" Generate request/response message.

		:param beacon_config: server or client configuration. Client configuration is used for request and \
		server configuration for response
		:param invert_hello: return message with reverse header when this argument is set to True.
		:return: bytes
		"""

		message = self.hello_message(invert_hello=invert_hello) + self._message_address_generate(beacon_config)
		return message

	@verify_type(beacon_config=WConfig)
	def _message_address_generate(self, beacon_config):
		""" Generate address for request/response message.

		:param beacon_config: server or client configuration. Client configuration is used for request and \
		server configuration for response
		:return: bytes
		"""

		address = None

		if beacon_config['wasp-general::network::beacon']['public_address'] != '':
			address = str(WIPV4SocketInfo.parse_address(
				beacon_config['wasp-general::network::beacon']['public_address']
			)).encode('ascii')

		if address is not None:
			address = WBeaconGouverneurMessenger.__message_splitter__ + address

			if beacon_config['wasp-general::network::beacon']['public_port'] != '':
				port = beacon_config.getint('wasp-general::network::beacon', 'public_port')
				address += WBeaconGouverneurMessenger.__message_splitter__ + str(port).encode('ascii')

		return address if address is not None else b''

	@verify_type(message=bytes, invert_hello=bool)
	def _message_address_parse(self, message, invert_hello=False):
		""" Read address from beacon message. If no address is specified then "nullable" WIPV4SocketInfo returns

		:param message: message to parse
		:param invert_hello: defines whether message header is the original one or reversed.
		:return: WIPV4SocketInfo
		"""
		message_header = self.hello_message(invert_hello=invert_hello)

		if message[:len(message_header)] != message_header:
			raise ValueError('Invalid message header')

		message = message[len(message_header):]
		message_parts = message.split(WBeaconGouverneurMessenger.__message_splitter__)

		address = None
		port = None

		if len(message_parts) > 3:
			raise ValueError('Invalid message. Too many separators')
		elif len(message_parts) == 3:
			address = WIPV4SocketInfo.parse_address(message_parts[1].decode('ascii'))
			port = WIPPort(int(message_parts[2]))
		elif len(message_parts) == 2 and len(message_parts[1]) > 0:
			address = WIPV4SocketInfo.parse_address(message_parts[1].decode('ascii'))

		return WIPV4SocketInfo(address, port)

	@verify_type('paranoid', beacon_config=WConfig)
	def request(self, beacon_config):
		""" :meth:`.WBeaconMessengerBase.request` method implementation.

		see :class:`.WBeaconGouverneurMessenger`
		"""
		return self._message(beacon_config)

	@verify_type('paranoid', beacon_config=WConfig, request=bytes, client_address=WIPV4SocketInfo)
	def has_response(self, beacon_config, request, client_address):
		""" :meth:`.WBeaconMessengerBase.has_response` method implementation. This method compares request
		header with internal one.
		"""
		try:
			self._message_address_parse(request, invert_hello=self.__invert_hello)
			return True
		except ValueError:
			pass
		return False

	@verify_type('paranoid', beacon_config=WConfig, request=bytes, client_address=WIPV4SocketInfo)
	def response(self, beacon_config, request, client_address):
		""" :meth:`.WBeaconMessengerBase.request` method implementation.

		see :class:`.WBeaconGouverneurMessenger`
		"""
		return self._message(beacon_config, invert_hello=self.__invert_hello)

	@verify_type('paranoid', beacon_config=WConfig, request=bytes)
	@verify_type(client_address=WIPV4SocketInfo)
	def response_address(self, beacon_config, request, client_address):
		""" :meth:`.WBeaconMessengerBase.request` method implementation.

		see :class:`.WBeaconGouverneurMessenger`
		"""
		si = self._message_address_parse(request, invert_hello=self.__invert_hello)
		address = si.address()
		port = si.port()
		return WIPV4SocketInfo(
			address if address is not None else client_address.address(),
			port if port is not None else client_address.port()
		)

	@verify_type('paranoid', beacon_config=WConfig, response=bytes, server_address=WIPV4SocketInfo)
	def valid_response(self, beacon_config, response, server_address):
		""" :meth:`.WBeaconMessengerBase.valid_response` method implementation. Response when it has correct
		header. Response header must be reversed if this messenger was constructed with 'invert_hello' flag.
		"""
		try:
			self._message_address_parse(response, invert_hello=self.__invert_hello)
			return True
		except ValueError:
			pass
		return False


class WHostgroupBeaconMessenger(WBeaconGouverneurMessenger):
	""" This messenger is based on :class:`.WBeaconGouverneurMessenger` class. This messenger extends
	:class:`.WBeaconGouverneurMessenger` functionality by working with host group names. Also, this class doubles
	maximum message size defined in :class:`.WBeaconMessengerBase`. In cases where no host group name are
	specified this class works as its basic class :class:`.WBeaconGouverneurMessenger`.

	Messages format is updated from this:

	'[Message header]<:[Address<:TCP/UDP port>]>'

	to this:

	'[Message header]<:[Address<:TCP/UDP port>]><#<[Hostgroup name]>,<[Hostgroup name]...>'>

	'Message header', 'Address' and 'TCP/UDP port' work the same way as they specified in
	:class:`.WBeaconGouverneurMessenger` class. At the end of the original message new optional separator is
	appended. This separator is defined at :attr:`.WHostgroupBeaconMessenger.__message_groups_splitter__`.
	After this separator host group names can be defined. Host group names can contain latin letters and numbers
	only. Host group names are separated by :attr:`.WHostgroupBeaconMessenger.__group_splitter__`

	If this messenger is constructed with at least one host group name, then it won'not response to requests,
	that do not have at least one host group name, that this messenger was constructed with.
	"""

	message_maxsize = 1024
	""" Doubled message size for list of names
	"""
	__message_groups_splitter__ = b'#'
	""" Bytes that separate original message from extended one
	"""
	__group_splitter__ = b','
	""" Bytes that separate different names
	"""

	re_hostgroup_name = re.compile('^[a-zA-Z0-9]+$')
	""" Regular expression for host group name validation
	"""

	@verify_type('paranoid', hello_message=bytes, invert_hello=bool)
	@verify_value('paranoid', hello_message=lambda x: len(x.decode('ascii')) >= 0)
	@verify_value('paranoid', hello_message=lambda x: WHostgroupBeaconMessenger.__message_groups_splitter__ not in x)
	@verify_type(hostgroup_names=str)
	@verify_value(hostgroup_names=lambda x: WHostgroupBeaconMessenger.re_hostgroup_name.match(x) is not None)
	def __init__(self, hello_message, *hostgroup_names, invert_hello=False):
		""" Create new messenger

		:param hello_message: same as hello_message in :meth:`.WBeaconGouverneurMessenger.__init__`
		:param hostgroup_names: list of host group names
		"""
		WBeaconGouverneurMessenger.__init__(self, hello_message, invert_hello=invert_hello)

		self.__hostgroups = []
		self.__hostgroups.extend([x.encode() for x in hostgroup_names])

	def hostgroups(self):
		""" Return list of host group names

		:return: list of str
		"""
		return [x.decode() for x in self.__hostgroups]

	@verify_type('paranoid', beacon_config=WConfig, invert_hello=bool)
	def _message(self, beacon_config, invert_hello=False):
		""" Overridden :meth:`.WBeaconGouverneurMessenger._message` method. Appends encoded host group names
		to requests and responses.

		:param beacon_config: beacon configuration
		:return: bytes
		"""
		m = WBeaconGouverneurMessenger._message(self, beacon_config, invert_hello=invert_hello)
		hostgroups = self._message_hostgroup_generate()
		if len(hostgroups) > 0:
			m += (WHostgroupBeaconMessenger.__message_groups_splitter__ + hostgroups)
		return m

	def _message_hostgroup_generate(self):
		""" Encode messenger host group names
		:return: bytes
		"""
		return b','.join(self.__hostgroups)

	@verify_type(message=bytes)
	def _message_hostgroup_parse(self, message):
		""" Parse given message and return list of group names and socket information. Socket information
		is parsed in :meth:`.WBeaconGouverneurMessenger._message_address_parse` method

		:param message: bytes
		:return: tuple of list of group names and WIPV4SocketInfo
		"""
		splitter_count = message.count(WHostgroupBeaconMessenger.__message_groups_splitter__)
		if splitter_count == 0:
			return [], WBeaconGouverneurMessenger._message_address_parse(self, message)
		elif splitter_count == 1:
			splitter_pos = message.find(WHostgroupBeaconMessenger.__message_groups_splitter__)
			groups = []
			group_splitter = WHostgroupBeaconMessenger.__group_splitter__
			for group_name in message[(splitter_pos + 1):].split(group_splitter):
				groups.append(group_name.strip())
			address = WBeaconGouverneurMessenger._message_address_parse(self, message[:splitter_pos])
			return groups, address
		else:
			raise ValueError('Invalid message. Too many separators')

	@verify_type('paranoid', beacon_config=WConfig, request=bytes, client_address=WIPV4SocketInfo)
	def has_response(self, beacon_config, request, client_address):
		""" :meth:`.WBeaconMessengerBase.has_response` method implementation. This method compares request
		headers as :meth:`.WBeaconGouverneurMessenger.has_response` do and compares specified group names
		with internal names.
		"""
		try:
			groups, address = self._message_hostgroup_parse(request)

			if len(self.__hostgroups) == 0 or len(groups) == 0:
				return True

			for group_name in groups:
				if group_name in self.__hostgroups:
					return True
			return False
		except ValueError:
			pass
		return False

	@verify_type('paranoid', beacon_config=WConfig, request=bytes)
	@verify_type(client_address=WIPV4SocketInfo)
	def response_address(self, beacon_config, request, client_address):
		""" :meth:`.WBeaconMessengerBase.response_address` method implementation. It just removes host group names
		part and return :meth:`.WBeaconMessengerBase.response_address` result
		"""
		si = self._message_hostgroup_parse(request)[1]
		address = si.address()
		port = si.port()
		return WIPV4SocketInfo(
			address if address is not None else client_address.address(),
			port if port is not None else client_address.port()
		)
