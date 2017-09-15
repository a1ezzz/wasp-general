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
import traceback

from wasp_general.task.base import WStoppableTask, WTask
from wasp_general.verify import verify_type


class WThreadJoiningTimeoutError(Exception):
	""" Exception is raised when thread joining timeout is expired
	"""
	pass


class WThreadTask(WStoppableTask, metaclass=ABCMeta):
	""" Task that runs in a separate thread. Since there is no right way in Python to stop or terminate neighbor
	thread, so it's highly important for derived classes to be capable to stop correctly.

	This class implements :meth:`.WTask.start` method by creating new thread. Thread that is call
	:meth:`.WTask.thread_started` method.
	"""

	__thread_join_timeout__ = 10
	""" Default thread joining time (in seconds)
	"""

	__thread_name__ = None

	@verify_type(thread_name=(str, None), join_on_stop=bool, ready_to_stop=bool)
	@verify_type(thread_join_timeout=(int, float, None))
	def __init__(self, thread_name=None, join_on_stop=True, ready_to_stop=False, thread_join_timeout=None):
		""" Construct new threaded task.

		If 'ready_to_stop' is True, then thread event object is created (can be accessed through
		:meth:`.WThreadTask.ready_event`). This event shows, that this thread task has been done and it
		is ready to be stopped correctly. This event is set automatically after :meth:`.WTask.thread_started`
		method call. So, it implies that this method doesn't call extra thread or process creation,
		or :meth:`.WTask.thread_started` method waits for a thread/process termination. It implies that there
		are no leftover threads or processes (which can be cleaned up later, in the
		:meth:`.WTask.thread_stopped` method).

		If 'join_on_stop' is True, then thread event object is created (can be accessed through
		:meth:`.WThreadTask.stop_event`). This event shows, that there was a request for task to stop. Since
		task can be requested to stop at any time (application terminated, task canceled, ...) , it is
		better to enable and poll this flag. This flag enables automatic call of thread cleanup. When
		this flag is False, then child class must do all the cleaning itself (like
		thread joining and :meth:`.WThreadTask.close_thread` method calling).

		There are two other events - :meth:`.WThreadTask.start_event` and :meth:`.WThreadTask.exception_event`.
		The first one shows that thread function was started (it means that new thread was already created).
		The second one is set when exception is raised inside :meth:`.WThreadTask.thread_started` method.
		All exceptions, that are raised inside thread function, are passed to the
		callback :meth:`.WThreadTask.thread_exception`.

		With both flags ('ready_to_stop' and 'join_on_stop') there can be a situation, when ready event
		wasn't set, but stop event has been set already. This situation shows, that task was terminated
		before completion.

		:note: With join_on_stop flag enabled, :meth:`.WThreadTask.stop` method can not be called from the same
		execution thread. It means, that it can not be called from :meth:`.WThreadTask.start` or
		:meth:`.WThreadTask.thread_started` methods in direct or indirect way. In that case it is better to use
		'ready_to_stop' event polling.

		:param thread_name: name of the thread. It is used in thread constructor as name value only
		:param join_on_stop: define whether to create stop event object or not.
		:param ready_to_stop: define whether to create ready event object or not
		:param thread_join_timeout: timeout for joining operation. If it isn't set then default \
		:attr:`.WThreadTask.__thread_join_timeout__` value will be used. This value is used in \
		:meth:`.WThreadTask.close_thread` method and if thread wasn't stopped for this period of time, then \
		:class:`.WThreadJoiningTimeoutError` exception will be raised.

		note: Most event objects are cleared at :meth:`.WThreadTask.start` method (such as 'ready_event',
		'stop_event', 'exception_event'). But only 'start_event' is cleared at stopping process. It is made
		this way because there may be concurrency if multiple threads that will wait for this thread to
		stop and one of those threads will clear the flag/event before other threads will do their job.
		"""
		WStoppableTask.__init__(self)

		self.__thread_join_timeout = self.__class__.__thread_join_timeout__
		if thread_join_timeout is not None:
			self.__thread_join_timeout = thread_join_timeout
		self.__thread = None
		self.__thread_name = thread_name if thread_name is not None else self.__class__.__thread_name__
		self.__start_event = Event()
		self.__stop_event = Event() if join_on_stop is True else None
		self.__ready_event = Event() if ready_to_stop is True else None
		self.__exception_event = Event()

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

	def start_event(self):
		""" Return event which is set after the thread creation. Shows that a separate thread has been created
		already

		:return: Event
		"""
		return self.__start_event

	def stop_event(self):
		""" Return stop event object. Event will be available if object was constructed with join_on_stop flag

		:return: Event or None
		"""
		return self.__stop_event

	def ready_event(self):
		""" Return readiness event object. Event will be available if object was constructed with ready_to_stop
		flag

		:return: Event or None
		"""
		return self.__ready_event

	def exception_event(self):
		""" Return event which is set if exception is raised inside thread function

		:return: Event
		"""
		return self.__exception_event

	def join_timeout(self):
		""" Return task join timeout

		:return: int or float
		"""
		return self.__thread_join_timeout

	def close_thread(self):
		""" Clear all object descriptors for stopped task. Task must be joined prior to calling this method.

		:return: None
		"""
		if self.__thread is not None and self.__thread.is_alive() is True:
			raise WThreadJoiningTimeoutError('Thread is still alive. Thread name: %s' % self.__thread.name)
		self.start_event().clear()
		self.__thread = None

	def start(self):
		""" :meth:`WStoppableTask.start` implementation that creates new thread
		"""

		start_event = self.start_event()
		stop_event = self.stop_event()
		ready_event = self.ready_event()

		def thread_target():
			try:
				start_event.set()
				self.thread_started()
				if ready_event is not None:
					ready_event.set()
			except Exception as e:
				self.thread_exception(e)
				self.exception_event().set()

		if self.__thread is None:
			if stop_event is not None:
				stop_event.clear()

			if ready_event is not None:
				ready_event.clear()

			self.exception_event().clear()

			self.__thread = Thread(target=thread_target, name=self.thread_name())
			self.__thread.start()

	def stop(self):
		""" :meth:`WStoppableTask.stop` implementation that sets stop even (if available), calls
		:meth:`WStoppableTask.threaded_stopped` and cleans up thread (if configured)
		"""
		thread = self.thread()
		if thread is not None:
			if self.stop_event() is not None:
				self.stop_event().set()

			self.thread_stopped()

			if self.stop_event() is not None:
				thread.join(self.join_timeout())
				self.close_thread()

	@abstractmethod
	def thread_started(self):
		""" Real task that do all the work
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def thread_stopped(self):
		""" Method is called when task is about to stop (is called before joining process).
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	def thread_exception(self, raised_exception):
		""" Callback for handling exception, that are raised inside :meth:`.WThreadTask.thread_started`

		:param raised_exception: raised exception
		:return: None
		"""
		print('Thread execution was stopped by the exception. Exception: %s' % str(raised_exception))
		print('Traceback:')
		print(traceback.format_exc())

	def check_events(self):
		""" Check "stopping"-events ('ready_event', 'stop_event', 'exception_event') if one of them is set.
		Usually True value means that thread is meant to be stopped, means that it is finished its job or
		some error has happened or this thread was asked to stop

		:return: bool
		"""
		return (
			self.ready_event().is_set() is True or
			self.stop_event().is_set() is True or
			self.exception_event().is_set() is True
		)


