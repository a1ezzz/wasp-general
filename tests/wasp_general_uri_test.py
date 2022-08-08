# -*- coding: utf-8 -*-

import pytest

from wasp_general.uri import WURI, WURIQuery, WStrictURIQuery, WURIComponentVerifier, WURIQueryVerifier
from wasp_general.uri import WSchemeSpecification, WSchemeHandler, WSchemeCollection


def test_abstract():
	pytest.raises(TypeError, WSchemeHandler)
	pytest.raises(NotImplementedError, WSchemeHandler.create_handler, WURI())
	pytest.raises(NotImplementedError, WSchemeHandler.scheme_specification)


class TestWURI:

	def test(self):
		assert(isinstance(WURI.__all_components__, set) is True)
		assert(len(WURI.__all_components__) == len(WURI.Component))
		for c in WURI.Component:
			assert(c.value in WURI.__all_components__)

		uri = WURI()
		assert(isinstance(uri, WURI) is True)

		assert(uri.scheme() is None)
		assert(uri.username() is None)
		assert(uri.password() is None)
		assert(uri.hostname() is None)
		assert(uri.port() is None)
		assert(uri.path() is None)
		assert(uri.query() is None)
		assert(uri.fragment() is None)
		assert(str(uri) == '')
		assert(
			[x for x in uri] == [
				(WURI.Component.scheme, None),
				(WURI.Component.username, None),
				(WURI.Component.password, None),
				(WURI.Component.hostname, None),
				(WURI.Component.port, None),
				(WURI.Component.path, None),
				(WURI.Component.query, None),
				(WURI.Component.fragment, None)
			]
		)

		uri = WURI.parse(str(uri))
		assert(uri.scheme() is None)
		assert(uri.username() is None)
		assert(uri.password() is None)
		assert(uri.hostname() is None)
		assert(uri.port() is None)
		assert(uri.path() is None)
		assert(uri.query() is None)
		assert(uri.fragment() is None)

		uri = WURI(scheme='proto', hostname='host1', path='/foo')

		assert(uri.scheme() == 'proto')
		assert(uri.username() is None)
		assert(uri.password() is None)
		assert(uri.hostname() == 'host1')
		assert(uri.port() is None)
		assert(uri.path() == '/foo')
		assert(uri.query() is None)
		assert(uri.fragment() is None)
		assert(str(uri) == 'proto://host1/foo')
		assert(
			[x for x in uri] == [
				(WURI.Component.scheme, 'proto'),
				(WURI.Component.username, None),
				(WURI.Component.password, None),
				(WURI.Component.hostname, 'host1'),
				(WURI.Component.port, None),
				(WURI.Component.path, '/foo'),
				(WURI.Component.query, None),
				(WURI.Component.fragment, None)
			]
		)

		uri = WURI.parse(str(uri))
		assert(uri.scheme() == 'proto')
		assert(uri.username() is None)
		assert(uri.password() is None)
		assert(uri.hostname() == 'host1')
		assert(uri.port() is None)
		assert(uri.path() == '/foo')
		assert(uri.query() is None)
		assert(uri.fragment() is None)

		uri = WURI(
			scheme='proto', username='local_user', password='secret', hostname='host1', port=40,
			path='/foo', query='q=10;p=2', fragment='section1'
		)

		assert(uri.scheme() == 'proto')
		assert(uri.username() == 'local_user')
		assert(uri.password() == 'secret')
		assert(uri.hostname() == 'host1')
		assert(uri.port() == 40)
		assert(uri.path() == '/foo')
		assert(uri.query() == 'q=10;p=2')
		assert(uri.fragment() == 'section1')
		assert(str(uri) == 'proto://local_user:secret@host1:40/foo?q=10;p=2#section1')
		assert(
			[x for x in uri] == [
				(WURI.Component.scheme, 'proto'),
				(WURI.Component.username, 'local_user'),
				(WURI.Component.password, 'secret'),
				(WURI.Component.hostname, 'host1'),
				(WURI.Component.port, 40),
				(WURI.Component.path, '/foo'),
				(WURI.Component.query, 'q=10;p=2'),
				(WURI.Component.fragment, 'section1')
			]
		)

		uri = WURI.parse(str(uri))
		assert(uri.scheme() == 'proto')
		assert(uri.username() == 'local_user')
		assert(uri.password() == 'secret')
		assert(uri.hostname() == 'host1')
		assert(uri.port() == 40)
		assert(uri.path() == '/foo')
		assert(uri.query() == 'q=10;p=2')
		assert(uri.fragment() == 'section1')

		uri = WURI(scheme='proto', path='/foo')
		assert(str(uri) == 'proto:///foo')

		uri = WURI.parse(str(uri))
		assert(uri.scheme() == 'proto')
		assert(uri.username() is None)
		assert(uri.password() is None)
		assert(uri.hostname() is None)
		assert(uri.port() is None)
		assert(uri.path() == '/foo')
		assert(uri.query() is None)
		assert(uri.fragment() is None)

		with pytest.raises(AttributeError):
			v = uri.zzz  # noqa: F841

		uri.reset_component('path')
		uri.reset_component(WURI.Component.scheme)
		assert(uri.scheme() is None)
		assert(uri.username() is None)
		assert(uri.password() is None)
		assert(uri.hostname() is None)
		assert(uri.port() is None)
		assert(uri.path() is None)
		assert(uri.query() is None)
		assert(uri.fragment() is None)

		pytest.raises(ValueError, uri.component, WURI.Component.port, '80')
		pytest.raises(ValueError, uri.component, WURI.Component.hostname, 80)
		uri.component(WURI.Component.port, 80)
		assert(uri.port() == 80)


