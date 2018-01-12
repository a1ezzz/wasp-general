# -*- coding: utf-8 -*-
# wasp_general/uri.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

# TODO: document the code
# TODO: write tests for the code
# TODO: merge some from wasp_general.network.web.service and wasp_general.network.web.re_statements

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from enum import Enum
from urllib.parse import urlsplit, urlunsplit

from wasp_general.verify import verify_type


class WURI:

	class Component(Enum):
		scheme = 'scheme'
		username = 'username'
		password = 'password'
		hostname = 'hostname'
		port = 'port'
		path = 'path'
		query = 'query'
		fragment = 'fragment'

	def __init__(self, **components):
		self.__components = {x: None for x in WURI.Component}

		for component_name, component_value in components.items():
			self.component(component_name, component_value)

	def __getattr__(self, item):
		try:
			components_fn = object.__getattribute__(self, WURI.component.__name__)
			item = WURI.Component(item)
			return lambda: components_fn(item)
		except ValueError:
			pass

		return object.__getattribute__(self, item)

	def __str__(self):
		netloc = ''

		username = self.username()
		if username is not None:
			netloc += username

		password = self.password()
		if password is not None:
			netloc += ':' + password

		if len(netloc) > 0:
			netloc += '@'

		hostname = self.hostname()
		if hostname is not None:
			netloc += hostname

		port = self.port()
		if port is not None:
			netloc += ':' + str(port)

		scheme = self.scheme()
		path = self.path()
		if len(netloc) == 0 and scheme is not None and path is not None:
			path = '/' + path

		return urlunsplit((
			scheme if scheme is not None else '',
			netloc,
			path if path is not None else '',
			self.query(),
			self.fragment()
		))

	@verify_type(component=(str, Component))
	def component(self, component, value=None):
		if isinstance(component, str) is True:
			component = WURI.Component(component)
		if value is not None:
			self.__components[component] = value
			return value
		return self.__components[component]

	@classmethod
	def parse(cls, uri):
		uri_components = urlsplit(uri)
		adapter_fn = lambda x: x if x is not None and (isinstance(x, str) is False or len(x)) > 0 else None

		return cls(
			scheme=adapter_fn(uri_components.scheme),
			username=adapter_fn(uri_components.username),
			password=adapter_fn(uri_components.password),
			hostname=adapter_fn(uri_components.hostname),
			port=adapter_fn(uri_components.port),
			path=adapter_fn(uri_components.path),
			query=adapter_fn(uri_components.query),
			fragment=adapter_fn(uri_components.fragment),
		)
