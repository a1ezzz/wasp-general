# -*- coding: utf-8 -*-

import pytest
from datetime import datetime, timedelta
from decorator import decorator
from threading import Event

from wasp_general.datetime import utc_datetime
from wasp_general.task.thread import WThreadTask
from wasp_general.task.scheduler.proto import WScheduledTask, WTaskSchedule, WRunningScheduledTask
from wasp_general.task.scheduler.proto import WRunningTaskRegistryProto, WTaskSourceProto, WTaskSchedulerProto

from wasp_general.task.scheduler.scheduler import WSchedulerWatchdog, WRunningTaskRegistry, WPostponedTaskRegistry
from wasp_general.task.scheduler.scheduler import WTaskSourceRegistry, WTaskSchedulerService


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

	class DummyTask(WScheduledTask):

		__thread_polling_timeout__ = 0.01

		def __init__(self, wait_for=None):
			WScheduledTask.__init__(self)
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
		schedule = WTaskSchedule(task)

		registry = WRunningTaskRegistry()

		pytest.raises(TypeError, WSchedulerWatchdog.create, schedule, 1, 'thread1')

		dog = WSchedulerWatchdog.create(schedule, registry, 'thread1')
		assert(isinstance(dog, WSchedulerWatchdog) is True)
		assert(isinstance(dog, WThreadTask) is True)
		assert(dog.task_schedule() == schedule)
		assert(dog.registry() == registry)
		assert(dog.started_at() is None)
		assert(dog.running_task() is None)

		stop_event = Event()
		task = TestWSchedulerWatchdog.DummyTask(stop_event)
		schedule = WTaskSchedule(task)
		dog = TestWSchedulerWatchdog.HFWatchdog.create(schedule, registry, 'thread1')
		dog.start()
		dog.start_event().wait()
		task.started.wait()
		utc_dt = utc_datetime()
		assert((utc_dt - timedelta(seconds=10)) < dog.started_at() < utc_dt)
		running_task = dog.running_task()
		assert(isinstance(running_task, WRunningScheduledTask) is True)
		assert((utc_dt - timedelta(seconds=10)) < running_task.started_at() < utc_dt)
		assert(running_task.task_schedule() == schedule)
		pytest.raises(RuntimeError, dog.start)
		stop_event.set()
		dog.stop()

		buggy_schedule = WTaskSchedule(task)
		dog = WSchedulerWatchdog.create(buggy_schedule, registry, 'thread1')
		pytest.raises(RuntimeError, dog.thread_started)

		buggy_schedule = WTaskSchedule(task)
		buggy_schedule.task = lambda: None
		dog = WSchedulerWatchdog.create(buggy_schedule, registry, 'thread1')
		pytest.raises(RuntimeError, dog.start)

		buggy_schedule.task = lambda: 1
		dog = WSchedulerWatchdog.create(buggy_schedule, registry, 'thread1')
		pytest.raises(RuntimeError, dog.start)


class TestWRunningTaskRegistry:

	class HFRunningTaskRegistry(WRunningTaskRegistry):
		__thread_polling_timeout__ = TestWSchedulerWatchdog.HFWatchdog.__thread_polling_timeout__ / 2

	@repeat_fn(__test_repeat_count__)
	def test(self):
		registry = WRunningTaskRegistry()
		assert(isinstance(registry, WRunningTaskRegistry) is True)
		assert(isinstance(registry, WRunningTaskRegistryProto) is True)
		assert (isinstance(registry, WThreadTask) is True)
		assert(registry.watchdog_class() == WSchedulerWatchdog)

		registry = WRunningTaskRegistry(watchdog_cls=TestWSchedulerWatchdog.HFWatchdog)
		assert(registry.watchdog_class() == TestWSchedulerWatchdog.HFWatchdog)

		registry = TestWRunningTaskRegistry.HFRunningTaskRegistry()
		registry.start()
		registry.start_event().wait()
		assert(len(registry) == 0)
		assert(registry.running_tasks() == tuple())

		task1_stop_event = Event()
		task = TestWSchedulerWatchdog.DummyTask(task1_stop_event)
		schedule = WTaskSchedule(task)
		registry.exec(schedule)
		task.started.wait()
		assert(len(registry) == 1)
		running_task = registry.running_tasks()
		assert(isinstance(running_task, tuple) is True)
		assert(len(running_task) == 1)

		running_task = running_task[0]
		utc_dt = utc_datetime()
		assert(isinstance(running_task, WRunningScheduledTask) is True)
		assert((utc_dt - timedelta(seconds=10)) < running_task.started_at() < utc_dt)
		assert(running_task.task_schedule() == schedule)

		task1_stop_event.set()
		task.ready_event().wait()

		task1_stop_event = Event()
		task = TestWSchedulerWatchdog.DummyTask(task1_stop_event)
		schedule = WTaskSchedule(task)
		registry.exec(schedule)
		task.start_event().wait()
		task.started.wait()
		assert(len(registry) >= 1)
		registry.stop()


