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

from abc import ABCMeta, abstractmethod
from threading import Thread, Event

from wasp_general.task.base import WTaskStatus, WStoppableTask, WTask
from wasp_general.verify import verify_type


class WThreadJoiningTimeoutError(Exception):
	""" Exception is raised when thread joining timeout is expired
	"""
	pass


class WThreadTask(WStoppableTask, WTaskStatus, metaclass=ABCMeta):
	""" Task that runs in a separate thread.
	"""

	__thread_join_timeout__ = 10
	""" Default thread joining time (in seconds)
	"""

	__thread_name__ = None

	@verify_type(thread_name=(str, None), join_on_stop=bool, ready_to_stop=bool)
	@verify_type(thread_join_timeout=(int, float, None))
	def __init__(self, thread_name=None, join_on_stop=True, ready_to_stop=False, thread_join_timeout=None):
		""" Construct new threaded task. Since there is no right way in Python to stop or terminate neighbor
		thread, so it's highly important for derived classed to be capable to be stopped correctly.

		Original object "start" (and sometimes "stop") methods are "decorated" inside constructor with
		:meth:`.WThreadTask._decorate_start` and :meth:`.WThreadTask._decorate_stop` methods. This decoration
		helps to write derived start method in synchronous (foreground) way, and the same code will be called
		in a separate thread.

		If ready_to_stop is True, then it implies that "start" method doesn't call extra thread or process
		creation, or "start" method waits for a thread/process termination. It implies that there are no
		leftover threads or processes. So if this flag is set, then ready event is accessible via
		:meth:`.WThreadTask.ready_event` method, and this event will be marked at the "start" method end

		If join_on_stop is True, then this constructor wraps stop method with join call (timeout are defined
		with WThreadTask.__thread_join_timeout__ and thread_join_timeout). It means, that derived class can
		be interrupt at any time, so task have to poll :meth:`.WThreadTask.stop_event` event for
		notification of stopping.

		If join_on_stop is False, then child class must do all the stop-work itself (after that
		:meth:`.WThreadTask.close_thread` method must be called, otherwise task wouldn't start again).

		:note: With join_on_stop flag enabled, WThreadTask.stop method can not be called from the same
		execution thread. It means, that it can not be called from WThreadTask.start method in direct or
		indirect way.

		:param thread_name: name of the thread. It is used only in thread constructor as name value
		:param join_on_stop: define whether to decorate stop method or not. If task isn't stop for \
		:meth:`.WThreadTask.join_timeout` period of time, then :class:`.WThreadJoiningTimeoutError` will be \
		raised. When flag is set, stop event object is created (is accessible from \
		:meth:`.WThreadTask.stop_event`)
		:param ready_to_stop: flag creates ready event, which will be set at the task end
		:param thread_join_timeout: timeout for joining operation. If it isn't set then default \
		:attr:`.WThreadTask.__thread_join_timeout__` value will be used.
		"""
		WStoppableTask.__init__(self)
		WTaskStatus.__init__(self, decorate_start=False, decorate_stop=False)

		self.__thread_join_timeout = self.__class__.__thread_join_timeout__
		if thread_join_timeout is not None:
			self.__thread_join_timeout = thread_join_timeout
		self.__thread = None
		self.__thread_name = thread_name if thread_name is not None else self.__class__.__thread_name__
		self.__stop_event = Event() if join_on_stop is True else None
		self.__ready_event = Event() if ready_to_stop is True else None

		self.__original_start = self.start
		self.__original_stop = self.stop

		self._decorate_start()
		self._decorate_stop()

	def thread(self):
		""" Return current Thread object (or None if task wasn't started)

		:return: Thread or None
		"""
		return self.__thread

	def thread_name(self):
		""" Return thread name with which this thread is or will be created

		:return: str
		"""
		return self.__thread_name

	def stop_event(self):
		""" Return stop event object. Flag will be set if this object was constructed with join_on_stop=True

		:return: Event or None
		"""
		return self.__stop_event

	def ready_event(self):
		""" Return readiness event object. Flag will be set if this object was constructed with
		ready_to_stop=True

		:return: Event or None
		"""
		return self.__ready_event

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
			raise WThreadJoiningTimeoutError('Thread is still alive. Thread name: %s' % self.__thread.name)
		self.__thread = None
		if self.__stop_event is not None:
			self.__stop_event.clear()

		if self.__ready_event is not None:
			self.__ready_event.clear()

	def started(self):
		""" Get task status. Return True if task was started and wasn't finalized via
		':meth:`.WThreadTask.close_thread`' method call. Return False otherwise.

		:return: bool
		"""
		return self.__thread is not None

	def original_start(self):
		""" Return original (non-decorated) "start" method

		:return: function
		"""
		return self.__original_start

	def original_stop(self):
		""" Return original (non-decorated) "stop" method

		:return: function
		"""
		return self.__original_stop

	def _decorate_start(self):
		""" Decorate original start method with the thread magic and replace object "start" method

		:return: None
		"""

		thread_target = self.original_start()

		if self.ready_event() is not None:
			def foreground_task():
				self.original_start()()
				self.ready_event().set()

			thread_target = foreground_task

		def start():
			if self.__thread is None:
				self.__thread = Thread(target=thread_target, name=self.thread_name())
				self.__thread.start()
		self.start = start

	def _decorate_stop(self):
		""" Decorate and replace original stop method with the thread finalization routine
		(if appropriate flag was set)

		:return: None
		"""

		if self.stop_event() is None:
			self.stop = self.original_stop()
			return

		def stop():
			thread = self.thread()
			if thread is not None:
				self.stop_event().set()

			self.original_stop()()

			if thread is not None:
				thread.join(self.join_timeout())
				self.close_thread()
		self.stop = stop


