# -*- coding: utf-8 -*-
# wasp_general/network/web/proto.py
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

from abc import ABCMeta, abstractmethod, abstractclassmethod
import urllib.parse
import re

from wasp_general.verify import verify_type, verify_value, verify_subclass
from wasp_general.network.web.re_statements import http_get_vars_selection, http_post_vars_selection


class WWebResponseProto(metaclass=ABCMeta):
	""" Class represent server response for client HTTP-request
	"""

	def status(self):
		""" Return response status code. Is required for 1.0 protocol and beyond. It must be avoid
		in HTTP/0.9

		:return: None or int
		"""
		pass

	def headers(self):
		""" Return headers to set in response.

		:return: None if no headers is needed to be written or WHTTPHeaders
		"""
		pass

	def response_data(self):
		""" Return response payload

		:return: None if not required or bytes
		"""
		pass

	def __pushed_responses__(self):
		""" Return related HTTP-responses, that can be pushed to client. Available on HTTP/2 only

		:return: None if not required or tuple of WWebResponseProto
		"""
		return tuple()


class WWebRequestProto(metaclass=ABCMeta):
	""" Class represent client HTTP-request
	"""

	get_vars_re = re.compile(http_get_vars_selection)
	"""
	Regular expression that is used for GET-vars parsing
	"""

	post_vars_re = re.compile(http_post_vars_selection)
	"""
	Regular expression that is used for POST-vars parsing
	"""

	@abstractmethod
	def session(self):
		""" Return current session with which request is created

		:return: WWebSessionProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def method(self):
		""" Return request method (like POST/GET/...)

		:return: str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def path(self):
		""" Return request path (like /foo/bar/index.html)

		:return: str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def headers(self):
		""" Return request headers

		:return: None or WHTTPHeaders
		"""
		raise NotImplementedError('This method is abstract')

	def request_data(self):
		""" Return request payload

		:return: None or bytes
		"""
		pass

	def virtual_host(self):
		""" Return request virtual host ("Host" header value)

		:return: None or str
		"""
		if self.headers() is not None:
			host_value = self.headers()['Host']
			return host_value[0].lower() if host_value is not None else None

	def content_type(self):
		""" Return request content_type ("Content-Type" header value)

		:return: None or str
		"""
		if self.headers() is not None:
			return self.headers().content_type()

	def get_vars(self):
		""" Parse request path and return GET-vars

		:return: None or dictionary of names and tuples of values
		"""
		if self.method() != 'GET':
			raise RuntimeError('Unable to return get vars for non-get method')
		re_search = WWebRequestProto.get_vars_re.search(self.path())
		if re_search is not None:
			return urllib.parse.parse_qs(re_search.group(1), keep_blank_values=1)

	def post_vars(self):
		""" Parse request payload and return POST-vars

		:return: None or dictionary of names and tuples of values
		"""
		if self.method() != 'POST':
			raise RuntimeError('Unable to return post vars for non-get method')

		content_type = self.content_type()
		if content_type is None or content_type.lower() != 'application/x-www-form-urlencoded':
			raise RuntimeError('Unable to return post vars with invalid content-type request')

		request_data = self.request_data()
		request_data = request_data.decode() if request_data is not None else ''
		re_search = WWebRequestProto.post_vars_re.search(request_data)
		if re_search is not None:
			return urllib.parse.parse_qs(re_search.group(1), keep_blank_values=1)


class WWebSessionProto(metaclass=ABCMeta):
	""" Represent client session. For HTTP/0.9-1.0 every request creates new session. For HTTP/1.1 request
	can be joined in a single session if "Connection" header is used. For HTTP/2 protocol there can be single
	session for every client
	"""

	@abstractmethod
	def client_address(self):
		""" Return client IP-address and port

		:return: WIPV4SocketInfo
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def server_address(self):
		""" Return server IP-address and port to which client is connected

		:return: WIPV4SocketInfo
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def protocol_version(self):
		""" Return currently used protocol version

		:return: str (one of "0.9"/"1.0"/"1.1"/"2")
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def protocol(self):
		""" Return currently used protocol

		:return: str (one of "http"/"https")
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def read_request(self):
		""" Read next request from session

		:return: WWebRequestProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(request=WWebRequestProto, reponse=WWebResponseProto)
	def write_response(self, request, response):
		""" Write response to client

		:param request: original client request
		:param response: response to write
		:return:
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def session_close(self):
		""" Close session

		:return: None
		"""
		raise NotImplementedError('This method is abstract')


class WWebPresenter(metaclass=ABCMeta):
	""" Class represent worker that generates response over specified request.
	WWebTargetRouteProto defines what exactly method will be called and with what arguments.

	see :class:`.WWebTargetRouteProto`
	see :class:`.WWebRouteMapProto`
	"""

	@verify_type(request=WWebRequestProto)
	def __init__(self, request):
		""" Construct new worker

		:param request: client request
		"""
		self.__request = request

	@abstractclassmethod
	def __presenter_name__(cls):
		"""

		:return: str or None (in most cases - str)
		"""
		raise NotImplementedError('This method is abstract')

	def __request__(self):
		""" Return client request

		:return: WWebRequestProto
		"""
		return self.__request


class WWebErrorPresenter(WWebPresenter, metaclass=ABCMeta):
	""" Presenter which is used for displaying standard HTTP-errors and internal exceptions
	"""

	@abstractmethod
	@verify_type(code=int)
	@verify_value(code=lambda x: x > 0)
	def error_code(self, code):
		""" Return response for the given HTTP-code

		:param code: HTTP-code of error
		:return: WWebResponseProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(exception=Exception)
	def exception_error(self, exception):
		""" Return response for the given exception

		:param exception: raised exception to process and or display
		:return: WWebResponseProto
		"""
		raise NotImplementedError('This method is abstract')


