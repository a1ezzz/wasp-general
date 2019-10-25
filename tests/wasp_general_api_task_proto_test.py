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
	pytest.raises(TypeError, WTaskProto)
	pytest.raises(NotImplementedError, WTaskProto.start)

	pytest.raises(TypeError, WTaskRegistryProto)
	pytest.raises(NotImplementedError, WTaskRegistryProto.register, None, 'task_id', WTaskProto)

	pytest.raises(TypeError, WTaskLauncherProto)
	pytest.raises(NotImplementedError, WTaskLauncherProto.started_tasks, None)
	pytest.raises(NotImplementedError, WTaskLauncherProto.registry, None)
	pytest.raises(
		NotImplementedError, WTaskLauncherProto.start_task, None, 'foo'
	)
	pytest.raises(NotImplementedError, WTaskLauncherProto.stop_task, None, 'foo')
	pytest.raises(NotImplementedError, WTaskLauncherProto.stop_dependent_tasks, None, 'foo')
	pytest.raises(NotImplementedError, WTaskLauncherProto.all_stop, None)


class TestWTaskProto:

	class Task(WTaskProto):

		@classmethod
		def start(cls, *args, **kwargs):
			return TestWTaskProto.Task()

	def test(self):
		assert(WTaskProto.requirements() is None)
		assert(isinstance(WTaskProto.stop, WCapabilityDescriptor) is True)
		assert(isinstance(WTaskProto.terminate, WCapabilityDescriptor) is True)

		task = TestWTaskProto.Task()
		pytest.raises(NotImplementedError, task.stop)
		pytest.raises(NotImplementedError, task.terminate)
