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

from wasp_general.verify import verify_type, verify_value, verify_subclass
from wasp_general.signals.signals import WSignalSource

from wasp_general.api.task.proto import WTaskProto, WStartedTaskError, WStoppedTaskError


class WJoiningTimeoutError(Exception):
	""" Exception is raised when thread joining timeout is expired
	"""
	pass


@enum.unique
class WThreadTaskStatus(enum.Enum):
	""" A possible states of a :class:`WThreadTask` objects. The same values are used as a signal's names of a task

	A 'crashed' signal will send an exception that was raised
	"""
	stopped = 'stopped'  # a task was never started or is stopped already
	started = 'started'  # a task was started but a thread is not started yet
	running = 'running'  # a thread is started and and original task is about to start
	ready = 'ready'  # a thread function is stopped without exceptions and the thread is ready to be joined
	crashed = 'crashed'  # a thread function was stopped by an exceptions and the thread is ready to be joined
	froze = 'froze'  # a task was requested to stop but a thread was not joined in a time


class WThreadTask(WTaskProto, WSignalSource):
	""" This class helps to run a task in a separate thread. This class does not prevent any race conditions
	that may occur with an original task. So the :meth:`.WTaskProto.stop` method of an original task must be
	ready to be called from a separate thread. Also in some situations the :meth:`.WTaskProto.stop` method may be
	called before the :meth:`.WTaskProto.start` method
	"""

	@classmethod
	@verify_type('paranoid', thread_name=(str, None), join_timeout=(int, float, None))
	@verify_value('paranoid', task=lambda x: WTaskProto.stop in x, join_timeout=lambda x: x is None or x >= 0)
	@verify_subclass(task_cls=WTaskProto)
	def init_task(cls, task_cls=None, thread_name=None, join_timeout=None, **kwargs):
		""" :meth:`.WTaskProto.init_task` method implementation.

		:note: the "task_cls" parameter can not be omitted

		:param task_cls: same as the "task_cls" parameter in the :meth:`.WThreadTask.__init__` method
		:type task_cls: type (WTaskProto subclass)

		:param thread_name: same as the "thread_name" parameter in the :meth:`.WThreadTask.__init__` method
		:type thread_name: str | None

		:param join_timeout: same as the "join_timeout" parameter in the :meth:`.WThreadTask.__init__` method
		:type join_timeout: int | float | None

		:param kwargs: same as the "kwargs" parameter in the :meth:`.WThreadTask.__init__` method

		:rtype: WThreadTask
		"""
		return WThreadTask(task_cls, thread_name=thread_name, join_timeout=join_timeout, **kwargs)

	@verify_type('strict', thread_name=(str, None), join_timeout=(int, float, None))
	@verify_value('strict', join_timeout=lambda x: x is None or x >= 0)
	@verify_subclass('strict', task_cls=WTaskProto)
	@verify_value(task=lambda x: WTaskProto.stop in x)
	def __init__(self, task_cls, thread_name=None, join_timeout=None, **kwargs):
		""" Create a threaded task

		:param task_cls: an original task that should be run in a thread. This task must have the
		'WTaskProto.stop' capability
		:type task_cls: type (WTaskProto subclass)

		:param thread_name: name of a thread to create
		:type thread_name: str | None

		:param join_timeout: if defined then this is a period of time that this task will wait for an
		original task to stop in a :meth:`.WThreadTask.stop` method.  If this values is None then
		the :meth:`.WThreadTask.stop` method wait in a block mode forever
		:type join_timeout: int | float | None

		:param kwargs: arguments with which an original task should be initialized
		"""
		WTaskProto.__init__(self)
		WSignalSource.__init__(self, *(x.value for x in WThreadTaskStatus))

		self.__task = task_cls.init_task(**kwargs)
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
				self.__switch_status(WThreadTaskStatus.crashed, signal_args=e)
				self.__exception = e

		if self.__thread is None:
			self.__switch_status(WThreadTaskStatus.started)
			self.__exception = None
			self.__thread = Thread(target=thread_target, name=self.__thread_name)
			self.__thread.start()
		else:
			raise WStartedTaskError('A thread is running already')

	@verify_type('strict', new_status=WThreadTaskStatus)
	def __switch_status(self, new_status, signal_args=None):
		""" Switch current status and send a signal

		:param new_status: new status
		:type new_status: WThreadTaskStatus

		:param signal_args: argument to a signal to send
		:type signal_args: any

		:rtype: None
		"""
		self.__status = new_status
		self.send_signal(self.__status.value, signal_args=signal_args)

	def stop(self):
		""" :meth:`.WTaskProto.stop` method implementation.

		:rtype: None
		"""
		if self.__thread is not None:
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
