# -*- coding: utf-8 -*-

import pytest

from wasp_general.cache import WCacheStorage, WGlobalSingletonCacheStorage, WInstanceSingletonCacheStorage
from wasp_general.cache import cache_control


class TestWCacheStorage:

	@staticmethod
	def foo():
		pass

	@staticmethod
	def bar():
		pass

	def test(self):

		assert(issubclass(WCacheStorage.CacheMissedException, Exception) is True)

		cache_entry = WCacheStorage.CacheEntry()
		assert(cache_entry.has_value is False)
		assert(cache_entry.cached_value is None)

		cache_entry = WCacheStorage.CacheEntry(has_value=True, cached_value=1)
		assert(cache_entry.has_value is True)
		assert(cache_entry.cached_value == 1)

		foo = TestWCacheStorage.foo

		pytest.raises(TypeError, WCacheStorage)
		pytest.raises(NotImplementedError, WCacheStorage.put, None, None, foo)
		pytest.raises(NotImplementedError, WCacheStorage.clear, None, None)
		pytest.raises(NotImplementedError, WCacheStorage.get_cache, None, foo)

		class Storage(WCacheStorage):

			__cache_value__ = WCacheStorage.CacheEntry(has_value=True, cached_value='zzz')

			def put(self, result, decorated_function, *args, **kwargs):
				pass

			def clear(self, decorated_function=None):
				pass

			def get_cache(self, decorated_function, *args, **kwargs):
				return self.__cache_value__

		storage = Storage()
		assert(storage.has(foo) is True)
		assert(storage.get_result(foo) == 'zzz')

		storage.__cache_value__ = WCacheStorage.CacheEntry()
		assert(storage.has(foo) is False)
		pytest.raises(WCacheStorage.CacheMissedException, storage.get_result, foo)


class TestWGlobalSingletonCacheStorage:

	def test(self):
		foo = TestWCacheStorage.foo
		bar = TestWCacheStorage.bar

		global_singleton_storage = WGlobalSingletonCacheStorage()
		pytest.raises(WCacheStorage.CacheMissedException, global_singleton_storage.get_result, foo)
		assert(global_singleton_storage.has(foo) is False)
		assert(global_singleton_storage.has(foo, 1, k=2) is False)
		assert(global_singleton_storage.has(bar) is False)
		assert(global_singleton_storage.has(bar, 2, m='s') is False)

		global_singleton_storage.put(4, foo)
		assert(global_singleton_storage.has(foo) is True)
		assert(global_singleton_storage.get_result(foo) == 4)
		assert(global_singleton_storage.has(foo, 1, k=2) is True)
		assert(global_singleton_storage.get_result(foo, 1, k=2) == 4)
		assert(global_singleton_storage.has(bar) is False)
		assert(global_singleton_storage.has(bar, 2, m='s') is False)

		global_singleton_storage.put('q', bar, 7, l=8)
		assert(global_singleton_storage.has(bar) is True)
		assert(global_singleton_storage.get_result(bar) == 'q')
		assert(global_singleton_storage.has(bar, 2, m='s') is True)
		assert(global_singleton_storage.get_result(bar, 2, m='s') == 'q')

		global_singleton_storage.put('z', bar)
		assert(global_singleton_storage.get_result(bar) == 'z')
		assert(global_singleton_storage.get_result(bar, 2, m='s') == 'z')

		global_singleton_storage.clear(bar)
		assert(global_singleton_storage.has(foo) is True)
		assert(global_singleton_storage.get_result(foo) == 4)
		assert(global_singleton_storage.has(foo, 1, k=2) is True)
		assert(global_singleton_storage.get_result(foo, 1, k=2) == 4)
		assert(global_singleton_storage.has(bar) is False)
		assert(global_singleton_storage.has(bar, 2, m='s') is False)

		global_singleton_storage.clear()
		assert(global_singleton_storage.has(foo) is False)
		assert(global_singleton_storage.has(foo, 1, k=2) is False)
		assert(global_singleton_storage.has(bar) is False)
		assert(global_singleton_storage.has(bar, 2, m='s') is False)


