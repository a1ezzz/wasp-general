# -*- coding: utf-8 -*-
# wasp_general/task/launcher.py
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

import functools

from wasp_general.verify import verify_value, verify_type, verify_subclass
from wasp_general.thread import WCriticalResource
from wasp_general.api.registry import WAPIRegistryProto, register_api
from wasp_general.api.task.proto import WLauncherProto, WTaskProto, WLauncherTaskProto, WNoSuchTask, WRequirementsLoop
from wasp_general.api.task.proto import WDependenciesLoop, WStartedTaskError


class WLauncher(WLauncherProto, WCriticalResource):
	""" Thread safe :class:`.WLauncherProto` class implementation
	"""

	__critical_section_timeout__ = 5
	""" Timeout for capturing a lock for critical sections
	"""

	@verify_type('strict', registry=WAPIRegistryProto)
	def __init__(self, registry):
		""" Create a new launcher

		:param registry: a linked registry that will be used for requesting a task class by it's tag
		:type registry: WTaskRegistryProto
		"""
		WLauncherProto.__init__(self)
		WCriticalResource.__init__(self)
		self.__started_tasks = {}
		self.__registry = registry

	def registry(self):
		""" :meth:`.WLauncherProto.registry` method implementation

		:rtype: WTaskRegistryProto
		"""
		return self.__registry

	@verify_type('strict', task_tag=str)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def is_started(self, task_tag):
		""" :meth:`.WLauncherProto.is_started` method implementation

		:type task_tag: str

		:rtype: bool
		"""
		return task_tag in self.__started_tasks

	@verify_type('strict', task_tag=str)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def requirements(self, task_tag):
		""" This is a shortcut for requesting task's requirements by a task_tag

		:param task_tag: a tag of a task which requirements are requested
		:type task_tag: str

		:rtype: tuple of str | set of str | None
		"""
		task = self.__registry.get(task_tag)
		return task.requirements()

	def started_tasks(self):
		""" :meth:`.WLauncherProto.started_tasks` method implementation
		:rtype: generator
		"""
		for tag in self.__started_tasks.copy():
			yield tag

	def __iter__(self):
		""" Return generator that will iterate over all tasks
		:rtype: generator
		"""
		return self.started_tasks()

	def __len__(self):
		""" Return number of running tasks

		:rtype: int
		"""
		return len(self.__started_tasks)

	def __contains__(self, item):
		""" Chekc that a specified task is running

		:param item: task tag to check
		:type item: str

		:rtype: bool
		"""
		return item in self.__started_tasks

	@verify_type('strict', task_tag=str, skip_unresolved=bool, requirements_deep_check=bool)
	@verify_type('strict', loop_requirements=(set, None))
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def __requirements(
		self, task_tag, skip_unresolved=False, requirements_deep_check=False, loop_requirements=None
	):
		""" Return ordered task's requirements. Tags order allows to be confident that all the requirements
		are met before starting following tasks

		note: No mutual dependencies are allowed
		note: Some tags may be spotted more then once

		:param task_tag: same as 'task_tag' in :meth:`.WLauncherProto.start_task`
		:type task_tag: str

		:param skip_unresolved: same as 'skip_unresolved' in :meth:`.WLauncherProto.start_task`
		:type skip_unresolved: bool

		:param requirements_deep_check: same as 'requirements_deep_check' in
		:meth:`.WLauncherProto.start_task`
		:type requirements_deep_check: bool

		:param loop_requirements: this argument is used for checking a mutual dependencies and consists of
		a previously found requirements
		:type loop_requirements: set | None

		:rtype: tuple
		"""
		next_requirements = loop_requirements.copy() if loop_requirements is not None else set()

		if self.__registry.has(task_tag) is False:
			if skip_unresolved is True:
				return tuple()
			raise WNoSuchTask('Unable to find a required task with tag "%s"', task_tag)

		task_cls = self.__registry.get(task_tag)
		task_req = task_cls.requirements()
		task_started = task_tag in self.__started_tasks
		req_result = None

		if task_started:
			if loop_requirements is not None:
				if requirements_deep_check is False:
					return tuple()
				else:
					req_result = tuple()

		if req_result is None:
			req_result = ((task_tag, task_cls,),)

		result = tuple()
		if task_req is not None:
			next_requirements.add(task_tag)
			for r in task_req:
				if r in next_requirements:
					raise WRequirementsLoop(
						'A loop of requirements was detected. The following tasks depend on '
						'each other: %s', ', '.join(next_requirements)
					)

				result += self.__requirements(
					r,
					skip_unresolved=skip_unresolved,
					requirements_deep_check=requirements_deep_check,
					loop_requirements=next_requirements
				)

		return result + req_result

	@verify_type('strict', task_tag=str, skip_unresolved=bool, requirements_deep_check=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def start_task(self, task_tag, skip_unresolved=False, requirements_deep_check=False):
		""" This is a thread safe :meth:`.WLauncherProto.start_task` method implementation. A task
		or requirements that are going to be started must not call this or any 'stop' methods due to
		lock primitive

		:type task_tag: str
		:type skip_unresolved: bool
		:type requirements_deep_check: bool
		:rtype: int
		"""
		if task_tag in self.__started_tasks:
			raise WStartedTaskError('A task "%s" is started already', task_tag)

		if self.__registry.has(task_tag) is False:
			raise WNoSuchTask('Unable to find a task with tag "%s" to start', task_tag)

		requirements = self.__requirements(
			task_tag, skip_unresolved=skip_unresolved, requirements_deep_check=requirements_deep_check
		)
		started_tasks = set()
		for task_tag, task_cls in requirements:
			if task_tag in started_tasks:
				continue

			instance = task_cls.launcher_task(self)
			instance.start()
			self.__started_tasks[task_tag] = instance
			started_tasks.add(task_tag)

		return len(started_tasks)

	@verify_type('strict', task_tag=str, stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0, instance_id=lambda x: x is None or len(x) > 0)
	def __stop_task(self, task_tag, stop=True, terminate=False):
		""" Stop required tasks and return a number of stopped instances

		:param task_tag: same as 'task_tag' in :meth:`.WLauncherProto.stop_task`
		:type task_tag: str

		:param stop: same as 'stop' in :meth:`.WLauncherProto.stop_task`
		:type stop: bool

		:param terminate: same as 'terminate' in :meth:`.WLauncherProto.stop_task`
		:type terminate: bool

		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		task_instance = self.__started_tasks.get(task_tag, None)
		if task_instance is not None:
			if stop is True and WTaskProto.stop in task_instance:
				task_instance.stop()
			elif terminate is True and WTaskProto.terminate in task_instance:
				task_instance.terminate()
			self.__started_tasks.pop(task_tag)
			return 1
		return 0

	@verify_type('strict', task_tag=str, stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def stop_task(self, task_tag, stop=True, terminate=False):
		""" This is a thread safe :meth:`.WLauncherProto.stop` method implementation. Task
		or requirements that are going to be stopped must not call this or any 'start' or 'stop' methods due to
		lock primitive

		:type task_tag: str
		:type stop: bool
		:type terminate: bool
		:rtype: None

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		result = self.__stop_task(task_tag, stop=stop, terminate=terminate)
		if result == 0:
			raise WNoSuchTask('Unable to find a task "%s" to stop', task_tag)

	@verify_type('strict', task_tag=str, loop_dependencies=(set, None))
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def __dependent_tasks(self, task_tag, loop_dependencies=None):
		""" Return ordered tuple of tasks that depend on a specified task. Tags order allows to be confident
		that tasks that are not required to other tasks will be stopped first

		note: No mutual dependencies are allowed

		:param task_tag: same as 'task_tag' in :meth:`.WLauncherProto.stop_dependent_tasks`
		:type task_tag: str

		:param loop_dependencies: this argument is used for checking a mutual dependencies and consists of
		a previously found dependencies
		:type loop_dependencies: set | None

		:rtype: tuple
		"""
		next_dependencies = loop_dependencies.copy() if loop_dependencies is not None else set()

		if task_tag in next_dependencies:
			raise WDependenciesLoop(
				'A loop of dependencies was detected. The following tasks depend on '
				'each other: %s', ', '.join(next_dependencies)
			)

		next_dependencies.add(task_tag)
		result = tuple()
		for d_tag in self.__started_tasks:
			if d_tag not in result:
				task_req = self.requirements(d_tag)
				if task_req is not None and task_tag in task_req:
					result += self.__dependent_tasks(d_tag, loop_dependencies=next_dependencies)
		if loop_dependencies is not None:
			return result + (task_tag, )
		return result

	@verify_type('paranoid', task_tag=str, stop=bool, terminate=bool)
	@verify_value('paranoid', task_tag=lambda x: len(x) > 0)
	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def stop_dependent_tasks(self, task_tag, stop=True, terminate=False):
		""" This is a thread safe :meth:`.WLauncherProto.stop_dependent_tasks` method implementation. Task
		or requirements that are going to be stopped must not call this or any 'start' or 'stop' methods due to
		lock primitive

		:type task_tag: str
		:type stop: bool
		:type terminate: bool
		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		result = 0
		for task_tag in self.__dependent_tasks(task_tag):
			result += self.__stop_task(task_tag, stop=stop, terminate=terminate)
		return result

	@verify_type('strict', stop=bool, terminate=bool)
	def all_stop(self, stop=True, terminate=True):
		""" This is a thread safe :meth:`.WLauncherProto.all_stop` method implementation. Task
		or requirements that are going to be stopped must not call this or any 'start' or 'stop' methods due to
		lock primitive

		:type stop: bool
		:type terminate: bool
		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""

		with self.critical_context(timeout=self.__critical_section_timeout__) as c:
			result = 0
			while len(self.__started_tasks) > 0:
				task_tag = next(iter(self.__started_tasks))
				result += c.stop_dependent_tasks(task_tag, stop=stop, terminate=terminate)
				result += self.__stop_task(task_tag, stop=stop, terminate=terminate)

			return result


@verify_subclass('strict', launcher_task=WLauncherTaskProto)
def __launcher_task_api_id(launcher_task):
	""" This is an accessor that return a valid task tag from a task. The only purpose is to generate api_id for
	register_api function

	:param launcher_task: a task class which tag should be returned
	:type launcher_task: WLauncherTaskProto

	:rtype: str
	"""
	task_tag = launcher_task.__task_tag__
	if task_tag is None or not isinstance(task_tag, str):
		raise ValueError('Unable to get an api_id from task - it is None or has invalid type')
	return task_tag


register_task = functools.partial(register_api, api_id=__launcher_task_api_id, callable_api_id=True)  # this is
# a shortcut for a task registration
