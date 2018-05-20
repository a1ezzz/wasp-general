# -*- coding: utf-8 -*-
# wasp_general/network/clients/ftp.py
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

import ftplib

from wasp_general.uri import WSchemeSpecification, WURI, WURIComponentVerifier
from wasp_general.network.clients.proto import WNetworkClientProto
from wasp_general.verify import verify_type, verify_value

from wasp_general.network.clients.proto import WClientConnectionError, WClientCapabilityError
from wasp_general.network.clients.proto import WNetworkClientCapabilities


__basic_ftp_exceptions__ = (ftplib.error_perm, ftplib.error_proto, ftplib.error_reply, ftplib.error_temp)


class WFTPClient(WNetworkClientProto):
	""" FTP-client implementation of :class:`.WNetworkClientProto`
	"""

	@verify_type('paranoid', uri=WURI)
	def __init__(self, uri):
		""" Create new FTP-client

		:param uri: URI for a client connection
		"""
		WNetworkClientProto.__init__(self, uri)

		self.__ftp_client = ftplib.FTP()

		self.__ftp_connect_args = {'host': uri.hostname()}
		# TODO: FTP class in python3.6 has port argument. But 3.4 doesn't
		# if uri.port() is not None: self.__ftp_connect_args['port'] = uri.port()

		self.__ftp_auth_args = {}

		if uri.username() is not None:
			self.__ftp_auth_args['user'] = uri.username()
		if uri.password():
			self.__ftp_auth_args['passwd'] = uri.password()

	def ftp_client(self):
		""" Return FTP-client for accessing a server (internal usage only)

		:return: ftplib.FTP
		"""
		return self.__ftp_client

	def connect(self):
		""" :meth:`.WNetworkClientProto.connect` method implementation
		"""
		exceptions = list(__basic_ftp_exceptions__)
		exceptions.append(OSError)  # OSError for "no route to host" issue
		exceptions.append(ConnectionRefusedError)  # for unavailable service on a host

		try:
			self.ftp_client().connect(**self.__ftp_connect_args)
			self.ftp_client().login(**self.__ftp_auth_args)
		except tuple(exceptions) as e:
			raise WClientConnectionError('Unable to connect to the server') from e
		try:
			path = self.uri().path()
			if path is None:
				path = self.directory_sep()
			self.change_directory(path)
		except WClientCapabilityError as e:
			raise WClientConnectionError(
				'Unable to change current working directory to the specified one'
			) from e

	def disconnect(self):
		""" :meth:`.WNetworkClientProto.disconnect` method implementation
		"""
		self.ftp_client().close()

	@classmethod
	def scheme_specification(cls):
		""" :meth:`.WSchemeHandler.scheme_specification` method implementation
		"""
		return WSchemeSpecification(
			'ftp',
			WURIComponentVerifier(WURI.Component.username, WURIComponentVerifier.Requirement.optional),
			WURIComponentVerifier(WURI.Component.password, WURIComponentVerifier.Requirement.optional),
			WURIComponentVerifier(WURI.Component.hostname, WURIComponentVerifier.Requirement.required),
			WURIComponentVerifier(WURI.Component.path, WURIComponentVerifier.Requirement.optional)
		)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.current_dir, *__basic_ftp_exceptions__)
	def current_directory(self, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.current_directory` method implementation
		"""
		return self.ftp_client().pwd()

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.change_dir, *__basic_ftp_exceptions__)
	@verify_type(path=str)
	@verify_value(path=lambda x: len(x) > 0)
	def change_directory(self, path, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.change_directory` method implementation
		"""
		self.ftp_client().cwd(path)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.list_dir, *__basic_ftp_exceptions__)
	def list_directory(self, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.list_directory` method implementation
		"""
		return tuple(self.ftp_client().nlst())

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.make_dir, *__basic_ftp_exceptions__)
	@verify_type(directory_name=str)
	@verify_value(directory_name=lambda x: len(x) > 0)
	def make_directory(self, directory_name, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.make_directory` method implementation
		"""
		self.ftp_client().mkd(directory_name)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.remove_dir, *__basic_ftp_exceptions__)
	@verify_type(directory_name=str)
	@verify_value(directory_name=lambda x: len(x) > 0)
	def remove_directory(self, directory_name, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.remove_directory` method implementation
		"""
		self.ftp_client().rmd(directory_name)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.upload_file, *__basic_ftp_exceptions__)
	@verify_type(file_name=str)
	@verify_value(file_name=lambda x: len(x) > 0)
	def upload_file(self, file_name, file_obj, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.upload_file` method implementation
		"""
		self.ftp_client().storbinary('STOR ' + file_name, file_obj)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.remove_file, *__basic_ftp_exceptions__)
	@verify_type(file_name=str)
	@verify_value(file_name=lambda x: len(x) > 0)
	def remove_file(self, file_name, *args, **kwargs):
		""" :meth:`.WNetworkClientProto.remove_file` method implementation
		"""
		self.ftp_client().delete(file_name)
