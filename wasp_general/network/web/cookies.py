# -*- coding: utf-8 -*-
# wasp_general/network/web/cookies.py
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

from http.cookies import SimpleCookie
import re

from wasp_general.verify import verify_type, verify_value
from wasp_general.network.web.re_statements import http_path, http_cookie_expires, http_cookie_max_age
from wasp_general.network.web.re_statements import http_cookie_secure, http_cookie_httponly, http_cookie_domain


class WHTTPCookie:
	""" This class represent a single HTTP Cookie as it is described in RFC 6265.
	Call :meth:`.WHTTPCookie.ro` method to create unchangeable cookie copy
	"""

	cookie_name_non_compliance_re = re.compile(b'.*[\x00-\x1e\x7f()<>@,;:\\\\"/\[\]?={} \t].*')
	"""
	Check for non-acceptable cookie name

	see RFC 6265, Section 4.1.1
	"""

	cookie_value_non_compliance_re = re.compile(b'.*[\x00-\x1e\x7f \",;\\\].*')
	"""
	Check for non-acceptable cookie value

	see RFC 6265, Section 4.1.1
	"""

	cookie_attr_value_compliance = {
		'path': re.compile(http_path),
		'expires': re.compile(http_cookie_expires),
		'max-age': re.compile(http_cookie_max_age),
		'secure': re.compile(http_cookie_secure),
		'httponly': re.compile(http_cookie_httponly),
		'domain': re.compile(http_cookie_domain)
	}
	""" Dictionary of valid attribute names and appropriate values regexp
	"""

	@staticmethod
	def cookie_name_check(cookie_name):
		""" Check cookie name for validity. Return True if name is valid

		:param cookie_name: name to check
		:return: bool
		"""
		cookie_match = WHTTPCookie.cookie_name_non_compliance_re.match(cookie_name.encode('us-ascii'))
		return len(cookie_name) > 0 and cookie_match is None

	@staticmethod
	def cookie_value_check(cookie_value):
		""" Check cookie value for validity. Return True if value is valid

		:param cookie_value: value to check
		:return: bool
		"""
		return WHTTPCookie.cookie_value_non_compliance_re.match(cookie_value.encode('us-ascii')) is None

	@staticmethod
	def cookie_attr_value_check(attr_name, attr_value):
		""" Check cookie attribute value for validity. Return True if value is valid

		:param attr_name: attribute name to check
		:param attr_value: attribute value to check
		:return: bool
		"""
		attr_value.encode('us-ascii')
		return WHTTPCookie.cookie_attr_value_compliance[attr_name].match(attr_value) is not None

	@verify_type(name=str, value=str)
	@verify_value(name=lambda x: WHTTPCookie.cookie_name_check(x))
	@verify_value(value=lambda x: WHTTPCookie.cookie_value_check(x))
	def __init__(self, name, value, **attrs):
		""" Construct new cookie with defined name, value and attributes

		:param name: cookie name
		:param value: cookie value
		:param attrs: cookie attribute with its value. Attribute name must be in lowercase. In order to set
		'max-age' attribute, dash character ('-') may be replaced by underscore ('_') both variants are
		allowed
		"""
		self.__name = name
		self.__value = value
		self.__attrs = {}
		self.__ro_flag = False
		for attr_name in attrs:
			self.attr(attr_name, attrs[attr_name])

	def name(self):
		""" Return cookie name

		:return: str
		"""
		return self.__name

	@verify_type(name=str, new_value=(str, None))
	@verify_value(new_value=lambda x: x is None or WHTTPCookie.cookie_value_check(x))
	def value(self, new_value=None):
		""" Return cookie value. Cookie value can be updated, when new_value is not None. Cookie value
		couldn't be changed if cookie is in read-only mode (RuntimeError exception is raised).

		:param new_value: new value to set
		:return: str
		"""
		if new_value is not None:
			if self.__ro_flag:
				raise RuntimeError('Read-only cookie changing attempt')
			self.__value = new_value
		return self.__value

	def attrs_as_dict(self):
		""" Return cookie attributes as dictionary, where keys are attribute names and values are their
		values

		:return: dict
		"""
		return self.__attrs.copy()

	@verify_type(name=str)
	def __attr_name(self, name):
		""" Return suitable and valid attribute name. This method replaces dash char to underscore. If name
		is invalid ValueError exception is raised

		:param name: cookie attribute name
		:return: str
		"""
		if name not in self.cookie_attr_value_compliance.keys():
			suggested_name = name.replace('_', '-').lower()
			if suggested_name not in self.cookie_attr_value_compliance.keys():
				raise ValueError('Invalid attribute name is specified')
			name = suggested_name
		return name

	@verify_type('paranoid', attr_name=str)
	@verify_type(attr_value=(str, None))
	def attr(self, attr_name, attr_value=None):
		""" Return attribute value. Attribute value can be updated with this method. In order to update
		attribute value attr_value must be set. Cookie attribute value couldn't be changed if cookie is
		in read-only mode (RuntimeError exception is raised).

		:param attr_name: target attribute name
		:param attr_value: new value to set
		:return: str
		"""
		name = self.__attr_name(attr_name)
		if attr_value is not None:
			if WHTTPCookie.cookie_attr_value_check(name, attr_value) is not True:
				raise ValueError('Unacceptable value passed')
			if self.__ro_flag:
				raise RuntimeError('Read-only cookie changing attempt')
			self.__attrs[name] = attr_value
			return attr_value
		return self.__attrs[name]

	@verify_type('paranoid', attr_name=str)
	def remove_attr(self, attr_name):
		""" Remove cookie attribute. Cookie attribute couldn't be removed if cookie is in read-only mode
		(RuntimeError exception is raised).

		:param attr_name: name of attribute to remove
		:return: None
		"""
		if self.__ro_flag:
			raise RuntimeError('Read-only cookie changing attempt')
		name = self.__attr_name(attr_name)
		if name in self.__attrs.keys():
			self.__attrs.pop(attr_name)

	def __str__(self):
		""" Return valid "Set-Cookie" HTTP-header for this cookie

		:return: str
		"""
		simple_cookie = SimpleCookie()
		simple_cookie[self.__name] = self.__value
		for attr_name in self.__attrs.keys():
			simple_cookie[self.__name][attr_name] = self.__attrs[attr_name]
		return str(simple_cookie)

	def ro(self):
		""" Return read-only copy

		:return: WHTTPCookie
		"""
		ro_cookie = self.copy()
		ro_cookie.__ro_flag = True
		return ro_cookie

	def copy(self):
		""" Return copy

		:return: WHTTPCookie
		"""
		copy_cookie = WHTTPCookie(self.__name, self.__value)
		copy_cookie.__attrs = self.__attrs.copy()
		return copy_cookie


