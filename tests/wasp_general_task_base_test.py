# -*- coding: utf-8 -*-

import pytest

from wasp_general.task.base import WTask, WStoppableTask, WTerminatableTask, WSyncTask


def test_abstract_classes():
	pytest.raises(TypeError, WTask)
	pytest.raises(NotImplementedError, WTask.start, None)

	pytest.raises(TypeError, WStoppableTask)
	pytest.raises(NotImplementedError, WStoppableTask.stop, None)

	pytest.raises(TypeError, WTerminatableTask)
	pytest.raises(NotImplementedError, WTerminatableTask.terminate, None)


class TestWSyncTask:

	def test_task(self):

		pytest.raises(TypeError, WSyncTask)

		class T1(WSyncTask):

			last_call_result = None

			def start(self):
				T1.last_call_result = 'T1.start'

		t1 = T1()
		assert(isinstance(t1, WTask) is True)
		assert(isinstance(t1, WStoppableTask) is True)

		assert(T1.last_call_result is None)
		t1.start()
		assert(T1.last_call_result == 'T1.start')

		t1.stop()
		assert(T1.last_call_result == 'T1.start')

		class T2(WSyncTask):

			last_call_result = None

			def start(self):
				T2.last_call_result = 'T2.start'

			def stop(self):
				T2.last_call_result = 'T2.stop'

		t2 = T2()
		t2.start()
		assert(T2.last_call_result == 'T2.start')
		t2.stop()
		assert(T2.last_call_result == 'T2.stop')
