# -*- coding: utf-8 -*-
# wasp_general/task/scheduler/scheduler.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

import uuid
from datetime import timezone
from threading import Event

from wasp_general.verify import verify_type, verify_value, verify_subclass
from wasp_general.thread import WCriticalResource
from wasp_general.datetime import utc_datetime

from wasp_general.task.scheduler.proto import WScheduledTask, WRunningTaskRegistryProto, WTaskSchedulerProto
from wasp_general.task.scheduler.proto import WTaskSchedule, WRunningScheduledTask, WTaskSourceProto
from wasp_general.task.thread import WPollingThreadTask


class WSchedulerWatchdog(WCriticalResource, WPollingThreadTask):
	""" Class that is looking for execution process of scheduled task. Each scheduled task has its own
	watchdog. Watchdog that will un-register stopped task from registry of running tasks
	"""

	__thread_polling_timeout__ = WPollingThreadTask.__thread_polling_timeout__ / 2
	""" Polling timeout
	"""

	__scheduled_task_startup_timeout__ = WPollingThreadTask.__thread_polling_timeout__ / 2
	""" Timeout for scheduled task to start (thread creation time)
	"""

	__lock_acquiring_timeout__ = 5
	""" Timeout with which critical section lock must be acquired
	"""

	@classmethod
	@verify_type('paranoid', task_schedule=WTaskSchedule)
	def create(cls, task_schedule, registry, thread_name):
		""" Core method for watchdog creation. Derived classes may redefine this method in order to change
		watchdog creation process

		:param task_schedule: scheduled task that is ready to be executed
		:param registry: registry that is created this watchdog and registry that must be notified of \
		scheduled task stopping
		:param thread_name: name of watch dog thread
		:return:
		"""
		return cls(task_schedule, registry, thread_name)

	@verify_type(task_schedule=WTaskSchedule)
	@verify_type('paranoid', thread_name=str)
	def __init__(self, task_schedule, registry, thread_name):
		""" Create new watch dog.

		:param task_schedule: scheduled task that is ready to be executed
		:param registry: registry that is created this watch dog and registry that must be notified of \
		scheduled task stopping
		:param thread_name: name of watch dog thread

		note: :class:`.WRunningTaskRegistry` is using :meth:`.WSchedulerWatchdog.create` method for watch
		dog creation
		"""
		WCriticalResource.__init__(self)
		WPollingThreadTask.__init__(self, thread_name=thread_name)
		if isinstance(registry, WRunningTaskRegistry) is False:
			raise TypeError('Invalid registry type')

		self.__task_schedule = task_schedule
		self.__registry = registry
		self.__started_at = None
		self.__task = None

	def task_schedule(self):
		""" Return scheduled task

		:return: WTaskSchedule
		"""
		return self.__task_schedule

	def registry(self):
		""" Return parent registry

		:return: WRunningTaskRegistry
		"""
		return self.__registry

	def started_at(self):
		""" Return datetime in UTC timezone when the scheduled task was started

		:return: datetime in UTC or None
		"""
		return self.__started_at

	def start(self):
		""" Start scheduled task and start watching

		:return: None
		"""
		self.__dog_started()
		WPollingThreadTask.start(self)

	def thread_started(self):
		""" Start watchdog thread function

		:return: None
		"""
		self.__thread_started()
		WPollingThreadTask.thread_started(self)

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def __dog_started(self):
		""" Prepare watchdog for scheduled task starting

		:return: None
		"""
		if self.__task is not None:
			raise RuntimeError('Unable to start task. In order to start a new task - at first stop it')

		self.__started_at = utc_datetime()
		self.__task = self.task_schedule().task()
		if isinstance(self.__task, WScheduledTask) is False:
			task_class = self.__task.__class__.__qualname__
			raise RuntimeError('Unable to start unknown type of task: %s' % task_class)

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def __thread_started(self):
		""" Start a scheduled task

		:return: None
		"""
		if self.__task is None:
			raise RuntimeError('Unable to start thread without "start" method call')
		self.__task.start()
		self.__task.start_event().wait(self.__scheduled_task_startup_timeout__)

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def _polling_iteration(self):
		""" Poll for scheduled task stop events

		:return: None
		"""
		if self.__task is None:
			self.ready_event().set()
		elif self.__task.check_events() is True:
			self.ready_event().set()
			self.registry().task_finished(self)

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def thread_stopped(self):
		""" Stop scheduled task beacuse of watchdog stop

		:return: None
		"""
		if self.__task is not None:
			self.__task.stop()
			self.__started_at = None
			self.__task = None

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def running_task(self):
		""" Return information about running scheduled task. If task is not running (for example in the middle
		of a termination) - None is returned

		:return: WRunningScheduledTask or None
		"""
		started_at = self.started_at()
		if started_at is None:
			return
		return WRunningScheduledTask(self.task_schedule(), started_at)