class TestWURIQuery:

	def test(self):
		query = WURIQuery()
		assert(str(query) == '')
		assert(list(query) == [])
		assert(('foo' in query) is False)
		assert(('aaa' in query) is False)

		query = WURIQuery.parse('foo=bar&zzz=bar')
		assert(str(query) in ('foo=bar&zzz=bar', 'zzz=bar&foo=bar'))
		assert(list(query) in (['foo', 'zzz'], ['zzz', 'foo']))
		assert(('foo' in query) is True)
		assert(('aaa' in query) is False)

		query.add_parameter('aaa')
		assert(('aaa' in query) is True)
		query.remove_parameter('foo')
		assert(('foo' in query) is False)
		assert(str(query) in ('aaa=&zzz=bar', 'zzz=bar&aaa='))

		query.replace_parameter('zzz')
		query.replace_parameter('aaa', '123')
		assert(str(query) in ('aaa=123&zzz=', 'zzz=&aaa=123'))

		query = WURIQuery.parse('foo=bar&foo=&zzz=123')
		assert(query['foo'] in (('bar', None), (None, 'bar')))
		assert(query['zzz'] == ('123', ))

		query.add_parameter('foo', 'nnn')
		r = query['foo']
		assert(len(r) == 3)
		assert('bar' in r)
		assert('nnn' in r)
		assert(None in r)

		params = {x: y for x, y in query.parameters()}
		assert(len(params) == 2)
		assert('foo' in params)
		assert(len(params['foo']) == 3)
		assert('bar' in params['foo'])
		assert('nnn' in params['foo'])
		assert(None in params['foo'])
		assert('zzz' in params)
		assert(params['zzz'] == ['123'])

		query = WURIQuery.parse('')
		assert({x: y for x, y in query.parameters()} == {})


