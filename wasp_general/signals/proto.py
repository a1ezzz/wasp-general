# -*- coding: utf-8 -*-
# wasp_general/signals/proto.py
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

# TODO: write tests for the code

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value


class WSignalSourceProto(metaclass=ABCMeta):
	""" An entry class for an object that sends signals. Every callback and watcher is saved as a 'weak' reference.
	So in most cases in order to stop watching or executing callback it is sufficient just to discard all
	references
	"""

	class WatcherProto(metaclass=ABCMeta):
		""" A class that will be returned by :meth:`.WSignalSourceProto.watch` method. With this object
		it is possible to wait for the next unhandled signal
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
	@verify_type('strict', signal_name=str)
	def send_signal(self, signal_name, signal_args=None):
		""" Send a signal from this object

		:param signal_name: a name of a signal to send
		:type signal_name: str
		:param signal_args: a signal argument that may be send with a signal
		:type signal_args: any

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def signals(self):
		""" Return names of signals that may be sent

		:rtype: tuple of str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', signal_name=str, watcher=(WatcherProto, None))
	def watch(self, signal_name, watcher=None):
		""" Create a "watcher" that helps to wait for a new (unhandled) signal

		:param signal_name: signal to wait
		:type signal_name: str

		:param watcher: if it is specified then this watcher will be used instead of creating a new one. With
		this parameter it is much easier to create a single watcher that waits for multiple signals
		:type watcher: WSignalSourceProto.WatcherProto | None

		:rtype: WSignalSourceProto.WatcherProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', signal_name=str, watcher=WatcherProto)
	def remove_watcher(self, signal_name, watcher):
		""" Unregister the specified watcher and prevent it to be notified when new signal is sent

		:param signal_name: signal that will trigger a watcher
		:type signal_name: str

		:param watcher: watcher that should be unregistered
		:type watcher: WSignalSourceProto.WatcherProto

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', signal_name=str)
	@verify_value('strict', callback=lambda x: callable(x))
	def callback(self, signal_name, callback):
		""" Register a callback that will be executed when new signal is sent

		:param signal_name: signal that will trigger a callback
		:type signal_name: str

		:param callback: callback that must be executed
		:type callback: WSignalCallbackProto | callable

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', signal_name=str)
	@verify_value('strict', callback=lambda x: callable(x))
	def remove_callback(self, signal_name, callback):
		""" Unregister the specified callback and prevent it to be executed when new signal is sent

		:param signal_name: signal that should be avoided
		:type signal_name: str

		:param callback: callback that should be unregistered
		:type callback: WSignalCallbackProto | callable

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')


class WSignalCallbackProto(metaclass=ABCMeta):
	""" An example of class that may receive signals
	"""

	@abstractmethod
	@verify_type('strict', signal_name=str, signal_source=WSignalSourceProto)
	def __call__(self, signal_name, signal_source, signal_args=None):
		""" A callback that will be called when a signal is sent

		:param signal_name: name of a signal that was send
		:type signal_name: str

		:param signal_source: origin of a signal
		:type signal_source: WSignalSourceProto

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')
