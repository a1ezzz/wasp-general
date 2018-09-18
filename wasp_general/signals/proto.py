# -*- coding: utf-8 -*-
# wasp_general/signals/proto.py.py
#
# Copyright (C) 2018 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
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

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type


class WSignalSourceProto(metaclass=ABCMeta):
	""" An entry class for an object that sends signals
	"""

	@abstractmethod
	@verify_type(signal_name=str)
	def send_signal(self, signal_name):
		""" Send a signal with this object as a signal source

		:param signal_name: name of a signal to send
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def signals(self):
		""" Return signal names that may be sent

		:return: list of str
		"""
		raise NotImplementedError('This method is abstract')


class WSignalReceiverProto(metaclass=ABCMeta):
	""" A class that may receive signals
	"""

	@abstractmethod
	@verify_type(signal_name=str, signal_source=WSignalSourceProto)
	def receive_signal(self, signal_name, signal_source):
		""" A callback that will be called on a signal sending

		:param signal_name: name of a signal that was send
		:param signal_source: origin of a signal
		:return: None
		"""
		raise NotImplementedError('This method is abstract')


class WSignalSenderProto(WSignalSourceProto):
	""" Class of an object that is able to link this sender with a receiver
	"""

	@abstractmethod
	@verify_type(signal_name=str, receiver=WSignalReceiverProto)
	def connect(self, signal_name, receiver):
		""" Link the given receiver with a specific signal and this sender

		:param signal_name: name of a signal that will be linked
		:param receiver: a "callback" that will be called when a signal sends
		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(signal_name=str, receiver=WSignalReceiverProto)
	def disconnect(self, signal_name, receiver):
		""" Unlink the given receiver from a specific signal and this sender

		:param signal_name: name of a signal that should be unlinked
		:param receiver: a "callback" that should be unlinked
		:return: None
		"""
		raise NotImplementedError('This method is abstract')