class TestWStrictURIQuery:

	def test_parameter_specification(self):
		spec = WStrictURIQuery.ParameterSpecification('foo')
		assert(spec.name() == 'foo')
		assert(spec.nullable() is True)
		assert(spec.multiple() is True)
		assert(spec.optional() is False)
		assert(spec.re_obj() is None)

		spec = WStrictURIQuery.ParameterSpecification(
			'foo', nullable=False, multiple=False, optional=True, reg_exp=r'^\d+$'
		)
		assert(spec.nullable() is False)
		assert(spec.multiple() is False)
		assert(spec.optional() is True)
		assert(spec.re_obj() is not None)

	def test(self):
		base_query = WURIQuery()
		query = WStrictURIQuery(base_query)
		assert(isinstance(query, WURIQuery) is True)
		assert(query.extra_parameters() is True)
		query.add_parameter('foo')

		query = WStrictURIQuery.strict_parse('foo=zzz')
		assert(isinstance(query, WStrictURIQuery) is True)

		required_foo = WStrictURIQuery.ParameterSpecification('foo')
		pytest.raises(ValueError, WStrictURIQuery, base_query, required_foo)

		optional_foo = WStrictURIQuery.ParameterSpecification('foo', optional=True, nullable=False)
		query = WStrictURIQuery(base_query, optional_foo, extra_parameters=False)
		assert(query.extra_parameters() is False)
		pytest.raises(ValueError, query.add_parameter, 'bar')
		pytest.raises(ValueError, query.replace_parameter, 'bar')
		pytest.raises(ValueError, query.add_parameter, 'foo')
		query.add_parameter('foo', 'zzz')
		pytest.raises(ValueError, query.replace_parameter, 'foo')
		query.replace_parameter('foo', '123')
		assert(str(query) == 'foo=123')

		query = WStrictURIQuery.strict_parse('foo=zzz&bar=&bar=111', required_foo)
		pytest.raises(ValueError, query.remove_parameter, 'foo')
		query.remove_parameter('bar')
		assert(str(query) == 'foo=zzz')
		query.remove_specification('foo')
		query.remove_parameter('foo')
		assert (str(query) == '')

		single_bar = WStrictURIQuery.ParameterSpecification('bar', multiple=False)
		query = WStrictURIQuery.strict_parse('foo=zzz&bar=', required_foo, single_bar)
		pytest.raises(ValueError, query.add_parameter, 'bar')
		pytest.raises(ValueError, query.add_specification, WStrictURIQuery.ParameterSpecification('bar'))
		query.replace_specification(WStrictURIQuery.ParameterSpecification('bar'))
		query.add_parameter('bar')

		optional_bar = WStrictURIQuery.ParameterSpecification('bar', optional=True, reg_exp='^zxc|123$')
		query = WStrictURIQuery.strict_parse('bar=', optional_bar)
		query.replace_parameter('bar', '123')
		pytest.raises(ValueError, query.replace_parameter, 'bar', 'zzz')
		pytest.raises(ValueError, query.add_parameter, 'bar', 'zzz')
		query.add_parameter('bar')


class TestWURIComponentVerifier:

	def test(self):
		component_verifier = WURIComponentVerifier(
			WURI.Component.hostname, WURIComponentVerifier.Requirement.required
		)
		assert(component_verifier.requirement() == WURIComponentVerifier.Requirement.required)
		assert(component_verifier.re_obj() is None)
		assert(component_verifier.component() == WURI.Component.hostname)

		assert(component_verifier.validate(WURI.parse('scheme://hostname')) is True)
		assert(component_verifier.validate(WURI.parse('scheme:///path?query=')) is False)

		component_verifier = WURIComponentVerifier(
			WURI.Component.hostname, WURIComponentVerifier.Requirement.unsupported
		)
		assert(component_verifier.validate(WURI.parse('scheme://hostname')) is False)

		component_verifier = WURIComponentVerifier(
			WURI.Component.hostname, WURIComponentVerifier.Requirement.required, '^host-[0-9]+$'
		)
		assert(component_verifier.validate(WURI.parse('scheme://hostname')) is False)
		assert(component_verifier.validate(WURI.parse('scheme://host-5')) is True)

		component_verifier = WURIComponentVerifier(
			WURI.Component.hostname, WURIComponentVerifier.Requirement.optional, '^host-[0-9]+$'
		)
		assert(component_verifier.validate(WURI.parse('scheme://hostname')) is False)
		assert(component_verifier.validate(WURI.parse('scheme://host-5')) is True)
		assert(component_verifier.validate(WURI.parse('scheme:///path?query=')) is True)


