# -*- coding: utf-8 -*-
#! TODO: cleanup is required

import pytest
import re

from wasp_general.network.primitives import WIPV4SocketInfo
from wasp_general.network.web.proto import WWebResponseProto, WWebPresenter, WWebTargetRouteProto, WWebRouteMapProto
from wasp_general.network.web.proto import WWebPresenterCollectionProto, WWebSessionProto, WWebServiceProto
from wasp_general.network.web.request import WWebRequest
from wasp_general.network.web.service import WSimpleErrorPresenter, WWebTargetRoute, WWebRoute, WWebRouteMap
from wasp_general.network.web.service import WWebService, WSimplePresenterCollection, WWebEnhancedPresenter
from wasp_general.network.web.service import WWebPresenterFactory
from wasp_general.network.web.headers import WHTTPHeaders
from wasp_general.network.web.debug import WWebDebugInfo


class TestWSimpleErrorPresenter:

	class Session(WWebSessionProto):

		def client_address(self):
			WIPV4SocketInfo('127.0.0.1', 65000)

		def server_address(self):
			WIPV4SocketInfo('127.0.0.1', 80)

		def protocol(self):
			return 'http'

		def protocol_version(self):
			return '0.9'

		def read_request(self):
			pass

		def write_response(self, request, response):
			pass

		def session_close(self):
			pass

	def test_error_presenter(self):
		session = TestWSimpleErrorPresenter.Session()
		request = WWebRequest(session, 'GET', '/foo')

		error = WSimpleErrorPresenter(request)
		assert(isinstance(error, WSimpleErrorPresenter) is True)
		assert(isinstance(error.error_code(501), WWebResponseProto) is True)
		assert(error.error_code(502).status() == 502)

		assert(isinstance(error.exception_error(ValueError('Text exception')), WWebResponseProto) is True)
		assert(error.exception_error(ValueError('Text exception')).status() == 500)

		name = WSimpleErrorPresenter.__presenter_name__()
		assert(isinstance(name, str) is True)
		assert(len(name) > 0)


class TestWWebTargetRoute:

	class Presenter(WWebPresenter):

		@classmethod
		def __presenter_name__(cls):
			return 'presenter name'

	class RouteMap(WWebRouteMapProto):

		def route(self, request, service):
			pass

		def error_presenter(self):
			pass

	def test_target_route(self):
		route_map = TestWWebTargetRoute.RouteMap()
		source_route = WWebRoute('/', 'presenter name')
		route = WWebTargetRoute('presenter name', 'action1', source_route, route_map, arg1='foo', arg2=3)
		assert(isinstance(route, WWebTargetRouteProto) is True)
		assert(route.route_map() == route_map)
		assert(route.presenter_name() == 'presenter name')
		assert(route.presenter_action() == 'action1')
		assert(route.presenter_args()['arg1'] == 'foo')
		assert(route.presenter_args()['arg2'] == 3)

		source_route = WWebRoute('/', 'presenter name')
		route = WWebTargetRoute('presenter name', 'action1', source_route, route_map, arg1='foo', arg2=3)
		assert(route.route() == source_route)


