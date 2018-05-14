# -*- coding: utf-8 -*-
# wasp_general/capability.py
#
# Copyright (C) 2018 the wasp-general authors and contributors
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

from abc import ABCMeta

from wasp_general.verify import verify_type


class WCapabilitiesHolderMeta(ABCMeta):
	""" Metaclass that stores different "capabilities". Each "capability" is a function that implement a common
	function. This metaclass does not replace but extends interface pattern. If a class implement less then five
	interfaces, then this metaclass must be omitted. But in case of dozens different "interfaces" implementation,
	it is possible to use each function as a "capability" and write a cleaner code.
	"""

	def __init__(cls, name, bases, namespace):
		""" Generate new class with this metaclass. Find and register every "capability", that were defined
		by a specified class

		:param name: same as 'name' in :meth:`.ABCMeta.__init__` method
		:param bases: same as 'bases' in :meth:`.ABCMeta.__init__` method
		:param namespace: same as 'namespace' in :meth:`.ABCMeta.__init__` method
		"""
		ABCMeta.__init__(cls, name, bases, namespace)

		cls.__class_capabilities__ = {}

		for i in dir(cls):
			i = getattr(cls, i)
			if i is not None and hasattr(i, '__capability_name__'):
				cap_name = i.__capability_name__
				if cap_name in cls.__class_capabilities__:
					raise ValueError(
						'Unable to register capability "%s" for class "%s" and method "%s". '
						'This capability has been already defined for "%s"' %
						(cap_name, name, i.__name__, cls.__class_capabilities__[cap_name])
					)
				cls.__class_capabilities__[cap_name] = i.__name__

	@staticmethod
	@verify_type(cap_name=str)
	def capability(cap_name):
		""" This is a decorator, that mark the specified function with a capability name. Later on, marked
		functions will be processed by this metaclass and registered

		:param cap_name: capability name with which the decorated function will be marked. It must be unique
		within a single class

		:return: decorating function
		"""
		def fn_decorator(original_function):
			original_function.__capability_name__ = cap_name
			return original_function
		return fn_decorator


class WCapabilitiesHolder(metaclass=WCapabilitiesHolderMeta):
	""" Class that may be used for accessing registered capabilities. There is only one assumption, "capability"
	must be a general method (bounded method)
	"""

	def capability(self, cap_name):
		""" Return capability by its name

		:param cap_name: name of a capability to return
		:return: bounded method or None (if a capability is not found)
		"""
		if cap_name in self.__class_capabilities__:
			function_name = self.__class_capabilities__[cap_name]
			return getattr(self, function_name)