class TestWURIQueryVerifier:

	def test(self):
		optional_foo = WStrictURIQuery.ParameterSpecification('foo', optional=True, reg_exp='zzz|123')
		required_bar = WStrictURIQuery.ParameterSpecification('bar', nullable=False)

		verifier = WURIQueryVerifier(
			WURIComponentVerifier.Requirement.required, optional_foo, required_bar
		)
		assert(isinstance(verifier, WURIComponentVerifier) is True)
		assert(verifier.validate(WURI.parse('scheme:///')) is False)
		assert(verifier.validate(WURI.parse('scheme:///?bar=0')) is True)
		assert(verifier.validate(WURI.parse('scheme:///?bar=')) is False)
		assert(verifier.validate(WURI.parse('scheme:///?foo=&bar=1')) is True)
		assert(verifier.validate(WURI.parse('scheme:///?foo=123&bar=1')) is True)
		assert(verifier.validate(WURI.parse('scheme:///?foo=zxc&bar=1')) is False)

		verifier = WURIQueryVerifier(
			WURIComponentVerifier.Requirement.optional, optional_foo, required_bar
		)
		assert(verifier.validate(WURI.parse('scheme:///')) is True)
		assert(verifier.validate(WURI.parse('scheme:///?bar=0')) is True)
		assert(verifier.validate(WURI.parse('scheme:///?bar=')) is False)
		assert(verifier.validate(WURI.parse('scheme:///?foo=&bar=1')) is True)
		assert(verifier.validate(WURI.parse('scheme:///?foo=123&bar=1')) is True)
		assert(verifier.validate(WURI.parse('scheme:///?foo=zxc&bar=1')) is False)


class TestWSchemeSpecification:

	def test(self):
		scheme_spec = WSchemeSpecification('proto')
		assert(isinstance(scheme_spec, WSchemeSpecification) is True)
		assert(scheme_spec.scheme_name() == 'proto')

		assert(
			[scheme_spec.verifier(x).requirement() for x in WURI.Component] == [
				WURIComponentVerifier.Requirement.required,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported
			]
		)

		assert(
			[(x[0], x[1].requirement()) for x in scheme_spec] == [
				(WURI.Component.scheme, WURIComponentVerifier.Requirement.required),
				(WURI.Component.username, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.password, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.hostname, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.port, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.path, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.query, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.fragment, WURIComponentVerifier.Requirement.unsupported)
			]
		)

		assert(scheme_spec.is_compatible(WURI.parse('proto:')) is True)
		assert(scheme_spec.is_compatible(WURI.parse('proto://host')) is False)

		scheme_spec = WSchemeSpecification(
			'proto',
			WURIComponentVerifier(WURI.Component.hostname, WURIComponentVerifier.Requirement.required),
			WURIComponentVerifier(WURI.Component.port, WURIComponentVerifier.Requirement.optional)
		)

		assert(
			[scheme_spec.verifier(x).requirement() for x in WURI.Component] == [
				WURIComponentVerifier.Requirement.required,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.required,
				WURIComponentVerifier.Requirement.optional,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported,
				WURIComponentVerifier.Requirement.unsupported
			]
		)

		assert(
			[(x[0], x[1].requirement()) for x in scheme_spec] == [
				(WURI.Component.scheme, WURIComponentVerifier.Requirement.required),
				(WURI.Component.username, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.password, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.hostname, WURIComponentVerifier.Requirement.required),
				(WURI.Component.port, WURIComponentVerifier.Requirement.optional),
				(WURI.Component.path, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.query, WURIComponentVerifier.Requirement.unsupported),
				(WURI.Component.fragment, WURIComponentVerifier.Requirement.unsupported)
			]
		)

		assert(scheme_spec.is_compatible(WURI.parse('proto:')) is False)
		assert(scheme_spec.is_compatible(WURI.parse('proto://host')) is True)
		assert(scheme_spec.is_compatible(WURI.parse('proto://host:30')) is True)
		assert(scheme_spec.is_compatible(WURI.parse('proto:///')) is False)

		pytest.raises(
			ValueError,
			WSchemeSpecification,
			'proto',
			WURIComponentVerifier(WURI.Component.scheme, WURIComponentVerifier.Requirement.required)
		)

		pytest.raises(
			ValueError,
			WSchemeSpecification,
			'proto',
			WURIComponentVerifier(WURI.Component.hostname, WURIComponentVerifier.Requirement.required),
			WURIComponentVerifier(WURI.Component.hostname, WURIComponentVerifier.Requirement.required)
		)

		pytest.raises(TypeError, WSchemeSpecification, 'proto', hostname='optional')


