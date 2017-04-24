# -*- coding: utf-8 -*-
# wasp_general/network/messenger/auth.py
#
# Copyright (C) 2016 the wasp-general authors and contributors
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
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value

'''
from wasp_general.network.messenger.onion import WMessengerOnionBase, WMessengerOnionLayer, WMessageModifier
from wasp_general.network.messenger.onion import WMessengerOnionSessionBase


class WMessengerAuth(metaclass=ABCMeta):

	class Action(Enum):
		permit = 0
		forbid = 1

	@verify_type(
		message=(bytes, str, None), onion=WMessengerOnionBase,
		session=WMessengerOnionSessionBase, current_layer_index=int
	)
	@verify_value(current_layer_index=lambda x: x >= -1)
	def pack(self, message, onion, session, current_layer_index):
		raise NotImplementedError('This method is abstract')

	@verify_type(
		message=(bytes, str, None), onion=WMessengerOnionBase,
		session=WMessengerOnionSessionBase, current_layer_index=int
	)
	@verify_value(current_layer_index=lambda x: x >= -1)
	def unpack(self, message, onion, session, current_layer_index):
		raise NotImplementedError('This method is abstract')


class WMessengerAuthLayer(WMessengerOnionLayer):

	__layer_name__ = ""

	@verify_type(auth=WMessengerAuth)
	def __init__(self, auth):
		WMessengerOnionLayer.__init__(self, WMessengerAuthLayer.__layer_name__)
		self.__auth = auth

	@verify_type(
		message=(bytes, str, None), onion=WMessengerOnionBase,
		session=WMessengerOnionSessionBase, current_layer_index=int
	)
	@verify_value(current_layer_index=lambda x: x >= -1)
	def pack(self, message, onion, session, current_layer_index):
		pass

	@verify_type(
		message=(bytes, str, None), onion=WMessengerOnionBase,
		session=WMessengerOnionSessionBase, current_layer_index=int
	)
	@verify_value(current_layer_index=lambda x: x >= -1)
	def unpack(self, message, onion, session, current_layer_index):
		pass
'''
