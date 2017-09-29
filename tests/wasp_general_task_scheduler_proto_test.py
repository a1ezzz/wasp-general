# -*- coding: utf-8 -*-

import pytest
from datetime import datetime

from wasp_general.task.thread import WThreadTask
from wasp_general.datetime import utc_datetime

from wasp_general.task.scheduler.proto import WScheduledTask, WTaskSchedule, WRunningScheduledTask, WTaskSourceProto
from wasp_general.task.scheduler.proto import WRunningTaskRegistryProto, WTaskSchedulerProto


def test_abstract():
	pytest.raises(TypeError, WTaskSourceProto)
	pytest.raises(NotImplementedError, WTaskSourceProto.has_tasks, None)
	pytest.raises(NotImplementedError, WTaskSourceProto.next_start, None)
	pytest.raises(NotImplementedError, WTaskSourceProto.tasks_planned, None)
	pytest.raises(TypeError, WRunningTaskRegistryProto)

	schedule = WTaskSchedule(TestWScheduledTask.DummyTask())
	pytest.raises(NotImplementedError, WRunningTaskRegistryProto.exec, None, schedule)
	pytest.raises(NotImplementedError, WRunningTaskRegistryProto.running_tasks, None)
	pytest.raises(TypeError, WTaskSchedulerProto)
	pytest.raises(NotImplementedError, WTaskSchedulerProto.update, None)


class TestWScheduledTask:

	class DummyTask(WScheduledTask):

		def thread_started(self):
			pass

		def thread_stopped(self):
			pass

	def test(self):
		task = TestWScheduledTask.DummyTask()
		assert(isinstance(task, WScheduledTask) is True)
		assert(isinstance(task, WThreadTask) is True)

		assert(task.stop_event() is not None)
		assert(task.ready_event() is not None)


class TestWTaskSchedule:

	def test(self):
		task = TestWScheduledTask.DummyTask()

		pytest.raises(TypeError, WTaskSchedule, task, policy=1)

		schedule = WTaskSchedule(task)
		assert(schedule.task() == task)
		assert(schedule.policy() == WTaskSchedule.PostponePolicy.wait)
		assert(schedule.task_id() is None)

		callback_result = []

		def drop_callback():
			callback_result.append(1)

		schedule = WTaskSchedule(task, on_drop=drop_callback)
		assert(callback_result == [])
		schedule.task_dropped()
		assert(callback_result == [1])


class TestWRunningScheduledTask:

	def test(self):
		task = TestWScheduledTask.DummyTask()
		schedule = WTaskSchedule(task)
		started_at = datetime.now()

		assert(ValueError, WRunningScheduledTask, schedule, started_at)

		started_at = utc_datetime()
		running_task = WRunningScheduledTask(schedule, started_at, 1)
		assert(running_task.task_schedule() == schedule)
		assert(running_task.started_at() == started_at)
		assert(running_task.task_uid() == 1)
