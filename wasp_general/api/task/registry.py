# -*- coding: utf-8 -*-
# wasp_general/task/registry.py
#
# Copyright (C) 2019 the wasp-general authors and contributors
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

from wasp_general.api.registry import WAPIRegistry, WDuplicateAPIIdError
from wasp_general.api.task.proto import WTaskRegistryProto, WTaskProto

from wasp_general.verify import verify_type, verify_subclass, verify_value


class WTaskRegistry(WTaskRegistryProto, WAPIRegistry):
	""" Simple :class:`.WTaskRegistryProto` class implementation
	"""

	@verify_type('strict', fallback_registry=(WTaskRegistryProto, None))
	def __init__(self, fallback_registry=None):
		""" Create new registry

		:param fallback_registry: a fallback registry that may be used for searching
		:type fallback_registry: WTaskRegistryProto | None
		"""
		WTaskRegistryProto.__init__(self)
		WAPIRegistry.__init__(self, fallback_registry=fallback_registry)

	@verify_type('strict', api_id=str)
	@verify_subclass('strict', api_descriptor=WTaskProto)
	@verify_value('strict', api_id=lambda x: len(x) > 0)
	def register(self, api_id, api_descriptor):
		""" :meth:`.WTaskRegistryProto.register` method implementation
		:type api_id: str
		:type api_descriptor: WTaskProto
		:rtype: None
		"""
		return WAPIRegistry.register(self, api_id, api_descriptor)


__default_task_registry__ = WTaskRegistry()
""" Instance of the default task registry
"""


@verify_type('strict', registry=(WTaskRegistryProto, type, None), task_tag=(str, None))
@verify_value('strict', task_tag=lambda x: x is None or len(x) > 0)
def register_class(task_tag, registry=None):
	""" Return a class decorator that will register original class

	:param task_tag: tag (name) of a task a decorated class represents
	:type task_tag: str | None

	:param registry: registry in which task will be registered (default registry is used for the 'None' value)
	:type registry: WTaskRegistryProto | None

	:rtype: callable
	"""

	def decorator_fn(cls):
		reg = registry
		if reg is None:
			reg = __default_task_registry__
		try:
			reg.register(task_tag, cls)
		except WDuplicateAPIIdError:
			current_entry = reg.get(task_tag)
			if current_entry is not cls:
				raise

		return cls
	return decorator_fn