class TestWPostponedTaskRegistry:

	@repeat_fn(__test_repeat_count__)
	def test(self):
		registry = WPostponedTaskRegistry()
		assert(registry.maximum_tasks() is None)
		assert(registry.has_tasks() is False)
		assert(len(registry) == 0)

		drop_count = []

		def on_drop():
			drop_count.append(None)

		task = TestWSchedulerWatchdog.DummyTask()
		wait_schedule1 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.wait, on_drop=on_drop
		)
		wait_schedule2 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.wait, on_drop=on_drop
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

		registry = WPostponedTaskRegistry(maximum_tasks=0)
		assert(len(drop_count) == 0)
		assert(len(registry) == 0)

		registry.postpone(wait_schedule1)
		assert(len(drop_count) == 1)
		assert(len(registry) == 0)

		registry.postpone(wait_schedule2)
		assert(len(drop_count) == 2)
		assert(len(registry) == 0)

		drop_count.clear()
		registry = WPostponedTaskRegistry(maximum_tasks=1)
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
		registry = WPostponedTaskRegistry()
		assert(len(drop_count) == 0)
		assert(len(registry) == 0)

		drop_schedule = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.drop, on_drop=on_drop
		)
		registry.postpone(drop_schedule)
		assert(len(drop_count) == 1)
		assert(len(registry) == 0)

		drop_count.clear()
		postpone_first_group_1_schedule1 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_first, task_id='group1', on_drop=on_drop
		)

		postpone_first_group_1_schedule2 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_first, task_id='group1', on_drop=on_drop
		)

		postpone_first_group_2_schedule = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_first, task_id='group2', on_drop=on_drop
		)

		postpone_first_schedule1 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_first, on_drop=on_drop
		)

		postpone_first_schedule2 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_first, on_drop=on_drop
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

		wait_group_1 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.wait, task_id='group1', on_drop=on_drop
		)
		registry.postpone(wait_group_1)
		pytest.raises(RuntimeError, registry.postpone, postpone_first_group_1_schedule1)
		tasks = [x for x in registry]

		drop_count.clear()
		postpone_last_group_1_schedule1 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_last, task_id='group1', on_drop=on_drop
		)

		postpone_last_group_1_schedule2 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_last, task_id='group1', on_drop=on_drop
		)

		postpone_last_group_2_schedule = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_last, task_id='group2', on_drop=on_drop
		)

		postpone_last_schedule1 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_last, on_drop=on_drop
		)

		postpone_last_schedule2 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.postpone_last, on_drop=on_drop
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

		wait_group_1 = WTaskSchedule(
			task, policy=WTaskSchedule.PostponePolicy.wait, task_id='group1', on_drop=on_drop
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

		def has_tasks(self):
			if self.tasks is not None:
				result = tuple(self.tasks)
				self.tasks.clear()
				return result

		def next_start(self):
			if len(self.tasks) > 0:
				return utc_datetime()

	@repeat_fn(__test_repeat_count__)
	def test(self):
		registry = WTaskSourceRegistry()
		assert(registry.check() is None)
		assert(registry.task_sources() == tuple())

		task_source1 = TestWTaskSourceRegistry.TaskSource()
		registry.add_source(task_source1)
		assert(registry.check() is None)
		assert(registry.task_sources() == (task_source1, ))

		task1 = WTaskSchedule(TestWSchedulerWatchdog.DummyTask())
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
		task2 = WTaskSchedule(TestWSchedulerWatchdog.DummyTask())
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


class TestWTaskSchedulerService:

	__wait_task_timeout__ = 0.001

	class HFSchedulerService(WTaskSchedulerService):
		__thread_polling_timeout__ = (
			TestWRunningTaskRegistry.HFRunningTaskRegistry.__thread_polling_timeout__ / 2
		)

	class DummyTask(TestWSchedulerWatchdog.DummyTask):

		__result__ = 0
		__dropped__ = 0

		def __init__(self, wait_for=None):
			TestWSchedulerWatchdog.DummyTask.__init__(self, wait_for=wait_for)
			self.drop_event = Event()

		def thread_started(self):
			TestWSchedulerWatchdog.DummyTask.thread_started(self)
			TestWTaskSchedulerService.DummyTask.__result__ += 1

		def on_drop(self):
			TestWTaskSchedulerService.DummyTask.__dropped__ += 1
			self.drop_event.set()

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
				events[0].wait(TestWTaskSchedulerService.__wait_task_timeout__)

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
				tasks[0].ready_event().wait(TestWTaskSchedulerService.__wait_task_timeout__)

	@repeat_fn(__test_repeat_count__)
	def test(self):
		TestWTaskSchedulerService.DummyTask.__result__ = 0
		TestWTaskSchedulerService.DummyTask.__dropped__ = 0

		service = WTaskSchedulerService()
		assert(isinstance(service, WTaskSchedulerService) is True)
		assert(isinstance(service, WTaskSchedulerProto) is True)
		assert(isinstance(service, WThreadTask) is True)
		assert(service.maximum_running_tasks() > 0)
		assert(service.maximum_running_tasks() == WTaskSchedulerService.__default_maximum_running_tasks__)
		assert(service.maximum_postponed_tasks() is None)
		assert(service.task_sources() == tuple())

		service = WTaskSchedulerService(maximum_postponed_tasks=2, maximum_running_tasks=1)
		assert(service.maximum_running_tasks() == 1)
		assert(service.maximum_postponed_tasks() == 2)

		pytest.raises(
			ValueError, WTaskSchedulerService, maximum_postponed_tasks=1,
			postponed_tasks_registry=WPostponedTaskRegistry()
		)

		service = TestWTaskSchedulerService.HFSchedulerService(
			maximum_running_tasks=2, running_tasks_registry=TestWRunningTaskRegistry.HFRunningTaskRegistry(
				watchdog_cls=TestWSchedulerWatchdog.HFWatchdog
			)
		)

		task_source1 = TestWTaskSourceRegistry.TaskSource()
		service.add_task_source(task_source1)
		assert(service.task_sources() == (task_source1, ))

		service.start()
		service.start_event().wait()

		assert (TestWTaskSchedulerService.DummyTask.__result__ == 0)
		assert(TestWTaskSchedulerService.DummyTask.__dropped__ == 0)
		task1 = TestWTaskSchedulerService.DummyTask()
		task_source1.tasks.append(WTaskSchedule(task1, on_drop=task1.on_drop))
		service.update()

		task1.start_event().wait()
		TestWTaskSchedulerService.wait_for_tasks(task1)

		assert(TestWTaskSchedulerService.DummyTask.__result__ == 1)
		assert(TestWTaskSchedulerService.DummyTask.__dropped__ == 0)

		task_source2 = TestWTaskSourceRegistry.TaskSource()
		service.add_task_source(task_source2)
		result = service.task_sources()
		assert(result == (task_source1, task_source2) or result == (task_source2, task_source1))

		long_run_task = TestWTaskSchedulerService.DummyTask(Event())

		group1_task1_stop_event = Event()
		group1_task1 = TestWTaskSchedulerService.DummyTask(group1_task1_stop_event)
		group1_task2_stop_event = Event()
		group1_task2 = TestWTaskSchedulerService.DummyTask(group1_task2_stop_event)
		task_source1.tasks.append(WTaskSchedule(long_run_task, on_drop=long_run_task.on_drop))
		task_source1.tasks.append(
			WTaskSchedule(
				group1_task1, on_drop=group1_task1.on_drop, task_id='group1',
				policy=WTaskSchedule.PostponePolicy.drop
			)
		)
		task_source2.tasks.append(
			WTaskSchedule(
				group1_task2, on_drop=group1_task2.on_drop, task_id='group1',
				policy=WTaskSchedule.PostponePolicy.drop
			)
		)

		service.update()

		TestWTaskSchedulerService.wait_for_events(group1_task1.start_event(), group1_task2.start_event())
		running_tasks = service.running_tasks()
		for task in running_tasks:
			assert(isinstance(task, WRunningScheduledTask) is True)
			task = task.task_schedule().task()
			assert(task in (group1_task1, group1_task2, long_run_task))

		TestWTaskSchedulerService.wait_for_tasks(group1_task1, group1_task2)
		group1_task1_stop_event.set()
		group1_task2_stop_event.set()
		TestWTaskSchedulerService.wait_for_tasks(group1_task1, group1_task2, every=True)
		assert(TestWTaskSchedulerService.DummyTask.__result__ == 2)
		assert(TestWTaskSchedulerService.DummyTask.__dropped__ == 1)

		group1_task1.stop()
		group1_task2.stop()

		group1_task1_stop_event = Event()
		group1_task2_stop_event = Event()

		group1_task1 = TestWTaskSchedulerService.DummyTask(group1_task1_stop_event)
		group1_task2 = TestWTaskSchedulerService.DummyTask(group1_task2_stop_event)

		task_source1.tasks.append(
			WTaskSchedule(
				group1_task1, on_drop=group1_task1.on_drop, task_id='group1',
				policy=WTaskSchedule.PostponePolicy.wait
			)
		)
		task_source2.tasks.append(
			WTaskSchedule(
				group1_task2, on_drop=group1_task2.on_drop, task_id='group1',
				policy=WTaskSchedule.PostponePolicy.wait
			)
		)

		service.update()

		group1_task1_stop_event.set()
		group1_task2_stop_event.set()
		TestWTaskSchedulerService.wait_for_tasks(group1_task1, group1_task2, every=True)
		assert(TestWTaskSchedulerService.DummyTask.__result__ == 4)
		assert(TestWTaskSchedulerService.DummyTask.__dropped__ == 1)

		service.stop()
		TestWTaskSchedulerService.wait_for_tasks(long_run_task)
