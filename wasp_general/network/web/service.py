# -*- coding: utf-8 -*-
# wasp_general/network/web/service.py
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
from inspect import getfullargspec, ismethod
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_subclass, verify_value
from wasp_general.network.web.proto import WWebTargetRouteProto, WWebRouteMapProto, WWebRequestProto, WWebServiceProto
from wasp_general.network.web.proto import WWebPresenter, WWebErrorPresenter, WWebSessionProto
from wasp_general.network.web.proto import WWebPresenterCollectionProto, WWebPresenterFactoryProto
from wasp_general.network.web.re_statements import wasp_route_arg_name_selection, wasp_route_arg_value_selection
from wasp_general.network.web.re_statements import wasp_route_custom_arg_selection, wasp_route_import_pattern
from wasp_general.network.web.re_statements import wasp_route_arg_name
from wasp_general.network.web.response import WWebResponse
from wasp_general.network.web.headers import WHTTPHeaders
from wasp_general.network.web.debug import WWebDebugInfo


class WSimpleErrorPresenter(WWebErrorPresenter):
	""" Simple :class:`.WWebErrorPresenter` implementation
	"""

	@verify_type('paranoid', request=WWebRequestProto)
	def __init__(self, request):
		""" Create new error presenter

		:param request: origin request
		"""
		WWebErrorPresenter.__init__(self, request)
		self.__messages = {
			404: 'Page not found'
		}

	@verify_type(code=int)
	@verify_value(code=lambda x: x > 0)
	def __message__(self, code):
		if code in self.__messages.keys():
			return self.__messages[code]
		return 'Internal error: %i' % code

	@verify_type('paranoid', code=int)
	@verify_value('paranoid', code=lambda x: x > 0)
	def error_code(self, code):
		""" :meth:`.WWebErrorPresenter.error_code` method implementation
		"""
		return WWebResponse(
			status=code,
			headers=WHTTPHeaders(**{'Content-Type': 'text/plain; charset=utf-8'}),
			response_data=self.__message__(code).encode()
		)

	@verify_type(exception=Exception)
	def exception_error(self, exception):
		""" :meth:`.WWebErrorPresenter.exception_error` method implementation
		"""
		return self.error_code(500)

	@classmethod
	def __presenter_name__(cls):
		""" :meth:`.WWebPresenter.__presenter_name__` method implementation
		"""
		return 'simple-error-presenter'


