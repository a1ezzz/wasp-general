# -*- coding: utf-8 -*-

import pytest
import time

from wasp_general.task.base import WTaskStatus, WStoppableTask, WTerminatableTask
from wasp_general.task.thread import WThreadTask


class TestWThreadTask:

	def test_init(self):
		assert(issubclass(WThreadTask, WTaskStatus) is True)
		assert(issubclass(WThreadTask, WStoppableTask) is True)
		assert(issubclass(WThreadTask, WTerminatableTask) is False)
		pytest.raises(TypeError, WThreadTask)
		pytest.raises(NotImplementedError, WThreadTask.start, None)
		pytest.raises(NotImplementedError, WThreadTask.stop, None)

		class T(WThreadTask):

			def start(self):
				pass

			def stop(self):
				pass

		T()

	def test_task(self):

		class FastTask(WThreadTask):

			__thread_join_timeout__ = 3

			call_stack = []

			def start(self):
				FastTask.call_stack.append('FastTask.start')

			def stop(self):
				FastTask.call_stack.append('FastTask.stop')

		class SlowTask(FastTask):

			sleep_time = 0.5

			def start(self):
				FastTask.start(self)
				time.sleep(SlowTask.sleep_time)

		t = FastTask()
		assert(t.thread() is None)
		assert(t.started() is False)
		assert(t.join_timeout() == FastTask.__thread_join_timeout__)
		assert(t.stop_event().is_set() is False)
		t.start()
		assert(t.thread() is not None)
		assert(t.started() is True)
		assert(t.thread().name != 'custom thread name')
		assert(t.stop_event().is_set() is False)
		t.stop()
		assert(t.thread() is None)
		assert(t.started() is False)
		assert(t.stop_event().is_set() is False)
		assert(FastTask.call_stack == ['FastTask.start', 'FastTask.stop'])

		FastTask.__thread_join_timeout__ = 2
		t = FastTask(thread_name='custom thread name')
		assert(t.join_timeout() == FastTask.__thread_join_timeout__)
		t.start()
		assert(t.thread().name == 'custom thread name')
		t.stop()

		FastTask.__thread_name__ = 'class thread name'
		t = FastTask()
		t.start()
		assert(t.thread().name == 'class thread name')
		t.stop()

		t = FastTask(thread_join_timeout=4)
		assert(t.join_timeout() != FastTask.__thread_join_timeout__)
		assert(t.join_timeout() == 4)

		t = SlowTask(thread_join_timeout=0.01)
		t.start()
		assert(t.stop_event().is_set() is False)
		pytest.raises(RuntimeError, t.stop)
		assert(t.stop_event().is_set() is True)
		t.thread().join(SlowTask.sleep_time)
		t.close_thread()
		assert(t.thread() is None)
		assert(t.stop_event().is_set() is False)

		FastTask.call_stack = []
		t = FastTask(join_on_stop=False)
		assert(t.thread() is None)
		assert(t.started() is False)
		t.start()
		assert(t.thread() is not None)
		assert(t.started() is True)
		t.stop()
		assert(t.thread() is not None)
		assert(t.started() is True)
		assert(FastTask.call_stack == ['FastTask.start', 'FastTask.stop'])
		t.thread().join()
		t.close_thread()
		assert(t.thread() is None)
		assert(t.started() is False)
