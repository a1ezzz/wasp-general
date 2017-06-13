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

# TODO: document the code
# TODO: write tests for the code

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


class WSchedulerWatchingDog(WPollingThreadTask):

	__thread_polling_timeout__ = WPollingThreadTask.__thread_polling_timeout__ / 2

	@classmethod
	@verify_type(task_schedule=WTaskSchedule)
	def create(cls, task_schedule, registry, thread_name):
		return cls(task_schedule, registry, thread_name)

	@verify_type(task_schedule=WTaskSchedule)
	def __init__(self, task_schedule, registry, thread_name):
		WPollingThreadTask.__init__(self, thread_name=thread_name)
		if isinstance(registry, WRunningTaskRegistry) is False:
			raise TypeError('Invalid registry type')

		self.__task_schedule = task_schedule
		self.__registry = registry
		self.__started_at = None
		self.__task = None

	def task_schedule(self):
		return self.__task_schedule

	def registry(self):
		return self.__registry

	def started_at(self):
		return self.__started_at

	def start(self):
		self.__started_at = utc_datetime()
		self.__task = self.task_schedule().task()
		if isinstance(self.__task, WScheduledTask) is False:
			task_class = self.__task.__class__.__qualname__
			raise RuntimeError('Unable to start unknown type of task: %s' % task_class)

		self.__task.start()
		WPollingThreadTask.start(self)

	def _polling_iteration(self):
		if self.__task.ready_event().is_set() is True:
			self.registry().task_finished(self)

	def stop(self):
		self.task_schedule().task().stop()
		self.__started_at = None
		self.__task = None

	def running_task(self):
		started_at = self.started_at()
		if started_at is None:
			raise RuntimeError("Task isn't running")
		return WRunningScheduledTask(self.task_schedule(), started_at)


class WRunningTaskRegistry(WCriticalResource, WRunningTaskRegistryProto, WPollingThreadTask):

	@verify_subclass(watching_dog_cls=(WSchedulerWatchingDog, None))
	def __init__(self, watching_dog_cls=None):
		WCriticalResource.__init__(self)
		WRunningTaskRegistryProto.__init__(self)
		WPollingThreadTask.__init__(self, thread_name='SchedulerRegistry')
		self.__running_registry = []
		self.__done_registry = []
		self.__cleanup_event = Event()
		self.__watching_dog_cls = watching_dog_cls if watching_dog_cls is not None else WSchedulerWatchingDog

	def cleanup_event(self):
		return self.__cleanup_event

	def watching_dog_class(self):
		return self.__watching_dog_cls

	@WCriticalResource.critical_section()
	@verify_type(task_schedule=WTaskSchedule)
	def exec(self, task_schedule):
		watching_dog = self.watching_dog_class().create(
			task_schedule, self, 'TaskSchedulerWatchingDog-%s' % str(uuid.uuid4())
		)
		watching_dog.start()
		self.__running_registry.append(watching_dog)

	@WCriticalResource.critical_section()
	def running_tasks(self):
		return [x.running_task() for x in self.__running_registry]

	@WCriticalResource.critical_section()
	def __len__(self):
		return len(self.__running_registry)

	@WCriticalResource.critical_section()
	def task_finished(self, watching_dog):
		if isinstance(watching_dog, WSchedulerWatchingDog) is False:
			raise TypeError('Invalid type of watching dog')
		self.__running_registry.remove(watching_dog)
		self.__done_registry.append(watching_dog)
		self.cleanup_event().set()

	def _polling_iteration(self):
		if self.cleanup_event().is_set() is True:
			self.cleanup()

	@WCriticalResource.critical_section()
	def cleanup(self):
		for task in self.__done_registry:
			task.stop()
		self.__done_registry.clear()
		self.cleanup_event().clear()

	def stop(self):
		self.cleanup()
		self.stop_running_tasks()

	@WCriticalResource.critical_section()
	def stop_running_tasks(self):
		for task in self.__running_registry:
			task.stop()
		self.__running_registry.clear()