class WThreadCustomTask(WThreadTask):
	""" Class that can run any task in a separate thread. It just wraps start method, and for a
	:class:`.WStoppableTask` object it wraps stop method also. So for a WThreadTask class task, this object
	will create new thread "inside" new thread. Because of this, it is important that appropriate flags was set
	within constructor
	"""

	@verify_type(task=WTask, thread_name=(str, None), join_on_stop=bool, ready_to_stop=bool)
	@verify_type(thread_join_timeout=(int, float, None))
	def __init__(self, task, thread_name=None, join_on_stop=True, ready_to_stop=False, thread_join_timeout=None):
		""" Create new WThreadTask task for the given task

		:param task: task that must be started in a separate thread
		:param thread_name: same as thread_name in :meth:`.WThreadTask.__init__` method
		:param join_on_stop: same as join_on_stop in :meth:`.WThreadTask.__init__` method
		:param ready_to_stop: same as ready_to_stop in :meth:`.WThreadTask.__init__` method
		:param thread_join_timeout: same as thread_join_timeout in :meth:`.WThreadTask.__init__` method
		"""
		WThreadTask.__init__(
			self, thread_name=thread_name, join_on_stop=join_on_stop, ready_to_stop=ready_to_stop,
			thread_join_timeout=thread_join_timeout
		)
		self.__task = task

	def task(self):
		""" Return original task

		:return: WTask
		"""
		return self.__task

	def start(self):
		""" Start original task

		:return: None
		"""
		self.task().start()

	def stop(self):
		""" If original task is :class:`.WStoppableTask` object, then stop it

		:return: None
		"""
		task = self.task()
		if isinstance(task, WStoppableTask) is True:
			task.stop()


