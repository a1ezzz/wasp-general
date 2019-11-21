
import pytest

from wasp_general.api.registry import WAPIRegistry
from wasp_general.api.task.proto import WLauncherTaskProto, WLauncherProto, WNoSuchTask, WStartedTaskError
from wasp_general.api.task.proto import WRequirementsLoop, WDependenciesLoop
from wasp_general.api.task.launcher import WLauncher, register_task


class TestWTaskLauncher:

	launch_counter = 0
	stop_exec_counter = 0
	terminate_exec_counter = 0

	class BaseTask(WLauncherTaskProto):
		@classmethod
		def launcher_task(cls, launcher):
			TestWTaskLauncher.launch_counter += 1
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
		start_exec_counter = TestWTaskLauncher.launch_counter

		registry = WAPIRegistry()
		launcher = WLauncher(registry)
		assert(isinstance(launcher, WLauncherProto) is True)
		assert(launcher.registry() is registry)

		assert(len(launcher) == 0)
		assert(list(launcher) == [])
		assert(len(list(launcher.started_tasks())) == 0)
		assert(list(launcher.started_tasks()) == [])

		assert(launcher.is_started('task1') is False)
		assert('task1' not in launcher)

		register_task(registry=registry)(TestWTaskLauncher.Task1)

		assert(launcher.start_task('task1') == 1)
		assert(TestWTaskLauncher.launch_counter == (start_exec_counter + 1))
		assert(launcher.is_started('task1') is True)
		assert('task1' in launcher)

		pytest.raises(WStartedTaskError, launcher.start_task, 'task1')
		assert(len(launcher) == 1)
		assert(list(launcher) == ['task1'])
		assert(launcher.is_started('task1') is True)
		assert('task1' in launcher)

		pytest.raises(WNoSuchTask, launcher.start_task, 'unknown_task')
		pytest.raises(WNoSuchTask, launcher.stop_task, 'unknown_task')

		launcher.stop_task('task1')
		assert(len(launcher) == 0)

	def test_requirements(self):
		launch_counter = TestWTaskLauncher.launch_counter

		registry = WAPIRegistry()

		register_task(registry=registry)(TestWTaskLauncher.Task1)
		register_task(registry=registry)(TestWTaskLauncher.Task2)
		register_task(registry=registry)(TestWTaskLauncher.Task3)
		register_task(registry=registry)(TestWTaskLauncher.Task4)
		register_task(registry=registry)(TestWTaskLauncher.Task5)
		register_task(registry=registry)(TestWTaskLauncher.Task6)

		launcher = WLauncher(registry)
		assert(launcher.requirements('task1') is None)
		assert(set(launcher.requirements('task2')) == {'task1'})
		assert(set(launcher.requirements('task3')) == {'task1', 'task2'})

		assert(launcher.start_task('task3') == 3)
		assert(len(launcher) == 3)
		assert('task2' in launcher)
		assert('task2' in launcher)
		assert('task3' in launcher)
		assert(TestWTaskLauncher.launch_counter == (launch_counter + 3))

		pytest.raises(WStartedTaskError, launcher.start_task, 'task2')
		assert(len(tuple(launcher)) == 3)

		pytest.raises(WNoSuchTask, launcher.start_task, 'task4')
		assert(launcher.start_task('task4', skip_unresolved=True) == 1)
		assert(len(launcher) == 4)
		assert('task1' in launcher)
		assert('task2' in launcher)
		assert('task3' in launcher)
		assert('task4' in launcher)
		assert(TestWTaskLauncher.launch_counter == (launch_counter + 4))

		launcher.stop_task('task1')
		launcher.stop_task('task4')
		assert(len(launcher) == 2)
		assert('task2' in launcher)
		assert('task3' in launcher)

		assert(launcher.start_task('task4', skip_unresolved=True) == 1)
		assert(len(launcher) == 3)
		assert('task2' in launcher)
		assert('task3' in launcher)
		assert('task4' in launcher)
		assert(TestWTaskLauncher.launch_counter == (launch_counter + 5))

		launcher.stop_task('task4')
		assert(len(launcher) == 2)

		assert(launcher.start_task('task4', skip_unresolved=True, requirements_deep_check=True) == 2)
		assert(len(launcher) == 4)
		assert('task1' in launcher)
		assert('task2' in launcher)
		assert('task3' in launcher)
		assert('task4' in launcher)
		assert(TestWTaskLauncher.launch_counter == (launch_counter + 7))

		pytest.raises(WRequirementsLoop, launcher.start_task, 'task5')
		pytest.raises(WRequirementsLoop, launcher.start_task, 'task6')

	def test_stop(self):
		stop_exec_counter = TestWTaskLauncher.stop_exec_counter
		terminate_exec_counter = TestWTaskLauncher.terminate_exec_counter

		registry = WAPIRegistry()
		register_task(registry=registry)(TestWTaskLauncher.Task1)
		register_task(registry=registry)(TestWTaskLauncher.Task2)
		register_task(registry=registry)(TestWTaskLauncher.Task3)
		register_task(registry=registry)(TestWTaskLauncher.Task4)

		launcher = WLauncher(registry)
		assert(launcher.start_task('task3') == 3)
		assert(launcher.start_task('task4', skip_unresolved=True) == 1)

		launcher.stop_task('task1')
		assert(TestWTaskLauncher.stop_exec_counter == stop_exec_counter)
		assert(TestWTaskLauncher.terminate_exec_counter == terminate_exec_counter)

		launcher.stop_task('task2')
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 1))
		assert(TestWTaskLauncher.terminate_exec_counter == terminate_exec_counter)

		launcher.stop_task('task3')
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 1))
		assert(TestWTaskLauncher.terminate_exec_counter == terminate_exec_counter)

		launcher.start_task('task3')
		launcher.stop_task('task3', terminate=True)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 1))
		assert(TestWTaskLauncher.terminate_exec_counter == (terminate_exec_counter + 1))

		pytest.raises(WNoSuchTask, launcher.stop_task, 'task3')

		launcher.stop_task('task2', stop=False)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 1))
		assert(TestWTaskLauncher.terminate_exec_counter == (terminate_exec_counter + 1))

		launcher.start_task('task3')
		assert(len(launcher) == 4)
		assert('task1' in launcher)
		assert('task2' in launcher)
		assert('task3' in launcher)
		assert('task4' in launcher)

		assert(launcher.stop_dependent_tasks('task1') == 3)
		assert(TestWTaskLauncher.stop_exec_counter == (stop_exec_counter + 2))
		assert(TestWTaskLauncher.terminate_exec_counter == (terminate_exec_counter + 1))
		assert(list(launcher) == ['task1'])

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

		register_task(registry=registry)(Task7)
		register_task(registry=registry)(Task8)

		launcher.start_task('task8')
		assert(len(launcher) == 3)
		assert('task1' in launcher)
		assert('task7' in launcher)
		assert('task8' in launcher)

		Task7.__requirements__ = ('task8', )
		pytest.raises(WDependenciesLoop, launcher.stop_dependent_tasks, 'task1')

		Task7.__requirements__ = None
		assert(launcher.all_stop() == 3)
		assert(list(launcher) == [])


def test_register_task():
	registry = WAPIRegistry()
	assert(registry.has(TestWTaskLauncher.Task1.__task_tag__) is False)

	register_task(registry=registry)(TestWTaskLauncher.Task1)

	assert(registry.has(TestWTaskLauncher.Task1.__task_tag__) is True)
	assert(registry.get(TestWTaskLauncher.Task1.__task_tag__) is TestWTaskLauncher.Task1)

	class CorrupterTask(WLauncherTaskProto):
		# there is no redefined __task_tag__

		@classmethod
		def launcher_task(cls, launcher):
			TestWTaskLauncher.launch_counter += 1
			return cls()

		def start(self):
			pass

	with pytest.raises(ValueError):
		register_task(registry=registry)(CorrupterTask)

	CorrupterTask.__task_tag__ = 1  # not it has a tag, but it has invalid type

	with pytest.raises(ValueError):
		register_task(registry=registry)(CorrupterTask)

	CorrupterTask.__task_tag__ = 'task'  # now it is ok
	register_task(registry=registry)(CorrupterTask)