class WThreadCustomTask(WThreadTask):
	""" Class that can run any task in a separate thread. It just wraps start method, and for a
	:class:`.WStoppableTask` object it wraps stop method also. So for a WThreadTask class task, this object
	will create new thread "inside" new thread. Because of this, it is important that appropriate flags was set
	within constructor
	"""

	@verify_type(task=WTask)
	@verify_type('paranoid', thread_name=(str, None), join_on_stop=bool, ready_to_stop=bool)
	@verify_type('paranoid', thread_join_timeout=(int, float, None))
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

	def thread_started(self):
		""" Start original task

		:return: None
		"""
		self.task().start()

	def thread_stopped(self):
		""" If original task is :class:`.WStoppableTask` object, then stop it

		:return: None
		"""
		task = self.task()
		if isinstance(task, WStoppableTask) is True:
			task.stop()


class WPollingThreadTask(WThreadTask, metaclass=ABCMeta):
	""" Create task, that will be executed in a separate thread, and will wait for stop event or ready event and
	till that will do small piece of work. This threaded task will be constructed with
	'join_on_stop' and 'ready_to_stop' flags turned on

	Polling timeout is a timeout after which next call for a small piece of work will be done. Real
	:meth:`.WPollingThreadTask.__polling_iteration` method implementation must be fast
	(faster then joining timeout), so it must do small piece of work each time only. It is crucial to do that,
	because busy thread can be terminated at any time, and so can not be finalized gracefully.

	If one thread spawns other threads it is obvious to stop them from the same thread they are generated.
	And at this point, wrong joining and polling timeouts could break start-stop mechanics. So parent thread
	should have joining timeout not less then children threads have (it is better to have joining timeout greater
	then children timeout). And polling timeout should be not greater (as little as possible) then children
	threads have
	"""

	__thread_polling_timeout__ = WThreadTask.__thread_join_timeout__ / 4
	""" Default polling timeout
	"""

	@verify_type('paranoid', thread_name=(str, None), thread_join_timeout=(int, float, None))
	@verify_type(polling_timeout=(int, float, None))
	def __init__(self, thread_name=None, thread_join_timeout=None, polling_timeout=None):
		""" Create new task

		:param thread_name: same as 'thread_name' in :meth:`.WThreadTask.__init__`
		:param thread_join_timeout: same as 'thread_join_timeout' in :meth:`.WThreadTask.__init__`
		:param polling_timeout: polling timeout for this task
		"""
		WThreadTask.__init__(
			self, thread_name=thread_name, join_on_stop=True, ready_to_stop=True,
			thread_join_timeout=thread_join_timeout
		)
		self.__polling_timeout = \
			polling_timeout if polling_timeout is not None else self.__class__.__thread_polling_timeout__

	def polling_timeout(self):
		""" Task polling timeout

		:return: int or float
		"""
		return self.__polling_timeout

	def thread_started(self):
		""" Start polling for a stop event or ready event and do small work via
		:meth:`.WPollingThreadTask._polling_iteration` method call

		:return: None
		"""
		while self.check_events() is False:
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

	@verify_type(threaded_task_chain=WThreadTask)
	@verify_type('paranoid', thread_name=(str, None), thread_join_timeout=(int, float, None))
	@verify_type('paranoid', polling_timeout=(int, float, None))
	def __init__(
		self, *threaded_task_chain, thread_name=None, thread_join_timeout=None, polling_timeout=None
	):
		""" Create threaded tasks

		:param threaded_task_chain: tasks to execute
		:param thread_name: same as thread_name in :meth:`WPollingThreadTask.__init__`
		:param thread_join_timeout: same as thread_join_timeout in :meth:`WPollingThreadTask.__init__`
		:param polling_timeout: same as polling_timeout in :meth:`WPollingThreadTask.__init__`
		"""
		WPollingThreadTask.__init__(
			self, thread_name=thread_name, thread_join_timeout=thread_join_timeout,
			polling_timeout=polling_timeout
		)
		self.__task_chain = threaded_task_chain
		for task in self.__task_chain:
			if task.ready_event() is None:
				raise ValueError("Chained task must be constructed with 'ready_to_stop' flag")
		self.__current_task = None

	def _polling_iteration(self):
		""" :meth:`.WPollingThreadTask._polling_iteration` implementation
		"""
		if len(self.__task_chain) > 0:
			if self.__current_task is None:
				self.__current_task = 0

			task = self.__task_chain[self.__current_task]
			if task.thread() is None:
				task.start()
			elif task.ready_event().is_set() is True:
				task.stop()
				if self.__current_task < (len(self.__task_chain) - 1):
					self.__current_task += 1
				else:
					self.ready_event().set()
			elif task.exception_event().is_set() is True:
				raise RuntimeError('Child thread failed')
		else:
			self.ready_event().set()

	def thread_stopped(self):
		""" :meth:`.WThreadTask._polling_iteration` implementation
		"""
		if self.__current_task is not None:
			task = self.__task_chain[self.__current_task]
			task.stop()
			self.__current_task = None
