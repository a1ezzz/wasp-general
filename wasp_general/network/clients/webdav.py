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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import webdav3.client
from abc import abstractmethod

from wasp_general.uri import WSchemeSpecification, WURIQuery, WURI, WURIComponentVerifier, WURIQueryVerifier, WStrictURIQuery
from wasp_general.network.clients.base import WBasicNetworkClientProto
from wasp_general.network.clients.base import WBasicNetworkClientListDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientChangeDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientMakeDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientCurrentDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientUploadFileCapability
from wasp_general.network.clients.base import WBasicNetworkClientRemoveFileCapability


class WWebDavClientBase(WBasicNetworkClientProto):

	def __init__(self, uri, http_protocol_scheme):
		WBasicNetworkClientProto.__init__(self, uri)

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

		self.__session_path = '/'

		query = uri.query()
		if query is not None:
			parsed_query = WURIQuery.parse(query)
			self.__session_path = parsed_query['remote_path']

		self.__dav_client = webdav3.client.Client(webdav_options)

	def dav_client(self):
		return self.__dav_client

	def session_path(self, value=None):
		if value is not None:
			self.__session_path = value
		return self.__session_path

	def _close(self):
		pass

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
			WURIComponentVerifier(WURI.Component.path, WURIComponentVerifier.Requirement.optional),
			WURIQueryVerifier(
				WURIComponentVerifier.Requirement.optional,
				WStrictURIQuery.ParameterSpecification(
					'remote_path', nullable=False, multiple=False, optional=False
				),
				extra_parameters=False
			)
		)

	@classmethod
	def agent_capabilities(cls):
		return WWebDavClientListDirCapability, \
			WWebDavClientMakeDirCapability, \
			WWebDavCurrentDirCapability, \
			WWebDavChangeDirCapability, \
			WWebDavClientUploadFileCapability, \
			WWebDavClientRemoveFileCapability


class WWebDavClient(WWebDavClientBase):

	def __init__(self, uri):
		WWebDavClientBase.__init__(self, uri, 'http')

	@classmethod
	def scheme_name(cls):
		return 'dav'


class WWebDavsClient(WWebDavClientBase):

	def __init__(self, uri):
		WWebDavClientBase.__init__(self, uri, 'https')

	@classmethod
	def scheme_name(cls):
		return 'davs'


class WWebDavClientListDirCapability(WBasicNetworkClientListDirCapability):

	def request(self, *args, **kwargs):
		agent = self.network_agent()
		client = agent.dav_client()
		return tuple(client.list(agent.session_path()))


class WWebDavClientMakeDirCapability(WBasicNetworkClientMakeDirCapability):

	def request(self, directory_name, *args, **kwargs):
		agent = self.network_agent()
		client = agent.dav_client()
		return client.mkdir(agent.session_path() + '/' + directory_name) is True


class WWebDavCurrentDirCapability(WBasicNetworkClientCurrentDirCapability):

	def request(self, *args, **kwargs):
		return self.network_agent().session_path()


class WWebDavChangeDirCapability(WBasicNetworkClientChangeDirCapability):

	def request(self, path, *args, **kwargs):
		agent = self.network_agent()
		client = agent.dav_client()
		if client.isdir(path) is True:
			self.network_agent().session_path(path)
			return True
		return False


class WWebDavClientUploadFileCapability(WBasicNetworkClientUploadFileCapability):

	def request(self, file_name, file_obj, *args, **kwargs):
		agent = self.network_agent()
		client = agent.dav_client()
		client.upload_to(file_obj.read(), agent.session_path() + '/' + file_name)
		return True


class WWebDavClientRemoveFileCapability(WBasicNetworkClientRemoveFileCapability):

	def request(self, file_name, *args, **kwargs):
		agent = self.network_agent()
		client = agent.dav_client()
		remote_path = agent.session_path() + '/' + file_name
		path_info = client.info(remote_path)
		# check if it is a file
		client.clean(remote_path)
		return True
