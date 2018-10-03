
import pytest
import threading
import functools

from wasp_general.thread import critical_section_dynamic_lock, critical_section_lock, WCriticalResource
from wasp_general.thread import WCriticalSectionError


def test_critical_section():

	test_vars = {
		'lock': threading.Lock(),
		'counter': 0,
		'threads': 50,
		'increments': 50
	}

	def lock_getter():
		return test_vars['lock']

	def shared_counter_fn():
		for i in range(test_vars['increments']):
			test_vars['counter'] += 1

	lock_decorators = [
		functools.partial(critical_section_dynamic_lock, lock_fn=lock_getter),
		functools.partial(critical_section_lock, test_vars['lock'])
	]

	for l_d in lock_decorators:

		test_vars['counter'] = 0

		thread_safe_fn = l_d()(shared_counter_fn)

		threads = [threading.Thread(target=thread_safe_fn) for x in range(test_vars['threads'])]
		for th in threads:
			th.start()

		for th in threads:
			th.join()

		assert(test_vars['counter'] == (test_vars['threads'] * test_vars['increments']))

		thread_safe_fn = l_d(timeout=5)(shared_counter_fn)
		test_vars['lock'].acquire()
		pytest.raises(WCriticalSectionError, thread_safe_fn)
		assert(test_vars['counter'] == (test_vars['threads'] * test_vars['increments']))

		thread_safe_fn = l_d(timeout=5, raise_exception=False)(shared_counter_fn)
		thread_safe_fn()
		assert(test_vars['counter'] == (test_vars['threads'] * test_vars['increments']))

		test_vars['lock'].release()


class TestWCriticalResource:

	__threads__ = 50
	__repeats__ = 50

	class SharedResource(WCriticalResource):

		__lock_acquiring_timeout__ = 5

		def __init__(self):
			WCriticalResource.__init__(self)
			self.counter = 0

		@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
		def increase(self):
			self.counter += 1

	def test(self):
		sr = TestWCriticalResource.SharedResource()
		assert(sr.counter == 0)

		def thread_fn_increase():
			for i in range(self.__repeats__):
				sr.increase()

		threads = [threading.Thread(target=thread_fn_increase) for x in range(self.__threads__)]
		for th in threads:
			th.start()

		for th in threads:
			th.join()

		assert(sr.counter == (self.__threads__ * self.__repeats__))

#
# class TestWAtomicCounter:
#
# 	__threads__ = 50
# 	__repeats__ = 50
#
# 	def test(self):
#
# 		c = WAtomicCounter()
# 		assert(c.__int__() == 0)
#
# 		c.increase_counter()
# 		assert(c.__int__() == 1)
#
# 		c.increase_counter(delta=10)
# 		assert(c.__int__() == 11)
#
# 		c = WAtomicCounter(5)
# 		assert(c.__int__() == 5)
#
# 		c.increase_counter()
# 		assert(c.__int__() == 6)
#
# 	def test_counter_maximum(self):
# 		bits_count = (8 * 8) - 1
# 		# TODO switch to "(8 * 8)" after the moment when AtomicULongLong will be available
#
# 		c = WAtomicCounter((1 << bits_count) - 1)
# 		pytest.raises(OverflowError, WAtomicCounter, 1 << bits_count)
#
# 	def test_multi_threading(self):
# 		c = WAtomicCounter()
#
# 		def thread_fn_increase():
# 			for i in range(self.__repeats__):
# 				c.increase_counter()
#
# 		threads = [threading.Thread(target=thread_fn_increase) for x in range(self.__threads__)]
# 		for th in threads:
# 			th.start()
#
# 		for th in threads:
# 			th.join()
#
# 		assert(c.__int__() == (self.__threads__ * self.__repeats__))
