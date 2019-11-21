# -*- coding: utf-8 -*-

import pytest
import enum

from wasp_general.api.capability import WCapabilityDescriptor
from wasp_general.api.signals import WSignal, WSignalSourceProto, WSignalSource

from wasp_general.api.task.proto import WNoSuchTask, WRequirementsLoop, WDependenciesLoop, WStartedTaskError
from wasp_general.api.task.proto import WStoppedTaskError, WTaskProto, WLauncherTaskProto, WLauncherProto
from wasp_general.api.task.proto import WScheduledTaskProto, WTaskPostponePolicy, WScheduleRecordProto
from wasp_general.api.task.proto import WScheduleSourceProto, WSchedulerProto


def test_exceptions():
	assert(issubclass(WNoSuchTask, Exception) is True)
	assert(issubclass(WRequirementsLoop, Exception) is True)
	assert(issubclass(WDependenciesLoop, Exception) is True)
	assert(issubclass(WStartedTaskError, Exception) is True)
	assert(issubclass(WStoppedTaskError, Exception) is True)


def test_abstract_classes():
	pytest.raises(TypeError, WTaskProto)
	pytest.raises(NotImplementedError, WTaskProto.start, None)

	assert(issubclass(WLauncherTaskProto, WTaskProto) is True)
	pytest.raises(TypeError, WLauncherTaskProto)
	pytest.raises(NotImplementedError, WLauncherTaskProto.start, None)
	pytest.raises(NotImplementedError, WLauncherTaskProto.launcher_task, None)

	pytest.raises(TypeError, WLauncherProto)
	pytest.raises(NotImplementedError, WLauncherProto.is_started, None, 'foo')
	pytest.raises(NotImplementedError, WLauncherProto.started_tasks, None)
	pytest.raises(
		NotImplementedError, WLauncherProto.start_task, None, 'foo'
	)
	pytest.raises(NotImplementedError, WLauncherProto.stop_task, None, 'foo')
	pytest.raises(NotImplementedError, WLauncherProto.stop_dependent_tasks, None, 'foo')
	pytest.raises(NotImplementedError, WLauncherProto.all_stop, None)

	assert(issubclass(WScheduledTaskProto, WTaskProto) is True)
	pytest.raises(TypeError, WScheduledTaskProto)
	pytest.raises(NotImplementedError, WScheduledTaskProto.scheduled_task, None)

	pytest.raises(TypeError, WScheduleRecordProto)
	pytest.raises(NotImplementedError, WScheduleRecordProto.task, None)

	pytest.raises(TypeError, WScheduleSourceProto)

	pytest.raises(TypeError, WSchedulerProto)
	pytest.raises(NotImplementedError, WSchedulerProto.subscribe, None, TestWScheduleSourceProto.Source())
	pytest.raises(NotImplementedError, WSchedulerProto.unsubscribe, None, TestWScheduleSourceProto.Source())
	pytest.raises(NotImplementedError, WSchedulerProto.running_records, None)
	pytest.raises(NotImplementedError, WSchedulerProto.process, None, TestWScheduleRecordProto.Record(None))


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


class TestWLauncherTaskProto:

	class Task(WLauncherTaskProto):

		@classmethod
		def launcher_task(cls, launcher):
			return TestWLauncherTaskProto.Task()

		def start(self):
			pass

	def test(self):
		assert(TestWLauncherTaskProto.Task.requirements() is None)

		task = TestWLauncherTaskProto.Task.launcher_task(None)
		assert(isinstance(task, WTaskProto) is True)
		assert(WTaskProto.stop not in task)
		assert(WTaskProto.terminate not in task)


class TestWTaskPostponePolicy:

	def test(self):
		assert(issubclass(WTaskPostponePolicy, enum.Enum) is True)
		assert(hasattr(WTaskPostponePolicy, 'wait') is True)
		assert(hasattr(WTaskPostponePolicy, 'drop') is True)
		assert(hasattr(WTaskPostponePolicy, 'postpone_first') is True)
		assert(hasattr(WTaskPostponePolicy, 'postpone_last') is True)


class TestWScheduleRecordProto:

	class Record(WScheduleRecordProto):

		def __init__(self, task):
			self._task = task

		def task(self):
			return self._task

	def test(self):
		record = TestWScheduleRecordProto.Record(None)
		assert(record.group_id() is None)
		assert(record.policy() is WTaskPostponePolicy.wait)


class TestWScheduleSourceProto:

	class Source(WScheduleSourceProto, WSignalSource):
		pass

	def test(self):
		source = TestWScheduleSourceProto.Source()
		assert(isinstance(source, WSignalSource) is True)
		assert(isinstance(WScheduleSourceProto.task_scheduled, WSignal))
		WScheduleSourceProto.task_scheduled(source, TestWScheduleRecordProto.Record(None))


class TestWSchedulerProto:

	class Scheduler(WSchedulerProto, WSignalSource):

		def subscribe(self, schedule_source):
			pass

		def unsubscribe(self, schedule_source):
			pass

		def running_records(self):
			pass

		def process(self, schedule_record):
			pass

	def test(self):
		assert(issubclass(WSchedulerProto, WSignalSourceProto) is True)

		scheduler = TestWSchedulerProto.Scheduler()
		assert(isinstance(scheduler, WSignalSource) is True)

		assert(isinstance(WSchedulerProto.task_scheduled, WSignal))
		WSchedulerProto.task_scheduled(scheduler, TestWScheduleRecordProto.Record(None))

		assert(isinstance(WSchedulerProto.task_dropped, WSignal))
		WSchedulerProto.task_dropped(scheduler, TestWScheduleRecordProto.Record(None))

		assert(isinstance(WSchedulerProto.task_postponed, WSignal))
		WSchedulerProto.task_postponed(scheduler, TestWScheduleRecordProto.Record(None))

		assert(isinstance(WSchedulerProto.task_started, WSignal))
		WSchedulerProto.task_started(scheduler, TestWScheduleRecordProto.Record(None))

		assert(isinstance(WSchedulerProto.task_crashed, WSignal))
		WSchedulerProto.task_crashed(scheduler, tuple())

		assert(isinstance(WSchedulerProto.task_stopped, WSignal))
		WSchedulerProto.task_stopped(scheduler, tuple())
