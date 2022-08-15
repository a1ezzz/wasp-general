
import pytest
import datetime
from time import sleep

from wasp_general.api.signals import WSignalSource
from wasp_general.api.task.proto import WScheduleRecordProto, WTaskProto, WScheduledTaskPostponePolicy
from wasp_general.api.task.proto import WScheduledTaskResult, WTaskResult, WSchedulerProto, WScheduleSourceProto

from wasp_general.platform import WPlatformThreadEvent

from wasp_general.api.task.scheduler import WScheduleRecord, WSchedulerThreadExecutor, WSchedulerPostponeQueue
from wasp_general.api.task.scheduler import WScheduler


class TaskExample(WTaskProto):

    def __init__(self, long_running=False):
        WTaskProto.__init__(self)
        self.__long_running = long_running
        self.__event = WPlatformThreadEvent()

    def is_stopped(self):
        return self.__event.is_set()

    def stop(self):
        self.__event.set()

    def start(self):
        self.__event.clear()
        if self.__long_running:
            self.__event.wait()


class ExceptionalRecord(WScheduleRecord):

    def __init__(self):
        WScheduleRecord.__init__(self, TaskExample())

    def task(self):
        raise ValueError('!')


class TestWScheduleRecord:

    def test(self):
        task1 = TaskExample()
        record = WScheduleRecord(task1)
        assert(isinstance(record, WScheduleRecord) is True)
        assert(isinstance(record, WScheduleRecordProto) is True)
        assert(record.task() is task1)
        assert(record.group_id() is None)
        assert(record.ttl() is None)
        assert(record.simultaneous_policy() == 0)
        assert(record.postpone_policy() == WScheduledTaskPostponePolicy.wait)

        task2 = TaskExample()
        record = WScheduleRecord(
            task2, group_id='task_group', ttl=10, simultaneous_policy=2,
            postpone_policy=WScheduledTaskPostponePolicy.drop
        )

        assert(record.task() is task2)
        assert(record.group_id() == 'task_group')
        assert(record.ttl() == 10)
        assert(record.simultaneous_policy() == 2)
        assert(record.postpone_policy() == WScheduledTaskPostponePolicy.drop)


class TestWSchedulerThreadExecutor:

    @pytest.fixture
    def executor_fixture(self, wasp_signals):
        executor = WSchedulerThreadExecutor(wasp_signals.loop)
        executor.callback(WSchedulerThreadExecutor.record_processed, wasp_signals)
        executor.callback(WSchedulerThreadExecutor.task_started, wasp_signals)
        executor.callback(WSchedulerThreadExecutor.task_completed, wasp_signals)
        executor.callback(WSchedulerThreadExecutor.task_stopped, wasp_signals)

        task = TaskExample(long_running=True)
        record = WScheduleRecord(task)

        return wasp_signals, executor, task, record

    def test(self, wasp_signals):
        executor = WSchedulerThreadExecutor(wasp_signals.loop)
        assert(isinstance(executor, WSchedulerThreadExecutor) is True)
        assert(isinstance(executor, WSignalSource) is True)
        assert(executor.running_records() == tuple())
        pytest.raises(RuntimeError, executor.stop_record, WScheduleRecord(TaskExample()))  # unable to stop since
        # original loop is running (executor is not thread safe)

    def test_execution(self, executor_fixture):
        wasp_signals, executor, task, record = executor_fixture

        executor.execute(record)
        wasp_signals.wait(WSchedulerThreadExecutor.task_started)
        assert(wasp_signals.dump() == {
            WSchedulerThreadExecutor.task_started: (record, ),
        })

        wasp_signals.clear()
        task.stop()
        wasp_signals.wait(WSchedulerThreadExecutor.record_processed)
        assert(wasp_signals.dump() == {
            WSchedulerThreadExecutor.task_completed: (WScheduledTaskResult(record, WTaskResult()), ),
            WSchedulerThreadExecutor.task_stopped: (record, ),
            WSchedulerThreadExecutor.record_processed: (record, )
        })

    @pytest.mark.parametrize('runs', range(30))  # there was some concurrency issue with
    # the :meth:`.WSchedulerThreadExecutor.stop_record` method call
    def test_stop(self, executor_fixture, runs):
        wasp_signals, executor, task, record = executor_fixture

        executor.execute(record)
        wasp_signals.wait(WSchedulerThreadExecutor.task_started)

        wasp_signals.stop()
        wasp_signals.clear()
        assert(wasp_signals.loop.is_started() is False)

        executor.stop_record(record)
        assert(task.is_stopped() is True)


