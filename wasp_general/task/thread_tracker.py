# -*- coding: utf-8 -*-
# wasp_general/task/thread_tracker.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from abc import ABCMeta, abstractmethod
import traceback
from enum import Enum

from wasp_general.verify import verify_type

from wasp_general.task.thread import WThreadTask
from wasp_general.thread import WCriticalResource


class WThreadTrackerInfoStorageProto(metaclass=ABCMeta):
	""" Prototype for a storage that keeps thread task stop statuses normal stop, termination or raised
	unhandled exceptions)
	"""

	@abstractmethod
	@verify_type(task=WThreadTask, details=(str, None))
	def register_stop(self, task, task_details=None):
		""" Store stop status

		:param task: task that stopped
		:param task_details: (optional) task details - any kind of data related to the given task

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(task=WThreadTask, details=(str, None))
	def register_termination(self, task, task_details=None):
		""" Store termination status

		:param task: task that was terminated
		:param task_details: (optional) task details - any kind of data related to the given task

		:return: None
		"""
		raise NotImplementedError('This method is abstract')

	@abstractmethod
	@verify_type(task=WThreadTask, raised_exception=Exception, exception_details=str, details=(str, None))
	def register_exception(self, task, raised_exception, exception_details, task_details=None):
		""" Store exception status

		:param task: task that was terminated by unhandled exception
		:param raised_exception: unhandled exception
		:param exception_details: any kind of data related to the raised exception
		:param task_details: (optional) task details - any kind of data related to the given task

		:return: None
		"""
		raise NotImplementedError('This method is abstract')


# noinspection PyAbstractClass
class WThreadTracker(WThreadTask):
	""" Threaded task that may register its stop status (normal stop fact, task termination fact,
	unhandled exceptions)

	:note: Since there is an extra work that should be done at the task stop, this class may be inappropriate for
	low-latency situation. Also, registering termination statuses should be done quickly because of this task
	joining timeout.
	"""

	@verify_type('paranoid', thread_name=(str, None), join_on_stop=bool, thread_join_timeout=(int, float, None))
	@verify_type(tracker_storage=(WThreadTrackerInfoStorageProto, None), track_stop=bool, track_termination=bool)
	@verify_type(track_exception=bool)
	def __init__(
		self, tracker_storage=None, thread_name=None, join_on_stop=True, thread_join_timeout=None,
		track_stop=True, track_termination=True, track_exception=True
	):
		""" Create new tracker

		:param tracker_storage: storage that is used for registering statuses
		:param thread_name: same as 'thread_name' in :meth:`.WThreadTask.__init__`
		:param join_on_stop: same as 'join_on_stop' in :meth:`.WThreadTask.__init__`
		:param thread_join_timeout: same as 'thread_join_timeout' in :meth:`.WThreadTask.__init__`
		:param track_stop: whether to register stop status of this task or not
		:param track_termination: whether to register termination status of this task or not
		:param track_exception: whether to register unhandled exception or not
		"""
		WThreadTask.__init__(
			self,
			thread_name=thread_name,
			join_on_stop=join_on_stop,
			ready_to_stop=True,
			thread_join_timeout=thread_join_timeout
		)
		self.__tracker = tracker_storage
		self.__track_stop = track_stop
		self.__track_termination = track_termination
		self.__track_exception = track_exception

	def tracker_storage(self):
		""" Return linked storage

		:return: WThreadTrackerInfoStorageProto or None
		"""
		return self.__tracker

	def track_stop(self):
		""" Return True if this task is tracking "stop-status" otherwise - False

		:return: bool
		"""
		return self.__track_stop

	def track_termination(self):
		""" Return True if this task is tracking "termination-status" otherwise - False

		:return: bool
		"""
		return self.__track_termination

	def track_exception(self):
		""" Return True if this task is tracking unhandled exception otherwise - False

		:return: bool
		"""
		return self.__track_exception

	# noinspection PyMethodMayBeStatic
	def task_details(self):
		""" Return task details that should be registered with a tracker storage

		:return: str or None
		"""
		return None

	def thread_stopped(self):
		""" :meth:`.WThreadTask.thread_stopped` implementation. Register (if required) stop and termination
		status by a tracker storage

		:return: None
		"""
		tracker = self.tracker_storage()
		if tracker is not None:
			try:
				if self.ready_event().is_set() is True:
					if self.track_stop() is True:
						tracker.register_stop(self, task_details=self.task_details())
				elif self.exception_event().is_set() is False:
					if self.track_termination() is True:
						tracker.register_termination(self, task_details=self.task_details())
			except Exception as e:
				self.thread_tracker_exception(e)

	@verify_type(raised_exception=Exception)
	def thread_exception(self, raised_exception):
		""" :meth:`.WThreadTask.thread_exception` implementation. Register (if required) unhandled exception
		by a tracker storage

		:param raised_exception: unhandled exception

		:return: None
		"""
		tracker = self.tracker_storage()
		if tracker is not None:
			try:
				if self.track_exception() is True:
					tracker.register_exception(
						self,
						raised_exception,
						traceback.format_exc(),
						task_details=self.task_details()
					)
			except Exception as e:
				self.thread_tracker_exception(e)

	# noinspection PyMethodMayBeStatic
	@verify_type(raised_exception=Exception)
	def thread_tracker_exception(self, raised_exception):
		""" Method is called whenever an exception is raised during registering a status

		:param raised_exception: raised exception

		:return: None
		"""
		print('Thread tracker execution was stopped by the exception. Exception: %s' % str(raised_exception))
		print('Traceback:')
		print(traceback.format_exc())


class WSimpleTrackerStorage(WCriticalResource, WThreadTrackerInfoStorageProto):
	""" Simple :class:`.WThreadTrackerInfoStorageProto` implementation which stores statuses in a operation memory
	"""

	__critical_section_timeout__ = 1
	""" Timeout for capturing a lock for critical sections
	"""

	class RecordType(Enum):
		""" Possible status types
		"""
		stop = 1  # normal stop
		termination = 2  # termination stop
		exception = 3  # unhandled exception stop

	class Record:
		""" General record of single status
		"""

		@verify_type(thread_task=WThreadTask, task_details=(str, None))
		def __init__(self, record_type, thread_task, task_details=None):
			""" Create new record

			:param record_type: "stop-status"
			:param thread_task: original task
			:param task_details: task details
			"""
			if isinstance(record_type, WSimpleTrackerStorage.RecordType) is False:
				raise TypeError('Invalid type was specified for the record')
			self.record_type = record_type
			self.thread_task = thread_task
			self.task_details = task_details

	class ExceptionRecord(Record):
		""" Record for unhandled exception
		"""

		@verify_type('paranoid', task=WThreadTask, task_details=(str, None))
		@verify_type(exception=Exception, exception_details=str)
		def __init__(self, task, exception, exception_details, task_details=None):
			WSimpleTrackerStorage.Record.__init__(
				self, WSimpleTrackerStorage.RecordType.exception, task, task_details=task_details
			)
			self.exception = exception
			self.exception_details = exception_details

	@verify_type(records_limit=(int, None), record_stop=bool, record_termination=bool, record_exception=bool)
	def __init__(self, records_limit=None, record_stop=True, record_termination=True, record_exception=True):
		""" Create new storage

		:param records_limit: number of records to keep (if record limit is reached - new record will
		overwrite the oldest one)
		:param record_stop: whether to keep normal stop statuses or not
		:param record_termination: whether to keep termination stop statuses or not
		:param record_exception: whether to keep unhandled exceptions statuses or not
		"""
		WCriticalResource.__init__(self)
		WThreadTrackerInfoStorageProto.__init__(self)
		self.__limit = records_limit
		self.__registry = []
		self.__record_stop = record_stop
		self.__record_termination = record_termination
		self.__record_exception = record_exception

	def record_limit(self):
		""" Return maximum number of records to keep

		:return: int or None (for no limit)
		"""
		return self.__limit

	def record_stop(self):
		""" Return True if this storage is saving normal stop statuses, otherwise - False

		:return: bool
		"""
		return self.__record_stop

	def record_termination(self):
		""" Return True if this storage is saving termination stop statuses, otherwise - False

		:return: bool
		"""
		return self.__record_termination

	def record_exception(self):
		""" Return True if this storage is saving unhandled exceptions, otherwise - False

		:return: bool
		"""
		return self.__record_exception

	@verify_type(task=WThreadTask, details=(str, None))
	def register_stop(self, task, task_details=None):
		""" :meth:`.WSimpleTrackerStorage.register_stop` method implementation
		"""
		if self.record_stop() is True:
			record_type = WSimpleTrackerStorage.RecordType.stop
			record = WSimpleTrackerStorage.Record(record_type, task, task_details=task_details)
			self.__store_record(record)

	@verify_type(task=WThreadTask, details=(str, None))
	def register_termination(self, task, task_details=None):
		""" :meth:`.WSimpleTrackerStorage.register_termination` method implementation
		"""
		if self.record_termination() is True:
			record_type = WSimpleTrackerStorage.RecordType.termination
			record = WSimpleTrackerStorage.Record(record_type, task, task_details=task_details)
			self.__store_record(record)

	@verify_type(task=WThreadTask, raised_exception=Exception, exception_details=str, details=(str, None))
	def register_exception(self, task, raised_exception, exception_details, task_details=None):
		""" :meth:`.WSimpleTrackerStorage.register_exception` method implementation
		"""
		if self.record_exception() is True:
			record = WSimpleTrackerStorage.ExceptionRecord(
				task, raised_exception, exception_details, task_details=task_details
			)
			self.__store_record(record)

	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def __store_record(self, record):
		""" Save record in a internal storage

		:param record: record to save

		:return: None
		"""
		if isinstance(record, WSimpleTrackerStorage.Record) is False:
			raise TypeError('Invalid record type was')
		limit = self.record_limit()
		if limit is not None and len(self.__registry) >= limit:
			self.__registry.pop(0)
		self.__registry.append(record)

	@WCriticalResource.critical_section(timeout=__critical_section_timeout__)
	def __registry_copy(self):
		""" Return copy of tracked statuses

		:return: list of WSimpleTrackerStorage.Record
		"""
		return self.__registry.copy()

	def __iter__(self):
		""" Iterate over registered statuses (WSimpleTrackerStorage.Record). The newest record will be yield
		the first

		:return: generator
		"""
		registry = self.__registry_copy()
		registry.reverse()
		for record in registry:
			yield record
