# -*- coding: utf-8 -*-

import pytest

from wasp_general.cache import WCacheStorage, WGlobalSingletonCacheStorage, WInstanceSingletonCacheStorage
from wasp_general.cache import cache_control


class TestWCacheStorage:

	def test_storage(self):
		pytest.raises(TypeError, WCacheStorage)
		pytest.raises(NotImplementedError, WCacheStorage.put, None, None, None)
		pytest.raises(NotImplementedError, WCacheStorage.has, None, None)
		pytest.raises(NotImplementedError, WCacheStorage.get, None, None)

		def foo():
			pass

		def bar():
			pass

		global_singleton_storage = WGlobalSingletonCacheStorage()
		pytest.raises(KeyError, global_singleton_storage.get, foo)
		assert(global_singleton_storage.has(foo) is False)
		assert(global_singleton_storage.has(foo, 1, k=2) is False)
		assert(global_singleton_storage.has(bar) is False)
		assert(global_singleton_storage.has(bar, 2, m='s') is False)

		global_singleton_storage.put(4, foo)
		assert(global_singleton_storage.has(foo) is True)
		assert(global_singleton_storage.get(foo) == 4)
		assert(global_singleton_storage.has(foo, 1, k=2) is True)
		assert(global_singleton_storage.get(foo, 1, k=2) == 4)
		assert(global_singleton_storage.has(bar) is False)
		assert(global_singleton_storage.has(bar, 2, m='s') is False)

		global_singleton_storage.put('q', bar, 7, l=8)
		assert(global_singleton_storage.has(bar) is True)
		assert(global_singleton_storage.get(bar) == 'q')
		assert(global_singleton_storage.has(bar, 2, m='s') is True)
		assert(global_singleton_storage.get(bar, 2, m='s') == 'q')

		global_singleton_storage.put('z', bar)
		assert(global_singleton_storage.get(bar) == 'z')
		assert(global_singleton_storage.get(bar, 2, m='s') == 'z')

		instance_singleton_storage = WInstanceSingletonCacheStorage()
		pytest.raises(RuntimeError, instance_singleton_storage.put, 1, foo)
		pytest.raises(RuntimeError, instance_singleton_storage.has, foo)
		pytest.raises(RuntimeError, instance_singleton_storage.get, foo)

		class A:
			def foo(self):
				pass

			def bar(self):
				pass

		a1 = A()
		a2 = A()
		a3 = A()

		pytest.raises(KeyError, instance_singleton_storage.get, A.foo, a1)
		assert(instance_singleton_storage.has(A.foo, a1) is False)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.foo, a1, 1, k=2) is False)
		assert(instance_singleton_storage.has(A.foo, a2, 1, k=2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is False)
		assert(instance_singleton_storage.has(A.bar, a2) is False)
		assert(instance_singleton_storage.has(A.bar, a1, m='s') is False)
		assert(instance_singleton_storage.has(A.bar, a2, m='s') is False)

		instance_singleton_storage.put(8, A.foo, a1)
		assert(instance_singleton_storage.has(A.foo, a1) is True)
		assert(instance_singleton_storage.get(A.foo, a1) == 8)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.foo, a1, 1, k=2) is True)
		assert(instance_singleton_storage.get(A.foo, a1, 1, k=2) == 8)
		assert(instance_singleton_storage.has(A.foo, a2, 1, k=2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is False)
		assert(instance_singleton_storage.has(A.bar, a2) is False)
		assert(instance_singleton_storage.has(A.bar, a1, m='s') is False)
		assert(instance_singleton_storage.has(A.bar, a2, m='s') is False)

		instance_singleton_storage.put(18, A.bar, a2, k=9)
		assert(instance_singleton_storage.has(A.foo, a1) is True)
		assert(instance_singleton_storage.get(A.foo, a1) == 8)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.foo, a1, 1, k=2) is True)
		assert(instance_singleton_storage.get(A.foo, a1, 1, k=2) == 8)
		assert(instance_singleton_storage.has(A.foo, a2, 1, k=2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is False)
		assert(instance_singleton_storage.has(A.bar, a2) is True)
		assert(instance_singleton_storage.get(A.bar, a2) == 18)
		assert(instance_singleton_storage.has(A.bar, a1, m='s') is False)
		assert(instance_singleton_storage.has(A.bar, a2, m='s') is True)
		assert(instance_singleton_storage.get(A.bar, a2, m='s') == 18)

		instance_singleton_storage.put(7, A.bar, a1, q=5)
		assert(instance_singleton_storage.has(A.foo, a1) is True)
		assert(instance_singleton_storage.get(A.foo, a1) == 8)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.foo, a1, 1, k=2) is True)
		assert(instance_singleton_storage.get(A.foo, a1, 1, k=2) == 8)
		assert(instance_singleton_storage.has(A.foo, a2, 1, k=2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is True)
		assert(instance_singleton_storage.get(A.bar, a1) == 7)
		assert(instance_singleton_storage.has(A.bar, a2) is True)
		assert(instance_singleton_storage.get(A.bar, a2) == 18)
		assert(instance_singleton_storage.has(A.bar, a1, m='s') is True)
		assert(instance_singleton_storage.get(A.bar, a1, m='s') == 7)
		assert(instance_singleton_storage.has(A.bar, a2, m='s') is True)
		assert(instance_singleton_storage.get(A.bar, a2, m='s') == 18)

		instance_singleton_storage.put('d', A.bar, a2)
		assert(instance_singleton_storage.get(A.bar, a2) == 'd')
		assert(instance_singleton_storage.get(A.bar, a2, m='s') == 'd')

		pytest.raises(RuntimeError, instance_singleton_storage.get, A.foo, a3)


def test_cache_control():

	def foo(a, b=None):
		return a + (0 if b is None else b)

	validator_trigger = True

	def validator(fn, *args, **kwargs):
		return validator_trigger

	decorated_foo = cache_control()(foo)
	assert(decorated_foo(1, b=2) == 3)
	assert(decorated_foo(1, b=5) == 3)
	assert(decorated_foo(7) == 3)

	decorated_foo = cache_control(validator=validator)(foo)
	assert(decorated_foo(8) == 8)
	assert(decorated_foo(1, b=2) == 8)
	assert(decorated_foo(1, b=5) == 8)
	assert(decorated_foo(7) == 8)

	validator_trigger = False
	assert(decorated_foo(1, b=2) == 3)
	assert(decorated_foo(1, b=5) == 6)
	assert(decorated_foo(7) == 7)

	validator_trigger = True
	assert(decorated_foo(1, b=2) == 7)
	assert(decorated_foo(1, b=5) == 7)
