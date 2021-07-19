# -*- coding: utf-8 -*-
# wasp_general/task/proto.py
#
# Copyright (C) 2016-2019 the wasp-general authors and contributors
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

import enum
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value

from wasp_general.api.signals import WSignalSourceProto, WSignal
from wasp_general.api.capability import WCapabilitiesHolder, capability


class WNoSuchTask(Exception):
	""" This exception is raised when a specified by tag was not found
	"""
	pass


class WRequirementsLoop(Exception):
	""" This exception is raised when there is an attempt to start tasks with mutual dependencies
	"""
	pass


class WDependenciesLoop(Exception):
	""" This exception is raised when there is an attempt to stop tasks with mutual dependencies
	"""
	pass


class WStartedTaskError(Exception):
	""" This exception is raised when there is an attempt to start a task that has been started already
	"""
	pass


class WStoppedTaskError(Exception):
	""" This exception is raised when there is an attempt to stop a task that has been started already
	"""
	pass


class WTaskProto(WCapabilitiesHolder):
	""" Basic task prototype. Derived classes must implement the only thing - to start
	"""

	@abstractmethod
	def start(self):
		""" Start a task

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@capability
	def stop(self):
		""" Try to stop this task gracefully.

		:raise NotImplementedError: if this task can not be stopped

		:rtype: None
		"""
		raise NotImplementedError('The "stop" method is not supported')

	@capability
	def terminate(self):
		""" Try to stop this task at all costs

		:raise NotImplementedError: if this task can not be terminated

		:rtype: None
		"""
		raise NotImplementedError('The "terminate" method is not supported')


class WLauncherTaskProto(WTaskProto):
	""" This is a task prototype that may be launched by an :class:`.WLauncherProto` instance. Derived classes
	must redefine :meth:`.WLauncherTaskProto.launcher_task` method and define a task id (tag) via
	WLauncherTaskProto.__task_tag__
	"""

	__task_tag__ = None  # this is a unique identifier of a task. Must be redefined in derived classes

	@classmethod
	@abstractmethod
	def launcher_task(cls, launcher):
		""" Create and return a task that later will be started by a specified launcher

		:param launcher:  launcher with which this task will be started
		:type launcher: WLauncherProto

		:rtype: WLauncherTaskProto
		"""
		raise NotImplementedError('This method is abstract')

	@classmethod
	def requirements(cls):
		""" Return task's tags that are required to start in order this task to work. Or return
		None if this task may be started without any prerequisites

		:rtype: tuple of str | None
		"""
		return None


class WLauncherProto(metaclass=ABCMeta):
	""" This launcher starts and tracks :class:`.WLauncherTaskProto` tasks
	"""

	@abstractmethod
	@verify_type('strict', task_tag=str)
	@verify_value('strict', task_tag=lambda x: x is None or len(x) > 0)
	def is_started(self, task_tag):
		""" Check whether a task with a specified tag has been started

		:param task_tag: tag to check
		:type task_tag: str

		:rtype: bool
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def started_tasks(self):
		""" Return a generator that will yield tags of tasks that has been started

		:rtype: generator
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', task_tag=str, skip_unresolved=bool, requirements_deep_check=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def start_task(self, task_tag, skip_unresolved=False, requirements_deep_check=False):
		""" Star a task and its requirements. Return number of tasks that were started

		:param task_tag: tag of task that should be started
		:type task_tag: str

		:param skip_unresolved: whether a task should be started if all the requirements was not met
		:type skip_unresolved: bool

		:param requirements_deep_check: whether a recursive requirements check should be made. If this value
		is True then requirements of requirements should be checked
		:type requirements_deep_check: bool

		:raise WNoSuchTask: raises if the specified task or it's requirements can not be found
		:raise WStartedTaskError: if a task is started already
		:raise WRequirementsLoop: raises if there is a mutual dependency between tasks

		:rtype: int
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', task_tag=str, stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def stop_task(self, task_tag, stop=True, terminate=False):
		""" Stop a previously started task

		:param task_tag: a tag of task that should be stopped
		:type task_tag: str

		:param stop: whether to call a WTaskProto.stop capability if is supported by a task
		:type stop: bool

		:param terminate: whether to call a WTaskProto.terminate capability if is supported by a task
		:type terminate: bool

		:raise WNoSuchTask: raises if the specified task can not be found
		:raise WDependenciesLoop: raises if there is a mutual dependency between tasks

		:rtype: None

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', task_tag=str, stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def stop_dependent_tasks(self, task_tag, stop=True, terminate=False):
		""" Stop tasks that are dependent of a specified one or tasks that are dependent of found dependencies.
		And return number of tasks that were stopped

		:param task_tag: task that will be searched in a requirements of running tasks
		:type task_tag: str

		:param stop: whether to call a WTaskProto.stop capability if is supported by a task
		:type stop: bool

		:param terminate: whether to call a WTaskProto.terminate capability if is supported by a task
		:type terminate: bool

		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', stop=bool, terminate=bool)
	def all_stop(self, stop=True, terminate=True):
		""" Stop all the started tasks and return number of tasks that were stopped

		:param stop: whether to call a WTaskProto.stop capability if is supported by a task
		:type stop: bool

		:param terminate: whether to call a WTaskProto.terminate capability if is supported by a task
		:type terminate: bool

		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		raise NotImplementedError('This method is abstract')


@enum.unique
class WTaskPostponePolicy(enum.Enum):
	""" This is a policy that describes what should be done with a task if a scheduler won't be able to run
	it (like if the scheduler's limit of running tasks is reached).

	TODO: record TTL?
	"""
	wait = 1  # will postpone the task to execute it later
	drop = 2  # drop this task if it can't be executed at the moment


class WScheduleRecordProto(metaclass=ABCMeta):
	""" This class describes a single request that scheduler (:class:`.WSchedulerProto`) should process
	(should start). It has a :class:`.WScheduledTaskProto` task to be started and a postpone policy
	(:class:`.WTaskPostponePolicy`)

	A postpone policy will be applied to this task and to tasks with the same group id (if it was set). A postpone
	policy is a recommendation for a scheduler and a scheduler can omit it if (for example) a scheduler queue
	is full. 'WTaskPostponePolicy.postpone_first' and 'WTaskPostponePolicy.postpone_last' policies are not allowed
	without group id
	"""

	@abstractmethod
	def task(self):
		""" Return a task that should be started

		:rtype: WTaskProto
		"""
		raise NotImplementedError('This method is abstract')

	def policy(self):
		""" Return a postpone policy

		:rtype: WTaskPostponePolicy
		"""
		return WTaskPostponePolicy.wait


# noinspection PyAbstractClass
class WScheduleSourceProto(WSignalSourceProto):
	""" This class may generate :class:`.WScheduleRecordProto` requests for a scheduler (:class:`.WSchedulerProto`).
	This class decides what tasks and when should be run. When a time is come then this source emits
	a WScheduleSourceProto.task_scheduled signal
	"""

	task_scheduled = WSignal(payload_type_spec=WScheduleRecordProto)  # a new task should be started

	@classmethod
	def signals(cls):
		""" :meth:`.WSignalSourceProto.signals` method implementation

		:rtype: tuple[WSignal]
		"""
		return cls.task_scheduled,


# noinspection PyAbstractClass
class WSchedulerProto(WSignalSourceProto, WTaskProto):
	""" Represent a scheduler. A class that is able to execute tasks (:class:`.WScheduleRecordProto`) scheduled
	by sources (:class:`.WScheduleSourceProto`). This class tracks state of tasks that are running
	"""

	task_scheduled = WSignal(payload_type_spec=WScheduleRecordProto)
	task_dropped = WSignal(payload_type_spec=WScheduleRecordProto)
	task_postponed = WSignal(payload_type_spec=WScheduleRecordProto)
	task_started = WSignal(payload_type_spec=WScheduleRecordProto)
	task_crashed = WSignal(payload_type_spec=tuple)  # two items tuple - scheduledrecord and an exception
	task_stopped = WSignal(payload_type_spec=tuple)  # two items tuple - scheduledrecord and a task result

	@abstractmethod
	@verify_type('strict', schedule_source=WScheduleSourceProto)
	def subscribe(self, schedule_source):
		""" Subscribe this scheduler to a specified source in order to and start tasks from it

		:param schedule_source: source of records that should be subscribed
		:type schedule_source: WScheduleSourceProto

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', schedule_source=WScheduleSourceProto)
	def unsubscribe(self, schedule_source):
		""" Unsubscribe this scheduler from a specified sources and do process tasks from it

		:param schedule_source: source of records to unsubscribe from
		:type schedule_source: WTaskSourceProto

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def running_records(self):
		""" Return generator that will iterate over running tasks (records)

		:rtype: generator (of WScheduleRecordProto instances)
		"""
		raise NotImplementedError('This method is abstract')

	@classmethod
	def signals(cls):
		""" Signals that this class may emit

		:rtype: tuple[WSignal]
		"""
		return cls.task_scheduled, \
			cls.task_dropped, \
			cls.task_postponed, \
			cls.task_started, \
			cls.task_crashed, \
			cls.task_stopped
