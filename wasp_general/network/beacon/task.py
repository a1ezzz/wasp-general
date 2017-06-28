# -*- coding: utf-8 -*-
# wasp_general/network/beacon/task.py
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

from wasp_general.task.thread import WThreadTask

from wasp_general.network.beacon.beacon import WNetworkServerBeacon


class WNetworkBeaconTask(WNetworkServerBeacon, WThreadTask):
	""" Convenient way to start WNetworkBeacon server side

	see :class:`.WNetworkServerBeacon`
	"""

	def __init__(self, config=None, config_section=None, thread_name=None, messenger=None):
		""" Create new threaded task

		:param config: same as config in :meth:`.WNetworkServerBeacon.__init__` method
		:param config_section: same as config_section in :meth:`.WNetworkServerBeacon.__init__` method
		:param thread_name: same as thread_name in :meth:`.WThreadTask.__init__` method
		:param messenger: same as messenger in :meth:`.WNetworkServerBeacon.__init__` method
		"""
		WNetworkServerBeacon.__init__(self, config=config, config_section=config_section, messenger=messenger)
		WThreadTask.__init__(self, thread_name=thread_name)

	def start(self):
		WThreadTask.start(self)

	def stop(self):
		WThreadTask.stop(self)

	def thread_started(self):
		WNetworkServerBeacon.start(self)

	def thread_stopped(self):
		WNetworkServerBeacon.stop(self)