class WRunningTaskRegistry(WCriticalResource, WRunningTaskRegistryProto, WPollingThreadTask):
	""" Registry of started scheduled tasks. Has :meth:`.WRunningTaskRegistry.cleanup_event` event that is set when
	any of running scheduled task stopped. This event starts process of internal clean up (descriptors that were
	created for shceduled task - will be removed)
	"""

	__thread_polling_timeout__ = WPollingThreadTask.__thread_polling_timeout__ / 4
	""" Polling timeout
	"""

	__watchdog_startup_timeout__ = WSchedulerWatchdog.__thread_polling_timeout__
	""" Timeout for watchdog to start (thread creation time)
	"""

	__lock_acquiring_timeout__ = 5
	""" Timeout with which critical section lock must be acquired
	"""

	@verify_subclass(watchdog_cls=(WSchedulerWatchdog, None))
	def __init__(self, watchdog_cls=None):
		""" Create new registry

		:param watchdog_cls: watchdog that should be used (:class:`.WSchedulerWatchdog` by default)
		"""
		WCriticalResource.__init__(self)
		WRunningTaskRegistryProto.__init__(self)
		WPollingThreadTask.__init__(self, thread_name='SchedulerRegistry')
		self.__running_registry = []
		self.__done_registry = []
		self.__cleanup_event = Event()
		self.__watchdog_cls = watchdog_cls if watchdog_cls is not None else WSchedulerWatchdog

	def cleanup_event(self):
		""" Return "cleanup" event

		:return: Event
		"""
		return self.__cleanup_event

	def watchdog_class(self):
		""" Return watchdog class that is used by this registry

		:return: WSchedulerWatchdog class or subclass
		"""
		return self.__watchdog_cls

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	@verify_type('paranoid', task_schedule=WTaskSchedule)
	def exec(self, task_schedule):
		""" Start the given task (no checks are made by this method, task will be started as is)

		:param task_schedule: scheduled task to start

		:return: None
		"""
		watchdog = self.watchdog_class().create(
			task_schedule, self, 'TaskScheduler-Watchdog-%s' % str(uuid.uuid4())
		)
		watchdog.start()
		watchdog.start_event().wait(self.__watchdog_startup_timeout__)
		self.__running_registry.append(watchdog)

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def running_tasks(self):
		""" Return scheduled tasks that are running at the moment

		:return: tuple of WRunningScheduledTask
		"""
		return tuple(filter(lambda x: x is not None, [x.running_task() for x in self.__running_registry]))

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def __len__(self):
		""" Return number of running tasks

		:return: int
		"""
		return len(self.__running_registry)

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	@verify_type(watchdog=WSchedulerWatchdog)
	def task_finished(self, watchdog):
		""" Handle/process scheduled task stop

		:param watchdog: watchdog of task that was stopped

		:return: None
		"""
		if watchdog in self.__running_registry:  # when cleanup hits stop
			self.__running_registry.remove(watchdog)
			self.__done_registry.append(watchdog)
			self.cleanup_event().set()

	def _polling_iteration(self):
		""" Poll for cleanup event

		:return: None
		"""
		if self.cleanup_event().is_set() is True:
			self.cleanup()

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def cleanup(self):
		""" Do cleanup (stop and remove watchdogs that are no longer needed)

		:return: None
		"""
		for task in self.__done_registry:
			task.stop()
		self.__done_registry.clear()
		self.cleanup_event().clear()

	def thread_stopped(self):
		""" Handle registry stop

		:return: None
		"""
		self.cleanup()
		self.stop_running_tasks()

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def stop_running_tasks(self):
		""" Terminate all the running tasks

		:return: None
		"""
		for task in self.__running_registry:
			task.stop()
		self.__running_registry.clear()


