# -*- coding: utf-8 -*-
# wasp_general/api/capability.py
#
# Copyright (C) 2018-2019 the wasp-general authors and contributors
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

# TODO: check docs

from abc import ABCMeta
from inspect import isfunction

from wasp_general.verify import verify_type, verify_value

"""
This module provides a possibility to define a "weak" interface classes. Such classes will have more several functions
that may be or may be not overridden by derived classes. And derived classes are permitted to override some functions
only. That type of function is called "capability". By design as a capability may be used a class methods only.
And "classmethod" or "staticmethod" can not be used.
"""


class WCapabilityDescriptor:
	""" This class describes a single capability. Every capability (function) has its own descriptor
	"""

	@verify_type('strict', capability_cls=type, capability_name=str)
	@verify_value('strict', capability_name=lambda x: len(x) > 0)
	def __init__(self, capability_cls, capability_name):
		"""

		:param capability_cls: class that defines a capability
		:type capability_cls: type

		:param capability_name: function name
		:type capability_name: str
		"""
		self.__cls = capability_cls
		self.__name = capability_name

	def cls(self):
		""" Return origin class

		:rtype: type
		"""
		return self.__cls

	def name(self):
		""" Return capability name

		:rtype: str
		"""
		return self.__name


def capability(f):
	""" Mark a decorated function as a capability

	:param f: function that is defined as a capability
	:type f: function

	:rtype: function
	"""
	f.__wasp_capability__ = None
	return f


class WCapabilitiesHolderMeta(ABCMeta):
	""" This metaclass sets capability descriptor for every newly marked capabilities
	"""

	def __init__(cls, name, bases, namespace):
		""" Generate new class with this metaclass

		:param name: same as 'name' in :meth:`.ABCMeta.__init__` method
		:param bases: same as 'bases' in :meth:`.ABCMeta.__init__` method
		:param namespace: same as 'namespace' in :meth:`.ABCMeta.__init__` method
		"""
		ABCMeta.__init__(cls, name, bases, namespace)

		for n in dir(cls):
			i = ABCMeta.__getattribute__(cls, n)
			if callable(i) and hasattr(i, '__wasp_capability__'):
				if isfunction(i) is False:
					raise TypeError(
						'Only functions may be a "capability". Classmethod or staticmethod '
						'are not supported'
					)
				if i.__wasp_capability__ is None:
					i.__wasp_capability__ = WCapabilityDescriptor(cls, i.__name__)

	def __getattribute__(cls, item):
		""" Return attribute value, but for capability return its descriptor

		:param item: attribute to return
		:type item: any

		:rtype: WCapabilityDescriptor | any
		"""
		result = ABCMeta.__getattribute__(cls, item)
		if hasattr(result, '__wasp_capability__'):
			return result.__wasp_capability__
		return result


@verify_type('strict', obj_capability=WCapabilityDescriptor)
def iscapable(obj, obj_capability):
	""" Check if the specified object (or type) is capable of something. I.e. check if a function from a descriptor
	has been overridden in the derived class. Return True if function has been overridden and False otherwise

	:param obj: object to check
	:type obj: object

	:param obj_capability: capability descriptor
	:type obj_capability: WCapabilityDescriptor

	:rtype: bool
	"""

	if isinstance(obj, type):
		if issubclass(obj, obj_capability.cls()) is True:
			f = getattr(obj, obj_capability.name())
			return not isinstance(f, WCapabilityDescriptor)
	elif isinstance(obj, obj_capability.cls()) is True:
		f = getattr(obj, obj_capability.name())
		return not hasattr(f, '__wasp_capability__')
	return False


class WCapabilitiesHolder(metaclass=WCapabilitiesHolderMeta):
	""" Simple base class for defining capabilities. Besides that this class uses :class:`.WCapabilitiesHolderMeta`
	metaclass already. This class overrides '__contains__' method, so 'in' operator may be used for checking
	whether a class has a capability
	"""

	@verify_type('paranoid', obj_capability=WCapabilityDescriptor)
	def __contains__(self, item):
		""" Check whether this object has a capability

		:param item: capability to check
		:type item: WCapabilityDescriptor

		:rtype: bool
		"""
		return iscapable(self, item)
