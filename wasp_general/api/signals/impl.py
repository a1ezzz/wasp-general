# -*- coding: utf-8 -*-
# wasp_general/api/signals/impl.py
#
# Copyright (C) 2019 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# Wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

import weakref

from wasp_c_extensions.threads import awareness_wait
from wasp_c_extensions.queue import WMCQueue, WMCQueueSubscriber

from wasp_general.verify import verify_type, verify_value, TypeVerifier

from wasp_general.platform import WPlatformThreadEvent

from wasp_general.api.signals.proto import WSignalWatcherProto, WSignalSourceProto, WSignalProxyProto
from wasp_general.api.signals.proto import WSignalCallbackProto, WUnknownSignalException


class WSignalSource(WSignalSourceProto):
	""" :class:`.WSignalSourceProto` implementation that is based on :class:`.WMCQueue`
	"""

	class Watcher(WSignalWatcherProto, WMCQueueSubscriber):
		""" :class:`.WSignalWatcherProto` implementation that is used by :class:`.WSignalSource`
		"""

		@verify_type('strict', queue=WMCQueue)
		@verify_value('strict', unsubscribe_callback=lambda x: callable(x))
		def __init__(self, queue, unsubscribe_callback):
			""" Create new watcher

			:param queue: queue with signals records
			:type queue: WMCQueue

			:param unsubscribe_callback: callback that will be called on unsubscription
			:type unsubscribe_callback: callable
			"""
			WSignalWatcherProto.__init__(self)
			WMCQueueSubscriber.__init__(self, queue)
			self.__unsubscribe_callback = unsubscribe_callback
			self.__event = WPlatformThreadEvent()

		@verify_type('strict', timeout=(int, float, None))
		@verify_value('strict', timeout=lambda x: x is None or x >= 0)
		def wait(self, timeout=None):
			""" Wait for unhandled signal. If there is unhandled signal already then this function
			returns immediately.

			:param timeout: timeout during which new signal will be awaited. If it is not specified, then
			new signal will be awaited "forever"
			:type timeout: int | float | None

			:return: True - if there is unhandled signal, False - otherwise
			:rtype: bool
			"""
			return awareness_wait(self.__event, self.has_next, timeout=timeout)

		def notify(self):
			""" Notify awaited calls (:meth:`.WSignalSource.Watcher.wait`) that there is a new unhandled
			signal

			:rtype: None
			"""

			self.__event.set()

		def unsubscribe(self):
			""" Stop watching for new signals (even current signals that awaited in a queue). After this
			function call methods :meth:`.WSignalSource.Watcher.wait`,
			:meth:`.WSignalSource.Watcher.has_next` and :meth:`.WSignalSource.Watcher.next` becomes
			unavailable

			:rtype: None
			"""
			if self.subscribed():
				WMCQueueSubscriber.unsubscribe(self)
				self.__unsubscribe_callback(self)
				self.__unsubscribe_callback = None

		def has_next(self):
			""" Check if there is unhandled signal in a queue already

			:raise RuntimeError: if this watcher is unsubscribed

			:return: True - if there is unhandled signal, False - otherwise
			:rtype:  bool
			"""
			return WMCQueueSubscriber.has_next(self)

		def next(self):
			"""
			Return a payload of the next unhandled signal. It must be in a queue already,
			otherwise exception will be raised

			:raise KeyError: if there is no the next signal
			:raise RuntimeError: if this watcher is unsubscribed

			:rtype: any
			"""
			return WMCQueueSubscriber.next(self)

	def __init__(self):
		""" Create new signal source
		"""

		signal_ids = self.signals()
		if len(signal_ids) != len(set(signal_ids)):
			raise ValueError('Signal identifiers must be unique')

		WSignalSourceProto.__init__(self)
		self.__queues = {x: WMCQueue(callback=self.__watchers_callbacks_exec(x)) for x in signal_ids}
		self.__watchers_callbacks = {x: weakref.WeakSet() for x in signal_ids}
		self.__direct_callbacks = {x: weakref.WeakSet() for x in signal_ids}

	def __watchers_callbacks_exec(self, signal_id):
		""" Generate callback for a queue

		:param signal_id: name of a signal that callback is generated for
		:type signal_id: any

		:rtype: callable
		"""
		def callback_fn():
			for watcher in self.__watchers_callbacks[signal_id]:
				if watcher is not None:
					watcher.notify()
		return callback_fn

	def send_signal(self, signal_id, payload=None):
		""" :meth:`.WSignalSourceProto.send_signal` implementation
		"""
		try:
			self.__queues[signal_id].push(payload)
			for callback in self.__direct_callbacks[signal_id]:
				if callback is not None:
					callback(self, signal_id, payload)
		except KeyError:
			raise WUnknownSignalException('Unknown signal "%s"' % signal_id)

	def watch(self, signal_id):
		""" :meth:`.WSignalSourceProto.watch` implementation

		:rtype: watcher: WSignalSource.Watcher
		"""
		watcher = WSignalSource.Watcher(
			self.__queues[signal_id], lambda x: self.__watchers_callbacks[signal_id].remove(x)
		)
		self.__watchers_callbacks[signal_id].add(watcher)
		return watcher

	@verify_type('strict', watcher=Watcher)
	def remove_watcher(self, watcher):
		""" :meth:`.WSignalSourceProto.remove_watcher` implementation

		:type watcher: WSignalSource.Watcher
		"""
		watcher.unsubscribe()

	@verify_value('strict', callback=lambda x: callable(x))
	def callback(self, signal_id, callback):
		""" :meth:`.WSignalSourceProto.callback` implementation
		"""
		self.__direct_callbacks[signal_id].add(callback)

	@verify_value('strict', callback=lambda x: callable(x))
	def remove_callback(self, signal_id, callback):
		""" :meth:`.WSignalSourceProto.remove_callback` implementation
		"""
		try:
			self.__direct_callbacks[signal_id].remove(callback)
		except KeyError:
			raise ValueError('Signal "%s" does not have the specified callback' % signal_id)

	@classmethod
	def signals(cls):
		""" :meth:`.WSignalSourceProto.signals` implementation (returns empty tuple by default)
		"""
		return tuple()


