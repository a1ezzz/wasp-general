# -*- coding: utf-8 -*-

import pytest

from wasp_general.api.registry import WAPIRegistry
from wasp_general.api.transformation import WTransformationError, WTransformationRegistry
from wasp_general.api.transformation import __default_transformation_registry__, register_class


def test_exceptions():
	assert(issubclass(WTransformationError, Exception) is True)


class TestWTransformationRegistry:

	def test(self):
		registry = WTransformationRegistry()
		assert(isinstance(registry, WTransformationRegistry) is True)
		assert(isinstance(registry, WAPIRegistry) is True)

		assert(registry.dismantle(7) == 7)
		assert(registry.dismantle('foo') == 'foo')
		assert(registry.dismantle(None) is None)
		assert(registry.dismantle([1, 2, '3', 4]) == [1, 2, '3', 4])

		assert(registry.compose(7) == 7)
		assert(registry.compose('foo') == 'foo')
		assert(registry.compose(None) is None)
		assert(registry.compose([1, 2, '3', 4]) == [1, 2, '3', 4])

		class A:
			def __init__(self, i):
				self.i = i

			def __eq__(self, other):
				return self.i == other.i

		def a_compose(obj_dump, registry):
			return A(obj_dump)

		def a_dismantle(obj, registry):
			return obj.i

		registry.register_function(
			A, WTransformationRegistry.RegFunctionType.compose_fn, a_compose
		)

		registry.register_function(
			'A', WTransformationRegistry.RegFunctionType.dismantle_fn, a_dismantle
		)

		pytest.raises(NotImplementedError, registry.register, 'foo_id', lambda x, y: None)

		a = A(1)
		dismantled_a = registry.dismantle(a)
		assert(isinstance(dismantled_a, dict) is True)
		assert(WTransformationRegistry.__composer_hook_attr__ in dismantled_a)
		assert(WTransformationRegistry.__composer_dump_attr__ in dismantled_a)
		assert(registry.compose(dismantled_a) == a)

		dismantled_copy = dismantled_a.copy()
		dismantled_copy.pop(WTransformationRegistry.__composer_hook_attr__)
		pytest.raises(ValueError, registry.compose, dismantled_copy)

		dismantled_copy = dismantled_a.copy()
		dismantled_copy.pop(WTransformationRegistry.__composer_dump_attr__)
		pytest.raises(ValueError, registry.compose, dismantled_copy)

		pytest.raises(WTransformationError, __default_transformation_registry__.dismantle, a)
		pytest.raises(WTransformationError, __default_transformation_registry__.compose, dismantled_a)

	def test_default(self):
		assert(isinstance(__default_transformation_registry__, WTransformationRegistry) is True)

		registry = __default_transformation_registry__
		set_obj = {1, '2', 3, 4}
		composed_set = registry.compose(registry.dismantle(set_obj))
		assert(composed_set is not set_obj)
		assert(composed_set == set_obj)

		dict_obj = {
			'a': 'b',
			1: 1,
			'3': 3
		}
		composed_dict = registry.compose(registry.dismantle(dict_obj))
		assert(composed_dict is not dict_obj)
		assert(composed_dict == dict_obj)


@pytest.fixture
def default_registry_wrap(request):
	default_ids = set(__default_transformation_registry__.ids())

	def fin():
		registered_ids = set(__default_transformation_registry__.ids())
		for api_id in registered_ids.difference(default_ids):
			__default_transformation_registry__.unregister(api_id)

	request.addfinalizer(fin)


@pytest.mark.usefixtures('default_registry_wrap')
def test_class_decorator():

	class A:
		def __init__(self, i):
			self.i = i

		def __eq__(self, other):
			return self.i == other.i

	pytest.raises(WTransformationError, __default_transformation_registry__.dismantle, A(1))

	@register_class
	class B(A):
		@staticmethod
		def compose(obj_dump, registry):
			return B(obj_dump)

		@staticmethod
		def dismantle(obj, registry):
			return obj.i

	b = B(1)
	compiled_b = __default_transformation_registry__.compose(__default_transformation_registry__.dismantle(b))
	assert(b == compiled_b)

	@register_class()
	class C(A):
		@staticmethod
		def compose(obj_dump, registry):
			return C(obj_dump)

		@staticmethod
		def dismantle(obj, registry):
			return obj.i

	c = C(1)
	compiled_c = __default_transformation_registry__.compose(__default_transformation_registry__.dismantle(c))
	assert(c == compiled_c)

	with pytest.raises(TypeError):
		@register_class
		class D(A):
			@staticmethod
			def compose(obj_dump, registry):
				return D(obj_dump)

	with pytest.raises(TypeError):
		@register_class
		class E(A):
			@staticmethod
			def dismantle(obj, registry):
				return obj.i

	registry = WTransformationRegistry(fallback_registry=__default_transformation_registry__)

	@register_class(registry=registry, compose_fn='obj_compose', dismantle_fn='obj_dismantle')
	class F(A):
		@staticmethod
		def obj_compose(obj_dump, registry):
			return F(obj_dump)

		@staticmethod
		def obj_dismantle(obj, registry):
			return obj.i

	f = F(1)
	dismantled_f = registry.dismantle(f)
	compiled_f = registry.compose(dismantled_f)
	assert(f == compiled_f)

	pytest.raises(WTransformationError, __default_transformation_registry__.dismantle, f)
	pytest.raises(WTransformationError, __default_transformation_registry__.compose, dismantled_f)
