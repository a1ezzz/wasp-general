
import pytest

from wasp_general.platform import WPlatformThreadEvent
from wasp_general.api.task.proto import WTaskProto, WTaskStartError, WTaskStopError, WTaskResult
from wasp_general.api.task.base import WSingleStateTask

from wasp_general.api.task.thread import WJoiningTimeoutError, WThreadedTaskResult, WThreadTask


def test_exceptions():
    assert(issubclass(WJoiningTimeoutError, Exception) is True)


class TestWThreadedTaskResult:

    def test(self):
        task = TestWThreadTask.Task()
        result = WTaskResult()
        threaded_task_result = WThreadedTaskResult(task=task, result=result)
        assert(threaded_task_result.task is task)
        assert(threaded_task_result.result is result)


class TestWThreadTask:

    class Task(WTaskProto):

        exception = None
        sleep_event = WPlatformThreadEvent()

        def start(self):
            self.sleep_event.wait()

            if self.exception:
                raise self.exception

        def stop(self):
            pass

    def test(self):
        task = TestWThreadTask.Task()
        task.sleep_event.set()

        threaded_task = WThreadTask(task=task)
        assert(isinstance(threaded_task, WSingleStateTask) is True)
        assert(threaded_task.task() is task)
        threaded_task.start()
        threaded_task.stop()

        TestWThreadTask.Task.exception = Exception('!')
        threaded_task.start()  # just check that exception in task doesn't affect threaded task
        threaded_task.stop()
        TestWThreadTask.Task.exception = None

    def test_exceptions(self):
        task = TestWThreadTask.Task()
        threaded_task = WThreadTask(task=task)
        threaded_task.start()
        pytest.raises(WTaskStartError, threaded_task.start)
        threaded_task.stop()
        pytest.raises(WTaskStopError, threaded_task.stop)

        TestWThreadTask.Task.sleep_event.clear()
        threaded_task = WThreadTask(task=task, join_timeout=1)
        threaded_task.start()
        pytest.raises(WJoiningTimeoutError, threaded_task.stop)
        TestWThreadTask.Task.sleep_event.set()
        threaded_task.stop()

    def test_signals(self, wasp_signals):
        task = TestWThreadTask.Task()
        threaded_task = WThreadTask(task=task, join_timeout=1)
        TestWThreadTask.Task.sleep_event.clear()

        threaded_task.callback(WThreadTask.task_started, wasp_signals)
        threaded_task.callback(WThreadTask.task_completed, wasp_signals)
        threaded_task.callback(WThreadTask.task_stopped, wasp_signals)

        threaded_task.callback(WThreadTask.threaded_task_started, wasp_signals)
        threaded_task.callback(WThreadTask.threaded_task_completed, wasp_signals)
        threaded_task.callback(WThreadTask.threaded_task_froze, wasp_signals)

        assert(wasp_signals.dump() == dict())

        threaded_task.start()
        wasp_signals.wait(WThreadTask.threaded_task_started)
        assert(wasp_signals.dump() == {
            WThreadTask.task_started: (None, ),
            WThreadTask.threaded_task_started: (task, )
        })

        TestWThreadTask.Task.sleep_event.set()
        threaded_task.stop()
        wasp_signals.wait(WThreadTask.task_stopped)

        assert(wasp_signals.dump() == {
            WThreadTask.task_started: (None, ),
            WThreadTask.task_completed: (WTaskResult(), ),
            WThreadTask.task_stopped: (None, ),
            WThreadTask.threaded_task_started: (task, ),
            WThreadTask.threaded_task_completed: (WThreadedTaskResult(task=task, result=WTaskResult()), )
        })

        exc = Exception('!')
        TestWThreadTask.Task.exception = exc
        TestWThreadTask.Task.sleep_event.clear()
        threaded_task.start()
        wasp_signals.wait(WThreadTask.threaded_task_started)
        wasp_signals.clear()
        TestWThreadTask.Task.sleep_event.set()
        threaded_task.stop()
        wasp_signals.wait(WThreadTask.task_stopped)
        assert(wasp_signals.dump() == {
            WThreadTask.task_completed: (WTaskResult(), ),
            WThreadTask.task_stopped: (None, ),
            WThreadTask.threaded_task_completed: (WThreadedTaskResult(task=task, result=WTaskResult(exception=exc)), )
        })

        TestWThreadTask.Task.exception = None
        TestWThreadTask.Task.sleep_event.clear()
        threaded_task.start()
        wasp_signals.wait(WThreadTask.threaded_task_started)
        wasp_signals.clear()

        pytest.raises(WJoiningTimeoutError, threaded_task.stop)
        assert(wasp_signals.dump() == {
            WThreadTask.threaded_task_froze: (task, ),
        })

        TestWThreadTask.Task.sleep_event.set()
        threaded_task.stop()
