
import pytest
import threading
import functools
import gc

from wasp_general.thread import acquire_lock, critical_section_dynamic_lock, critical_section_lock, WCriticalResource
from wasp_general.thread import WCriticalSectionError


def test_acquire_lock():
	lock = threading.Lock()
	assert(acquire_lock(lock) is True)  # blocking mode - may wait forever
	assert(acquire_lock(lock, timeout=-1) is False)  # lock is already locked and non-blocking mode is used
	assert(acquire_lock(lock, timeout=1) is False)  # lock is already locked and blocking mode is used
	lock.release()
	assert(acquire_lock(lock, timeout=-1) is True)


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
		def increase(self, **kwargs):
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

	def test_exceptions(self):
		class A:
			@WCriticalResource.critical_section()
			def foo(self):
				pass
		with pytest.raises(TypeError):
			A().foo()


class TestWLockFreeContext:

	__threads__ = 50
	__repeats__ = 50

	def test(self):
		sr = TestWCriticalResource.SharedResource()
		assert(sr.counter == 0)

		def thread_fn_increase():
			for i in range(self.__repeats__):
				with sr.critical_context(timeout=1) as c:
					c.increase()

		threads = [threading.Thread(target=thread_fn_increase) for x in range(self.__threads__)]
		for th in threads:
			th.start()

		for th in threads:
			th.join()

		assert(sr.counter == (self.__threads__ * self.__repeats__))

		class A(WCriticalResource):
			@classmethod
			def foo(cls, i):
				return 2 * i

		a = A()
		with a.critical_context() as c:
			assert(c.foo(1) is 2)  # access to original attributes works still

	def test_exceptions(self):
		sr = TestWCriticalResource.SharedResource()
		c1 = sr.critical_context(timeout=1)

		with c1:
			pass  # this is ok
		with pytest.raises(WCriticalSectionError):
			with c1:
				with c1:  # there is no way to lock a context twice
					pass

		c2 = sr.critical_context(timeout=1)
		with c1:
			pass  # this is fine still
		with pytest.raises(WCriticalSectionError):
			with c1:
				with c2:  # there is no way to get in a critical section even from different contexts
					pass

		with c1:
			pass  # this doesn't do anything bad
		with pytest.raises(WCriticalSectionError):
			with c1:
				sr.increase()  # this won't work either

		c1.__enter__()  # the object is "locked"
		with pytest.raises(WCriticalSectionError):
			sr.increase()  # the object is locked definitely
		del c1
		gc.collect()
		sr.increase()  # the object was unlocked automatically

		with pytest.raises(WCriticalSectionError):
			_ = c2.increase  # access to a underlined methods are not allowed without a lock
