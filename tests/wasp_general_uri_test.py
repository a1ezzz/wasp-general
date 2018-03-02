# -*- coding: utf-8 -*-

import pytest

from wasp_general.uri import WURI, WSchemeSpecification, WSchemeHandler, WSchemeCollection


def test_abstract():
	pytest.raises(TypeError, WSchemeHandler)
	pytest.raises(NotImplementedError, WSchemeHandler.create_handler, WURI())
	pytest.raises(NotImplementedError, WSchemeHandler.scheme_specification)


class TestWURI:

	def test(self):
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

		pytest.raises(AttributeError, "uri.zzz")


class TestWSchemeSpecification:

	def test(self):
		scheme_spec = WSchemeSpecification('proto')
		assert(isinstance(scheme_spec, WSchemeSpecification) is True)
		assert(scheme_spec.scheme_name() == 'proto')

		assert(
			[scheme_spec.descriptor(x) for x in WURI.Component] == [
				WSchemeSpecification.ComponentDescriptor.required,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported
			]
		)

		assert(
			[x for x in scheme_spec] == [
				(WURI.Component.scheme, WSchemeSpecification.ComponentDescriptor.required),
				(WURI.Component.username, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.password, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.hostname, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.port, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.path, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.query, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.fragment, WSchemeSpecification.ComponentDescriptor.unsupported)
			]
		)

		assert(scheme_spec.is_compatible(WURI.parse('proto:')) is True)
		assert(scheme_spec.is_compatible(WURI.parse('proto://host')) is False)

		scheme_spec = WSchemeSpecification(
			'proto',
			hostname=WSchemeSpecification.ComponentDescriptor.required,
			port=WSchemeSpecification.ComponentDescriptor.optional
		)

		assert(
			[scheme_spec.descriptor(x) for x in WURI.Component] == [
				WSchemeSpecification.ComponentDescriptor.required,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.required,
				WSchemeSpecification.ComponentDescriptor.optional,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported,
				WSchemeSpecification.ComponentDescriptor.unsupported
			]
		)

		assert(
			[x for x in scheme_spec] == [
				(WURI.Component.scheme, WSchemeSpecification.ComponentDescriptor.required),
				(WURI.Component.username, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.password, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.hostname, WSchemeSpecification.ComponentDescriptor.required),
				(WURI.Component.port, WSchemeSpecification.ComponentDescriptor.optional),
				(WURI.Component.path, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.query, WSchemeSpecification.ComponentDescriptor.unsupported),
				(WURI.Component.fragment, WSchemeSpecification.ComponentDescriptor.unsupported)
			]
		)

		assert(scheme_spec.is_compatible(WURI.parse('proto:')) is False)
		assert(scheme_spec.is_compatible(WURI.parse('proto://host')) is True)
		assert(scheme_spec.is_compatible(WURI.parse('proto://host:30')) is True)
		assert(scheme_spec.is_compatible(WURI.parse('proto:///')) is False)

		pytest.raises(
			TypeError, WSchemeSpecification,
			'proto', scheme=WSchemeSpecification.ComponentDescriptor.required
		)

		pytest.raises(TypeError, WSchemeSpecification, 'proto', hostname='optional')


class TestWSchemeCollection:

	# noinspection PyAbstractClass
	class Handler(WSchemeHandler):

		def __init__(self, uri):
			WSchemeHandler.__init__(self)
			self.uri = uri

		@classmethod
		def create_handler(cls, uri):
			return cls(uri)

	class HandlerFoo(Handler):

		@classmethod
		def scheme_specification(cls):
			return WSchemeSpecification('foo', path=WSchemeSpecification.ComponentDescriptor.required)

	class HandlerBar(Handler):

		@classmethod
		def scheme_specification(cls):
			return WSchemeSpecification(
				'bar',
				path=WSchemeSpecification.ComponentDescriptor.required,
				query=WSchemeSpecification.ComponentDescriptor.optional
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

		collection.add(TestWSchemeCollection.HandlerBar)
		assert(isinstance(collection.open(uri1), TestWSchemeCollection.HandlerBar) is True)
		assert(isinstance(collection.open(uri2), TestWSchemeCollection.HandlerFoo) is True)
		assert(isinstance(collection.open(uri3), TestWSchemeCollection.HandlerBar) is True)
		assert(isinstance(collection.open(uri4), TestWSchemeCollection.HandlerBar) is True)
		pytest.raises(WSchemeCollection.SchemeIncompatible, collection.open, uri5)