class TestWWebRoute:

	class Session(WWebSessionProto):

		def client_address(self):
			WIPV4SocketInfo('127.0.0.1', 65000)

		def server_address(self):
			WIPV4SocketInfo('127.0.0.1', 80)

		def protocol(self):
			return 'http'

		def protocol_version(self):
			return '0.9'

		def read_request(self):
			pass

		def write_response(self, request, response):
			pass

		def session_close(self):
			pass

	class Service(WWebServiceProto):

		def route_map(self):
			return

		def presenter_collection(self):
			return

		def presenter_factory(self):
			return

		def execute(self, request, target_route):
			return

	def test_arg_search(self):
		pytest.raises(TypeError, WWebRoute.ArgSearch)
		pytest.raises(NotImplementedError, WWebRoute.ArgSearch.args, None)
		pytest.raises(NotImplementedError, WWebRoute.ArgSearch.reduce_pattern, None)

		assert(issubclass(WWebRoute.BasicArgSearch, WWebRoute.ArgSearch) is True)
		basic_search = WWebRoute.BasicArgSearch('/section/{action}/page/{page_param1}')
		args = list(basic_search.args())
		args.sort(key=lambda x: x[1])
		assert(args == [('action', 9), ('page_param1', 23)])
		reduce_fn = basic_search.reduce_pattern()
		test_re = re.compile(reduce_fn('/foo/{bar}//1/page/'))
		assert(test_re.match('/foo/var1//1/page/') is not None)
		assert(test_re.match('/foo/1//1/page/') is not None)
		assert(test_re.match('/foo/1/page') is None)

		assert(issubclass(WWebRoute.CustomArgSearch, WWebRoute.ArgSearch) is True)
		custom_search = WWebRoute.CustomArgSearch('arg_foo', 77, '{arg_foo: "(\d+)"}', '(\d+)')
		assert(custom_search.args() == (('arg_foo', 77),))
		reduce_fn = custom_search.reduce_pattern()
		assert(reduce_fn('/zzz{arg_foo: "(\d+)"}aaa//') == '/zzz(\d+)aaa//')

		custom_search = WWebRoute.CustomArgSearch('arg1', 77, '{pattern!}', 'replace_with_text')
		reduce_fn = custom_search.reduce_pattern()
		assert(reduce_fn('/page/{pattern!}/zzz') == '/page/replace_with_text/zzz')

		pattern = '/section/{section_action: "(\w+)"}/page/{page_index: "(\d+)"}}'
		args_searches = list(WWebRoute.CustomArgSearch.custom(pattern))
		assert(args_searches[0].args() == (('section_action', 9),))
		reduce_fn = args_searches[0].reduce_pattern()
		reduce_result = reduce_fn('/section/{section_action: "(\w+)"}/page/{page_index: "(\d+)"}')
		assert(reduce_result == '/section/(\w+)/page/{page_index: "(\d+)"}')
		assert(args_searches[1].args() == (('page_index', 40),))
		reduce_fn = args_searches[1].reduce_pattern()
		reduce_result = reduce_fn('/section/{section_action: "(\w+)"}/page/{page_index: "(\d+)"}')
		assert(reduce_result == '/section/{section_action: "(\w+)"}/page/(\d+)')

	def test_route(self):
		route_map = TestWWebTargetRoute.RouteMap()
		route = WWebRoute('/foo/section/{action}/{index:"(\d+)"}/page/{page_action}', 'presenter name')
		request = WWebRequest(TestWWebRoute.Session(), 'GET', '/foo/section/bla_bla_action/13/page/show_page')

		collection = WSimplePresenterCollection()
		collection.add(TestWWebTargetRoute.Presenter)
		service = TestWWebRoute.Service()
		service.presenter_collection = lambda: collection
		service.route_map = lambda: route_map
		match = route.match(request, service)
		assert(isinstance(match, WWebTargetRoute) is True)
		assert(match.presenter_name() == 'presenter name')
		assert(match.presenter_action() == 'bla_bla_action')
		assert(match.presenter_args() == {'index': '13', 'page_action': 'show_page'})

		route = WWebRoute(
			'/index', 'presenter name', action='default_action', protocols=('http',), arg1='value1'
		)
		request = WWebRequest(TestWWebRoute.Session(), 'GET', '/index')
		match = route.match(request, service)
		assert(isinstance(match, WWebTargetRoute) is True)
		assert(match.presenter_name() == 'presenter name')
		assert(match.presenter_action() == 'default_action')
		assert(match.presenter_args()['arg1'] == 'value1')

		session = TestWWebRoute.Session()
		request = WWebRequest(session, 'GET', '/index')
		assert(route.match(request, service) is not None)

		session.protocol = lambda: 'https'
		assert(route.match(request, service) is None)

		route = WWebRoute(
			'/index//', 'presenter name', virtual_hosts=('ns.foo.bar',), methods=('POST',), ports=(8080,)
		)
		session.protocol = lambda: 'http'
		session.server_address = lambda: WIPV4SocketInfo('127.0.0.1', 8080)
		request = WWebRequest(session, 'POST', '/index//', headers=WHTTPHeaders(host='ns.foo.bar'))
		assert(route.match(request, service) is not None)

		session.server_address = lambda: WIPV4SocketInfo('127.0.0.1', 8081)
		request = WWebRequest(session, 'POST', '/index//', headers=WHTTPHeaders(host='ns.foo.bar'))
		assert(route.match(request, service) is None)

		session.server_address = lambda: WIPV4SocketInfo('127.0.0.1', 8080)
		request = WWebRequest(session, 'GET', '/index', headers=WHTTPHeaders(host='ns.foo.bar'))
		assert(route.match(request, service) is None)

		request = WWebRequest(session, 'POST', '/index')
		assert(route.match(request, service) is None)

		request = WWebRequest(session, 'POST', '/section', headers=WHTTPHeaders(host='ns.foo.bar'))
		assert(route.match(request, service) is None)

		request = WWebRequest(session, 'POST', '/index', headers=WHTTPHeaders(host='ns.foo.bar'))
		assert(route.match(request, service) is not None)

		route = WWebRoute('/index', 'presenter name', arg1='value1')
		assert(route.url_for() == '/index')

		route = WWebRoute('/index/{index}', 'presenter name', index='1')
		assert(route.url_for() == '/index/1')
		assert(route.url_for(index='page2') == '/index/page2')

		route = WWebRoute('/page/{action}/1', 'presenter name', protocols=('https',))
		assert(route.url_for(host='foo.bar') == 'https://foo.bar/page/index/1')
		assert(route.url_for(host='foo.bar', port=14) == 'https://foo.bar:14/page/index/1')
		assert(route.url_for(protocol='http', host='foo.bar') == 'http://foo.bar/page/index/1')

		route = WWebRoute('/page/{var_name}/1', 'presenter name')
		pytest.raises(RuntimeError, route.url_for)


