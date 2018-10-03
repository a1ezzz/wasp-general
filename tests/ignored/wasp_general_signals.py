
import pytest
from blinker import signal
from time import time
import resource

from wasp_general.atomic import WAtomicCounter
from wasp_general.signals import WSignalReceiverProto, WSignalSourceProto, WSignalConnectionMatrix, WSignalSource
from wasp_general.signals import WSignalConnectionMatrixProto

from threading import Thread


class CheckSignalReceiver(WSignalReceiverProto):

	__lock_acquiring_timeout__ = 5

	def __init__(self):
		WSignalReceiverProto.__init__(self)
		self.counter = WAtomicCounter()

	def receive_signal(self, signal, signal_source, signal_count):
		self.counter.increase_counter(signal_count)

	def __call__(self, *args, **kwargs):
		self.receive_signal(None, None, 1)


class CheckBlinkerConnectionMatrix(WSignalConnectionMatrixProto):

	@classmethod
	def connect(cls, signal_sender, signal_name, receiver):
		signal(signal_name).connect(receiver, sender=signal_sender)

	@classmethod
	def disconnect(cls, signal_sender, signal_name, receiver):
		signal(signal_name).disconnect(receiver)


class CheckBlinkerSignalSender(WSignalSourceProto):

	def send_signal(self, signal_name):
		signal(signal_name).send(self)

	def signals(self):
		pass

	def connection_matrix(self):
		return CheckBlinkerConnectionMatrix


__test_environment__ = {
	'senders_count': 20,
	'recv_count': 20,
	'sends_count': 20,
	'signals_names': [('test_signal_%i' % x) for x in range(20)],

	'blinker_senders_impl': [],
	'wasp_senders_impl': [],

	'connection_matrix_one': WSignalConnectionMatrix(),
	'connection_matrix_two': WSignalConnectionMatrix()
}

__test_environment__['blinker_senders_impl'].extend([
	CheckBlinkerSignalSender() for x in range(__test_environment__['senders_count'])
])

__test_environment__['wasp_senders_impl'].extend([
	WSignalSource(
		__test_environment__['connection_matrix_one'],
		*__test_environment__['signals_names']
	) for x in range(int(__test_environment__['senders_count'] / 2))
])

__test_environment__['wasp_senders_impl'].extend([
	WSignalSource(
		__test_environment__['connection_matrix_two'],
		*__test_environment__['signals_names']
	) for x in range(int(__test_environment__['senders_count'] / 2))
])


class TestSignals:

	__implementations__ = [
		(
			__test_environment__['blinker_senders_impl'],
			False,
			"blinker"
		),
		(
			__test_environment__['wasp_senders_impl'],
			True,
			"wasp"
		),
		(
			__test_environment__['blinker_senders_impl'],
			False,
			"blinker"
		),
		(
			__test_environment__['wasp_senders_impl'],
			True,
			"wasp"
		)

	]

	@pytest.mark.parametrize("senders, use_con_matrix, impl_name", __implementations__)
	def test(self, senders, use_con_matrix, impl_name):

		receivers = []

		for i in range(__test_environment__['recv_count']):
			r = CheckSignalReceiver()
			for s in senders:
				for signal_name in __test_environment__['signals_names']:
					con_matrix = s.connection_matrix()
					con_matrix.connect(s, signal_name, r)
				receivers.append(r)

		def send_signals_fn():
			for i in range(int(__test_environment__['sends_count'] / 2)):
				for sender in senders:
					for signal_name in __test_environment__['signals_names']:
						sender.send_signal(signal_name)

		signals_thread_one = Thread(target=send_signals_fn)
		signals_thread_two = Thread(target=send_signals_fn)

		if use_con_matrix is True:
			con_matrix_thread_one = Thread(target=__test_environment__['connection_matrix_one'].start)
			con_matrix_thread_two = Thread(target=__test_environment__['connection_matrix_two'].start)

			con_matrix_thread_one.start()
			con_matrix_thread_two.start()

		start_time = time()
		signals_thread_one.start()
		signals_thread_two.start()
		signals_thread_one.join()
		signals_thread_two.join()
		finish_time = time()

		if use_con_matrix is True:
			__test_environment__['connection_matrix_one'].stop()
			__test_environment__['connection_matrix_two'].stop()

			con_matrix_thread_one.join()
			con_matrix_thread_two.join()

			__test_environment__['connection_matrix_one'].process_signals()
			__test_environment__['connection_matrix_two'].process_signals()

		usage = resource.getrusage(resource.RUSAGE_SELF)

		arg_tuple = (impl_name, str(start_time), str(finish_time), str(finish_time - start_time))
		print('Implementation %s. Started at: %s. Finished at: %s. Duration: %s' % arg_tuple)
		arg_tuple = (impl_name, str(usage[0]), str(usage[1]), str(usage[2] / 1024))
		print("Implementation %s. Memory consumption: usertime=%s systime=%s mem=%s mb" % arg_tuple)

		for r in receivers:
			assert(
				r.counter.__int__() == (
					__test_environment__['sends_count'] *
					__test_environment__['senders_count'] *
					len(__test_environment__['signals_names'])
				)
			)


if __name__ == '__main__':
	for i in TestSignals.__implementations__:
		TestSignals().test(*i)
		print()