class TestWInstanceSingletonCacheStorage:

	def test_cache_record(self):
		foo = TestWCacheStorage.foo

		cache_record = WInstanceSingletonCacheStorage.InstanceCacheRecord('qaz', foo)
		assert(cache_record.decorated_function() == foo)
		cache_entry = cache_record.cache_entry()
		assert(isinstance(cache_entry, WCacheStorage.CacheEntry) is True)
		assert(cache_entry.has_value is True)
		assert(cache_entry.cached_value == 'qaz')

		cache_record.update('wsx')
		assert(cache_record.cache_entry().cached_value == 'wsx')

		cache_record = WInstanceSingletonCacheStorage.InstanceCacheRecord.create('zxc', foo)
		assert(isinstance(cache_record, WInstanceSingletonCacheStorage.InstanceCacheRecord) is True)
		assert(cache_record.cache_entry().has_value is True)
		assert(cache_record.cache_entry().cached_value == 'zxc')

	def test(self):
		foo = TestWCacheStorage.foo

		instance_singleton_storage = WInstanceSingletonCacheStorage()
		pytest.raises(RuntimeError, instance_singleton_storage.put, 1, foo)
		pytest.raises(RuntimeError, instance_singleton_storage.has, foo)
		pytest.raises(RuntimeError, instance_singleton_storage.get_result, foo)

		class A:
			def foo(self):
				pass

			def bar(self):
				pass

		a1 = A()
		a2 = A()
		a3 = A()

		pytest.raises(WCacheStorage.CacheMissedException, instance_singleton_storage.get_result, A.foo, a1)
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
		assert(instance_singleton_storage.get_result(A.foo, a1) == 8)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.foo, a1, 1, k=2) is True)
		assert(instance_singleton_storage.get_result(A.foo, a1, 1, k=2) == 8)
		assert(instance_singleton_storage.has(A.foo, a2, 1, k=2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is False)
		assert(instance_singleton_storage.has(A.bar, a2) is False)
		assert(instance_singleton_storage.has(A.bar, a1, m='s') is False)
		assert(instance_singleton_storage.has(A.bar, a2, m='s') is False)

		instance_singleton_storage.put(18, A.bar, a2, k=9)
		assert(instance_singleton_storage.has(A.foo, a1) is True)
		assert(instance_singleton_storage.get_result(A.foo, a1) == 8)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.foo, a1, 1, k=2) is True)
		assert(instance_singleton_storage.get_result(A.foo, a1, 1, k=2) == 8)
		assert(instance_singleton_storage.has(A.foo, a2, 1, k=2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is False)
		assert(instance_singleton_storage.has(A.bar, a2) is True)
		assert(instance_singleton_storage.get_result(A.bar, a2) == 18)
		assert(instance_singleton_storage.has(A.bar, a1, m='s') is False)
		assert(instance_singleton_storage.has(A.bar, a2, m='s') is True)
		assert(instance_singleton_storage.get_result(A.bar, a2, m='s') == 18)

		instance_singleton_storage.put(7, A.bar, a1, q=5)
		assert(instance_singleton_storage.has(A.foo, a1) is True)
		assert(instance_singleton_storage.get_result(A.foo, a1) == 8)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.foo, a1, 1, k=2) is True)
		assert(instance_singleton_storage.get_result(A.foo, a1, 1, k=2) == 8)
		assert(instance_singleton_storage.has(A.foo, a2, 1, k=2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is True)
		assert(instance_singleton_storage.get_result(A.bar, a1) == 7)
		assert(instance_singleton_storage.has(A.bar, a2) is True)
		assert(instance_singleton_storage.get_result(A.bar, a2) == 18)
		assert(instance_singleton_storage.has(A.bar, a1, m='s') is True)
		assert(instance_singleton_storage.get_result(A.bar, a1, m='s') == 7)
		assert(instance_singleton_storage.has(A.bar, a2, m='s') is True)
		assert(instance_singleton_storage.get_result(A.bar, a2, m='s') == 18)

		instance_singleton_storage.put('d', A.bar, a2)
		assert(instance_singleton_storage.get_result(A.bar, a2) == 'd')
		assert(instance_singleton_storage.get_result(A.bar, a2, m='s') == 'd')

		instance_singleton_storage.clear(decorated_function=A.bar)
		assert(instance_singleton_storage.has(A.foo, a1) is True)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is False)
		assert(instance_singleton_storage.has(A.bar, a2) is False)

		instance_singleton_storage.clear()
		assert(instance_singleton_storage.has(A.foo, a1) is False)
		assert(instance_singleton_storage.has(A.foo, a2) is False)
		assert(instance_singleton_storage.has(A.bar, a1) is False)
		assert(instance_singleton_storage.has(A.bar, a2) is False)

		pytest.raises(WCacheStorage.CacheMissedException, instance_singleton_storage.get_result, A.foo, a3)

		class DummyCacheRecord(WInstanceSingletonCacheStorage.InstanceCacheRecord):

			def cache_entry(self, *args, **kwargs):
				return WCacheStorage.CacheEntry()

		pytest.raises(TypeError, WInstanceSingletonCacheStorage, cache_record_cls=A)
		instance_singleton_storage = WInstanceSingletonCacheStorage(cache_record_cls=DummyCacheRecord)

		instance_singleton_storage.put('d', A.bar, a2)
		assert(instance_singleton_storage.has(A.bar, a2) is False)

	def test_get_cache(self):

		class A:
			def foo(self):
				pass

		a1 = A()
		a2 = A()
		a3 = A()

		instance_singleton_storage = WInstanceSingletonCacheStorage()
		assert(instance_singleton_storage.cache_hit() is None)
		assert(instance_singleton_storage.cache_missed() is None)

		assert(instance_singleton_storage.get_cache(A.foo, a1).has_value is False)
		assert(instance_singleton_storage.cache_hit() is None)
		assert(instance_singleton_storage.cache_missed() is None)

		instance_singleton_storage.put(1, A.foo, a1)
		assert(instance_singleton_storage.get_cache(A.foo, a1).has_value is True)
		assert(instance_singleton_storage.cache_hit() is None)
		assert(instance_singleton_storage.cache_missed() is None)

		instance_singleton_storage = WInstanceSingletonCacheStorage(statistic=True)
		assert(instance_singleton_storage.cache_hit() == 0)
		assert(instance_singleton_storage.cache_missed() == 0)

		assert(instance_singleton_storage.get_cache(A.foo, a1).has_value is False)
		assert(instance_singleton_storage.cache_hit() == 0)
		assert(instance_singleton_storage.cache_missed() == 1)

		assert(instance_singleton_storage.get_cache(A.foo, a2).has_value is False)
		assert(instance_singleton_storage.cache_hit() == 0)
		assert(instance_singleton_storage.cache_missed() == 2)

		instance_singleton_storage.put(1, A.foo, a1)
		assert(instance_singleton_storage.get_cache(A.foo, a1).has_value is True)
		assert(instance_singleton_storage.cache_hit() == 1)
		assert(instance_singleton_storage.cache_missed() == 2)

		assert(instance_singleton_storage.get_cache(A.foo, a3).has_value is False)
		assert(instance_singleton_storage.cache_hit() == 1)
		assert(instance_singleton_storage.cache_missed() == 3)

		instance_singleton_storage.put(1, A.foo, a3)
		assert(instance_singleton_storage.get_cache(A.foo, a3).has_value is True)
		assert(instance_singleton_storage.cache_hit() == 2)
		assert(instance_singleton_storage.cache_missed() == 3)

		assert(instance_singleton_storage.get_cache(A.foo, a3).has_value is True)
		assert(instance_singleton_storage.cache_hit() == 3)
		assert(instance_singleton_storage.cache_missed() == 3)

		assert(instance_singleton_storage.get_cache(A.foo, a3).has_value is True)
		assert(instance_singleton_storage.cache_hit() == 4)
		assert(instance_singleton_storage.cache_missed() == 3)

		instance_singleton_storage.clear()
		assert(instance_singleton_storage.cache_hit() == 0)
		assert(instance_singleton_storage.cache_missed() == 0)

		assert(instance_singleton_storage.get_cache(A.foo, a3).has_value is False)
		assert(instance_singleton_storage.cache_hit() == 0)
		assert(instance_singleton_storage.cache_missed() == 1)

		class DummyCacheRecord(WInstanceSingletonCacheStorage.InstanceCacheRecord):

			def cache_entry(self, *args, **kwargs):
				return WCacheStorage.CacheEntry()

		instance_singleton_storage = WInstanceSingletonCacheStorage(
			cache_record_cls=DummyCacheRecord, statistic=True
		)
		assert(instance_singleton_storage.cache_hit() == 0)
		assert(instance_singleton_storage.cache_missed() == 0)

		instance_singleton_storage.put(1, A.foo, a1)
		assert(instance_singleton_storage.get_cache(A.foo, a1).has_value is False)
		assert(instance_singleton_storage.cache_hit() == 0)
		assert(instance_singleton_storage.cache_missed() == 1)

		assert(instance_singleton_storage.get_cache(A.foo, a2).has_value is False)
		assert(instance_singleton_storage.cache_hit() == 0)
		assert(instance_singleton_storage.cache_missed() == 2)


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
