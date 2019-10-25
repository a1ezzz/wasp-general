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

import uuid

from wasp_general.verify import verify_value, verify_type
from wasp_general.thread import WCriticalResource
from wasp_general.api.task.proto import WTaskLauncherProto, WTaskRegistryProto, WTaskProto, WNoSuchTask
from wasp_general.api.task.proto import WRequirementsLoop, WDependenciesLoop
from wasp_general.api.task.registry import __default_task_registry__


class WTaskLauncher(WTaskLauncherProto, WCriticalResource):
	""" Thread safe :class:`.WTaskLauncherProto` class implementation
	"""

	__critical_section_timeout__ = 5
	""" Timeout for capturing a lock for critical sections
	"""

	@verify_type('strict', registry=(WTaskRegistryProto, None))
	def __init__(self, registry=None):
		""" Create a new launcher

		:param registry: a linked registry that will be used for requesting a task class by it's tag
		:type registry: WTaskRegistryProto
		"""
		WTaskLauncherProto.__init__(self)
		WCriticalResource.__init__(self)
		if registry is None:
			registry = __default_task_registry__
		self.__started_tasks = {}
		self.__registry = registry

	def registry(self):
		""" :meth:`.WTaskLauncherProto.registry` method implementation

		:rtype: WTaskRegistryProto
		"""
		return self.__registry

	@verify_type('strict', task_tag=str)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def requirements(self, task_tag):
		""" This is a shortcut for a requesting task's requirements by a task_tag

		:param task_tag: a tag of a task which requirements are requested
		:type task_tag: str

		:rtype: tuple of str | set of str | None
		"""
		task = self.__registry.get(task_tag)
		return task.requirements()

	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def __tasks_copy(self):
		""" Copy an internal tasks storage
		:rtype: dict
		"""
		result = {k: v.copy() for k, v in self.__started_tasks.items()}
		return result

	@verify_type('paranoid', task_tag=(str, None))
	@verify_value('paranoid', task_tag=lambda x: x is None or len(x) > 0)
	def started_tasks(self, task_tag=None):
		""" :meth:`.WTaskLauncherProto.started_tasks` method implementation
		:type task_tag: str | None
		:rtype: generator
		"""
		started_tasks = self.__tasks_copy()
		if task_tag is None:
			return ((task_tag, instance_id) for task_tag, i in started_tasks.items() for instance_id in i)
		elif task_tag in started_tasks:
			return ((task_tag, x) for x in started_tasks[task_tag])
		else:
			raise WNoSuchTask('Task with tag "%s" was not found', task_tag)

	def __iter__(self):
		""" Return generator that will iterate over all tasks

		:rtype: generator
		"""
		return self.started_tasks()

	@verify_type('strict', task_tag=str, skip_unresolved=bool, requirements_deep_check=bool)
	@verify_type('strict', loop_requirements=(set, None))
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def __requirements(
		self, task_tag, skip_unresolved=False, requirements_deep_check=False, loop_requirements=None
	):
		""" Return ordered task's requirements. Tags order allows to be confident that all the requirements
		are met before starting following tasks

		note: No mutual dependencies are allowed
		note: some tags may be spotted more then once

		:param task_tag: same as 'task_tag' in :meth:`.WTaskLauncherProto.start_task`
		:type task_tag: str

		:param skip_unresolved: same as 'skip_unresolved' in :meth:`.WTaskLauncherProto.start_task`
		:type skip_unresolved: bool

		:param requirements_deep_check: same as 'requirements_deep_check' in
		:meth:`.WTaskLauncherProto.start_task`
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
					loop_requirements = next_requirements
				)

		return result + req_result

	@verify_type('strict', task_tag=str, skip_unresolved=bool, requirements_deep_check=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def start_task(self, task_tag, skip_unresolved=False, requirements_deep_check=False):
		""" This is a thread safe :meth:`.WTaskLauncherProto.start_task` method implementation. Task
		or requirements that are going to start must not call this or any 'stop' methods due to
		lock primitive

		:type task_tag: str
		:type skip_unresolved: bool
		:type requirements_deep_check: bool
		:rtype: str
		"""
		if self.__registry.has(task_tag) is False:
			raise WNoSuchTask('Unable to find a task with tag "%s" to start', task_tag)

		requirements = self.__requirements(
			task_tag, skip_unresolved=skip_unresolved, requirements_deep_check=requirements_deep_check
		)
		started_tasks = set()

		last_instance_id = None
		for task_tag, task_cls in requirements:
			if task_tag in started_tasks:
				continue

			instance = task_cls.start()
			last_instance_id = str(uuid.uuid4())

			instances_dict = self.__started_tasks.get(task_tag, {})
			instances_dict[last_instance_id] = instance
			self.__started_tasks[task_tag] = instances_dict
			started_tasks.add(task_tag)

		return last_instance_id

	@verify_type('strict', task_tag=str, instance_id=(str, None), stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0, instance_id=lambda x: x is None or len(x) > 0)
	def __stop_task(self, task_tag, instance_id=None, stop=True, terminate=False):
		""" Stop required tasks and return a number of stopped instances

		:param task_tag: same as 'task_tag' in :meth:`.WTaskLauncherProto.stop_task`
		:type task_tag: str

		:param instance_id: same as 'instance_id' in :meth:`.WTaskLauncherProto.stop_task`
		:type instance_id: str | None

		:param stop: same as 'stop' in :meth:`.WTaskLauncherProto.stop_task`
		:type stop: bool

		:param terminate: same as 'terminate' in :meth:`.WTaskLauncherProto.stop_task`
		:type terminate: bool

		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""

		if task_tag not in self.__started_tasks:
			return 0

		instances = self.__started_tasks[task_tag]

		def stop_instance(i_id):
			instance = instances[i_id]
			if stop is True and WTaskProto.stop in instance:
				instance.stop()
			elif terminate is True and WTaskProto.terminate in instance:
				instance.terminate()
			instances.pop(i_id)

			if len(instances) == 0:
				self.__started_tasks.pop(task_tag)

		if instance_id is not None:
			if instance_id not in instances:
				return 0
			stop_instance(instance_id)
			return 1

		count = 0
		for instance_id in instances.copy():
			stop_instance(instance_id)
			count += 1
		return count

	@verify_type('strict', task_tag=str, instance_id=(str, None), stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0, instance_id=lambda x: x is None or len(x) > 0)
	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def stop_task(self, task_tag, instance_id=None, stop=True, terminate=False):
		""" This is a thread safe :meth:`.WTaskLauncherProto.stop` method implementation. Task
		or requirements that are going to start must not call this or any 'start' or 'stop' methods due to
		lock primitive

		:type task_tag: str
		:type instance_id: str
		:type stop: bool
		:type terminate: bool
		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		result = self.__stop_task(task_tag, instance_id=instance_id, stop=stop, terminate=terminate)
		if result == 0:
			if instance_id is None:
				raise WNoSuchTask('Unable to find a task "%s" to stop', task_tag)
			else:
				raise WNoSuchTask(
					'Unable to find a task "%s" (instance id - "%s") to stop',
					task_tag, instance_id
				)
		return result

	@verify_type('strict', task_tag=str, loop_dependencies=(set, None))
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def __dependent_tasks(self, task_tag, loop_dependencies=None):
		""" Return ordered tuple of tasks that depend on a specified task. Tags order allows to be confident
		that tasks that are not required to other tasks will be stopped first

		note: No mutual dependencies are allowed

		:param task_tag: same as 'task_tag' in :meth:`.WTaskLauncherProto.stop_dependent_tasks`
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

	@verify_type('strict', task_tag=str, stop=bool, terminate=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def __stop_dependent_tasks(self, task_tag, stop=True, terminate=False):
		""" This is a NOT-thread safe method that is used by the :meth:`.WTaskLauncher.stop_dependent_tasks`
		and the :meth:`.WTaskLauncher.all_stop` methods. This method do the same as the original one -
		:meth:`.WTaskLauncherProto.stop_dependent_tasks`

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

	@verify_type('paranoid', task_tag=str, stop=bool, terminate=bool)
	@verify_value('paranoid', task_tag=lambda x: len(x) > 0)
	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def stop_dependent_tasks(self, task_tag, stop=True, terminate=False):
		""" This is a thread safe :meth:`.WTaskLauncherProto.stop_dependent_tasks` method implementation. Task
		or requirements that are going to start must not call this or any 'start' or 'stop' methods due to
		lock primitive

		:type task_tag: str
		:type stop: bool
		:type terminate: bool
		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		return self.__stop_dependent_tasks(task_tag=task_tag, stop=stop, terminate=terminate)

	@verify_type('strict', stop=bool, terminate=bool)
	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def all_stop(self, stop=True, terminate=True):
		""" This is a thread safe :meth:`.WTaskLauncherProto.all_stop` method implementation. Task
		or requirements that are going to start must not call this or any 'start' or 'stop' methods due to
		lock primitive

		:type stop: bool
		:type terminate: bool
		:rtype: int

		TODO: replace "stop" and "terminate" parameters with enum.IntFlag (python>=3.6 is required)
		"""
		result = 0
		while len(self.__started_tasks) > 0:
			task_tag = next(iter(self.__started_tasks))
			result += self.__stop_dependent_tasks(task_tag, stop=stop, terminate=terminate)
			result += self.__stop_task(task_tag, stop=stop, terminate=terminate)

		return result
