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

from wasp_general.check.verify import verify_type


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


class WTaskStatus(WTask, metaclass=ABCMeta):
	""" Task with information about task state (whether it was started or stopped). State of the task must be
	defined manually.
	"""

	@verify_type(decorate_start=bool, decorate_stop=bool)
	def __init__(self, decorate_start=True, decorate_stop=True):
		""" Construct new class. You can't construct this class because of abstract methods. You must inherit
		this class and override start method. If decorate_stop is True then you need to override method
		stop also.

		:param decorate_start: if True - constructor will decorate start method (so after start method \
		called task will be marked as started)
		:param decorate_stop: if True - constructor will decorate stop method (so after stop method \
		called task will be marked as stopped). To use this flag, class must inherit WStoppableTask class
		"""
		WTask.__init__(self)
		self.__started = False

		if decorate_start is True:
			original_start = self.start

			def decorated_start():
				original_start()
				self._started(True)

			self.start = decorated_start

		if decorate_stop is True:
			if isinstance(self, WStoppableTask) is False:
				raise TypeError('To decorate stop method class must inherit WStoppableTask class')
			else:
				original_stop = self.stop

				def decorated_stop():
					original_stop()
					self._started(False)

				self.stop = decorated_stop

	@verify_type(value=bool)
	def _started(self, value):
		""" Mark this task as started or stopped

		:param value: if True - then this task marks as started, otherwise - stopped.
		:return: None
		"""
		self.__started = value

	def started(self):
		""" Get task status

		:return: True - if task is started, and False if it is stopped
		"""
		return self.__started
