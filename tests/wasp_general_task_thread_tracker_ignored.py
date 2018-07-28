# -*- coding: utf-8 -*-

import pytest
import time

from wasp_general.task.thread import WThreadTask
from wasp_general.task.scheduler.proto import WScheduleTask, WScheduleRecord
from wasp_general.task.thread_tracker import WThreadTrackerInfoStorageProto, WThreadTracker, WSimpleTrackerStorage
from wasp_general.task.thread_tracker import WScheduleRecordTracker, WTrackerEvents


def test_abstract():
	pytest.raises(TypeError, WThreadTrackerInfoStorageProto)
	pytest.raises(
		NotImplementedError,
		WThreadTrackerInfoStorageProto.register_start,
		None, TestWThreadTracker.Task()
	)
	pytest.raises(
		NotImplementedError,
		WThreadTrackerInfoStorageProto.register_stop,
		None, TestWThreadTracker.Task()
	)
	pytest.raises(
		NotImplementedError,
		WThreadTrackerInfoStorageProto.register_termination,
		None, TestWThreadTracker.Task()
	)
	pytest.raises(
		NotImplementedError,
		WThreadTrackerInfoStorageProto.register_exception,
		None, TestWThreadTracker.Task(), ValueError('!'), '!'
	)
	pytest.raises(
		NotImplementedError,
		WThreadTrackerInfoStorageProto.register_wait,
		None, TestWThreadTracker.Task()
	)
	pytest.raises(
		NotImplementedError,
		WThreadTrackerInfoStorageProto.register_drop,
		None, TestWThreadTracker.Task()
	)

	pytest.raises(TypeError, WThreadTracker)


class TestWThreadTracker:

	class Task(WThreadTracker):

		def thread_started(self):
			pass

		def long_task(self):
			while self.stop_event().is_set() is False:
				time.sleep(0.01)

		@staticmethod
		def exc_task(*args, **kwargs):
			raise ValueError('!')

	class ScheduleTask(Task, WScheduleTask):

		def __init__(self, tracker_storage=None):
			TestWThreadTracker.Task.__init__(self, tracker_storage=tracker_storage)
			WScheduleTask.__init__(self)

	class Storage(WThreadTrackerInfoStorageProto):

		def __init__(self):
			self.start_count = 0
			self.stop_count = 0
			self.termination_count = 0
			self.exception_count = 0
			self.wait_count = 0
			self.drop_count = 0

		def register_start(self, task, event_details=None):
			self.start_count += 1

		def register_stop(self, task, event_details=None):
			self.stop_count += 1

		def register_termination(self, task, event_details=None):
			self.termination_count += 1

		def register_exception(self, task, raised_exception, exception_details, event_details=None):
			self.exception_count += 1

		def register_wait(self, task, event_details=None):
			self.wait_count += 1

		def register_drop(self, task, event_details=None):
			self.drop_count += 1

		def status(self):
			return (
				self.start_count, self.stop_count, self.termination_count, self.exception_count,
				self.wait_count, self.drop_count
			)

	def test(self):
		task = TestWThreadTracker.Task()
		assert(isinstance(task, TestWThreadTracker.Task) is True)
		assert(isinstance(task, WThreadTracker) is True)
		assert(isinstance(task, WThreadTask) is True)
		assert(task.tracker_storage() is None)
		assert(task.event_details(WTrackerEvents.start) is None)

		assert(task.track_stop() is True)
		assert(task.track_termination() is True)
		assert(task.track_exception() is True)

		task.start()
		task.ready_event().wait()
		task.stop()

		storage = TestWThreadTracker.Storage()
		assert(storage.status() == (0, 0, 0, 0, 0, 0))
		task = TestWThreadTracker.Task(tracker_storage=storage)
		assert(storage.status() == (0, 0, 0, 0, 0, 0))
		task.start()
		assert(storage.status() == (1, 0, 0, 0, 0, 0))
		task.ready_event().wait()
		task.stop()
		assert(storage.status() == (1, 1, 0, 0, 0, 0))

		task.thread_started = task.long_task
		assert(storage.status() == (1, 1, 0, 0, 0, 0))
		task.start()
		assert(storage.status() == (2, 1, 0, 0, 0, 0))
		task.start_event().wait()
		assert(storage.status() == (2, 1, 0, 0, 0, 0))
		task.stop()
		assert(storage.status() == (2, 1, 1, 0, 0, 0))

		task.thread_started = TestWThreadTracker.Task.exc_task
		assert(storage.status() == (2, 1, 1, 0, 0, 0))
		task.start()
		task.start_event().wait()
		task.stop()
		assert(storage.status() == (3, 1, 1, 1, 0, 0))

		storage.register_exception = TestWThreadTracker.Task.exc_task
		assert(storage.status() == (3, 1, 1, 1, 0, 0))
		task.start()
		task.start_event().wait()
		task.stop()
		assert(storage.status() == (4, 1, 1, 1, 0, 0))

		task = TestWThreadTracker.Task(
			tracker_storage=storage, track_start=False, track_stop=False, track_termination=False,
			track_exception=False
		)

		assert(task.track_stop() is False)
		assert(task.track_termination() is False)
		assert(task.track_exception() is False)

		task.start()
		task.ready_event().wait()
		task.stop()

		task.thread_started = task.long_task
		task.start()
		task.stop()

		task.thread_started = TestWThreadTracker.Task.exc_task
		task.start()
		task.stop()

		assert(storage.status() == (4, 1, 1, 1, 0, 0))

		storage.register_stop = TestWThreadTracker.Task.exc_task
		task = TestWThreadTracker.Task(tracker_storage=storage)
		task.start()
		task.ready_event().wait()
		task.stop()


