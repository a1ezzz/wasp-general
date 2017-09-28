# -*- coding: utf-8 -*-

import pytest
from datetime import datetime

from wasp_general.task.dependency import WDependentTask, WTaskDependencyRegistryStorage, WTaskDependencyRegistry
from wasp_general.task.registry import WRegisteredTask
from wasp_general.task.base import WTask, WStoppableTask


class TestWDependentTask:

	def test_task(self):

		with pytest.raises(ValueError):
			class T1(metaclass=WDependentTask):
				pass

		with pytest.raises(TypeError):

			class FakeR:
				pass

			class T2(metaclass=WDependentTask):
				__registry__ = FakeR

		class R(WTaskDependencyRegistry):
			__registry_storage__ = WTaskDependencyRegistryStorage()
			last_task_result = None

		with pytest.raises(ValueError):
			class R2(WTaskDependencyRegistry):
				__registry_storage__ = WTaskDependencyRegistryStorage()
				__skip_none_registry_tag__ = False

			class T3(metaclass=WDependentTask):
				__registry__ = R2

		with pytest.raises(TypeError):
			class T4(metaclass=WDependentTask):
				__registry__ = R
				__registry_tag__ = 1

		class T5(WTask, metaclass=WDependentTask):
			__registry__ = R
			__registry_tag__ = 'task.tag'

			def start(self):
				R.last_task_result = 'T5 call'

		assert(R.__registry_storage__.count() == 1)
		assert(R.last_task_result is None)
		assert(isinstance(T5.start_dependent_task(), T5) is True)
		assert(R.last_task_result == 'T5 call')


class TestWTaskDependencyRegistryStorage:

	def test_task(self):

		assert(WTaskDependencyRegistryStorage.__multiple_tasks_per_tag__ is False)

		registry_storage = WTaskDependencyRegistryStorage()

		class R(WTaskDependencyRegistry):
			__registry_storage__ = WTaskDependencyRegistryStorage()

		with pytest.raises(TypeError):
			class T1(WTask, metaclass=WRegisteredTask):
				__registry__ = R
				__registry_tag__ = 'task1'

		class T2(WTask, metaclass=WDependentTask):
			__registry__ = R
			__registry_tag__ = 'task2'

			last_call_result = None

			def start(self):
				T2.last_call_result = datetime.now()

		assert(registry_storage.count() == 0)
		registry_storage.add(T2)
		assert (registry_storage.count() == 1)

		class T3(WStoppableTask, metaclass=WDependentTask):
			__registry__ = R
			__registry_tag__ = 'task3'

			def start(self):
				pass

			def stop(self):
				pass

		class T4(WStoppableTask, metaclass=WDependentTask):
			__registry__ = R
			__registry_tag__ = 'task4'
			__dependency__ = ['task3']

			def start(self):
				pass

			def stop(self):
				pass

		class T5(WStoppableTask, metaclass=WDependentTask):
			__registry__ = R
			__registry_tag__ = 'task5'
			__dependency__ = ['task3', 'task4']

			def start(self):
				pass

			def stop(self):
				pass

		class T6(WStoppableTask, metaclass=WDependentTask):
			__registry__ = R
			__registry_tag__ = 'task6'
			__dependency__ = ['task3', 'unknown_task']

			def start(self):
				pass

			def stop(self):
				pass

		class T7(WStoppableTask, metaclass=WDependentTask):
			__registry__ = R
			__registry_tag__ = 'task7'
			__dependency__ = []

			def start(self):
				pass

			def stop(self):
				pass

		class T8(WStoppableTask, metaclass=WDependentTask):
			__registry__ = R
			__registry_tag__ = 'task8'
			__dependency__ = ['task5', 'task7']

			def start(self):
				pass

			def stop(self):
				pass

		registry_storage.add(T3)
		registry_storage.add(T4)
		registry_storage.add(T5)
		registry_storage.add(T6)
		registry_storage.add(T7)
		registry_storage.add(T8)
		assert(registry_storage.count() == 7)

		registry_storage.dependency_check(T2)
		registry_storage.dependency_check(T3)
		registry_storage.dependency_check(T4)
		registry_storage.dependency_check(T5)
		pytest.raises(RuntimeError, registry_storage.dependency_check, T6)
		registry_storage.dependency_check(T6, skip_unresolved=True)

		T5.__dependency__ = ['task4']
		T3.__dependency__ = ['task5']

		pytest.raises(RuntimeError, registry_storage.dependency_check, T3)
		pytest.raises(RuntimeError, registry_storage.dependency_check, T4)
		pytest.raises(RuntimeError, registry_storage.dependency_check, T5)

		T5.__dependency__ = ['task3', 'task4']
		T3.__dependency__ = []

		pytest.raises(RuntimeError, registry_storage.start_task, 'unknown tag')

		assert(registry_storage.started_tasks(task_registry_id='task2') is None)
		registry_storage.start_task('task2')
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task2'), T2) is True)

		last_result = T2.last_call_result
		registry_storage.start_task('task2')
		assert(last_result == T2.last_call_result)

		assert(registry_storage.started_tasks(task_registry_id='task3') is None)
		assert(registry_storage.started_tasks(task_registry_id='task4') is None)
		registry_storage.start_task('task4')
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task3'), T3) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task4'), T4) is True)

		assert(len(registry_storage.started_tasks()) == 3)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task3', task_cls=T3), T3) is True)
		assert(registry_storage.started_tasks(task_registry_id='task3', task_cls=T4) is None)
		assert(isinstance(registry_storage.started_tasks(task_cls=T3)[0], T3) is True)

		assert(registry_storage.started_tasks(task_registry_id='task6') is None)
		pytest.raises(RuntimeError, registry_storage.start_task, 'task6')
		registry_storage.start_task('task6', skip_unresolved=True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task6'), T6) is True)

		registry_storage.stop_task('unknown tag')
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task2'), T2) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task3'), T3) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task4'), T4) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task6'), T6) is True)

		registry_storage.stop_task('task3')
		assert(registry_storage.started_tasks(task_registry_id='task3') is None)
		assert(registry_storage.started_tasks(task_registry_id='task4') is None)
		assert(registry_storage.started_tasks(task_registry_id='task6') is None)

		T3.__dependency__ = ['unknown task']
		pytest.raises(RuntimeError, registry_storage.start_task, 'task5')
		T3.__dependency__ = []

		assert(registry_storage.started_tasks(task_registry_id='task3') is None)
		assert(registry_storage.started_tasks(task_registry_id='task4') is None)
		assert(registry_storage.started_tasks(task_registry_id='task5') is None)
		registry_storage.start_task('task5')
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task3'), T3) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task4'), T4) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task5'), T5) is True)
		registry_storage.stop_task('task3', stop_dependent=False)
		assert(registry_storage.started_tasks(task_registry_id='task3') is None)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task4'), T4) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task5'), T5) is True)

		registry_storage.start_task('task3')
		registry_storage.start_task('task8')
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task3'), T3) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task4'), T4) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task5'), T5) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task7'), T7) is True)
		assert(isinstance(registry_storage.started_tasks(task_registry_id='task8'), T8) is True)
		registry_storage.stop_task('task8', stop_requirements=True)
		assert(registry_storage.started_tasks(task_registry_id='task3') is None)
		assert(registry_storage.started_tasks(task_registry_id='task4') is None)
		assert(registry_storage.started_tasks(task_registry_id='task5') is None)
		assert(registry_storage.started_tasks(task_registry_id='task7') is None)
		assert(registry_storage.started_tasks(task_registry_id='task8') is None)


