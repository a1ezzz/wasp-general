# -*- coding: utf-8 -*-
# wasp_general/task/base.py
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

from abc import ABCMeta, abstractmethod


class WTask(metaclass=ABCMeta):

	@abstractmethod
	def start(self):
		raise NotImplementedError('This method is abstract')


class WStoppableTask(WTask):

	@abstractmethod
	def stop(self):
		raise NotImplementedError('This method is abstract')


class WTerminatableTask(WTask):

	@abstractmethod
	def terminate(self):
		raise NotImplementedError('This method is abstract')


class WTaskStatus(WTask):

	def __init__(self):
		WTask.__init__(self)
		self.__started = False

	def _started(self, value):
		self.__started = value

	def started(self):
		return self.__started


class WTaskHealth(WTaskStatus):

	@abstractmethod
	def sensor(self, sensor_name):
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	def healthy(self):
		raise NotImplementedError('This method is abstract')
