# -*- coding: utf-8 -*-

import pytest

from wasp_general.task.thread import WThreadTask

from wasp_general.network.beacon.beacon import WNetworkServerBeacon

from wasp_general.network.beacon.task import WNetworkBeaconTask


class TestNetworkBeaconTask:

	def test_task(self):
		task = WNetworkBeaconTask()
		assert(isinstance(task, WThreadTask) is True)
		assert(isinstance(task, WNetworkServerBeacon) is True)
		assert(task.started() is False)
		task.start()
		assert(task.started() is True)
		task.stop()
		assert(task.started() is False)