class TestWTaskDependencyRegistry:

	def test_registry(self):

		class R1(WTaskDependencyRegistry):
			pass

		with pytest.raises(ValueError):
			R1.registry_storage()

		with pytest.raises(TypeError):
			class FakeRS:
				pass
			R1.__registry_storage__ = FakeRS()
			R1.registry_storage()

		R1.__registry_storage__ = WTaskDependencyRegistryStorage()
		assert(R1.registry_storage() == R1.__registry_storage__)

		class T1(WTask, metaclass=WDependentTask):
			__registry__ = R1
			__registry_tag__ = 'task1'

			last_call_result = None

			def start(self):
				T1.last_call_result = 'T1.start'

			def stop(self):
				T1.last_call_result = 'T1.stop'

		class T2(WStoppableTask, metaclass=WDependentTask):
			__registry__ = R1
			__registry_tag__ = 'task2'

			last_call_result = None

			def start(self):
				T2.last_call_result = 'T2.start'

			def stop(self):
				T2.last_call_result = 'T2.stop'

		assert(R1.registry_storage().started_tasks(task_registry_id='task1') is None)
		assert(R1.registry_storage().started_tasks(task_registry_id='task2') is None)

		R1.start_task('task1')
		assert(isinstance(R1.registry_storage().started_tasks(task_registry_id='task1'), T1) is True)
		assert(T1.last_call_result == 'T1.start')
		assert(R1.registry_storage().started_tasks(task_registry_id='task2') is None)

		R1.stop_task('task1')
		assert(R1.registry_storage().started_tasks(task_registry_id='task1') is None)
		assert(T1.last_call_result == 'T1.start')
		assert(R1.registry_storage().started_tasks(task_registry_id='task2') is None)

		R1.start_task('task2')
		assert(R1.registry_storage().started_tasks(task_registry_id='task1') is None)
		assert(isinstance(R1.registry_storage().started_tasks(task_registry_id='task2'), T2) is True)
		assert(T2.last_call_result == 'T2.start')

		R1.stop_task('task2')
		assert(R1.registry_storage().started_tasks(task_registry_id='task1') is None)
		assert(R1.registry_storage().started_tasks(task_registry_id='task2') is None)
		assert(T2.last_call_result == 'T2.stop')

		R1.start_task('task1')
		R1.start_task('task2')
		assert(isinstance(R1.registry_storage().started_tasks(task_registry_id='task1'), T1) is True)
		assert(isinstance(R1.registry_storage().started_tasks(task_registry_id='task2'), T2) is True)

		R1.all_stop()
		assert(R1.registry_storage().started_tasks(task_registry_id='task1') is None)
		assert(R1.registry_storage().started_tasks(task_registry_id='task2') is None)
