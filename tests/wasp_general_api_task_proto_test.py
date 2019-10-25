# -*- coding: utf-8 -*-

import pytest

from wasp_general.api.capability import WCapabilityDescriptor
from wasp_general.api.task.proto import WNoSuchTask, WRequirementsLoop, WDependenciesLoop
from wasp_general.api.task.proto import WTaskProto, WTaskRegistryProto, WTaskLauncherProto


def test_exceptions():
	assert(issubclass(WNoSuchTask, Exception) is True)
	assert(issubclass(WRequirementsLoop, Exception) is True)
	assert(issubclass(WDependenciesLoop, Exception) is True)


def test_abstract_classes():

	class Registry(WTaskRegistryProto):

		def get(self, api_id):
			pass

		def has(self, api_id):
			pass

		def register(self, api_id, api_descriptor):
			pass

		def unregister(self, api_id):
			pass

		def ids(self):
			pass

	pytest.raises(TypeError, WTaskProto)
	pytest.raises(NotImplementedError, WTaskProto.start, None)

	pytest.raises(TypeError, WTaskRegistryProto)
	pytest.raises(NotImplementedError, WTaskRegistryProto.register, None, 'task_id', WTaskProto)

	pytest.raises(TypeError, WTaskLauncherProto)
	pytest.raises(NotImplementedError, WTaskLauncherProto.started_tasks, None)
	pytest.raises(
		NotImplementedError, WTaskLauncherProto.start_task, None, Registry(), 'foo'
	)
	pytest.raises(NotImplementedError, WTaskLauncherProto.stop_task, None, 'foo')
	pytest.raises(NotImplementedError, WTaskLauncherProto.all_stop, None)


class TestWTaskProto:

	def test(self):
		assert(WTaskProto.requirements() is None)
		assert(isinstance(WTaskProto.stop, WCapabilityDescriptor) is True)
		assert(isinstance(WTaskProto.terminate, WCapabilityDescriptor) is True)

		class Task(WTaskProto):
			def start(cls, *args, **kwargs):
				pass

		task = Task()
		pytest.raises(NotImplementedError, task.stop)
		pytest.raises(NotImplementedError, task.terminate)
