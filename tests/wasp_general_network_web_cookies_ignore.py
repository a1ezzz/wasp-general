# -*- coding: utf-8 -*-

import pytest

from http.cookies import SimpleCookie

from wasp_general.network.web.cookies import WHTTPCookie, WHTTPCookieJar


class TestWHTTPCookies:

	def test_cookie(self):
		cookie = WHTTPCookie('cookie1', 'value1', path='/---')
		assert(isinstance(cookie, WHTTPCookie) is True)
		assert(cookie.name() == 'cookie1')
		assert(cookie.value() == 'value1')
		assert(cookie.value('value2') == 'value2')
		assert(cookie.attr('path') == '/---')
		assert(cookie.attr('path', '/!!!') == '/!!!')
		assert(cookie.attrs_as_dict() == {'path': '/!!!'})
		pytest.raises(ValueError, cookie.attr, 'path', ';;;')

		assert(str(cookie) == 'Set-Cookie: cookie1=value2; Path=/!!!')

		copy_cookie = cookie.copy()
		assert(str(copy_cookie) == 'Set-Cookie: cookie1=value2; Path=/!!!')
		copy_cookie.remove_attr('path')
		assert(str(copy_cookie) == 'Set-Cookie: cookie1=value2')

		ro_cookie = cookie.ro()
		assert(str(ro_cookie) == 'Set-Cookie: cookie1=value2; Path=/!!!')
		pytest.raises(RuntimeError, ro_cookie.value, 'zzz')
		pytest.raises(RuntimeError, ro_cookie.attr, 'path', '/zzz')
		pytest.raises(RuntimeError, ro_cookie.remove_attr, 'path')

		cookie = WHTTPCookie('cookie2', 'value0', max_age='1/1/1')
		assert(str(cookie) == 'Set-Cookie: cookie2=value0; Max-Age=1/1/1')
		cookie.attr('max-age', '2/2/2')
		assert(str(cookie) == 'Set-Cookie: cookie2=value0; Max-Age=2/2/2')
		pytest.raises(ValueError, cookie.attr, 'ZZZZ', '3/3/3')


class TestWHTTPCookieJar:

	def test_cookie_jar(self):
		cookie_jar = WHTTPCookieJar()
		assert(isinstance(cookie_jar, WHTTPCookieJar) is True)
		assert(cookie_jar.cookies() == tuple())

		cookie = WHTTPCookie('cookie1', 'value1')
		cookie_jar.add_cookie(cookie)
		assert(cookie_jar.cookies() == ('cookie1',))
		assert(cookie_jar['cookie1'] == cookie)
		assert(cookie_jar['cookie1'].value() == 'value1')
		cookie.value('value2')
		assert(cookie_jar['cookie1'].value() == 'value2')
		assert([x for x in cookie_jar] == [cookie])

		ro_cookie_jar = cookie_jar.ro()
		pytest.raises(RuntimeError, ro_cookie_jar.remove_cookie, 'cookie1')
		pytest.raises(RuntimeError, ro_cookie_jar.add_cookie, WHTTPCookie('cookie2', 'value2'))
		pytest.raises(RuntimeError, ro_cookie_jar['cookie1'].value, 'value3')

		cookie_jar.remove_cookie('cookie1')
		assert(cookie_jar.cookies() == tuple())

	def test_import_simple_cookie(self):
		simple_cookie = SimpleCookie()
		simple_cookie['cookie1'] = 'value1'
		simple_cookie['cookie1']['path'] = '/'
		simple_cookie['cookie2'] = 'value2'
		simple_cookie['cookie2']['domain'] = 'foo.bar'

		cookie_jar = WHTTPCookieJar.import_simple_cookie(simple_cookie)
		cookies = list(cookie_jar.cookies())
		cookies.sort()
		assert(cookies == ['cookie1', 'cookie2'])
		assert(cookie_jar['cookie1'].value() == 'value1')
		assert(cookie_jar['cookie2'].value() == 'value2')
		assert(str(cookie_jar['cookie1']) == 'Set-Cookie: cookie1=value1; Path=/')
		assert(str(cookie_jar['cookie2']) == 'Set-Cookie: cookie2=value2; Domain=foo.bar')

	def test_import_header_text(self):
		http_code = 'Set-Cookie: cookie1=value1; Path=/;, cookie2=value2; Domain=foo.bar\r\n'

		cookie_jar = WHTTPCookieJar.import_header_text(http_code)
		cookies = list(cookie_jar.cookies())
		cookies.sort()
		assert(cookies == ['cookie1', 'cookie2'])
		assert(cookie_jar['cookie1'].value() == 'value1')
		assert(cookie_jar['cookie2'].value() == 'value2')
		assert(str(cookie_jar['cookie1']) == 'Set-Cookie: cookie1=value1; Path=/')
		assert(str(cookie_jar['cookie2']) == 'Set-Cookie: cookie2=value2; Domain=foo.bar')
