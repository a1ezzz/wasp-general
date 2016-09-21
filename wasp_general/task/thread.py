# -*- coding: utf-8 -*-
# wasp_general/thread.py
#
# Copyright (C) 2016 the wasp-general authors and contributors
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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta
from threading import Thread, Event

from wasp_general.task.base import WTaskStatus, WStoppableTask
from wasp_general.verify import verify_type


class WThreadTask(WStoppableTask, WTaskStatus, metaclass=ABCMeta):
	""" Task that runs in a separate thread.
	"""

	__thread_join_timeout__ = 5
	""" Default thread joining time
	"""

	@verify_type(thread_name=(str, None), join_on_stop=bool, thread_join_timeout=(int, float, None))
	def __init__(self, thread_name=None, join_on_stop=True, thread_join_timeout=None):
		""" Construct new threaded task. Since there is no right way in Python to stop or terminate neighbor
		thread, so it's highly important for derived classed to be capable to be stopped correctly.

		If join_on_stop is True, then this constructor wraps stop method with join call (timeout are defined
		with WThreadTask.__thread_join_timeout__ and thread_join_timeout). It means, that derived class can
		be interrupt at any time, so task have to poll :meth:`.WThreadTask.stop_event` event for
		notification of stopping.

		If join_on_stop is False, then child class must do all the stop-work itself (after that
		:meth:`.WThreadTask.close_thread` method must be called, otherwise task wouldn't start again).

		:param thread_name: name of the thread. It is used only in thread constructor as name value
		:param join_on_stop: define whether to decorate stop method or not. If task isn't stop for
		:meth:`.WThreadTask.join_timeout` period of time, then RuntimeError will be raised
		:param thread_join_timeout: timeout for joining operation. If it isn't set then default \
		:attr:`.WThreadTask.__thread_join_timeout__` value will be used.
		"""
		WStoppableTask.__init__(self)
		WTaskStatus.__init__(self, decorate_start=False, decorate_stop=False)

		self.__thread_join_timeout = self.__class__.__thread_join_timeout__
		if thread_join_timeout is not None:
			self.__thread_join_timeout = thread_join_timeout
		self.__thread = None
		self.__stop_event = Event()

		original_start = self.start

		def start():
			if self.__thread is None:
				self.__thread = Thread(target=original_start, name=thread_name)
				self.__thread.start()
		self.start = start

		if join_on_stop is True:
			original_stop = self.stop

			def stop():
				original_stop()
				if self.__thread is not None:
					self.__stop_event.set()
					self.__thread.join(self.__thread_join_timeout)
					self.close_thread()
			self.stop = stop

	def thread(self):
		""" Return current Thread object (or None if task wasn't started)

		:return: Thread or None
		"""
		return self.__thread

	def stop_event(self):
		""" Return stop event object. Flag will be set if this object was constructed with join_on_stop=True

		:return: Event
		"""
		return self.__stop_event

	def join_timeout(self):
		""" Return task join timeout

		:return: int or float
		"""
		return self.__thread_join_timeout

	def close_thread(self):
		""" Clear all object descriptors for stopped task. Task must be joined prior to calling this method.

		:return: None
		"""
		if self.__thread.is_alive() is True:
			raise RuntimeError('Thread is still alive')
		self.__thread = None
		self.__stop_event.clear()

	def started(self):
		""" Get task status. Return True if task was started and wasn't finalized via
		':meth:`.WThreadTask.close_thread`' method call. Return False otherwise.

		:return: bool
		"""
		return self.__thread is not None
