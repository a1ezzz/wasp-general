# -*- coding: utf-8 -*-

import pytest
from datetime import datetime

from wasp_general.task.thread import WThreadTask
from wasp_general.datetime import utc_datetime

from wasp_general.task.scheduler.proto import WScheduleTask, WScheduleRecord, WTaskSourceProto
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

		assert(task.uid() is not None)
		assert(TestWScheduleTask.DummyTask().uid() != TestWScheduleTask.DummyTask().uid())


class TestWScheduleRecord:

	def test(self):
		task = TestWScheduleTask.DummyTask()

		pytest.raises(TypeError, WScheduleRecord, task, policy=1)

		schedule = WScheduleRecord(task)
		assert(schedule.task() == task)
		assert(schedule.policy() == WScheduleRecord.PostponePolicy.wait)
		assert(schedule.task_group_id() is None)
		assert(schedule.task_uid() == task.uid())

		drop_callback_result = []

		def drop_callback():
			drop_callback_result.append(1)

		wait_callback_result = []

		def wait_callback():
			wait_callback_result.append(1)

		schedule = WScheduleRecord(task, on_drop=drop_callback)
		assert(drop_callback_result == [])
		schedule.task_dropped()
		assert(drop_callback_result == [1])

		schedule = WScheduleRecord(task, on_wait=wait_callback)
		assert(wait_callback_result == [])
		schedule.task_postponed()
		assert(wait_callback_result == [1])
