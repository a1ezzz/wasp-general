# -*- coding: utf-8 -*-
# wasp_general/network/web/debug.py
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

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type
from wasp_general.network.web.proto import WWebRequestProto, WWebResponseProto, WWebTargetRouteProto


class WWebDebugInfo(metaclass=ABCMeta):
	""" This is API prototype for web-service debugging process
	"""

	@abstractmethod
	def session_id(self):
		""" Create new token, that is used for session identification

		:return: any type
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(request=WWebRequestProto, protocol_version=str, protocol=str)
	def request(self, session_id, request, protocol_version, protocol):
		""" Dump client request

		:param session_id: session origin
		:param request: client request
		:param protocol_version: client protocol version (like 0.9/1.0/1.1/2)
		:param protocol: client protocol (like http/https)
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(response=WWebResponseProto)
	def response(self, session_id, response):
		""" Dump server response to client

		:param session_id: session origin
		:param response: server response
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(target_route=(WWebTargetRouteProto, None))
	def target_route(self, session_id, target_route):
		""" Dump target route

		:param session_id: session origin
		:param target_route: target route
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(exc=Exception)
	def exception(self, session_id, exc):
		""" Dump raised exception (may be called more then once)

		:param session_id: session origin
		:param exc: raised exception
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def finalize(self, session_id):
		""" Client session finalization. This method is called whenever exceptions were risen or not

		:param session_id: session origin
		:return: None
		"""
		raise NotImplementedError('This method is abstract')
