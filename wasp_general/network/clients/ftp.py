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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import ftplib

from wasp_general.network.clients.proto import WNetworkClientProto
from wasp_general.network.clients.base import WBasicNetworkClientProto
from wasp_general.network.clients.base import WBasicNetworkClientListDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientChangeDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientMakeDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientCurrentDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientUploadFileCapability
from wasp_general.network.clients.base import WBasicNetworkClientRemoveFileCapability


class WFTPClient(WBasicNetworkClientProto):

	def __init__(self, uri):
		WBasicNetworkClientProto.__init__(self, uri)

		try:
			ftp_args = {'host': uri.hostname()}
			# TODO: FTP class in python3.6 has port argument. But 3.4 doesn't
			'''
			if uri.port() is not None:
				ftp_args['port'] = uri.port()
			'''

			ftp_client = ftplib.FTP(**ftp_args)

			login_args = {}
			if uri.username() is not None:
				login_args['user'] = uri.username()
			if uri.password():
				login_args['passwd'] = uri.password()
			ftp_client.login(**login_args)

			ftp_client.cwd(uri.path() if uri.path() is not None else '/')

			self.__ftp_client = ftp_client

		except (ftplib.error_perm, ftplib.error_proto, ftplib.error_reply, ftplib.error_temp):
			raise WNetworkClientProto.ConnectionError(
				'Unable to connect to %s' % str(uri)
			)
		except OSError:  # no route to host and so on
			raise WNetworkClientProto.ConnectionError(
				'Unable to connect to %s' % str(uri)
			)

	def ftp_client(self):
		return self.__ftp_client

	def _close(self):
		self.__ftp_client.close()

	@classmethod
	def scheme(cls):
		return 'ftp'

	@classmethod
	def agent_capabilities(cls):
		return WFTPClientListDirCapability, \
			WFTPClientMakeDirCapability, \
			WFTPClientChangeDirCapability, \
			WFTPClientUploadFileCapability, \
			WFTPClientRemoveFileCapability


class WFTPClientChangeDirCapability(WBasicNetworkClientChangeDirCapability):

	def request(self, path, *args, exec_cmd=None, **kwargs):
		try:
			self.network_agent().ftp_client().cwd(path)
			if exec_cmd is not None:
				return self.network_agent().request(exec_cmd, *args, **kwargs)
			return True
		except (ftplib.error_perm, ftplib.error_proto, ftplib.error_reply, ftplib.error_temp):
			if exec_cmd is not None:
				return
			return False


class WFTPClientCurrentDirCapability(WBasicNetworkClientCurrentDirCapability):

	def request(self, *args, **kwargs):
		return self.network_agent().ftp_client().pwd()


class WFTPClientListDirCapability(WBasicNetworkClientListDirCapability):

	def request(self, *args, **kwargs):
		try:
			return tuple(self.network_agent().ftp_client().nlst())
		except (ftplib.error_perm, ftplib.error_proto, ftplib.error_reply, ftplib.error_temp):
			return


class WFTPClientMakeDirCapability(WBasicNetworkClientMakeDirCapability):

	def request(self, directory_name, *args, **kwargs):
		try:
			return len(self.network_agent().ftp_client().mkd(directory_name)) > 0
		except (ftplib.error_perm, ftplib.error_proto, ftplib.error_reply, ftplib.error_temp):
			return False


class WFTPClientUploadFileCapability(WBasicNetworkClientUploadFileCapability):

	def request(self, file_name, file_obj, *args, **kwargs):
		try:
			self.network_agent().ftp_client().storbinary('STOR ' + file_name, file_obj)
			return True
		except (ftplib.error_perm, ftplib.error_proto, ftplib.error_reply, ftplib.error_temp):
			return False


class WFTPClientRemoveFileCapability(WBasicNetworkClientRemoveFileCapability):

	def request(self, file_name, *args, **kwargs):
		try:
			self.network_agent().ftp_client().delete(file_name)
			return True
		except (ftplib.error_perm, ftplib.error_proto, ftplib.error_reply, ftplib.error_temp):
			return False
