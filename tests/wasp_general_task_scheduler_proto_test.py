# -*- coding: utf-8 -*-

import pytest
from datetime import datetime

from wasp_general.task.thread import WThreadTask
from wasp_general.datetime import utc_datetime

from wasp_general.task.scheduler.proto import WScheduleTask, WScheduleRecord, WRunningScheduleRecord, WTaskSourceProto
from wasp_general.task.scheduler.proto import WRunningRecordRegistryProto, WSchedulerServiceProto


def test_abstract():
	pytest.raises(TypeError, WTaskSourceProto)
	pytest.raises(NotImplementedError, WTaskSourceProto.has_records, None)
	pytest.raises(NotImplementedError, WTaskSourceProto.next_start, None)
	pytest.raises(NotImplementedError, WTaskSourceProto.tasks_planned, None)
	pytest.raises(NotImplementedError, WTaskSourceProto.scheduler_service, None)
	pytest.raises(TypeError, WRunningRecordRegistryProto)

	schedule = WScheduleRecord(TestWScheduleTask.DummyTask())
	pytest.raises(NotImplementedError, WRunningRecordRegistryProto.exec, None, schedule)
	pytest.raises(NotImplementedError, WRunningRecordRegistryProto.running_records, None)
	pytest.raises(TypeError, WSchedulerServiceProto)
	pytest.raises(NotImplementedError, WSchedulerServiceProto.update, None)


class TestWScheduleTask:

	class DummyTask(WScheduleTask):

		def thread_started(self):
			pass

		def thread_stopped(self):
			pass

	def test(self):
		task = TestWScheduleTask.DummyTask()
		assert(isinstance(task, WScheduleTask) is True)
		assert(isinstance(task, WThreadTask) is True)

		assert(task.stop_event() is not None)
		assert(task.ready_event() is not None)


class TestWScheduleRecord:

	def test(self):
		task = TestWScheduleTask.DummyTask()

		pytest.raises(TypeError, WScheduleRecord, task, policy=1)

		schedule = WScheduleRecord(task)
		assert(schedule.task() == task)
		assert(schedule.policy() == WScheduleRecord.PostponePolicy.wait)
		assert(schedule.task_group_id() is None)

		callback_result = []

		def drop_callback():
			callback_result.append(1)

		schedule = WScheduleRecord(task, on_drop=drop_callback)
		assert(callback_result == [])
		schedule.task_dropped()
		assert(callback_result == [1])


class TestWRunningScheduleRecord:

	def test(self):
		task = TestWScheduleTask.DummyTask()
		record = WScheduleRecord(task)
		started_at = datetime.now()

		assert(ValueError, WRunningScheduleRecord, record, started_at)

		started_at = utc_datetime()
		running_task = WRunningScheduleRecord(record, started_at)
		assert(running_task.task() == task)
		assert(running_task.task_uid() == task.uid())
		assert(running_task.record() == record)
		assert(running_task.started_at() == started_at)
