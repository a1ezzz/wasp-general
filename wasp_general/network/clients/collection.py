# -*- coding: utf-8 -*-
# wasp_general/network/clients/collection.py
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

from wasp_general.network.clients.ftp import WFTPClient
from wasp_general.network.clients.file import WLocalFile
from wasp_general.uri import WURI


class WNetworkClientCollectionProto:

	def __init__(self, *network_client_cls, default_scheme=None):
		self.__client_cls = []
		self.__default_scheme = default_scheme
		for client_cls in network_client_cls:
			self.add(client_cls)

	def default_scheme(self):
		return self.__default_scheme

	def add(self, network_client_cls):
		self.__client_cls.append(network_client_cls)

	def client_cls(self):
		return tuple(self.__client_cls)

	def open(self, uri):
		if uri.scheme() is None:
			uri.component(WURI.Component.scheme, self.default_scheme())

		for client_cls in self.client_cls():
			if client_cls.scheme() == uri.scheme():
				return client_cls.open(uri)


__default_client_collection__ = WNetworkClientCollectionProto(
	WLocalFile,
	WFTPClient,
	default_scheme=WLocalFile.scheme()
)
