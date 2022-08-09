
import pytest

from wasp_general.api.registry import WAPIRegistry
from wasp_general.api.task.proto import WLauncherTaskProto, WLauncherProto, WNoSuchTaskError, WTaskStartError
from wasp_general.api.task.proto import WRequirementsLoopError, WDependenciesLoopError, WTaskStopMode
from wasp_general.api.task.launcher import WLauncher, register_task


class TestData:

    launch_counter = 0
    stop_exec_counter = 0
    terminate_exec_counter = 0

    registry = WAPIRegistry()

    class BaseTask(WLauncherTaskProto):
        @classmethod
        def launcher_task(cls):
            TestData.launch_counter += 1
            return cls()

        def start(self):
            pass

    @register_task(registry)
    class Task1(BaseTask):
        __task_tag__ = 'task1'

    @register_task(registry)
    class Task2(BaseTask):
        __task_tag__ = 'task2'

        @classmethod
        def requirements(cls):
            return 'task1',

        def stop(self):
            TestData.stop_exec_counter += 1

    @register_task(registry)
    class Task3(BaseTask):
        __task_tag__ = 'task3'

        @classmethod
        def requirements(cls):
            return 'task1', 'task2'

        def terminate(self):
            TestData.terminate_exec_counter += 1

    @register_task(registry)
    class Task4(BaseTask):
        __task_tag__ = 'task4'

        @classmethod
        def requirements(cls):
            return 'task3', 'unresolved_task'

    @register_task(registry)
    class Task5(BaseTask):
        __task_tag__ = 'task5'

        @classmethod
        def requirements(cls):
            return 'task3', 'task6'  # mutual dependency check

    @register_task(registry)
    class Task6(BaseTask):
        __task_tag__ = 'task6'

        @classmethod
        def requirements(cls):
            return 'task1', 'task6'  # mutual dependency check

    @register_task(registry)
    class Task7(BaseTask):
        __task_tag__ = 'task7'
        __requirements__ = None

        @classmethod
        def requirements(cls):
            return cls.__requirements__

    @register_task(registry)
    class Task8(BaseTask):
        __task_tag__ = 'task8'

        @classmethod
        def requirements(cls):
            return 'task7', 'task1'


class TestWTaskLauncher:

    def test(self):
        start_exec_counter = TestData.launch_counter
        launcher = WLauncher(TestData.registry)
        assert(isinstance(launcher, WLauncherProto) is True)

        assert(len(launcher) == 0)
        assert(list(launcher) == [])
        assert(len(list(launcher.started_tasks())) == 0)
        assert(list(launcher.started_tasks()) == [])

        assert(launcher.is_started('task1') is False)
        assert('task1' not in launcher)

        assert(launcher.start_task('task1') == 1)
        assert(TestData.launch_counter == (start_exec_counter + 1))
        assert(launcher.is_started('task1') is True)
        assert('task1' in launcher)

        pytest.raises(WTaskStartError, launcher.start_task, 'task1')
        assert(len(launcher) == 1)
        assert(list(launcher) == ['task1'])
        assert(launcher.is_started('task1') is True)
        assert('task1' in launcher)

        pytest.raises(WNoSuchTaskError, launcher.start_task, 'unknown_task')
        pytest.raises(WNoSuchTaskError, launcher.stop_task, 'unknown_task')

        launcher.stop_task('task1')
        assert(len(launcher) == 0)

    def test_requirements(self):
        launch_counter = TestData.launch_counter
        launcher = WLauncher(TestData.registry)

        assert(launcher.start_task('task3') == 3)
        assert(len(launcher) == 3)
        assert('task2' in launcher)
        assert('task2' in launcher)
        assert('task3' in launcher)
        assert(TestData.launch_counter == (launch_counter + 3))

        pytest.raises(WTaskStartError, launcher.start_task, 'task2')
        assert(len(tuple(launcher)) == 3)

        pytest.raises(WNoSuchTaskError, launcher.start_task, 'task4')
        assert(launcher.start_task('task4', skip_unresolved=True) == 1)
        assert(len(launcher) == 4)
        assert('task1' in launcher)
        assert('task2' in launcher)
        assert('task3' in launcher)
        assert('task4' in launcher)
        assert(TestData.launch_counter == (launch_counter + 4))

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
        assert(TestData.launch_counter == (launch_counter + 5))

        launcher.stop_task('task4')
        assert(len(launcher) == 2)

        pytest.raises(WRequirementsLoopError, launcher.start_task, 'task5')
        pytest.raises(WRequirementsLoopError, launcher.start_task, 'task6')

    def test_stop(self):
        stop_exec_counter = TestData.stop_exec_counter
        terminate_exec_counter = TestData.terminate_exec_counter

        launcher = WLauncher(TestData.registry)

        assert(launcher.start_task('task3') == 3)
        assert(launcher.start_task('task4', skip_unresolved=True) == 1)

        launcher.stop_task('task1')
        assert(TestData.stop_exec_counter == stop_exec_counter)
        assert(TestData.terminate_exec_counter == terminate_exec_counter)

        launcher.stop_task('task2')
        assert(TestData.stop_exec_counter == (stop_exec_counter + 1))
        assert(TestData.terminate_exec_counter == terminate_exec_counter)

        launcher.stop_task('task3')
        assert(TestData.stop_exec_counter == (stop_exec_counter + 1))
        assert(TestData.terminate_exec_counter == terminate_exec_counter)

        launcher.start_task('task3')
        launcher.stop_task('task3', stop_mode=WTaskStopMode.terminate)
        assert(TestData.stop_exec_counter == (stop_exec_counter + 1))
        assert(TestData.terminate_exec_counter == (terminate_exec_counter + 1))

        pytest.raises(WNoSuchTaskError, launcher.stop_task, 'task3')

        launcher.stop_task('task2')
        assert(TestData.stop_exec_counter == (stop_exec_counter + 2))
        assert(TestData.terminate_exec_counter == (terminate_exec_counter + 1))

        launcher.start_task('task3')
        assert(len(launcher) == 4)
        assert('task1' in launcher)
        assert('task2' in launcher)
        assert('task3' in launcher)
        assert('task4' in launcher)

        assert(launcher.stop_dependent_tasks('task1') == 3)
        assert(TestData.stop_exec_counter == (stop_exec_counter + 3))
        assert(TestData.terminate_exec_counter == (terminate_exec_counter + 1))
        assert(list(launcher) == ['task1'])

        launcher.start_task('task8')
        assert(len(launcher) == 3)
        assert('task1' in launcher)
        assert('task7' in launcher)
        assert('task8' in launcher)

        TestData.Task7.__requirements__ = ('task8', )
        pytest.raises(WDependenciesLoopError, launcher.stop_dependent_tasks, 'task1')

        TestData.Task7.__requirements__ = None
        assert(launcher.all_stop() == 3)
        assert(list(launcher) == [])


def test_register_task():
    registry = WAPIRegistry()
    assert(registry.has(TestData.Task1.__task_tag__) is False)

    register_task(registry=registry)(TestData.Task1)

    assert(registry.has(TestData.Task1.__task_tag__) is True)
    assert(registry.get(TestData.Task1.__task_tag__) is TestData.Task1)

    class CorrupterTask(WLauncherTaskProto):
        # there is no redefined __task_tag__

        @classmethod
        def launcher_task(cls,):
            TestData.launch_counter += 1
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
