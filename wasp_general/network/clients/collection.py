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

from wasp_general.verify import verify_subclass

from wasp_general.network.clients.proto import WNetworkClientProto
from wasp_general.network.clients.ftp import WFTPClient
from wasp_general.network.clients.file import WLocalFile
from wasp_general.network.clients.webdav import WWebDavsClient
from wasp_general.uri import WSchemeCollection


class WNetworkClientCollectionProto(WSchemeCollection):

	@verify_subclass(scheme_handler_cls=WNetworkClientProto)
	def add(self, scheme_handler_cls):
		return WSchemeCollection.add(self, scheme_handler_cls)


__default_client_collection__ = WNetworkClientCollectionProto(
	WLocalFile,
	WFTPClient,
	WWebDavsClient,
	default_handler_cls=WLocalFile
)
