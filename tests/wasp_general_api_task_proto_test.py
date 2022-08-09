# -*- coding: utf-8 -*-

import enum
import pytest

from wasp_general.api.capability import WCapabilityDescriptor, iscapable, WCapabilitiesHolderMeta
from wasp_general.api.registry import WAPIRegistry
from wasp_general.api.signals import ASignalSourceProto, WSignalSourceMeta

from wasp_general.api.task.proto import WRequirementsLoopError, WDependenciesLoopError, WTaskStartError, WTaskStopError
from wasp_general.api.task.proto import WNoSuchTaskError, WCapabilitiesSignalsMeta, WTaskResult, WTaskProto
from wasp_general.api.task.proto import WTaskStopMode, WLauncherTaskProto, WLauncherProto, WScheduledTaskPostponePolicy
from wasp_general.api.task.proto import WScheduleRecordProto, WScheduleSourceProto, WScheduledTaskResult
from wasp_general.api.task.proto import WSchedulerProto


def test_exceptions():
    assert(issubclass(WRequirementsLoopError, Exception) is True)
    assert(issubclass(WDependenciesLoopError, Exception) is True)
    assert(issubclass(WTaskStartError, Exception) is True)
    assert(issubclass(WTaskStopError, Exception) is True)
    assert(issubclass(WNoSuchTaskError, Exception) is True)


def test_abstract_classes():
    pytest.raises(TypeError, WTaskProto)
    pytest.raises(NotImplementedError, WTaskProto.start, None)

    assert(issubclass(WLauncherTaskProto, WTaskProto) is True)
    pytest.raises(TypeError, WLauncherTaskProto)
    pytest.raises(NotImplementedError, WLauncherTaskProto.launcher_task)
    pytest.raises(NotImplementedError, WLauncherTaskProto.start, None)

    pytest.raises(TypeError, WLauncherProto)
    assert(issubclass(WLauncherProto, WAPIRegistry) is True)
    pytest.raises(NotImplementedError, WLauncherProto.is_started, None, 'foo')
    pytest.raises(NotImplementedError, WLauncherProto.started_tasks, None)
    pytest.raises(
        NotImplementedError, WLauncherProto.start_task, None, 'foo'
    )
    pytest.raises(NotImplementedError, WLauncherProto.stop_task, None, 'foo')
    pytest.raises(NotImplementedError, WLauncherProto.stop_dependent_tasks, None, 'foo')
    pytest.raises(NotImplementedError, WLauncherProto.all_stop, None)

    pytest.raises(TypeError, WScheduleRecordProto)
    pytest.raises(NotImplementedError, WScheduleRecordProto.task, None)

    pytest.raises(TypeError, WSchedulerProto)
    pytest.raises(NotImplementedError, WSchedulerProto.subscribe, None, WScheduleSourceProto())
    pytest.raises(NotImplementedError, WSchedulerProto.unsubscribe, None, WScheduleSourceProto())


class TestWCapabilitiesSignalsMeta:

    def test(self):
        assert(issubclass(WCapabilitiesSignalsMeta, WSignalSourceMeta) is True)
        assert(issubclass(WCapabilitiesSignalsMeta, WCapabilitiesHolderMeta) is True)


class TestWTaskResult:

    def test(self):
        exc = ValueError('!')
        result = object()
        task_result = WTaskResult(result=result, exception=exc)
        assert(task_result.result is result)
        assert(task_result.exception is exc)


class TestWTaskProto:

    class Task(WTaskProto):
        def start(self):
            pass

    def test(self):
        assert(isinstance(WTaskProto.stop, WCapabilityDescriptor) is True)
        assert(isinstance(WTaskProto.terminate, WCapabilityDescriptor) is True)

        task = TestWTaskProto.Task()
        pytest.raises(NotImplementedError, task.stop)
        pytest.raises(NotImplementedError, task.terminate)

        assert(iscapable(task, WTaskProto.stop) is False)
        assert(iscapable(task, WTaskProto.terminate) is False)

        task.emit(WTaskProto.task_started)
        task.emit(WTaskProto.task_stopped)
        task.emit(WTaskProto.task_terminated)
        task.emit(WTaskProto.task_completed, WTaskResult())