class TestWSimpleTrackerStorage:

	def test(self):

		pytest.raises(TypeError, WSimpleTrackerStorage.Record, 1, TestWThreadTracker.Task())

		storage = WSimpleTrackerStorage()
		assert(isinstance(storage, WSimpleTrackerStorage) is True)
		assert(isinstance(storage, WThreadTrackerInfoStorageProto) is True)
		assert(storage.record_limit() is None)
		assert([] == [x for x in storage])

		task1 = TestWThreadTracker.Task(storage)
		task1.start()

		result = [x for x in storage]
		assert(len(result) == 1)
		assert(result[0].record_type == WTrackerEvents.start)
		assert(result[0].thread_task == task1)
		assert(result[0].event_details is None)

		task1.stop()

		result = [x for x in storage]
		assert(len(result) == 2)
		assert(result[0].record_type == WTrackerEvents.stop)
		assert(result[0].thread_task == task1)
		assert(result[0].event_details is None)
		assert(result[1].thread_task == task1)
		assert(result[1].record_type == WTrackerEvents.start)

		task2 = TestWThreadTracker.Task(storage)
		task2.event_details = lambda x: '!!!'
		task2.start()
		task2.stop()

		result = [x for x in storage]
		assert(len(result) == 4)
		assert(result[0].record_type == WTrackerEvents.stop)
		assert(result[0].thread_task == task2)
		assert(result[0].event_details == '!!!')
		assert(result[1].thread_task == task2)
		assert(result[2].thread_task == task1)
		assert(result[3].thread_task == task1)

		task3 = TestWThreadTracker.Task(storage)
		task3.thread_started = task3.long_task
		task3.start()
		task3.start_event().wait()
		task3.stop()

		result = [x for x in storage]
		assert(len(result) == 6)
		assert(result[0].record_type == WTrackerEvents.termination)
		assert(result[0].thread_task == task3)
		assert(result[0].event_details is None)
		assert(result[1].thread_task == task3)
		assert(result[2].thread_task == task2)
		assert(result[3].thread_task == task2)
		assert(result[4].thread_task == task1)
		assert(result[5].thread_task == task1)

		task4 = TestWThreadTracker.Task(storage)
		task4.thread_started = TestWThreadTracker.Task.exc_task
		task4.start()
		task4.start_event().wait()
		task4.stop()

		result = [x for x in storage]
		assert(len(result) == 8)
		assert(result[0].record_type == WTrackerEvents.exception)
		assert(result[0].thread_task == task4)
		assert(result[0].event_details is None)
		assert(result[1].thread_task == task4)
		assert(result[2].thread_task == task3)
		assert(result[3].thread_task == task3)
		assert(result[4].thread_task == task2)
		assert(result[5].thread_task == task2)
		assert(result[6].thread_task == task1)
		assert(result[7].thread_task == task1)

		task5 = TestWThreadTracker.ScheduleTask(storage)
		record1 = WScheduleRecordTracker(task5)
		record1.task_postponed()
		result = [x for x in storage]
		assert(len(result) == 9)
		assert(result[0].record_type == WTrackerEvents.wait)
		assert(result[0].thread_task == task5)
		assert(result[0].event_details is None)
		assert(result[1].thread_task == task4)
		assert(result[2].thread_task == task4)
		assert(result[3].thread_task == task3)
		assert(result[4].thread_task == task3)
		assert(result[5].thread_task == task2)
		assert(result[6].thread_task == task2)
		assert(result[7].thread_task == task1)
		assert(result[8].thread_task == task1)

		task6 = TestWThreadTracker.ScheduleTask(storage)
		record2 = WScheduleRecordTracker(task6)
		record2.task_dropped()
		result = [x for x in storage]
		assert(len(result) == 10)
		assert(result[0].record_type == WTrackerEvents.drop)
		assert(result[0].thread_task == task6)
		assert(result[0].event_details is None)
		assert(result[1].thread_task == task5)
		assert(result[2].thread_task == task4)
		assert(result[3].thread_task == task4)
		assert(result[4].thread_task == task3)
		assert(result[5].thread_task == task3)
		assert(result[6].thread_task == task2)
		assert(result[7].thread_task == task2)
		assert(result[8].thread_task == task1)
		assert(result[9].thread_task == task1)

		assert(storage.last_record(TestWThreadTracker.ScheduleTask(storage).uid()) is None)
		assert(isinstance(storage.last_record(task5.uid()), WSimpleTrackerStorage.Record) is True)
		assert(storage.last_record(task5.uid()).thread_task == task5)
		assert(storage.last_record(task5.uid(), WTrackerEvents.drop) is None)
		assert(storage.last_record(task5.uid(), WTrackerEvents.drop, WTrackerEvents.wait).thread_task == task5)

		storage = WSimpleTrackerStorage(records_limit=4)
		task1 = TestWThreadTracker.Task(storage)
		task1.start()
		task1.stop()

		task2 = TestWThreadTracker.Task(storage)
		task2.event_details = lambda x: '!!!'
		task2.start()
		task2.stop()

		task3 = TestWThreadTracker.Task(storage)
		task3.thread_started = task3.long_task
		task3.start()
		task3.start_event().wait()
		task3.stop()

		task4 = TestWThreadTracker.Task(storage)
		task4.thread_started = TestWThreadTracker.Task.exc_task
		task4.start()
		task4.start_event().wait()
		task4.stop()

		result = [x for x in storage]

		assert(len(result) == 4)
		assert(result[0].record_type == WTrackerEvents.exception)
		assert(result[0].thread_task == task4)
		assert(result[0].event_details is None)
		assert(result[1].thread_task == task4)
		assert(result[2].thread_task == task3)
		assert(result[3].thread_task == task3)

		storage = WSimpleTrackerStorage(
			record_start=False, record_stop=False, record_termination=False, record_exception=False,
			record_wait=False, record_drop=False
		)
		task1 = TestWThreadTracker.Task(storage)
		task1.start()
		task1.stop()

		task2 = TestWThreadTracker.Task(storage)
		task2.event_details = lambda x: '!!!'
		task2.start()
		task2.stop()

		task3 = TestWThreadTracker.Task(storage)
		task3.thread_started = task3.long_task
		task3.start()
		task3.start_event().wait()
		task3.stop()

		task4 = TestWThreadTracker.Task(storage)
		task4.thread_started = TestWThreadTracker.Task.exc_task
		task4.start()
		task4.start_event().wait()
		task4.stop()

		task5 = TestWThreadTracker.ScheduleTask(storage)
		record1 = WScheduleRecordTracker(task5)
		record1.task_postponed()

		task6 = TestWThreadTracker.ScheduleTask(storage)
		record2 = WScheduleRecordTracker(task6)
		record2.task_dropped()

		result = [x for x in storage]
		assert(len(result) == 0)

		pytest.raises(TypeError, storage._WSimpleTrackerStorage__store_record, 1)


class TestWScheduleRecordTracker:

	def test(self):
		storage = TestWThreadTracker.Storage()
		assert(storage.status() == (0, 0, 0, 0, 0, 0))

		task = TestWThreadTracker.ScheduleTask(tracker_storage=storage)
		record1 = WScheduleRecordTracker(task)
		assert(isinstance(record1, WScheduleRecordTracker))
		assert(isinstance(record1, WScheduleRecord))

		record1.task_postponed()
		assert (storage.status() == (0, 0, 0, 0, 1, 0))

		record1.task_dropped()
		assert (storage.status() == (0, 0, 0, 0, 1, 1))

		record2 = WScheduleRecordTracker(task, track_drop=False, track_wait=False)
		record2.task_postponed()
		record2.task_dropped()
		assert (storage.status() == (0, 0, 0, 0, 1, 1))
