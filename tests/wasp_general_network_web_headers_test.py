# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.web.cookies import WHTTPCookie
from wasp_general.network.web.headers import WHTTPHeaders


class TestWHTTPHeaders:

	def test_headers(self):
		headers1 = WHTTPHeaders()
		assert(isinstance(headers1, WHTTPHeaders) is True)

		headers2 = WHTTPHeaders(header1='value1', **{'header-2': 'value-2'})
		assert(isinstance(headers2, WHTTPHeaders) is True)

		assert(headers1.headers() == tuple())
		headers_list = list(headers2.headers())
		headers_list.sort()
		assert(tuple(headers_list) == ('Header-2', 'Header1'))
		headers2 = headers2.switch_name_style('2')
		headers2.set_cookie_jar().add_cookie(WHTTPCookie('cookie', 'value'))
		headers_list = list(headers2.headers())
		headers_list.sort()
		assert(tuple(headers_list) == ('header-2', 'header1'))
		headers2 = headers2.switch_name_style('1.1')
		headers_list = list(headers2.headers())
		headers_list.sort()
		assert(tuple(headers_list) == ('Header-2', 'Header1'))
		headers2._WHTTPHeaders__normalization_mode = '3'
		pytest.raises(RuntimeError, headers2.normalize_name, 'header')
		headers2._WHTTPHeaders__normalization_mode = '1.1'

		headers1.add_headers('Header-Foo', 'bar')
		assert(headers1['header-foo'] == ('bar',))
		assert(headers1.get_headers('HeadEr-fOO') == ('bar',))
		headers1.add_headers('Header-Foo', 'zzz', 'yyy')
		assert(headers1['header-foo'] == ('bar', 'zzz', 'yyy'))
		headers1.replace_headers('header-foo', 'xxx', 'ccc')
		assert(headers1['header-foo'] == ('xxx', 'ccc'))
		headers1.remove_headers('header-Foo')
		assert(headers1.headers() == tuple())

		ro_headers = headers2.ro()
		assert(isinstance(ro_headers, WHTTPHeaders) is True)
		assert(ro_headers['header1'] == ('value1',))
		pytest.raises(RuntimeError, ro_headers.add_headers, 'header', 'value')
		pytest.raises(RuntimeError, ro_headers.remove_headers, 'header')
		pytest.raises(RuntimeError, ro_headers.replace_headers, 'header', '!')

		headers1.add_headers('content-type', 'foo/bar', 'text/plain')
		assert(headers1['content-type'] == ('foo/bar', 'text/plain'))
		assert(headers1.content_type() == 'foo/bar')
		assert(headers1.content_type('zzz') == 'zzz')
		assert(headers1.content_type() == 'zzz')

		headers1.add_headers('Cookie', 'client_cookie=val1; Path=/')
		assert(headers1.client_cookie_jar().cookies() == ('client_cookie',))
		assert(headers1.client_cookie_jar()['client_cookie'].value() == 'val1')
		assert(headers1.client_cookie_jar()['client_cookie'].attr('path') == '/')
		pytest.raises(RuntimeError, headers1.client_cookie_jar().remove_cookie, 'client_cookie')
		pytest.raises(RuntimeError, headers1.client_cookie_jar()['client_cookie'].value, 'aaa')

	def test_import(self):
		http_code = 'Header1: value1\r\n'
		http_code += 'Header-Foo: bar\r\n'
		http_code += 'Set-Cookie: cookie1=cookie_value1; Path=/\r\n'
		http_code += 'Cookie: cookie2=value2; Domain=zzz\r\n'

		headers = WHTTPHeaders.import_headers(http_code)
		assert(headers['Header1'] == ('value1',))
		assert(headers['Header-Foo'] == ('bar',))
		assert(headers.set_cookie_jar()['cookie1'].value() == 'cookie_value1')
		assert(headers.set_cookie_jar()['cookie1'].attr('Path') == '/')
		assert(headers.client_cookie_jar()['cookie2'].value() == 'value2')
		assert(headers.client_cookie_jar()['cookie2'].attr('Domain') == 'zzz')