class TestWWebRouteMap:

	class ErrorPresenter(WSimpleErrorPresenter):
		pass

	class Presenter(WWebPresenter):

		def index(self):
			pass

		@classmethod
		def __presenter_name__(cls):
			return 'presenter name'

	class SamplePresenter(WWebPresenter):

		def show(self):
			pass

		def index(self):
			pass

		@classmethod
		def __presenter_name__(cls):
			return 'SamplePresenter'

	class EnhancedPresenter(WWebEnhancedPresenter):

		def index(self):
			pass

		@classmethod
		def __presenter_name__(cls):
			return 'enhanced presenter name'

	class TargetRoute(WWebTargetRouteProto):

		def presenter_name(self):
			return 'enhanced presenter name'

		def presenter_action(self):
			return 'index'

	def test_route_map(self):
		collection = WSimplePresenterCollection()
		collection.add(TestWWebRouteMap.Presenter)
		collection.add(TestWWebRouteMap.EnhancedPresenter)
		service = TestWWebRoute.Service()
		service.presenter_collection = lambda: collection

		route_map = WWebRouteMap()
		service.route_map = lambda: route_map
		assert(isinstance(route_map, WWebRouteMap) is True)
		assert(isinstance(route_map, WWebRouteMapProto) is True)
		assert(route_map.error_presenter() == WSimpleErrorPresenter)

		route_map.set_error_presenter(TestWWebRouteMap.ErrorPresenter)
		assert(route_map.error_presenter() == TestWWebRouteMap.ErrorPresenter)

		request = WWebRequest(TestWWebRoute.Session(), 'GET', '/index')
		assert(route_map.route(request, service) is None)
		route_map.connect('/index', 'presenter name')
		assert(route_map.route(request, service) is not None)

		request = WWebRequest(TestWWebRoute.Session(), 'GET', '/page')
		assert(route_map.route(request, service) is None)
		route_map.append(WWebRoute('/page', 'presenter name'))
		assert(route_map.route(request, service) is not None)

	def test_import(self):

		collection = WSimplePresenterCollection()
		collection.add(TestWWebRouteMap.SamplePresenter)
		service = TestWWebRoute.Service()
		service.presenter_collection = lambda: collection
		route_map = WWebRouteMap()
		service.route_map = lambda: route_map

		request = WWebRequest(TestWWebRoute.Session(), 'GET', '/page/1')
		assert(route_map.route(request, service) is None)

		route_map.import_route('/page/{code:"(\d+)"} => SamplePresenter (action = show, code=404, v, foo=bar)')
		target_route = route_map.route(request, service)
		assert(target_route is not None)
		assert(target_route.presenter_args() == {'code': '1', 'v': None, 'foo': 'bar'})

		request = WWebRequest(TestWWebRoute.Session(), 'GET', '/index')
		assert(route_map.route(request, service) is None)
		route_map.import_route('/index => SamplePresenter')
		target_route = route_map.route(request, service)
		assert(target_route is not None)
		assert(target_route.presenter_args() == {})

		pytest.raises(ValueError, route_map.import_route, 'AAAA')
		pytest.raises(RuntimeError, route_map.import_route, '/page => Presenter (()')