class WWebRoute:
	""" Class is used for single route description. It helps to match single request to corresponding presenter
	(:class:`.WWebPresenter`). Every route is described by a single pattern (that later compiles to regular
	expression). Pattern may define different route arguments. There is a way to define default arguments with
	default values, this is done by passing arguments in object constructor. Every route argument
	(except special arguments) will be provided to the related presenter action via :class:`.WWebTargetRoute` class.

	Every special argument can be defined in a object constructor, but there is a single special argument
	('action') that can be defined in pattern also. Special arguments usage:
	- 'action': redefines presenter action. Default value is 'index'
	- 'virtual_hosts': is used for request matching. If defined, there must be 'Host' header
	in client request, which equals hostname saved in 'virtual_hosts'. Hostnames are case-insensitive. Default value
	is None which is matched to any hostname
	- 'protocols': defines protocol for client request matching. Suitable protocols are 'http' or 'https'. Default
	value contains both protocols.
	- 'ports': list/tuple/set of ports client is connected to. Default value is None, which is matched to any port
	- 'methods': available client methods like GET, POST, HEAD. Method name is case-sensitive. Default value allow
	to use GET and POST methods
	"""

	class ArgSearch(metaclass=ABCMeta):
		""" Class for internal usage only. It is used for route argument searching from the given pattern and
		later pattern preparation
		"""

		@abstractmethod
		def args(self):
			""" Return arguments, that were found inside the given pattern. Each argument is a tuple of
			argument name and argument position index inside the origin pattern.

			:return: tuple of (str, int)
			"""
			raise NotImplementedError('This method is abstract')

		@abstractmethod
		def reduce_pattern(self):
			""" Return functor that accept single parameter, which is a pattern to prepare. Pattern
			preparation is a process which replace argument specification with regular expression substring,
			regular expression that is used for determine argument value.

			:return: function or lambda
			"""
			raise NotImplementedError('This method is abstract')

	class BasicArgSearch(ArgSearch):
		""" This is a simple route argument search, that is looking for simple pattern "{<argument_name>}".
		In the prepared patter this argument specification will be replaced with "(\w+)" statement
		"""

		arg_re = re.compile(wasp_route_arg_name_selection)
		""" Argument name pattern
		"""

		@verify_type(pattern=str)
		@verify_value(pattern=lambda x: len(x) > 0)
		def __init__(self, pattern):
			""" Construct new search

			:param pattern: pattern with argument specification
			"""
			self.__pattern = pattern
			self.__replace_with = wasp_route_arg_value_selection

		def args(self):
			""" :meth:`.WWebRoute.ArgSearch.args` implementation
			"""
			result = []
			for arg in WWebRoute.BasicArgSearch.arg_re.findall(self.__pattern):
				result.append((arg, self.__pattern.find('{%s}' % arg)))
			return tuple(result)

		def reduce_pattern(self):
			""" :meth:`.WWebRoute.ArgSearch.reduce_pattern` implementation
			"""
			return lambda x: WWebRoute.BasicArgSearch.arg_re.sub(self.__replace_with, x)

	class CustomArgSearch(ArgSearch):
		""" This is more complex argument search than :class:`.WWebRoute.BasicArgSearch`. This class provides
		an ability to control target argument regular expression. Instead of using simple regexp like
		:class:`.WWebRoute.BasicArgSearch` does (:class:`.WWebRoute.BasicArgSearch` uses '(\w+)'), this class
		will search for a special statements that describe and argument name and corresponding regexp.
		Statements obey the following format "{<argument_name>:"<regular_expression>"}".
		"""

		custom_arg_re = re.compile(wasp_route_custom_arg_selection)
		""" Argument name pattern
		"""

		@verify_type(arg_name=str, arg_pos=int, arg_spec=str, arg_custom_re_text=str)
		@verify_value(arg_name=lambda x: len(x) > 0, arg_pos=lambda x: x >= 0)
		@verify_value(arg_spec=lambda x: len(x) > 0, arg_custom_re_text=lambda x: len(x) > 0)
		def __init__(self, arg_name, arg_pos, arg_spec, arg_custom_re_text):
			""" Construct new search. Actually this is a result of search. all the magic happens in
			:meth:`.WWebRoute.CustomArgSearch.custom` method

			:param arg_name: found argument name
			:param arg_pos: found argument position
			:param arg_spec: found argument specification (whole sentence)
			:param arg_custom_re_text: found regular expression
			"""
			self.__arg_name = arg_name
			self.__arg_pos = arg_pos
			self.__arg_spec = arg_spec
			self.__arg_re = arg_custom_re_text

		def args(self):
			""" :meth:`.WWebRoute.ArgSearch.args` implementation
			"""
			return (self.__arg_name, self.__arg_pos),

		def reduce_pattern(self):
			""" :meth:`.WWebRoute.ArgSearch.reduce_pattern` implementation
			"""
			return lambda x: x.replace(self.__arg_spec, self.__arg_re)

		@classmethod
		@verify_type(pattern=str)
		@verify_value(pattern=lambda x: len(x) > 0)
		def custom(cls, pattern):
			""" Parse the given pattern for arguments and iterate over results
			(:class:`.WWebRoute.CustomArgSearch` is yielded)

			:param pattern: pattern for search
			:return: None
			"""
			reduced_pattern = pattern
			for arg in WWebRoute.CustomArgSearch.custom_arg_re.findall(pattern):
				arg_search = WWebRoute.CustomArgSearch(arg[1], pattern.find(arg[0]), arg[0], arg[2])
				reduced_pattern = arg_search.reduce_pattern()(reduced_pattern)
				yield arg_search

	multiple_slashes_re = re.compile("//+")
	""" Regexp for removing extra slashes
	"""

	pattern_parentheses_removing_re = re.compile('(\([^()]*\([^()]*\)[^()]*\))')
	""" Regexp for removing internal parentheses
	"""

	pattern_parentheses_removing_nested_re = re.compile('(\([^()]*\([^()]*\)[^()]*\([^()]*\)[^()]*\))')
	""" Regexp for removing internal nested parentheses
	"""

	pattern_recombination_re = re.compile('(\([^()]*\))')
	""" Regexp for source argument compilation
	"""

	@verify_type(pattern=str, presenter=str, action=(str, None), virtual_hosts=(list, tuple, set, None))
	@verify_type(protocols=(list, tuple, set, None), ports=(list, tuple, set, None))
	@verify_type(methods=(list, tuple, set, None))
	def __init__(self, pattern, presenter, **kwargs):
		""" Create new route

		:param pattern: route declarative pattern, that may contain arguments definition
		:param presenter: target presenter name
		:param kwargs: route arguments (default and special arguments)
		"""

		self.original_pattern = pattern
		## Source pattern. It doesn't change during lifetime, the only usage is debug

		self.route_args = []
		## Route arguments encoded in url

		self.presenter = presenter
		## Presenter to use

		self.presenter_args = {}
		## Default arguments for the given action

		self.action = "index"
		## Action to run (default "index")

		self.virtual_hosts = None
		## List of hosts in URI (None - any host)

		self.ports = None
		## List of ports in URI (None - any port)

		self.protocols = ("http", "https")
		## List of protocols (default "http" and "https")

		self.methods = ("GET", "POST")
		## List of HTTP method (default "GET" and "POST")

		arg_search = WWebRoute.BasicArgSearch(self.normalize_uri(pattern))
		route_args = list(arg_search.args())
		reduce_fn = [arg_search.reduce_pattern()]
		# process simple arguments like {action} or {index}

		for arg_search in WWebRoute.CustomArgSearch.custom(pattern):
			route_args.extend(arg_search.args())
			reduce_fn.append(arg_search.reduce_pattern())
		# process customized arguments like {param1: "(\d+)"}

		route_args.sort(key=lambda x: x[1])
		self.route_args = [x[0] for x in route_args]
		# reorder route args

		pattern = self.normalize_uri(pattern)
		for fn in reduce_fn:
			pattern = fn(pattern)
		self.pattern = "^" + pattern + "$"
		self.re_pattern = re.compile(self.pattern)
		# pattern compilation

		for key in kwargs.keys():

			if key == "action":
				self.action = kwargs["action"]
				continue

			if key == "virtual_hosts":
				self.virtual_hosts = tuple([x.lower() for x in kwargs["virtual_hosts"]])
				continue

			if key == "protocols":
				self.protocols = tuple(kwargs["protocols"])
				continue

			if key == "ports":
				self.ports = tuple(kwargs["ports"])
				continue

			if key == "methods":
				self.methods = tuple(kwargs["methods"])
				continue

			self.presenter_args[key] = kwargs[key]
		# extra presenter args

	@classmethod
	@verify_type(uri=str)
	def normalize_uri(cls, uri):
		""" Normalize the given URI (removes extra slashes)

		:param uri: uri to normalize
		:return: str
		"""
		uri = WWebRoute.multiple_slashes_re.sub("/", uri)

		# remove last slash
		if len(uri) > 1:
			if uri[-1] == '/':
				uri = uri[:-1]

		return uri

	@verify_type(request=WWebRequestProto, service=WWebServiceProto)
	def match(self, request, service):
		""" Check this route for matching the given request. If this route is matched, then target route is
		returned.

		:param request: request to match
		:param service: source service
		:return: WWebTargetRoute or None
		"""
		uri = self.normalize_uri(request.path())

		if request.session().protocol() not in self.protocols:
			return

		if request.method() not in self.methods:
			return

		if self.virtual_hosts and request.virtual_host() not in self.virtual_hosts:
			return

		if self.ports and int(request.session().server_address().port()) not in self.ports:
			return

		match_obj = self.re_pattern.match(uri)

		if not match_obj:
			return

		presenter_action = self.action
		presenter_args = self.presenter_args.copy()

		for i in range(len(self.route_args)):
			if self.route_args[i] == 'action':
				presenter_action = match_obj.group(i + 1)
			else:
				presenter_args[self.route_args[i]] = match_obj.group(i + 1)

		return WWebTargetRoute(self.presenter, presenter_action, self, service.route_map(), **presenter_args)

	def url_for(self, **kwargs):
		""" Generate url for client with specified route arguments. For the source route '/page/{page_index}'
		this method must be called with 'page_index' parameter (for '3' as 'page_index' parameter result will
		be '/page/3' for 'foo_bar' - '/page/foo_bar'). If 'host', 'protocol' and 'ports' are set as single
		element list or they are passed as method parameters, then absolute link is generated as a result.

		Every parameter in the source pattern must be defined. They can be defined as this method parameters
		or in a constructor. If source pattern has more arguments than it can be resolved, then exception will
		be raised

		:param kwargs: route arguments to use
		:return: str
		"""
		host = self.virtual_hosts[0] if self.virtual_hosts is not None and len(self.virtual_hosts) == 1 else None
		port = self.ports[0] if self.ports is not None and len(self.ports) == 1 else None
		protocol = self.protocols[0] if self.protocols is not None and len(self.protocols) == 1 else None
		route_args = self.route_args.copy()

		url_args = []
		for key in kwargs.keys():
			if key == 'host':
				host = kwargs['host']
				continue
			if key == 'port':
				port = kwargs['port']
				continue
			if key == 'protocol':
				protocol = kwargs['protocol']
				continue

			url_args.append(key)

		url_prefix = ''
		if protocol is not None and host is not None:
			url_prefix += ('%s://%s' % (protocol, host))
			if port is not None:
				url_prefix += (':%i' % port)

		pattern = self.pattern[1:-1]
		check = lambda x: WWebRoute.pattern_parentheses_removing_re.search(x) is not None or \
			WWebRoute.pattern_parentheses_removing_nested_re.search(x) is not None
		while check(pattern) is True:
			pattern = WWebRoute.pattern_parentheses_removing_re.sub('()', pattern)
			pattern = WWebRoute.pattern_parentheses_removing_nested_re.sub('(())', pattern)

		arg_i = 0
		while WWebRoute.pattern_recombination_re.search(pattern) is not None:
			arg_name = route_args[arg_i]
			arg_value = None
			if arg_name in url_args:
				arg_value = kwargs[arg_name]
			elif arg_name == 'action':
				arg_value = self.action
			elif arg_name in self.presenter_args:
				arg_value = self.presenter_args[arg_name]

			if arg_value is None:
				raise RuntimeError('Invalid argument')

			pattern = WWebRoute.pattern_recombination_re.sub(arg_value, pattern, 1)
			arg_i += 1

		return url_prefix + self.normalize_uri(pattern)