class WHTTPCookieJar:
	""" Class represent collection of cookies. Call :meth:`.WHTTPCookieJar.ro` method to create read-only copy
	(in this state no changes are allowed)
	"""

	def __init__(self):
		""" Construct new collection
		"""
		self.__cookies = {}
		self.__ro_flag = False

	def cookies(self):
		""" Return available cookie names

		:return: tuple of str
		"""
		return tuple(self.__cookies.keys())

	@verify_type(cookie=WHTTPCookie)
	def add_cookie(self, cookie):
		""" Add new cookie (or replace if there is cookie with the same name already)

		:param cookie: cookie to add
		:return: None
		"""
		if self.__ro_flag:
			raise RuntimeError('Read-only cookie-jar changing attempt')
		self.__cookies[cookie.name()] = cookie

	@verify_type(cookie_name=str)
	def remove_cookie(self, cookie_name):
		""" Remove cookie by its name

		:param cookie_name: cookie name
		:return:
		"""
		if self.__ro_flag:
			raise RuntimeError('Read-only cookie-jar changing attempt')
		if cookie_name in self.__cookies.keys():
			self.__cookies.pop(cookie_name)

	@verify_type(item=str)
	def __getitem__(self, item):
		""" Get cookie by its name

		:param item: cookie name
		:return:
		"""
		return self.__cookies[item]

	def __iter__(self):
		""" Iterate over cookie collection

		:return: None
		"""
		for cookie in self.__cookies.values():
			yield cookie

	def ro(self):
		""" Return read-only copy

		:return: WHTTPCookieJar
		"""
		ro_jar = WHTTPCookieJar()
		for cookie in self.__cookies.values():
			ro_jar.add_cookie(cookie.ro())
		ro_jar.__ro_flag = True
		return ro_jar

	@classmethod
	@verify_type(simple_cookie=SimpleCookie)
	def import_simple_cookie(cls, simple_cookie):
		""" Create cookie jar from SimpleCookie object

		:param simple_cookie: cookies to import
		:return: WHTTPCookieJar
		"""
		cookie_jar = WHTTPCookieJar()
		for cookie_name in simple_cookie.keys():
			cookie_attrs = {}
			for attr_name in WHTTPCookie.cookie_attr_value_compliance.keys():
				attr_value = simple_cookie[cookie_name][attr_name]
				if attr_value != '':
					cookie_attrs[attr_name] = attr_value

			cookie_jar.add_cookie(WHTTPCookie(
				cookie_name, simple_cookie[cookie_name].value, **cookie_attrs
			))
		return cookie_jar

	@classmethod
	@verify_type(cookie_text=str)
	def import_header_text(cls, cookie_text):
		""" Create cookie jar from HTTP Header text like 'Set-Cookie: cookie=value'

		:param cookie_text: http header code
		:return: WHTTPCookieJar
		"""
		simple_cookie = SimpleCookie()
		simple_cookie.load(cookie_text)
		return cls.import_simple_cookie(simple_cookie)
