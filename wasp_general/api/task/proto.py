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


class WTaskProto(WCapabilitiesHolder):
	""" Basic task prototype. Derived classes must implement the only thing - to start
	"""

	@classmethod
	@abstractmethod
	def start(cls, *args, **kwargs):
		""" Start this task

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@classmethod
	def requirements(cls):
		""" Return tuple of task's names that are required to start in order this task to work. Or return
		None if this task may be started without any condition

		:rtype: tuple of str | None
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
	""" This launcher tracks started tasks
	"""

	@abstractmethod
	@verify_type('strict', task_tag=(str, None))
	@verify_value('strict', task_tag=lambda x: x is None or len(x) > 0)
	def started_tasks(self, task_tag=None):
		""" Return tasks that were started

		:param task_tag: filter tasks by tag. If this tag is specified, then only that type of tasks will
		be returned
		:type task_tag: str | None

		:rtype: tuple of WTaskProto
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', registry=WTaskRegistryProto, task_tag=str, skip_unresolved=bool)
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def start_task(self, registry, task_tag, *args, skip_unresolved=False, **kwargs):
		""" Star task from a registry and return it's id (instance id)

		:param registry: a registry from which a task will be get
		:type registry: WTaskRegistryProto

		:param task_tag: tag of task that should be started
		:type task_tag: str

		:param args: arguments that will be passed to :meth:`.WTaskProto.start` method
		:type args: any

		:param skip_unresolved: whether a task should be started if all the requirements was not met
		:type skip_unresolved: bool

		:param kwargs: named arguments that will be passed to :meth:`.WTaskProto.start` method
		:type kwargs: any

		:rtype: str
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type('strict', task_tag=str, stop_dependent=bool, stop_requirements=bool, instance_id=(str, None))
	@verify_value('strict', task_tag=lambda x: len(x) > 0)
	def stop_task(self, task_tag, stop_dependent=True, stop_requirements=False, instance_id=None):
		""" Stop a previously started task

		:param task_tag: a tag of task that should be stopped
		:type task_tag: str

		:param stop_dependent: whether to stop tasks that require a specified task
		:type stop_dependent: bool

		:param stop_requirements: whether to stop tasks that are requirement for a specifieds task
		:type stop_requirements: bool

		:param instance_id: stop a specific task instance but not all of them
		:type instance_id: str

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def all_stop(self):
		""" Stop all the started tasks

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')
