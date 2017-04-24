# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.web.proto import WWebResponseProto, WWebRequestProto, WWebSessionProto, WWebPresenter
from wasp_general.network.web.proto import WWebTargetRouteProto, WWebRouteMapProto, WWebErrorPresenter
from wasp_general.network.web.proto import WWebServiceProto, WWebPresenterCollectionProto, WWebPresenterFactoryProto

from wasp_general.network.web.headers import WHTTPHeaders


def test_abstract():
	pytest.raises(TypeError, WWebRequestProto)
	pytest.raises(NotImplementedError, WWebRequestProto.session, None)
	pytest.raises(NotImplementedError, WWebRequestProto.method, None)
	pytest.raises(NotImplementedError, WWebRequestProto.path, None)
	pytest.raises(NotImplementedError, WWebRequestProto.headers, None)

	pytest.raises(TypeError, WWebSessionProto)
	pytest.raises(NotImplementedError, WWebSessionProto.client_address, None)
	pytest.raises(NotImplementedError, WWebSessionProto.server_address, None)
	pytest.raises(NotImplementedError, WWebSessionProto.protocol_version, None)
	pytest.raises(NotImplementedError, WWebSessionProto.protocol, None)
	pytest.raises(NotImplementedError, WWebSessionProto.read_request, None)
	pytest.raises(
		NotImplementedError, WWebSessionProto.write_response, None,
		TestWWebRequestProto.Request(), TestWWebResponseProto()
	)
	pytest.raises(NotImplementedError, WWebSessionProto.session_close, None)

	pytest.raises(TypeError, WWebTargetRouteProto)
	pytest.raises(NotImplementedError, WWebTargetRouteProto.presenter_name, None)
	pytest.raises(NotImplementedError, WWebTargetRouteProto.presenter_action, None)

	class Service(WWebServiceProto):

		def route_map(self):
			return

		def presenter_collection(self):
			return

		def presenter_factory(self):
			return

		def execute(self, request, target_route):
			return

	pytest.raises(TypeError, WWebRouteMapProto)
	pytest.raises(NotImplementedError, WWebRouteMapProto.route, None, TestWWebRequestProto.Request(), Service())
	pytest.raises(NotImplementedError, WWebRouteMapProto.error_presenter, None)

	pytest.raises(TypeError, WWebErrorPresenter)
	pytest.raises(NotImplementedError, WWebErrorPresenter.error_code, None, 100)
	pytest.raises(NotImplementedError, WWebErrorPresenter.exception_error, None, Exception(''))

	pytest.raises(TypeError, WWebServiceProto)
	pytest.raises(NotImplementedError, WWebServiceProto.route_map, None)
	pytest.raises(NotImplementedError, WWebServiceProto.presenter_collection, None)
	pytest.raises(NotImplementedError, WWebServiceProto.presenter_factory, None)
	pytest.raises(
		NotImplementedError, WWebServiceProto.execute, None,
		TestWWebRequestProto.Request(), TestWWebTargetRouteProto.Route()
	)

	pytest.raises(TypeError, WWebPresenterCollectionProto)
	pytest.raises(NotImplementedError, WWebPresenterCollectionProto.presenter, None, 'presenter')
	pytest.raises(NotImplementedError, WWebPresenterCollectionProto.has, None, 'presenter')

	pytest.raises(TypeError, WWebPresenter)
	pytest.raises(NotImplementedError, WWebPresenter.__presenter_name__)

	pytest.raises(TypeError, WWebPresenterFactoryProto)
	pytest.raises(NotImplementedError, WWebPresenterFactoryProto.instantiable, None, TestWWebPresenter.Presenter)
	pytest.raises(NotImplementedError, WWebPresenterFactoryProto.instantiate, None, TestWWebPresenter.Presenter)


class TestWWebResponseProto:

	def test_response(self):
		response = WWebResponseProto()
		assert(isinstance(response, WWebResponseProto) is True)
		assert(response.status() is None)
		assert(response.headers() is None)
		assert(response.response_data() is None)
		assert(response.__pushed_responses__() == tuple())


class TestWWebRequestProto:

	class Request(WWebRequestProto):
		def session(self):
			pass

		def method(self):
			return 'GET'

		def path(self):
			return '/foo/bar?test_var=value?&test_var=&foo=%02/bar#/zzz?'

		def headers(self):
			headers = WHTTPHeaders()
			headers.add_headers('Host', 'foo.bar:8080')
			headers.add_headers('Content-type', 'application/x-www-form-urlencoded')
			return headers

	def test_request(self):

		request = TestWWebRequestProto.Request()
		assert(request.request_data() is None)
		assert(request.virtual_host() == 'foo.bar:8080')
		assert(request.content_type() == 'application/x-www-form-urlencoded')

		get_vars = request.get_vars()
		assert(get_vars['foo'] == ['\x02/bar'])
		get_vars = get_vars['test_var']
		get_vars.sort()
		assert(get_vars == ['', 'value?'])
		request.method = lambda: 'POST'
		pytest.raises(RuntimeError, request.get_vars)

		request.request_data = lambda: b'test_var=post_value?&test_var=&zzz=/xxx%01#/zzz?'
		post_vars = request.post_vars()
		assert(post_vars['zzz'] == ['/xxx\x01'])
		post_vars = post_vars['test_var']
		post_vars.sort()
		post_vars.sort()
		assert(post_vars == ['', 'post_value?'])

		request.method = lambda: 'GET'
		pytest.raises(RuntimeError, request.post_vars)
		request.method = lambda: 'POST'
		request.headers = lambda: None
		pytest.raises(RuntimeError, request.post_vars)


class TestWWebPresenter:

	class Presenter(WWebPresenter):

		@classmethod
		def __presenter_name__(cls):
			return 'preseter name'

	def test_presenter(self):
		request = TestWWebRequestProto.Request()
		presenter = TestWWebPresenter.Presenter(request)

		assert(isinstance(presenter, WWebPresenter) is True)
		assert(presenter.__request__() == request)


class TestWWebTargetRouteProto:

	class DummyPresenter:

		zzz = '!'

		def __init__(self, request):
			pass

		def foo(self, a, b=5):
			return a * b

		def _bar(self):
			return 1

	class Route(WWebTargetRouteProto):

		def route_map(self):
			return None

		def presenter_name(self):
			return 'test presenter'

		def presenter_action(self):
			return 'foo'

	def test_route(self):
		route = TestWWebTargetRouteProto.Route()
		assert(route.presenter_args() == {})


class TestWWebRouteMapProto:

	class RouteMap(WWebRouteMapProto):

		def route(self, request):
			pass

		def error_presenter(self):
			pass

	def test_route(self):
		route_map = TestWWebRouteMapProto.RouteMap()

		target_route = TestWWebTargetRouteProto.Route()
		assert(target_route.presenter_action() == 'foo')
		assert(route_map.target_route_valid(target_route) is True)
		target_route.presenter_action = lambda: '_bar'
		assert(route_map.target_route_valid(target_route) is False)
