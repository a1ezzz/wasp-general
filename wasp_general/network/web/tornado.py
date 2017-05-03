# -*- coding: utf-8 -*-
# wasp_general/network/web/tornado.py
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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import weakref
from tornado.web import RequestHandler

from wasp_general.network.web.proto import WWebResponseProto
from wasp_general.verify import verify_type
from wasp_general.network.web.headers import WHTTPHeaders
from wasp_general.network.web.session import WWebSessionAdapter
from wasp_general.network.web.request import WWebRequest
from wasp_general.network.web.cookies import WHTTPCookieJar


class WTornadoRequestHandler(RequestHandler):
	"""
	According to http://www.tornadoweb.org/en/stable/web.html, requesthandlers are not thread safe

	"""

	def __init__(self, wasp_web_service, application, request, **kwargs):
		RequestHandler.__init__(self, application, request, **kwargs)
		self.__sessions = {}
		self.__wasp_web_service = wasp_web_service

	def compute_etag(self):
		pass

	def __handle_request(self):

		fileno = self.request.connection.stream.socket.fileno()

		def close_session():
			if fileno in self.__sessions.keys():
				del self.__sessions[fileno]
			else:
				pass
				# very strange

		if fileno in self.__sessions.keys():
			session = self.__sessions[fileno]
		else:
			session = WTornadoSessionAdapter(self, close_session)
			self.__sessions[fileno] = session

		self.__wasp_web_service.process_request(session)

	def get(self, *args, **kwargs):
		self.__handle_request()

	def head(self, *args, **kwargs):
		self.__handle_request()

	def post(self, *args, **kwargs):
		self.__handle_request()

	def delete(self, *args, **kwargs):
		self.__handle_request()

	def patch(self, *args, **kwargs):
		self.__handle_request()

	def put(self, *args, **kwargs):
		self.__handle_request()

	def options(self, *args, **kwargs):
		self.__handle_request()

	@classmethod
	def __handler__(self, wasp_web_service):
		class Hanlder(WTornadoRequestHandler):
			def __init__(self, application, request, **kwargs):
				WTornadoRequestHandler.__init__(self, wasp_web_service, application, request, **kwargs)
		return Hanlder


class WTornadoSessionAdapter(WWebSessionAdapter):

	def __init__(self, request_handler, cleanup_handler):

		def weakref_handler(socket_ref):
			self.session_close()

		self.__request_handler = request_handler
		self.__socket_ref = weakref.ref(request_handler.request.connection.stream.socket, weakref_handler)
		self.__protocol_version = request_handler.request.version[len('HTTP/'):]
		self.__protocol = request_handler.request.protocol
		self.__cleanup_handler = cleanup_handler

	def accepted_socket(self):
		return self.__socket_ref()

	def protocol_version(self):
		return self.__protocol_version

	def protocol(self):
		return self.__protocol

	def read_request(self):
		handler_headers = self.__request_handler.request.headers
		headers = WHTTPHeaders()
		for header_name in handler_headers.keys():
			headers.add_headers(header_name, *handler_headers.get_list(header_name))

		for cookie in WHTTPCookieJar.import_simple_cookie(self.__request_handler.cookies):
			headers.set_cookie_jar().add_cookie(cookie)

		request = WWebRequest(
			self, self.__request_handler.request.method, self.__request_handler.request.path,
			headers=headers.ro()
		)
		#! todo: fix
		#request.set_request_body()
		return request

	@verify_type(request=WWebRequest, reponse=WWebResponseProto, pushed_responses=WWebResponseProto)
	def write_response(self, request, response, *pushed_responses):
		status = response.status()
		headers = response.headers()
		response_data = response.response_data()

		if status is not None:
			self.__request_handler.set_status(status)

		if headers is not None:
			headers = headers.switch_name_style(self.protocol_version())
			for header_name in headers.headers():
				for header_value in headers[header_name]:
					self.__request_handler.add_header(header_name, header_value)

			content_type = headers.content_type()
			if content_type is not None:
				self.__request_handler.set_header(headers.normalize_name('Content-Type'), content_type)
			elif response_data is not None:
				self.__request_handler.set_header(
					headers.normalize_name('Content-Type'), 'application/octet-stream'
				)

			for cookie in headers.set_cookie_jar():
				self.__request_handler.set_cookie(
					cookie.name(), cookie.value(), **cookie.attrs_as_dict()
				)

		if response_data is not None:
			self.__request_handler.write(response_data)

	def session_close(self):
		self.__cleanup_handler()
