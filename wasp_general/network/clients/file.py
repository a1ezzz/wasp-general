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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import io
import os

from wasp_general.network.clients.base import WBasicNetworkClientProto
from wasp_general.network.clients.base import WBasicNetworkClientListDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientChangeDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientMakeDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientCurrentDirCapability
from wasp_general.network.clients.base import WBasicNetworkClientUploadFileCapability
from wasp_general.network.clients.base import WBasicNetworkClientRemoveFileCapability


class WLocalFile(WBasicNetworkClientProto):

	def __init__(self, uri):
		WBasicNetworkClientProto.__init__(self, uri)
		self.__session_path = uri.path() if uri.path() is not None else '/'

	def session_path(self, value=None):
		if value is not None:
			self.__session_path = value
		return self.__session_path

	def _close(self):
		self.__session_path = None

	@classmethod
	def scheme(cls):
		return 'file'

	@classmethod
	def agent_capabilities(cls):
		return WLocalFileListDirCapability, \
			WLocalFileMakeDirCapability, \
			WLocalFileChangeDirCapability, \
			WLocalFileUploadFileCapability, \
			WLocalFileRemoveFileCapability


class WLocalFileChangeDirCapability(WBasicNetworkClientChangeDirCapability):

	def request(self, path, *args, exec_cmd=None, **kwargs):
		if os.path.isdir(path) is True:
			self.network_agent().session_path(path)
			return True
		return False


class WLocalFileCurrentDirCapability(WBasicNetworkClientCurrentDirCapability):

	def request(self, *args, **kwargs):
		return self.network_agent().session_path()


class WLocalFileListDirCapability(WBasicNetworkClientListDirCapability):

	def request(self, *args, **kwargs):
		return tuple(os.listdir(self.network_agent().session_path()))


class WLocalFileMakeDirCapability(WBasicNetworkClientMakeDirCapability):

	def request(self, directory_name, *args, **kwargs):
		os.mkdir(os.path.join(self.network_agent().session_path(), directory_name))
		return True


class WLocalFileUploadFileCapability(WBasicNetworkClientUploadFileCapability):

	def request(self, file_name, file_obj, *args, **kwargs):
		with open(os.path.join(self.network_agent().session_path(), file_name), mode='wb') as f:
			chunk = file_obj.read(io.DEFAULT_BUFFER_SIZE)
			while len(chunk) > 0:
				f.write(chunk)
				chunk = file_obj.read(io.DEFAULT_BUFFER_SIZE)

		return True


class WLocalFileRemoveFileCapability(WBasicNetworkClientRemoveFileCapability):

	def request(self, file_name, *args, **kwargs):
		os.unlink(os.path.join(self.network_agent().session_path(), file_name))
		return True
