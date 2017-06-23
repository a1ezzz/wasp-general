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

	@abstractmethod
	def put(self, result, decorated_function, *args, **kwargs):
		""" Save (or replace) result for given function

		:param result: result to be saved
		:param decorated_function: calling function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def has(self, decorated_function, *args, **kwargs):
		""" Check if there is a result for given function

		:param decorated_function: calling function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def get(self, decorated_function, *args, **kwargs):
		""" Get result from storage for specified function. Will raise an exception if there is no result.

		:param decorated_function: calling function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called
		:return: result (any type, even None)
		"""
		raise NotImplementedError('This method is abstract')


class WGlobalSingletonCacheStorage(WCacheStorage):
	""" Simple storage that acts as global singleton. Result (singleton) is saved on the first call. It doesn't
	matter with which parameters function was called, result will be the result from the first call.
	"""

	def __init__(self):
		""" Construct new storage
		"""
		self._storage = {}

	def put(self, result, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.put` method implementation
		"""
		self._storage[decorated_function] = result

	def has(self, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.has` method implementation
		"""
		return decorated_function in self._storage.keys()

	def get(self, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.get` method implementation
		"""
		return self._storage[decorated_function]


class WInstanceSingletonCacheStorage(WCacheStorage):
	""" This storage acts like :class:`.WGlobalSingletonCacheStorage` storage, but works with bounded methods only
	(class methods or object method). For every object it keeps the first result of called bounded method.

	For example. If we have two object derived from the same class, and the same method is called, then this
	storage will keep two separate results, one for each instance.

	This implementation uses weakrefs, so memory leak doesn't happen (here).
	"""

	def __init__(self):
		""" Construct new storage
		"""
		self._storage = {}

	def __check(self, decorated_function, *args, **kwargs):
		""" Check whether function is a bounded method or not. If check fails then exception is raised

		:param decorated_function: calling function (original)
		:param args: args with which function is called
		:param kwargs: kwargs with which function is called
		:return: None
		"""
		if len(args) >= 1:
			obj = args[0]
			function_name = decorated_function.__name__
			if hasattr(obj, function_name) is True:
				fn = getattr(obj, function_name)
				if callable(fn) and fn.__self__ == obj:
					return

		raise RuntimeError('Only bounded methods are allowed')

	def put(self, result, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.put` method implementation
		"""
		self.__check(decorated_function, *args, **kwargs)

		ref = weakref.ref(args[0])
		if decorated_function not in self._storage:
			self._storage[decorated_function] = [{'instance': ref, 'result': result}]
		else:
			found = False
			for i in self._storage[decorated_function]:
				if i['instance']() == args[0]:
					i['result'] = result
					found = True
					break
			if found is False:
				self._storage[decorated_function].append({'instance': ref, 'result': result})

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

	def has(self, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.has` method implementation
		"""
		self.__check(decorated_function, *args, **kwargs)

		if decorated_function in self._storage:
			for i in self._storage[decorated_function]:
				if i['instance']() == args[0]:
					return True
		return False

	def get(self, decorated_function, *args, **kwargs):
		""" :meth:`WCacheStorage.get` method implementation
		"""
		self.__check(decorated_function, *args, **kwargs)

		for i in self._storage[decorated_function]:
			if i['instance']() == args[0]:
				return i['result']
		raise RuntimeError('Result unavailable')


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
		def second_level_decorator(decorated_function_sl, *args, **kwargs):

			validator_check = validator(decorated_function_sl, *args, **kwargs)

			if validator_check is not True or storage.has(decorated_function_sl, *args, **kwargs) is False:
				result = decorated_function_sl(*args, **kwargs)
				storage.put(result, decorated_function_sl, *args, **kwargs)
				return result
			else:
				return storage.get(decorated_function_sl, *args, **kwargs)

		return decorator(second_level_decorator)(decorated_function)
	return first_level_decorator
