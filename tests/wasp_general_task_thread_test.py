# -*- coding: utf-8 -*-

import pytest
import time

from wasp_general.task.base import WStoppableTask, WTerminatableTask, WTask
from wasp_general.task.thread import WThreadTask, WThreadCustomTask, WThreadJoiningTimeoutError, WPollingThreadTask
from wasp_general.task.thread import WThreadedTaskChain


class TestWThreadTask:

	def test_init(self):
		assert(issubclass(WThreadTask, WStoppableTask) is True)
		assert(issubclass(WThreadTask, WTerminatableTask) is False)
		pytest.raises(TypeError, WThreadTask)
		pytest.raises(NotImplementedError, WThreadTask.thread_started, None)
		pytest.raises(NotImplementedError, WThreadTask.thread_stopped, None)

		class T(WThreadTask):

			def thread_started(self):
				pass

			def thread_stopped(self):
				pass

		T()

	def test_task(self):

		class FastTask(WThreadTask):

			__thread_join_timeout__ = 3

			call_stack = []

			def thread_started(self):
				FastTask.call_stack.append('FastTask.start')

			def thread_stopped(self):
				FastTask.call_stack.append('FastTask.stop')

		class SlowTask(FastTask):

			sleep_time = 0.5

			def thread_started(self):
				FastTask.start(self)
				time.sleep(SlowTask.sleep_time)

		t = FastTask()
		assert(t.thread() is None)
		assert(t.join_timeout() == FastTask.__thread_join_timeout__)
		assert(t.start_event().is_set() is False)
		assert(t.stop_event().is_set() is False)
		assert(t.ready_event() is None)

		t.start()
		assert(t.thread() is not None)
		assert(t.thread().name != 'custom thread name')
		assert(t.start_event().is_set() is True)
		assert(t.stop_event().is_set() is False)
		assert(t.ready_event() is None)

		t.stop()
		assert(t.thread() is None)
		assert(t.start_event().is_set() is False)
		assert(t.stop_event().is_set() is True)
		assert(FastTask.call_stack == ['FastTask.start', 'FastTask.stop'])
		assert(t.ready_event() is None)

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
		pytest.raises(WThreadJoiningTimeoutError, t.stop)
		assert(t.stop_event().is_set() is True)
		t.thread().join(SlowTask.sleep_time)
		t.close_thread()
		assert(t.thread() is None)
		assert(t.stop_event().is_set() is True)

		FastTask.call_stack = []
		t = FastTask(join_on_stop=False)
		assert(t.thread() is None)
		t.start()
		assert(t.thread() is not None)
		t.stop()
		assert(t.thread() is not None)
		assert(FastTask.call_stack == ['FastTask.start', 'FastTask.stop'])
		t.thread().join()
		t.close_thread()
		assert(t.thread() is None)

		slow_task = SlowTask(ready_to_stop=True)
		assert(slow_task.ready_event().is_set() is False)

		slow_task.start()
		assert(slow_task.ready_event().is_set() is False)
		assert(slow_task.stop_event().is_set() is False)

		slow_task.ready_event().wait(SlowTask.sleep_time * 2)
		assert(slow_task.ready_event().is_set() is True)
		assert(slow_task.stop_event().is_set() is False)

		slow_task.stop()
		assert(slow_task.ready_event().is_set() is True)
		assert(slow_task.stop_event().is_set() is True)

		t = FastTask()
		raised_exception = []

		def test_exception():
			raise KeyError('Test exception')

		def handle_exception(exc):
			raised_exception.append(exc.__class__)

		t.thread_started = test_exception
		assert (t.exception_event().is_set() is False)
		t.start()
		t.exception_event().wait(FastTask.__thread_join_timeout__)
		time.sleep(0.1)
		assert(t.exception_event().is_set() is True)
		t.stop()
		assert (t.exception_event().is_set() is True)

		assert(raised_exception == [])
		t.thread_exception = handle_exception
		t.start()
		t.exception_event().wait(FastTask.__thread_join_timeout__)
		time.sleep(0.1)
		assert(raised_exception == [KeyError])
		t.stop()
		assert(raised_exception == [KeyError])


class TestWThreadCustomTask:

	__call_stack__ = []

	class Task(WTask):

		def start(self):
			TestWThreadCustomTask.__call_stack__.append('Task::start')

	class StoppableTask(WStoppableTask):

		def start(self):
			TestWThreadCustomTask.__call_stack__.append('StoppableTask::start')

		def stop(self):
			TestWThreadCustomTask.__call_stack__.append('StoppableTask::stop')

	def test(self):
		task = TestWThreadCustomTask.Task()
		threaded_task = WThreadCustomTask(task)

		assert(isinstance(threaded_task, WThreadCustomTask) is True)
		assert(isinstance(threaded_task, WThreadTask) is True)

		TestWThreadCustomTask.__call_stack__.clear()
		assert(TestWThreadCustomTask.__call_stack__ == [])

		threaded_task.start()
		assert(TestWThreadCustomTask.__call_stack__ == ['Task::start'])

		threaded_task.stop()
		assert(TestWThreadCustomTask.__call_stack__ == ['Task::start'])

		task = TestWThreadCustomTask.StoppableTask()
		threaded_task = WThreadCustomTask(task)

		TestWThreadCustomTask.__call_stack__.clear()
		assert(TestWThreadCustomTask.__call_stack__ == [])

		threaded_task.start()
		assert(TestWThreadCustomTask.__call_stack__ == ['StoppableTask::start'])

		threaded_task.stop()
		assert(TestWThreadCustomTask.__call_stack__ == ['StoppableTask::start', 'StoppableTask::stop'])


