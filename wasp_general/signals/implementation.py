# -*- coding: utf-8 -*-
# wasp_general/<FILENAME>.py
#
# Copyright (C) 2018 the wasp-general authors and contributors
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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import weakref
import time
from abc import abstractmethod

from wasp_general.verify import verify_type, verify_value
from wasp_general.thread import WCriticalResource
from wasp_general.atomic import WAtomicCounter
from wasp_general.signals.proto import WSignalSourceProto, WSignalReceiverProto, WSignalConnectionMatrixProto


class WROCounterReference:
	""" Represent weak read only reference to a counter
	"""

	@verify_type(original_counter=WAtomicCounter)
	def __init__(self, original_counter):
		""" Create new read-only reference

		:param original_counter: counter this object is referencing to
		"""
		self.__counter_ref = weakref.ref(original_counter)

	def __int__(self):
		""" Return current counter value

		:return: int or None (if the referenced object was discarded)
		"""
		obj = self.__counter_ref()
		if obj is None:
			return None

		return obj.__int__()


class WLinkedSignalCounter(WAtomicCounter):
	""" Represent a counter which also has a linked reference to other counter. May be useful when it is required to
	compare to values
	"""

	@verify_type(original_counter=WAtomicCounter)
	def __init__(self, original_counter):
		""" Create new "linked" counter

		:param original_counter: counter that this object is "linked" to
		"""
		WAtomicCounter.__init__(self, value=original_counter.__int__())
		self.__original_counter = WROCounterReference(original_counter)

	def original_counter(self):
		""" Return "linked" counter

		:return: WROCounterReference
		"""
		return self.__original_counter


