# -*- coding: utf-8 -*-
# wasp_general/task.sync.py
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

from abc import abstractmethod

from wasp_general.task.base import WStoppableTask, WTaskStatus


class WSyncTask(WStoppableTask, WTaskStatus):

	def __init__(self):
		WStoppableTask.__init__(self)
		WTaskStatus.__init__(self)

	@abstractmethod
	def _start(self):
		raise NotImplementedError('This method is abstract')

	def _stop(self):
		pass

	def start(self):
		self._start()
		self._started(True)

	def stop(self):
		self._started(False)
		self._stop()
