
import pytest

from wasp_general.api.registry import WAPIRegistry, WDuplicateAPIIdError
from wasp_general.api.task.proto import WTaskRegistryProto, WTaskProto
from wasp_general.api.task.registry import WTaskRegistry, __default_task_registry__, register_class


class TestWTaskRegistry:

	def test(self):
		registry = WTaskRegistry()
		assert(isinstance(registry, WTaskRegistryProto) is True)
		assert(isinstance(registry, WAPIRegistry) is True)

		registry.register('task1', WTaskProto)

	def test_default(self):
		assert (isinstance(__default_task_registry__, WTaskRegistry) is True)


@pytest.fixture
def default_registry_wrap(request):
	default_ids = set(__default_task_registry__.ids())

	def fin():
		registered_ids = set(__default_task_registry__.ids())
		for api_id in registered_ids.difference(default_ids):
			__default_task_registry__.unregister(api_id)

	request.addfinalizer(fin)


@pytest.mark.usefixtures('default_registry_wrap')
def test_registry_class():

	class T1(WTaskProto):
		__task_tag__ = 'task1'

	class T2(WTaskProto):
		__task_tag__ = 'task2'

	class T3(WTaskProto):
		__task_tag__ = 'task3'

	registry = WTaskRegistry(fallback_registry=__default_task_registry__)
	assert(registry.has('task1') is False)
	assert(registry.has('task2') is False)
	assert(registry.has('task3') is False)
	assert(__default_task_registry__.has('task1') is False)
	assert(__default_task_registry__.has('task2') is False)
	assert(__default_task_registry__.has('task3') is False)

	register_class(registry=registry)(T1)
	register_class(T2)
	register_class()(T3)
	assert(registry['task1'] is T1)
	assert(registry['task2'] is T2)
	assert(registry['task3'] is T3)
	assert(__default_task_registry__.has('task1') is False)
	assert(__default_task_registry__['task2'] is T2)
	assert(__default_task_registry__['task3'] is T3)

	register_class(registry=registry)(T1)  # no exception is raised since a class is the same
	with pytest.raises(WDuplicateAPIIdError):
		class T(T1):
			pass
		register_class(registry=registry)(T)

	with pytest.raises(TypeError):
		class T4(WTaskProto):

			@classmethod
			def start(cls, **kwargs):
				return

		register_class(registry=registry)(T4)
