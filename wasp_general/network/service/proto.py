# -*- coding: utf-8 -*-
# wasp_general/network/service_v2/proto.py
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

from abc import ABCMeta, abstractmethod
from socket import socket
from threading import Event
from enum import Enum

from wasp_general.verify import verify_type, verify_value


class WPollingHandlerProto(metaclass=ABCMeta):
	""" Prototype of handler that is capable to produce polling function. That polling function awaits for specific
	events on specific file objects. Once a polling function is returned, that function must ignore any changes
	that may be happen to this handler.

	The derived classes should respect timeout property. It should be used by a polling function that waits for
	events for the specific time. This function may be called from an infinite loop; that loop at each iteration
	polls some file objects and checks a stop event.
	"""

	class PollingError(Exception):
		""" Exception in case of errors during polling
		"""

		def __init__(self, *file_objects):
			""" Create new exception

			:param file_objects: file objects that were sources of an exception
			"""
			Exception.__init__(self, 'Error during polling file-objects')
			self.__file_objects = file_objects

		def file_objects(self):
			""" Return file objects that were sources of an exception

			:return: any file-like objects
			"""
			return self.__file_objects

	class PollingEvent(Enum):
		""" Event that may be awaited during polling
		"""
		read = 1
		write = 2

	def __init__(self):
		""" Create new polling handler
		"""
		self.__file_obj = []
		self.__event_mask = None
		self.__timeout = None

	def file_obj(self):
		""" Return file objects that must be polled

		:return: any file-like objects
		"""
		return tuple(self.__file_obj)

	def poll_fd(self, file_obj):
		""" Append file object that should be polled.

		:param file_obj: file object to add

		:return: None
		"""
		self.__file_obj.append(file_obj)

	def event_mask(self):
		""" Return binary mask of events that must be polled

		:return: int
		"""
		return self.__event_mask

	def timeout(self):
		""" Return timeout that may be used by a polling function. The polling function should not block
		current process or thread for more then this timeout.

		:return: int, float or None (if a timeout does not set)
		"""
		return self.__timeout

	@verify_type(timeout=(int, float, None))
	@verify_value(timeout=lambda x: x is None or x >= 0)
	def setup_poll(self, event_mask, timeout=None):
		""" Setup this handler and save specified parameters. This method does not discard file-objects that
		were set before.

		:param event_mask: WPollingHandlerProto.PollingEvent or int - replace polling events, that this handler
		should wait. In case of a :class:`.WPollingHandlerProto.PollingEvent` instance - this single event will
		be awaited. In case of int value - bit-mask may be used. Bit mask is a sum of
		:class:`.WPollingHandlerProto.PollingEvent` values

		:param timeout: set a timeout that may be used by polling function

		:return: None
		"""
		if isinstance(event_mask, WPollingHandlerProto.PollingEvent) is True:
			event_mask = event_mask.value
		elif isinstance(event_mask, int) is False:
			raise TypeError('Invalid type of event_mask')

		self.__event_mask = event_mask
		self.__timeout = timeout

	def reset(self):
		""" Reset this handler settings and return it to a default state.

		:return: None
		"""
		self.__file_obj = []
		self.__event_mask = None
		self.__timeout = None

	@abstractmethod
	def polling_function(self):
		""" Return polling function, that does not accept any argument, but awaits for specific events on
		specific file objects during a specific timeout. Values of events, file objects and timeout that
		are used by that function are obtained from this handler. No matter what will happen to this handler,
		a polling function must use values that were set at the moment of function generation.

		:return: callable
		"""
		raise NotImplementedError('This method is abstract')

	@classmethod
	def create_handler(cls):
		""" Create new handler. As constructors of derived classes may have some extra arguments, this method
		should be used prior to a direct constructor call.

		:return: WPollingHandlerProto
		"""
		return cls()


class WServiceWorkerProto(metaclass=ABCMeta):
	""" This class is used for interaction with a client connection
	"""

	@abstractmethod
	@verify_type(socket_obj=socket)
	def process(self, socket_obj):
		""" Process new client connection

		:param socket_obj: client connection
		:return:
		"""
		raise NotImplementedError('This method is abstract')


class WServiceFactoryProto(metaclass=ABCMeta):
	""" This class is used for managing service workers (:class:`.WServiceWorkerProto` instances)
	"""

	def __init__(self):
		""" Create new factory
		"""
		self.__stop_event = None

	@verify_type(stop_event=Event)
	def configure(self, stop_event, **kwargs):
		""" Configure this factory

		:param stop_event: save this stop event. This event will be set when service is about to stop
		:param kwargs: extra arguments

		:return: None
		"""
		self.__stop_event = stop_event

	def stop_event(self):
		""" Return stop event

		:return: Event
		"""
		return self.__stop_event

	@abstractmethod
	def worker(self, timeout=None):
		""" Return worker for the next client. This method may block a current thread till a worker is
		available. If a timeout is specified, then this method may block the current thread during
		this period of time only.

		:param timeout: if specified - period of time the current thread may await till a worker is available

		:return: WServiceWorkerProto or None (if no worker is available like in case of timeout)
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def terminate_workers(self):
		""" Stop all the running workers

		:return: None
		"""
		raise NotImplementedError('This method is abstract')
