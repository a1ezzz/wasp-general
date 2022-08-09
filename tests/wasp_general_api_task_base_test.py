
import pytest

from threading import Thread, Event

from wasp_general.api.task.proto import WTaskProto, WTaskStartError, WTaskStopError, WTaskResult

from wasp_general.api.task.base import WSingleStateTask


class TestWSingleStateTask:

    class Task(WSingleStateTask):
        def __init__(self, *args, result=None, **kwargs):
            WSingleStateTask.__init__(self, *args, **kwargs)
            self.result = result

        def start(self):
            if self.result and isinstance(self.result, Exception):
                raise self.result
            return self.result

        def complete(self):
            if self.result and isinstance(self.result, Exception):
                self._switch_task_state(WSingleStateTask.TaskState.completed, WTaskResult(exception=self.result))
            else:
                self._switch_task_state(WSingleStateTask.TaskState.completed, WTaskResult(result=self.result))

    class CorruptedTask(WSingleStateTask):
        def start(self):
            raise ValueError('!')

    class StoppableTask(WSingleStateTask):
        def start(self):
            pass

        def stop(self):
            pass

    class InterruptableTask(WSingleStateTask):
        def start(self):
            pass

        def terminate(self):
            pass

    class LongRunTask(WSingleStateTask):
        def __init__(self):
            WSingleStateTask.__init__(self)
            self.start_event = Event()
            self.stop_event = Event()
            self.terminate_event = Event()

        def start(self):
            self.start_event.wait()

        def stop(self):
            self.stop_event.wait()

        def terminate(self):
            self.terminate_event.wait()

    def test(self):
        task = TestWSingleStateTask.Task()
        assert(isinstance(task, WTaskProto) is True)
        assert(task.task_state() is WSingleStateTask.TaskState.stopped)
        task.start()
        assert(task.task_state() is WSingleStateTask.TaskState.completed)

        task = TestWSingleStateTask.Task(detachable=True)
        assert(task.task_state() is WSingleStateTask.TaskState.stopped)
        task.start()
        assert(task.task_state() is WSingleStateTask.TaskState.started)
        task.complete()
        assert(task.task_state() is WSingleStateTask.TaskState.completed)

        task = TestWSingleStateTask.StoppableTask()
        assert(task.task_state() is WSingleStateTask.TaskState.stopped)
        task.start()
        assert(task.task_state() is WSingleStateTask.TaskState.completed)
        task.stop()
        assert(task.task_state() is WSingleStateTask.TaskState.stopped)

        task = TestWSingleStateTask.InterruptableTask(detachable=True)
        assert(task.task_state() is WSingleStateTask.TaskState.stopped)
        task.start()
        assert(task.task_state() is WSingleStateTask.TaskState.started)
        task.terminate()
        assert(task.task_state() is WSingleStateTask.TaskState.terminated)

    def test_exceptions(self):
        task = TestWSingleStateTask.CorruptedTask()
        pytest.raises(ValueError, task.start)

        task = TestWSingleStateTask.CorruptedTask(detachable=True)
        pytest.raises(ValueError, task.start)

        task = TestWSingleStateTask.LongRunTask()
        task_thread = Thread(target=task.start)
        task_thread.start()
        pytest.raises(WTaskStartError, task.start)  # unable to start twice
        task.start_event.set()  # stop thread
        task_thread.join()

        task = TestWSingleStateTask.LongRunTask()
        task_thread = Thread(target=task.stop)
        task_thread.start()
        pytest.raises(WTaskStopError, task.stop)  # unable to stop twice
        task.stop_event.set()
        task_thread.join()

        task = TestWSingleStateTask.LongRunTask()
        task_thread = Thread(target=task.terminate)
        task_thread.start()
        pytest.raises(WTaskStopError, task.terminate)  # unable to stop twice
        task.terminate_event.set()
        task_thread.join()

    def test_signals(self, wasp_signals):
        task = TestWSingleStateTask.Task(result='foo')
        task.callback(WSingleStateTask.task_started, wasp_signals)
        task.callback(WSingleStateTask.task_completed, wasp_signals)
        task.start()
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_started: (None, ),
            WSingleStateTask.task_completed: (WTaskResult(result='foo'), ),
        })

        task = TestWSingleStateTask.Task(result='bar', detachable=True)
        wasp_signals.clear()
        task.callback(WSingleStateTask.task_started, wasp_signals)
        task.callback(WSingleStateTask.task_completed, wasp_signals)
        assert(wasp_signals.dump() == {})
        task.start()
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_started: (None, ),
        })

        wasp_signals.clear()
        task.complete()
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_completed: (WTaskResult(result='bar'), ),
        })

        exc = ValueError('!')
        wasp_signals.clear()
        task = TestWSingleStateTask.Task(result=exc)
        task.callback(WSingleStateTask.task_started, wasp_signals)
        task.callback(WSingleStateTask.task_completed, wasp_signals)
        pytest.raises(ValueError, task.start)
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_started: (None, ),
            WSingleStateTask.task_completed: (WTaskResult(exception=exc), ),
        })

        wasp_signals.clear()
        task = TestWSingleStateTask.Task(result=exc, detachable=True)
        task.callback(WSingleStateTask.task_started, wasp_signals)
        task.callback(WSingleStateTask.task_completed, wasp_signals)
        pytest.raises(ValueError, task.start)
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_started: (None, ),
        })

        wasp_signals.clear()
        task.complete()
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_completed: (WTaskResult(exception=exc), ),
        })

        task = TestWSingleStateTask.StoppableTask()
        task.callback(WSingleStateTask.task_started, wasp_signals)
        task.callback(WSingleStateTask.task_completed, wasp_signals)
        task.callback(WSingleStateTask.task_stopped, wasp_signals)

        wasp_signals.clear()
        task.start()
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_started: (None, ),
            WSingleStateTask.task_completed: (WTaskResult(), ),
        })

        wasp_signals.clear()
        task.stop()
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_stopped: (None, ),
        })

        task = TestWSingleStateTask.InterruptableTask()
        task.callback(WSingleStateTask.task_terminated, wasp_signals)
        wasp_signals.clear()
        task.terminate()
        assert(wasp_signals.dump() == {
            WSingleStateTask.task_terminated: (None, ),
        })