class TestWSimplePresenterCollection:

	class DummyPresenter(WWebPresenter):

		@classmethod
		def __presenter_name__(cls):
			return 'dummy presenter'

	def test_collection(self):
		collection = WSimplePresenterCollection()
		assert(isinstance(collection, WSimplePresenterCollection) is True)
		assert(isinstance(collection, WWebPresenterCollectionProto) is True)
		assert(len(collection) == 0)

		assert(collection.presenter('Name') is None)
		assert(collection.has('Name') is False)
		assert(collection.has('dummy presenter') is False)
		collection.add(TestWWebTargetRoute.Presenter)
		collection.add(TestWSimplePresenterCollection.DummyPresenter)
		assert(collection.presenter('dummy presenter') == TestWSimplePresenterCollection.DummyPresenter)
		assert(collection.has('dummy presenter') is True)
		assert(len(collection) == 2)


class TestWWebService:

	class Collection(WSimplePresenterCollection):
		pass

	class WebRoute(WWebRouteMap):
		pass

	class Response(WWebResponseProto):

		def status(self):
			return 200

	class Presenter(WWebPresenter):

		__test__ = 1

		@classmethod
		def __presenter_name__(cls):
			return 'presenter'

		def index(self):
			return 'presenter-index'

		def add(self, a, b=5):
			return a + b

	class EnhancedPresenter(WWebEnhancedPresenter):

		def index(self, p=0):
			return TestWWebService.Response()

		@classmethod
		def __presenter_name__(cls):
			return 'enhanced presenter name'

	class Session(WWebSessionProto):

		written_responses = []

		def client_address(self):
			return

		def server_address(self):
			return

		def protocol_version(self):
			return

		def protocol(self):
			return 'http'

		def read_request(self):
			return WWebRequest(self, 'GET', '/1')

		def write_response(self, request, response):
			self.written_responses.append(response.status())

		def session_close(self):
			self.written_responses.append(-1)

	class Debugger(WWebDebugInfo):

		__requests__ = {}
		__responses__ = {}
		__target_routes__ = {}
		__exceptions__ = {}
		__finalized__ = []

		id = 0

		def session_id(self):
			self.__class__.id += 1
			self.__class__.__exceptions__[self.__class__.id] = []
			return self.__class__.id

		def request(self, session_id, request, protocol_version, protocol):
			self.__class__.__requests__[session_id] = (request, protocol_version, protocol)

		def response(self, session_id, response):
			self.__class__.__responses__[session_id] = response

		def target_route(self, session_id, target_route):
			self.__class__.__target_routes__[session_id] = target_route

		def exception(self, session_id, exc):
			self.__class__.__exceptions__[session_id].append(exc)

		def finalize(self, session_id):
			self.__class__.__finalized__.append(session_id)

	def test_service(self):

		service = WWebService()
		assert(isinstance(service.route_map(), WWebRouteMap) is True)
		assert(isinstance(service.presenter_collection(), WSimplePresenterCollection) is True)

		service = WWebService(
			route_map=TestWWebService.WebRoute(),
			collection=TestWWebService.Collection(),
			debugger=TestWWebService.Debugger()
		)
		assert(isinstance(service.route_map(), TestWWebService.WebRoute) is True)
		assert(isinstance(service.presenter_collection(), TestWWebService.Collection) is True)

		session = TestWWebService.Session()
		service.process_request(session)
		assert(TestWWebService.Session.written_responses == [404])

		service.connect('/{p}', TestWWebService.EnhancedPresenter)
		service.process_request(session)
		assert(TestWWebService.Session.written_responses == [404, 200])

		session.read_request = lambda: WWebRequest(session, 'GET', '/page/1')
		service.process_request(session)
		assert(TestWWebService.Session.written_responses == [404, 200, 404])

		class P(WWebEnhancedPresenter):

			@classmethod
			def __presenter_name__(cls):
				return 'P-presenter'

			@classmethod
			def __public_routes__(cls):
				return WWebRoute('/page/1', cls.__presenter_name__(), d=1),

			def index(self, d):
				return TestWWebService.Response()

		service.add_presenter(P)
		service.process_request(session)
		assert(TestWWebService.Session.written_responses == [404, 200, 404, 200])

		target_route = TestWWebRouteMap.TargetRoute()
		target_route.presenter_name = lambda: 'Unknown presenter'
		service.route_map().route = lambda x, y: target_route
		service.process_request(session)
		assert(TestWWebService.Session.written_responses == [404, 200, 404, 200, 500])

		service.add_presenter(TestWWebService.Presenter)

		target_route.presenter_name = lambda: 'presenter'
		target_route.presenter_action = lambda: 'unknown action'
		service.process_request(session)
		assert(TestWWebService.Session.written_responses == [404, 200, 404, 200, 500, 500])

		target_route.presenter_action = lambda: '__test__'
		service.process_request(session)
		assert(TestWWebService.Session.written_responses == [404, 200, 404, 200, 500, 500, 500])

		target_route.presenter_name = lambda: 'P-presenter'
		target_route.presenter_action = lambda: 'index'

		original_route = WWebTargetRoute(
			'P-presenter', 'index', WWebRoute('/', 'P-presenter'), service.route_map()
		)
		response = service.proxy(session.read_request(), original_route, 'presenter', action='add', a=2)
		assert(response == 7)

		def exc_fn():
			raise RuntimeError('')
		session.read_request = exc_fn
		service.process_request(session)
		assert(TestWWebService.Session.written_responses == [404, 200, 404, 200, 500, 500, 500, -1])

		requests = {}
		for key in TestWWebService.Debugger.__requests__.keys():
			requests[key] = TestWWebService.Debugger.__requests__[key][0].path()

		assert(requests == {
			1: '/1', 2: '/1', 3: '/page/1', 4: '/page/1', 5: '/page/1', 6: '/page/1', 7: '/page/1'
		})

		responses = {}
		for key in TestWWebService.Debugger.__responses__.keys():
			responses[key] = TestWWebService.Debugger.__responses__[key].status()
		assert(responses == {1: 404, 2: 200, 3: 404, 4: 200})

		targets = {}
		for key in TestWWebService.Debugger.__target_routes__.keys():
			target = TestWWebService.Debugger.__target_routes__[key]
			targets[key] = target.presenter_name() if target is not None else None
		assert(targets == {
			1: None, 2: 'enhanced presenter name', 3: None, 4: 'P-presenter',
			5: 'P-presenter', 6: 'P-presenter', 7: 'P-presenter'
		})

		exc = {}
		for key in TestWWebService.Debugger.__exceptions__.keys():
			exc[key] = [x.__class__ for x in TestWWebService.Debugger.__exceptions__[key]]
		assert(exc == {
			1: [], 2: [], 3: [], 4: [], 5: [RuntimeError], 6: [RuntimeError], 7: [RuntimeError],
			8: [RuntimeError]
		})

		assert(TestWWebService.Debugger.__finalized__ == [1, 2, 3, 4, 5, 6, 7, 8])


