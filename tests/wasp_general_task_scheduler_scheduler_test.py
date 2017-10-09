# -*- coding: utf-8 -*-

import pytest
from datetime import datetime, timedelta
from decorator import decorator
from threading import Event

from wasp_general.datetime import utc_datetime
from wasp_general.task.thread import WThreadTask
from wasp_general.task.scheduler.proto import WScheduleTask, WScheduleRecord
from wasp_general.task.scheduler.proto import WRunningRecordRegistryProto, WTaskSourceProto, WSchedulerServiceProto

from wasp_general.task.scheduler.scheduler import WSchedulerWatchdog, WRunningRecordRegistry, WPostponedRecordRegistry
from wasp_general.task.scheduler.scheduler import WTaskSourceRegistry, WSchedulerService


def repeat_fn(count):
	def fl_decorator(decorated_fn):
		def sl_decorator(original_fn, *args, **kwargs):
			for i in range(count):
				original_fn(*args, **kwargs)
		return decorator(sl_decorator)(decorated_fn)
	return fl_decorator


__test_repeat_count__ = 25


class TestWSchedulerWatchdog:

	class HFWatchdog(WSchedulerWatchdog):
		__thread_polling_timeout__ = 0.01

	class DummyTask(WScheduleTask):

		__thread_polling_timeout__ = 0.01

		def __init__(self, wait_for=None):
			WScheduleTask.__init__(self)
			self.started = Event()
			self.wait_for = wait_for

		def thread_started(self):
			self.started.set()
			if self.wait_for is None:
				return

			while self.wait_for.is_set() is False and self.stop_event().is_set() is False:
				self.wait_for.wait(TestWSchedulerWatchdog.DummyTask.__thread_polling_timeout__)

		def thread_stopped(self):
			self.started.clear()

	@repeat_fn(__test_repeat_count__)
	def test(self):
		task = TestWSchedulerWatchdog.DummyTask()
		schedule = WScheduleRecord(task)

		registry = WRunningRecordRegistry()

		pytest.raises(TypeError, WSchedulerWatchdog.create, schedule, 1)

		dog = WSchedulerWatchdog.create(schedule, registry)
		assert(isinstance(dog, WSchedulerWatchdog) is True)
		assert(isinstance(dog, WThreadTask) is True)
		assert(dog.record() == schedule)
		assert(dog.registry() == registry)

		stop_event = Event()
		task = TestWSchedulerWatchdog.DummyTask(stop_event)
		schedule = WScheduleRecord(task)
		dog = TestWSchedulerWatchdog.HFWatchdog.create(schedule, registry)
		dog.start()
		dog.start_event().wait()
		task.started.wait()
		assert(dog.record() == schedule)
		pytest.raises(RuntimeError, dog.start)
		stop_event.set()
		dog.stop()

		buggy_schedule = WScheduleRecord(task)
		dog = WSchedulerWatchdog.create(buggy_schedule, registry)
		pytest.raises(RuntimeError, dog.thread_started)

		buggy_schedule = WScheduleRecord(task)

		class A:
			def uid(self):
				return 1

		buggy_schedule.task = lambda: A()
		dog = WSchedulerWatchdog.create(buggy_schedule, registry)
		pytest.raises(RuntimeError, dog.start)


