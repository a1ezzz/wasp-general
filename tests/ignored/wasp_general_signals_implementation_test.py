
import pytest
import threading
import gc
import time
import weakref

from wasp_general.signals.proto import WSignalSourceProto, WSignalReceiverProto

from wasp_general.atomic import WAtomicCounter

from wasp_general.signals.implementation import WSignalSourceProtoImplProto, WSignalConnectionMatrixProto
from wasp_general.signals.implementation import WROCounterReference, WLinkedSignalCounter, WSignalStorage
from wasp_general.signals.implementation import WSignalSource, WSignalConnectionMatrix


def test_abstract():

	class S(WSignalSourceProtoImplProto):

		def send_signal(self, signal):
			pass

		def signals(self):
			pass

		def connection_matrix(self):
			pass

		def signals_counters(self, *signals_names):
			pass

		def linked_counters(self, *signals_names):
			pass

		def source_counter(self):
			pass

	class R(WSignalReceiverProto):

		def receive_signal(self, signal, signal_source, signal_count):
			pass

	assert(issubclass(WSignalSourceProtoImplProto, WSignalSourceProto) is True)
	pytest.raises(TypeError, WSignalSourceProtoImplProto)
	pytest.raises(NotImplementedError, WSignalSourceProtoImplProto.signals_counters, None)
	pytest.raises(NotImplementedError, WSignalSourceProtoImplProto.linked_counters, None)
	pytest.raises(NotImplementedError, WSignalSourceProtoImplProto.source_counter, None)

	pytest.raises(TypeError, WSignalConnectionMatrixProto)
	pytest.raises(NotImplementedError, WSignalConnectionMatrixProto.connect, None, S(), '', R())
	pytest.raises(NotImplementedError, WSignalConnectionMatrixProto.disconnect, None, S(), '', R())


class TestWROCounterReference:

	def test(self):
		c = WAtomicCounter()
		ro_c = WROCounterReference(c)
		assert(ro_c.__int__() == 0)

		c.increase_counter(10)
		assert(ro_c.__int__() == 10)

		c = None
		gc.collect()
		assert(ro_c.__int__() is None)


class TestWLinkedSignalCounter:

	def test(self):
		c = WAtomicCounter(10)
		lc = WLinkedSignalCounter(c)
		assert(isinstance(lc, WAtomicCounter) is True)
		assert(isinstance(lc.original_counter(), WROCounterReference) is True)
		assert(lc.original_counter().__int__() == 10)
		assert(lc.__int__() == 10)

		c.increase_counter(1)
		assert(c.__int__() == 11)
		assert(lc.__int__() == 10)

		lc.increase_counter(1)
		assert(c.__int__() == 11)
		assert(lc.__int__() == 11)

		lc.increase_counter(1)
		assert(c.__int__() == 11)
		assert(lc.__int__() == 12)


class TestWSignalStorage:

	__signal1_name__ = 'signal1'
	__signal2_name__ = 'signal2'

	def test(self):
		s = WSignalStorage()
		assert(isinstance(s, WAtomicCounter) is True)
		pytest.raises(RuntimeError, s.increase_counter)

		assert(s.signals_names() == tuple())
		pytest.raises(ValueError, s.linked_counters, TestWSignalStorage.__signal1_name__)

		s = WSignalStorage(TestWSignalStorage.__signal1_name__, TestWSignalStorage.__signal2_name__)
		signals = s.signals_names()
		assert(len(signals) == 2)
		assert(TestWSignalStorage.__signal1_name__ in signals)
		assert(TestWSignalStorage.__signal2_name__ in signals)

		lc = s.linked_counters(TestWSignalStorage.__signal1_name__)
		assert(isinstance(lc, dict) is True)
		assert(len(lc) == 1)
		assert(isinstance(lc[TestWSignalStorage.__signal1_name__], WLinkedSignalCounter) is True)

		lc = s.linked_counters(TestWSignalStorage.__signal1_name__)
		assert(s.__int__() == 0)
		assert(lc[TestWSignalStorage.__signal1_name__].__int__() == 0)
		s.emit(TestWSignalStorage.__signal1_name__)
		assert(s.__int__() == 1)
		assert(lc[TestWSignalStorage.__signal1_name__].__int__() == 0)  # watcher did not commit a signal

		s_c = s.signals_counters(
			TestWSignalStorage.__signal1_name__, TestWSignalStorage.__signal2_name__
		)
		assert(
			s_c == {
				TestWSignalStorage.__signal1_name__: 1,
				TestWSignalStorage.__signal2_name__: 0
			}
		)


