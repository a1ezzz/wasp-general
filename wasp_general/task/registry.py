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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod

from wasp_general.task.base import WTask


class WTaskRegistryBase(metaclass=ABCMeta):

	@abstractmethod
	def add(self, task):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def remove(self, task):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def clear(self):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def tasks(self, registry_tag):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def count(self):
		raise NotImplementedError('This method is abstract')


class WTaskRegistryStorage(WTaskRegistryBase):

	__multiple_tasks_per_tag__ = True

	def __init__(self):
		self.__registry = {}

	def add(self, task):
		registry_tag = task.__registry_tag__
		if registry_tag not in self.__registry.keys():
			self.__registry[registry_tag] = [task]
		elif self.__multiple_tasks_per_tag__ is True:
			self.__registry[registry_tag].append(task)
		else:
			raise RuntimeError('Multiple tasks with same tag appended')

	def remove(self, task):
		registry_tag = task.__registry_tag__
		if registry_tag in self.__registry.keys():
			self.__registry[registry_tag].remove(task)
			if len(self.__registry[registry_tag]) == 0:
				self.__registry.pop(registry_tag)

	def clear(self):
		self.__registry.clear()

	def tasks(self, registry_tag):
		if registry_tag not in self.__registry.keys():
			return None
		tasks = self.__registry[registry_tag]
		return tasks if self.__multiple_tasks_per_tag__ is True else tasks[0]

	def count(self):
		result = 0
		for tasks in self.__registry.values():
			result += len(tasks)
		return result


class WTaskRegistry:

	__registry_storage__ = None

	@classmethod
	def registry_storage(cls):
		if cls.__registry_storage__ is None:
			raise ValueError('__registry_storage__ must be defined')
		if isinstance(cls.__registry_storage__, WTaskRegistryBase) is False:
			raise TypeError("Property '__registry_storage__' is invalid (must derived from WTaskRegistryBase)")

		return cls.__registry_storage__

	@classmethod
	def add(cls, task):
		cls.registry_storage().add(task)

	@classmethod
	def remove(cls, task):
		cls.registry_storage().remove(task)

	@classmethod
	def clear(cls):
		cls.registry_storage().clear()


class WRegisteredTask(ABCMeta):

	__registry_tag__ = None
	__registry__ = None

	def __init__(cls, name, bases, dict):
		ABCMeta.__init__(cls, name, bases, dict)

		if cls.__registry__ is None:
			raise ValueError('__registry__ must be defined')

		if issubclass(cls.__registry__, WTaskRegistry) is False:
			raise TypeError("Property '__registry__' of tasks class has invalid type (must be WTaskRegistry or its subclass)")

		cls.__registry__.add(cls)
