
import pytest

from wasp_general.api.uri import WURIRestriction, WURIQueryRestriction, WURIAPIRegistry, register_scheme_handler
from wasp_general.api.check import WArgsRestrictionError, WArgsValueRestriction, WChainChecker, WArgsRequirements
from wasp_general.api.registry import WAPIRegistry, WNoSuchAPIIdError
from wasp_general.uri import WURI, WURIQuery


class TestWURIRestriction:

	def test(self):
		restriction = WChainChecker()
		uri_restriction = WURIRestriction(restriction)
		assert(isinstance(uri_restriction, WURIRestriction) is True)
		assert(isinstance(uri_restriction, WArgsValueRestriction) is True)

		uri = WURI.parse('protocol://hostname1:1111/?foo=bar')
		uri_restriction.check(uri=uri)

		uri_restriction = WURIRestriction(restriction, 'uri')
		uri_restriction.check(uri=uri)

		uri_restriction = WURIRestriction(
			WArgsRequirements(WURI.Component.hostname.value),
			'uri'
		)
		uri_restriction.check()
		uri_restriction.check(uri=uri)
		pytest.raises(WArgsRestrictionError, uri_restriction.check, uri=WURI.parse('scheme:///path'))

		uri_restriction.check_value('//host/')
		pytest.raises(WArgsRestrictionError, uri_restriction.check_value, 'scheme:///path')


class TestWURIQueryRestriction:

	def test(self):
		uri_query_restriction = WURIQueryRestriction()
		assert(isinstance(uri_query_restriction, WURIQueryRestriction) is True)
		assert(isinstance(uri_query_restriction, WArgsValueRestriction) is True)

		uri_query_restriction = WURIQueryRestriction(WArgsRequirements('foo'))
		uri_query_restriction.check()
		uri_query_restriction.check(query=WURIQuery.parse('foo=bar'))
		pytest.raises(WArgsRestrictionError, uri_query_restriction.check, query=WURIQuery.parse(''))

		uri_query_restriction.check_value(WURIQuery.parse('foo=bar'))
		pytest.raises(WArgsRestrictionError, uri_query_restriction.check_value, WURIQuery.parse(''))

	def test_uri(self):
		uri_restriction = WURIRestriction(WURIQueryRestriction(WArgsRequirements('foo')))
		uri_restriction.check()
		uri_restriction.check('///')
		uri_restriction.check('///?')
		uri_restriction.check(WURI.parse('///?foo=bar&zzz=1'))
		pytest.raises(WArgsRestrictionError, uri_restriction.check, WURI.parse('///?zzz=1'))


class TestWURIAPIRegistry:

	def test(self):
		registry = WURIAPIRegistry()
		assert(isinstance(registry, WURIAPIRegistry) is True)
		assert(isinstance(registry, WAPIRegistry) is True)

		pytest.raises(WNoSuchAPIIdError, registry.open, '///')
		pytest.raises(WNoSuchAPIIdError, registry.open, 'protocol:///')
		pytest.raises(WNoSuchAPIIdError, registry.open, 'foo///')

		protocol_descriptor = object()
		registry.register('protocol', protocol_descriptor)
		pytest.raises(WNoSuchAPIIdError, registry.open, '///')
		assert(registry.open('protocol:///') is protocol_descriptor)
		pytest.raises(WNoSuchAPIIdError, registry.open, 'foo///')

		foo_descriptor = object()
		registry.register('foo', foo_descriptor)
		pytest.raises(WNoSuchAPIIdError, registry.open, '///')
		assert(registry.open('protocol:///') is protocol_descriptor)
		assert(registry.open('foo:///') is foo_descriptor)


def test_register_scheme_handler():

	def foo(a, b):
		return a + b

	def bar(a, b):
		return a - b

	registry = WURIAPIRegistry()
	pytest.raises(TypeError, register_scheme_handler, registry)
	register_scheme_handler(registry, 'foo')(foo)
	register_scheme_handler(registry, 'bar')(bar)

	assert(registry.open('foo://')(2, 3) == 5)
	assert(registry.open('bar://')(2, 3) == -1)
