# -*- coding: utf-8 -*-
# wasp_general/network/clients/base.py
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

from enum import Enum
from abc import abstractmethod, abstractclassmethod

from wasp_general.network.clients.proto import WNetworkClientCapabilityProto, WNetworkClientProto
from wasp_general.verify import verify_type
from wasp_general.uri import WURI


class WCommonNetworkClientCapability(Enum):
	current_dir = 'current_dir'
	change_dir = 'change_dir'
	list_dir = 'list_dir'
	make_dir = 'make_dir'
	upload_file = 'upload_file'
	remove_file = 'remove_file'


# noinspection PyAbstractClass
class WBasicNetworkClientCapability(WNetworkClientCapabilityProto):

	def __init__(self, network_agent):
		WNetworkClientCapabilityProto.__init__(self)
		self.__network_agent = network_agent

	def network_agent(self):
		return self.__network_agent

	def capability_id(self):
		return self.common_capability().value

	@abstractclassmethod
	def common_capability(cls):
		raise NotImplementedError('This method is abstract')

	@classmethod
	def create_capability(cls, network_agent):
		return cls(network_agent)


# noinspection PyAbstractClass
class WBasicNetworkClientProto(WNetworkClientProto):

	def __init__(self, uri):
		self.__uri = uri
		self.__capabilities = \
			{x.common_capability(): x.create_capability(self) for x in self.agent_capabilities()}
		self.__is_closed = False

	def uri(self):
		return self.__uri

	def capabilities(self):
		return self.__capabilities.values()

	def request(self, capability_id, *args, **kwargs):
		if self.is_closed() is True:
			raise RuntimeError('Operation requested on this closed client')

		if self.is_capable(capability_id) is True:
			common_capability = WCommonNetworkClientCapability(capability_id)
			for capability in self.capabilities():
				if capability.common_capability() == common_capability:
					return capability.request(*args, **kwargs)
		raise RuntimeError('Unable to execute unsupported capability: %s' % str(capability_id))

	def is_closed(self):
		return self.__is_closed

	def close(self):
		if self.__is_closed is False:
			self._close()
		self.__is_closed = True

	@classmethod
	def is_capable(cls, capability_id):
		common_capability = WCommonNetworkClientCapability(capability_id)
		for agent_cap in cls.agent_capabilities():
			if agent_cap.common_capability() == common_capability:
				return True
		return False

	@classmethod
	@verify_type(uri=WURI)
	def open(cls, uri):
		if uri.scheme() != cls.scheme():
			raise RuntimeError('Unsupported scheme spotted!')

		return cls(uri)

	@abstractmethod
	def _close(self):
		raise NotImplementedError('This method is abstract')

	@abstractclassmethod
	def agent_capabilities(cls):
		raise NotImplementedError('This method is abstract')


# noinspection PyAbstractClass
class WBasicNetworkClientChangeDirCapability(WBasicNetworkClientCapability):

	@classmethod
	def common_capability(cls):
		return WCommonNetworkClientCapability.change_dir


# noinspection PyAbstractClass
class WBasicNetworkClientListDirCapability(WBasicNetworkClientCapability):

	@classmethod
	def common_capability(cls):
		return WCommonNetworkClientCapability.list_dir


# noinspection PyAbstractClass
class WBasicNetworkClientMakeDirCapability(WBasicNetworkClientCapability):

	@classmethod
	def common_capability(cls):
		return WCommonNetworkClientCapability.make_dir


# noinspection PyAbstractClass
class WBasicNetworkClientCurrentDirCapability(WBasicNetworkClientCapability):

	@classmethod
	def common_capability(cls):
		return WCommonNetworkClientCapability.current_dir


# noinspection PyAbstractClass
class WBasicNetworkClientUploadFileCapability(WBasicNetworkClientCapability):

	@classmethod
	def common_capability(cls):
		return WCommonNetworkClientCapability.upload_file


# noinspection PyAbstractClass
class WBasicNetworkClientRemoveFileCapability(WBasicNetworkClientCapability):

	@classmethod
	def common_capability(cls):
		return WCommonNetworkClientCapability.remove_file
