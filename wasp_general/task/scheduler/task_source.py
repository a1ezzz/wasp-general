# -*- coding: utf-8 -*-
# wasp_general/task/scheduler/task_source.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from datetime import datetime, timedelta, MAXYEAR, timezone
from calendar import monthrange, weekday

from wasp_general.verify import verify_type, verify_value
from wasp_general.datetime import utc_datetime
from wasp_general.thread import WCriticalResource

from wasp_general.task.scheduler.proto import WTaskSourceProto, WTaskSchedule, WScheduledTask, WTaskSchedulerProto


class WCronSchedule:

	__calendar__ = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

	@verify_type(start_datetime=(datetime, None), minute=(int, None), hour=(int, None), day_of_month=(int, None))
	@verify_type(day_of_week=(int, None), month=(int, None))
	@verify_value(minute=lambda x: x is None or (0 <= x <= 59))
	@verify_value(hour=lambda x: x is None or (0 <= x <= 23))
	@verify_value(day_of_month=lambda x: x is None or (1 <= x <= 31))
	@verify_value(day_of_week=lambda x: x is None or (1 <= x <= 7))
	@verify_value(month=lambda x: x is None or (1 <= x <= 12))
	def __init__(self, start_datetime=None, minute=None, hour=None, day_of_month=None, day_of_week=None, month=None):

		if month is not None and day_of_month is not None and day_of_month > WCronSchedule.__calendar__[month]:
			raise ValueError('Invalid day and month combination')

		self.__start_datetime = start_datetime if start_datetime is not None else self.now()
		self.__next_start = None

		self.__minute = minute
		self.__hour = hour
		self.__day_of_month = day_of_month
		self.__day_of_week = day_of_week
		self.__month = month

		self.update()

	def start_datetime(self):
		return self.__start_datetime

	@verify_type(start_datetime=datetime)
	def _set_start_datetime(self, start_datetime):
		self.__start_datetime = start_datetime
		self.__next_start = None

	@verify_type('paranoid', year=int, month=int, day=int, hour=int, minute=int)
	@verify_value('paranoid', year=lambda x: x > 0)
	@verify_value('paranoid', month=lambda x: x is None or (1 <= x <= 12))
	@verify_value('paranoid', day=lambda x: x is None or (1 <= x <= 31))
	@verify_value('paranoid', hour=lambda x: x is None or (0 <= x <= 23))
	@verify_value('paranoid', minute=lambda x: x is None or (0 <= x <= 59))
	def _datetime(self, year, month, day, hour, minute):
		return datetime(year, month, day, hour, minute)

	def next_start(self):
		return self.__next_start

	def minute(self):
		return self.__minute

	def hour(self):
		return self.__hour

	def day_of_month(self):
		return self.__day_of_month

	def day_of_week(self):
		return self.__day_of_week

	def month(self):
		return self.__month

	def no_frequency(self):
		result = self.minute() is None and self.hour() is None and self.day_of_month() is None
		return result is True and self.day_of_week() is None and self.month() is None

	def final_datetime(self):
		return datetime(MAXYEAR, 12, 31, 23, 59)

	@classmethod
	def now(cls):
		return datetime.now()

	def update(self):
		if self.no_frequency() is True:
			return

		for (year, month) in self.month_iterator():
			for day in self.day_iterator(year, month):
				for (hour, minute) in self.time_iterator(year, month, day):
					self.__next_start = self._datetime(year, month, day, hour, minute)
					return

	@verify_type(omit_skipped=bool)
	def complete(self, omit_skipped=True):
		if self.no_frequency() is True:
			return

		next_start = self.next_start()
		seconds_last_minute = next_start.second
		seconds_last_hour = (next_start.minute * 60) + seconds_last_minute
		seconds_last_day = (next_start.hour * 24 * 60 * 60) + seconds_last_hour
		time_shift = 0
		if self.month() is not None:
			year = next_start.year
			month = next_start.month
			if month < 12:
				month += 1
			else:
				year += 1
				month = 1
			time_shift = (self._datetime(year, month, 1, 0, 0) - next_start).total_seconds()
		elif self.day_of_week() is not None:
			time_shift = (7 * 24 * 60 * 60) - seconds_last_day
		elif self.day_of_month() is not None:
			time_shift = (24 * 60 * 60) - seconds_last_day
		elif self.hour() is not None:
			time_shift = (60 * 60) - seconds_last_hour
		elif self.minute() is not None:
			time_shift = 60 - seconds_last_minute

		time_shift += 1
		new_start = next_start + timedelta(seconds=time_shift)
		if omit_skipped is True:
			now = self.now()
			if now > new_start:
				new_start = now

		self._set_start_datetime(new_start)
		self.update()

	def month_iterator(self):
		if self.no_frequency():
			return

		start_datetime = self.start_datetime()
		start_year = start_datetime.year
		start_month = start_datetime.month

		final_datetime = self.final_datetime()
		max_year = final_datetime.year
		max_month = final_datetime.month

		month = self.month()
		year = start_year

		if month is not None:
			if month < start_month:
				year += 1

			if year > max_year or (year == max_year and month > max_month):
				return

			while year < max_year or (year == max_year and month < max_month):
				yield ((year, month))
				year += 1

		else:  # month is None
			month = start_month
			while year < max_year or (year == max_year and month < max_month):
				yield ((year, month))

				if month < 12:
					month += 1
				else:
					year += 1
					month = 1

	def day_iterator(self, year, month):
		if self.no_frequency():
			return

		start_datetime = self.start_datetime()
		days_in_month = monthrange(year, month)[1]

		day_of_month = self.day_of_month()
		day_of_week = self.day_of_week()

		final_datetime = self.final_datetime()
		if year == final_datetime.year and month == final_datetime.month:
			days_in_month = final_datetime.day

		start_day = start_datetime.day
		if year != start_datetime.year or month != start_datetime.month:
			start_day = 1

		if day_of_month is None and day_of_week is None:
			day = start_day
			while day <= days_in_month:
				yield day
				day += 1
		elif day_of_month is not None and day_of_week is None:
			if start_day <= days_in_month:
				yield day_of_month
		elif day_of_month is not None and day_of_week is not None:
			if start_day <= days_in_month and weekday(year, month, day_of_month) == day_of_week:
				yield day_of_month
		else:  # day_of_month is None and day_of_week is not None
			current_weekday = weekday(year, month, start_day)

			delta = day_of_week - current_weekday
			if delta < 0:
				delta += 7
			day = start_day + delta

			while day <= days_in_month:
				yield day
				day += 7

	def time_iterator(self, year, month, day):
		start_datetime = self.start_datetime()
		max_hour = 23
		max_minute = 59

		hour = self.hour()
		minute = self.minute()

		final_datetime = self.final_datetime()
		if year == final_datetime.year and month == final_datetime.month and day == self.final_datetime():
			max_hour = final_datetime.hour
			max_minute = final_datetime.minute

		start_hour = start_datetime.hour
		start_minute = start_datetime.minute
		if year != start_datetime.year or month != start_datetime.month or day != start_datetime.day:
			start_hour = 0
			start_minute = 0

		if hour is None and minute is None:
			hour = start_hour
			minute = start_minute
			while start_hour <= hour < max_hour or (hour == max_hour and start_minute <= minute <= max_minute):
				yield ((hour, minute))
				if minute < 59:
					minute += 1
				else:
					minute = 0
					hour += 1
		elif hour is not None and minute is None:
			minute = start_minute
			if start_hour <= hour <= max_hour:
				while minute <= max_minute:
					yield ((hour, minute))
					minute += 1
		elif hour is not None and minute is not None:
			if start_hour <= hour < max_hour or (hour == max_hour and start_minute <= minute <= max_minute):
				yield ((hour, minute))
		else:  # hour is None and minute is not None
			hour = start_hour
			if start_minute > minute:
				hour += 1

			while start_hour <= hour < max_hour or (hour == max_hour and start_minute <= minute <= max_minute):
				yield ((hour, minute))
				hour += 1

	@classmethod
	@verify_type(scheduled=str)
	def from_string(cls, scheduled):
		return cls.from_string_tokens(*filter(lambda x: len(x) > 0, scheduled.strip().split(' ')))

	@classmethod
	@verify_type(tokens=str)
	def from_string_tokens(cls, *tokens):
		if len(tokens) != 5:
			raise ValueError('Malformed cron-schedule')

		tokens = [int(x) if x != '*' else None for x in tokens]

		if len(tokens) != 5:
			raise ValueError('Malformed cron-schedule')
		return cls(
			cls.now(), minute=tokens[0], hour=tokens[1], day_of_month=tokens[2], day_of_week=tokens[3],
			month=tokens[4]
		)


