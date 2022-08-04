
import pytest

from wasp_general.api.uri import WURIRestriction, WURIQueryRestriction
from wasp_general.api.check import WArgsRestrictionError, WArgsValueRestriction, WChainChecker, WArgsRequirements
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
