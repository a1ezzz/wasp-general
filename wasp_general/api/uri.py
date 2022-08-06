# -*- coding: utf-8 -*-
# wasp_general/api/uri.py
#
# Copyright (C) 2019 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

from wasp_general.verify import verify_type, verify_value

from wasp_general.api.check import WArgsRestrictionProto, WArgsValueRestriction, WChainChecker
from wasp_general.api.registry import register_api, WAPIRegistry

from wasp_general.uri import WURI, WURIQuery


class WURIRestriction(WArgsValueRestriction):
	""" This restriction splits URI into components from the selected arguments. And applies the specified
	restriction
	"""

	@verify_type('strict', restrictions=WArgsRestrictionProto)
	@verify_type('paranoid', args_selection=WArgsValueRestriction.ArgsSelection, extra_kw_args=str)
	def __init__(
		self, restriction, *extra_kw_args, args_selection=WArgsValueRestriction.ArgsSelection.none,
	):
		""" Create new restriction

		:param restriction: a restriction that will be applied on URI components
		:type restriction: WArgsRestrictionProto

		:param extra_kw_args: same as extra_kw_args parameter in meth:`.WArgsValueRestriction.__init__` method
		:type extra_kw_args: str

		:param args_selection: same as args_selection parameter in meth:`.WArgsValueRestriction.__init__`
		method
		:type args_selection: WArgsValueRestriction.ArgsSelection
		"""
		WArgsValueRestriction.__init__(self, *extra_kw_args, args_selection=args_selection)
		self.__restriction = restriction

	@verify_type('strict', value=(WURI, str), name=(str, None))
	def check_value(self, value, name=None):
		""" :meth:`.WArgsValueRestriction.check_value` method implementation. Checks the given URI value by
		splitting into components and applying a restriction on them

		:param value: same as thw value parameter in the meth:`.WArgsValueRestriction.check_value` method
		:type value: WURI | str

		:param name: same as the name parameter in the meth:`.WArgsValueRestriction.check_value` method
		:type name: str | None

		:rtype: None
		"""
		if isinstance(value, str) is True:
			value = WURI.parse(value)

		self.__restriction.check(
			**{comp.value: comp_value for comp, comp_value in value if comp_value is not None}
		)


class WURIQueryRestriction(WArgsValueRestriction):
	""" This restriction converts query parameters from an URI into a :class:`dict` object and applies restrictions
	on that dictionary.

	Note: in order this restriction to work an URI query must be specified as a named parameter "query"
	"""

	@verify_type('strict', restrictions=WArgsRestrictionProto)
	def __init__(self, *restrictions):
		""" Create new restriction

		:param restrictions: restriction that will be applied on query parameters
		:type restrictions: WArgsRestrictionProto
		"""
		WArgsValueRestriction.__init__(
		        self, WURI.Component.query, args_selection=WArgsValueRestriction.ArgsSelection.none
		)
		self.__restriction_chain = WChainChecker(*restrictions)

	@verify_type('strict', value=(WURIQuery, str), name=(str, None))
	def check_value(self, value, name=None):
		""" :meth:`.WArgsValueRestriction.check_value` method implementation. Converts the given URI query
		into dictionary and applies restriction

		:param value: same as the value parameter in the meth:`.WArgsValueRestriction.check_value` method
		:type value: WURIQuery | str

		:param name: same as the name parameter in the meth:`.WArgsValueRestriction.check_value` method
		:type name: str | None

		:rtype: None
		"""
		if isinstance(value, str) is True:
			value = WURIQuery.parse(value)

		self.__restriction_chain.check(**{
			param_name: param_value for param_name, param_value in value.parameters()
		})


class WURIAPIRegistry(WAPIRegistry):
	""" This is a registry implementation, that uses API id as a scheme name from an URI
	"""

	@verify_type('strict', uri=(WURI, str))
	def open(self, uri):
		""" Return descriptor by an URI scheme name

		:param uri: URI from which a scheme name will be fetched
		:type uri: WURI | str

		:rtype: any

		:raise WNoSuchAPIIdError: when the specified scheme was not found
		"""
		if isinstance(uri, str) is True:
			uri = WURI.parse(uri)
		return self.get(uri.scheme())


@verify_type('strict', scheme_name=str, registry=WURIAPIRegistry)
@verify_value('strict', scheme_name=lambda x: len(x) > 0 and ':' not in x)
def register_scheme_handler(registry, scheme_name):
	""" This is a decorator, that may limit input parameters. This limit will be used if the correct
	WASP_ENABLE_CHECKS variable was set. This decorator should be used in conjugation with
	an :class:`.WURIAPIRegistry` object

	:param registry: registry decorated function will be registered in
	:type registry: WURIAPIRegistry

	:param scheme_name: name of an URI scheme with which decorated function will be registered
	:type scheme_name: str

	:rtype: callable
	"""
	return register_api(registry, scheme_name)