class WWebTargetRoute(WWebTargetRouteProto):
	""" Simple :class:`.WWebTargetRouteProto` implementation
	"""

	@verify_type(presenter_name=str, presenter_action=str, route=WWebRoute, route_map=WWebRouteMapProto)
	def __init__(self, presenter_name, presenter_action, route, route_map, **presenter_args):
		""" Construct new target route

		:param presenter_name: name of the target presenter. May vary from the presenter name that is specified
		in route object
		:param presenter_action: presenter action (method) to execute
		:param presenter_args: args to execute with
		:param route: source route or None if this object wasn't created within a route
		:param route_map: source route map
		"""
		self.__presenter_name = presenter_name
		self.__presenter_action = presenter_action
		self.__presenter_args = presenter_args
		self.__route = route
		self.__route_map = route_map

	def route(self):
		""" Return origin route map

		:return: WWebRoute
		"""
		return self.__route

	def route_map(self):
		""" Return origin route map

		:return: WWebRouteMap
		"""
		return self.__route_map

	def presenter_name(self):
		""" :meth:`.WWebTargetRouteProto.presenter_class` method implementation
		"""
		return self.__presenter_name

	def presenter_action(self):
		""" :meth:`.WWebTargetRouteProto.presenter_action` method implementation
		"""
		return self.__presenter_action

	def presenter_args(self):
		""" :meth:`.WWebTargetRouteProto.presenter_args` method implementation
		"""
		return self.__presenter_args


