
from tempfile import mktemp, mkdtemp
import os
import pytest
import shutil
from threading import Thread, Lock, Event

from wasp_c_extensions.ev_loop import WEventLoop


@pytest.fixture
def temp_file(request):
	filename = mktemp('-pytest-wasp-general')

	def fin():
		if os.path.exists(filename):
			os.unlink(filename)
	request.addfinalizer(fin)
	return filename


@pytest.fixture
def temp_dir(request):
	dir_name = mkdtemp('-pytest-wasp-general')

	def fin():
		if os.path.exists(dir_name):
			shutil.rmtree(dir_name)
	request.addfinalizer(fin)
	return dir_name


@pytest.fixture
def wasp_signals(request):
	wev_loop = WEventLoop()
	thread = Thread(target=wev_loop.start_loop)
	thread.start()

	def fin():
		if wev_loop.is_started():
			wev_loop.stop_loop()
		if thread.is_alive():
			thread.join()
	request.addfinalizer(fin)

	class SignalsCallback:

		def __init__(self, loop, thread):
			self.loop = loop
			self.__thread = thread
			self.__lock = Lock()
			self.__callback_events = {}

			self.__wait_signal = None
			self.__thread_event = Event()

		def __call__(self, source, signal, signal_value=None):
			with self.__lock:
				self.__callback_events.setdefault(signal, [])
				self.__callback_events[signal].append(signal_value)

				if self.__wait_signal is not None and self.__wait_signal == signal:
					self.__thread_event.set()

		def signals(self, signal):
			with self.__lock:
				return tuple(self.__callback_events.get(signal, []))

		def has(self, signal):
			with self.__lock:
				return len(self.__callback_events.get(signal, [])) > 0

		def wait(self, signal):
			with self.__lock:
				if self.__callback_events.get(signal, []):
					return
				self.__wait_signal = signal

			self.__thread_event.wait()
			with self.__lock:
				self.__wait_signal = None
				self.__thread_event.clear()

		def clear(self):
			with self.__lock:
				self.__callback_events.clear()

		def dump(self):
			with self.__lock:
				return {x: tuple(y) for x, y in self.__callback_events.copy().items()}

		def stop(self):
			self.loop.stop_loop()
			self.__thread.join()

	return SignalsCallback(wev_loop, thread)
