# -*- coding: utf-8 -*-
# wasp_general/network/clients/webdav.py
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

import webdav3.client
from webdav3.exceptions import WebDavException
from abc import abstractmethod

from wasp_general.verify import verify_type, verify_value
from wasp_general.uri import WSchemeSpecification, WURIQuery, WURI, WURIComponentVerifier, WURIQueryVerifier
from wasp_general.uri import WStrictURIQuery

from wasp_general.network.clients.proto import WNetworkClientCapabilities, WClientCapabilityError
from wasp_general.network.clients.proto import WClientConnectionError
from wasp_general.network.clients.virtual_dir import WVirtualDirectoryClient


class WWebDavClientBase(WVirtualDirectoryClient):

	@verify_type(uri=WURI, http_protocol_scheme=str)
	@verify_value(http_protocol_scheme=lambda x: len(x) > 0)
	def __init__(self, uri, http_protocol_scheme):
		WVirtualDirectoryClient.__init__(self, uri)

		webdav_uri = '%s://%s' % (http_protocol_scheme, uri.hostname())
		if uri.port() is not None:
			webdav_uri += (':%s' % uri.port())

		if uri.path() is not None:
			webdav_uri += ('/%s' % uri.path())

		webdav_options = {
			'webdav_hostname': webdav_uri
		}

		if uri.username() is not None:
			webdav_options['webdav_login'] = uri.username()
			if uri.password() is not None:
				webdav_options['webdav_password'] = uri.password()

		query = uri.query()
		if query is not None:
			parsed_query = WURIQuery.parse(query)
			self.session_path(parsed_query['remote_path'][0])

		self.__dav_client = webdav3.client.Client(webdav_options)

	def dav_client(self):
		return self.__dav_client

	def connect(self):
		try:
			self.list_directory()
		except WClientCapabilityError as e:
			raise WClientConnectionError('Unable to connect to the server') from e

	def disconnect(self):
		self.session_path(self.directory_sep())

	@classmethod
	@abstractmethod
	def scheme_name(cls):
		raise NotImplementedError('This method is abstract')

	@classmethod
	def scheme_specification(cls):
		return WSchemeSpecification(
			cls.scheme_name(),

			WURIComponentVerifier(WURI.Component.username, WURIComponentVerifier.Requirement.optional),
			WURIComponentVerifier(WURI.Component.password, WURIComponentVerifier.Requirement.optional),
			WURIComponentVerifier(WURI.Component.hostname, WURIComponentVerifier.Requirement.required),
			WURIComponentVerifier(WURI.Component.port, WURIComponentVerifier.Requirement.optional),
			WURIComponentVerifier(WURI.Component.path, WURIComponentVerifier.Requirement.optional),
			WURIQueryVerifier(
				WURIComponentVerifier.Requirement.optional,
				WStrictURIQuery.ParameterSpecification(
					'remote_path', nullable=False, multiple=False, optional=False
				),
				extra_parameters=False
			)
		)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.current_dir)
	def current_directory(self, *args, **kwargs):
		return self.session_path()

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.change_dir, WebDavException, ValueError)
	@verify_type(path=str)
	@verify_value(path=lambda x: len(x) > 0)
	def change_directory(self, path, *args, **kwargs):
		client = self.dav_client()
		previous_path = self.session_path()
		try:
			if client.is_dir(self.session_path(path)) is False:
				raise ValueError('Unable to change current working directory to non-directory entry')
		except Exception:
			self.session_path(previous_path)
			raise

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.list_dir, WebDavException)
	def list_directory(self, *args, **kwargs):
		return tuple(self.dav_client().list(self.session_path()))

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.make_dir, WebDavException)
	@verify_type(directory_name=str)
	@verify_value(directory_name=lambda x: len(x) > 0)
	def make_directory(self, directory_name, *args, **kwargs):
		self.dav_client().mkdir(self.join_path(self.session_path(), directory_name))

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.remove_dir, WebDavException, ValueError)
	@verify_type(directory_name=str)
	@verify_value(directory_name=lambda x: len(x) > 0)
	def remove_directory(self, directory_name, *args, **kwargs):
		client = self.dav_client()
		remote_path = self.join_path(self.session_path(), directory_name)

		if client.is_dir(remote_path) is False:
			raise ValueError('Unable to remove non-directory entry')
		client.clean(remote_path)

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.upload_file, WebDavException)
	@verify_type(file_name=str)
	@verify_value(file_name=lambda x: len(x) > 0)
	def upload_file(self, file_name, file_obj, *args, **kwargs):
		self.dav_client().upload_to(file_obj, self.join_path(self.session_path(), file_name))

	@WNetworkClientCapabilities.capability(WNetworkClientCapabilities.remove_file, WebDavException, ValueError)
	@verify_type(file_name=str)
	@verify_value(file_name=lambda x: len(x) > 0)
	def remove_file(self, file_name, *args, **kwargs):
		client = self.dav_client()
		remote_path = self.join_path(self.session_path(), file_name)
		if client.is_dir(remote_path) is True:
			raise ValueError('Unable to remove non-file entry')
		client.clean(remote_path)


class WWebDavClient(WWebDavClientBase):

	@verify_type('paranoid', uri=WURI)
	def __init__(self, uri):
		WWebDavClientBase.__init__(self, uri, 'http')

	@classmethod
	def scheme_name(cls):
		return 'dav'


class WWebDavsClient(WWebDavClientBase):

	@verify_type('paranoid', uri=WURI)
	def __init__(self, uri):
		WWebDavClientBase.__init__(self, uri, 'https')

	@classmethod
	def scheme_name(cls):
		return 'davs'
