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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type


class WTask(metaclass=ABCMeta):
	""" Basic task prototype. Must implement the only thing - to start
	"""

	@abstractmethod
	def start(self):
		""" Start this task

		:return: None
		"""
		raise NotImplementedError('This method is abstract')


class WStoppableTask(WTask):
	""" Task that can be stopped (graceful shutdown)
	"""

	@abstractmethod
	def stop(self):
		""" Stop this task (graceful shutdown)

		:return: None
		"""
		raise NotImplementedError('This method is abstract')


class WTerminatableTask(WStoppableTask):
	""" Task that can be terminated (rough shutdown)
	"""

	@abstractmethod
	def terminate(self):
		""" Terminate this task (rough shutdown)

		:return: None
		"""
		raise NotImplementedError('This method is abstract')


class WSyncTask(WStoppableTask, metaclass=ABCMeta):
	""" This class is some kind of declaration, that the following task is executed in foreground.
	"""

	def __init__(self):
		WStoppableTask.__init__(self)

	def stop(self):
		""" Stop this task. This implementation does nothing.

		:return: None
		"""
		pass