def anonymous_source(*signals):
	""" This function returns object of a locally generated class. That object is a WSignalSourceProto
	implementation that may send a specified signals.

	This function is useful for testing and for internal implementations

	:param signals: signals that a target signal source may send
	:type signals: any

	:rtype: WSignalSourceProto
	"""

	class Source(WSignalSource):
		@classmethod
		def signals(cls):
			return signals

	return Source()


class WSignalProxy(WSignalProxyProto):
	""" :class:`.WSignalProxyProto` implementation that is based on :class:`.WSignalSource`
	"""

	class ProxiedSignal(WSignalProxyProto.ProxiedSignalProto):
		""" :class:`.WSignalProxyProto.ProxiedSignalProto` implementation that is used by class
		:class:`.WSignalProxy`
		"""

		@verify_type('strict', signal_source=(WSignalSourceProto, weakref.ReferenceType))
		def __init__(self, signal_source, signal_id, payload):
			""" Create new signal descriptor

			:param signal_source: origin source
			:type signal_source: WSignalSource | weak reference to WSignalSource

			:param signal_id: origin signal id
			:type signal_id: any

			:param payload: signal argument
			:type payload: any
			"""

			self.__signal_source = signal_source
			self.__signal_id = signal_id
			self.__payload = payload

		def signal_source(self):
			""" :meth:`.WSignalProxyProto.ProxiedSignalProto.signal_source` implementation
			"""
			return self.__signal_source

		def signal_id(self):
			""" :meth:`.WSignalProxyProto.ProxiedSignalProto.signal_id` implementation
			"""
			return self.__signal_id

		def payload(self):
			""" :meth:`.WSignalProxyProto.ProxiedSignalProto.payload` implementation
			"""
			return self.__payload

	class ProxyCallback(WSignalCallbackProto):
		""" This class is used as a callback for proxying original signals. May be used with multiple sources
		"""

		@verify_type('strict', signal_target=WSignalSourceProto, weak_ref=bool)
		def __init__(self, signal_target, signal, weak_ref=False):
			""" Create new callback

			:param signal_target: a target where signal should be proxied to
			:type signal_target: WSignalSourceProto

			:param signal: a signal that this callback should send in order to notify 'signal_target'
			:type signal: any

			:param weak_ref: whether to send a source to the target as a weak reference or as an
			ordinary object. is False by default
			:type weak_ref: bool
			"""
			self.__signal_target = signal_target
			self.__signal = signal
			self.__weak_ref = weak_ref

		@verify_type('strict', signal_source=WSignalSourceProto)
		def __call__(self, signal_source, signal_id, payload=None):
			""" Callback that may be used with :class:`.WSignalSource`

			:param signal_source: a signal origin
			:type signal_source: WSignalSourceProto

			:param signal_id: a name of a signal
			:type signal_id: any

			:param payload: a signal argument
			:type payload: any

			:rtype: None
			"""
			if self.__weak_ref:
				signal_source = weakref.ref(signal_source)

			self.__signal_target.send_signal(
				self.__signal, WSignalProxy.ProxiedSignal(signal_source, signal_id, payload)
			)

	def __init__(self):
		""" Create new proxy object
		"""
		WSignalProxyProto.__init__(self)
		proxy_signal = object()
		self.__signal_source = anonymous_source(proxy_signal)
		self.__watcher = self.__signal_source.watch(proxy_signal)
		self.__callback = WSignalProxy.ProxyCallback(self.__signal_source, proxy_signal)
		self.__weak_ref_callback = WSignalProxy.ProxyCallback(self.__signal_source, proxy_signal, weak_ref=True)

	@verify_type('strict', signal_source=WSignalSourceProto, signal_names=str, weak_ref=bool)
	@verify_value(signal_names=lambda x: len(x) > 0)
	def proxy(self, signal_source, *signal_ids, weak_ref=False):
		""" :meth:`.WSignalProxyProto.proxy` implementation
		"""
		callback = self.__callback if weak_ref is False else self.__weak_ref_callback
		for signal_name in signal_ids:
			signal_source.callback(signal_name, callback)

	@verify_type('strict', signal_source=WSignalSourceProto, signal_names=str)
	def stop_proxying(self, signal_source, *signal_ids, weak_ref=False):
		""" :meth:`.WSignalProxyProto.stop_proxying` implementation
		"""
		callback = self.__callback if weak_ref is False else self.__weak_ref_callback
		for signal_name in signal_ids:
			signal_source.remove_callback(signal_name, callback)

	def wait(self, timeout=None):
		""" :meth:`.WSignalProxyProto.wait` implementation
		"""
		return self.__watcher.wait(timeout=timeout)

	def has_next(self):
		""" :meth:`.WSignalProxyProto.has_next` implementation
		"""
		return self.__watcher.has_next()

	def next(self):
		""" :meth:`.WSignalProxyProto.next` implementation
		"""
		return self.__watcher.next()


