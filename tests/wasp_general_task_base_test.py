# -*- coding: utf-8 -*-

import pytest

from wasp_general.task.base import WTask, WStoppableTask, WTerminatableTask, WTaskStatus


def test_abstract_classes():
	pytest.raises(TypeError, WTask)
	pytest.raises(NotImplementedError, WTask.start, None)

	pytest.raises(TypeError, WStoppableTask)
	pytest.raises(NotImplementedError, WStoppableTask.stop, None)

	pytest.raises(TypeError, WTerminatableTask)
	pytest.raises(NotImplementedError, WTerminatableTask.terminate, None)

	pytest.raises(TypeError, WTaskStatus)


class TestWTaskStatus:

	def test_started(self):

		class TaskA(WTaskStatus):

			def __init__(self):
				WTaskStatus.__init__(self, decorate_start=False, decorate_stop=False)

			def start(self):
				self._started(True)

			def custom_stop(self):
				self._started(False)

		class TaskB(WStoppableTask, WTaskStatus):

			def start(self):
				pass

			def stop(self):
				pass

		class TaskC(WTaskStatus):

			def start(self):
				pass

		task_a = TaskA()
		assert(task_a.started() is False)
		task_a.start()
		assert (task_a.started() is True)
		task_a.custom_stop()
		assert (task_a.started() is False)

		task_b = TaskB()
		assert (task_b.started() is False)
		task_b.start()
		assert (task_b.started() is True)
		task_b.stop()
		assert (task_b.started() is False)

		pytest.raises(TypeError, TaskC)