class WCronLocalTZSchedule(WCronSchedule):
	pass


class WCronUTCSchedule(WCronSchedule):

	@verify_type('paranoid', start_datetime=(datetime, None), minute=(int, None), hour=(int, None))
	@verify_type('paranoid', day_of_month=(int, None), day_of_week=(int, None), month=(int, None))
	@verify_value('paranoid', minute=lambda x: x is None or (0 <= x <= 59))
	@verify_value('paranoid', hour=lambda x: x is None or (0 <= x <= 23))
	@verify_value('paranoid', day_of_month=lambda x: x is None or (1 <= x <= 31))
	@verify_value('paranoid', day_of_week=lambda x: x is None or (1 <= x <= 7))
	@verify_value('paranoid', month=lambda x: x is None or (1 <= x <= 12))
	@verify_value(start_datetime=lambda x: x.tzinfo is not None and x.tzinfo == timezone.utc)
	def __init__(self, start_datetime=None, minute=None, hour=None, day_of_month=None, day_of_week=None, month=None):
		WCronSchedule.__init__(
			self, start_datetime, minute=minute, hour=hour, day_of_month=day_of_month,
			day_of_week=day_of_week, month=month
		)

	@verify_type(start_datetime=datetime)
	@verify_value(start_datetime=lambda x: x.tzinfo is not None and x.tzinfo == timezone.utc)
	def _set_start_datetime(self, start_datetime):
		WCronSchedule._set_start_datetime(self, start_datetime)

	@verify_type('paranoid', year=int, month=int, day=int, hour=int, minute=int)
	@verify_value('paranoid', year=lambda x: x > 0)
	@verify_value('paranoid', month=lambda x: x is None or (1 <= x <= 12))
	@verify_value('paranoid', day=lambda x: x is None or (1 <= x <= 31))
	@verify_value('paranoid', hour=lambda x: x is None or (0 <= x <= 23))
	@verify_value('paranoid', minute=lambda x: x is None or (0 <= x <= 59))
	def _datetime(self, year, month, day, hour, minute):
		return utc_datetime(datetime(year, month, day, hour, minute), local_value=False)

	@classmethod
	def now(cls):
		return utc_datetime()