class TestWPollingThreadTask:

	class Task(WPollingThreadTask):

		call_stack = []

		def _polling_iteration(self):
			TestWPollingThreadTask.Task.call_stack.append('Task iteration')

		def thread_stopped(self):
			TestWPollingThreadTask.Task.call_stack.append('Task stop')

	def test(self):
		pytest.raises(TypeError, WPollingThreadTask)
		pytest.raises(NotImplementedError, WPollingThreadTask._polling_iteration, None)
		pytest.raises(NotImplementedError, WPollingThreadTask.thread_stopped, None)

		task = TestWPollingThreadTask.Task()
		assert(isinstance(task, WPollingThreadTask) is True)
		assert(isinstance(task, WThreadTask) is True)
		assert(task.polling_timeout() == WPollingThreadTask.__thread_polling_timeout__)

		timeout = WPollingThreadTask.__thread_polling_timeout__ + 2
		task = TestWPollingThreadTask.Task(polling_timeout=timeout)
		assert(task.polling_timeout() == timeout)

		timeout = 0.001
		task = TestWPollingThreadTask.Task(polling_timeout=timeout)
		task.start()
		time.sleep(timeout * 5)
		task.stop()
		assert(TestWPollingThreadTask.Task.call_stack[:4] == [
			'Task iteration', 'Task iteration', 'Task iteration', 'Task iteration'
		])
		assert (TestWPollingThreadTask.Task.call_stack[-1] == 'Task stop')

		TestWPollingThreadTask.Task.call_stack.clear()
		TestWPollingThreadTask.Task.__thread_polling_timeout__ = 0.1
		task = TestWPollingThreadTask.Task()
		assert(task.polling_timeout() == TestWPollingThreadTask.Task.__thread_polling_timeout__)
		task.start()
		time.sleep(timeout * 2)
		task.stop()
		assert(len(TestWPollingThreadTask.Task.call_stack[:-1]) <= 3)
		for call in TestWPollingThreadTask.Task.call_stack[:-1]:
			assert(call == 'Task iteration')
		assert (TestWPollingThreadTask.Task.call_stack[-1] == 'Task stop')


class TestWThreadedTaskChain:

	def test(self):
		polling_timeout = 0.001
		chain = WThreadedTaskChain(polling_timeout=polling_timeout)
		assert(isinstance(chain, WThreadedTaskChain) is True)
		assert(isinstance(chain, WPollingThreadTask) is True)

		assert (chain.ready_event().is_set() is False)
		chain.start()
		time.sleep(polling_timeout * 5)
		assert(chain.ready_event().is_set() is True)
		chain.stop()

		class Task(WThreadTask):

			call_trace = []

			def __init__(self, sleep_timeout, call_trace_id, ready_to_stop=True):
				WThreadTask.__init__(self, ready_to_stop=ready_to_stop)
				self.__sleep_timeout = sleep_timeout
				self.__trace_id = call_trace_id

			def thread_started(self):
				time.sleep(self.__sleep_timeout)
				Task.call_trace.append(self.__trace_id)
				self.stop_event().set()

			def thread_stopped(self):
				pass

		pytest.raises(ValueError, WThreadedTaskChain, Task(0, 'task', ready_to_stop=False))

		task1_sleep_timeout = 0.1
		task1 = Task(task1_sleep_timeout, 'task1')

		task2_sleep_timeout = 0.001
		task2 = Task(task2_sleep_timeout, 'task2')

		assert(Task.call_trace == [])
		task1.start()
		task2.start()
		time.sleep(task1_sleep_timeout * 5)
		task1.stop()
		task2.stop()
		assert(Task.call_trace == ['task2', 'task1'])

		Task.call_trace.clear()
		chain = WThreadedTaskChain(task1, task2, polling_timeout=polling_timeout)
		assert(Task.call_trace == [])
		chain.start()
		time.sleep(task1_sleep_timeout * 5)
		assert(Task.call_trace == ['task1', 'task2'])
		chain.stop()

		def test_exception():
			print('RAISE EXCEPTION!')
			raise KeyError('Test exception')
		task2.thread_started = test_exception

		task2_raised_exception = []

		def task2_handle_exception(exc):
			print('TASK CAUGHT EXC: ' + str(exc))
			task2_raised_exception.append(exc.__class__)

		task2.thread_exception = task2_handle_exception

		chain_raised_exception = []

		def chain_handle_exception(exc):
			print('CHAIN CAUGHT EXC: ' + str(exc))
			chain_raised_exception.append(exc.__class__)

		assert(task2_raised_exception == [])
		assert(chain_raised_exception == [])
		chain = WThreadedTaskChain(task1, task2, polling_timeout=polling_timeout)
		chain.thread_exception = chain_handle_exception
		chain.start()
		chain.exception_event().wait(polling_timeout * 5)
		time.sleep(0.5)
		assert(task2_raised_exception == [KeyError])
		assert(chain_raised_exception == [RuntimeError])
		chain.stop()
		assert(task2_raised_exception == [KeyError])
		assert(chain_raised_exception == [RuntimeError])

		assert(Task.call_trace == ['task1', 'task2', 'task1'])