class WWebRouteMap(WWebRouteMapProto):
	""" This class represent collection of routes. It has methods for linking a source pattern to th corresponding
	presenter. There is :meth:`WWebRouteMap.route` method that allow to search for a target route by the given
	client request.

	:class:`.WWebRouteMapProto` implementation
	"""

	import_route_re = re.compile(wasp_route_import_pattern)
	""" Regexp for text parsing and custom routes importing
	"""
	import_route_arg_re = re.compile(
		'^\s*(' + wasp_route_arg_name + ')(\s*=\s*(' + wasp_route_arg_value_selection + '))?\s*$'
	)
	""" Regexp for attribute parsing of imported text
	"""

	def __init__(self):
		""" Create new route map
		"""
		self.__routes = []
		self.__error_presenter = WSimpleErrorPresenter

	@verify_type('paranoid', request=WWebRequestProto, service=WWebServiceProto)
	def route(self, request, service):
		""" :meth:`.WWebRouteMapProto.route` method implementation
		"""
		for route in self.__routes:
			result = route.match(request, service)
			if result is not None:
				if self.target_route_valid(result) is True:
					return result

	def error_presenter(self):
		""" :meth:`.WWebRouteMapProto.error_presenter` method implementation
		"""
		return self.__error_presenter

	@verify_subclass(presenter=WWebErrorPresenter)
	def set_error_presenter(self, presenter):
		""" Set error presenter for this route map

		:param presenter: presenter to be used for error handling
		:return: None
		"""
		self.__error_presenter = presenter

	@verify_type('paranoid', pattern=str, presenter=str)
	def connect(self, pattern, presenter, **kwargs):
		""" Connect the given pattern with the given presenter

		:param pattern: URI pattern
		:param presenter: target presenter name
		:param kwargs: route arguments (see :class:`.WWebRoute`)
		:return: None
		"""
		self.__routes.append(WWebRoute(pattern, presenter, **kwargs))

	@verify_type(route=WWebRoute)
	def append(self, route):
		""" Append route to collection

		:param route: route to add
		:return: None
		"""
		self.__routes.append(route)

	@verify_type(route_as_txt=str)
	@verify_value(route_as_txt=lambda x: len(x) > 0)
	def import_route(self, route_as_txt):
		""" Import route written as a string

		:param route_as_txt: single string (single route) to import
		:return: None
		"""
		route_match = WWebRouteMap.import_route_re.match(route_as_txt)
		if route_match is None:
			raise ValueError('Invalid route code')

		pattern = route_match.group(1)
		presenter_name = route_match.group(2)
		route_args = route_match.group(4)  # may be None

		if route_args is not None:
			result_args = {}
			for arg_declaration in route_args.split(","):
				arg_match = WWebRouteMap.import_route_arg_re.match(arg_declaration)
				if arg_match is None:
					raise RuntimeError('Invalid argument declaration in route')
				result_args[arg_match.group(1)] = arg_match.group(3)

			self.connect(pattern, presenter_name, **result_args)
		else:
			self.connect(pattern, presenter_name)


