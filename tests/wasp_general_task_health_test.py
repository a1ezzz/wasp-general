# -*- coding: utf-8 -*-

import pytest

'''
from wasp_general.task.health import WTaskHealthSensor, WMeasurableTaskHealthSensor, WTaskHealth


def test_abstract_classes():
	pytest.raises(TypeError, WTaskHealthSensor)
	pytest.raises(NotImplementedError, WTaskHealthSensor.healthy, None)

	pytest.raises(TypeError, WMeasurableTaskHealthSensor)
	pytest.raises(NotImplementedError, WMeasurableTaskHealthSensor.value, None)
	pytest.raises(NotImplementedError, WMeasurableTaskHealthSensor.measurement_unit, None)

	pytest.raises(TypeError, WTaskHealth)


class TestWTaskHealthSensor:

	def test_sensor(self):

		class S(WTaskHealthSensor):
			def healthy(self):
				return True

		s1 = S('recommended hdd sensor', WTaskHealthSensor.WTaskSensorSeverity.recommended)
		assert(s1.name() == 'recommended hdd sensor')
		assert(s1.description() is None)
		assert(s1.severity() == WTaskHealthSensor.WTaskSensorSeverity.recommended)

		s2 = S('hdd critical sensor', WTaskHealthSensor.WTaskSensorSeverity.critical, description='bla-bla')
		assert (s2.name() == 'hdd critical sensor')
		assert (s2.description() == 'bla-bla')
		assert (s2.severity() == WTaskHealthSensor.WTaskSensorSeverity.critical)


class TestWMeasurableTaskHealthSensor:

	def test_sensor(self):

		class S(WMeasurableTaskHealthSensor):
			def value(self):
				return 1

		s1 = S('s1 sensor', WTaskHealthSensor.WTaskSensorSeverity.recommended, 10)
		assert(s1.name() == 's1 sensor')
		assert(s1.description() is None)
		assert(s1.severity() == WTaskHealthSensor.WTaskSensorSeverity.recommended)
		assert(s1.error_value() == 10)

		assert(s1.healthy() is True)
		s1.value = lambda: 11
		assert(s1.healthy() is False)

		s2 = S('s2 sensor', WTaskHealthSensor.WTaskSensorSeverity.recommended, 10, comparator=lambda x, y: x > y)
		assert(s2.healthy() is False)
		s2.value = lambda: 11
		assert(s2.healthy() is True)


class TestWTaskHealth:

	def test_healthy(self):

		class H(WTaskHealth):
			def start(self):
				pass

		h1 = H(decorate_stop=False)
		assert(h1.sensors() == [])
		assert(h1.healthy() is None)

		pytest.raises(TypeError, H, 1, decorate_stop=False)

		class S(WTaskHealthSensor):
			def healthy(self):
				return True

		s1 = S('sensor1', WTaskHealthSensor.WTaskSensorSeverity.recommended)
		s2 = S('sensor2', WTaskHealthSensor.WTaskSensorSeverity.important)
		h2 = H(s1, s2, decorate_stop=False)
		assert(h2.sensors() == ['sensor1', 'sensor2'] or h2.sensors() == ['sensor2', 'sensor1'])
		assert(h2.sensor('sensor1') == s1)
		assert(h2.sensor('sensor2') == s2)
		assert(h2.healthy() is None)

		s1.healthy = lambda: False
		assert(h2.healthy() == WTaskHealthSensor.WTaskSensorSeverity.recommended)
		s2.healthy = lambda: False
		assert(h2.healthy() == WTaskHealthSensor.WTaskSensorSeverity.important)

		s1.severity = lambda: WTaskHealthSensor.WTaskSensorSeverity.critical
		assert(h2.healthy() == WTaskHealthSensor.WTaskSensorSeverity.critical)
'''
