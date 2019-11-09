
from contextlib import suppress
import pytest

from wasp_general.platform import WPlatformThreadEvent
from wasp_general.api.task.proto import WTaskProto, WStoppedTaskError, WStartedTaskError

from wasp_general.api.task.thread import WJoiningTimeoutError, WThreadTaskStatus, WThreadTask


def test_exceptions():
	assert(issubclass(WJoiningTimeoutError, Exception) is True)


class TestWThreadTask:

	class Task(WTaskProto):

		exception = None
		sleep_event = None

		@classmethod
		def init_task(cls, **kwargs):
			return cls()

		def start(self):
			if self.sleep_event:
				self.sleep_event.wait()

			if self.exception:
				raise self.exception

		def stop(self):
			pass

	def test(self):
		threaded_task = WThreadTask.init_task(task_cls=TestWThreadTask.Task)
		assert(isinstance(threaded_task.task(), TestWThreadTask.Task))
		assert(threaded_task.status() is WThreadTaskStatus.stopped)
		assert(threaded_task.exception() is None)
		threaded_task.start()
		status = threaded_task.status()
		assert(
			status is WThreadTaskStatus.started or
			status is WThreadTaskStatus.running or
			status is WThreadTaskStatus.ready
		)
		assert(threaded_task.exception() is None)
		threaded_task.stop()
		assert(threaded_task.status() is WThreadTaskStatus.stopped)
		assert(threaded_task.exception() is None)

		exc = Exception('!')
		TestWThreadTask.Task.exception = exc
		threaded_task.start()
		assert(threaded_task.exception() is exc)
		threaded_task.stop()
		assert(threaded_task.exception() is exc)

		TestWThreadTask.Task.exception = None
		threaded_task.start()
		assert(threaded_task.exception() is None)
		threaded_task.stop()

	def test_exceptions(self):
		threaded_task = WThreadTask.init_task(task_cls=TestWThreadTask.Task)
		threaded_task.start()
		pytest.raises(WStartedTaskError, threaded_task.start)
		threaded_task.stop()
		pytest.raises(WStoppedTaskError, threaded_task.stop)

		threaded_task = WThreadTask.init_task(task_cls=TestWThreadTask.Task, join_timeout=1)
		TestWThreadTask.Task.sleep_event = WPlatformThreadEvent()
		threaded_task.start()
		pytest.raises(WJoiningTimeoutError, threaded_task.stop)
		TestWThreadTask.Task.sleep_event.set()
		threaded_task.stop()

		TestWThreadTask.Task.sleep_event = None

	def test_signals(self):
		threaded_task = WThreadTask.init_task(task_cls=TestWThreadTask.Task, join_timeout=1)

		stop_watcher = threaded_task.watch(WThreadTaskStatus.stopped.value)
		start_watcher = threaded_task.watch(WThreadTaskStatus.started.value)
		run_watcher = threaded_task.watch(WThreadTaskStatus.running.value)
		ready_watcher = threaded_task.watch(WThreadTaskStatus.ready.value)
		crash_watcher = threaded_task.watch(WThreadTaskStatus.crashed.value)
		freeze_watcher = threaded_task.watch(WThreadTaskStatus.froze.value)

		assert(stop_watcher.wait(timeout=1) is False)

		threaded_task.start()
		start_watcher.wait()  # if there is no such signal - will wait forever
		run_watcher.wait()
		ready_watcher.wait()

		threaded_task.stop()
		stop_watcher.wait()

		assert(crash_watcher.wait(timeout=1) is False)
		TestWThreadTask.Task.exception = Exception('!')
		threaded_task.start()
		crash_watcher.wait()
		TestWThreadTask.Task.exception = None
		threaded_task.stop()

		assert(freeze_watcher.wait(timeout=1) is False)
		TestWThreadTask.Task.sleep_event = WPlatformThreadEvent()
		threaded_task.start()
		with suppress(WJoiningTimeoutError):
			threaded_task.stop()
		freeze_watcher.wait()
		TestWThreadTask.Task.sleep_event.set()
		threaded_task.stop()

		TestWThreadTask.Task.sleep_event = None
