# -*- coding: utf-8 -*-
# wasp_general/api/transformation.py
#
# Copyright (C) 2017-2019 the wasp-general authors and contributors
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

import enum
import functools

from wasp_general.verify import verify_type, verify_value

from wasp_general.api.registry import WAPIRegistry, WNoSuchAPIIdError


class WTransformationError(Exception):
	""" This exception is raised if an object can not be dismantled or dismantled object can not be compiled
	"""
	pass


class WTransformationRegistry(WAPIRegistry):
	""" This registry stores functions that may dismantle objects and may compile dismantled objects into
	original ones. "Dismantling" is a procedure that simplify object structure so it may be converted to
	JSON or YAML formats. Simple types such as None, int, float, str, list are not modified. Dict or custom
	objects are transformed to a dict consists of simple types objects
	"""

	@enum.unique
	class RegFunctionType(enum.Enum):
		""" Supported registry functions

		:note: This enum is used for registry implementation only and may be changed in future
		"""

		dismantle_fn = 'dismantle__'
		""" This type of functions are used for dismantling
		"""

		compose_fn = 'compose__'
		""" This type of functions are used for composition
		"""

	__composer_hook_attr__ = '__composer_hook__'
	""" Key of a dictionary that points to a class name of an object

	:note: This key is used for registry implementation only and may be changed in future
	"""

	__composer_dump_attr__ = '__composer_dump__'
	""" Key of a dictionary that points to an object structure

	:note: This key is used for registry implementation only and may be changed in future
	"""

	@verify_type('strict', api_id=str)
	@verify_value('strict', api_descriptor=lambda x: callable(x))
	def register(self, api_id, api_descriptor):
		""" This method must be omitted, because of additional restrictions to api_id that may be used
		"""
		raise NotImplementedError(
			'This method must be omitted. Use the "WTransformationRegistry.register_function"'
			'method instead'
		)

	@verify_type('strict', cls=(type, str), func_type=RegFunctionType)
	@verify_value('strict', func=lambda x: callable(x))
	def register_function(self, cls, func_type, func):
		""" This is alternate to :meth:`.WTransformationRegistry.register` function that register the
		specified callable object.

		:param cls: class which may be composed or dismantled by the function
		:type cls: type | str

		:param func_type: defines operation that will by the function
		:type func_type: WTransformationRegistry.RegFunctionType

		:param func: function that may do the specified operation (composition or dismantling) on the
		specified class
		:type func: callable

		:raise WDuplicateAPIIdError: when the registry already has a function for the specified class
		and the specified operation

		:rtype: None
		"""
		api_id = self.__api_id(func_type, cls)
		WAPIRegistry.register(self, api_id, func)

	def compose(self, obj_dump):
		""" Create an object from a previously created dump. A dump is a result of
		:meth:`.WTransformationRegistry.dismantle` method call

		:param obj_dump: structure from which an object should be created
		:type obj_dump: object | None

		:rtype: object | None
		"""
		if obj_dump is None or isinstance(obj_dump, (int, float, str)):
			return obj_dump
		elif isinstance(obj_dump, list):
			return [self.compose(x) for x in obj_dump]

		assert(isinstance(obj_dump, dict))
		for attr in (self.__composer_hook_attr__, self.__composer_dump_attr__):
			if attr not in obj_dump:
				raise ValueError('The required attribute "%s" was not found in a dictionary' % attr)

		hook_name = obj_dump[self.__composer_hook_attr__]
		try:
			api_id = self.__api_id(WTransformationRegistry.RegFunctionType.compose_fn, hook_name)
			fn = self.get(api_id)
			return fn(obj_dump[self.__composer_dump_attr__], self)
		except WNoSuchAPIIdError:
			raise WTransformationError('Unable to compose unknown class "%s"' % hook_name)

	def dismantle(self, obj):
		""" Create an dump of an object. This dump may be used to create object copy later.

		:param obj: an object to dump
		:type obj: object | None

		:rtype: object | None
		"""
		if obj is None or isinstance(obj, (int, float, str)):
			return obj
		elif isinstance(obj, list):
			return [self.dismantle(x) for x in obj]

		cls = obj.__class__
		hook_name = self.__hook_name(cls)

		try:
			api_id = self.__api_id(WTransformationRegistry.RegFunctionType.dismantle_fn, cls)
			fn = self.get(api_id)
			obj_dump = fn(obj, self)

			return {
				self.__composer_hook_attr__: hook_name,
				self.__composer_dump_attr__: obj_dump
			}
		except WNoSuchAPIIdError:
			raise WTransformationError('Unable to dismantle unknown class "%s"' % hook_name)

	@verify_type('strict', cls=(str, type))
	@verify_value('strict', cls=lambda x: isinstance(x, type) or len(x) > 0)
	def __hook_name(self, cls):
		""" Return a class id. This id may be used in objects dumps, and as a part of a registry api_id

		:param cls: name of a class or a type whose name should be used
		:type cls: str | type

		:rtype: str
		"""
		if isinstance(cls, str) is False:
			cls = cls.__name__
		return cls

	@verify_type('strict', registry_type=RegFunctionType, cls=(str, type))
	@verify_value('strict', cls=lambda x: isinstance(x, type) or len(x) > 0)
	def __api_id(self, registry_type, cls):
		""" Return registry's api_id

		:param registry_type: function type for which api_id should be generated
		:type registry_type: WTransformationRegistry.RegFunctionType

		:param cls: name of a class or a type for which api_id should be generated
		:type cls: str | type

		:rtype: str
		"""
		return registry_type.value + self.__hook_name(cls)