# noinspection PyAbstractClass
class WSignalSourceProtoImplProto(WSignalSourceProto):
	""" Detailed abstract class that will be used in this implementation. A core idea is to use integer atomic
	counters which is used as a sign of a committed signal. One counter is used for a total number of signals
	that was sent by this object. Others - for specific signals.
	"""

	@abstractmethod
	def source_counter(self):
		""" Return a total number of signals that was sent by this object

		:return: int
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(signals_names=str)
	def signals_counters(self, *signals_names):
		""" Return numbers of signals that was sent by this object

		:param signals_names: name of signals which counters should be returned
		:return: dict where keys are signal names and values are corresponding counter values
		"""

		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(signals_names=str)
	def linked_counters(self, *signals_names):
		""" Return :class:`.WLinkedSignalCounter` objects for specified signals. Each
		:class:`.WLinkedSignalCounter` object has a "link" to an original signal counter.

		:param signals_names: name of signals which "linked counters" should be returned
		:return: dict where keys are signal names and values are :class:`.WLinkedSignalCounter` objects
		"""
		raise NotImplementedError('This method is abstract')


class WSignalStorage(WAtomicCounter):
	""" This storage counts how many times signals were sent. It counts each signal that was sent and inherits
	a :class:`.WAtomicCounter` class to represent a total number of signals that were sent
	"""

	@verify_type(signals_names=str)
	def __init__(self, *signals_names):
		""" Create new storage

		:param signals_names: list of permitted signals
		"""
		WAtomicCounter.__init__(self)
		self.__signals = {x:  WAtomicCounter() for x in signals_names}

	@verify_type(signal_name=str)
	def emit(self, signal_name):
		""" Send a signal

		:param signal_name: signal name to send

		:return: None
		"""
		self.__signals[signal_name].increase_counter(1)
		WAtomicCounter.increase_counter(self, 1)

	def increase_counter(self, delta=None):
		""" This is the inherited method :meth:`.WAtomicCounter.increase_counter` that must not be called
		directly. In order to increase a total number of signals that were sent use
		the :meth:`.WSignalStorage.emit` method
		"""
		raise RuntimeError('This method must not be called. Use emit() method instead!')

	def signals_names(self):
		""" Return signal names that are permitted to be sent

		:return: tuple of str
		"""
		return tuple(self.__signals.keys())

	@verify_type(signals_names=str)
	def signals_counters(self, *signals_names):
		""" Return counter values for specific signals

		:param signals_names: name of signals which counters should be returned
		:return: dict, where key is a signal name (str) and a value is a corresponding counter value (int)
		"""
		return {x: self.__signals[x].__int__() for x in signals_names}

	@verify_type(signals_names=str)
	def linked_counters(self, *signals_names):
		""" Create and return "linked" counters for specific signals

		:param signals_names: name of signals for which "linked" counters should be created
		:return: dict, where key is a signal name (str) and a value is
		a :class:`.WLinkedSignalCounter` class object
		"""
		counters = {}
		for signal_name in signals_names:
			if signal_name not in self.__signals:
				raise ValueError('Unknown signal')
			counters[signal_name] = WLinkedSignalCounter(self.__signals[signal_name])
		return counters


class WSignalSource(WSignalSourceProtoImplProto):
	""" A signal source that sends signals via :class:`.WSignalConnectionMatrixProto` object
	"""

	@verify_type(con_matrix=WSignalConnectionMatrixProto)
	@verify_type('paranoid', signals_names=str)
	def __init__(self, con_matrix, *signals_names):
		""" Create new signal sender

		:param con_matrix: object that connects and disconnects senders and receivers. This object delivers
		signals also
		:param signals_names: Names of signals that this object is capable to send
		"""
		WSignalSourceProtoImplProto.__init__(self)
		self.__storage = WSignalStorage(*signals_names)
		self.__con_matrix = con_matrix

	@verify_type('paranoid', signal_name=str)
	def send_signal(self, signal_name):
		""" :meth:`.WSignalSourceProto.send_signal` method implementation
		"""
		if signal_name not in self.signals():
			raise ValueError('An invalid signal name was specified')
		self.__storage.emit(signal_name)
		self.__con_matrix.increase_counter(1)

	def signals(self):
		""" :meth:`.WSignalSourceProto.signals` method implementation
		"""
		return self.__storage.signals_names()

	def source_counter(self):
		""" :meth:`.WSignalSourceProtoImplProto.source_counter` method implementation
		"""
		return self.__storage.__int__()

	@verify_type('paranoid', signals_names=str)
	def signals_counters(self, *signals_names):
		""" :meth:`.WSignalSourceProtoImplProto.signals_counters` method implementation
		"""
		return self.__storage.signals_counters(*signals_names)

	@verify_type('paranoid', signal_names=str)
	def linked_counters(self, *signal_names):
		""" :meth:`.WSignalSourceProtoImplProto.linked_counters` method implementation
		"""
		return self.__storage.linked_counters(*signal_names)

	def connection_matrix(self):
		return self.__con_matrix


class WSignalConnectionMatrix(WSignalConnectionMatrixProto, WAtomicCounter, WCriticalResource):
	""" :class:`.WSignalConnectionMatrixProto` implementation. In order to process signals, this object
	should be started via :meth:`.WSignalConnectionMatrix.start` method call
	"""

	__lock_acquiring_timeout__ = 5  # timeout with which there will be an attempt to acquire a lock

	__default_polling_timeout__ = 0.01  # default timeout that will occur between signals processing

	class CacheEntries:
		""" Class for holding information about senders, signals, receivers states and its counters
		"""

		@verify_type(weak=bool)
		def __init__(self, weak=True):
			""" Create new entry

			:param weak: should internal records be stored in "weak"-reference dictionary or in a general
			dictionary
			"""
			self.cached_value = 0
			self.entries = weakref.WeakKeyDictionary() if weak is True else {}
			self.__weak = weak

		def weak(self):
			""" Return whether this entry hold internal records in "weak"-reference dictionary or not

			:return: bool
			"""
			return self.__weak

		def entries_items(self):
			""" Return copy of internal items

			:return: iterable of key-value pairs
			"""
			return self.entries.copy().items()

	@verify_type(polling_timeout=(int, float, None))
	@verify_value(polling_timeout=lambda x: x is None or x > 0)
	def __init__(self, polling_timeout=None):
		""" Create new connection matrix

		:param polling_timeout: timeout that will occur between signals processing
		"""
		WSignalConnectionMatrixProto.__init__(self)
		WAtomicCounter.__init__(self)
		WCriticalResource.__init__(self)

		self.__connections = WSignalConnectionMatrix.CacheEntries(weak=True)
		self.__running = False
		self.__polling_timeout = \
			polling_timeout if polling_timeout is not None else self.__default_polling_timeout__

	def polling_timeout(self):
		""" Return timeout that will occur between signals processing

		:return: int or float
		"""
		return self.__polling_timeout

	@verify_type(signal_sender=WSignalSourceProtoImplProto, signal_name=str, receiver=WSignalReceiverProto)
	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def disconnect(self, signal_sender, signal_name, receiver):
		""" :meth:`.WSignalConnectionMatrix.disconnect` method implementation
		"""

		signal_disconnected = False

		if signal_sender in self.__connections.entries:
			source_entry = self.__connections.entries[signal_sender]

			if signal_name in source_entry.entries:
				signal_entry = source_entry.entries[signal_name]

				if receiver in signal_entry.entries:
					signal_entry.entries.pop(receiver)
					signal_disconnected = True

				if signal_disconnected is True and len(signal_entry.entries) == 0:
					source_entry.entries.pop(signal_name)

			if signal_disconnected is True and len(source_entry.entries) == 0:
				self.__connections.entries.pop(signal_sender)

		if signal_disconnected is False:
			raise ValueError('Already disconnected')

	@verify_type(signal_sender=WSignalSourceProtoImplProto, signal_name=str, receiver=WSignalReceiverProto)
	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def connect(self, signal_sender, signal_name, receiver):
		""" :meth:`.WSignalConnectionMatrix.connect` method implementation
		"""
		if signal_sender in self.__connections.entries:
			source_entry = self.__connections.entries[signal_sender]
		else:
			source_entry = WSignalConnectionMatrix.CacheEntries(weak=False)
			self.__connections.entries[signal_sender] = source_entry

		if signal_name in source_entry.entries:
			signal_entry = source_entry.entries[signal_name]
		else:
			signal_entry = WSignalConnectionMatrix.CacheEntries(weak=True)
			source_entry.entries[signal_name] = signal_entry

		if receiver not in signal_entry.entries:
			signal_entry.entries[receiver] = signal_sender.linked_counters(signal_name)[signal_name]
		else:
			raise ValueError('Already connected')

	def start(self):
		""" Start processing signals

		:return: None
		"""
		self.__running = True
		pt = self.polling_timeout()

		while self.__running is True:
			self.process_signals()
			time.sleep(pt)

	def stop(self):
		""" Stop processing signals

		:return: None
		"""
		self.__running = False

	@verify_type(commit_changes=bool)
	def __iter__(self, commit_changes=False):
		""" Iterate over signals that are awaiting to be processed. tuple object will be yielded, this object
		consists of "delta" (int - how many signals were received after the last commit),
		signal_source (:class:`.WSignalSourceProtoImplProto` - source signal object), signal_name (name of
		a signal that was sent), receiver (:class:`.WSignalReceiverProto` - a receiver that is awaiting for a
		signal).

		:param commit_changes: if is True, then yielded signals will be treated as processed, otherwise -
		such signals will be included in the next method call

		:return: None
		"""
		signals_emitted = self.__int__()
		if signals_emitted > self.__connections.cached_value:

			for signal_source, source_entry in self.__connections.entries_items():
				source_entry_state = signal_source.source_counter()
				if source_entry_state > source_entry.cached_value:

					signal_names = source_entry.entries.keys()
					source_state = signal_source.signals_counters(*signal_names)

					for signal_name, signal_entry in source_entry.entries_items():

						signal_state = source_state[signal_name]

						if signal_state > signal_entry.cached_value:
							for receiver, linked_counter in signal_entry.entries_items():
								delta = signal_state - signal_entry.cached_value
								yield delta, signal_source, signal_name, receiver

								if commit_changes is True:
									linked_counter.increase_counter(delta)

						if commit_changes is True:
							signal_entry.cached_value = signal_state

				if commit_changes is True:
					source_entry.cached_value = source_entry_state

			if commit_changes is True:
				self.__connections.cached_value = signals_emitted

	def process_signals(self):
		""" Process signals that were sent

		:return: None
		"""
		for delta, signal_source, signal_name, receiver in self.__iter__(commit_changes=True):
			if delta > 0:
				receiver.receive_signal(signal_source, signal_name, delta)
