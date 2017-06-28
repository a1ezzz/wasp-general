# -*- coding: utf-8 -*-
# wasp_general/task/dependency.py
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

from wasp_general.verify import verify_type, verify_subclass
from wasp_general.task.registry import WTaskRegistry, WRegisteredTask, WTaskRegistryStorage
from wasp_general.task.base import WTask, WStoppableTask


class WDependentTask(WRegisteredTask):
	""" Metaclass for dependent tasks. It is used for automatic resolving required dependencies (starting required
	tasks). Derived classes must be able to be constructed with constructor without arguments or they must
	override :meth:`.WDependentTask.start_dependent_task` method.

	If derived class inherits :class:`wasp_general.task.base.WStoppableTask` class, then it could be stopped
	(automatically stopped via registry class, such as :class:`.WTaskDependencyRegistry`)

	When __registry_tag__ is set to None, related task registry must have '__skip_none_registry_tag__' flag
	set to False, otherwise - exception is raised. Such task (that have __registry_tag__ set to None) will be
	excluded from registry.

	In order to include task to registry, task must define __registry_tag__, which has to be a str class.
	"""

	__dependency__ = []
	""" List of tags (str). Each tag represent task, that required to start prior to this task.
	"""
	__description__ = None
	""" Just task description. Should be str type.
	"""

	def __init__(cls, name, bases, namespace):
		""" Construct new class. Derived class must redefine __registry__ and __registry_tag__ properties.
		In order to start dependency task automatically, property __dependency__ must be redefined.

		It is highly important, that derived class method :meth:`.WDependentTask.start_dependent_task` will
		be able to construct and start this task.

		:param name: as name in type(cls, name, bases, namespace)
		:param bases: as bases in type(cls, name, bases, namespace)
		:param namespace: as namespace in type(cls, name, bases, namespace)
		"""

		if cls.__auto_registry__ is True:

			if cls.__registry__ is None:
				raise ValueError('__registry__ must be defined')

			if issubclass(cls.__registry__, WTaskDependencyRegistry) is False:
				raise TypeError(
					"Property '__registry__' of tasks class has invalid type (must be "
					"WTaskDependencyRegistry or its subclass)"
				)

			if cls.__registry_tag__ is None:
				if cls.__registry__.__skip_none_registry_tag__ is False:
					raise ValueError("Property '__registry_tag__' must be defined")
			elif isinstance(cls.__registry_tag__, str) is False:
				raise TypeError("Property '__registry_tag__' must be string type")

		WRegisteredTask.__init__(cls, name, bases, namespace)

	def start_dependent_task(cls):
		""" Start this task and return its instance

		:return: WTask
		"""
		task = cls()
		# noinspection PyUnresolvedReferences
		task.start()
		return task