class WPollingThreadTask(WThreadTask, metaclass=ABCMeta):
	""" Create task, that will be executed in a separate thread, and will wait for stop event and till that
	will do small piece of work

	Polling timeout is a timeout after which next call for a small piece of work will be done. Real
	:meth:`.WPollingThreadTask.__polling_iteration` method implementation must be fast
	(faster then joining timeout), so it must do small piece of work each time only. It is crucial to do that,
	because busy thread can be terminated at any time, and so can not be finalized gracefully.

	If one thread spawns other threads it is obvious to stop them from the same thread they are generated.
	And at this point wrong joining and polling timeouts could break start-stop mechanics. So parent thread
	should have joining timeout not less then children threads have (it is better to have joining timeout greater
	then children timeout). And polling timeout should be not greater (as little as possible is better) then
	children threads have
	"""

	__thread_polling_timeout__ = WThreadTask.__thread_join_timeout__ / 4
	""" Default polling timeout
	"""

	@verify_type(thread_name=(str, None), join_on_stop=bool, ready_to_stop=bool)
	@verify_type(thread_join_timeout=(int, float, None), polling_timeout=(int, float, None))
	def __init__(
		self, thread_name=None, join_on_stop=True, ready_to_stop=False, thread_join_timeout=None,
		polling_timeout=None
	):
		""" Create new task

		:param thread_name: same as 'thread_name' in :meth:`.WThreadTask.__init__`
		:param join_on_stop: same as 'join_on_stop' in :meth:`.WThreadTask.__init__`
		:param ready_to_stop: same as 'ready_to_stop' in :meth:`.WThreadTask.__init__`
		:param thread_join_timeout: same as 'thread_join_timeout' in :meth:`.WThreadTask.__init__`
		:param polling_timeout: polling timeout for this task
		"""
		WThreadTask.__init__(
			self, thread_name=thread_name, join_on_stop=join_on_stop, ready_to_stop=ready_to_stop,
			thread_join_timeout=thread_join_timeout
		)
		self.__polling_timeout = \
			polling_timeout if polling_timeout is not None else self.__class__.__thread_polling_timeout__

	def polling_timeout(self):
		""" Task polling timeout

		:return: int or float
		"""
		return self.__polling_timeout

	def start(self):
		""" Start polling for a stop event and do small work via :meth:`.WPollingThreadTask.__polling_iteration`
		method call

		:return: None
		"""
		while self.stop_event().is_set() is False:
			self._polling_iteration()
			self.stop_event().wait(self.polling_timeout())

	@abstractmethod
	def _polling_iteration(self):
		""" Do small work

		:return: None
		"""
		raise NotImplementedError('This method is abstract')


class WThreadedTaskChain(WPollingThreadTask):
	""" Threaded task, that executes given tasks sequentially
	"""

	@verify_type(threaded_task_chain=WThreadTask, thread_name=(str, None), join_on_stop=bool, ready_to_stop=bool)
	@verify_type(thread_join_timeout=(int, float, None))
	def __init__(
		self, *threaded_task_chain, thread_name=None, join_on_stop=True, ready_to_stop=False,
		thread_join_timeout=None, polling_timeout=None
	):
		""" Create threaded tasks

		:param threaded_task_chain: tasks to execute
		:param thread_name: same as thread_name in :meth:`WPollingThreadTask.__init__`
		:param join_on_stop: same as join_on_stop in :meth:`WPollingThreadTask.__init__`
		:param ready_to_stop: same as ready_to_stop in :meth:`WPollingThreadTask.__init__`
		:param thread_join_timeout: same as thread_join_timeout in :meth:`WPollingThreadTask.__init__`
		:param polling_timeout: same as polling_timeout in :meth:`WPollingThreadTask.__init__`
		"""
		WPollingThreadTask.__init__(
			self, thread_name=thread_name, join_on_stop=join_on_stop, ready_to_stop=ready_to_stop,
			thread_join_timeout=thread_join_timeout, polling_timeout=polling_timeout
		)
		self.__task_chain = threaded_task_chain
		self.__current_task = None

	def _polling_iteration(self):
		""" :meth:`.WPollingThreadTask._polling_iteration` implementation
		"""
		if len(self.__task_chain) > 0:
			if self.__current_task is None:
				self.__current_task = 0

			task = self.__task_chain[self.__current_task]
			if task.started() is False:
				task.start()
			elif task.stop_event().is_set() is True:
				task.stop()
				if self.__current_task < (len(self.__task_chain) - 1):
					self.__current_task += 1
				else:
					self.stop_event().set()
		else:
			self.stop_event().set()

	def stop(self):
		""" :meth:`.WThreadTask._polling_iteration` implementation
		"""
		if self.__current_task is not None:
			task = self.__task_chain[self.__current_task]
			task.stop()
			self.__current_task = None
