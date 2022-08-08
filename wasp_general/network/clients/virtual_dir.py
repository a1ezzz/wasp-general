# -*- coding: utf-8 -*-
# wasp_general/network/clients/virtual_dir.py
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

import re

from wasp_general.verify import verify_type, verify_value
from wasp_general.uri import WURI
from wasp_general.network.clients.proto import WNetworkClientProto


# noinspection PyAbstractClass
class WVirtualDirectoryClient(WNetworkClientProto):
	""" This class may be used as a basic class for network clients, that does not keep connection between
	capabilities calls. That type of clients may create connection for each request. In this case it is important
	to save current session directory, because it influences on calls behaviour. This class helps to save and
	to change current session directory during such calls.
	"""

	@verify_type(start_path=(str, None))
	@verify_type('paranoid', uri=WURI)
	@verify_value(start_path=lambda x: x is None or len(x) > 0)
	def __init__(self, uri, start_path=None):
		""" Create new client

		:param uri: same as uri in :meth:`.WNetworkClientProto.__init__`
		:param start_path: this is a start point that prepends before a session directory for getting a \
		full path. By default, start point is a same as a directory separator)
		"""
		WNetworkClientProto.__init__(self, uri)
		self.__session_path = self.directory_sep()
		self.__normalize_re = re.compile('\\%s\\%s+' % (self.directory_sep(), self.directory_sep()))
		self.__start_path = self.normalize_path(start_path) if start_path is not None else self.directory_sep()

	def start_path(self):
		""" Return a start path for this client

		:return: str
		"""
		return self.__start_path

	@verify_type(path=str)
	@verify_value(path=lambda x: len(x) > 0)
	def normalize_path(self, path):
		""" Normalize the given path, like removing redundant directory separators

		:param path: path to normalize

		:return: str
		"""
		return self.__normalize_re.sub(self.directory_sep(), path)

	@verify_type(path=str)
	@verify_value(path=lambda x: len(x) > 0)
	def join_path(self, *path):
		""" Unite entries to generate a single path

		:param path: path items to unite

		:return: str
		"""
		path = self.directory_sep().join(path)
		return self.normalize_path(path)

	@verify_type(path=(str, None))
	@verify_value(path=lambda x: x is None or len(x) > 0)
	def session_path(self, path=None):
		""" Set and/or get current session path

		:param path: if defined, then set this value as a current session directory. If this value starts \
		with a directory separator, then it is treated as an absolute path. In this case this value replaces
		a current one, otherwise this value is appended to a current one.

		:return: str
		"""
		if path is not None:
			if path.startswith(self.directory_sep()) is True:
				self.__session_path = self.normalize_path(path)
			else:
				self.__session_path = self.join_path(self.__session_path, path)
		return self.__session_path

	def full_path(self):
		""" Return a full path to a current session directory. A result is made by joining a start path with
		current session directory

		:return: str
		"""
		return self.normalize_path(self.directory_sep().join((self.start_path(), self.session_path())))