class TestWRunningRecordRegistry:

	class HFRunningTaskRegistry(WRunningRecordRegistry):
		__thread_polling_timeout__ = TestWSchedulerWatchdog.HFWatchdog.__thread_polling_timeout__ / 2

	@repeat_fn(__test_repeat_count__)
	def test(self):
		registry = WRunningRecordRegistry(thread_name_suffix='!')
		assert(isinstance(registry, WRunningRecordRegistry) is True)
		assert(isinstance(registry, WRunningRecordRegistryProto) is True)
		assert (isinstance(registry, WThreadTask) is True)
		assert(registry.watchdog_class() == WSchedulerWatchdog)

		registry = WRunningRecordRegistry(watchdog_cls=TestWSchedulerWatchdog.HFWatchdog)
		assert(registry.watchdog_class() == TestWSchedulerWatchdog.HFWatchdog)

		registry = TestWRunningRecordRegistry.HFRunningTaskRegistry()
		registry.start()
		registry.start_event().wait()
		assert(len(registry) == 0)
		assert(registry.running_records() == tuple())

		task1_stop_event = Event()
		task = TestWSchedulerWatchdog.DummyTask(task1_stop_event)
		schedule = WScheduleRecord(task)
		registry.exec(schedule)
		task.started.wait()
		assert(len(registry) == 1)
		running_task = registry.running_records()
		assert(isinstance(running_task, tuple) is True)
		assert(len(running_task) == 1)

		running_task = running_task[0]
		assert(running_task == schedule)

		task1_stop_event.set()
		task.ready_event().wait()

		task1_stop_event = Event()
		task = TestWSchedulerWatchdog.DummyTask(task1_stop_event)
		schedule = WScheduleRecord(task)
		registry.exec(schedule)
		task.start_event().wait()
		task.started.wait()
		assert(len(registry) >= 1)
		registry.stop()


class TestWPostponedRecordRegistry:

	@repeat_fn(__test_repeat_count__)
	def test(self):
		registry = WPostponedRecordRegistry()
		assert(registry.maximum_records() is None)
		assert(registry.has_records() is False)
		assert(len(registry) == 0)

		drop_count = []

		def on_drop():
			drop_count.append(None)

		task = TestWSchedulerWatchdog.DummyTask()
		wait_schedule1 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.wait, on_drop=on_drop
		)
		wait_schedule2 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.wait, on_drop=on_drop
		)

		assert(len(drop_count) == 0)
		assert(len(registry) == 0)

		registry.postpone(wait_schedule1)
		assert(len(drop_count) == 0)
		assert(len(registry) == 1)

		registry.postpone(wait_schedule2)
		assert(len(drop_count) == 0)
		assert(len(registry) == 2)

		tasks = [x for x in registry]
		assert(len(registry) == 0)
		assert(wait_schedule1 in tasks)
		assert(wait_schedule2 in tasks)

		registry = WPostponedRecordRegistry(maximum_records=0)
		assert(len(drop_count) == 0)
		assert(len(registry) == 0)

		registry.postpone(wait_schedule1)
		assert(len(drop_count) == 1)
		assert(len(registry) == 0)

		registry.postpone(wait_schedule2)
		assert(len(drop_count) == 2)
		assert(len(registry) == 0)

		drop_count.clear()
		registry = WPostponedRecordRegistry(maximum_records=1)
		assert(len(drop_count) == 0)
		assert(len(registry) == 0)

		registry.postpone(wait_schedule1)
		assert(len(drop_count) == 0)
		assert(len(registry) == 1)

		registry.postpone(wait_schedule2)
		assert(len(drop_count) == 1)
		assert(len(registry) == 1)

		tasks = [x for x in registry]
		assert(len(registry) == 0)
		assert(wait_schedule1 in tasks)
		assert(wait_schedule2 not in tasks)

		drop_count.clear()
		registry = WPostponedRecordRegistry()
		assert(len(drop_count) == 0)
		assert(len(registry) == 0)

		drop_schedule = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.drop, on_drop=on_drop
		)
		registry.postpone(drop_schedule)
		assert(len(drop_count) == 1)
		assert(len(registry) == 0)

		drop_count.clear()
		postpone_first_group_1_schedule1 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_first, task_group_id='group1', on_drop=on_drop
		)

		postpone_first_group_1_schedule2 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_first, task_group_id='group1', on_drop=on_drop
		)

		postpone_first_group_2_schedule = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_first, task_group_id='group2', on_drop=on_drop
		)

		postpone_first_schedule1 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_first, on_drop=on_drop
		)

		postpone_first_schedule2 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_first, on_drop=on_drop
		)

		registry.postpone(postpone_first_group_1_schedule1)
		assert(len(drop_count) == 0)
		assert(len(registry) == 1)

		registry.postpone(postpone_first_group_1_schedule2)
		assert(len(drop_count) == 1)
		assert(len(registry) == 1)

		registry.postpone(postpone_first_group_2_schedule)
		assert(len(drop_count) == 1)
		assert(len(registry) == 2)

		registry.postpone(postpone_first_schedule1)
		assert(len(drop_count) == 1)
		assert(len(registry) == 3)

		registry.postpone(postpone_first_schedule2)
		assert(len(drop_count) == 1)
		assert(len(registry) == 4)

		tasks = [x for x in registry]
		assert(len(registry) == 0)
		assert(postpone_first_group_1_schedule1 in tasks)
		assert(postpone_first_group_2_schedule in tasks)
		assert(postpone_first_schedule1 in tasks)
		assert(postpone_first_schedule2 in tasks)

		wait_group_1 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.wait, task_group_id='group1', on_drop=on_drop
		)
		registry.postpone(wait_group_1)
		pytest.raises(RuntimeError, registry.postpone, postpone_first_group_1_schedule1)
		tasks = [x for x in registry]

		drop_count.clear()
		postpone_last_group_1_schedule1 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_last, task_group_id='group1', on_drop=on_drop
		)

		postpone_last_group_1_schedule2 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_last, task_group_id='group1', on_drop=on_drop
		)

		postpone_last_group_2_schedule = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_last, task_group_id='group2', on_drop=on_drop
		)

		postpone_last_schedule1 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_last, on_drop=on_drop
		)

		postpone_last_schedule2 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.postpone_last, on_drop=on_drop
		)
		registry.postpone(postpone_last_group_1_schedule1)
		assert(len(drop_count) == 0)
		assert(len(registry) == 1)

		registry.postpone(postpone_last_group_1_schedule2)
		assert(len(drop_count) == 1)
		assert(len(registry) == 1)

		registry.postpone(postpone_last_group_2_schedule)
		assert(len(drop_count) == 1)
		assert(len(registry) == 2)

		registry.postpone(postpone_last_schedule1)
		assert(len(drop_count) == 1)
		assert(len(registry) == 3)

		registry.postpone(postpone_last_schedule2)
		assert(len(drop_count) == 1)
		assert(len(registry) == 4)

		tasks = [x for x in registry]
		assert(len(registry) == 0)
		assert(postpone_last_group_1_schedule2 in tasks)
		assert(postpone_last_group_2_schedule in tasks)
		assert(postpone_last_schedule1 in tasks)
		assert(postpone_last_schedule2 in tasks)

		wait_group_1 = WScheduleRecord(
			task, policy=WScheduleRecord.PostponePolicy.wait, task_group_id='group1', on_drop=on_drop
		)
		registry.postpone(wait_group_1)
		pytest.raises(RuntimeError, registry.postpone, postpone_last_group_1_schedule1)

		wait_group_1.policy = lambda: None
		pytest.raises(RuntimeError, registry.postpone, wait_group_1)


