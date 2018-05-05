# -*- coding: utf-8 -*-
# wasp_general/network/service_v2/proto.py
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
from socket import socket
from threading import Event

from wasp_general.verify import verify_type


class WServiceWorkerProto(metaclass=ABCMeta):
	""" This class is used for interaction with a client connection
	"""

	@abstractmethod
	@verify_type(socket_obj=socket)
	def process(self, socket_obj):
		""" Process new client connection

		:param socket_obj: client connection
		:return:
		"""
		raise NotImplementedError('This method is abstract')


class WServiceFactoryProto(metaclass=ABCMeta):
	""" This class is used for managing service workers (:class:`.WServiceWorkerProto` instances)
	"""

	def __init__(self):
		""" Create new factory
		"""
		self.__stop_event = None

	@verify_type(stop_event=Event)
	def configure(self, stop_event, **kwargs):
		""" Configure this factory

		:param stop_event: save this stop event. This event will be set when service is about to stop
		:param kwargs: extra arguments

		:return: None
		"""
		self.__stop_event = stop_event

	def stop_event(self):
		""" Return stop event

		:return: Event
		"""
		return self.__stop_event

	@abstractmethod
	def worker(self, timeout=None):
		""" Return worker for the next client. This method may block a current thread till a worker is
		available. If a timeout is specified, then this method may block the current thread during
		this period of time only.

		:param timeout: if specified - period of time the current thread may await till a worker is available

		:return: WServiceWorkerProto or None (if no worker is available like in case of timeout)
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def terminate_workers(self):
		""" Stop all the running workers

		:return: None
		"""
		raise NotImplementedError('This method is abstract')
