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

# TODO: document the code
# TODO: write tests for the code

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
	""" Every scheduled task must be:
		- able to be stopped at any time
		- able to return its status (running or stopped)
		- able to notify about task end (event)
	For now, as a good start is to use WThreadTask as task, that comply all of the requirements. Later it may
	be changed.
	"""

	@verify_type(thread_name_suffix=(str, None))
	def __init__(self, thread_name_suffix=None, thread_join_timeout=None):

		if thread_name_suffix is None:
			thread_name_suffix = str(uuid.uuid4())

		WThreadTask.__init__(
			self, thread_name='ScheduledTask-%s' % thread_name_suffix, join_on_stop=True, ready_to_stop=True,
			thread_join_timeout=thread_join_timeout
		)


class WTaskSchedule:

	class PostponePolicy(Enum):
		wait = 1  # will stack every postponed task to execute them later (default)
		drop = 2  # drop this task if it can't be executed at the moment
		postpone_first = 3  # stack the first task and drop all the following tasks with the same task ID
		postpone_last = 4  # stack the last task and drop all the previous tasks with the same task ID

	@verify_type(task=WScheduledTask, starting_datetime=datetime, task_id=(str, None))
	@verify_value(on_drop=lambda x: x is None or callable(x))
	def __init__(self, task, policy=None, task_id=None, on_drop=None):

		if policy is not None and isinstance(policy, WTaskSchedule.PostponePolicy) is False:
			raise TypeError('Invalid policy object type')

		self.__task = task
		self.__policy = policy if policy is not None else WTaskSchedule.PostponePolicy.wait
		self.__task_id = task_id
		self.__on_drop = on_drop

	def task(self):
		return self.__task

	def policy(self):
		"""
		:return: WTaskScheduleProto.PostponePolicy
		"""
		return self.__policy

	def task_id(self):
		"""
		:return: str or None
		"""
		return self.__task_id

	def task_dropped(self):
		"""
		Method is called when this task was dropped

		:note: this method is not called in a separate thread

		:return: None
		"""
		if self.__on_drop is not None:
			return self.__on_drop()


class WRunningScheduledTask:

	@verify_type(schedule=WTaskSchedule, started_at=datetime)
	@verify_value(starting_datetime=lambda x: x.tzinfo is not None and x.tzinfo == timezone.utc)
	def __init__(self, schedule, started_at):
		self.__scheduled = schedule
		self.__started_at = started_at

	def task_schedule(self):
		return self.__scheduled

	def started_at(self):
		return self.__started_at


class WTaskSourceProto(metaclass=ABCMeta):

	@abstractmethod
	def has_tasks(self):
		"""
		:return: list of WTaskSchedule (list with one element at least) or None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def next_start(self):
		"""
		:return: datetime in utc timezone
		"""
		raise NotImplementedError('This method is abstract')


class WRunningTaskRegistryProto(metaclass=ABCMeta):

	@abstractmethod
	@verify_type(task_schedule=WTaskSchedule)
	def exec(self, task_schedule):
		"""
		:param task_schedule: task to execute
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def running_tasks(self):
		"""
		:return: list of WRunningScheduledTask
		"""
		raise NotImplementedError('This method is abstract')


class WTaskSchedulerProto(metaclass=ABCMeta):

	@abstractmethod
	@verify_type(task_source=(WTaskSourceProto, None))
	def update(self, task_source=None):
		""" Update task sources information about next start. Update information for the specified source
		or for all of them

		It must have thread-safe implementation, that must reflect this single object
		:return:
		"""
		raise NotImplementedError('This method is abstract')
