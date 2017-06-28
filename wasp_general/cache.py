# -*- coding: utf-8 -*-
# wasp_general/cache.py
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

import weakref
from decorator import decorator
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_value, verify_type


class WCacheStorage(metaclass=ABCMeta):
	""" Abstract class for cache storage
	"""

	class CacheMissedException(Exception):
		""" Exception is raised in :meth:`.WCacheStorage.get_result` and derived methods as an error for
		accessing cache record that doesn't exist
		"""
		pass

	class CacheEntry:
		""" Cache request result, is used in :meth:`.WCacheStorage.get_cache` to determine if there is a
		cached value and what that value is.
		"""

		@verify_type(has_value=bool)
		def __init__(self, has_value=False, cached_value=None):
			""" Create new request result

			:param has_value: defines whether there is a cached value (True) or not (False)
			:param cached_value: defines cached value, this parameter should be used only if
			has_value is True
			"""
			self.has_value = has_value
			self.cached_value = cached_value

	@abstractmethod
	@verify_value(decorated_function=lambda x: callable(x))
	def put(self, result, decorated_function, *args, **kwargs):
		""" Save (or replace) result for given function

		:param result: result to be saved
		:param decorated_function: called function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_value(decorated_function=lambda x: callable(x))
	def get_cache(self, decorated_function, *args, **kwargs):
		""" Get cache entry (:class:`.WCacheStorage.CacheEntry`) for the specified arguments

		:param decorated_function: called function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called

		:return: WCacheStorage.CacheEntry
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_value(decorated_function=lambda x: x is None or callable(x))
	def clear(self, decorated_function=None):
		""" Remove results from this storage

		:param decorated_function: if specified, then results will be removed for this function only

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@verify_value('paranoid', decorated_function=lambda x: callable(x))
	def has(self, decorated_function, *args, **kwargs):
		""" Check if there is a result for given function

		:param decorated_function: called function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called

		:return: None
		"""
		return self.get_cache(decorated_function, *args, **kwargs).has_value

	@verify_value('paranoid', decorated_function=lambda x: callable(x))
	def get_result(self, decorated_function, *args, **kwargs):
		""" Get result from storage for specified function. Will raise an exception
		(:class:`.WCacheStorage.CacheMissedException`) if there is no cached result.

		:param decorated_function: called function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called

		:return: (any type, even None)
		"""
		cache_entry = self.get_cache(decorated_function, *args, **kwargs)
		if cache_entry.has_value is False:
			raise WCacheStorage.CacheMissedException('No cache record found')
		return cache_entry.cached_value


class WGlobalSingletonCacheStorage(WCacheStorage):
	""" Simple storage that acts as global singleton. Result (singleton) is saved on the very first call. It doesn't
	matter with which parameters function was called, result will be the same for all the rest calls.
	"""

	def __init__(self):
		""" Construct new storage
		"""
		self._storage = {}

	@verify_value(decorated_function=lambda x: callable(x))
	def put(self, result, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.put` method implementation
		"""
		self._storage[decorated_function] = result

	@verify_value(decorated_function=lambda x: callable(x))
	def has(self, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.has` method implementation
		"""
		return decorated_function in self._storage.keys()

	@verify_value(decorated_function=lambda x: callable(x))
	def get_result(self, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.get_result` method implementation
		"""
		try:
			return self._storage[decorated_function]
		except KeyError:
			raise WCacheStorage.CacheMissedException('No cache record found')

	@verify_value('paranoid', decorated_function=lambda x: callable(x))
	def get_cache(self, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.get_cache` method implementation
		"""
		has_value = self.has(decorated_function, *args, **kwargs)
		cached_value = None
		if has_value is True:
			cached_value = self.get_result(decorated_function, *args, **kwargs)
		return WCacheStorage.CacheEntry(has_value=has_value, cached_value=cached_value)

	@verify_value(decorated_function=lambda x: x is None or callable(x))
	def clear(self, decorated_function=None):
		""" :meth:`WCacheStorage.clear` method implementation
		"""
		if decorated_function is not None and decorated_function in self._storage:
			self._storage.pop(decorated_function)
		else:
			self._storage.clear()


class WInstanceSingletonCacheStorage(WCacheStorage):
	""" This storage acts similar to :class:`.WGlobalSingletonCacheStorage` storage, but works with bounded
	methods only (class methods or object method). For every object it keeps results with "cache-record" class
	(:class:`.WInstanceSingletonCacheStorage.InstanceCacheRecord`), this class (is used by default) saves
	the very first result and returns it every time. For example, by default if we have two object derived
	from the same class, and the same method is called, then this storage will keep two separate results,
	one for each instance.

	Exact behaviour can be tweaked through :class:`.WInstanceSingletonCacheStorage.InstanceCacheRecord` inheritance.
	So derived "cache-records" classes can do things in there own way, they may save every called result, or may not
	save anything.

	This class was extended to support internal statistics with cache hits and misses. Still, this class is not
	thread safe, but accessing statistics from a separate thread should work. Statistics is calculated for
	records that was fetch through :meth:`WInstanceSingletonCacheStorage.get_cache` method only

	:note: This implementation uses weakrefs, so memory leak doesn't happen (here).
	"""

	class InstanceCacheRecord:
		""" Class is used to save cached results for the specified method and for the single instance. This
		class saves the very first result only. This class uses :class:`.WCacheStorage.CacheEntry` the same way
		as :class:`.WCacheStorage` storage does - it help to determine, whether there is a cached value or not.

		Because derived class constructor signature may differ from this class constructor signature, then
		in order to create cache record there should be a unified method, which is
		:meth:`.WInstanceSingletonCacheStorage.InstanceCacheRecord.create`
		"""

		@verify_value('paranoid', decorated_function=lambda x: callable(x))
		def __init__(self, result, decorated_function):
			""" Create new cache record

			:param result: result to keep
			:param decorated_function: called bounded method (original)
			"""
			self.__decorated_function = decorated_function
			self.__result = result

		def decorated_function(self):
			""" Return original method

			:return: bounded method
			"""
			return self.__decorated_function

		def cache_entry(self, *args, **kwargs):
			""" Return cache entry for the specified arguments

			:param args: args with which bounded method was called
			:param kwargs: kwargs with which bounded method was called

			:return: WCacheStorage.CacheEntry
			"""
			return WCacheStorage.CacheEntry(has_value=True, cached_value=self.__result)

		def update(self, result, *args, **kwargs):
			""" Update (or add other one) result, that was generated with specified arguments

			:param result: result to keep
			:param args: args with which bounded method was called
			:param kwargs: kwargs with which bounded method was called

			:return: None
			"""
			self.__result = result

		@classmethod
		@verify_value('paranoid', decorated_function=lambda x: callable(x))
		def create(cls, result, decorated_function, *args, **kwargs):
			""" Create new "cache-record" for the specified arguments

			:param result: result to keep
			:param decorated_function: called bounded method
			:param args: args with which bounded method was called
			:param kwargs: kwargs with which bounded method was called

			:return: WInstanceSingletonCacheStorage.InstanceCacheRecord
			"""
			return cls(result, decorated_function)

	@verify_type(statistic=bool)
	def __init__(self, cache_record_cls=None, statistic=False):
		""" Construct new storage

		:param cache_record_cls: class for keeping cache
		:param statistic: whether to store statistics about cache hits and misses or not
		"""
		self._storage = {}
		self._cache_record_cls = None
		if cache_record_cls is not None:
			if issubclass(cache_record_cls, WInstanceSingletonCacheStorage.InstanceCacheRecord) is False:
				raise TypeError('Invalid cache record class')
			self._cache_record_cls = cache_record_cls
		else:
			self._cache_record_cls = WInstanceSingletonCacheStorage.InstanceCacheRecord
		self.__statistic = statistic
		self.__cache_missed = 0 if self.__statistic is True else None
		self.__cache_hit = 0 if self.__statistic is True else None

	@verify_value('paranoid', decorated_function=lambda x: callable(x))
	def __check(self, decorated_function, *args, **kwargs):
		""" Check whether function is a bounded method or not. If check fails then exception is raised

		:param decorated_function: called function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called
		:return: None
		"""
		# TODO replace this function with decorator which can be turned off like verify_* does
		if len(args) >= 1:
			obj = args[0]
			function_name = decorated_function.__name__
			if hasattr(obj, function_name) is True:
				fn = getattr(obj, function_name)
				if callable(fn) and fn.__self__ == obj:
					return

		raise RuntimeError('Only bounded methods are allowed')

	@verify_value(decorated_function=lambda x: callable(x))
	def put(self, result, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.put` method implementation
		"""
		self.__check(decorated_function, *args, **kwargs)

		ref = weakref.ref(args[0])
		if decorated_function not in self._storage:
			cache_entry = self._cache_record_cls.create(result, decorated_function, *args, **kwargs)
			self._storage[decorated_function] = [{'instance': ref, 'result': cache_entry}]
		else:
			instance_found = False
			for i in self._storage[decorated_function]:
				if i['instance']() == args[0]:
					cache_entry = i['result']
					cache_entry.update(result, *args, **kwargs)
					instance_found = True
					break
			if instance_found is False:
				cache_entry = self._cache_record_cls.create(result, decorated_function, *args, **kwargs)
				self._storage[decorated_function].append({'instance': ref, 'result': cache_entry})

		def finalize_ref():
			if decorated_function in self._storage:
				fn_list = self._storage[decorated_function]
				if len(fn_list) == 1 and fn_list[0]['instance'] == ref:
					del self._storage[decorated_function]

				for i in range(len(fn_list)):
					if fn_list[i]['instance'] == ref:
						fn_list.pop(i)
						return

		weakref.finalize(args[0], finalize_ref)

	@verify_value(decorated_function=lambda x: callable(x))
	def get_cache(self, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.get_cache` method implementation
		"""
		self.__check(decorated_function, *args, **kwargs)
		if decorated_function in self._storage:
			for i in self._storage[decorated_function]:
				if i['instance']() == args[0]:
					result = i['result'].cache_entry(*args, **kwargs)
					if self.__statistic is True:
						if result.has_value is True:
							self.__cache_hit += 1
						else:
							self.__cache_missed += 1
					return result

		if self.__statistic is True:
			self.__cache_missed += 1

		return WCacheStorage.CacheEntry()

	@verify_value(decorated_function=lambda x: x is None or callable(x))
	def clear(self, decorated_function=None):
		""" :meth:`WCacheStorage.clear` method implementation (Clears statistics also)
		"""
		if decorated_function is not None and decorated_function in self._storage:
			self._storage.pop(decorated_function)
		else:
			self._storage.clear()

		if self.__statistic is True:
			self.__cache_missed = 0
			self.__cache_hit = 0

	def cache_missed(self):
		""" Return cache misses (return None if class was constructed without 'statistic' flag)

		:return: int or None
		"""
		return self.__cache_missed

	def cache_hit(self):
		""" Return cache hits (return None if class was constructed without 'statistic' flag)

		:return: int or None
		"""
		return self.__cache_hit


@verify_type(storage=(None, WCacheStorage))
@verify_value(validator=lambda x: x is None or callable(x))
def cache_control(validator=None, storage=None):
	""" Decorator that is used for caching result.

	:param validator: function, that has following signature (decorated_function, \*args, \*\*kwargs), where \
	decorated_function - original function, args - function arguments, kwargs - function keyword arguments. \
	This function must return True if cache is valid (old result must be use if it there is one), or False - to \
	generate and to store new result. So function that always return True can be used as singleton. And function \
	that always return False won't cache anything at all. By default (if no validator is specified), it presumes \
	that cache is always valid.
	:param storage: storage that is used for caching results. see :class:`.WCacheStorage` class.

	:return: decorated function
	"""

	def default_validator(*args, **kwargs):
		return True

	if validator is None:
		validator = default_validator

	if storage is None:
		storage = WGlobalSingletonCacheStorage()

	def first_level_decorator(decorated_function):
		def second_level_decorator(original_function, *args, **kwargs):

			validator_check = validator(original_function, *args, **kwargs)
			cache_entry = storage.get_cache(original_function, *args, **kwargs)

			if validator_check is not True or cache_entry.has_value is False:
				result = original_function(*args, **kwargs)
				storage.put(result, original_function, *args, **kwargs)
				return result
			else:
				return cache_entry.cached_value

		return decorator(second_level_decorator)(decorated_function)
	return first_level_decorator