class TestWTaskSourceRegistry:

	class TaskSource(WTaskSourceProto):

		def __init__(self):
			WTaskSourceProto.__init__(self)
			self.tasks = []

		def has_records(self):
			if self.tasks is not None:
				result = tuple(self.tasks)
				self.tasks.clear()
				return result

		def next_start(self):
			if len(self.tasks) > 0:
				return utc_datetime()

		def tasks_planned(self):
			return len(self.tasks)

		def scheduler_service(self):
			return None

	@repeat_fn(__test_repeat_count__)
	def test(self):
		registry = WTaskSourceRegistry()
		assert(registry.check() is None)
		assert(registry.task_sources() == tuple())

		task_source1 = TestWTaskSourceRegistry.TaskSource()
		registry.add_source(task_source1)
		assert(registry.check() is None)
		assert(registry.task_sources() == (task_source1, ))

		task1 = WScheduleRecord(TestWSchedulerWatchdog.DummyTask())
		task_source1.tasks.append(task1)
		registry.update()
		assert(registry.check() == (task1, ))
		assert(registry.check() is None)

		task_source2 = TestWTaskSourceRegistry.TaskSource()
		registry.add_source(task_source2)
		assert(registry.check() is None)
		result = registry.task_sources()
		assert(result == (task_source1, task_source2) or result == (task_source2, task_source1))

		task_source1.tasks.append(task1)
		task2 = WScheduleRecord(TestWSchedulerWatchdog.DummyTask())
		task_source2.tasks.append(task2)
		assert(registry.check() is None)

		registry.update(task_source=task_source2)
		assert(registry.check() == (task2, ))
		assert(registry.check() == (task1, ))

		utc_now = utc_datetime()
		task_source1.tasks.append(task1)
		task_source2.tasks.append(task2)
		task_source2.next_start = lambda: utc_now
		registry.update()
		assert(registry.check() == (task2, ))

		task_source1.next_start = lambda: utc_now
		task_source2.tasks.append(task2)
		registry.update()
		result = registry.check()
		assert(result == (task1, task2) or result == (task2, task1))

		task_source1.next_start = lambda: datetime.now()
		pytest.raises(ValueError, registry.update)


