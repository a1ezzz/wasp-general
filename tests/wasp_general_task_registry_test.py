# -*- coding: utf-8 -*-

from wasp_general.task.sync import WSyncTask
from wasp_general.task.registry import WTaskRegistry, WRegisteredTask, WTaskRegistryStorage


class TestSnippet:

	def test_a(self):

		assert(WTaskRegistry.__registry_storage__ is None)

		class TempTaskRegistry(WTaskRegistry):
			__registry_storage__ = WTaskRegistryStorage()

		assert(TempTaskRegistry.__registry_storage__.count() == 0)

		class TaskA(WSyncTask, metaclass=WRegisteredTask):
			__registry__ = TempTaskRegistry

			def _start(self):
				pass

		assert(WTaskRegistry.__registry_storage__ is None)
		assert(TempTaskRegistry.__registry_storage__.count() == 1)
		assert(TempTaskRegistry.__registry_storage__.tasks(None)[0] == TaskA)
