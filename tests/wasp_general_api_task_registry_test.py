
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
	registry = WTaskRegistry(fallback_registry=__default_task_registry__)
	assert(registry.has('task1') is False)
	assert(registry.has('task2') is False)
	assert(__default_task_registry__.has('task1') is False)
	assert(__default_task_registry__.has('task2') is False)

	register_class('task1', registry=registry)(WTaskProto)
	register_class('task2')(WTaskProto)
	assert(registry['task1'] is WTaskProto)
	assert(registry['task2'] is WTaskProto)
	assert(__default_task_registry__.has('task1') is False)
	assert(__default_task_registry__['task2'] is WTaskProto)

	register_class('task1', registry=registry)(WTaskProto)  # no exception is raised since a class is the same
	with pytest.raises(WDuplicateAPIIdError):
		class T(WTaskProto):
			pass
		register_class('task1', registry=registry)(T)