class WPostponedTaskRegistry:
	""" Registry for postponed tasks.
	"""

	@verify_type(maximum_tasks=(int, None))
	@verify_value(maximum_tasks=lambda x: x is None or x >= 0)
	def __init__(self, maximum_tasks=None):
		""" Create new registry

		:param maximum_tasks: maximum number of tasks to postpone (no limit by default)
		"""
		self.__tasks = []
		self.__maximum_tasks = maximum_tasks

	def maximum_tasks(self):
		""" Return maximum number of tasks to postpone

		:return: int
		"""
		return self.__maximum_tasks

	@verify_type(task_schedule=WTaskSchedule)
	def postpone(self, task_schedule):
		""" Postpone (if required) the given task. The real action is depended on task postpone policy

		:param task_schedule: task to postpone
		:return: None
		"""

		maximum_tasks = self.maximum_tasks()
		if maximum_tasks is not None and len(self.__tasks) >= maximum_tasks:
			task_schedule.task_dropped()
			return

		task_policy = task_schedule.policy()
		task_id = task_schedule.task_id()

		if task_policy == WTaskSchedule.PostponePolicy.wait:
			self.__tasks.append(task_schedule)

		elif task_policy == WTaskSchedule.PostponePolicy.drop:
			task_schedule.task_dropped()

		elif task_policy == WTaskSchedule.PostponePolicy.postpone_first:
			if task_id is None:
				self.__tasks.append(task_schedule)
			else:
				schedule_found = None
				for previous_scheduled_task, task_index in self.__search_task(task_id):
					if previous_scheduled_task.policy() != task_policy:
						raise RuntimeError('Invalid tasks policies')
					schedule_found = previous_scheduled_task
					break

				if schedule_found is not None:
					task_schedule.task_dropped()
				else:
					self.__tasks.append(task_schedule)

		elif task_policy == WTaskSchedule.PostponePolicy.postpone_last:
			if task_id is None:
				self.__tasks.append(task_schedule)
			else:
				schedule_found = None
				for previous_scheduled_task, task_index in self.__search_task(task_id):
					if previous_scheduled_task.policy() != task_policy:
						raise RuntimeError('Invalid tasks policies')
					schedule_found = task_index
					break

				if schedule_found is not None:
					self.__tasks.pop(schedule_found).task_dropped()

				self.__tasks.append(task_schedule)
		else:
			raise RuntimeError('Invalid policy spotted')

	@verify_type(task_id=str)
	def __search_task(self, task_id):
		""" Search (iterate over) for tasks with the given task id

		:param task_id: target id

		:return: None
		"""
		for i in range(len(self.__tasks)):
			task_schedule = self.__tasks[i]
			if task_schedule.task_id() == task_id:
				yield task_schedule, i

	def has_tasks(self):
		""" Check if there are postpone tasks. True - there is at least one postpone task, False - otherwise

		:return: bool
		"""
		return len(self.__tasks) > 0

	def __len__(self):
		""" Return number of postponed tasks

		:return: int
		"""
		return len(self.__tasks)

	def __iter__(self):
		""" Iterate over postpone tasks. Once task is yield from this method, this task is removed from registry

		:return: None
		"""
		while len(self.__tasks) > 0:
			yield self.__tasks.pop(0)