class WSimplePresenterCollection(WWebPresenterCollectionProto):
	""" This is a simple presenter collection

	:class:`.WWebPresenterCollectionProto` implementation
	"""

	def __init__(self):
		""" Construct new collection
		"""
		WWebPresenterCollectionProto.__init__(self)
		self.__presenters = {}

	@verify_subclass(presenter=WWebPresenter)
	def add(self, presenter):
		""" Add presenter to this collection

		:param presenter: presenter to add
		:return: None
		"""
		self.__presenters[presenter.__presenter_name__()] = presenter

	@verify_type(section=str, presenter_name=str)
	@verify_value(section=lambda x: len(x) > 0, presenter_name=lambda x: len(x) > 0)
	def presenter(self, presenter_name):
		""" :meth:`.WWebPresenterCollectionProto.presenter` method implementation
		"""
		if presenter_name in self.__presenters.keys():
			return self.__presenters[presenter_name]

	@verify_type(presenter_name=str)
	@verify_value(presenter_name=lambda x: len(x) > 0)
	def has(self, presenter_name):
		""" :meth:`.WWebPresenterCollectionProto.has` method implementation
		"""
		return presenter_name in self.__presenters.keys()

	def __len__(self):
		""" Return total presenters count

		:return: int
		"""
		return len(self.__presenters)