class TestWSchemeCollection:

	# noinspection PyAbstractClass
	class Handler(WSchemeHandler):

		def __init__(self, uri):
			WSchemeHandler.__init__(self)
			self.uri = uri

		@classmethod
		def create_handler(cls, uri, **kwargs):
			return cls(uri)

	class HandlerFoo(Handler):

		@classmethod
		def scheme_specification(cls):
			return WSchemeSpecification(
				'foo',
				WURIComponentVerifier(WURI.Component.path, WURIComponentVerifier.Requirement.required)
			)

	class HandlerBar(Handler):

		@classmethod
		def scheme_specification(cls):
			return WSchemeSpecification(
				'bar',
				WURIComponentVerifier(WURI.Component.path, WURIComponentVerifier.Requirement.required),
				WURIComponentVerifier(WURI.Component.query, WURIComponentVerifier.Requirement.optional)
			)

	def test_exceptions(self):
		e = WSchemeCollection.NoHandlerFound(WURI())
		assert(isinstance(e, WSchemeCollection.NoHandlerFound) is True)
		assert(isinstance(e, Exception) is True)

		e = WSchemeCollection.SchemeIncompatible(WURI())
		assert(isinstance(e, WSchemeCollection.SchemeIncompatible) is True)
		assert(isinstance(e, Exception) is True)

	def test(self):
		uri1 = WURI.parse('/path')
		uri2 = WURI.parse('foo:///path')
		uri3 = WURI.parse('bar:///path')
		uri4 = WURI.parse('bar:///path?test=foo')
		uri5 = WURI.parse('foo:///path?test=foo')

		collection = WSchemeCollection()
		assert(isinstance(collection, WSchemeCollection) is True)
		assert(collection.handler() is None)
		assert(collection.handler(scheme_name='foo') is None)
		assert(collection.handler(scheme_name='bar') is None)

		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, uri1)
		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, uri2)
		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, uri3)
		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, uri4)
		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, uri5)

		collection = WSchemeCollection(
			TestWSchemeCollection.HandlerFoo, default_handler_cls=TestWSchemeCollection.HandlerBar
		)
		assert(isinstance(collection, WSchemeCollection) is True)
		assert(collection.handler() == TestWSchemeCollection.HandlerBar)
		assert(collection.handler(scheme_name='foo') == TestWSchemeCollection.HandlerFoo)
		assert(collection.handler(scheme_name='bar') is None)

		assert(isinstance(collection.open(uri1), TestWSchemeCollection.HandlerBar) is True)
		assert(isinstance(collection.open(uri2), TestWSchemeCollection.HandlerFoo) is True)
		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, uri3)
		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, uri4)
		pytest.raises(WSchemeCollection.SchemeIncompatible, collection.open, uri5)

		assert(isinstance(collection.open('/path'), TestWSchemeCollection.HandlerBar) is True)
		assert(isinstance(collection.open('foo:///path'), TestWSchemeCollection.HandlerFoo) is True)
		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, 'bar:///path')
		pytest.raises(WSchemeCollection.NoHandlerFound, collection.open, 'bar:///path?test=foo')
		pytest.raises(WSchemeCollection.SchemeIncompatible, collection.open, 'foo:///path?test=foo')

		collection.add(TestWSchemeCollection.HandlerBar)
		assert(isinstance(collection.open(uri1), TestWSchemeCollection.HandlerBar) is True)
		assert(isinstance(collection.open(uri2), TestWSchemeCollection.HandlerFoo) is True)
		assert(isinstance(collection.open(uri3), TestWSchemeCollection.HandlerBar) is True)
		assert(isinstance(collection.open(uri4), TestWSchemeCollection.HandlerBar) is True)
		pytest.raises(WSchemeCollection.SchemeIncompatible, collection.open, uri5)