class WWebTargetRouteProto(metaclass=ABCMeta):
	""" Represent single route that matches client request
	"""

	@abstractmethod
	def presenter_name(self):
		""" Return presenter name to be used

		:return: WWebPresenter
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def presenter_action(self):
		""" Return method name to be called

		:return: str
		"""
		raise NotImplementedError('This method is abstract')

	def presenter_args(self):
		""" Return arguments to be used with presenter method

		:return: dict, where keys - are argument names and values - argument values (any type)
		"""
		return dict()


class WWebPresenterCollectionProto(metaclass=ABCMeta):
	""" Represent collection of presenters

	see :class:`.WWebPresenter`
	"""

	@abstractmethod
	@verify_type(presenter_name=str)
	@verify_value(presenter_name=lambda x: len(x) > 0)
	def presenter(self, presenter_name):
		""" Return presenter by its name

		:param presenter_name: name of presenter class
		:return: type (WWebPresenter sublcass) or None (if there is no such presenter)
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(presenter_name=str)
	@verify_value(presenter_name=lambda x: len(x) > 0)
	def has(self, presenter_name):
		""" Return if there is a presenter with the given name

		:param presenter_name: name of presenter
		:return: bool
		"""
		raise NotImplementedError('This method is abstract')


class WWebPresenterFactoryProto(metaclass=ABCMeta):
	""" This class is used for presenter object instantiation. Different presenter classes may have different
	constructor and so may require different arguments, so this class implementation will be possible to
	instantiate limited presenter classes. Because of that, this class is tightly connected with specific
	WWebServiceProto implementation, which uses this class for creating presenter
	"""

	@abstractmethod
	@verify_subclass(presenter_class=WWebPresenter)
	def instantiable(self, presenter_class):
		""" Check if this factory can produce the specified presenter

		:param presenter_class: target presenter class
		:return: bool
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(presenter_name=str)
	@verify_subclass(presenter_class=WWebPresenter)
	def instantiate(self, presenter_class, *args, **kwargs):
		""" Create new presenter object. Different implementation may have different required arguments

		:param presenter_class: presenter class to instantiate
		:param args: instantiation arguments (may vary)
		:param kwargs: instantiation arguments (may vary)
		:return: WWebPresenter
		"""
		raise NotImplementedError('This method is abstract')


class WWebServiceProto(metaclass=ABCMeta):
	""" Represent service that unites wasp-general web-functionality
	"""

	@abstractmethod
	def route_map(self):
		""" Return service route map

		:return: WWebRouteMapProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def presenter_collection(self):
		""" Return service presenter collection

		:return: WWebPresenterCollection
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def presenter_factory(self):
		""" Return current presenter factory

		:return: WWebPresenterFactoryProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(request=WWebRequestProto, target_route=WWebTargetRouteProto)
	def execute(self, request, target_route):
		""" Execute given target route and return response

		:param request: client request
		:param target_route: route to execute
		:return: WWebResponseProto
		"""
		raise NotImplementedError('This method is abstract')


class WWebRouteMapProto(metaclass=ABCMeta):
	""" Represent collection of routes
	"""

	@abstractmethod
	@verify_type(request=WWebRequestProto, service=WWebServiceProto)
	def route(self, request, service):
		""" Return the first route that matches client request

		:param request: client request
		:param service: source service
		:return: None if no route is found, WWebTargetRouteProto otherwise
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def error_presenter(self):
		""" Return presenter that is used for error handling

		:return: WWebErrorPresenter
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(target_route=WWebTargetRouteProto)
	def target_route_valid(self, target_route):
		""" Check target route for execution. This method is used for omitting special methods (actions)
		from being executed

		:param target_route: route to check
		:return: bool
		"""
		return target_route.presenter_action()[0] != '_'