class TestWSchedulerPostponeQueue:

    @pytest.fixture
    def queue_fixture(self, wasp_signals):
        postpone_queue = WSchedulerPostponeQueue()
        postpone_queue.callback(WSchedulerPostponeQueue.task_dropped, wasp_signals)
        postpone_queue.callback(WSchedulerPostponeQueue.task_postponed, wasp_signals)
        postpone_queue.callback(WSchedulerPostponeQueue.task_expired, wasp_signals)

        return wasp_signals, postpone_queue

    def test(self, wasp_signals):
        postpone_queue = WSchedulerPostponeQueue()
        assert(isinstance(postpone_queue, WSchedulerPostponeQueue) is True)
        assert(isinstance(postpone_queue, WSignalSource) is True)

    @pytest.mark.parametrize(
        "policy, group_name1, group_name2", [
            (WScheduledTaskPostponePolicy.wait, None, None),
            (WScheduledTaskPostponePolicy.wait, 'group1', 'group2'),
            (WScheduledTaskPostponePolicy.keep_last, None, None),
            (WScheduledTaskPostponePolicy.keep_last, 'group1', 'group2'),
            (WScheduledTaskPostponePolicy.keep_first, None, None),
            (WScheduledTaskPostponePolicy.keep_first, 'group1', 'group2'),
        ]
    )
    def test_groups(self, queue_fixture, policy, group_name1, group_name2):
        wasp_signals, postpone_queue = queue_fixture
        task = TaskExample()

        record1 = WScheduleRecord(task, postpone_policy=policy, group_id=group_name1)
        postpone_queue.postpone(record1)
        wasp_signals.wait(WSchedulerPostponeQueue.task_postponed)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_postponed: (record1, )
        })

        wasp_signals.clear()
        record2 = WScheduleRecord(task, postpone_policy=policy, group_id=group_name2)
        postpone_queue.postpone(record2)
        wasp_signals.wait(WSchedulerPostponeQueue.task_postponed)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_postponed: (record2, )
        })

        assert(postpone_queue.next_record() is record1)
        assert(postpone_queue.next_record() is record2)
        assert(postpone_queue.next_record() is None)

    def test_ttl(self, queue_fixture):
        wasp_signals, postpone_queue = queue_fixture
        task = TaskExample()

        record1 = WScheduleRecord(task, ttl=(datetime.datetime.utcnow().timestamp() + 1000))  # this one is kept
        record2 = WScheduleRecord(task, ttl=(datetime.datetime.utcnow().timestamp() - 10))  # this one is dropped
        postpone_queue.postpone(record1)
        postpone_queue.postpone(record2)
        wasp_signals.wait(WSchedulerPostponeQueue.task_postponed)
        wasp_signals.wait(WSchedulerPostponeQueue.task_expired)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_postponed: (record1, ),
            WSchedulerPostponeQueue.task_expired: (record2, )
        })
        assert(postpone_queue.next_record() is record1)
        assert(postpone_queue.next_record() is None)

    def test_ttl_next_record(self, queue_fixture):
        wasp_signals, postpone_queue = queue_fixture
        task = TaskExample()
        timedelta = 0.5

        record = WScheduleRecord(task, ttl=(datetime.datetime.utcnow().timestamp() + timedelta))  # this one is kept
        postpone_queue.postpone(record)
        wasp_signals.wait(WSchedulerPostponeQueue.task_postponed)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_postponed: (record, ),
        })
        wasp_signals.clear()

        sleep(2 * timedelta)
        assert(postpone_queue.next_record() is None)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_expired: (record, ),
        })

    def test_drop_policy(self, queue_fixture):
        wasp_signals, postpone_queue = queue_fixture
        task = TaskExample()

        record = WScheduleRecord(task, postpone_policy=WScheduledTaskPostponePolicy.drop)
        postpone_queue.postpone(record)
        wasp_signals.wait(WSchedulerPostponeQueue.task_dropped)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_dropped: (record, ),
        })
        assert(postpone_queue.next_record() is None)

    def test_keep_last(self, queue_fixture):
        wasp_signals, postpone_queue = queue_fixture
        task = TaskExample()

        record1 = WScheduleRecord(task, group_id='group')
        record2 = WScheduleRecord(task, group_id='group')
        record3 = WScheduleRecord(task, group_id='group', postpone_policy=WScheduledTaskPostponePolicy.keep_last)
        # the last policy wins
        record4 = WScheduleRecord(task, ttl=1)  # this record is for just to be sure, that others are processed
        postpone_queue.postpone(record1)
        postpone_queue.postpone(record2)
        postpone_queue.postpone(record3)
        postpone_queue.postpone(record4)
        wasp_signals.wait(WSchedulerPostponeQueue.task_expired)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_postponed: (record1, record2, record3),  # at first, record1 and record2
            # is postponed
            WSchedulerPostponeQueue.task_dropped: (record1, record2, ),  # but when record3 is arrived, record1 so
            # as record2 are dropped
            WSchedulerPostponeQueue.task_expired: (record4, )
        })
        assert(postpone_queue.next_record() is record3)
        assert(postpone_queue.next_record() is None)

    def test_keep_first(self, queue_fixture):
        wasp_signals, postpone_queue = queue_fixture
        task = TaskExample()

        record1 = WScheduleRecord(task, group_id='group')
        record2 = WScheduleRecord(task, group_id='group')
        record3 = WScheduleRecord(task, group_id='group', postpone_policy=WScheduledTaskPostponePolicy.keep_first)
        # the last policy wins
        record4 = WScheduleRecord(task, ttl=1)  # this record is for just to be sure, that others are processed
        postpone_queue.postpone(record1)
        postpone_queue.postpone(record2)
        postpone_queue.postpone(record3)
        postpone_queue.postpone(record4)
        wasp_signals.wait(WSchedulerPostponeQueue.task_expired)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_postponed: (record1, record2),  # at first, record2 is postponed
            WSchedulerPostponeQueue.task_dropped: (record2, record3, ),  # but when record3 is arrived, record2
            # is dropped
            WSchedulerPostponeQueue.task_expired: (record4, )
        })
        assert(postpone_queue.next_record() is record1)
        assert(postpone_queue.next_record() is None)

    def test_next_record_filter_fn(self, queue_fixture):
        wasp_signals, postpone_queue = queue_fixture

        task = TaskExample()
        record = WScheduleRecord(task, group_id='group')
        postpone_queue.postpone(record)
        wasp_signals.wait(WSchedulerPostponeQueue.task_postponed)
        assert(wasp_signals.dump() == {
            WSchedulerPostponeQueue.task_postponed: (record, )
        })

        wasp_signals.clear()
        assert(postpone_queue.next_record(filter_fn=lambda x: False) is None)
        assert(wasp_signals.dump() == {})

        assert (postpone_queue.next_record(filter_fn=lambda x: True) is record)


