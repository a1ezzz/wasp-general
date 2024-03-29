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

import enum
import re
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from abc import ABCMeta, abstractmethod

from wasp_general.types.str_enum import WStrEnum
from wasp_general.verify import verify_type, verify_subclass


class WURI:
	"""
	Class that represent URI as it is described in RFC 3986
	"""

	@enum.unique
	class Component(WStrEnum):
		""" Parts/components names that URI is consists of
		"""
		scheme = enum.auto()
		username = enum.auto()
		password = enum.auto()
		hostname = enum.auto()
		port = enum.auto()
		path = enum.auto()
		query = enum.auto()
		fragment = enum.auto()

	__all_components__ = {str(x) for x in Component}

	def __init__(self, **components):
		""" Create new WURI object. By default, empty URI is created

		:param components: components that must be set for this URI. Keys - components names as they
		defined in :class:`.WURI.Component`, values - corresponding values
		:type components: str|int
		"""
		self.__components = {x: None for x in WURI.Component}

		for component_name, component_value in components.items():
			self.component(component_name, component_value)

	@verify_type('strict', item=str)
	def __getattr__(self, item):
		""" Return component value by its name

		:param item: component name
		:type item: str

		:return: in case of component name - function, that returns str, int or None
		:rtype: () -> (str|int|None)
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

		:rtype: str
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

	@verify_type('strict', component=(str, Component), value=(str, int, None))
	def component(self, component, value=None):
		""" Set and/or get component value.

		:param component: component name to return
		:type component: str | WURI.Component
		:param value: if value is not None, this value will be set as a component value
		:type value: str | int | None

		:rtype: str
		"""
		if isinstance(component, str) is True:
			component = WURI.Component(component)
		if value is not None:
			if isinstance(value, int) is True:
				if component != WURI.Component.port:
					raise ValueError('"int" type is suitable for "WURI.Component.port" component only')
			elif component == WURI.Component.port:
				raise ValueError('"WURI.Component.port" value must be "int" type')

			self.__components[component] = value
			return value
		return self.__components[component]

	@verify_type('strict', component=(str, Component))
	def reset_component(self, component):
		""" Unset component in this URI

		:param component: component name (or component type) to reset
		:type component: str | WURI.Component

		:rtype: None
		"""
		if isinstance(component, str) is True:
			component = WURI.Component(component)
		self.__components[component] = None

	@classmethod
	@verify_type('strict', uri=str)
	def parse(cls, uri):
		""" Parse URI-string and return WURI object

		:param uri: string to parse
		:type uri: str

		:rtype: WURI
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

		:rtype: generator
		"""
		for component in WURI.Component:
			component_name = component.value
			component_value_fn = getattr(self, component_name)
			yield component, component_value_fn()


class WURIQuery:
	""" Represent a query component of an URI. Any parameter may present for more then one time
	"""
	# TODO: add quote/ unqoute to replace %XX

	def __init__(self):
		""" Create new query component
		"""
		self.__query = {}

	@verify_type('strict', name=str, value=(str, None))
	def replace_parameter(self, name, value=None):
		""" Replace parameter in this query. All previously added values will be discarded

		:param name: parameter name to replace
		:type name: str

		:param value: parameter value to set (None to set null-value)
		:type value: str | None

		:rtype: None
		"""
		self.__query[name] = [value]

	@verify_type('strict', name=str, value=(str, None))
	def add_parameter(self, name, value=None):
		""" Add new parameter value to this query. New value will be appended to previously added values.

		:param name: parameter name
		:type name: str

		:param value: value to add (None to set null-value)
		:type value: str | None

		:rtype: None
		"""
		if name not in self.__query:
			self.__query[name] = [value]
		else:
			self.__query[name].append(value)

	@verify_type('strict', name=str)
	def remove_parameter(self, name):
		""" Remove the specified parameter from this query

		:param name: name of a parameter to remove
		:type name: str

		:rtype: None
		"""
		if name in self.__query:
			self.__query.pop(name)

	@verify_type('strict', item=str)
	def __contains__(self, item):
		""" Check if this query has the specified parameter

		:param item: parameter name to check
		:type item: str

		:rtype: bool
		"""
		return item in self.__query

	def __str__(self):
		""" Encode parameters from this query, so it can be use in URI

		:rtype: str
		"""
		parameters = {x: [y if y is not None else '' for y in self.__query[x]] for x in self.__query}
		return urlencode(parameters, True)

	@verify_type('strict', item=str)
	def __getitem__(self, item):
		""" Return all parameters values

		:param item: parameter name to retrieve
		:rtype item: str

		:rtype: (str, None)
		"""
		return tuple(self.__query[item])

	def __iter__(self):
		""" Iterate over parameters names

		:rtype: generator
		"""
		for name in self.__query:
			yield name

	def parameters(self):
		""" Iterate over items, pair of component name and component value will be raised

		:rtype: generator
		"""
		for item in self.__query.items():
			yield item

	@classmethod
	@verify_type('strict', query_str=str)
	def parse(cls, query_str):
		""" Parse string that represent query component from URI

		:param query_str: string without '?'-sign
		:type query_str: str

		:rtype: WURIQuery
		"""
		if not len(query_str):
			return cls()
		parsed_query = parse_qs(query_str, keep_blank_values=True, strict_parsing=True)
		result = cls()
		for parameter_name in parsed_query.keys():
			for parameter_value in parsed_query[parameter_name]:
				result.add_parameter(
					parameter_name,
					parameter_value if len(parameter_value) > 0 else None
				)
		return result


class WStrictURIQuery(WURIQuery):
	# TODO: Remove this class

	""" Strict version of :class:`.WURIQuery` class. It has optional limits and requirements
	"""

	class ParameterSpecification:
		""" Single query parameter specification. Defines optional limits and requirements for a single
		parameter
		"""

		@verify_type('strict', name=str, nullable=bool, multiple=bool, optional=bool, reg_exp=(str, None))
		def __init__(self, name, nullable=True, multiple=True, optional=False, reg_exp=None):
			""" Create new parameter specification.

			:param name: parameter name
			:rtype name: str

			:param nullable: whether parameter may have empty (null) value or not
			:rtype nullable: bool

			:param multiple: whether parameter may be specified more then one time or not
			:rtype multiple: bool

			:param optional: whether parameter must be specified at least one time or not
			:rtype optional: bool

			:param reg_exp: regular expression that all non-nullable values must match
			:rtype reg_exp: str
			"""
			self.__name = name
			self.__nullable = nullable
			self.__multiple = multiple
			self.__optional = optional
			self.__re_obj = re.compile(reg_exp) if reg_exp is not None else None

		def name(self):
			""" Return parameter name

			:rtype: str
			"""
			return self.__name

		def nullable(self):
			""" Return whether a parameter may have empty (null) value or not

			:rtype: bool
			"""
			return self.__nullable

		def multiple(self):
			""" Return whether a parameter may be specified more then one time or not

			:rtype: bool
			"""
			return self.__multiple

		def optional(self):
			""" Return whether a parameter must be specified at least one time or not

			:rtype: bool
			"""
			return self.__optional

		def re_obj(self):
			""" Return re module object for the specified regular expression, that all non-nullable values
			must match, or None if regular expression is not defined

			:rtype: re object | None
			"""
			return self.__re_obj

	@verify_type('strict', base_query=WURIQuery, specs=ParameterSpecification, extra_parameters=bool)
	def __init__(self, base_query, *specs, extra_parameters=True):
		""" Create new strict query

		:param base_query: base query, that must match all of the specifications
		:rtype base_query: WURIQuery

		:param specs: list of parameters specifications
		:rtype specs: WStrictURIQuery.ParameterSpecification

		:param extra_parameters: whether parameters that was not specified in "specs" are allowed
		:rtype extra_parameters: bool
		"""
		WURIQuery.__init__(self)
		self.__specs = {}
		self.__extra_parameters = extra_parameters

		for spec in specs:
			self.add_specification(spec)

		for name in base_query:
			for value in base_query[name]:
				self.add_parameter(name, value)

		for name in self.__specs:
			if self.__specs[name].optional() is False and name not in self:
				raise ValueError('Required parameter "%s" is missing' % name)

	def extra_parameters(self):
		""" Return flag, whether query parameters that was not specified in "specs" are allowed

		:rtype: bool
		"""
		return self.__extra_parameters

	@verify_type('strict', specification=ParameterSpecification)
	def replace_specification(self, specification):
		""" Replace current query parameter specification or add new one. No checks for the specified or any
		parameter are made regarding specification replacement

		:param specification: new specification that will replace specification for the corresponding parameter
		:type specification: WStrictURIQuery.ParameterSpecification

		:rtype: None
		"""
		self.__specs[specification.name()] = specification

	@verify_type('strict', specification=ParameterSpecification)
	def add_specification(self, specification):
		""" Add a new query parameter specification. If this object already has a specification for the
		specified parameter - exception is raised. No checks for the specified or any parameter are made
		regarding specification appending

		:param specification: new specification that will be added
		:type specification: WStrictURIQuery.ParameterSpecification

		:rtype: None
		"""
		name = specification.name()
		if name in self.__specs:
			raise ValueError('WStrictURIQuery object already has specification for parameter "%s" ' % name)
		self.__specs[name] = specification

	@verify_type('strict', name=str)
	def remove_specification(self, name):
		""" Remove a specification that matches a query parameter. No checks for the specified or any parameter
		are made regarding specification removing

		:param name: parameter name to remove
		:type name: str

		:rtype: None
		"""
		if name in self.__specs:
			self.__specs.pop(name)

	@verify_type('strict', name=str, value=(str, None))
	def replace_parameter(self, name, value=None):
		""" Replace a query parameter values with a new value. If a new value does not match current
		specifications, then exception is raised

		:param name: parameter name to replace
		:type name: str

		:param value: new parameter value. None is for empty (null) value
		:type value: str | None

		:rtype: None
		"""
		spec = self.__specs[name] if name in self.__specs else None
		if self.extra_parameters() is False and spec is None:
			raise ValueError('Extra parameters are forbidden for this WStrictURIQuery object')

		if spec is not None and spec.nullable() is False and value is None:
			raise ValueError('Nullable values is forbidden for parameter "%s"' % name)

		if spec is not None and value is not None:
			re_obj = spec.re_obj()
			if re_obj is not None and re_obj.match(value) is None:
				raise ValueError('Value does not match regular expression')

		WURIQuery.replace_parameter(self, name, value=value)

	@verify_type('strict', name=str, value=(str, None))
	def add_parameter(self, name, value=None):
		""" Add a query parameter and its value. If this query already has a parameter, or a new value does
		not match current specifications, then exception is raised

		:param name: parameter name to add
		:type name: str

		:param value: parameter value. None is for empty (null) value
		:type value: str | None

		:rtype: None
		"""
		spec = self.__specs[name] if name in self.__specs else None
		if self.extra_parameters() is False and spec is None:
			raise ValueError('Extra parameters are forbidden for this WStrictURIQuery object')

		if spec is not None and spec.nullable() is False and value is None:
			raise ValueError('Nullable values is forbidden for parameter "%s"' % name)

		if spec is not None and spec.multiple() is False and name in self:
			raise ValueError('Multiple values is forbidden for parameter "%s"' % name)

		if spec is not None and value is not None:
			re_obj = spec.re_obj()
			if re_obj is not None and re_obj.match(value) is None:
				raise ValueError('Value does not match regular expression')

		WURIQuery.add_parameter(self, name, value=value)

	@verify_type('strict', name=str)
	def remove_parameter(self, name):
		""" Remove parameter from this query. If a parameter is mandatory, then exception is raised

		:param name: parameter name to remove
		:type name: str

		:rtype: None
		"""
		spec = self.__specs[name] if name in self.__specs else None
		if spec is not None and spec.optional() is False:
			raise ValueError('Unable to remove a required parameter "%s"' % name)

		WURIQuery.remove_parameter(self, name)

	@classmethod
	@verify_type('strict', query_name=str)
	def parse(cls, query_str):
		""" :meth:`.WURIQuery.parse` method implementation. Returns :class:`.WURIQuery instead of
		:class:`.WStrictURIQuery`

		:type query_str: str

		:rtype: WURIQuery
		"""
		return WURIQuery.parse(query_str)

	@classmethod
	@verify_type('strict', query_str=str, specs=ParameterSpecification, extra_parameters=bool)
	def strict_parse(cls, query_str, *specs, extra_parameters=True):
		""" Parse query and return :class:`.WStrictURIQuery` object

		:param query_str: query component of URI to parse
		:type query_str: str

		:param specs: list of parameters specifications
		:type specs: WStrictURIQuery.ParameterSpecification

		:param extra_parameters: whether parameters that was not specified in "specs" are allowed
		:type extra_parameters: bool

		:rtype: WStrictURIQuery
		"""
		plain_result = cls.parse(query_str)
		return WStrictURIQuery(plain_result, *specs, extra_parameters=extra_parameters)


class WURIComponentVerifier:
	# TODO: Remove this class

	""" Descriptor that helps to verify that an URI component matches a specification
	"""

	@enum.unique
	class Requirement(enum.Enum):
		""" Represent necessity of URI component

		"""
		required = 0  # URI component is mandatory
		optional = 1  # URI component may present in an URI
		unsupported = None  # URI component is unavailable and it must be excluded from an URI

	@verify_type('strict', component=WURI.Component, requirement=Requirement, reg_exp=(str, None))
	def __init__(self, component, requirement, reg_exp=None):
		""" Create new URI component descriptor

		:param component: URI component, that should be verified
		:type component: WURI.Component

		:param requirement: URI component necessity
		:type requirement: WURIComponentVerifier.Requirement

		:param reg_exp: If specified - a regular expression, which URI component value (if defined) must match
		:type reg_exp: str | None
		"""
		self.__component = component
		self.__requirement = requirement
		self.__re_obj = re.compile(reg_exp) if reg_exp is not None else None

	def component(self):
		""" Return an URI component, that this specification is describing

		:rtype: WURI.Component
		"""
		return self.__component

	def requirement(self):
		""" Return an URI component necessity

		:rtype: WURIComponentVerifier.Requirement
		"""
		return self.__requirement

	def re_obj(self):
		""" If it was specified in a constructor, return regular expression object, that may be used for
		matching

		:rtype: re object | None
		"""
		return self.__re_obj

	@verify_type('strict', uri=WURI)
	def validate(self, uri):
		""" Check an URI for compatibility with this specification. Return True if the URI is compatible.

		:param uri: an URI to check
		:type uri: WURI

		:rtype: bool
		"""
		requirement = self.requirement()
		uri_component = uri.component(self.component())

		if uri_component is None:
			return requirement != WURIComponentVerifier.Requirement.required
		if requirement == WURIComponentVerifier.Requirement.unsupported:
			return False

		re_obj = self.re_obj()
		if re_obj is not None:
			return re_obj.match(uri_component) is not None
		return True


class WURIQueryVerifier(WURIComponentVerifier):
	# TODO: Remove this class

	""" Specific URI component descriptor that verify an query part only
	"""

	@verify_type('paranoid', requirement=WURIComponentVerifier.Requirement)
	@verify_type('strict', specs=WStrictURIQuery.ParameterSpecification, extra_parameters=bool)
	def __init__(self, requirement, *specs, extra_parameters=True):
		""" Create new query descriptor

		:param requirement: same as 'requirement' in :meth:`.WURIComponentVerifier.__init__`
		:type requirement: WURIComponentVerifier.Requirement

		:param specs: list of parameters specifications
		:type specs: WStrictURIQuery.ParameterSpecification

		:param extra_parameters: whether parameters that was not specified in "specs" are allowed
		:rtype extra_parameters: bool
		"""
		WURIComponentVerifier.__init__(self, WURI.Component.query, requirement)
		self.__specs = specs
		self.__extra_parameters = extra_parameters

	@verify_type('paranoid', uri=WURI)
	def validate(self, uri):
		""" Check that an query part of an URI is compatible with this descriptor. Return True if the URI is
		compatible.

		:param uri: an URI to check
		:type uri: WURI

		:rtype: bool
		"""
		if WURIComponentVerifier.validate(self, uri) is False:
			return False
		try:
			value = uri.component(self.component())
			if value is not None:
				WStrictURIQuery(
					WURIQuery.parse(value),
					*self.__specs,
					extra_parameters=self.__extra_parameters
				)
		except ValueError:
			return False
		return True


class WSchemeSpecification:
	# TODO: Remove this class

	""" Specification for URI, that is described by scheme-component
	"""

	@verify_type('strict', scheme_name=str, verifiers=WURIComponentVerifier)
	def __init__(self, scheme_name, *verifiers):
		""" Create new scheme specification. Every component that was not described by this method is treated
		as unsupported

		:param scheme_name: URI scheme value
		:type scheme_name: str

		:param verifiers: list of specifications for URI components
		:type verifiers: WURIComponentVerifier
		"""
		self.__scheme_name = scheme_name

		self.__verifiers = {
			WURI.Component.scheme: WURIComponentVerifier(
				WURI.Component.scheme, WURIComponentVerifier.Requirement.required
			)
		}

		for verifier in verifiers:
			component = verifier.component()
			if component in self.__verifiers:
				raise ValueError(
					'Multiple verifiers were spotted for the same component: %s' % component.value
				)

			self.__verifiers[component] = verifier

		for component in WURI.Component:
			if component not in self.__verifiers:
				self.__verifiers[component] = WURIComponentVerifier(
					component, WURIComponentVerifier.Requirement.unsupported
				)

	def scheme_name(self):
		""" Return scheme name that this specification is describing

		:rtype: str
		"""
		return self.__scheme_name

	@verify_type('strict', component=WURI.Component)
	def verifier(self, component):
		""" Return descriptor for the specified component

		:param component: component name which descriptor should be returned
		:rtype component: WURI.Component

		:rtype: WSchemeSpecification.ComponentDescriptor
		"""
		return self.__verifiers[component]

	def __iter__(self):
		""" Iterate over URI components. This method yields tuple of component (:class:`.WURI.Component`) and
		its descriptor (WURIComponentVerifier)

		:rtype: generator
		"""
		for component in WURI.Component:
			yield component, self.__verifiers[component]

	@verify_type('strict', uri=WURI)
	def is_compatible(self, uri):
		""" Check if URI is compatible with this specification. Compatible URI has scheme name that matches
		specification scheme name, has all of the required components, does not have unsupported components
		and may have optional components

		:param uri: URI to check
		:type uri: WURI

		:rtype: bool
		"""
		for component, component_value in uri:
			if self.verifier(component).validate(uri) is False:
				return False

		return True


class WSchemeHandler(metaclass=ABCMeta):
	# TODO: Remove this class

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
	@verify_type('strict', uri=WURI)
	def create_handler(cls, uri, **kwargs):
		""" Return handler instance

		:param uri: original URI, that a handler is created for
		:type uri: WURI

		:param kwargs: additional arguments that may be used by a handler specialization

		:rtype: WSchemeHandler
		"""
		raise NotImplementedError('This method is abstract')


class WSchemeCollection:
	# TODO: Remove this class
	""" Collection of URI scheme handlers, that is capable to process different WURI. Only one handler per scheme
	is supported. Suitable handler will be searched by a scheme name.
	"""

	class NoHandlerFound(Exception):
		""" Exception that is raised when no handler is found for a URI
		"""

		def __init__(self, uri):
			""" Create new exception object

			:param uri: URI which scheme does not have a corresponding handler
			:type uri: WURI
			"""
			Exception.__init__(self, 'No handler was found for the specified URI: %s' % str(uri))

	class SchemeIncompatible(Exception):
		""" Exception that is raised when URI does not match a specification (:class:`.WSchemeSpecification`).
		This happens if URI has unsupported components or does not have a required components.
		"""

		def __init__(self, uri):
			""" Create new exception object

			:param uri: URI that does not comply a handler specification (:class:`.WSchemeSpecification`)
			:type uri: WURI
			"""
			Exception.__init__(
				self,
				'Handler was found for the specified scheme. '
				'But URI has not required components or has unsupported components: %s' % str(uri)
			)

	@verify_subclass('paranoid', scheme_handler_cls=WSchemeHandler)
	@verify_subclass('strict', default_handler_cls=(WSchemeHandler, None))
	def __init__(self, *scheme_handlers_cls, default_handler_cls=None):
		""" Create new collection

		:param scheme_handlers_cls: handlers to add to this collection
		:type scheme_handlers_cls: type

		:param default_handler: handler that must be called for a URI that does not have scheme component
		:type default_handler_cls: type
		"""
		self.__handlers_cls = []
		self.__default_handler_cls = default_handler_cls
		for handler_cls in scheme_handlers_cls:
			self.add(handler_cls)

	@verify_subclass('strict', scheme_handler_cls=WSchemeHandler)
	def add(self, scheme_handler_cls):
		""" Append the specified handler to this collection

		:param scheme_handler_cls: handler that should be added
		:type scheme_handler_cls: type

		:rtype: None
		"""
		self.__handlers_cls.append(scheme_handler_cls)

	@verify_type('strict', scheme_name=(str, None))
	def handler(self, scheme_name=None):
		""" Return handler which scheme name matches the specified one

		:param scheme_name: scheme name to search for
		:type scheme_name: str | None

		:return: WSchemeHandler class or None (if matching handler was not found)
		:rtype: WSchemeHandler | None
		"""
		if scheme_name is None:
			return self.__default_handler_cls
		for handler in self.__handlers_cls:
			if handler.scheme_specification().scheme_name() == scheme_name:
				return handler

	@verify_type('strict', uri=(WURI, str))
	def open(self, uri, **kwargs):
		""" Return handler instance that matches the specified URI. WSchemeCollection.NoHandlerFound and
		WSchemeCollection.SchemeIncompatible may be raised.

		:param uri: URI to search handler for
		:type uri: WURI | str

		:param kwargs: additional arguments that may be used by a handler specialization

		:rtype: WSchemeHandler
		"""
		if isinstance(uri, str) is True:
			uri = WURI.parse(uri)

		handler = self.handler(uri.scheme())
		if handler is None:
			raise WSchemeCollection.NoHandlerFound(uri)

		if uri.scheme() is None:
			uri.component('scheme', handler.scheme_specification().scheme_name())

		if handler.scheme_specification().is_compatible(uri) is False:
			raise WSchemeCollection.SchemeIncompatible(uri)

		return handler.create_handler(uri, **kwargs)
