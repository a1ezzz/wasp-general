# -*- coding: utf-8 -*-
# wasp_general/api/signals/proto.py
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

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value


class WSignalWatcherProto(metaclass=ABCMeta):
	""" Objects of this class are able to wait for unhandled signals. Such objects are returned by
	:meth:`.WSignalSourceProto.watch` method. They are also implemented in :class:`.WSignalProxyProto` classes.
	"""

	@abstractmethod
	@verify_type('strict', timeout=(int, float, None))
	@verify_value(timeout=lambda x: x is None or x >= 0)
	def wait(self, timeout=None):
		""" Return True if there is an unhandled signal. False - otherwise

		:param timeout: If it is specified it means a period to wait for a new signal. If it is not
		set then this method will wait "forever"

		:rtype: bool
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def has_next(self):
		""" Check if there is unhandled signal already

		:return: True if there is at least one unhandled signal, False - otherwise
		:rtype: bool
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def next(self):
		""" Return next unhandled signal. If there is no unhandled signal then an exception will be raised

		:rtype: any
		"""
		raise NotImplementedError('This method is abstract')


class WSignalSourceProto(metaclass=ABCMeta):
	""" An entry class for an object that sends signals. Every callback and watcher is saved as a 'weak' reference.
	So in most cases in order to stop watching or executing callback it is sufficient just to discard all
	references

	Any hashable object may be a signal identifier (signal_id)
	"""

	@abstractmethod
	def send_signal(self, signal_id, payload=None):
		""" Send a signal from this object

		:param signal_id: an id of a signal to send
		:type signal_id: any

		:param payload: a payload that may be send with a signal
		:type payload: any

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def watch(self, signal_id):
		""" Create a "watcher" that helps to wait for a new (unhandled) signal

		:param signal_id: signal to wait
		:type signal_id: any

		:rtype: WSignalWatcherProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', watcher=WSignalWatcherProto)
	def remove_watcher(self, watcher):
		""" Unregister the specified watcher and prevent it to be notified when new signal is sent

		:param watcher: watcher that should be unregistered
		:type watcher: WSignalWatcherProto

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_value('strict', callback=lambda x: callable(x))
	def callback(self, signal_id, callback):
		""" Register a callback that will be executed when new signal is sent

		:param signal_id: signal that will trigger a callback
		:type signal_id: any

		:param callback: callback that must be executed
		:type callback: WSignalCallbackProto | callable

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_value('strict', callback=lambda x: callable(x))
	def remove_callback(self, signal_id, callback):
		""" Unregister the specified callback and prevent it to be executed when new signal is sent

		:param signal_id: signal that should be avoided
		:type signal_id: any

		:param callback: callback that should be unregistered
		:type callback: WSignalCallbackProto | callable

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@classmethod
	@abstractmethod
	def signals(cls):
		""" Return iterable that consists of items (signals) that this class may send

		:rtype: iterable
		"""
		raise NotImplementedError('This method is abstract')


class WSignalCallbackProto(metaclass=ABCMeta):
	""" An example of class that may receive signals
	"""

	@abstractmethod
	@verify_type('strict', signal_source=WSignalSourceProto)
	def __call__(self, signal_source, signal_id, payload):
		""" A callback that will be called when a signal is sent

		:param signal_source: origin of a signal
		:type signal_source: WSignalSourceProto

		:param signal_id: an id of a signal that was send
		:type signal_id: any

		:param payload: any payload that has been sent with a signal. A specific signal
		may relay on this argument and may raise an exception if an unsupported value is spotted
		:type payload: any

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')


class WSignalProxyProto(WSignalWatcherProto):
	""" With this class it is possible to wait for several signals (even from different signal sources) with
	a signal wait call.

	Since this class is a subclass of :class:`.WSignalWatcherProto` this class has methods such as
	:meth:`.WSignalWatcherProto.wait`, :meth:`.WSignalWatcherProto.has_next`,
	:meth:`.WSignalWatcherProto.next`. With such methods it is possible to wait for a new signals and
	postpone signals handling
	"""

	class ProxiedSignalProto(metaclass=ABCMeta):
		""" This class represent proxied signal. Besides payload that is passed with a sending call it will
		have information about signal origin
		"""

		@abstractmethod
		def signal_source(self):
			""" Return signal source object

			:rtype: WSignalSourceProto or weak reference to WSignalSourceProto
			"""
			raise NotImplementedError('This method is abstract')

		@abstractmethod
		def signal_id(self):
			""" Return a signal id that causes this message

			:rtype: any
			"""
			raise NotImplementedError('This method is abstract')

		@abstractmethod
		def payload(self):
			""" Return a payload that has been sent with a signal

			:rtype: any
			"""
			raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', signal_source=WSignalSourceProto, signal_names=str, weak_ref=bool)
	def proxy(self, signal_source, *signal_ids, weak_ref=False):
		""" Start proxying new signals

		:param signal_source: signal origin to proxy
		:type signal_source: WSignalSourceProto

		:param signal_ids: identifiers of signals to proxy
		:type signal_ids: any

		:param weak_ref: whether signal origin will be stored as is or as a weak reference
		:type weak_ref: bool

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', signal_source=WSignalSourceProto, weak_ref=bool)
	def stop_proxying(self, signal_source, *signal_ids, weak_ref=False):
		""" Stop proxying signals

		:param signal_source: signal origin to stop proxying
		:type signal_source: WSignalSourceProto

		:param signal_ids: identifiers of signals that should not be proxied
		:type signal_ids: any

		:param weak_ref: whether signal origin was requested as weak ref or as a ordinary object
		:type weak_ref: bool

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')


class WUnknownSignalException(Exception):
	""" This exception may be raised if there was a request to signal source with unsupported signal name.
	Usually it means that signal source is not able to send such signal.
	"""
	pass
