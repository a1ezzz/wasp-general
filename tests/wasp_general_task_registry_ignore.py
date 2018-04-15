# -*- coding: utf-8 -*-

import pytest

from wasp_general.task.registry import WRegisteredTask, WTaskRegistryBase, WTaskRegistryStorage, WTaskRegistry
from wasp_general.task.base import WTask


def test_abstract_classes():
	pytest.raises(TypeError, WTaskRegistryBase)
	pytest.raises(NotImplementedError, WTaskRegistryBase.add, None, None)
	pytest.raises(NotImplementedError, WTaskRegistryBase.remove, None, None)
	pytest.raises(NotImplementedError, WTaskRegistryBase.clear, None)
	pytest.raises(NotImplementedError, WTaskRegistryBase.tasks, None, None)
	pytest.raises(NotImplementedError, WTaskRegistryBase.tasks_by_tag, None, None)
	pytest.raises(NotImplementedError, WTaskRegistryBase.tags, None)
	pytest.raises(NotImplementedError, WTaskRegistryBase.count, None)


class TestWRegisteredTask:

	def test_task(self):

		with pytest.raises(ValueError):
			class T1(metaclass=WRegisteredTask):
				pass

		class FakeR:
			pass

		with pytest.raises(TypeError):
			class T2(metaclass=WRegisteredTask):
				__registry__ = FakeR

		class R(WTaskRegistry):
			__registry_storage__ = WTaskRegistryStorage()

		assert(R.__registry_storage__.count() == 0)

		with pytest.raises(TypeError):
			class T3(metaclass=WRegisteredTask):
				__registry__ = R

		class T4(WTask, metaclass=WRegisteredTask):
			__registry__ = R

		assert(R.__registry_storage__.count() == 0)

		R.__skip_none_registry_tag__ = False

		class T4(WTask, metaclass=WRegisteredTask):
			__registry__ = R

		assert(R.__registry_storage__.count() == 1)

		class T5(WTask, metaclass=WRegisteredTask):
			__registry__ = R
			__auto_registry__ = False
		assert(R.__registry_storage__.count() == 1)


class TestWTaskRegistryStorage:

	def test(self):

		registry_storage = WTaskRegistryStorage()

		class R(WTaskRegistry):
			__registry_storage__ = WTaskRegistryStorage()

		with pytest.raises(TypeError):
			class FakeT1:
				pass
			registry_storage.add(FakeT1)

		with pytest.raises(TypeError):
			class FakeT2(WTask):
				pass
			registry_storage.add(FakeT2)

		class T1(WTask, metaclass=WRegisteredTask):
			__registry__ = R

		class T2(WTask, metaclass=WRegisteredTask):
			__registry__ = R

		assert(registry_storage.count() == 0)
		registry_storage.add(T1)
		assert(registry_storage.count() == 1)
		registry_storage.add(T1)
		assert(registry_storage.count() == 2)
		registry_storage.add(T2)
		assert(registry_storage.count() == 3)

		assert(len(list(filter(lambda x: x == T1, registry_storage.tasks_by_tag(None)))) == 2)
		assert(len(list(filter(lambda x: x == T2, registry_storage.tasks_by_tag(None)))) == 1)

		assert(len(registry_storage.tasks()) == 3)
		assert(len(registry_storage.tasks(task_cls=T2)) == 1)

		registry_storage.clear()
		assert(registry_storage.count() == 0)

		registry_storage.__multiple_tasks_per_tag__ = False
		registry_storage.add(T1)
		assert(registry_storage.count() == 1)

		with pytest.raises(RuntimeError):
			registry_storage.add(T1)

		with pytest.raises(RuntimeError):
			registry_storage.add(T2)

		class T3(WTask, metaclass=WRegisteredTask):
			__registry__ = R
			__registry_tag__ = 1

		registry_storage.add(T3)
		assert(registry_storage.count() == 2)

		assert(registry_storage.tags() == (1, None))

		assert(registry_storage.count() == 2)
		assert(registry_storage.tasks_by_tag(1) == T3)
		assert(registry_storage.tasks_by_tag(None) == T1)
		registry_storage.remove(T3)
		assert(registry_storage.count() == 1)
		assert(registry_storage.tasks_by_tag(None) == T1)
		assert(registry_storage.tasks_by_tag(1) is None)

		assert(registry_storage.tasks_by_tag(2) is None)


class TestWTaskRegistry:

	def test_registry(self):

		class R1(WTaskRegistry):
			__skip_none_registry_tag__ = False

		with pytest.raises(ValueError):
			R1.registry_storage()

		with pytest.raises(TypeError):
			class FakeRS:
				pass
			R1.__registry_storage__ = FakeRS()
			R1.registry_storage()

		R1.__registry_storage__ = WTaskRegistryStorage()
		assert(R1.registry_storage() == R1.__registry_storage__)

		class R2(WTaskRegistry):
			__registry_storage__ = WTaskRegistryStorage()

		class T(WTask, metaclass=WRegisteredTask):
			__registry__ = R2

		assert(R1.registry_storage().count() == 0)
		R1.add(T)
		assert(R1.registry_storage().count() == 1)
		R1.remove(T)
		assert (R1.registry_storage().count() == 0)

		R1.add(T)
		R1.add(T)
		assert (R1.registry_storage().count() == 2)
		R1.clear()
		assert (R1.registry_storage().count() == 0)
