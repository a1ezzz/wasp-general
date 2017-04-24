# -*- coding: utf-8 -*-
# wasp_general/network/web/re_statements.py
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


http_header_name = '[^\x00-\x1e\x7f()<>@,;:\\\\"/\[\]?={} \t]+'.encode('us-ascii')
"""
Represent valid HTTP header name.

see RFC 1945, Section 4.2
external usage: :class:`.WHTTPHeaders`
"""

http_method_name = 'GET|HEAD|POST|PUT|DELETE|CONNECT|OPTIONS|TRACE'
"""
Represent valid HTTP method. This regexp has as strict restriction as HTTP/2 (RFC 7231) does.

see RFC 1945, Section 5.1.1. RFC 2616, Section 5.1.1, RFC 7231, Section 4.1

external usage: :class:`.WWebRequest`
"""

http_path_alphabet = 'a-zA-Z0-9_\-.~%:/?#\[\]@!$&\'()*+,;=\"'
"""
Represent valid set of chars, that URI can have

for URI see RFC 3986, Section 3
"""

http_path = '/[' + http_path_alphabet + ']*'
"""
Represent valid requested URI

for URI see RFC 3986, Section 3
external usage: :class:`.WWebRequest`, :class:`.WHTTPCookie`
"""

http_version = '0\.9|1\.0|1\.1'
"""
Represent valid requested HTTP-versions

see RFC 2616, Section 3.1
"""

uri_query_alphabet = 'a-zA-Z0-9\-._~%!$&\'()*+,;=:@/?'
"""
Represent valid set of chars, that query can have it in URI

see RFC 2616, Section 3.1
"""

uri_fragment_alphabet = 'a-zA-Z0-9\-._~%!$&\'()*+,;=:@/?'
"""
Represent valid set of chars, that fragment can have it in URI

see RFC 2616, Section 3.1
"""

http_get_vars_selection = '\?([' + uri_query_alphabet + ']+)(#[' + uri_fragment_alphabet + ']*)?$'
"""
Allow to select variables (GET-variables) and fragment code from URI

see RFC 2616, Section 3.4
external usage: :class:`.WWebRequestProto`
"""

http_post_vars_selection = '([' + uri_query_alphabet + ']+)'
"""
Allow to select variables that are given as 'application/x-www-form-urlencoded'.

see RFC 1867
external usage: :class:`.WWebRequestProto`
"""

http_cookie_expires = '[a-zA-Z0-9 ,:-]+'
"""
Represent valid Expires attribute value of cookie

see RFC 6265, Section 5.2.1
external usage: :class:`.WHTTPCookie`
"""

http_cookie_max_age = '[1-9][0-9]*'
"""
Represent valid Max-Age attribute value of cookie

see RFC 6265, Section 5.2.2
external usage: :class:`.WHTTPCookie`
"""

http_cookie_domain = '[a-zA-Z\-.0-9]+'
"""
Represent valid Domain attribute value of cookie

see RFC 6265, Section 5.2.3
external usage: :class:`.WHTTPCookie`
"""

http_cookie_secure = '.*'
"""
Represent valid Secure attribute value of cookie

see RFC 6265, Section 5.2.5
external usage: :class:`.WHTTPCookie`
"""

http_cookie_httponly = '.*'
"""
Represent valid HttpOnly attribute value of cookie

see RFC 6265, Section 5.2.6
external usage: :class:`.WHTTPCookie`
"""

wasp_presenter_name_alphabet = 'a-zA-Z0-9_.\-'
"""
Represent valid set of chars, that presenter name can have
"""

wasp_presenter_name_selection = '([a-zA-Z][' + wasp_presenter_name_alphabet + ']*)'
"""
Allow to select presenter name
"""

wasp_route_uri_pattern_alphabet = http_path_alphabet + '\{\}\\\\'
"""
Represent valid set of chars, that route URI pattern can have
"""

wasp_route_arg_name = '[a-zA-Z][a-zA-Z0-9_]*'
"""
Represent valid name for route argument name

external usage: :class:`.WWebRouteMap`
"""
wasp_route_arg_name_selection = '\{(' + wasp_route_arg_name + ')\}'
"""
Represent simple route argument pattern

external usage: :class:`.WWebRoute.BasicArgSearch`
"""

wasp_route_arg_value_alphabet = http_path_alphabet
for c in ['/', '?', ',', '#']:
	wasp_route_arg_value_alphabet = wasp_route_arg_value_alphabet.replace(c, '')
""" Represent valid set of chars, that route argument value can have
"""

wasp_route_arg_value_selection = '([' + wasp_route_arg_value_alphabet + ']+)'
"""
Allow to select route argument from a requested URI

external usage: :class:`.WWebRoute.BasicArgSearch`
"""

wasp_route_custom_arg_value_pattern = '[^\"]'
"""
Represent custom route argument pattern
"""

wasp_route_custom_arg_selection = \
	'(\{(' + wasp_route_arg_name + ') *: *\"(' + wasp_route_custom_arg_value_pattern + '+)\"\})'
"""
Allow to select custom route argument name and argument pattern from URI pattern

external usage: :class:`.WWebRoute.CustomArgSearch`
"""

wasp_route_import_pattern = \
	'^\s*([' + wasp_route_uri_pattern_alphabet + ']+) +=> +' + wasp_presenter_name_selection + '( +\((.*)\))?\s*$'
"""
Allow to parse custom route from a imported text

external usage: :class:`.WWebRouteMap`
"""