class WWebService(WWebServiceProto):
	""" This class joins together all web-package functionality.

	:class:`.WWebServiceProto` implementation
	"""

	@verify_type(route_map=(WWebRouteMap, None), collection=(WWebPresenterCollectionProto, None))
	@verify_type(debugger=(WWebDebugInfo, None))
	@verify_subclass(factory=(WWebPresenterFactoryProto, None))
	def __init__(self, route_map=None, collection=None, factory=None, debugger=None):
		""" Create new service

		:param route_map: route map to be uses (if None, internal route map will be used)
		:param collection: collection to be used (if None, internal collection will be used)
		"""
		self.__route_map = route_map if route_map is not None else WWebRouteMap()
		self.__presenter_collection = collection
		self.__factory = factory() if factory is not None else WWebPresenterFactory()
		self.__debugger = debugger
		if self.__presenter_collection is None:
			self.__presenter_collection = WSimplePresenterCollection()

	def route_map(self):
		""" :meth:`.WWebServiceProto.route_map` method implementation
		"""
		return self.__route_map

	def presenter_collection(self):
		""" :meth:`.WWebServiceProto.presenter_collection` method implementation
		"""
		return self.__presenter_collection

	def presenter_factory(self):
		""" :meth:`.WWebServiceProto.presenter_factory` method implementation
		"""
		return self.__factory

	@verify_type(session=WWebSessionProto)
	def process_request(self, session):
		""" Process single request from the given session

		:param session: session for reading requests and writing responses
		:return: None
		"""

		debugger = self.debugger()
		debugger_session_id = debugger.session_id() if debugger is not None else None

		try:
			request = session.read_request()
			if debugger_session_id is not None:
				debugger.request(
					debugger_session_id, request, session.protocol_version(), session.protocol()
				)

			try:
				target_route = self.route_map().route(request, self)
				if debugger_session_id is not None:
					debugger.target_route(debugger_session_id, target_route)

				if target_route is not None:
					response = self.execute(request, target_route)
				else:
					presenter_cls = self.route_map().error_presenter()
					presenter = presenter_cls(request)
					response = presenter.error_code(code=404)

				if debugger_session_id is not None:
					debugger.response(debugger_session_id, response)

			except Exception as e:
				if debugger_session_id is not None:
					debugger.exception(debugger_session_id, e)

				presenter_cls = self.route_map().error_presenter()
				presenter = presenter_cls(request)
				response = presenter.exception_error(e)

			session.write_response(request, response, *response.__pushed_responses__())
		except Exception as e:
			if debugger_session_id is not None:
				debugger.exception(debugger_session_id, e)

			session.session_close()

		if debugger_session_id is not None:
			debugger.finalize(debugger_session_id)

	@verify_type('paranoid', request=WWebRequestProto, target_route=WWebTargetRouteProto)
	def create_presenter(self, request, target_route):
		""" Create presenter from the given requests and target routes

		:param request: client request
		:param target_route: route to use
		:return: WWebPresenter
		"""
		presenter_name = target_route.presenter_name()
		if self.presenter_collection().has(presenter_name) is False:
			raise RuntimeError('No such presenter: %s' % presenter_name)
		presenter_class = self.presenter_collection().presenter(presenter_name)
		return self.presenter_factory().instantiate(presenter_class, request, target_route, self)

	@verify_type('paranoid', request=WWebRequestProto, target_route=WWebTargetRouteProto)
	def execute(self, request, target_route):
		""" :meth:`.WWebServiceProto.execute` method implementation
		"""
		presenter = self.create_presenter(request, target_route)
		presenter_name = target_route.presenter_name()
		action_name = target_route.presenter_action()
		presenter_args = target_route.presenter_args()

		if hasattr(presenter, action_name) is False:
			raise RuntimeError('No such action "%s" for "%s" presenter' % (action_name, presenter_name))

		action = getattr(presenter, action_name)
		if ismethod(action) is False:
			raise RuntimeError(
				'Unable to execute "%s" action for "%s" presenter' % (action_name, presenter_name)
			)

		args_spec = getfullargspec(action)
		defaults = len(args_spec.defaults) if args_spec.defaults is not None else 0
		action_args = list()
		action_kwargs = dict()

		for i in range(len(args_spec.args)):
			arg = args_spec.args[i]
			if arg == 'self':
				continue

			is_kwarg = i >= (len(args_spec.args) - defaults)

			if is_kwarg is False:
				action_args.append(presenter_args[arg])
			elif arg in presenter_args:
				action_kwargs[arg] = presenter_args[arg]

		return action(*action_args, **action_kwargs)

	@verify_type('paranoid', pattern=str, presenter=(type, str))
	@verify_value('paranoid', presenter=lambda x: issubclass(x, WWebPresenter) or isinstance(x, str))
	def connect(self, pattern, presenter, **kwargs):
		""" Shortcut for self.route_map().connect() method. It is possible to pass presenter class instead of
		its name - in that case such class will be saved in presenter collection and it will be available in
		route matching.

		:param pattern: same as pattern in :meth:`.WWebRouteMap.connect` method
		:param presenter: presenter name or presenter class
		:param kwargs: same as kwargs in :meth:`.WWebRouteMap.connect` method
		:return: None
		"""
		if isinstance(presenter, type) and issubclass(presenter, WWebPresenter) is True:
			self.presenter_collection().add(presenter)
			presenter = presenter.__presenter_name__()
		self.__route_map.connect(pattern, presenter, **kwargs)

	@verify_subclass(presenter=WWebPresenter)
	def add_presenter(self, presenter):
		""" Add presenter to a collection. If the given presenter is a :class:`.WWebEnhancedPresenter` instance
		then public routes are checked (via :meth:`..WWebEnhancedPresenter.__public_routes__` method) and are
		added in this route map

		:param presenter: presenter to add
		:return: None
		"""
		self.__presenter_collection.add(presenter)
		if issubclass(presenter, WWebEnhancedPresenter) is True:
			for route in presenter.__public_routes__():
				self.route_map().append(route)

	@verify_type('paranoid', request=WWebRequestProto, presenter_name=str)
	@verify_type(original_target_route=WWebTargetRoute)
	def proxy(self, request, original_target_route, presenter_name, **kwargs):
		""" Execute the given presenter as a target for the given client request

		:param request: original client request
		:param original_target_route: previous target route
		:param presenter_name: target presenter name
		:param kwargs: presenter arguments
		:return: WWebResponseProto
		"""

		action_kwargs = kwargs.copy()
		action_name = 'index'
		if 'action' in action_kwargs:
			action_name = action_kwargs['action']
			action_kwargs.pop('action')

		original_route = original_target_route.route()
		original_route_map = original_target_route.route_map()
		target_route = WWebTargetRoute(
			presenter_name, action_name, original_route, original_route_map, **action_kwargs
		)
		return self.execute(request, target_route)

	def debugger(self):
		return self.__debugger