class WTaskDependencyRegistryStorage(WTaskRegistryStorage):
	""" Storage that is used to store :class:`.WDependentTask` task.
	"""

	__multiple_tasks_per_tag__ = False
	""" Each task must have unique __registry_tag__ property.
	See :attr:`wasp_general.task.registry.WTaskRegistryStorage.__multiple_tasks_per_tag__`
	"""

	def __init__(self):
		""" Construct new storage
		"""
		WTaskRegistryStorage.__init__(self)
		self.__started = []

	@verify_type('paranoid', task_cls=WDependentTask)
	def add(self, task_cls):
		""" Add task to this storage. Multiple tasks with the same tag are not allowed

		:param task_cls: task to add
		:return: None
		"""
		return WTaskRegistryStorage.add(self, task_cls)

	@verify_subclass(task_cls=WTask)
	@verify_type(task_cls=WDependentTask)
	def dependency_check(self, task_cls, skip_unresolved=False):
		""" Check dependency of task for irresolvable conflicts (like task to task mutual dependency)

		:param task_cls: task to check
		:param skip_unresolved: flag controls this method behaviour for tasks that could not be found. \
		When False, method will raise an exception if task tag was set in dependency and the related task \
		wasn't found in registry. When True that unresolvable task will be omitted

		:return: None
		"""

		def check(check_task_cls, global_dependencies):
			if check_task_cls.__registry_tag__ in global_dependencies:
				raise RuntimeError('Recursion dependencies for %s' % task_cls.__registry_tag__)

			dependencies = global_dependencies.copy()
			dependencies.append(check_task_cls.__registry_tag__)

			for dependency in check_task_cls.__dependency__:
				dependent_task = self.tasks(dependency)
				if dependent_task is None and skip_unresolved is False:
					raise RuntimeError(
						"Task '%s' dependency unresolved (%s)" %
						(task_cls.__registry_tag__, dependency)
					)

				if dependent_task is not None:
					check(dependent_task, dependencies)

		check(task_cls, [])

	@verify_type(task_tag=str)
	def started_task(self, task_tag):
		""" Get started task instance from registry by its tag

		:param task_tag: task tag
		:return: started task instance (WTask)
		"""

		for task in self.__started:
			if task.__registry_tag__ == task_tag:
				return task

	@verify_type(task_tag=str, skip_unresolved=bool)
	def start_task(self, task_tag, skip_unresolved=False):
		""" Check dependency for the given task_tag and start task. For dependency checking see
		:meth:`.WTaskDependencyRegistryStorage.dependency_check`. If task is already started then it must be
		stopped before it will be started again.

		:param task_tag: task to start. Any required dependencies will be started automatically.
		:param skip_unresolved: flag controls this method behaviour for tasks that could not be found. \
		When False, method will raise an exception if task tag was set in dependency and the related task \
		wasn't found in registry. When True that unresolvable task will be omitted

		:return: None
		"""
		if self.started_task(task_tag) is not None:
			return

		task_cls = self.tasks(task_tag)
		if task_cls is None:
			raise RuntimeError("Task '%s' wasn't found" % task_tag)

		self.dependency_check(task_cls, skip_unresolved=skip_unresolved)

		def start_dependency(start_task_cls):
			for dependency in start_task_cls.__dependency__:

				if self.started_task(dependency) is not None:
					continue

				dependent_task = self.tasks(dependency)

				if dependent_task is not None:
					start_dependency(dependent_task)

			self.__started.append(start_task_cls.start_dependent_task())

		start_dependency(task_cls)

	@verify_type(task_tag=str, stop_dependent=bool, stop_requirements=bool)
	def stop_task(self, task_tag, stop_dependent=True, stop_requirements=False):
		""" Stop task with the given task tag. If task already stopped, then nothing happens.

		:param task_tag: task to stop
		:param stop_dependent: if True, then every task, that require the given task as dependency, will be \
		stopped before.
		:param stop_requirements: if True, then every task, that is required as dependency for the given task, \
		will be stopped after.
		:return: None
		"""
		# TODO: "coverage" requires more tests

		def stop(task_to_stop):
			if task_to_stop in self.__started:
				if isinstance(task_to_stop, WStoppableTask) is True:
					task_to_stop.stop()
				self.__started.remove(task_to_stop)

		task = self.started_task(task_tag)

		if task is None:
			return

		def stop_dependency(task_to_stop):
			deeper_dependencies = []
			for dependent_task in self.__started:
				if task_to_stop.__registry_tag__ in dependent_task.__class__.__dependency__:
					deeper_dependencies.append(dependent_task)

			for dependent_task in deeper_dependencies:
				stop_dependency(dependent_task)

			stop(task_to_stop)

		def calculate_requirements(task_to_stop, cross_requirements=False):
			requirements = set()

			for dependent_task in self.__started:
				if dependent_task.__class__.__registry_tag__ in task_to_stop.__class__.__dependency__:
					requirements.add(dependent_task)

			if cross_requirements is True:
				return requirements

			result = set()
			for task_a in requirements:
				requirement_match = False
				for task_b in requirements:
					if task_a.__class__.__registry_tag__ in task_b.__class__.__dependency__:
						requirement_match = True
						break
				if requirement_match is False:
					result.add(task_a)
			return result

		def calculate_priorities(task_to_stop, *extra_tasks, current_result=None, requirements_left=None):
			if current_result is None:
				current_result = []

			tasks_to_stop = [task_to_stop]
			if len(extra_tasks) > 0:
				tasks_to_stop.extend(extra_tasks)

			current_result.append(list(tasks_to_stop))

			all_requirements = calculate_requirements(tasks_to_stop[0], cross_requirements=True)
			nested_requirements = calculate_requirements(tasks_to_stop[0])

			for dependent_task in tasks_to_stop[1:]:
				nested_requirements = nested_requirements.union(calculate_requirements(dependent_task))
				all_requirements.update(calculate_requirements(dependent_task, cross_requirements=True))

			all_requirements = all_requirements.difference(nested_requirements)

			if requirements_left is not None:
				requirements_left = requirements_left.difference(all_requirements)
				nested_requirements.update(requirements_left)

			if len(nested_requirements) == 0:
				return current_result

			return calculate_priorities(
				*list(nested_requirements), current_result=current_result, requirements_left=all_requirements
			)

		if stop_dependent is True:
			stop_dependency(task)

		if stop_requirements is True:
			for task_list in calculate_priorities(task):
				for single_task in task_list:
					stop(single_task)
		else:
			stop(task)


class WTaskDependencyRegistry(WTaskRegistry):
	""" Registry for the :class:`.WDependentTask` classes. Registry storage must be

	Derived classes must redefine __registry_storage__ property (which has to be
	:class:`.WTaskDependencyRegistryStorage` instance). (see :attr:`.WTaskRegistry.__registry_storage__`)
	"""

	@classmethod
	def registry_storage(cls):
		""" Get registry storage

		:return: WTaskDependencyRegistryStorage
		"""
		if cls.__registry_storage__ is None:
			raise ValueError('__registry_storage__ must be defined')
		if isinstance(cls.__registry_storage__, WTaskDependencyRegistryStorage) is False:
			raise TypeError(
				"Property '__registry_storage__' is invalid (must derived from WTaskRegistryBase)"
			)

		return cls.__registry_storage__

	@classmethod
	def start_task(cls, task_tag, skip_unresolved=False):
		""" Start task from registry

		:param task_tag: same as in :meth:`.WTaskDependencyRegistryStorage.start_task` method
		:param skip_unresolved: same as in :meth:`.WTaskDependencyRegistryStorage.start_task` method
		:return: None
		"""
		registry = cls.registry_storage()
		registry.start_task(task_tag, skip_unresolved=skip_unresolved)

	@classmethod
	def stop_task(cls, task_tag, stop_dependent=True, stop_requirements=False):
		""" Stop started task from registry

		:param task_tag: same as in :meth:`.WTaskDependencyRegistryStorage.stop_task` method
		:param stop_dependent: same as in :meth:`.WTaskDependencyRegistryStorage.stop_task` method
		:param stop_requirements: same as in :meth:`.WTaskDependencyRegistryStorage.stop_task` method
		:return: None
		"""
		registry = cls.registry_storage()
		registry.stop_task(task_tag, stop_dependent=stop_dependent, stop_requirements=stop_requirements)

	@classmethod
	def all_stop(cls):
		""" Stop every task started within this registry

		:return: None
		"""
		for task_tag in cls.registry_storage().tags():
			cls.stop_task(task_tag)
