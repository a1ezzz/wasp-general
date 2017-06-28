# -*- coding: utf-8 -*-
# wasp_general/task/registry.py
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

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_subclass, verify_type
from wasp_general.task.base import WTask


class WRegisteredTask(ABCMeta):
	""" Metaclass for task, that is stored in registry.  Derived class must redefine __registry__ property
	(and __registry_tag__ depends on registry storage - see
	:attr:`.WTaskRegistryStorage.__multiple_tasks_per_tag__`)
	"""

	__auto_registry__ = True
	""" Flag specifies whether this class will be registered automatically in registry or not
	"""

	__registry_tag__ = None
	""" Tag, that represent task. Depends on registry storage, independent task could be marked the same tag
	"""

	__registry__ = None
	""" Registry, that holds this task. Must be redefined in derived classes.
	"""

	def __init__(cls, name, bases, namespace):
		""" Construct new class. Derived class must redefine __registry__ property (and __registry_tag__
		depends on registry storage - see :attr:`.WTaskRegistryStorage.__multiple_tasks_per_tag__`)

		:param name: as name in type(cls, name, bases, namespace)
		:param bases: as bases in type(cls, name, bases, namespace)
		:param namespace: as namespace in type(cls, name, bases, namespace)
		"""
		ABCMeta.__init__(cls, name, bases, namespace)

		if cls.__auto_registry__ is not True:
			return

		if cls.__registry__ is None:
			raise ValueError('__registry__ must be defined')

		if issubclass(cls.__registry__, WTaskRegistry) is False:
			raise TypeError(
				"Property '__registry__' of tasks class has invalid type (must be"
				"WTaskRegistry or its subclass)"
			)

		if issubclass(cls, WTask) is False:
			raise TypeError('This class must inherit WTask class')

		cls.__registry__.add(cls)


class WTaskRegistryBase(metaclass=ABCMeta):
	""" Prototype for registry storage. Derived class must redefined following methods
	"""

	@abstractmethod
	def add(self, task):
		""" Add task to storage

		:param task: task to add (WTask class with WRegisteredTask metaclass)
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def remove(self, task):
		""" Remove task from storage

		:param task: task to remove (WTask class with WRegisteredTask metaclass)
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def clear(self):
		""" Remove every task from storage

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def tasks(self, registry_tag):
		""" Get tasks from registry by its tag

		:param registry_tag: any hash-able object
		:return: Return task or list of tasks
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def count(self):
		""" Registered task count

		:return: int
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def tags(self):
		""" Return available registry tags

		:return: tuple of str
		"""
		raise NotImplementedError('This method is abstract')


class WTaskRegistryStorage(WTaskRegistryBase):
	""" Simple registry storage implementation
	"""

	__multiple_tasks_per_tag__ = True
	""" Flag that switches storing behaviour. If True - multiple task with the same tag are permitted,
	otherwise - task with the same tag is treated as error.
	"""

	def __init__(self):
		""" Construct new registry storage
		"""
		self.__registry = {}

	@verify_subclass(task_cls=WTask)
	@verify_type(task_cls=WRegisteredTask)
	def add(self, task_cls):
		""" Add task to this storage. Depends on :attr:`.WTaskRegistryStorage.__multiple_tasks_per_tag__`
		tasks with the same __registry_tag__ can be treated as error.

		:param task_cls: task to add
		:return: None
		"""

		registry_tag = task_cls.__registry_tag__
		if registry_tag not in self.__registry.keys():
			self.__registry[registry_tag] = [task_cls]
		elif self.__multiple_tasks_per_tag__ is True:
			self.__registry[registry_tag].append(task_cls)
		else:
			raise RuntimeError('Multiple tasks with same tag appended')

	@verify_subclass(task_cls=WTask)
	@verify_type(task_cls=WRegisteredTask)
	def remove(self, task_cls):
		""" Remove task from the storage. If task class are stored multiple times
		(if :attr:`.WTaskRegistryStorage.__multiple_tasks_per_tag__` is True) - removes all of them.

		:param task_cls: task to remove
		:return: None
		"""
		registry_tag = task_cls.__registry_tag__
		if registry_tag in self.__registry.keys():
			self.__registry[registry_tag] = \
				list(filter(lambda x: x != task_cls, self.__registry[registry_tag]))
			if len(self.__registry[registry_tag]) == 0:
				self.__registry.pop(registry_tag)

	def clear(self):
		""" Removes every task from storage

		:return: None
		"""
		self.__registry.clear()

	def tasks(self, registry_tag):
		""" Get tasks from registry by its tag

		:param registry_tag: any hash-able object
		:return: Return task (if :attr:`.WTaskRegistryStorage.__multiple_tasks_per_tag__` is not True) or \
		list of tasks
		"""
		if registry_tag not in self.__registry.keys():
			return None
		tasks = self.__registry[registry_tag]
		return tasks if self.__multiple_tasks_per_tag__ is True else tasks[0]

	def tags(self):
		""" :meth:`.WTaskRegistryBase.tags` implementation
		"""
		return tuple(self.__registry.keys())

	def count(self):
		""" Registered task count

		:return: int
		"""
		result = 0
		for tasks in self.__registry.values():
			result += len(tasks)
		return result


class WTaskRegistry:
	""" Basic task registry. Derived classes must redefine __registry_storage__ property
	(see :attr:`.WTaskRegistry.__registry_storage__`)
	"""

	__registry_storage__ = None
	""" Storage that is used within this registry
	"""

	__skip_none_registry_tag__ = True
	""" Flag defines whether to register task which has __registry_tag__ set to None or not
	"""

	@classmethod
	def registry_storage(cls):
		""" Get registry storage

		:return: WTaskRegistryBase
		"""
		if cls.__registry_storage__ is None:
			raise ValueError('__registry_storage__ must be defined')
		if isinstance(cls.__registry_storage__, WTaskRegistryBase) is False:
			raise TypeError("Property '__registry_storage__' is invalid (must derived from WTaskRegistryBase)")

		return cls.__registry_storage__

	@classmethod
	@verify_subclass('paranoid', task_cls=WTask)
	@verify_type('paranoid', task_cls=WRegisteredTask)
	def add(cls, task_cls):
		""" Add task class to storage

		:param task_cls: task to add
		:return: None
		"""

		if task_cls.__registry_tag__ is None and cls.__skip_none_registry_tag__ is True:
			return

		cls.registry_storage().add(task_cls)

	@classmethod
	@verify_subclass('paranoid', task_cls=WTask)
	@verify_type('paranoid', task_cls=WRegisteredTask)
	def remove(cls, task_cls):
		""" Remove task class to storage

		:param task_cls: task to remove
		:return: None
		"""
		cls.registry_storage().remove(task_cls)

	@classmethod
	def clear(cls):
		""" Remove every task from storage

		:return: None
		"""
		cls.registry_storage().clear()
