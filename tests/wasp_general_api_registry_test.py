
import pytest

from wasp_general.api.registry import WNoSuchAPIIdError, WDuplicateAPIIdError, WAPIRegistryProto, WAPIRegistry
from wasp_general.api.registry import register_api


def test_exceptions():
	assert(issubclass(WNoSuchAPIIdError, Exception) is True)
	assert(issubclass(WDuplicateAPIIdError, Exception) is True)


def test_abstract():
	pytest.raises(TypeError, WAPIRegistryProto)
	pytest.raises(NotImplementedError, WAPIRegistryProto.register, None, None, None)
	pytest.raises(NotImplementedError, WAPIRegistryProto.get, None, None)


class TestWAPIRegistry:

	def test(self):
		registry = WAPIRegistry()
		pytest.raises(WNoSuchAPIIdError, registry.get, 'foo')
		pytest.raises(WNoSuchAPIIdError, registry.get, 'bar')

		registry.register('foo', 1)
		assert(registry.get('foo') == 1)
		pytest.raises(WNoSuchAPIIdError, registry.get, 'bar')

		pytest.raises(WDuplicateAPIIdError, registry.register, 'foo', 1)

		registry.register('bar', 1)
		assert(registry['foo'] == 1)
		assert(registry['bar'] == 1)

		secondary_registry = WAPIRegistry(fallback_registry=registry)
		assert(secondary_registry['foo'] == 1)
		assert(secondary_registry['bar'] == 1)
		pytest.raises(WNoSuchAPIIdError, secondary_registry.get, 'zzz')
		pytest.raises(WNoSuchAPIIdError, secondary_registry.get, 'xxx')

		registry.register('zzz', 1)
		assert(secondary_registry['foo'] == 1)
		assert(secondary_registry['bar'] == 1)
		assert(secondary_registry['zzz'] == 1)
		pytest.raises(WNoSuchAPIIdError, secondary_registry.get, 'xxx')

		secondary_registry.register('xxx', 1)
		assert(secondary_registry['foo'] == 1)
		assert(secondary_registry['bar'] == 1)
		assert(secondary_registry['zzz'] == 1)
		assert(secondary_registry['xxx'] == 1)
		pytest.raises(WNoSuchAPIIdError, registry.get, 'xxx')


def test_register_api():

	def foo(a, b):
		return a + b

	def bar(a, b):
		return a - b

	registry = WAPIRegistry()

	decorated_foo = register_api(registry)(foo)
	decorated_bar = register_api(registry, api_id='zzz')(bar)

	assert(decorated_foo(3, 4) == 7)
	assert(decorated_bar(3, 4) == -1)

	assert(registry['test_register_api.<locals>.foo'](5, 2) == 7)
	assert(registry['zzz'](5, 2) == 3)

	pytest.raises(WNoSuchAPIIdError, registry.get, 'bar')