class TestWSignalSender:
	__test_counters__ = 50
	__emit_threads__ = 50
	__watch_threads__ = 50
	__sleep_timeout__ = 0.1

	class CMatrix(WSignalConnectionMatrixProto, WAtomicCounter):

		def __init__(self):
			WSignalConnectionMatrixProto.__init__(self)
			WAtomicCounter.__init__(self)
			self.connections = []

		def connect(self, signal_sender, signal_name, receiver):
			self.connections.append((signal_sender, signal_name, receiver))

		def disconnect(self, signal_sender, signal_name, receiver):
			self.connections.remove((signal_sender, signal_name, receiver))

	class Receiver(WSignalReceiverProto):

		def __init__(self):
			WSignalReceiverProto.__init__(self)
			self.counter = 0

		def receive_signal(self, signal, signal_source, signal_count):
			self.counter += signal_count

	def test(self):
		c_matrix = TestWSignalSender.CMatrix()
		s = WSignalSource(c_matrix, TestWSignalStorage.__signal1_name__, TestWSignalStorage.__signal2_name__)
		assert(isinstance(s, WSignalSourceProto) is True)
		assert(s.source_counter() == 0)
		assert(s.connection_matrix() == c_matrix)

		signals = s.signals()
		assert(len(signals) == 2)
		assert(TestWSignalStorage.__signal1_name__ in signals)
		assert(TestWSignalStorage.__signal2_name__ in signals)

		signals_counters = s.signals_counters()
		assert(signals_counters == dict())

		signals_counters = s.signals_counters(TestWSignalStorage.__signal1_name__)
		assert(
			signals_counters == {
				TestWSignalStorage.__signal1_name__: 0
			}
		)

		signals_counters = s.signals_counters(
			TestWSignalStorage.__signal1_name__, TestWSignalStorage.__signal2_name__
		)
		assert(
			signals_counters == {
				TestWSignalStorage.__signal1_name__: 0,
				TestWSignalStorage.__signal2_name__: 0
			}
		)

		pytest.raises(ValueError, s.send_signal, 'test')
		assert(s.source_counter() == 0)

		s.send_signal(TestWSignalStorage.__signal1_name__)
		assert(s.source_counter() == 1)

		signals_counters = s.signals_counters(
			TestWSignalStorage.__signal1_name__, TestWSignalStorage.__signal2_name__
		)
		assert(
			signals_counters == {
				TestWSignalStorage.__signal1_name__: 1,
				TestWSignalStorage.__signal2_name__: 0
			}
		)

		lc = s.linked_counters(TestWSignalStorage.__signal1_name__)
		assert(isinstance(lc, dict) is True)
		assert(len(lc) == 1)
		assert(isinstance(lc[TestWSignalStorage.__signal1_name__], WLinkedSignalCounter) is True)

		# r = TestWSignalSender.Receiver()
		# assert((s, TestWSignalStorage.__signal2_name__, r) not in c_matrix.connections)
		# s.connect(TestWSignalStorage.__signal2_name__, r)
		# assert((s, TestWSignalStorage.__signal2_name__, r) in c_matrix.connections)
		# s.disconnect(TestWSignalStorage.__signal2_name__, r)
		# assert((s, TestWSignalStorage.__signal2_name__, r) not in c_matrix.connections)

	def test_multi_threading(self):
		s = WSignalSource(
			TestWSignalSender.CMatrix(),
			TestWSignalStorage.__signal1_name__,
			TestWSignalStorage.__signal2_name__
		)
		lc = s.linked_counters(TestWSignalStorage.__signal1_name__)[TestWSignalStorage.__signal1_name__]
		assert(lc.__int__() == 0)

		total_calls = TestWSignalSender.__test_counters__ * TestWSignalSender.__emit_threads__

		test_status = {'stop_flag': False}

		def emit_fn():

			for i in range(TestWSignalSender.__test_counters__):
				s.send_signal(TestWSignalStorage.__signal1_name__)

		def watch_fn():

			def check_fn():

				# NOTE: In a real world an exception may be raised!

				current_value = lc.original_counter().__int__()

				while lc.__int__() < current_value:
					lc.increase_counter(current_value - lc.__int__())

			while test_status['stop_flag'] is False:
				check_fn()
				time.sleep(self.__sleep_timeout__)

			check_fn()

		emit_threads = [threading.Thread(target=emit_fn) for x in range(TestWSignalSender.__emit_threads__)]
		watch_threads = [threading.Thread(target=watch_fn) for x in range(TestWSignalSender.__watch_threads__)]

		for th in emit_threads:
			th.start()

		for th in watch_threads:
			th.start()

		for th in emit_threads:
			th.join()
		test_status['stop_flag'] = True

		for th in watch_threads:
			th.join()

		assert(s.source_counter() == total_calls)

		counters = s.signals_counters(TestWSignalStorage.__signal1_name__, TestWSignalStorage.__signal2_name__)
		assert(counters[TestWSignalStorage.__signal1_name__] == total_calls)
		assert(counters[TestWSignalStorage.__signal2_name__] == 0)
		assert(lc.__int__() == total_calls)


