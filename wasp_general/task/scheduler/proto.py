# -*- coding: utf-8 -*-
# wasp_general/task/scheduler/proto.py
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
from abc import ABCMeta, abstractmethod
from enum import Enum
from datetime import datetime, timezone

from wasp_general.verify import verify_type, verify_value

from wasp_general.task.thread import WThreadTask


class WScheduledTask(WThreadTask):
	""" Class represent task that may run by a scheduler
	Every scheduled task must be able:
		- to be stopped at any time
		- to return its status (running or stopped)
		- to notify when task end (thread event)

	note: derived classes must implement :meth:`.WThreadTask.thread_started` and :meth:`.WThreadTask.thread_stopped`
	methods in order to be instantiable
	"""

	__thread_name_prefix__ = 'ScheduledTask-'
	""" Thread name prefix
	"""

	@verify_type(thread_name_suffix=(str, None))
	@verify_type('paranoid', thread_join_timeout=(int, float, None))
	def __init__(self, thread_name_suffix=None, thread_join_timeout=None):
		""" Create new task

		:param thread_name_suffix: suffix that applies to thread name (if is not specified - uuid4 is used)
		:param thread_join_timeout: same as thread_join_timeout in :meth:`.WThreadTask.__init__` method
		"""

		if thread_name_suffix is None:
			thread_name_suffix = str(uuid.uuid4())

		WThreadTask.__init__(
			self, thread_name=(self.__thread_name_prefix__ + thread_name_suffix), join_on_stop=True,
			ready_to_stop=True, thread_join_timeout=thread_join_timeout
		)


class WTaskSchedule:
	""" This class specifies how :class:`.WScheduledTask` should run. It should be treated as scheduler record
	without execution time.

	:class:`.WTaskSchedule` has a policy, that describes what scheduler should do if it can not run this task
	at the specified moment. This policy is a recommendation for a scheduler and a scheduler can omit it if
	(for example) a scheduler queue is full. In any case, if this task is dropped (skipped) from being running
	"on_drop" callback is called (it invokes via :meth:`.WTaskSchedule.task_dropped` method)

	note: It is important that tasks with the same id (task_id) have the same postpone policy. If they do not have
	the same policy, then exception may be raised. No pre-checks are made to resolve this, because of unpredictable
	logic of different tasks from different sources
	"""
	# TODO: add policy that resolves concurrency of running tasks (like skipping tasks, that is already running)

	class PostponePolicy(Enum):
		""" Specifies what should be with this task if a scheduler won't be able to run it (like if the
		scheduler limit of running tasks is reached).
		"""
		wait = 1  # will stack every postponed task to execute them later (default)
		drop = 2  # drop this task if it can't be executed at the moment
		postpone_first = 3  # stack the first task and drop all the following tasks with the same task ID
		postpone_last = 4  # stack the last task and drop all the previous tasks with the same task ID

	@verify_type(task=WScheduledTask, task_id=(str, None))
	@verify_value(on_drop=lambda x: x is None or callable(x))
	def __init__(self, task, policy=None, task_id=None, on_drop=None):
		""" Create new schedule record

		:param task: task to run
		:param policy: postpone policy
		:param task_id: identifier that groups different scheduler records and single postpone policy
		:param on_drop: callback, that must be called if this task is skipped
		"""

		if policy is not None and isinstance(policy, WTaskSchedule.PostponePolicy) is False:
			raise TypeError('Invalid policy object type')

		self.__task = task
		self.__policy = policy if policy is not None else WTaskSchedule.PostponePolicy.wait
		self.__task_id = task_id
		self.__on_drop = on_drop

	def task(self):
		""" Return task that should be run

		:return: WScheduledTask
		"""
		return self.__task

	def policy(self):
		""" Return postpone policy

		:return: WTaskScheduleProto.PostponePolicy
		"""
		return self.__policy

	def task_id(self):
		""" Return task id

		:return: str or None

		see :meth:`.WTaskSchedule.__init__`
		"""
		return self.__task_id

	def task_dropped(self):
		""" Call a "on_drop" callback. This method is executed by a scheduler when it skip this task

		:return: None
		"""
		if self.__on_drop is not None:
			return self.__on_drop()


class WRunningScheduledTask:
	""" This is a descriptor for running scheduler records (:class:`.WTaskSchedule`)
	"""

	@verify_type(schedule=WTaskSchedule, started_at=datetime)
	@verify_value(starting_datetime=lambda x: x.tzinfo is not None and x.tzinfo == timezone.utc)
	def __init__(self, schedule, started_at):
		""" Create new descriptor

		:param schedule: started schedule record
		:param started_at: datetime when the specified task was started (it must be specified in UTC timezone)
		"""
		self.__scheduled = schedule
		self.__started_at = started_at

	def task_schedule(self):
		""" Return started schedule record

		:return: WTaskSchedule
		"""
		return self.__scheduled

	def started_at(self):
		""" Return datetime when this task was started

		:return: datetime in UTC timezone
		"""
		return self.__started_at


class WTaskSourceProto(metaclass=ABCMeta):
	""" Prototype for scheduler record generator. :class:`.WTaskSchedulerProto` doesn't have scheduler as set of
	scheduler records. Instead, a scheduler uses this class as scheduler records holder and checks if it is time
	to execute them.
	"""

	@abstractmethod
	def has_tasks(self):
		""" Return tasks that should be run at the moment.


		:return: tuple of WTaskSchedule (tuple with one element at least) or None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def next_start(self):
		""" Return datetime when the next task should be executed.

		:return: datetime in UTC timezone
		"""
		raise NotImplementedError('This method is abstract')


class WRunningTaskRegistryProto(metaclass=ABCMeta):
	""" This class describes a registry of running tasks. It executes a scheduler record (:class:`.WTaskSchedule`),
	creates and store the related descriptor (:class:`.WRunningScheduledTask`), and watches that tasks are running
	"""

	@abstractmethod
	@verify_type(task_schedule=WTaskSchedule)
	def exec(self, task_schedule):
		""" Execute the given scheduler record (no checks are made at this method, task executes as is)

		:param task_schedule: task to execute

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def running_tasks(self):
		""" Return tuple of running tasks

		:return: tuple of WRunningScheduledTask
		"""
		raise NotImplementedError('This method is abstract')


class WTaskSchedulerProto(metaclass=ABCMeta):
	""" Represent a scheduler. A core of wasp_general.task.scheduler module
	"""

	@abstractmethod
	@verify_type(task_source=(WTaskSourceProto, None))
	def update(self, task_source=None):
		""" Update task sources information about next start. Update information for the specified source
		or for all of them

		This method implementation must be thread-safe as different threads (different task source, different
		registries) may modify scheduler internal state.
		:return:
		"""
		raise NotImplementedError('This method is abstract')
