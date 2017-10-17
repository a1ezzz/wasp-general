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


# noinspection PyAbstractClass
class WScheduleTask(WThreadTask):
	""" Class represent task that may run by a scheduler
	Every schedule task must be able:
		- to be stopped at any time
		- to return its status (running or stopped)
		- to notify when task end (thread event)

	note: derived classes must implement :meth:`.WThreadTask.thread_started` and :meth:`.WThreadTask.thread_stopped`
	methods in order to be instantiable

	Each task instance has "unique" identifier
	"""

	__thread_name_prefix__ = 'ScheduledTask-'
	""" Thread name prefix
	"""

	@verify_type('paranoid', thread_join_timeout=(int, float, None))
	def __init__(self, thread_join_timeout=None):
		""" Create new task

		:param thread_join_timeout: same as thread_join_timeout in :meth:`.WThreadTask.__init__` method
		"""

		self.__uid = self.generate_uid()

		WThreadTask.__init__(
			self, thread_name=(self.__thread_name_prefix__ + str(self.__uid)), join_on_stop=True,
			ready_to_stop=True, thread_join_timeout=thread_join_timeout
		)

	def uid(self):
		return self.__uid

	@classmethod
	def generate_uid(cls):
		""" Return "random" "unique" identifier

		:return: UUID
		"""
		return uuid.uuid4()


class WScheduleRecord:
	""" This class specifies how :class:`.WScheduleTask` should run. It should be treated as scheduler record, that
	may not have execution time.

	:class:`.WScheduleRecord` has a policy, that describes what scheduler should do if it can not run this task
	at the specified moment. This policy is a recommendation for a scheduler and a scheduler can omit it if
	(for example) a scheduler queue is full. In any case, if this task is dropped (skipped) or postponed (moved to
	a queue of waiting tasks) correlated callback is called. "on_drop" callback is called for skipped tasks
	(it invokes via :meth:`.WScheduleRecord.task_dropped` method) and "on_wait" for postponed tasks (via
	:meth:`.WScheduleRecord.task_postponed` method)

	note: It is important that tasks with the same id (task_group_id) have the same postpone policy. If they do not
	have the same policy, then exception may be raised. No pre-checks are made to resolve this, because of
	unpredictable logic of different tasks from different sources
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

	@verify_type(task=WScheduleTask, task_group_id=(str, None))
	@verify_value(on_drop=lambda x: x is None or callable(x), on_wait=lambda x: x is None or callable(x))
	def __init__(self, task, policy=None, task_group_id=None, on_drop=None, on_wait=None):
		""" Create new schedule record

		:param task: task to run
		:param policy: postpone policy
		:param task_group_id: identifier that groups different scheduler records and single postpone policy
		:param on_drop: callback, that must be called if this task is skipped
		:param on_wait: callback, that must be called if this task is postponed
		"""

		if policy is not None and isinstance(policy, WScheduleRecord.PostponePolicy) is False:
			raise TypeError('Invalid policy object type')

		self.__task = task
		self.__policy = policy if policy is not None else WScheduleRecord.PostponePolicy.wait
		self.__task_group_id = task_group_id
		self.__on_drop = on_drop
		self.__on_wait = on_wait

	def task(self):
		""" Return task that should be run

		:return: WScheduleTask
		"""
		return self.__task

	def task_uid(self):
		""" Shortcut for self.task().uid()
		"""
		return self.task().uid()

	def policy(self):
		""" Return postpone policy

		:return: WScheduleRecord.PostponePolicy
		"""
		return self.__policy

	def task_group_id(self):
		""" Return task id

		:return: str or None

		see :meth:`.WScheduleRecord.__init__`
		"""
		return self.__task_group_id

	def task_postponed(self):
		""" Call a "on_wait" callback. This method is executed by a scheduler when it postpone this task

		:return: None
		"""
		if self.__on_wait is not None:
			return self.__on_wait()

	def task_dropped(self):
		""" Call a "on_drop" callback. This method is executed by a scheduler when it skip this task

		:return: None
		"""
		if self.__on_drop is not None:
			return self.__on_drop()


class WTaskSourceProto(metaclass=ABCMeta):
	""" Prototype for scheduler record generator. :class:`.WSchedulerServiceProto` doesn't have scheduler as set of
	records. Instead, a service uses this class as scheduler records holder and checks if it is time to execute
	them.
	"""

	@abstractmethod
	def has_records(self):
		""" Return records that should be run at the moment.


		:return: tuple of WScheduleRecord (tuple with one element at least) or None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def next_start(self):
		""" Return datetime when the next task should be executed.

		:return: datetime in UTC timezone
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def tasks_planned(self):
		""" Return number of records (tasks) that are planned to run

		:return: int
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def scheduler_service(self):
		""" Return associated scheduler service

		:return: WSchedulerServiceProto or None
		"""
		raise NotImplementedError('This method is abstract')


class WRunningRecordRegistryProto(metaclass=ABCMeta):
	""" This class describes a registry of running tasks. It executes a scheduler record
	(:class:`.WScheduleRecord`), creates and store the related records (:class:`.WScheduleRecord`), and watches
	that these tasks are running
	"""

	@abstractmethod
	@verify_type(schedule_record=WScheduleRecord)
	def exec(self, schedule_record):
		""" Execute the given scheduler record (no time checks are made at this method, task executes as is)

		:param schedule_record: record to execute

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def running_records(self):
		""" Return tuple of running tasks

		:return: tuple of WScheduleRecord
		"""
		raise NotImplementedError('This method is abstract')


class WSchedulerServiceProto(metaclass=ABCMeta):
	""" Represent a scheduler. A core of wasp_general.task.scheduler module
	"""

	@abstractmethod
	@verify_type(task_source=(WTaskSourceProto, None))
	def update(self, task_source=None):
		""" Update task sources information about next start. Update information for the specified source
		or for all of them

		:param task_source: if it is specified - then update information for this source only

		This method implementation must be thread-safe as different threads (different task source, different
		registries) may modify scheduler internal state.
		:return:
		"""
		raise NotImplementedError('This method is abstract')