class WCronTaskSchedule(WTaskSchedule):

	@verify_type('paranoid', task=WScheduledTask, task_id=(str, None))
	@verify_value('paranoid', on_drop=lambda x: x is None or callable(x))
	@verify_type(schedule=WCronSchedule, omit_skipped=bool)
	@verify_value(schedule=lambda x: isinstance(x, WCronLocalTZSchedule) or isinstance(x, WCronUTCSchedule))
	def __init__(self, cron_schedule, task, policy=None, task_id=None, on_drop=None, omit_skipped=True):
		WTaskSchedule.__init__(self, task, policy=policy, task_id=task_id, on_drop=on_drop)
		self.__schedule = cron_schedule
		self.__omit_skipped = omit_skipped

	def cron_schedule(self):
		return self.__schedule

	def next_start(self):
		cron = self.cron_schedule()
		next_start = cron.next_start()
		if isinstance(cron, WCronLocalTZSchedule):
			return utc_datetime(dt=next_start)
		elif isinstance(cron, WCronUTCSchedule):
			return next_start
		raise RuntimeError('Corrupted object!')

	def complete(self):
		self.cron_schedule().complete(omit_skipped=self.__omit_skipped)


class WCronTaskSource(WTaskSourceProto, WCriticalResource):
	# TODO: fix next_start() can return None

	@verify_type(scheduler=WTaskSchedulerProto)
	def __init__(self, scheduler):
		WTaskSourceProto.__init__(self)
		WCriticalResource.__init__(self)
		self.__scheduler = scheduler
		self.__tasks = []
		self.__next_task = None

	def scheduler(self):
		return self.__scheduler

	@verify_type(task=WCronTaskSchedule)
	def add_task(self, task):
		self.__add_task(task)
		self.scheduler().update(task_source=self)

	@WCriticalResource.critical_section()
	@verify_type('paranoid', task=WCronTaskSchedule)
	def __add_task(self, task):
		self.__tasks.append(task)
		self.__update(task)

	@verify_type('paranoid', task=(WCronTaskSchedule, None))
	def __update(self, task=None):
		if task is not None:
			next_start = task.next_start()
			if self.__next_task is None or next_start < self.__next_task.next_start():
				self.__next_task = task
		elif len(self.__tasks) > 0:
			next_task = self.__tasks[0]
			for task in self.__tasks[1:]:
				if task.next_start() < next_task.next_start():
					next_task = task
			self.__next_task = next_task
		else:
			self.__next_task = None

	@WCriticalResource.critical_section()
	def tasks_planned(self):
		return len(self.__tasks)

	@WCriticalResource.critical_section()
	def has_tasks(self):
		if self.__next_task is not None and self.__next_task.next_start() <= utc_datetime():
			result = [self.__next_task]
			self.__next_task.complete()
			self.__update()
			return tuple(result)

	@WCriticalResource.critical_section()
	def next_start(self):
		if self.__next_task is not None:
			return self.__next_task.next_start()
