# -*- coding: utf-8 -*-
# wasp_general/network/clients/file.py
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

import io
import os

from wasp_general.uri import WSchemeSpecification, WURIComponentVerifier, WURI
from wasp_general.network.clients.proto import WClientCapabilityError, WClientConnectionError
from wasp_general.network.clients.proto import WNetworkClientCapabilities

from wasp_general.network.clients.virtual_dir import WVirtualDirectoryClient

from wasp_general.verify import verify_type, verify_value


__basic_file_exceptions__ = (
	FileExistsError, PermissionError, IsADirectoryError, FileNotFoundError, NotADirectoryError, FileExistsError
)  # exceptions that are raised during I/O operations


class WLocalFileClient(WVirtualDirectoryClient):
	""" FTP-client implementation of :class:`.WNetworkClientProto`
	"""

	@verify_type(uri=WURI)
	def __init__(self, uri):
		"""  Create new client that interacts with local filesystem

		:param uri: URI for a client connection
		"""
		WVirtualDirectoryClient.__init__(self, uri, start_path=uri.path())

	def directory_sep(self):
		""" :meth:`.WNetworkClientProto.directory_sep` implementation
		"""
		return os.path.sep

	def connect(self):
		""" :meth:`.WNetworkClientProto.connect` method implementation
		"""
		try:
			self.list_directory()
		except WClientCapabilityError as e:
			raise WClientConnectionError(
				'Unable to change current working directory to the specified one'
			) from e

	def disconnect(self):
		""" :meth:`.WNetworkClientProto.disconnect` method implementation
		"""
		self.session_path(self.directory_sep())

	@classmethod
	def scheme_specification(cls):
		""" :meth:`.WSchemeHandler.scheme_specification` method implementation
		"""
		return WSchemeSpecification(
			'file',
			WURIComponentVerifier(WURI.Component.path, WURIComponentVerifier.Requirement.optional)
		)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.current_dir, *__basic_file_exceptions__)
	def current_directory(self, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.current_directory` method implementation
		"""
		return self.session_path()

	@WNetworkClientCapabilities.capability(
		WNetworkClientCapabilities.change_dir, ValueError, *__basic_file_exceptions__
	)
	@verify_type(path=str)
	@verify_value(path=lambda x: len(x) > 0)
	def change_directory(self, path, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.change_directory` method implementation
		"""
		previous_path = self.session_path()
		self.session_path(path)
		if os.path.isdir(self.full_path()) is False:
			self.session_path(previous_path)
			raise ValueError('Unable to change directory. It does not exist or is not a directory')

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.list_dir, *__basic_file_exceptions__)
	def list_directory(self, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.list_directory` method implementation
		"""
		return tuple(os.listdir(self.full_path()))

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.make_dir, *__basic_file_exceptions__)
	@verify_type(directory_name=str)
	@verify_value(directory_name=lambda x: len(x) > 0)
	def make_directory(self, directory_name, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.make_directory` method implementation
		"""
		previous_path = self.session_path()
		try:
			self.session_path(directory_name)
			os.mkdir(self.full_path())
		finally:
			self.session_path(previous_path)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.remove_dir, *__basic_file_exceptions__)
	@verify_type(directory_name=str)
	@verify_value(directory_name=lambda x: len(x) > 0)
	def remove_directory(self, directory_name, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.remove_directory` method implementation
		"""
		previous_path = self.session_path()
		try:
			self.session_path(directory_name)
			os.rmdir(self.full_path())
		finally:
			self.session_path(previous_path)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.upload_file, *__basic_file_exceptions__)
	@verify_type(file_name=str)
	@verify_value(file_name=lambda x: len(x) > 0)
	def upload_file(self, file_name, file_obj, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.upload_file` method implementation
		"""
		previous_path = self.session_path()
		try:
			self.session_path(file_name)
			with open(self.full_path(), mode='wb') as f:
				chunk = file_obj.read(io.DEFAULT_BUFFER_SIZE)
				while len(chunk) > 0:
					f.write(chunk)
					chunk = file_obj.read(io.DEFAULT_BUFFER_SIZE)
		finally:
			self.session_path(previous_path)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.remove_file, *__basic_file_exceptions__)
	@verify_type(file_name=str)
	@verify_value(file_name=lambda x: len(x) > 0)
	def remove_file(self, file_name, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.remove_file` method implementation
		"""
		previous_path = self.session_path()
		try:
			self.session_path(file_name)
			os.unlink(self.full_path())
		finally:
			self.session_path(previous_path)
