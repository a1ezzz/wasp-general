# -*- coding: utf-8 -*-
# wasp_general/network/web/response.py
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

from wasp_general.verify import verify_type, verify_value

from wasp_general.network.web.proto import WWebResponseProto
from wasp_general.network.web.headers import WHTTPHeaders


class WWebResponse(WWebResponseProto):
	""" Simple :class:`.WWebResponseProto` implementation
	"""

	@verify_type(status=(int, None), headers=(WHTTPHeaders, None), response_data=(bytes, None))
	@verify_value(status=lambda x: x is None or x > 0)
	def __init__(self, status=None, headers=None, response_data=None):
		""" Create new response

		:param status: response status code
		:param headers: response headers
		:param response_data: response data
		"""
		WWebResponseProto.__init__(self)
		self.__status = status
		self.__headers = headers
		self.__response_data = response_data
		self.__pushed_responses = []

	def status(self):
		""" :meth:`.WWebResponseProto.status` method implementation
		"""
		return self.__status

	def headers(self):
		""" :meth:`.WWebResponseProto.headers` method implementation
		"""
		return self.__headers

	def response_data(self):
		""" :meth:`.WWebResponseProto.response_data` method implementation
		"""
		return self.__response_data

	@verify_type(response=WWebResponseProto)
	def __push__(self, *responses):
		""" Save responses to push

		:param responses: responses to push
		:return:
		"""
		self.__pushed_responses.extend(responses)

	def __pushed_responses__(self):
		""" :meth:`.WWebResponseProto.__pushed_responses__` method implementation
		"""
		return tuple(self.__pushed_responses)
