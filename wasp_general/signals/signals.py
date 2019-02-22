# -*- coding: utf-8 -*-
# wasp_general/signals/signals.py
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

from wasp_general.verify import verify_type, verify_value

from wasp_general.platform import WPlatformThreadEvent

from wasp_general.signals.proto import WSignalWatcherProto, WSignalSourceProto, WSignalProxyProto, WSignalCallbackProto
from wasp_general.signals.proto import WUnknownSignalException


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

			:return: True - if there is unhandled signal, False - otherwise
			:rtype:  bool
			"""
			return WMCQueueSubscriber.has_next(self)

		def next(self):
			"""
			Return next unhandled signal. It must be in a queue already, otherwise Exception will be raised

			:rtype: any
			"""
			return WMCQueueSubscriber.next(self)

	@verify_type('strict', signal_names=str)
	def __init__(self, *signal_names):
		""" Create new signal source

		:param signal_names: names of signals that this object may send
		:type signal_names: str
		"""

		WSignalSourceProto.__init__(self)
		self.__signal_names = signal_names
		self.__queues = {x: WMCQueue(callback=self.__watchers_callbacks_exec(x)) for x in signal_names}
		self.__watchers_callbacks = {x: weakref.WeakSet() for x in signal_names}
		self.__direct_callbacks = {x: weakref.WeakSet() for x in signal_names}

	def __watchers_callbacks_exec(self, signal_name):
		""" Generate callback for a queue

		:param signal_name: name of a signal that callback is generated for
		:type signal_name: str

		:rtype: callable
		"""
		def callback_fn():
			for watcher in self.__watchers_callbacks[signal_name]:
				if watcher is not None:
					watcher.notify()
		return callback_fn

	@verify_type('strict', signal_name=str)
	def send_signal(self, signal_name, signal_args=None):
		""" :meth:`.WSignalSourceProto.send_signal` implementation
		"""
		try:
			self.__queues[signal_name].push(signal_args)
			for callback in self.__direct_callbacks[signal_name]:
				if callback is not None:
					callback(self, signal_name, signal_args)
		except KeyError:
			raise WUnknownSignalException('Unknown signal "%s"' % signal_name)

	def signals(self):
		""" :meth:`.WSignalSourceProto.signals` implementation
		"""
		return self.__signal_names

	@verify_type('strict', signal_name=str)
	def watch(self, signal_name):
		""" :meth:`.WSignalSourceProto.watch` implementation

		:rtype: watcher: WSignalSource.Watcher
		"""
		watcher = WSignalSource.Watcher(
			self.__queues[signal_name], lambda x: self.__watchers_callbacks[signal_name].remove(x)
		)
		self.__watchers_callbacks[signal_name].add(watcher)
		return watcher

	@verify_type('strict', watcher=Watcher)
	def remove_watcher(self, watcher):
		""" :meth:`.WSignalSourceProto.remove_watcher` implementation

		:type watcher: WSignalSource.Watcher
		"""
		watcher.unsubscribe()

	@verify_type('strict', signal_name=str)
	@verify_value('strict', callback=lambda x: callable(x))
	def callback(self, signal_name, callback):
		""" :meth:`.WSignalSourceProto.callback` implementation
		"""
		self.__direct_callbacks[signal_name].add(callback)

	@verify_type('strict', signal_name=str)
	@verify_value('strict', callback=lambda x: callable(x))
	def remove_callback(self, signal_name, callback):
		""" :meth:`.WSignalSourceProto.remove_callback` implementation
		"""
		try:
			self.__direct_callbacks[signal_name].remove(callback)
		except KeyError:
			raise ValueError('Signal "%s" does not have the specified callback' % signal_name)


class WSignalProxy(WSignalProxyProto):
	""" :class:`.WSignalProxyProto` implementation that is based on :class:`.WSignalSource`
	"""

	__proxy_signal_name__ = ""  # name of a signal for internal usage

	class ProxiedSignal(WSignalProxyProto.ProxiedSignalProto):
		""" :class:`.WSignalProxyProto.ProxiedSignalProto` implementation that is used by class
		:class:`.WSignalProxy`
		"""

		@verify_type('strict', signal_source=(WSignalSource, weakref.ReferenceType), signal_name=str)
		def __init__(self, signal_source, signal_name, signal_arg):
			""" Create new signal descriptor

			:param signal_source: origin source
			:type signal_source: WSignalSource | weak reference to WSignalSource

			:param signal_name: origin signal name
			:type signal_name: str

			:param signal_arg: signal argument
			:type signal_arg: any
			"""

			self.__signal_source = signal_source
			self.__signal_name = signal_name
			self.__signal_arg = signal_arg

		def signal_source(self):
			""" :meth:`.WSignalProxyProto.ProxiedSignalProto.signal_source` implementation
			"""
			return self.__signal_source

		def signal_name(self):
			""" :meth:`.WSignalProxyProto.ProxiedSignalProto.signal_name` implementation
			"""
			return self.__signal_name

		def signal_arg(self):
			""" :meth:`.WSignalProxyProto.ProxiedSignalProto.signal_arg` implementation
			"""
			return self.__signal_arg

	class ProxyCallback(WSignalCallbackProto):
		""" This class is used as a callback for proxying original signals. May be used with multiple sources
		"""

		@verify_type('strict', signal_target=WSignalSourceProto, weak_ref=bool)
		def __init__(self, signal_target, weak_ref=False):
			""" Create new callback

			:param signal_target: a target where signal should be proxied to
			:type signal_target: WSignalSourceProto

			:param weak_ref: whether to send a source to the target as a weak reference or as an
			ordinary object. is False by default
			:type weak_ref: bool
			"""
			self.__signal_target = signal_target
			self.__weak_ref = weak_ref

		@verify_type('strict', signal_source=WSignalSourceProto, signal_name=str)
		def __call__(self, signal_source, signal_name, signal_arg=None):
			""" Callback that may be used with :class:`.WSignalSource`

			:param signal_source: a signal origin
			:type signal_source: WSignalSourceProto

			:param signal_name: a name of a signal
			:type signal_name: str

			:param signal_arg: a signal argument
			:type signal_arg: any

			:rtype: None
			"""
			if self.__weak_ref:
				signal_source = weakref.ref(signal_source)

			self.__signal_target.send_signal(
				WSignalProxy.__proxy_signal_name__,
				WSignalProxy.ProxiedSignal(signal_source, signal_name, signal_arg)
			)

	def __init__(self):
		""" Create new proxy object
		"""
		WSignalProxyProto.__init__(self)
		self.__signal_source = WSignalSource(WSignalProxy.__proxy_signal_name__)
		self.__watcher = self.__signal_source.watch(WSignalProxy.__proxy_signal_name__)
		self.__callback = WSignalProxy.ProxyCallback(self.__signal_source)
		self.__weak_ref_callback = WSignalProxy.ProxyCallback(self.__signal_source, weak_ref=True)

	@verify_type('strict', signal_source=WSignalSourceProto, signal_names=str, weak_ref=bool)
	@verify_value(signal_names=lambda x: len(x) > 0)
	def proxy(self, signal_source, *signal_names, weak_ref=False):
		""" :meth:`.WSignalProxyProto.proxy` implementation
		"""
		callback = self.__callback if weak_ref is False else self.__weak_ref_callback
		for signal_name in signal_names:
			signal_source.callback(signal_name, callback)

	@verify_type('strict', signal_source=WSignalSourceProto, signal_names=str)
	def stop_proxying(self, signal_source, *signal_names, weak_ref=False):
		""" :meth:`.WSignalProxyProto.stop_proxying` implementation
		"""
		callback = self.__callback if weak_ref is False else self.__weak_ref_callback
		for signal_name in signal_names:
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
