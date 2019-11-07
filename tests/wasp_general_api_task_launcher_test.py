
import pytest

from wasp_general.api.task.proto import WTaskLauncherProto, WTaskProto, WNoSuchTask, WRequirementsLoop
from wasp_general.api.task.proto import WDependenciesLoop
from wasp_general.api.task.registry import WTaskRegistry, __default_task_registry__, register_class
from wasp_general.api.task.launcher import WTaskLauncher


class TestWTaskLauncher:

	start_exec_counter = 0
	stop_exec_counter = 0
	terminate_exec_counter = 0

	class BaseTask(WTaskProto):
		@classmethod
		def init_task(cls, **kwargs):
			TestWTaskLauncher.start_exec_counter += 1
			return cls()

		def start(self):
			pass

	class Task1(BaseTask):

		__task_tag__ = 'task1'

	class Task2(BaseTask):

		__task_tag__ = 'task2'

		@classmethod
		def requirements(cls):
			return 'task1',

		def stop(self):
			TestWTaskLauncher.stop_exec_counter += 1

	class Task3(BaseTask):
		__task_tag__ = 'task3'

		@classmethod
		def requirements(cls):
			return 'task1', 'task2'

		def terminate(self):
			TestWTaskLauncher.terminate_exec_counter += 1

	class Task4(BaseTask):
		__task_tag__ = 'task4'

		@classmethod
		def requirements(cls):
			return 'task3', 'unresolved_task'

	class Task5(BaseTask):
		__task_tag__ = 'task5'

		@classmethod
		def requirements(cls):
			return 'task3', 'task6'  # mutual dependency check

	class Task6(BaseTask):
		__task_tag__ = 'task6'

		@classmethod
		def requirements(cls):
			return 'task1', 'task6'  # mutual dependency check

	def test(self):
		start_exec_counter = TestWTaskLauncher.start_exec_counter

		launcher = WTaskLauncher()
		assert(isinstance(launcher, WTaskLauncherProto) is True)
		assert(launcher.registry() is __default_task_registry__)

		registry = WTaskRegistry()
		launcher = WTaskLauncher(registry)
		assert(isinstance(launcher, WTaskLauncherProto) is True)
		assert(launcher.registry() is registry)

		assert(list(iter(launcher)) == [])
		assert(list(launcher.started_tasks()) == [])
		with pytest.raises(WNoSuchTask):
			list(launcher.started_tasks('task1'))

		register_class(registry=registry)(TestWTaskLauncher.Task1)

		simple_task_instance1 = launcher.start_task('task1')
		assert(isinstance(simple_task_instance1, str) is True)
		assert(TestWTaskLauncher.start_exec_counter == (start_exec_counter + 1))
		simple_task_instance2 = launcher.start_task('task1')
		assert(isinstance(simple_task_instance2, str) is True)
		assert(TestWTaskLauncher.start_exec_counter == (start_exec_counter + 2))
		assert(str(simple_task_instance1) != str(simple_task_instance2))

		tasks_list = list(iter(launcher))
		tasks_str_instances = [x[1] for x in tasks_list]
		assert([x[0] for x in tasks_list] == ['task1', 'task1'])
		assert(simple_task_instance1 in tasks_str_instances)
		assert(simple_task_instance2 in tasks_str_instances)

		pytest.raises(WNoSuchTask, launcher.start_task, 'unknown_task')
		pytest.raises(WNoSuchTask, launcher.stop_task, 'unknown_task')

		assert(launcher.stop_task('task1') == 2)

	def test_requirements(self):
		start_exec_counter = TestWTaskLauncher.start_exec_counter

		registry = WTaskRegistry()
		register_class(registry=registry)(TestWTaskLauncher.Task1)
		register_class(registry=registry)(TestWTaskLauncher.Task2)
		register_class(registry=registry)(TestWTaskLauncher.Task3)
		register_class(registry=registry)(TestWTaskLauncher.Task4)
		register_class(registry=registry)(TestWTaskLauncher.Task5)
		register_class(registry=registry)(TestWTaskLauncher.Task6)

		launcher = WTaskLauncher(registry)
		assert(launcher.requirements('task1') is None)
		assert(set(launcher.requirements('task2')) == {'task1'})
		assert(set(launcher.requirements('task3')) == {'task1', 'task2'})

		task3_instance = launcher.start_task('task3')
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 3)
		assert('task1' in tasks_tags)
		assert('task2' in tasks_tags)
		assert('task3' in tasks_tags)
		assert(TestWTaskLauncher.start_exec_counter == (start_exec_counter + 3))

		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task2'))) == 1)
		assert(tuple(launcher.started_tasks('task3')) == (('task3', task3_instance),))

		launcher.start_task('task2')
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 4)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task2'))) == 2)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)
		assert(TestWTaskLauncher.start_exec_counter == (start_exec_counter + 4))

		pytest.raises(WNoSuchTask, launcher.start_task, 'task4')
		launcher.start_task('task4', skip_unresolved=True)
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 5)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task2'))) == 2)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)
		assert(len(tuple(launcher.started_tasks('task4'))) == 1)
		assert(TestWTaskLauncher.start_exec_counter == (start_exec_counter + 5))

		assert(launcher.stop_task('task1') == 1)
		assert(launcher.stop_task('task4') == 1)
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 3)
		assert(len(tuple(launcher.started_tasks('task2'))) == 2)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)

		launcher.start_task('task4', skip_unresolved=True)
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 4)
		assert(len(tuple(launcher.started_tasks('task2'))) == 2)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)
		assert(len(tuple(launcher.started_tasks('task4'))) == 1)
		assert(TestWTaskLauncher.start_exec_counter == (start_exec_counter + 6))

		launcher.start_task('task4', skip_unresolved=True, requirements_deep_check=True)
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 6)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task2'))) == 2)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)
		assert(len(tuple(launcher.started_tasks('task4'))) == 2)
		assert(TestWTaskLauncher.start_exec_counter == (start_exec_counter + 8))

		pytest.raises(WRequirementsLoop, launcher.start_task, 'task5')
		pytest.raises(WRequirementsLoop, launcher.start_task, 'task6')

	def test_stop(self):
		stop_exec_counter = TestWTaskLauncher.stop_exec_counter
		terminate_exec_counter = TestWTaskLauncher.terminate_exec_counter

		registry = WTaskRegistry()
		register_class(registry=registry)(TestWTaskLauncher.Task1)
		register_class(registry=registry)(TestWTaskLauncher.Task2)
		register_class(registry=registry)(TestWTaskLauncher.Task3)
		register_class(registry=registry)(TestWTaskLauncher.Task4)

		launcher = WTaskLauncher(registry)
		launcher.start_task('task3')
		launcher.start_task('task4', skip_unresolved=True)
		launcher.start_task('task2')

		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 5)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task2'))) == 2)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)
		assert(len(tuple(launcher.started_tasks('task4'))) == 1)

		assert(launcher.stop_task('task1') == 1)
		assert(TestWTaskLauncher.stop_exec_counter == stop_exec_counter)
		assert(TestWTaskLauncher.terminate_exec_counter == terminate_exec_counter)

		assert(launcher.stop_task('task2') == 2)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 2))
		# note: there are two instances of 'task2'
		assert(TestWTaskLauncher.terminate_exec_counter == terminate_exec_counter)

		assert(launcher.stop_task('task3') == 1)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 2))
		assert(TestWTaskLauncher.terminate_exec_counter == terminate_exec_counter)

		launcher.start_task('task3')
		assert(launcher.stop_task('task3', terminate=True) == 1)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 2))
		assert(TestWTaskLauncher.terminate_exec_counter == (terminate_exec_counter + 1))

		launcher.start_task('task3')
		task2_instance = launcher.start_task('task2')
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 5)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task2'))) == 2)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)
		assert(len(tuple(launcher.started_tasks('task4'))) == 1)

		assert(launcher.stop_task('task2', instance_id=task2_instance) == 1)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 3))
		assert(TestWTaskLauncher.terminate_exec_counter == (terminate_exec_counter + 1))
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 4)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task2'))) == 1)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)
		assert(len(tuple(launcher.started_tasks('task4'))) == 1)

		pytest.raises(WNoSuchTask, launcher.stop_task, 'task2', 'unknown_instance')

		assert(launcher.stop_task('task2', stop=False) == 1)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 3))
		assert(TestWTaskLauncher.terminate_exec_counter == (terminate_exec_counter + 1))
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 3)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task3'))) == 1)
		assert(len(tuple(launcher.started_tasks('task4'))) == 1)

		assert(launcher.stop_dependent_tasks('task1') == 2)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 3))
		assert(TestWTaskLauncher.terminate_exec_counter == (terminate_exec_counter + 1))
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 1)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)

		class Task7(TestWTaskLauncher.BaseTask):
			__task_tag__ = 'task7'
			__requirements__ = None

			@classmethod
			def requirements(cls):
				return cls.__requirements__

		class Task8(TestWTaskLauncher.BaseTask):
			__task_tag__ = 'task8'

			@classmethod
			def requirements(cls):
				return 'task7', 'task1'

		register_class(registry=registry)(Task7)
		register_class(registry=registry)(Task8)

		launcher.start_task('task8')
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 3)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task7'))) == 1)
		assert(len(tuple(launcher.started_tasks('task8'))) == 1)

		Task7.__requirements__ = ('task8', )
		pytest.raises(WDependenciesLoop, launcher.stop_dependent_tasks, 'task1')

		Task7.__requirements__ = None
		tasks_tags = tuple(x[0] for x in launcher)
		assert(len(tasks_tags) == 3)
		assert(len(tuple(launcher.started_tasks('task1'))) == 1)
		assert(len(tuple(launcher.started_tasks('task7'))) == 1)
		assert(len(tuple(launcher.started_tasks('task8'))) == 1)

		launcher.all_stop()
		assert(list(launcher) == [])
