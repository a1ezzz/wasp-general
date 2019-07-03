# -*- coding: utf-8 -*-
# wasp_general/api/registry.py
#
# Copyright (C) 2019 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
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

from wasp_general.verify import verify_type

from abc import ABCMeta, abstractmethod

# TODO: document the code


class WNoSuchAPIIdError(Exception):
	""" This exception is raised when a looked up API id is not found
	"""
	pass


class WDuplicateAPIIdError(Exception):
	""" This exception is raised when an attempt to register a descriptor with an id, that has been already
	registered, is made
	"""
	pass


class WAPIRegistryProto(metaclass=ABCMeta):
	""" This is prototype for a general registry, object that stores anything by id. It may look like a dict object,
	but this class should be used in order to distinguish registry operation and commonly used dict
	"""

	@abstractmethod
	def register(self, api_id, api_descriptor):
		""" Save the specified descriptor by the specified id

		:param api_id:
		:type api_id: any (hashable only)

		:param api_descriptor:
		:type api_descriptor: any

		:raise WDuplicateAPIIdError: when the specified API id has been registered already

		:rtype: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def get(self, api_id):
		""" Retrieve previously saved descriptor by an id

		:param api_id:
		:type api_id: any (hashable only)

		:raise WNoSuchAPIIdError: when the specified API id has been registered already

		:rtype: any
		"""
		raise NotImplementedError('This method is abstract')


class WAPIRegistry(WAPIRegistryProto):
	""" This is a basic registry implementation. It behaves like a dict mostly
	"""

	def __init__(self):
		""" Create new registry
		"""
		WAPIRegistryProto.__init__(self)
		self.__descriptors = {}

	def register(self, api_id, api_descriptor):
		""" :meth:`.WAPIRegistryProto.register` method implementation
		"""
		if api_id in self.__descriptors:
			raise WDuplicateAPIIdError('The specified id "%s" has been used already' % str(api_id))
		self.__descriptors[api_id] = api_descriptor

	def get(self, api_id):
		""" :meth:`.WAPIRegistryProto.register` method implementation
		"""
		try:
			return self.__descriptors[api_id]
		except KeyError:
			raise WNoSuchAPIIdError('No such entry: %s' % api_id)

	def __getitem__(self, item):
		""" Return descriptor by it's API id

		:param item: API id
		:type item: any (hashable only)

		:rtype: any
		"""
		return self.__descriptors[item]


@verify_type('strict', registry=WAPIRegistry)
def register_api(registry, api_id=None):
	""" This decorator helps to register function or static method in the specified registry

	:param registry:
	:type registry: WAPIRegistry

	:param api_id: id with which function will be registered. If it is not specified then function qualification \
	name will be used
	:type api_id: any

	:rtype: callable
	"""

	def decorator_fn(decorated_function):
			reg_id = api_id if api_id is not None else decorated_function.__qualname__
			registry.register(reg_id, decorated_function)
			return decorated_function

	return decorator_fn
