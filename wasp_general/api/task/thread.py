# -*- coding: utf-8 -*-
# wasp_general/api/task/thread.py
#
# Copyright (C) 2016-2019 the wasp-general authors and contributors
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

import enum
from threading import Thread

from wasp_general.verify import verify_type
from wasp_general.api.signals import WSignalSource, WSignal

from wasp_general.api.task.proto import WTaskProto, WStartedTaskError, WStoppedTaskError


class WJoiningTimeoutError(Exception):
	""" Exception is raised when thread joining timeout is expired
	"""
	pass


class WThreadTask(WTaskProto, WSignalSource):
	""" This class helps to run a task in a separate thread. This class does not prevent any race conditions
	that may occur with an original task. So the task to run should implement the :meth:`.WTaskProto.stop` method
	and this method must be able to be called from a separate thread.

	In some circumstances the :meth:`.WTaskProto.stop` method may be called before the :meth:`.WTaskProto.start`
	method
	"""

	task_stopped = WSignal(payload_type_spec=None)  # a task was never started or is stopped already
	task_started = WSignal(payload_type_spec=None)  # a task was started but a thread is not started yet
	task_running = WSignal(payload_type_spec=None)  # a thread is started and and original task is about to start
	task_ready = WSignal(payload_type_spec=None)  # a thread function is stopped without exceptions and the thread
	# is ready to be joined
	task_crashed = WSignal(payload_type_spec=Exception)  # a thread function was stopped by an exceptions and
	# the thread is ready to be joined
	task_froze = WSignal(payload_type_spec=None)  # a task was requested to stop but a thread was not joined
	# in a time

	@verify_type('strict', task=WTaskProto, thread_name=(str, None))
	@verify_type('strict', join_timeout=(int, float, None))
	def __init__(self, task, thread_name=None, join_timeout=None):
		""" Create a threaded task

		:param task: a task that should be ran in a thread
		:type task: WTaskProto

		:param thread_name: name of a thread to create
		:type thread_name: str | None

		:param join_timeout: if defined then this is a period of time that this task will wait for an
		original task to stop in a :meth:`.WThreadTask.stop` method.  If this values is None then
		the :meth:`.WThreadTask.stop` method wait in a block mode forever

		:type join_timeout: int | float | None
		"""
		WTaskProto.__init__(self)
		WSignalSource.__init__(self)

		self.__task = task
		self.__thread_name = thread_name
		self.__join_timeout = join_timeout

		self.__thread = None
		self.__exception = None
		self.__status = WThreadTaskStatus.stopped

	def exception(self):
		""" Return an exception that was raised on the last :meth:`.WThreadTask.start` method call. Return
		None if there was not any. This values will be set to None at the next :meth:`.WThreadTask.start`
		method call

		:rtype: Exception | None
		"""
		return self.__exception

	def status(self):
		""" Return current status

		:rtype: WThreadTaskStatus
		"""
		return self.__status

	def task(self):
		""" Return an original task that is about to start (or is running already)

		:rtype: WTaskProto
		"""
		return self.__task

	def start(self):
		""" :meth:`.WTaskProto.start` method implementation.

		:rtype: None
		"""
		def thread_target():
			try:
				self.__switch_status(WThreadTaskStatus.running)
				self.__task.start()
				self.__switch_status(WThreadTaskStatus.ready)
			except Exception as e:
				self.__switch_status(WThreadTaskStatus.crashed, payload=e)
				self.__exception = e

		if self.__thread is None:
			self.__switch_status(WThreadTaskStatus.started)
			self.__exception = None
			self.__thread = Thread(target=thread_target, name=self.__thread_name)
			self.__thread.start()
		else:
			raise WStartedTaskError('A thread is running already')

	def __switch_status(self, new_status, payload=None):
		""" Switch current status and send a signal

		:param new_status: new status
		:type new_status: WThreadTaskStatus

		:param payload: argument to a signal to send
		:type payload: any

		:rtype: None
		"""
		self.__status = new_status
		self.__status.value(self, payload=payload)

	def stop(self):
		""" :meth:`.WTaskProto.stop` method implementation.

		:rtype: None
		"""
		if self.__thread is not None:
			if WTaskProto.stop in self.__task:
				self.__task.stop()
			self.__thread.join(self.__join_timeout)
			if self.__thread.is_alive() is True:
				self.__switch_status(WThreadTaskStatus.froze)
				raise WJoiningTimeoutError(
					'Thread is still alive. The thread name: %s' % self.__thread.name
				)
			self.__thread = None
			self.__switch_status(WThreadTaskStatus.stopped)
		else:
			raise WStoppedTaskError('A thread is stopped already')

	@classmethod
	def signals(cls):
		""" Signals that this class may emit

		:rtype: tuple[WSignal]
		"""
		return WThreadTask.task_stopped, \
			WThreadTask.task_started, \
			WThreadTask.task_running, \
			WThreadTask.task_ready, \
			WThreadTask.task_crashed, \
			WThreadTask.task_froze


@enum.unique
class WThreadTaskStatus(enum.Enum):
	""" A possible states of a :class:`WThreadTask` objects. Values are corresponding signals
	"""
	stopped = WThreadTask.task_stopped
	started = WThreadTask.task_started
	running = WThreadTask.task_running
	ready = WThreadTask.task_ready
	crashed = WThreadTask.task_crashed
	froze = WThreadTask.task_froze