class WTaskSourceRegistry:
	""" Registry of tasks sources. It works as a dynamic queue - every task source notify this registry when
	next task should be started. And this registry return those tasks that is about to start. Registry is able
	to return tasks from different sources at one time.
	"""

	def __init__(self):
		""" Create new registry
		"""
		self.__sources = {}

		self.__next_start = None
		self.__next_sources = []

	@verify_type(task_source=WTaskSourceProto)
	def add_source(self, task_source):
		""" Add new tasks source

		:param task_source:

		:return: None
		"""
		next_start = task_source.next_start()
		self.__sources[task_source] = next_start
		self.__update(task_source)

	@verify_type(task_source=(WTaskSourceProto, None))
	def update(self, task_source=None):
		""" Recheck next start of tasks from all the sources (or from the given one only)

		:param task_source: if defined - source to check

		:return: None
		"""
		if task_source is not None:
			self.__update(task_source)
		else:
			self.__update_all()

	def __update_all(self):
		""" Recheck next start of tasks from all the sources

		:return: None
		"""
		self.__next_start = None
		self.__next_sources = []

		for source in self.__sources:
			self.__update(source)

	@verify_type(task_source=WTaskSourceProto)
	def __update(self, task_source):
		""" Recheck next start of tasks from the given one only

		:param task_source: source to check

		:return: None
		"""
		next_start = task_source.next_start()
		if next_start is not None:

			if next_start.tzinfo is None or next_start.tzinfo != timezone.utc:
				raise ValueError('Invalid timezone information')

			if self.__next_start is None or next_start < self.__next_start:
				self.__next_start = next_start
				self.__next_sources = [task_source]
			elif next_start == self.__next_start:
				self.__next_sources.append(task_source)

	def check(self):
		""" Check if there are tasks to start and return them if there are any

		:return: tuple of WTaskSchedule or None (if there are no tasks to start)
		"""
		if self.__next_start is not None:
			utc_now = utc_datetime()
			if utc_now >= self.__next_start:
				result = []

				for task_source in self.__next_sources:
					scheduled_tasks = task_source.has_tasks()
					if scheduled_tasks is not None:
						result.extend(scheduled_tasks)

				self.__update_all()

				if len(result) > 0:
					return tuple(result)

	def task_sources(self):
		""" Return task sources that was added to this registry

		:return: tuple of WTaskSourceProto
		"""
		return tuple(self.__sources.keys())


