# -*- coding: utf-8 -*-
# wasp_general/network/web.py
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

from wasp_general.network.web.proto import WWebSessionProto, WWebRequestProto
from wasp_general.network.web.headers import WHTTPHeaders
from wasp_general.network.web.re_statements import http_method_name, http_path, http_version


class WWebRequest(WWebRequestProto):
	""" :class:`.WWebRequestProto` implementation. Class represent HTTP-request descriptor.
	Call :meth:`.WWebRequest.ro` method to create unchangeable copy
	"""

	request_line_re = re.compile(
		'^(' + http_method_name + ') +(' + http_path + ')( +HTTP/(' + http_version + '))?$'
	)
	"""
	Check for HTTP request line. See RFC 2616, Section 5.1


	"""

	@verify_type(session=WWebSessionProto, method=str, path=str, headers=(WHTTPHeaders, None))
	@verify_type(request_data=(bytes, None))
	@verify_value(method=lambda x: len(x) > 0)
	@verify_value(path=lambda x: len(x) > 0)
	def __init__(self, session, method, path, headers=None, request_data=None):
		"""
		Create new request descriptor

		:param session: request origin
		:param method: called HTTP-method
		:param path: called HTTP-path
		"""
		WWebRequestProto.__init__(self)
		self.__session = session
		self.__method = method.upper()
		self.__path = path
		self.__headers = headers
		self.__request_data = request_data
		self.__ro_flag = False

	def session(self):
		""" Return origin session

		:return: WWebSessionProto
		"""
		return self.__session

	def method(self):
		""" Return requested method

		:return: str
		"""
		return self.__method

	def path(self):
		""" Return requested path

		:return: str
		"""
		return self.__path

	def headers(self):
		""" Return request headers

		:return: WHTTPHeaders
		"""
		return self.__headers

	@verify_type(headers=WHTTPHeaders)
	def set_headers(self, headers):
		""" Set headers for request

		:param headers: headers to set
		:return: None
		"""
		if self.__ro_flag:
			raise RuntimeError('Read-only object changing attempt')
		self.__headers = headers

	def request_data(self):
		""" Return request data

		:return: bytes
		"""
		return self.__request_data

	@verify_type(request_data=bytes)
	def set_request_data(self, request_data):
		""" Set payload data for request

		:param request_data: data to set
		:return: None
		"""
		if self.__ro_flag:
			raise RuntimeError('Read-only object changing attempt')
		self.__request_data = request_data

	@classmethod
	@verify_type('paranoid', session=WWebSessionProto)
	@verify_type(request_line=str)
	def parse_request_line(cls, session, request_line):
		""" Parse given request line like 'GET /foo' or 'POST /zzz HTTP/1.0'

		:param session: origin session
		:param request_line: line to parse
		:return: WWebRequest
		"""
		r = cls.request_line_re.search(request_line)
		if r is not None:
			method, path, protocol_sentence, protocol_version = r.groups()
			return WWebRequest(session, method, path)
		raise ValueError('Invalid request line')

	@verify_type('paranoid', http_code=str)
	def parse_headers(self, http_code):
		""" Parse http-code (like 'Header-X: foo\r\nHeader-Y: bar\r\n') and retrieve (save) HTTP-headers

		:param http_code: code to parse
		:return: None
		"""
		if self.__ro_flag:
			raise RuntimeError('Read-only object changing attempt')
		self.__headers = WHTTPHeaders.import_headers(http_code)

	def ro(self):
		""" Create read-only copy

		:return: WWebRequest
		"""
		request = WWebRequest(
			self.session(), self.method(), self.path(),
			headers=self.headers().ro(), request_data=self.request_data()
		)
		request.__ro_flag = True
		return request
