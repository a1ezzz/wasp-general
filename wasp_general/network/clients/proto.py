# -*- coding: utf-8 -*-
# wasp_general/network/clients/proto.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

from abc import abstractmethod
from enum import Enum
from decorator import decorator

from wasp_general.verify import verify_type, verify_value, verify_subclass

from wasp_general.uri import WSchemeHandler, WURI
from wasp_general.capability import WCapabilitiesHolder


class WClientConnectionError(Exception):
	""" An exception is raised when connection attempt is failed
	"""
	pass


class WClientCapabilityError(Exception):
	""" An exception is raised when capability execution is failed
	"""
	pass


class WNetworkClientCapabilities(Enum):
	""" List of common capabilities.
	"""

	current_dir = 'current_dir'
	change_dir = 'change_dir'
	list_dir = 'list_dir'
	make_dir = 'make_dir'
	remove_dir = 'remove_dir'
	upload_file = 'upload_file'
	remove_file = 'remove_file'

	@staticmethod
	@verify_subclass(wrap_exceptions=Exception)
	def capability(cap, *wrap_exceptions):
		""" Return a decorator, that registers function as capability. Also, all specified exceptions are
		caught and instead of them the :class:`.WClientCapabilityError` exception is raised

		:param cap: target function capability (may be a str or :class:`.WNetworkClientCapabilities` class )
		:param wrap_exceptions: exceptions to caught

		:return: decorator
		"""
		if isinstance(cap, WNetworkClientCapabilities) is True:
			cap = cap.value
		elif isinstance(cap, str) is False:
			raise TypeError('Invalid capability type')

		def first_level_decorator(decorated_function):
			def second_level_decorator(original_function, *args, **kwargs):

				if len(wrap_exceptions) == 0:
					return original_function(*args, **kwargs)
				try:
					return original_function(*args, **kwargs)
				except wrap_exceptions as e:
					raise WClientCapabilityError(
						'Error during "%s" capability execution' % cap
					) from e
			result_fn = decorator(second_level_decorator)(decorated_function)
			result_fn.__capability_name__ = cap
			return result_fn
		return first_level_decorator


class WNetworkClientProto(WSchemeHandler, WCapabilitiesHolder):
	""" Base class for network clients. This class implements :class:`.WSchemeHandler` to handle connections
	encoded as URI and :class:`.WCapabilitiesHolder` to use capabilities as different client requests
	"""

	@verify_type(uri=WURI)
	def __init__(self, uri):
		""" Create new network client

		:param uri: URI, that describes client connection
		"""
		WSchemeHandler.__init__(self)
		WCapabilitiesHolder.__init__(self)
		self.__uri = uri

	@abstractmethod
	def connect(self):
		""" Connect to a source specified in URI

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def disconnect(self):
		""" Disconnect from a source

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	def uri(self):
		""" Return an URI, that was specified in a constructor

		:return: WURI
		"""
		return self.__uri

	@verify_type(cap_name=(str, WNetworkClientCapabilities))
	def capability(self, cap_name):
		""" Overrides original :meth:`.WCapabilitiesHolder.capability` method to support
		:class:`.WNetworkClientCapabilities` as a capability value
		"""
		if isinstance(cap_name, WNetworkClientCapabilities) is True:
			cap_name = cap_name.value
		return WCapabilitiesHolder.capability(self, cap_name)

	@verify_type(caps=(str, WNetworkClientCapabilities))
	def has_capabilities(self, *caps):
		""" Overrides original :meth:`.WCapabilitiesHolder.has_capabilities` method to support
		:class:`.WNetworkClientCapabilities` as a capability value
		"""
		for cap in caps:
			if isinstance(cap, WNetworkClientCapabilities) is True:
				cap = cap.value
			if WCapabilitiesHolder.has_capabilities(self, cap) is False:
				return False
		return True

	@verify_type(cap_name=(str, WNetworkClientCapabilities))
	def __call__(self, cap_name, *args, **kwargs):
		""" Overrides original :meth:`.WCapabilitiesHolder.__call__` method to support
		:class:`.WNetworkClientCapabilities` as a capability value
		"""
		if isinstance(cap_name, WNetworkClientCapabilities) is True:
			cap_name = cap_name.value
		return WCapabilitiesHolder.__call__(self, cap_name, *args, **kwargs)

	@classmethod
	@verify_type(uri=WURI)
	def create_handler(cls, uri, **kwargs):
		""" :meth:`.WSchemeHandler.create_handler` method implementation
		"""
		return cls(uri)

	# noinspection PyMethodMayBeStatic
	def directory_sep(self):
		""" Return symbol that is used by this client as a directory separator. If a path starts with that
		symbol then it treats as an absolute path by default

		:return: str
		"""
		return '/'

	def current_directory(self, *args, **kwargs):
		""" Return current session directory

		:param args: extra positional arguments that may be used by a capability
		:param kwargs: extra keyword-based arguments that may be used by a capability

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(path=str)
	@verify_value(path=lambda x: len(x) > 0)
	def change_directory(self, path, *args, **kwargs):
		""" Change current session directory to the specified one. If the path begins with directory separator
		then it may be treated as an absolute path

		:param path: target directory
		:param args: extra positional arguments that may be used by a capability
		:param kwargs: extra keyword-based arguments that may be used by a capability

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	def list_directory(self, *args, **kwargs):
		""" List current session directory

		:param args: extra positional arguments that may be used by a capability
		:param kwargs: extra keyword-based arguments that may be used by a capability

		:return: tuple of str
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(directory_name=str)
	@verify_value(directory_name=lambda x: len(x) > 0)
	def make_directory(self, directory_name, *args, **kwargs):
		""" Create directory. A directory is created in a current session directory. And a name must not
		contain a directory separator

		:param directory_name: directory name to create
		:param args: extra positional arguments that may be used by a capability
		:param kwargs: extra keyword-based arguments that may be used by a capability

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(directory_name=str)
	@verify_value(directory_name=lambda x: len(x) > 0)
	def remove_directory(self, directory_name, *args, **kwargs):
		""" Remove directory. A directory is removed from a current session directory. And a name must not
		contain a directory separator.

		:param directory_name: directory name to remove
		:param args: extra positional arguments that may be used by a capability
		:param kwargs: extra keyword-based arguments that may be used by a capability

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(file_name=str)
	@verify_value(file_name=lambda x: len(x) > 0)
	def upload_file(self, file_name, file_obj, *args, **kwargs):
		""" Upload file. File will be uploaded to a current session directory. A name must not contain
		a directory separator

		:param file_name: target file name
		:param file_obj: source object to upload
		:param args: extra positional arguments that may be used by a capability
		:param kwargs: extra keyword-based arguments that may be used by a capability

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@verify_type(file_name=str)
	@verify_value(file_name=lambda x: len(x) > 0)
	def remove_file(self, file_name, *args, **kwargs):
		""" Remove file. File will be removed from a current session directory. A name must not contain
		a directory separator

		:param file_name: file to remove
		:param args: extra positional arguments that may be used by a capability
		:param kwargs: extra keyword-based arguments that may be used by a capability

		:return: None
		"""
		raise NotImplementedError('This method is abstract')