class WTaskSchedulerService(WCriticalResource, WTaskSchedulerProto, WPollingThreadTask):
	""" Main scheduler service. This class unites different registries to present entire scheduler
	"""

	__thread_polling_timeout__ = WPollingThreadTask.__thread_polling_timeout__ / 8
	""" Polling timeout
	"""
	__lock_acquiring_timeout__ = 5
	""" Timeout with which critical section lock must be acquired
	"""

	__default_maximum_running_tasks__ = 10
	""" Number of tasks that are able to run simultaneously that is used by default
	"""

	@verify_type('paranoid', maximum_postponed_tasks=(int, None))
	@verify_value('paranoid', maximum_postponed_tasks=lambda x: x is None or x > 0)
	@verify_type(maximum_running_tasks=(int, None), running_tasks_registry=(WRunningTaskRegistry, None))
	@verify_type(postponed_tasks_registry=(WPostponedTaskRegistry, None))
	@verify_value(maximum_running_tasks=lambda x: x is None or x > 0)
	def __init__(
		self, maximum_running_tasks=None, running_tasks_registry=None, maximum_postponed_tasks=None,
		postponed_tasks_registry=None
	):
		""" Create new scheduler

		:param maximum_running_tasks: number of tasks that are able to run simultaneously \
		(WTaskSchedulerService.__default_maximum_running_tasks__ is used as default value)
		:param running_tasks_registry: registry for running tasks
		:param maximum_postponed_tasks: number of tasks that are able to be postponed (no limit by default)
		:param postponed_tasks_registry: registry for postponed tasks
		"""
		WCriticalResource.__init__(self)
		WTaskSchedulerProto.__init__(self)
		WPollingThreadTask.__init__(self, thread_name='TaskScheduler')

		if maximum_postponed_tasks is not None and postponed_tasks_registry is not None:
			raise ValueError(
				'Conflict values found. Unable to instantiate scheduler service with '
				'"maximum_postponed_tasks" and "postponed_tasks_registry" values (chose one)'
			)

		default = lambda x, y: x if x is not None else y

		self.__maximum_running_tasks = default(
			maximum_running_tasks, self.__class__.__default_maximum_running_tasks__
		)

		self.__running_tasks_registry = default(running_tasks_registry, WRunningTaskRegistry())
		self.__postponed_tasks_registry = WPostponedTaskRegistry(maximum_postponed_tasks)
		self.__sources_registry = WTaskSourceRegistry()

		self.__awake_at = None

	def maximum_running_tasks(self):
		""" Return number of tasks that are able to run simultaneously

		:return: int
		"""
		return self.__maximum_running_tasks

	def maximum_postponed_tasks(self):
		""" Return number of tasks that are able to be postponed

		:return: int or None (for no limit)
		"""
		return self.__postponed_tasks_registry.maximum_tasks()

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	@verify_type('paranoid', task_source=WTaskSourceProto)
	def add_task_source(self, task_source):
		""" Add tasks source

		:param task_source: task source to add

		:return: None
		"""
		self.__sources_registry.add_source(task_source)

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def task_sources(self):
		""" Return task sources that was added to this scheduler

		:return: tuple of WTaskSourceProto
		"""
		return self.__sources_registry.task_sources()

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	@verify_type('paranoid', task_source=(WTaskSourceProto, None))
	def update(self, task_source=None):
		""" Recheck next start of tasks from all the sources (or from the given one only)

		:param task_source: if defined - source to check

		:return: None
		"""
		self.__sources_registry.update(task_source=task_source)

	def running_tasks(self):
		""" Return scheduled tasks that are running at the moment

		:return: tuple of WRunningScheduledTask
		"""
		return self.__running_tasks_registry.running_tasks()

	def thread_started(self):
		""" Start required registries and start this scheduler

		:return: None
		"""
		self.__running_tasks_registry.start()
		self.__running_tasks_registry.start_event().wait()
		WPollingThreadTask.thread_started(self)

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def _polling_iteration(self):
		""" Poll for different scheduler events like: there are tasks to run, there are tasks to postpone
		there are postponed tasks that should be running

		:return: None
		"""
		scheduled_tasks = self.__sources_registry.check()
		has_postponed_tasks = self.__postponed_tasks_registry.has_tasks()
		maximum_tasks = self.maximum_running_tasks()

		if scheduled_tasks is not None or has_postponed_tasks is not None:
			running_tasks = len(self.__running_tasks_registry)

			if running_tasks >= maximum_tasks:
				if scheduled_tasks is not None:
					for task in scheduled_tasks:
						self.__postponed_tasks_registry.postpone(task)
			else:
				if has_postponed_tasks is True:
					for postponed_task in self.__postponed_tasks_registry:
						self.__running_tasks_registry.exec(postponed_task)
						running_tasks += 1
						if running_tasks >= maximum_tasks:
							break

				if scheduled_tasks is not None:
					for task in scheduled_tasks:
						if running_tasks >= maximum_tasks:
							self.__postponed_tasks_registry.postpone(task)
						else:
							self.__running_tasks_registry.exec(task)
							running_tasks += 1

	@WCriticalResource.critical_section(timeout=__lock_acquiring_timeout__)
	def thread_stopped(self):
		""" Stop registries and this scheduler

		:return: None
		"""
		self.__running_tasks_registry.stop()
