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

# TODO: merge some from wasp_general.network.web.service and wasp_general.network.web.re_statements

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from enum import Enum
from urllib.parse import urlsplit, urlunsplit
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_subclass


class WURI:
	"""
	Class that represent URI as it is described in RFC 3986
	"""

	class Component(Enum):
		""" Parts/components names that URI is consists of
		"""
		scheme = 'scheme'
		username = 'username'
		password = 'password'
		hostname = 'hostname'
		port = 'port'
		path = 'path'
		query = 'query'
		fragment = 'fragment'

	def __init__(self, **components):
		""" Create new WURI object. By default empty URI is created

		:param components: components that must be set for this URI. Keys - components names as they
		defined in :class:`.WURI.Component`, values - corresponding values
		"""
		self.__components = {x: None for x in WURI.Component}

		for component_name, component_value in components.items():
			self.component(component_name, component_value)

	@verify_type(item=str)
	def __getattr__(self, item):
		""" Return component value by its name

		:param item: component name
		:return: str
		"""
		try:
			components_fn = object.__getattribute__(self, WURI.component.__name__)
			item = WURI.Component(item)
			return lambda: components_fn(item)
		except ValueError:
			pass

		return object.__getattribute__(self, item)

	def __str__(self):
		""" Return string that represents this URI

		:return: str
		"""
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
			path = '//' + path

		return urlunsplit((
			scheme if scheme is not None else '',
			netloc,
			path if path is not None else '',
			self.query(),
			self.fragment()
		))

	@verify_type(component=(str, Component))
	def component(self, component, value=None):
		""" Set and/or get component value.

		:param component: component name to return
		:param value: if value is not None, this value will be set as a component value
		:return: str
		"""
		if isinstance(component, str) is True:
			component = WURI.Component(component)
		if value is not None:
			self.__components[component] = value
			return value
		return self.__components[component]

	@classmethod
	@verify_type(uri=str)
	def parse(cls, uri):
		""" Parse URI-string and return WURI object

		:param uri: string to parse
		:return: WURI
		"""
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

	def __iter__(self):
		""" Iterate over URI components. This method yields tuple of component name and its value

		:return: generator
		"""
		for component in WURI.Component:
			component_name = component.value
			component_value_fn = getattr(self, component_name)
			yield component, component_value_fn()


class WSchemeSpecification:
	""" Specification for URI, that is described by scheme-component
	"""

	class ComponentDescriptor(Enum):
		""" Value that describes component relation to a scheme specification
		"""
		required = 0
		optional = 1
		unsupported = None

	@verify_type(scheme_name=str)
	def __init__(self, scheme_name, **descriptors):
		""" Create new scheme specification. Every component that was not described by this method is treated
		as unsupported

		:param scheme_name: URI scheme value
		:param descriptors: component names and its descriptors
		(:class:`.WSchemeSpecification.ComponentDescriptor`)
		"""
		self.__scheme_name = scheme_name

		self.__descriptors = {x: WSchemeSpecification.ComponentDescriptor.unsupported for x in WURI.Component}
		self.__descriptors[WURI.Component.scheme] = WSchemeSpecification.ComponentDescriptor.required

		for descriptor_name in descriptors.keys():
			component = WURI.Component(descriptor_name)
			if component == WURI.Component.scheme:
				raise TypeError('Scheme name can not be specified twice')
			descriptor = descriptors[descriptor_name]
			if isinstance(descriptor, WSchemeSpecification.ComponentDescriptor) is False:
				raise TypeError('Invalid "%s" descriptor type' % descriptor_name)
			self.__descriptors[component] = descriptor

	def scheme_name(self):
		""" Return scheme name that this specification is describing

		:return: str
		"""
		return self.__scheme_name

	@verify_type(component=WURI.Component)
	def descriptor(self, component):
		""" Return descriptor for the specified component

		:param component: component name which descriptor should be returned
		:return: WSchemeSpecification.ComponentDescriptor
		"""
		return self.__descriptors[component]

	def __iter__(self):
		""" Iterate over URI components. This method yields tuple of component (:class:`.WURI.Component`) and
		its descriptor

		:return: generator
		"""
		for component in WURI.Component:
			yield component, self.__descriptors[component]

	@verify_type(uri=WURI)
	def is_compatible(self, uri):
		""" Check if URI is compatible with this specification. Compatible URI has scheme name that matches
		specification scheme name, has all of the required components, does not have unsupported components
		and may have optional components

		:param uri: URI to check
		:return: bool
		"""
		for component, component_value in uri:
			descriptor = self.descriptor(component)
			if component_value is None:
				if descriptor == WSchemeSpecification.ComponentDescriptor.required:
					return False
			elif descriptor == WSchemeSpecification.ComponentDescriptor.unsupported:
					return False
		return True


