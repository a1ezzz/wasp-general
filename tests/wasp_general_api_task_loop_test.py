
import pytest
import threading

from wasp_c_extensions.ev_loop import WEventLoop

from wasp_general.api.task.proto import WTaskProto, WTaskResult
from wasp_general.api.task.thread import WThreadTask

from wasp_general.api.task.loop import WEventLoopTask, WEventLoopThread


class TestWEventLoopTask:

    def test(self):
        task = WEventLoopTask()
        assert(isinstance(task, WEventLoopTask) is True)
        assert(isinstance(task, WTaskProto) is True)
        assert(isinstance(task.event_loop(), WEventLoop) is True)

        pytest.raises(RuntimeError, task.await_loop_start, 1)

    def test_thread(self, wasp_signals):
        loop = WEventLoop()
        task = WEventLoopTask(loop=loop)
        assert(task.event_loop() is loop)

        task.callback(WTaskProto.task_started, wasp_signals)
        task.callback(WTaskProto.task_completed, wasp_signals)
        task.callback(WTaskProto.task_stopped, wasp_signals)

        thread = threading.Thread(target=task.start)
        thread.start()
        task.await_loop_start()  # just await for a start
        assert(loop.is_started() is True)
        assert(wasp_signals.dump() == {
            WTaskProto.task_started: (None, )
        })

        wasp_signals.clear()
        task.stop()
        thread.join()
        assert(wasp_signals.dump() == {
            WTaskProto.task_completed: (WTaskResult(), ),
            WTaskProto.task_stopped: (None, )
        })


class TestWEventLoopThread:

    def test(self):
        thread = WEventLoopThread()
        assert(isinstance(thread, WEventLoopThread) is True)
        assert(isinstance(thread, WThreadTask) is True)
        assert(isinstance(thread.task(), WEventLoopTask) is True)

    def test_start(self):
        loop = WEventLoop()
        thread = WEventLoopThread(loop=loop)
        thread.start()
        thread.task().await_loop_start()
        thread.stop()
