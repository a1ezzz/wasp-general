# -*- coding: utf-8 -*-
# wasp_general/network/web/session.py
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

# TODO: make code more useful
# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_subclass, verify_type
from wasp_general.network.primitives import WIPV4SocketInfo

from wasp_general.network.web.proto import WWebSessionProto, WWebResponseProto
from wasp_general.network.web.request import WWebRequest


class WWebSessionAdapter(WWebSessionProto):

	def client_address(self):
		return WIPV4SocketInfo(*self.accepted_socket().getpeername())

	def server_address(self):
		return WIPV4SocketInfo(*self.accepted_socket().getsockname())

	@abstractmethod
	def accepted_socket(self):
		raise NotImplementedError('This method is abstract')


class WWebSessionBase(WWebSessionAdapter, metaclass=ABCMeta):
	""" Basic :class:`.WWebSessionProto` implementation. This class clarifies prototype and appends several methods
	"""
	#TODO: Continue development!

	@verify_subclass(request_cls=WWebRequest)
	def __init__(self, request_cls=WWebRequest):
		""" Construct class

		:param request_cls: request class to use
		"""
		self.__request_cls = request_cls

	@verify_type(request_line=str)
	def read_request_line(self, request_line):
		""" Read HTTP-request line

		:param request_line: line to parse
			for HTTP/0.9 is GET <Request-URI>
			for HTTP/1.0 and 1.1 is <METHOD> <Request-URI> HTTP/<HTTP-Version>, where HTTP-Version is 1.0
			or 1.1.
			for HTTP/2: binary headers are used
		"""

		request = self.__request_cls.parse_request_line(self, request_line)

		protocol_version = self.protocol_version()
		if protocol_version == '0.9':
			if request.method() != 'GET':
				raise Exception('HTTP/0.9 standard violation')
		elif protocol_version == '1.0' or protocol_version == '1.1':
			pass
		elif protocol_version == '2':
			pass
		else:
			raise RuntimeError('Unsupported HTTP-protocol')