class TestWSignalConnectionMatrix:

	poll_timeout = 0.5

	class Receiver(WSignalReceiverProto):

		def __init__(self):
			WSignalReceiverProto.__init__(self)
			self.counter = WAtomicCounter()

		def receive_signal(self, signal, signal_source, signal_count):
			self.counter.increase_counter(signal_count)

	def test_cache(self):

		class A:
			pass

		a1 = A()

		c = WSignalConnectionMatrix.CacheEntries()
		assert(c.weak() is True)
		assert(c.cached_value == 0)
		assert(list(c.entries.items()) == [])
		assert(list(c.entries_items()) == [])
		assert(isinstance(c.entries, weakref.WeakKeyDictionary) is True)
		assert(isinstance(c.entries, dict) is False)

		c.entries[a1] = 0
		assert(list(c.entries.items()) == [(a1, 0)])

		e = c.entries_items()
		assert(list(e) == [(a1, 0)])

		c.entries.pop(a1)
		gc.collect()
		assert(list(e) == [])
		assert(list(c.entries.items()) == [])

		c = WSignalConnectionMatrix.CacheEntries(weak=False)
		assert(c.weak() is False)
		assert(c.cached_value == 0)
		assert(list(c.entries.items()) == [])
		assert(isinstance(c.entries, weakref.WeakKeyDictionary) is False)
		assert(isinstance(c.entries, dict) is True)

		c.entries[a1] = 0
		assert(list(c.entries.items()) == [(a1, 0)])

		e = c.entries_items()
		assert(list(e) == [(a1, 0)])

		c.entries.pop(a1)
		gc.collect()
		assert(list(e) == [(a1, 0)])
		assert(list(c.entries.items()) == [])

	def test(self):
		cm = WSignalConnectionMatrix()
		assert(cm.polling_timeout() == WSignalConnectionMatrix.__default_polling_timeout__)

		cm = WSignalConnectionMatrix(polling_timeout=TestWSignalConnectionMatrix.poll_timeout)
		assert(cm.polling_timeout() == TestWSignalConnectionMatrix.poll_timeout)
		assert(list(cm) == [])

		sender1 = WSignalSource(cm, 'signal1', 'signal2')
		sender2 = WSignalSource(cm, 'signal2', 'signal3')
		receiver1 = TestWSignalConnectionMatrix.Receiver()
		receiver2 = TestWSignalConnectionMatrix.Receiver()

		cm.connect(sender1, 'signal1', receiver1)
		cm.connect(sender2, 'signal2', receiver2)
		pytest.raises(ValueError, cm.connect, sender1, 'signal1', receiver1)

		assert(list(cm) == [])
		sender1.send_signal('signal1')
		assert(list(cm) == [(1, sender1, 'signal1', receiver1)])
		assert(list(cm) == [(1, sender1, 'signal1', receiver1)])
		assert(list(cm.__iter__(commit_changes=True)) == [(1, sender1, 'signal1', receiver1)])
		assert(list(cm) == [])
		assert(list(cm.__iter__(commit_changes=True)) == [])

		cm.disconnect(sender1, 'signal1', receiver1)
		pytest.raises(ValueError, cm.disconnect, sender1, 'signal1', receiver1)

		sender1.send_signal('signal1')
		assert(list(cm) == [])

		sender2.send_signal('signal2')
		assert(list(cm) == [(1, sender2, 'signal2', receiver2)])
		sender2.send_signal('signal2')
		assert(list(cm) == [(2, sender2, 'signal2', receiver2)])
		list(cm.__iter__(commit_changes=True))
		assert(list(cm) == [])

		assert(receiver1.counter.__int__() == 0)
		assert(receiver2.counter.__int__() == 0)

		sender1.send_signal('signal1')
		sender1.send_signal('signal1')
		sender1.send_signal('signal1')

		sender2.send_signal('signal2')
		sender2.send_signal('signal2')
		sender2.send_signal('signal2')

		cm.process_signals()

		assert(receiver1.counter.__int__() == 0)
		assert(receiver2.counter.__int__() == 3)

		worker = threading.Thread(target=cm.start)
		worker.start()

		sender1.send_signal('signal1')
		sender1.send_signal('signal1')

		sender2.send_signal('signal2')
		sender2.send_signal('signal2')

		time.sleep(TestWSignalConnectionMatrix.poll_timeout * 3)

		cm.stop()
		worker.join()

		assert(receiver1.counter.__int__() == 0)
		assert(receiver2.counter.__int__() == 5)

		assert(list(cm) == [])
		sender2.send_signal('signal2')
		assert(list(cm) == [(1, sender2, 'signal2', receiver2)])
		assert(list(cm) == [(1, sender2, 'signal2', receiver2)])

		sender2 = None
		gc.collect()
		assert(list(cm) == [])
