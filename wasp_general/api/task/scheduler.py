# -*- coding: utf-8 -*-
# wasp_general/api/task/scheduler.py
#
# Copyright (C) 2017-2019, 2022 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

import datetime

from wasp_c_extensions.ev_loop import WEventLoop
from wasp_c_extensions.threads import WAtomicCounter

from wasp_general.api.signals import WSignalSource, WSignal, WEventLoopCallbacks

from wasp_general.thread import WCriticalResource
from wasp_general.verify import verify_type, verify_value

from wasp_general.api.task.proto import WTaskProto, WScheduledTaskPostponePolicy, WScheduleRecordProto
from wasp_general.api.task.proto import WScheduleSourceProto, WScheduledTaskResult, WSchedulerProto, WTaskResult
from wasp_general.api.task.thread import WThreadTask


class WScheduleRecord(WScheduleRecordProto):
	""" The :class:`.WScheduleRecordProto` implementation. Implementation is pretty straightforward
	"""

	@verify_type('strict', task=WTaskProto, group_id=(str, None), ttl=(int, float, None))
	@verify_type('strict', simultaneous_policy=(int, None), postpone_policy=WScheduledTaskPostponePolicy)
	def __init__(
		self, task, group_id=None, ttl=None, simultaneous_policy=None,
		postpone_policy=WScheduledTaskPostponePolicy.wait
	):
		""" Create a new record

		:param task: a task to execute
		:type task: WTaskProto

		:param group_id: record's group id. Please read :meth:`.WScheduleRecordProto.group_id`
		:type group_id: str | None

		:param ttl: record's ttl
		:type ttl: int | float | None

		:param simultaneous_policy: how many records with the same group_id should be running at the moment
		:type simultaneous_policy: int | None

		:param postpone_policy: what should be done if this record will be postponed
		:type postpone_policy: WScheduledTaskPostponePolicy
		"""
		self.__task = task
		self.__group_id = group_id
		self.__ttl = ttl
		self.__simultaneous_policy = simultaneous_policy if simultaneous_policy is not None else 0
		self.__postpone_policy = postpone_policy

	def task(self):
		""" The :meth:`.WScheduleRecordProto.task` method implementation

		:rtype: WTaskProto
		"""
		return self.__task

	def group_id(self):
		""" The :meth:`.WScheduleRecordProto.group_id` method implementation

		:rtype: str | None
		"""
		return self.__group_id

	def ttl(self):
		""" The :meth:`.WScheduleRecordProto.ttl` method implementation

		:rtype: int | float | None
		"""
		return self.__ttl

	def simultaneous_policy(self):
		""" The :meth:`.WScheduleRecordProto.simultaneous_policy` method implementation

		:rtype: int | None
		"""
		return self.__simultaneous_policy

	def postpone_policy(self):
		""" The :meth:`.WScheduleRecordProto.postpone_policy` method implementation

		:rtype: WScheduledTaskPostponePolicy
		"""
		return self.__postpone_policy


