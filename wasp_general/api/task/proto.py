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

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value, verify_subclass

from wasp_general.api.capability import WCapabilitiesHolder, capability
from wasp_general.api.registry import WAPIRegistryProto


class WNoSuchTask(Exception):
	""" This exception is raised when a specified by tag and/or a tag with instance id task was not found
	"""
	pass


class WRequirementsLoop(Exception):
	""" This exception is raised when there is an attempt to start a tasks with mutual dependencies
	"""
	pass


class WDependenciesLoop(Exception):
	""" This exception is raised when there is an attempt to stop a tasks with mutual dependencies
	"""
	pass


class WStartedTaskError(Exception):
	""" This exception is raised when there is an attempt to start a task that is started already
	"""
	pass


class WStoppedTaskError(Exception):
	""" This exception is raised when there is an attempt to stop a task that is started already
	"""
	pass


class WTaskProto(WCapabilitiesHolder):
	""" Basic task prototype. Derived classes must implement the only thing - to start
	"""

	__task_tag__ = None  # this is a unique identifier of a task. Must be redefined in derived classes

	@classmethod
	@abstractmethod
	def init_task(cls, **kwargs):
		""" Initialize this task

		:param kwargs: arguments with which task should be started

		:note: A task may be used as a requirement if it may be started without arguments

		:return: WTaskProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def start(self):
		""" Start a task

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@classmethod
	def requirements(cls):
		""" Return task's names that are required to start in order this task to work. Or return
		None if this task may be started without any prerequisites

		:rtype: tuple of str | set of str | None
		"""
		return None

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


class WTaskRegistryProto(WAPIRegistryProto):
	""" A detailed registry version
	"""

	@abstractmethod
	@verify_type('strict', api_id=str)
	@verify_subclass('strict', api_descriptor=WTaskProto)
	@verify_value('strict', api_id=lambda x: len(x) > 0)
	def register(self, api_id, api_descriptor):
		""" This is the overridden method :meth:`.WAPIRegistryProto.register` that restricts supported values

		:type api_id: str
		:type api_descriptor: type

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')


class WTaskLauncherProto(metaclass=ABCMeta):
	""" This launcher tracks started tasks from a linked registry
	"""

	@abstractmethod
	def registry(self):
		""" Return a registry with which this launcher is linked

		:rtype: WTaskRegistryProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', task_tag=(str, None))
	@verify_value('strict', task_tag=lambda x: x is None or len(x) > 0)
	def started_tasks(self, task_tag=None):
		""" Return a generator that will yield tuple of task's tag and instance id

		:param task_tag: filter tasks by tag. If this tag is specified, then only that type of tasks will
		be returned
		:type task_tag: str | None

		:raise WNoSuchTask: raises if the specified task can not be found

		:rtype: generator
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', task_tag=str, skip_unresolved=bool, requirements_deep_check=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def start_task(self, task_tag, skip_unresolved=False, requirements_deep_check=False):
		""" Star task from a registry and return it's id (instance id)

		:param task_tag: tag of task that should be started
		:type task_tag: str

		:param skip_unresolved: whether a task should be started if all the requirements was not met
		:type skip_unresolved: bool

		:param requirements_deep_check: whether a recursive requirements check should be made. If this value
		is True then requirements of requirements should be checked
		:type requirements_deep_check: bool

		:raise WNoSuchTask: raises if the specified task or it's requirements can not be found
		:raise WRequirementsLoop: raises if there is a mutual dependency between tasks

		:rtype: str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', task_tag=str, instance_id=(str, None), stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0, instance_id=lambda x: x is None or len(x) > 0)
	def stop_task(self, task_tag, instance_id=None, stop=True, terminate=False):
		""" Stop a previously started task and return number of tasks instances that were stopped

		:param task_tag: a tag of task that should be stopped
		:type task_tag: str

		:param instance_id: a task's instance id that should be stopped
		:type instance_id: str

		:param stop: whether to call a WTaskProto.stop capability if is supported by a task
		:type stop: bool

		:param terminate: whether to call a WTaskProto.terminate capability if is supported by a task
		:type terminate: bool

		:raise WNoSuchTask: raises if the specified task can not be found
		:raise WDependenciesLoop: raises if there is a mutual dependency between tasks

		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', task_tag=str, stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def stop_dependent_tasks(self, task_tag, stop=True, terminate=False):
		""" Stop tasks that are dependent by a specified one or tasks that are dependent by found dependencies.
		And return number of tasks instances that were stopped

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
		""" Stop all the started tasks and return number of tasks instances that were stopped

		:param stop: whether to call a WTaskProto.stop capability if is supported by a task
		:type stop: bool

		:param terminate: whether to call a WTaskProto.terminate capability if is supported by a task
		:type terminate: bool

		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		raise NotImplementedError('This method is abstract')
