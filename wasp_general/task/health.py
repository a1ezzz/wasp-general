# -*- coding: utf-8 -*-
# wasp_general/task/health.py
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

# TODO: this idea and implementation require to be more useful. Till that this module should be treated as deprecated

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod
from enum import Enum

from wasp_general.verify import verify_type, verify_value


class WTaskHealthSensor(metaclass=ABCMeta):
	""" Represent single sensor
	"""

	class WTaskSensorSeverity(Enum):
		""" Sensor severity
		"""
		recommended = 0
		important = 1
		critical = 2

	@verify_type(name=str, severity=WTaskSensorSeverity, description=(str, None))
	def __init__(self, name, severity, description=None):
		""" Construct new sensor

		:param name: sensor name
		:param severity: sensor severity
		:param description: sensor description
		"""
		self.__name = name
		self.__severity = severity
		self.__description = description

	def name(self):
		""" Return sensor name

		:return: string
		"""
		return self.__name

	def description(self):
		""" Return sensor description

		:return: string (or None if there is no description)
		"""
		return self.__description

	def severity(self):
		""" Return sensor severity

		:return: WTaskHealthSensor.WTaskSensorSeverity
		"""
		return self.__severity

	@abstractmethod
	def healthy(self):
		""" Return True if sensor is OK, else - False

		:return: bool
		"""
		raise NotImplementedError("This method is abstract")


class WMeasurableTaskHealthSensor(WTaskHealthSensor, metaclass=ABCMeta):
	""" Represent measurable sensor
	"""

	@verify_value(comparator=lambda x: x is None or callable(x))
	def __init__(self, name, severity, error_value, description=None, comparator=None):
		""" Construct new measurable sensor.

		:param name: sensor name (as in :meth:`.WTaskHealthSensor.__init__`)
		:param severity: sensor severity (as in :meth:`.WTaskHealthSensor.__init__`)
		:param error_value: sensor limit
		:param description: sensor description (as in :meth:`.WTaskHealthSensor.__init__`)
		:param comparator: callable, that compares sensor value with error_value (if result is True, then \
		sensor threats as healthy, if False - unhealthy). If comparator is None, then default function \
		is used (function compares if sensor value are less then error_value)
		"""
		WTaskHealthSensor.__init__(self, name, severity, description=description)
		self._error_value = error_value
		self._comparator = comparator if comparator is not None else lambda x, y: x < y

	def healthy(self):
		""" Return True if sensor is OK, else - False

		:return: bool
		"""
		return self._comparator(self.value(), self._error_value)

	def error_value(self):
		""" Return error_value

		:return: (any type)
		"""
		return self._error_value

	@abstractmethod
	def value(self):
		""" Return current value sensor

		:return: (any type)
		"""
		raise NotImplementedError("Value wasn't defined")

	def measurement_unit(self):
		""" Return measurement unit of sensor

		:return: string
		"""
		raise NotImplementedError("Measurement wasn't defined")


class WTaskHealth(metaclass=ABCMeta):
	""" This class presents API for task health probe. It can be used to probe if everything that task needs are
	ready or available (for example: disk space, file existing, socket is opened and so on).

	This is optional for the most tasks.

	"""

	@verify_type(sensors=WTaskHealthSensor)
	def __init__(self, *sensors, decorate_start=True, decorate_stop=True):

		self._sensors = {}
		for sensor in sensors:
			# noinspection PyUnresolvedReferences
			self._sensors[sensor.name()] = sensor

	def sensor(self, sensor_name):
		""" Return sensor by its name

		:param sensor_name: name of sensor
		:return: WMeasurableTaskHealthSensor instance
		"""
		return self._sensors[sensor_name]

	def sensors(self):
		""" Return list of sensor names

		:return: list of strings
		"""
		return list(self._sensors.keys())

	def healthy(self):
		""" Return task health. If None - task is healthy, otherwise - maximum severity of sensors

		:return: None or WTaskHealthSensor.WTaskSensorSeverity
		"""
		state = None
		for sensor in self._sensors.values():
			if sensor.healthy() is False:
				if state is None or sensor.severity().value > state.value:
					state = sensor.severity()
				if state == WTaskHealthSensor.WTaskSensorSeverity.critical:
					break

		return state
