# -*- coding: utf-8 -*-
# wasp_general/thread.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

from functools import partial
from threading import Lock
from decorator import decorator

from wasp_general.verify import verify_type, verify_value


class WCriticalSectionError(Exception):
	""" An exception that may be raised if a lock for a critical section could not be acquire
	"""
	pass


@verify_type('strict', timeout=(int, float, None), lock=Lock().__class__)
@verify_value('strict', lock_fn=lambda x: callable(x))
def acquire_lock(lock, timeout=None):
	""" This function overload the original :meth:`.Lock.acquire` method that has two arguments ('blocking'
	and 'timeout') with the one argument only - 'timeout'. This argument may be set to None now

	:param lock: a lock that should be gained
	:type lock: Lock

	:param timeout: timeout that this function should wait in order to gain a lock. If the "timeout" is not
	specified (is None) then wait forever in a blocking mode till a lock is gained, if the "timeout" is a
	positive value this is a period of time in seconds that this function will wait for a lock in a blocking mode.
	If a non-positive value is set then this function will return immediately even if lock was not gained
	:type timeout: int | float | None

	:return: whether a specified lock is gained or not
	:rtype: bool
	"""
	if timeout is None:
		blocking = True
		timeout = -1
	elif timeout <= 0:
		blocking = False
		timeout = -1
	else:
		blocking = True
	return lock.acquire(blocking=blocking, timeout=timeout)


@verify_type('strict', timeout=(int, float, None), raise_exception=bool)
@verify_value('strict', lock_fn=lambda x: callable(x))
def critical_section_dynamic_lock(lock_fn, timeout=None, raise_exception=True):
	""" Protect a function with a lock, that was get from the specified function. If a lock can not be acquire, then
	no function call will be made

	:param lock_fn: callable that returns a lock, with which a function may be protected
	:type lock_fn: callable

	:param timeout: the same as 'timeout' in the :func:`.acquire_lock` function
	:type timeout: int | float | None

	:param raise_exception: whenever to raise an WCriticalSectionError exception if lock can not be acquired
	:type raise_exception: bool

	:return: decorator with which a target function may be protected
	"""

	def first_level_decorator(decorated_function):
		decorated_function.__lock_free_fn__ = decorated_function

		def second_level_decorator(original_function, *args, **kwargs):
			lock = lock_fn(*args, **kwargs)
			if acquire_lock(lock, timeout=timeout) is True:
				try:
					result = original_function(*args, **kwargs)
					return result
				finally:
					lock.release()
			elif raise_exception is True:
				raise WCriticalSectionError('Unable to lock a critical section')

		return decorator(second_level_decorator)(decorated_function)
	return first_level_decorator


@verify_type('paranoid', timeout=(int, float, None), raise_exception=bool)
@verify_type('strict', lock=Lock().__class__)
def critical_section_lock(lock=None, timeout=None, raise_exception=True):
	""" An a wrapper for :func:`.critical_section_dynamic_lock` function call, but with a static lock object
	instead of a function that returns a lock

	:param lock: lock with which a function will be protected
	:param timeout: the same as 'timeout' in the :func:`.critical_section_dynamic_lock` function
	:param raise_exception: same as raise_exception in :func:`.critical_section_dynamic_lock` function

	:return: decorator with which a target function may be protected
	"""

	def lock_getter(*args, **kwargs):
		return lock

	return critical_section_dynamic_lock(
		lock_fn=lock_getter, timeout=timeout, raise_exception=raise_exception
	)


class WCriticalResource:
	""" Class for simplifying thread safety for a shared object. Each class instance holds its own lock object
	that :meth:`.WCriticalResource.critical_section` method will be used to protect bounded methods.
	Bounded methods are allowed to be protected only. Static methods or class methods are unsupported
	"""

	def __init__(self):
		""" Create a lock
		"""
		self.__lock = Lock()

	def thread_lock(self):
		""" Return a lock with which a bounded methods may be protected

		:return: threading.Lock
		"""
		return self.__lock

	@verify_type('paranoid', timeout=(int, float, None))
	def critical_context(self, timeout=None):
		""" Create a lock free context for this object

		:param timeout: the same as 'timeout' in the :meth:`.WLockFreeContext.__init__` method
		:type timeout: int | float | None

		:rtype: WLockFreeContext
		"""
		return WLockFreeContext(self, timeout=timeout)

	@staticmethod
	@verify_type('paranoid', timeout=(int, float, None), raise_exception=bool)
	def critical_section(timeout=None, raise_exception=True):
		""" Decorate a method with a lock protection (class methods and static methods are unsupported)

		:param timeout: the same as 'timeout' in the :func:`.critical_section_dynamic_lock` function
		:type timeout: int | float | None

		:param raise_exception: the same as 'raise_exception' in the :func:`.critical_section_dynamic_lock`
		function
		:type raise_exception: bool

		:rtype: bounded method
		"""

		def lock_fn(self, *args, **kwargs):
			if isinstance(self, WCriticalResource) is False:
				raise TypeError(
					'Invalid object type. It must be inherited from WCriticalResource class and'
					' decorated method must be bounded'
				)
			return self.thread_lock()

		return critical_section_dynamic_lock(lock_fn=lock_fn, timeout=timeout, raise_exception=raise_exception)


class WLockFreeContext:
	""" This class may be used as a context that gets a monopoly access to a critical resource
	(an :class:`.WCriticalResource` object) and all the methods of that resource won't try to access already
	gained lock and won't cause a dead lock.

	:note: this object doesn't protect itself from a race condition. So this object usage must be limited to a
	single thread only
	"""

	@verify_type('strict', critical_resource=WCriticalResource, timeout=(int, float, None))
	def __init__(self, critical_resource, timeout=None):
		""" Create a new context object

		:param critical_resource: resource that this context should access and protect
		:type critical_resource: WCriticalResource

		:param timeout: the same as 'timeout' in the :func:`.acquire_lock` function
		:type timeout: int | float | None
		"""
		self.__resource = critical_resource
		self.__timeout = timeout
		self.__unlock = False

	def __getattr__(self, item):
		""" "Proxy" an access to an original resource. If the result is protected by a lock with
		:meth:`.WCriticalResource.critical_section` decorator then an original (lock free) method is returned

		:raise WCriticalSectionError: if a resource was not locked before this access

		:rtype: any
		"""
		if not self.__unlock:
			raise WCriticalSectionError(
				'A resource access error. A lock to the resource must be gotten at first!'
			)

		r_item = object.__getattribute__(self.__resource, item)

		try:
			return partial(r_item.__lock_free_fn__, r_item.__self__)
		except AttributeError:
			pass
		return r_item

	def __enter__(self):
		""" Enter this context and lock a resource

		:raise WCriticalSectionError: if a resource was not locked during a specified timeout

		:rtype: WLockFreeContext
		"""
		if not acquire_lock(self.__resource.thread_lock(), self.__timeout):
			raise WCriticalSectionError('Unable to lock a critical section')
		self.__unlock = True
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		""" Exit a context and release a lock
		"""
		if self.__unlock is True:
			self.__unlock = False
			self.__resource.thread_lock().release()

	def __del__(self):
		""" If a resource is locked still then unlock it
		"""
		if self.__unlock is True:
			self.__unlock = False
			self.__resource.thread_lock().release()
