
import pytest
import threading

from wasp_general.atomic import WAtomicCounter


class TestWAtomicCounter:

	__threads__ = 50
	__repeats__ = 50

	def test(self):

		c = WAtomicCounter()
		assert(c.__int__() == 0)

		c.increase_counter(1)
		assert(c.__int__() == 1)

		c.increase_counter(10)
		assert(c.__int__() == 11)

		c = WAtomicCounter(5)
		assert(c.__int__() == 5)

		c.increase_counter(1)
		assert(c.__int__() == 6)

	def test_counter_maximum(self):
		u_long_long_bits_count = (8 * 8)

		WAtomicCounter((1 << u_long_long_bits_count) - 1)
		WAtomicCounter((1 << u_long_long_bits_count) + 10)

	def test_multi_threading(self):
		c = WAtomicCounter()

		def thread_fn_increase():
			for i in range(self.__repeats__):
				c.increase_counter(1)

		threads = [threading.Thread(target=thread_fn_increase) for x in range(self.__threads__)]
		for th in threads:
			th.start()

		for th in threads:
			th.join()

		assert(c.__int__() == (self.__threads__ * self.__repeats__))