class WWebEnhancedPresenter(WWebPresenter, metaclass=ABCMeta):
	""" This is enhanced version of presenter. Besides :class:`.WWebPresenter` class. This class objects
	could use an origin service instance and an origin target route
	"""

	@verify_type('paranoid', request=WWebRequestProto)
	@verify_type(target_route=WWebTargetRoute, service=WWebService)
	def __init__(self, request, target_route, service):
		""" Create new enhanced presenter

		:param request: client request
		:param target_route: source target route
		:param service: source service
		"""
		WWebPresenter.__init__(self, request)
		self.__target_route = target_route
		self.__service = service

	def __target_route__(self):
		""" Return origin target route

		:return: WWebTargetRoute
		"""
		return self.__target_route

	def __service__(self):
		""" Return origin service instance

		:return: WWebService
		"""
		return self.__service

	@classmethod
	def __public_routes__(cls):
		""" Return web routes, that this presenter makes "public" (available to :class:`.WWebService` route map)

		see :meth:`.WWebService.add_presenter` method

		:return: tuple/list of WWebRoute
		"""
		return tuple()

	@verify_type('paranoid', presenter_name=str)
	def __proxy__(self, presenter_name, **kwargs):
		""" Execute the given presenter as a target for the original client request

		:param presenter_name: target presenter name
		:param kwargs: presenter arguments
		:return: WWebResponseProto
		"""
		return self.__service__().proxy(self.__request__(), self.__target_route__(), presenter_name, **kwargs)