class WPostponedTaskRegistry:

	def __init__(self, maximum_tasks):
		self.__tasks = []
		self.__maximum_tasks = maximum_tasks

	def maximum_tasks(self):
		return self.__maximum_tasks

	@verify_type(task_schedule=WTaskSchedule)
	def postpone(self, task_schedule):

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
				for previous_schedule in self.__search_task(task_id):
					if previous_schedule.policy() != task_policy:
						raise RuntimeError('Invalid tasks policies')
					schedule_found = previous_schedule

				if schedule_found is not None:
					task_schedule.task_dropped()
				else:
					self.__tasks.append(task_schedule)

		elif task_policy == WTaskSchedule.PostponePolicy.postpone_last:
			if task_id is None:
				self.__tasks.append(task_schedule)
			else:
				for previous_schedule in self.__search_task(task_id):
					if previous_schedule.policy() != task_policy:
						raise RuntimeError('Invalid tasks policies')
					previous_schedule.task_dropped()

				self.__tasks.append(task_schedule)
		else:
			raise RuntimeError('Invalid policy spotted')

	@verify_type(task_id=str)
	def __search_task(self, task_id):
		for task_schedule in self.__tasks:
			if task_schedule.task_id() == task_id:
				yield task_schedule

	def has_tasks(self):
		return len(self.__tasks) > 0

	def __len__(self):
		return len(self.__tasks)

	def __iter__(self):
		while len(self.__tasks) > 0:
			task_schedule = self.__tasks[0]
			self.__tasks = self.__tasks[1:]
			yield task_schedule


class WTaskSourceRegistry(WCriticalResource):

	__thread_polling_timeout__ = WPollingThreadTask.__thread_polling_timeout__ / 4

	def __init__(self):
		WCriticalResource.__init__(self)
		self.__sources = {}

		self.__next_start = None
		self.__next_sources = []

	@WCriticalResource.critical_section()
	@verify_type(task_source=WTaskSourceProto)
	def add_source(self, task_source):
		next_start = task_source.next_start()
		self.__sources[task_source] = next_start
		self.__update(task_source)

	@WCriticalResource.critical_section()
	def update(self, task_source=None):
		if task_source is not None:
			self.__update(task_source)
		else:
			self.__update_all()

	def __update_all(self):
		self.__next_start = None
		self.__next_sources = []

		for source in self.__sources:
			self.__update(source)

	@verify_type(task_source=WTaskSourceProto)
	def __update(self, task_source):
		next_start = task_source.next_start()
		if next_start is not None:

			if next_start.tzinfo is None or next_start.tzinfo != timezone.utc:
				raise ValueError('Invalid timezone information')

			if self.__next_start is None or next_start < self.__next_start:
				self.__next_start = next_start
				self.__next_sources = [task_source]
			elif next_start == self.__next_start:
				self.__next_sources.append(task_source)

	@WCriticalResource.critical_section()
	def check(self):
		if self.__next_start is not None:
			utc_now = utc_datetime()
			if utc_now >= self.__next_start:
				result = []

				for task_source in self.__next_sources:
					task_schedule = task_source.has_tasks()
					if task_schedule is not None:
						result.extend(task_schedule)

				self.__update_all()

				if len(result) > 0:
					return result


class WTaskSchedulerService(WTaskSchedulerProto, WPollingThreadTask):

	__thread_polling_timeout__ = WPollingThreadTask.__thread_polling_timeout__ / 4
	__default_maximum_running_tasks__ = 10

	@verify_type(maximum_running_tasks=(int, None), maximum_postponed_tasks=(int, None))
	@verify_value(maximum_running_tasks=lambda x: x is None or x > 0)
	@verify_value(maximum_postponed_tasks=lambda x: x is None or x > 0)
	@verify_subclass(watching_dog_cls=(WSchedulerWatchingDog, None))
	def __init__(self, maximum_running_tasks=None, maximum_postponed_tasks=None, watching_dog_cls=None):
		WTaskSchedulerProto.__init__(self)
		WPollingThreadTask.__init__(self, thread_name='TaskScheduler')

		self.__maximum_running_tasks = self.__class__.__default_maximum_running_tasks__
		if maximum_running_tasks is not None:
			self.__maximum_running_tasks = maximum_running_tasks

		self.__running_tasks_registry = WRunningTaskRegistry(watching_dog_cls=watching_dog_cls)
		self.__postponed_tasks_registry = WPostponedTaskRegistry(maximum_postponed_tasks)
		self.__sources_registry = WTaskSourceRegistry()

		self.__awake_at = None

	def maximum_running_tasks(self):
		return self.__maximum_running_tasks

	def maximum_postponed_tasks(self):
		return self.__postponed_tasks_registry.maximum_tasks()

	@verify_type(task_source=WTaskSourceProto)
	def add_task_source(self, task_source):
		self.__sources_registry.add_source(task_source)

	def update(self, task_source=None):
		self.__sources_registry.update(task_source=task_source)

	def start(self):
		self.__running_tasks_registry.start()
		WPollingThreadTask.start(self)

	def _polling_iteration(self):
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

	def stop(self):
		self.__running_tasks_registry.stop()