class WSchedulerThreadExecutor(WSignalSource):
	""" This class is used along with the :class:`.WScheduler` which is the :class:`.WSchedulerProto` class
	implementation. This class allow to execute records and track them.

	:note: Methods in this class are not thread safe, because all methods and signals are used or processed within a
	single thread inside a loop in the :class:`.WScheduler` class
	"""

	record_processed = WSignal(WScheduleRecordProto)  # record processing is finished
	task_started = WSignal(WScheduleRecordProto)      # a scheduled record started
	task_completed = WSignal(WScheduledTaskResult)    # a scheduled record completed
	task_stopped = WSignal(None)                      # a stop request for a scheduled task completed

	@verify_type('strict', wev_loop=WEventLoop)
	def __init__(self, wev_loop):
		""" Create a new executor

		:param wev_loop: a loop with which all internals callbacks will be called
		:type wev_loop: WEventLoop
		"""
		WSignalSource.__init__(self)
		self.__callbacks = WEventLoopCallbacks(wev_loop)
		self.__running_records = dict()

	def running_records(self):
		""" Return records that are running at the moment

		:rtype: tuple of str
		"""
		return tuple(self.__running_records.keys())

	@verify_type('strict', record=WScheduleRecordProto)
	def stop_record(self, record):
		""" Stop execution of a record that is running

		:note: This method must be called when origin loop is stopped in order not to interfere with callbacks!

		:param record: record to stop
		:type record: WScheduleRecordProto

		TODO: check raise!!!!!
		:rtype: None
		"""
		if self.__callbacks.loop().is_started():
			raise RuntimeError('Unable to stop a record because of a running loop (callbacks may interfere)')
		threaded_task = self.__running_records.pop(record)
		threaded_task.stop()

	@verify_type('strict', record=WScheduleRecordProto)
	def execute(self, record):
		""" Execute a new record

		:param record: a record to start
		:type record: WScheduleRecordProto

		:rtype: None
		"""
		task = record.task()
		threaded_task = WThreadTask(task, thread_name='Scheduler record execution')

		def callback(signal_source, signal, signal_value=None):
			nonlocal record

			if signal == WThreadTask.threaded_task_started:
				self.emit(self.task_started, record)
			elif signal == WThreadTask.threaded_task_completed:
				self.emit(self.task_completed, WScheduledTaskResult(record=record, task_result=signal_value.result))
				signal_source.stop()  # stop (and join) a WThreadTask, this also emits WThreadTask.task_stopped
			elif signal == WThreadTask.task_stopped:
				# this routine work till the origin loop exists, so it doesn't interfere with the
				# :meth:`.WSchedulerThreadExecutor.stop_all` method
				self.emit(self.task_stopped, record)
				self.__running_records.pop(record)
				self.emit(self.record_processed, record)

		self.__callbacks.register(threaded_task, WThreadTask.threaded_task_started, callback)
		self.__callbacks.register(threaded_task, WThreadTask.threaded_task_completed, callback)
		self.__callbacks.register(threaded_task, WThreadTask.task_stopped, callback)

		threaded_task.start()
		self.__running_records[record] = threaded_task


class WSchedulerPostponeQueue(WSignalSource):
	""" This class is used along with the :class:`.WScheduler` which is the :class:`.WSchedulerProto` class
	implementation. This class allow to postpone records.

	:note: Methods in this class are not thread safe, because all methods and signals are used or processed within a
	single thread inside a loop in the :class:`.WScheduler` class
	"""

	task_dropped = WSignal(WScheduleRecordProto)    # a scheduled task dropped and would not start
	task_postponed = WSignal(WScheduleRecordProto)  # a scheduled task dropped and will start later
	task_expired = WSignal(WScheduleRecordProto)    # a scheduled task dropped because of expired ttl

	def __init__(self):
		""" Create a new queue with postpone records
		"""
		WSignalSource.__init__(self)
		self.__postponed_records = []

	@verify_type('strict', group_id=str)
	def __drop_all(self, group_id):
		""" Drop from a queue all record with the specified group_id

		:param group_id: id of a group which records should be dropped
		:type group_id: str

		:rtype: None
		"""
		dropped_records = 0
		for i in range(len(self.__postponed_records)):
			check_record = self.__postponed_records[i - dropped_records]
			if check_record.group_id() == group_id:
				self.__postponed_records.pop(i - dropped_records)
				dropped_records += 1
				self.emit(self.task_dropped, check_record)

	@verify_type('strict', group_id=str)
	def __keep_first(self, group_id):
		""" Try to keep the earliest record of the same group. Other records of the same group will be dropped

		:param group_id: id of a group which records should be dropped (all but the earliest)
		:type group_id: str

		:return: return True if the earliest record was found and return False otherwise
		:rtype: bool
		"""
		first_found = False
		dropped_records = 0
		for i in range(len(self.__postponed_records)):
			check_record = self.__postponed_records[i - dropped_records]
			if check_record.group_id() == group_id:
				if first_found:
					self.__postponed_records.pop(i - dropped_records)
					self.emit(self.task_dropped, check_record)
					dropped_records += 1
				else:
					first_found = True
		return first_found

	@verify_type('strict', record=WScheduleRecordProto)
	def postpone(self, record):
		""" Postpone a record (or drop it because of policy and/or ttl)

		:param record: record to postpone
		:type record: WScheduleRecordProto

		:rtype: None
		"""
		ttl = record.ttl()
		group_id = record.group_id()
		postpone_policy = record.postpone_policy()

		if postpone_policy == WScheduledTaskPostponePolicy.drop:
			self.emit(self.task_dropped, record)
			return

		if ttl is not None and ttl < datetime.datetime.utcnow().timestamp():
			self.emit(self.task_expired, record)
			return

		if postpone_policy == WScheduledTaskPostponePolicy.wait or group_id is None:
			self.__postponed_records.append(record)
			self.emit(self.task_postponed, record)
			return

		if postpone_policy == WScheduledTaskPostponePolicy.keep_last:
			self.__drop_all(group_id)
			self.__postponed_records.append(record)
			self.emit(self.task_postponed, record)
			return

		if postpone_policy == WScheduledTaskPostponePolicy.keep_first:
			if not self.__keep_first(group_id):
				self.__postponed_records.append(record)
				self.emit(self.task_postponed, record)
			else:
				self.emit(self.task_dropped, record)

	@verify_value('strict', filter_fn=lambda x: x is None or callable(x))
	def next_record(self, filter_fn=None):
		""" Get record from a queue to be executed next. The earliest records win, but not always

		:param filter_fn: check a record with this function. If record is suitable then this function should return
		True and False otherwise
		:type filter_fn: callable

		:return: return a record that should be executed next or return None if no suitable record is found
		:rtype: WScheduleRecordProto | None
		"""

		utc_now = datetime.datetime.utcnow().timestamp()
		dropped_records = 0

		for i in range(len(self.__postponed_records)):
			record = self.__postponed_records[i - dropped_records]

			ttl = record.ttl()
			if ttl is not None and ttl < utc_now:
				self.__postponed_records.pop(i - dropped_records)
				self.emit(self.task_expired, record)
				dropped_records += 1
				continue

			if filter_fn and not filter_fn(record):
				continue

			self.__postponed_records.pop(i - dropped_records)
			return record