class WWebPresenterFactory(WWebPresenterFactoryProto):
	""" WWebPresenterFactoryProto implementation. Can construct classes that do not have their own constructor and
	are derived from WWebPresenter or from WWebEnhancedPresenter classes
	"""

	@staticmethod
	def presenter_constructor(presenter_class, request, target_route, service):
		""" Function that is used for WWebPresenter creating

		:param presenter_class: class to construct
		:param request: original client request
		:param target_route: target route to execute
		:param service: source (parent) service
		:return: WWebPresenter
		"""
		return presenter_class(request)

	@staticmethod
	def enhanced_presenter_constructor(presenter_class, request, target_route, service):
		""" Function that is used for WWebEnhancedPresenter creating

		:param presenter_class: class to construct
		:param request: original client request
		:param target_route: target route to execute
		:param service: source (parent) service
		:return: WWebEnhancedPresenter
		"""
		return presenter_class(request, target_route, service)

	def __init__(self):
		""" Construct new factory
		"""
		WWebPresenterFactoryProto.__init__(self)

		self.__constructors = {
			WWebPresenter.__init__: WWebPresenterFactory.presenter_constructor,
			WWebEnhancedPresenter.__init__: WWebPresenterFactory.enhanced_presenter_constructor
		}

	@verify_subclass(presenter_class=WWebPresenter)
	def _add_constructor(self, presenter_class, constructor_fn):
		self.__constructors[presenter_class.__init__] = constructor_fn

	@verify_subclass(presenter_class=WWebPresenter)
	def instantiable(self, presenter_class):
		""" :meth:`.WWebPresenterFactoryProto.instantiable` method implementation.

		Checks if class doesn't have its own constructor and is derived from WWebPresenter or from
		WWebEnhancedPresenter

		:param presenter_class: class to check
		:return: bool
		"""
		return presenter_class.__init__ in self.__constructors.keys()

	@verify_type('paranoid', request=WWebRequestProto, target_route=WWebTargetRouteProto, service=WWebService)
	@verify_subclass('paranoid', presenter_class=WWebPresenter)
	def instantiate(self, presenter_class, request, target_route, service, *args, **kwargs):
		""" :meth:`.WWebPresenterFactoryProto.instantiate` method implementation.

		Construct new presenter or raise en exception if it isn't possible.

		:param presenter_class: class to construct
		:param request: original client request
		:param target_route: target route to execute
		:param service: source (parent) service
		:param args: additional parameters (do not used)
		:param kwargs: additional parameters (do not used)
		:return: WWebPresenter
		"""
		if self.instantiable(presenter_class) is False:
			raise RuntimeError('Presenter class is not instantiable')
		return self.__constructors[presenter_class.__init__](presenter_class, request, target_route, service)
