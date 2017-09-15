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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from threading import Lock
from decorator import decorator

from wasp_general.verify import verify_type, verify_value


class WCriticalSectionError(Exception):
	pass


@verify_type(blocking=bool, timeout=(int, float, None), raise_exception=bool)
@verify_value(lock_fn=lambda x: callable(x))
@verify_value(timeout=lambda x: x is None or x > 0)
def critical_section_dynamic_lock(lock_fn=None, blocking=True, timeout=None, raise_exception=True):

	if blocking is False or timeout is None:
		timeout = -1

	def first_level_decorator(decorated_function):
		def second_level_decorator(original_function, *args, **kwargs):
			lock = lock_fn(*args, **kwargs)
			if lock.acquire(blocking=blocking, timeout=timeout) is True:
				try:
					result = original_function(*args, **kwargs)
					return result
				finally:
					lock.release()
			elif raise_exception is True:
				WCriticalSectionError('Unable to lock critical section\n')

		return decorator(second_level_decorator)(decorated_function)
	return first_level_decorator


@verify_type('paranoid', lock=Lock().__class__, blocking=bool, timeout=(int, float, None), raise_exception=bool)
@verify_value('paranoid', timeout=lambda x: x is None or x > 0)
@verify_type(lock=Lock().__class__)
def critical_section_lock(lock=None, blocking=True, timeout=None, raise_exception=True):

	def lock_getter(*args, **kwargs):
		return lock

	return critical_section_dynamic_lock(
		lock_fn=lock_getter, blocking=blocking, timeout=timeout, raise_exception=raise_exception
	)


class WCriticalResource:

	def __init__(self):
		self.__lock = Lock()

	def thread_lock(self):
		return self.__lock

	@staticmethod
	@verify_type('paranoid', blocking=bool, timeout=(int, float, None), raise_exception=bool)
	@verify_value('paranoid', timeout=lambda x: x is None or x > 0)
	def critical_section(blocking=True, timeout=None, raise_exception=True):

		def lock_getter(self, *args, **kwargs):
			if isinstance(self, WCriticalResource) is False:
				raise TypeError(
					'Invalid object type. It must be inherited from WCriticalResource class and'
					' decorated method must be bounded'
				)
			return self.thread_lock()

		return critical_section_dynamic_lock(
			lock_fn=lock_getter, blocking=blocking, timeout=timeout, raise_exception=raise_exception
		)
