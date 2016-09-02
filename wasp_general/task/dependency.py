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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from wasp_general.task.registry import WTaskRegistry, WRegisteredTask, WTaskRegistryStorage


class WTaskDependencyRegistryStorage(WTaskRegistryStorage):

	__multiple_tasks_per_tag__ = False

	#//WTaskStatus
	def add(self, task):
		return WTaskRegistryStorage.add(self, task)

	#//WDependentTask
	def dependency_check(self, task, skip_unresolved=False):

		def check(check_task, global_dependencies):
			if check_task.__registry_tag__ in global_dependencies:
				raise RuntimeError('Recursion dependencies for %s' % task.__registry_tag__)

			dependencies = global_dependencies.copy()
			dependencies.append(check_task.__registry_tag__)

			for dependency in check_task.__dependency__:
				dependent_task = self.tasks(dependency)
				if dependent_task is None and skip_unresolved is False:
					raise RuntimeError("Task '%s' dependency unresolved (%s)" % (task.__registry_tag__, dependency))

				if dependent_task is not None:
					check(dependent_task, dependencies)

		check(task, [])

	def start_task(self, task_name, skip_unresolved=False):
		task = self.tasks(task_name)
		if task is None:
			raise RuntimeError("Task '%s' wasn't found" % task_name)
		self.dependency_check(task, skip_unresolved=skip_unresolved)

		def start_dependency(start_task):
			for dependency in start_task.__dependency__:
				dependent_task = self.tasks(dependency)
				if dependent_task is None and skip_unresolved is False:
					raise RuntimeError("Task '%s' dependency unresolved (%s)" % (task.__registry_tag__, dependency))

				if dependent_task is not None:
					start_dependency(dependent_task)

			start_task.start()

		start_dependency(task)


class WTaskDependencyRegistry(WTaskRegistry):

	@classmethod
	def registry_storage(cls):
		if cls.__registry_storage__ is None:
			raise ValueError('__registry_storage__ must be defined')
		if isinstance(cls.__registry_storage__, WTaskDependencyRegistryStorage) is False:
			raise TypeError("Property '__registry_storage__' is invalid (must derived from WTaskRegistryBase)")

		return cls.__registry_storage__

	@classmethod
	def start_task(cls, task_name):
		registry = cls.registry_storage()
		registry.start_task(task_name)


class WDependentTask(WRegisteredTask):

	__dependency__ = []
	__description__ = None

	def __init__(cls, name, bases, dict):

		if issubclass(cls.__registry__, WTaskDependencyRegistry) is False:
			raise TypeError("Property '__registry__' of tasks class has invalid type (must be WTaskDependencyRegistry or its subclass)")

		if cls.__registry_tag__ is None:
			raise ValueError("Property '__registry_tag__' must be defined")

		if isinstance(cls.__registry_tag__, str):
			raise TypeError("Property '__registry_tag__' must be string type")

		WRegisteredTask.__init__(cls, name, bases, dict)