__default_transformation_registry__ = WTransformationRegistry()
""" Instance of the default transformation registry
"""


@verify_type('strict', cls=(str, type), registry=(WTransformationRegistry, None))
@verify_value('strict', cls=lambda x: isinstance(x, type) or len(x) > 0)
def register_composer(cls, registry=None):
	""" Return a function decorator that will register a function in a registry. This function will be used for an
	object composition

	:param cls: class that may be composed
	:type cls: str | type

	:param registry: registry in which the decorated function should be registered or None for the default registry
	:type registry: WTransformationRegistry | None

	:rtype: callable
	"""
	if registry is None:
		registry = __default_transformation_registry__

	def decorator_fn(decorated_function):
		registry.register_function(cls, WTransformationRegistry.RegFunctionType.compose_fn, decorated_function)

	return decorator_fn


@verify_type('strict', cls=(str, type), registry=(WTransformationRegistry, None))
@verify_value('strict', cls=lambda x: isinstance(x, type) or len(x) > 0)
def register_dismantler(cls, registry=None):
	""" Return a decorator that will register a function in a registry. This function will be used for an
	object dismantling

	:param cls: class that may be dismantled
	:type cls: str | type

	:param registry: registry in which the decorated function should be registered or None for the default registry
	:type registry: WTransformationRegistry | None

	:rtype: callable
	"""
	if registry is None:
		registry = __default_transformation_registry__

	def decorator_fn(decorated_function):
		registry.register_function(cls, WTransformationRegistry.RegFunctionType.dismantle_fn, decorated_function)

	return decorator_fn


@register_dismantler('dict')
@verify_type('strict', obj=dict)
def dict_dismantler(obj, registry):
	""" This function is used for the 'dict' dismantling
	"""
	return {registry.dismantle(k): registry.dismantle(v) for k, v in obj.items()}


@register_composer('dict')
@verify_type('strict', obj=dict)
def dict_composer(obj_dump, registry):
	""" This function is used for the 'dict' composition
	"""
	return {registry.compose(k): registry.compose(v) for k, v in obj_dump.items()}


@register_dismantler('set')
@verify_type('strict', obj=set)
def set_dismantler(obj, registry):
	""" This function is used for the 'set' dismantling
	"""
	return [registry.dismantle(x) for x in obj]


@register_composer('set')
@verify_type('strict', obj_dump=list)
def set_composer(obj_dump, registry):
	""" This function is used for the 'set' composition
	"""
	return set([registry.compose(x) for x in obj_dump])


@verify_type('strict', registry=(WTransformationRegistry, type, None), compose_fn=(str, None), dismantle_fn=(str, None))
def register_class(registry=None, compose_fn=None, dismantle_fn=None):
	""" Return a class decorator that will register its composition and dismantling functions in a registry.
	Composition and dismantling functions must be members of a class, so it is better to decorate them with
	'staticmethod'. 'classmethod' will also work, but this may have side effects.

	This decorator may be used without a call, in that case the first argument will be a class to decorate and
	default values of registry and functions names will be used

	:param registry: registry in which functions will be registered (default registry is used for the 'None' value)
	:type registry: WTransformationRegistry | type | None

	:param compose_fn: name of a composition function to use ("compose" by default)
	:type compose_fn: str | None

	:param dismantle_fn: name of a dismantling function to use ("dismantle" by default)
	:type dismantle_fn: str | None

	:rtype: callable | type
	"""

	def decorator_fn(cls, reg=None, c_fn=None, d_fn=None):
		if c_fn is None:
			c_fn = 'compose'
		if d_fn is None:
			d_fn = 'dismantle'

		try:
			register_composer(cls, registry=reg)(getattr(cls, c_fn))
			register_dismantler(cls, registry=reg)(getattr(cls, d_fn))
		except AttributeError:
			raise TypeError(
				'The wrapped class "%s" must have "compose" and "dismantle" methods' % cls.__name__
			)
		return cls

	if registry is not None and isinstance(registry, type):
		# decorator was specified for class but was not called with arguments
		return decorator_fn(registry, reg=__default_transformation_registry__)

	return functools.partial(decorator_fn, reg=registry, c_fn=compose_fn, d_fn=dismantle_fn)
