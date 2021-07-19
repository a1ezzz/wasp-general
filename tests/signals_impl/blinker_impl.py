
from queue import Queue

from blinker import signal

from wasp_general.api.signals.proto import WSignalWatcherProto, WSignalSourceProto


class PlainWatcher(WSignalWatcherProto):

	def __init__(self):
		self.__queue = []

	def wait(self, timeout=None):
		pass

	def next(self):
		pass

	def has_next(self):
		return len(self.__queue) > 0

	def __call__(self, sender, payload=None, **kwargs):
		self.__queue.append(payload)


class Source(WSignalSourceProto):

	__watcher_cls__ = PlainWatcher

	def __init__(self, *signals):
		WSignalSourceProto.__init__(self)
		self.__signals = {s: signal(s) for s in signals}

	def send_signal(self, signal_id, payload=None):
		self.__signals[signal_id].send(self, payload=payload)

	def watch(self, signal_id):
		watcher = self.__watcher_cls__()
		self.__signals[signal_id].connect(watcher, sender=self)
		return watcher

	def remove_watcher(self, watcher):
		raise NotImplementedError('This method is abstract')

	def callback(self, signal_id, callback):
		raise NotImplementedError('This method is abstract')

	def remove_callback(self, signal_id, callback):
		raise NotImplementedError('This method is abstract')

	def signals(cls):
		raise NotImplementedError('This method is abstract')

	@classmethod
	def new_source(cls, *signals):
		return cls(*signals)


class QueueWatcher(WSignalWatcherProto):

	def __init__(self):
		self.__queue = Queue()
		self.__next_item = None

	def wait(self, timeout=None):
		if self.__next_item is None:
			self.__next_item = self.__queue.get()

	def has_next(self):
		return not self.__queue.empty()

	def next(self):
		if self.__next_item is not None:
			result = self.__next_item
			self.__next_item = None
			return result
		raise ValueError('!')

	def __call__(self, sender, payload=None, **kwargs):
		self.__queue.put(payload)


class QueueSource(Source):

	__watcher_cls__ = QueueWatcher