class WSignal:
	""" This class helps to specify a signal that signal source may send. Each class object is a single signal.
	It is possible to set a payload type that may be sent with a signal. It is possible to turn off a payload
	at all
	"""

	__payload_default_spec__ = object()  # default payload type. If it is used then there is no payload restrictions

	def __init__(self, payload_type_spec=__payload_default_spec__):
		""" Create new signal and set a suitable payload

		:param payload_type_spec: specification of a payload type. Value is the same as "type_spec" in
		the :meth:`.TypeVerifier.check` method with one exception. the None value means that payload is not
		supported by a signal
		:type payload_type_spec: any
		"""
		self.__type_check = payload_type_spec
		if payload_type_spec is not WSignal.__payload_default_spec__ and payload_type_spec is not None:
			self.__type_check = TypeVerifier().check(payload_type_spec, 'payload', self.__call__)

	@verify_type('strict', signal_source=WSignalSource)
	def __call__(self, signal_source, payload=None):
		""" Check a payload and emit this signal once more

		:param signal_source: where from this signal should be sent from
		:type signal_source: WSignalSource

		:param payload: a payload that will be checked and send it if it is valid
		:type payload: any

		:rtype: None
		"""
		if self.__type_check is not WSignal.__payload_default_spec__:
			if self.__type_check is None:
				if payload is not None:
					raise TypeError('This signal does not accept "payload"')
			else:
				self.__type_check(payload)
		signal_source.send_signal(self, payload=payload)


class WSignalPrioritizedProxy(WSignalProxyProto):
	pass