class TestWWebEnhancedPresenter:

	class Presenter(WWebEnhancedPresenter):

		@classmethod
		def __presenter_name__(cls):
			return 'presenter name'

	def test_presenter(self):
		assert(issubclass(WWebEnhancedPresenter, WWebPresenter) is True)

		service = WWebService()
		service.add_presenter(TestWWebService.Presenter)
		session = TestWWebService.Session()
		request = WWebRequest(session, 'GET', '/1')
		route = WWebRoute('/1', 'presenter name')
		target_route = WWebTargetRoute('presenter name', 'index', route, service.route_map())
		presenter = TestWWebEnhancedPresenter.Presenter(request, target_route, service)

		assert(presenter.__target_route__() == target_route)
		assert(presenter.__service__() == service)
		assert(WWebEnhancedPresenter.__public_routes__() == tuple())

		response = presenter.__proxy__('presenter', action='add', a=2)
		assert(response == 7)


class TestWWebPresenterFactory:

	def test_factory(self):
		factory = WWebPresenterFactory()

		class CustomPresenter(WWebPresenter):

			def __init__(self):
				return

			def __presenter_name__(cls):
				return

		assert(factory.instantiable(CustomPresenter) is False)

		service = WWebService()
		session = TestWWebService.Session()
		request = WWebRequest(session, 'GET', '/1')
		route = WWebRoute('/1', 'presenter name')
		target_route = WWebTargetRoute('presenter name', 'index', route, service.route_map())
		pytest.raises(
			RuntimeError, factory.instantiate, CustomPresenter, request, target_route, service
		)

		class CustomFactory(WWebPresenterFactory):

			def __init__(self):
				WWebPresenterFactory.__init__(self)

				def constructor(presenter_class, request, target_route, service):
					return CustomPresenter()

				self._add_constructor(CustomPresenter, constructor)

		p = CustomFactory().instantiate(CustomPresenter, request, target_route, service)
		assert(isinstance(p, CustomPresenter) is True)