class WScheduler(WSchedulerProto, WCriticalResource):
	"""  The :class:`.WSchedulerProto` class implementation

	:note: This implementation is thread safe mostly (record may be scheduled and may be processed at any moment).
	But two methods are not thread safe enough -- :meth:`.WScheduler.start` and :meth:`.WScheduler.stop`.

	!!! TODO: update!!! MAKE IT SAFE!!!!
	So there
	should be a protection in order not to call the start twice or to call stop during a start preparation
	"""

	__critical_section_timeout__ = 5
	""" Timeout with which critical section lock must be acquired
	"""

	@verify_type('strict', max_threads=int)
	@verify_value('strict', max_threads=lambda x: x > 0, callback_exception_handler=lambda x: x is None or callable(x))
	def __init__(self, max_threads, callback_exception_handler=None):
		""" Create a new scheduler

		:param max_threads: number of threads to be running simultaneously
		:type max_threads: int

		:param callback_exception_handler: handler that may process exceptions that are risen inside a loop
		:type callback_exception_handler: callable | None
		"""
		WSchedulerProto.__init__(self)
		WCriticalResource.__init__(self)
		self.__callback_exc_hr = callback_exception_handler

		self.__wev_loop = WEventLoop(immediate_stop=False)
		self.__callbacks = WEventLoopCallbacks(self.__wev_loop)
		self.__thread_slots = WAtomicCounter(max_threads, negative=False)
		self.__thread_executor = WSchedulerThreadExecutor(self.__wev_loop)
		self.__postpone_queue = WSchedulerPostponeQueue()

		self.__sources = set()

	def start(self):
		""" Start this scheduler (and an inside loop for callbacks processing)

		:rtype: None
		"""
		self.emit(self.task_started)

		self.__init_callbacks()

		try:
			self.__wev_loop.start_loop()
		except Exception as e:
			if self.__callback_exc_hr:
				self.__callback_exc_hr(e)
			else:
				raise
		finally:
			# there is an exception or a stop request, so finalize

			next_record = self.__postpone_queue.next_record()
			while next_record:
				self.emit(self.scheduled_task_dropped, next_record)
				next_record = self.__postpone_queue.next_record()

			for r in self.__thread_executor.running_records():
				self.__thread_executor.stop_record(r)
				self.emit(self.scheduled_task_stopped, r)
				self.__thread_slots.increase_counter(1)

			self.__fini_callbacks()
			self.emit(self.task_completed, WTaskResult())
			self.emit(self.task_stopped)

	def stop(self):
		"""

		:rtype: None
		"""
		# :note: may be called (and will be called from a different thread!)
		with self.critical_context(timeout=self.__critical_section_timeout__):
			for s in self.__sources:
				self.__callbacks.unregister(s, WScheduleSourceProto.task_scheduled, self.__task_scheduled_callback)
			self.__sources.clear()

		self.__wev_loop.stop_loop()

	@verify_type('strict', schedule_source=WScheduleSourceProto)
	def subscribe(self, schedule_source):
		self.__callbacks.register(
			schedule_source, WScheduleSourceProto.task_scheduled, self.__task_scheduled_callback
		)
		with self.critical_context(timeout=self.__critical_section_timeout__):
			self.__sources.add(schedule_source)

	@verify_type('strict', schedule_source=WScheduleSourceProto)
	def unsubscribe(self, schedule_source):
		self.__callbacks.unregister(
			schedule_source, WScheduleSourceProto.task_scheduled, self.__task_scheduled_callback
		)
		with self.critical_context(timeout=self.__critical_section_timeout__):
			self.__sources.remove(schedule_source)

	@verify_type('strict', record=WScheduleRecordProto)
	def __record_filter(self, record):
		simultaneous_policy = record.simultaneous_policy()
		group_id = record.group_id()
		group_counter = 0

		if simultaneous_policy and group_id:
			for r in self.__thread_executor.running_records():

				r_group_id = r.group_id()
				if r_group_id == group_id:
					group_counter += 1

				if group_counter >= simultaneous_policy:
					return False
		return True

	def __task_scheduled_callback(self, signal_source, signal, signal_value=None):
		self.emit(WSchedulerProto.task_scheduled, signal_value)

		if not self.__record_filter(signal_value):
			self.__postpone_queue.postpone(signal_value)
			return

		try:
			self.__thread_slots.increase_counter(-1)
		except ValueError:
			self.__postpone_queue.postpone(signal_value)
			return

		try:
			self.__thread_executor.execute(signal_value)
		except Exception:
			self.__thread_slots.increase_counter(1)
			raise

	def __record_processed_callback(self, signal_source, signal, signal_value=None):
		try:
			record = self.__postpone_queue.next_record(self.__record_filter)
			if record:
				self.__thread_executor.execute(record)
		except Exception:
			self.__thread_slots.increase_counter(1)
			raise

		if not record:
			self.__thread_slots.increase_counter(1)

	def __init_callbacks(self):
		self.__callbacks.register(
			self.__thread_executor, WSchedulerThreadExecutor.record_processed, self.__record_processed_callback
		)

		# WSchedulerThreadExecutor signals proxy
		self.__callbacks.proxy(
			self.__thread_executor, WSchedulerThreadExecutor.task_started, self, self.scheduled_task_started
		)
		self.__callbacks.proxy(
			self.__thread_executor, WSchedulerThreadExecutor.task_stopped, self, self.scheduled_task_stopped
		)
		self.__callbacks.proxy(
			self.__thread_executor, WSchedulerThreadExecutor.task_completed, self, self.scheduled_task_completed
		)

		# WSchedulerPostponeQueue signals proxy
		self.__callbacks.proxy(
			self.__postpone_queue, WSchedulerPostponeQueue.task_postponed, self, self.scheduled_task_postponed
		)
		self.__callbacks.proxy(
			self.__postpone_queue, WSchedulerPostponeQueue.task_dropped, self, self.scheduled_task_dropped
		)
		self.__callbacks.proxy(
			self.__postpone_queue, WSchedulerPostponeQueue.task_expired, self, self.scheduled_task_expired
		)

	def __fini_callbacks(self):
		self.__callbacks.clear()