class WSchemeHandler(metaclass=ABCMeta):
	""" Handler that do some work for compatible URI
	"""

	@classmethod
	@abstractmethod
	def scheme_specification(cls):
		""" Return scheme specification

		:return: WSchemeSpecification
		"""
		raise NotImplementedError('This method is abstract')

	@classmethod
	@abstractmethod
	@verify_type(uri=WURI)
	def create_handler(cls, uri, **kwargs):
		""" Return handler instance

		:param uri: original URI, that a handler is created for
		:param kwargs: additional arguments that may be used by a handler specialization

		:return: WSchemeHandler
		"""
		raise NotImplementedError('This method is abstract')


class WSchemeCollection:
	""" Collection of URI scheme handlers, that is capable to process different WURI. Only one handler per scheme
	is supported. Suitable handler will be searched by a scheme name.
	"""

	class NoHandlerFound(Exception):
		""" Exception that is raised when no handler is found for a URI
		"""

		def __init__(self, uri):
			""" Create new exception object

			:param uri: URI which scheme does not have a corresponding handler
			"""
			Exception.__init__(self, 'No handler was found for the specified URI: %s' % str(uri))

	class SchemeIncompatible(Exception):
		""" Exception that is raised when URI does not match a specification (:class:`.WSchemeSpecification`).
		This happens if URI has unsupported components or does not have a required components.
		"""

		def __init__(self, uri):
			""" Create new exception object

			:param uri: URI that does not comply a handler specification (:class:`.WSchemeSpecification`)
			"""
			Exception.__init__(
				self,
				'Handler was found for the specified scheme. '
				'But URI has not required components or has unsupported components: %s' % str(uri)
			)

	def __init__(self, *scheme_handlers_cls, default_handler_cls=None):
		""" Create new collection

		:param scheme_handlers_cls: handlers to add to this collection
		:param default_handler: handler that must be called for a URI that does not have scheme component
		"""
		self.__handlers_cls = []
		self.__default_handler_cls = default_handler_cls
		for handler_cls in scheme_handlers_cls:
			self.add(handler_cls)

	@verify_subclass(scheme_handler_cls=WSchemeHandler)
	def add(self, scheme_handler_cls):
		""" Append the specified handler to this collection

		:param scheme_handler_cls: handler that should be added
		:return: None
		"""
		self.__handlers_cls.append(scheme_handler_cls)

	def handler(self, scheme_name=None):
		""" Return handler which scheme name matches the specified one

		:param scheme_name: scheme name to search for
		:return: WSchemeHandler class or None (if matching handler was not found)
		"""
		if scheme_name is None:
			return self.__default_handler_cls
		for handler in self.__handlers_cls:
			if handler.scheme_specification().scheme_name() == scheme_name:
				return handler

	@verify_type(uri=WURI)
	def open(self, uri, **kwargs):
		""" Return handler instance that matches the specified URI. WSchemeCollection.NoHandlerFound and
		WSchemeCollection.SchemeIncompatible may be raised.

		:param uri: URI to search handler for
		:param kwargs: additional arguments that may be used by a handler specialization
		:return: WSchemeHandler
		"""
		handler = self.handler(uri.scheme())
		if handler is None:
			raise WSchemeCollection.NoHandlerFound(uri)

		if uri.scheme() is None:
			uri.component('scheme', handler.scheme_specification().scheme_name())

		if handler.scheme_specification().is_compatible(uri) is False:
			raise WSchemeCollection.SchemeIncompatible(uri)

		return handler.create_handler(uri, **kwargs)