class TestWSchedulerService:

	__wait_task_timeout__ = 0.001

	class HFSchedulerService(WSchedulerService):
		__thread_polling_timeout__ = (
			TestWRunningRecordRegistry.HFRunningTaskRegistry.__thread_polling_timeout__ / 2
		)

	class DummyTask(TestWSchedulerWatchdog.DummyTask):

		__result__ = 0
		__dropped__ = 0
		__waited__ = 0

		def __init__(self, wait_for=None):
			TestWSchedulerWatchdog.DummyTask.__init__(self, wait_for=wait_for)
			self.drop_event = Event()
			self.wait_event = Event()

		def thread_started(self):
			TestWSchedulerWatchdog.DummyTask.thread_started(self)
			TestWSchedulerService.DummyTask.__result__ += 1

		def on_drop(self):
			TestWSchedulerService.DummyTask.__dropped__ += 1
			self.drop_event.set()

		def on_wait(self):
			TestWSchedulerService.DummyTask.__waited__ += 1
			self.wait_event.set()

	def wait_for_events(*events, every=False):
		events = list(events)
		while len(events) > 0:

			for i in range(len(events)):
				event = events[i]
				if event.is_set() is True:
					if every is False:
						return
					events.pop(i)
					break

			if len(events) > 0:
				events[0].wait(TestWSchedulerService.__wait_task_timeout__)

	@staticmethod
	def wait_for_tasks(*tasks, every=False):
		tasks = list(tasks)
		while len(tasks) > 0:

			for i in range(len(tasks)):
				task = tasks[i]
				if task.check_events() is True or task.drop_event.is_set() is True:
					if every is False:
						return
					tasks.pop(i)
					break

			if len(tasks) > 0:
				tasks[0].ready_event().wait(TestWSchedulerService.__wait_task_timeout__)

	@repeat_fn(__test_repeat_count__)
	def test(self):
		TestWSchedulerService.DummyTask.__result__ = 0
		TestWSchedulerService.DummyTask.__dropped__ = 0
		TestWSchedulerService.DummyTask.__waited__ = 0

		service = WSchedulerService(thread_name_suffix='!')
		assert(isinstance(service, WSchedulerService) is True)
		assert(isinstance(service, WSchedulerServiceProto) is True)
		assert(isinstance(service, WThreadTask) is True)
		assert(service.maximum_running_records() > 0)
		assert(service.maximum_running_records() == WSchedulerService.__default_maximum_running_records__)
		assert(service.maximum_postponed_records() is None)
		assert(service.task_sources() == tuple())

		service = WSchedulerService(maximum_postponed_records=2, maximum_running_records=1)
		assert(service.maximum_running_records() == 1)
		assert(service.maximum_postponed_records() == 2)

		pytest.raises(
			ValueError, WSchedulerService, maximum_postponed_records=1,
			postponed_record_registry=WPostponedRecordRegistry()
		)

		service = TestWSchedulerService.HFSchedulerService(
			maximum_running_records=2,
			running_record_registry=TestWRunningRecordRegistry.HFRunningTaskRegistry(
				watchdog_cls=TestWSchedulerWatchdog.HFWatchdog
			)
		)

		task_source1 = TestWTaskSourceRegistry.TaskSource()
		service.add_task_source(task_source1)
		assert(service.task_sources() == (task_source1, ))

		service.start()
		service.start_event().wait()

		assert (TestWSchedulerService.DummyTask.__result__ == 0)
		assert(TestWSchedulerService.DummyTask.__dropped__ == 0)
		assert(TestWSchedulerService.DummyTask.__waited__ == 0)
		task1 = TestWSchedulerService.DummyTask()
		task_source1.tasks.append(WScheduleRecord(task1, on_drop=task1.on_drop, on_wait=task1.on_wait))
		service.update()

		task1.start_event().wait()

		TestWSchedulerService.wait_for_tasks(task1)

		assert(TestWSchedulerService.DummyTask.__result__ == 1)
		assert(TestWSchedulerService.DummyTask.__dropped__ == 0)
		assert(TestWSchedulerService.DummyTask.__waited__ == 0)

		task_source2 = TestWTaskSourceRegistry.TaskSource()
		service.add_task_source(task_source2)
		result = service.task_sources()
		assert(result == (task_source1, task_source2) or result == (task_source2, task_source1))

		long_run_task = TestWSchedulerService.DummyTask(Event())

		group1_task1_stop_event = Event()
		group1_task1 = TestWSchedulerService.DummyTask(group1_task1_stop_event)
		group1_task2_stop_event = Event()
		group1_task2 = TestWSchedulerService.DummyTask(group1_task2_stop_event)
		task_source1.tasks.append(WScheduleRecord(
			long_run_task, on_drop=long_run_task.on_drop, on_wait=long_run_task.on_wait
		))
		task_source1.tasks.append(
			WScheduleRecord(
				group1_task1, on_drop=group1_task1.on_drop, on_wait=group1_task1.on_wait,
				task_group_id='group1', policy=WScheduleRecord.PostponePolicy.drop
			)
		)
		task_source2.tasks.append(
			WScheduleRecord(
				group1_task2, on_drop=group1_task2.on_drop, on_wait=group1_task2.on_wait,
				task_group_id='group1', policy=WScheduleRecord.PostponePolicy.drop
			)
		)

		service.update()

		TestWSchedulerService.wait_for_events(group1_task1.start_event(), group1_task2.start_event())

		result = service.records_status()
		assert(result == (1, 0) or result == (2, 0))

		running_tasks = service.running_records()
		for record in running_tasks:
			task = record.task()
			assert(task in (group1_task1, group1_task2, long_run_task))

		TestWSchedulerService.wait_for_tasks(group1_task1, group1_task2)

		group1_task1_stop_event.set()
		group1_task2_stop_event.set()
		TestWSchedulerService.wait_for_tasks(group1_task1, group1_task2, every=True)
		assert(TestWSchedulerService.DummyTask.__result__ == 2)
		assert(TestWSchedulerService.DummyTask.__dropped__ == 1)
		assert(TestWSchedulerService.DummyTask.__waited__ == 0)

		group1_task1.stop()
		group1_task2.stop()

		group1_task1_stop_event = Event()
		group1_task2_stop_event = Event()

		group1_task1 = TestWSchedulerService.DummyTask(group1_task1_stop_event)
		group1_task2 = TestWSchedulerService.DummyTask(group1_task2_stop_event)

		task_source1.tasks.append(
			WScheduleRecord(
				group1_task1, on_drop=group1_task1.on_drop, on_wait=group1_task1.on_wait,
				task_group_id='group1', policy=WScheduleRecord.PostponePolicy.wait
			)
		)
		task_source2.tasks.append(
			WScheduleRecord(
				group1_task2, on_drop=group1_task2.on_drop, on_wait=group1_task2.on_wait,
				task_group_id='group1', policy=WScheduleRecord.PostponePolicy.wait
			)
		)

		service.update()

		result = service.records_status()

		group1_task1_stop_event.set()
		group1_task2_stop_event.set()
		TestWSchedulerService.wait_for_tasks(group1_task1, group1_task2, every=True)

		group1_task1.wait_event.wait()
		group1_task2.wait_event.wait()

		assert(TestWSchedulerService.DummyTask.__result__ == 4)
		assert(TestWSchedulerService.DummyTask.__dropped__ == 1)
		assert(TestWSchedulerService.DummyTask.__waited__ == 2)

		service.stop()
		TestWSchedulerService.wait_for_tasks(long_run_task)
