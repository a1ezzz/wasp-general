# -*- coding: utf-8 -*-
# wasp_general/api/task/thread.py
#
# Copyright (C) 2016-2019, 2022 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# Wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

from dataclasses import dataclass
from threading import Thread

from wasp_general.verify import verify_type
from wasp_general.api.signals import WSignal

from wasp_general.api.task.proto import WTaskProto, WTaskStartError, WTaskStopError, WTaskResult
from wasp_general.api.task.base import WSingleStateTask


class WJoiningTimeoutError(Exception):
	""" Exception is raised when thread joining timeout is expired
	"""
	pass


@dataclass
class WThreadedTaskResult:
	""" This class is used by a signal defining a result of a completed threaded-task
	"""

	task: WTaskProto     # executed task
	result: WTaskResult  # task result


class WThreadTask(WSingleStateTask):
	""" This class helps to run a task in a separate thread. This class does not prevent any race conditions
	that may occur with an original task. A task to run should implement the :meth:`.WTaskProto.stop` method
	and this method must be able to be called from a separate thread.
	"""

	threaded_task_started = WSignal(WTaskProto)             # a task was started but a thread is not started yet
	threaded_task_completed = WSignal(WThreadedTaskResult)  # a thread function was stopped because of completion
	# or an exception and the thread is ready to be joined
	threaded_task_froze = WSignal(WTaskProto)               # a task was requested to stop but a thread was not joined
	# in a time

	@verify_type('strict', task=WTaskProto, thread_name=(str, None), join_timeout=(int, float, None))
	def __init__(self, task, thread_name=None, join_timeout=None):
		""" Create a threaded task

		:param task: a task that should be run in a thread
		:type task: WTaskProto

		:param thread_name: name of a thread to create
		:type thread_name: str | None

		:param join_timeout: if defined then this is a period of time that this task will wait for an
		original task to stop in a :meth:`.WThreadTask.stop` method.  If this value is None then
		the :meth:`.WThreadTask.stop` method wait in a block mode forever
		:type join_timeout: int | float | None
		"""
		WSingleStateTask.__init__(self, detachable=True)

		self.__task = task
		self.__thread_name = thread_name
		self.__join_timeout = join_timeout

		self.__thread = None

	def task(self):
		""" Return an original task that is about to start (or is running already)

		:rtype: WTaskProto
		"""
		return self.__task

	def start(self):
		""" :meth:`.WTaskProto.start` method implementation.

		:raise WTaskStartError: if a thread is started already

		:rtype: None
		"""
		def thread_target():
			try:
				self.emit(WThreadTask.threaded_task_started, self.__task)
				result = self.__task.start()
				self.emit(
					WThreadTask.threaded_task_completed,
					WThreadedTaskResult(task=self.__task, result=WTaskResult(result=result))
				)
			except Exception as e:
				self.emit(
					WThreadTask.threaded_task_completed,
					WThreadedTaskResult(task=self.__task, result=WTaskResult(exception=e))
				)
			finally:
				self._switch_task_state(WSingleStateTask.TaskState.completed, WTaskResult())

		if self.__thread is None:
			self.__thread = Thread(target=thread_target, name=self.__thread_name)
			self.__thread.start()
		else:
			raise WTaskStartError('A thread is running already')

	def stop(self):
		""" :meth:`.WTaskProto.stop` method implementation.

		:raise WTaskStopError: if a thread is stopped already

		:rtype: None
		"""
		if self.__thread is not None:
			if WTaskProto.stop in self.__task:
				self.__task.stop()
			self.__thread.join(self.__join_timeout)
			if self.__thread.is_alive() is True:
				self.emit(WThreadTask.threaded_task_froze, self.__task)
				raise WJoiningTimeoutError(
					'Thread is still alive. The thread name: %s' % self.__thread.name
				)
			self.__thread = None
		else:
			raise WTaskStopError('A thread is stopped already')