class TestWScheduler:

    @pytest.fixture
    def scheduler_fixture(self, wasp_signals):
        scheduler = WScheduler(1)
        scheduler.callback(WSchedulerProto.task_scheduled, wasp_signals)
        scheduler.callback(WSchedulerProto.scheduled_task_dropped, wasp_signals)
        scheduler.callback(WSchedulerProto.scheduled_task_postponed, wasp_signals)
        scheduler.callback(WSchedulerProto.scheduled_task_expired, wasp_signals)
        scheduler.callback(WSchedulerProto.scheduled_task_started, wasp_signals)
        scheduler.callback(WSchedulerProto.scheduled_task_completed, wasp_signals)
        scheduler.callback(WSchedulerProto.scheduled_task_stopped, wasp_signals)

        source = WScheduleSourceProto()
        scheduler.subscribe(source)

        return wasp_signals, scheduler, source

    def test(self):
        scheduler = WScheduler(1)
        assert(isinstance(scheduler, WScheduler) is True)
        assert(isinstance(scheduler, WSchedulerProto) is True)

        scheduler.start()
        scheduler.stop()

    def test_simultaneous_policy(self, wasp_signals):
        scheduler = WScheduler(10)
        scheduler.callback(WSchedulerProto.scheduled_task_started, wasp_signals)
        scheduler.callback(WSchedulerProto.scheduled_task_completed, wasp_signals)
        scheduler.callback(WSchedulerProto.scheduled_task_postponed, wasp_signals)

        source = WScheduleSourceProto()
        scheduler.subscribe(source)

        scheduler.start()

        task1 = TaskExample(long_running=True)
        record1 = WScheduleRecord(task1, group_id='group')
        task2 = TaskExample(long_running=True)
        record2 = WScheduleRecord(task2, group_id='group', simultaneous_policy=1)
        task3 = TaskExample(long_running=True)
        record3 = WScheduleRecord(task3, group_id='group', simultaneous_policy=1)

        source.emit(WScheduleSourceProto.task_scheduled, record1)
        source.emit(WScheduleSourceProto.task_scheduled, record2)
        wasp_signals.wait(WSchedulerProto.scheduled_task_postponed)
        assert(wasp_signals.dump() == {
            WSchedulerProto.scheduled_task_started: (record1, ),
            WSchedulerProto.scheduled_task_postponed: (record2, ),
        })

        wasp_signals.clear()
        source.emit(WScheduleSourceProto.task_scheduled, record3)
        wasp_signals.wait(WSchedulerProto.scheduled_task_postponed)
        assert(wasp_signals.dump() == {
            WSchedulerProto.scheduled_task_postponed: (record3, ),
        })

        wasp_signals.clear()
        task1.stop()
        wasp_signals.wait(WSchedulerProto.scheduled_task_started)
        assert(wasp_signals.dump() == {
            WSchedulerProto.scheduled_task_completed: (WScheduledTaskResult(record1, WTaskResult()),),
            WSchedulerProto.scheduled_task_started: (record2, ),
        })

        wasp_signals.clear()
        task2.stop()
        wasp_signals.wait(WSchedulerProto.scheduled_task_started)
        assert(wasp_signals.dump() == {
            WSchedulerProto.scheduled_task_completed: (WScheduledTaskResult(record2, WTaskResult()),),
            WSchedulerProto.scheduled_task_started: (record3, ),
        })

        scheduler.stop()

    def test_subscription(self, scheduler_fixture):
        wasp_signals, scheduler, source = scheduler_fixture
        pytest.raises(ValueError, scheduler.subscribe, source)

        scheduler.unsubscribe(source)
        pytest.raises(ValueError, scheduler.unsubscribe, source)

        scheduler.subscribe(source)

    def test_scheduler(self, scheduler_fixture):
        wasp_signals, scheduler, source = scheduler_fixture
        task = TaskExample(long_running=True)
        record = WScheduleRecord(task)
        scheduler.start()

        assert(wasp_signals.dump() == {})
        source.emit(WScheduleSourceProto.task_scheduled, record)
        wasp_signals.wait(WSchedulerProto.scheduled_task_started)
        assert(wasp_signals.dump() == {
            WSchedulerProto.task_scheduled: (record, ),
            WSchedulerProto.scheduled_task_started: (record, ),
        })

        wasp_signals.clear()
        task.stop()
        wasp_signals.wait(WSchedulerProto.scheduled_task_stopped)
        assert(wasp_signals.dump() == {
            WSchedulerProto.scheduled_task_completed: (
                WScheduledTaskResult(record, WTaskResult()),
            ),
            WSchedulerProto.scheduled_task_stopped: (record, ),
        })

        scheduler.stop()

    @pytest.mark.parametrize(
        "record2, signal", [
            (WScheduleRecord(TaskExample()), WSchedulerProto.scheduled_task_postponed),
            (WScheduleRecord(TaskExample(), ttl=1), WSchedulerProto.scheduled_task_expired),
            (
                WScheduleRecord(TaskExample(), postpone_policy=WScheduledTaskPostponePolicy.drop),
                WSchedulerProto.scheduled_task_dropped
            ),
        ]
    )
    def test_postpone(self, scheduler_fixture, record2, signal):
        wasp_signals, scheduler, source = scheduler_fixture
        task1 = TaskExample(long_running=True)
        record1 = WScheduleRecord(task1)

        scheduler.start()

        assert (wasp_signals.dump() == {})
        source.emit(WScheduleSourceProto.task_scheduled, record1)
        wasp_signals.wait(WSchedulerProto.scheduled_task_started)
        wasp_signals.clear()

        source.emit(WScheduleSourceProto.task_scheduled, record2)
        wasp_signals.wait(signal)
        assert (wasp_signals.dump() == {
            WSchedulerProto.task_scheduled: (record2, ),
            signal: (record2, )
        })

        task1.stop()
        scheduler.stop()

    def test_drop_on_stop(self, scheduler_fixture):
        wasp_signals, scheduler, source = scheduler_fixture
        scheduler.start()

        task1 = TaskExample(long_running=True)
        record1 = WScheduleRecord(task1)
        source.emit(WScheduleSourceProto.task_scheduled, record1)

        record2 = WScheduleRecord(TaskExample())
        source.emit(WScheduleSourceProto.task_scheduled, record2)
        wasp_signals.wait(WSchedulerProto.scheduled_task_postponed)
        wasp_signals.clear()

        scheduler.stop()

        wasp_signals.wait(WSchedulerProto.scheduled_task_dropped)
        wasp_signals.wait(WSchedulerProto.scheduled_task_stopped)
        assert (wasp_signals.dump() == {
            WSchedulerProto.scheduled_task_stopped: (record1, ),
            WSchedulerProto.scheduled_task_dropped: (record2, ),
        })