class TestWTaskStopMode:

    def test(self):
        assert(issubclass(WTaskStopMode, enum.Enum) is True)
        assert([x for x in WTaskStopMode] == [WTaskStopMode.stop, WTaskStopMode.terminate])


class TestWLauncherTaskProto:

    class Task(WLauncherTaskProto):

        __task_tag__ = 'task'

        @classmethod
        def launcher_task(cls):
            return cls()

        def start(self):
            pass

    def test(self):
        assert(TestWLauncherTaskProto.Task.requirements() is None)

        task = TestWLauncherTaskProto.Task.launcher_task()
        assert(isinstance(task, WTaskProto) is True)
        assert(WTaskProto.stop not in task)
        assert(WTaskProto.terminate not in task)


class TestWScheduledTaskPostponePolicy:

    def test(self):
        assert(issubclass(WScheduledTaskPostponePolicy, enum.Enum) is True)
        assert(
            [x for x in WScheduledTaskPostponePolicy] == [
                WScheduledTaskPostponePolicy.wait,
                WScheduledTaskPostponePolicy.drop,
                WScheduledTaskPostponePolicy.keep_first,
                WScheduledTaskPostponePolicy.keep_last
            ]
        )


class TestWScheduleRecordProto:

    class Record(WScheduleRecordProto):
        def task(self):
            return None

    def test(self):
        record = TestWScheduleRecordProto.Record()
        assert(record.group_id() is None)
        assert(record.ttl() is None)
        assert(record.simultaneous_policy() == 0)
        assert(record.postpone_policy() is WScheduledTaskPostponePolicy.wait)


class TestWScheduleSourceProto:

    def test(self):
        source = WScheduleSourceProto()
        assert(isinstance(source, ASignalSourceProto) is True)
        source.emit(WScheduleSourceProto.task_scheduled, TestWScheduleRecordProto.Record())


class TestWScheduledTaskResult:

    def test(self):
        pytest.raises(TypeError, WScheduledTaskResult)

        record = TestWScheduleRecordProto.Record()
        exc = ValueError('!')
        task_result = WTaskResult(exception=exc)
        record_result = WScheduledTaskResult(record=record, task_result=task_result)
        assert(record_result.record is record)
        assert(record_result.task_result is task_result)


class TestWSchedulerProto:

    class Scheduler(WSchedulerProto):

        def subscribe(self, schedule_source):
            pass

        def unsubscribe(self, schedule_source):
            pass

        def running_records(self):
            pass

        def start(self):
            pass

    def test(self):
        assert(issubclass(WSchedulerProto, ASignalSourceProto) is True)

        scheduler = TestWSchedulerProto.Scheduler()
        assert(isinstance(scheduler, ASignalSourceProto) is True)

        scheduler.emit(WSchedulerProto.task_scheduled, TestWScheduleRecordProto.Record())
        scheduler.emit(WSchedulerProto.scheduled_task_dropped, TestWScheduleRecordProto.Record())
        scheduler.emit(WSchedulerProto.scheduled_task_expired, TestWScheduleRecordProto.Record())
        scheduler.emit(WSchedulerProto.scheduled_task_postponed, TestWScheduleRecordProto.Record())
        scheduler.emit(WSchedulerProto.scheduled_task_started, TestWScheduleRecordProto.Record())
        scheduler.emit(
            WSchedulerProto.scheduled_task_completed,
            WScheduledTaskResult(TestWScheduleRecordProto.Record(), WTaskResult())
        )
        scheduler.emit(WSchedulerProto.scheduled_task_stopped, TestWScheduleRecordProto.Record())
