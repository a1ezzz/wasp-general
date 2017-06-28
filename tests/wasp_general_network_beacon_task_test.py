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
		assert(task.thread() is None)
		task.start()
		assert(task.thread() is not None)
		task.stop()
		assert(task.thread() is None)
