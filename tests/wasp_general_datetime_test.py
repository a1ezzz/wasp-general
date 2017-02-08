# -*- coding: utf-8 -*-

import datetime
import time

from wasp_general.datetime import local_tz, utc_datetime, local_datetime


def test_datetime():
	now_dt = utc_datetime()
	assert(now_dt.timetz().tzinfo == datetime.timezone.utc)

	test_dt = datetime.datetime(1970, 9, 8, 7, 0)
	utc_test_dt = utc_datetime(test_dt)
	assert(utc_test_dt.timetz().tzinfo == datetime.timezone.utc)
	assert(utc_test_dt.utcoffset().seconds == 0)

	compare_utc_test_dt = test_dt + datetime.timedelta(seconds=time.timezone)
	assert(compare_utc_test_dt.year == utc_test_dt.year)
	assert(compare_utc_test_dt.month == utc_test_dt.month)
	assert(compare_utc_test_dt.day == utc_test_dt.day)
	assert(compare_utc_test_dt.hour == utc_test_dt.hour)
	assert(compare_utc_test_dt.minute == utc_test_dt.minute)
	assert(compare_utc_test_dt.second == utc_test_dt.second)

	utc_test_dt = utc_datetime(test_dt, local_value=False)
	assert(utc_test_dt.timetz().tzinfo == datetime.timezone.utc)
	assert(utc_test_dt.year == 1970)
	assert(utc_test_dt.month == 9)
	assert(utc_test_dt.day == 8)
	assert(utc_test_dt.hour == 7)
	assert(utc_test_dt.minute == 0)
	assert(utc_test_dt.second == 0)

	now_dt = local_datetime()
	assert(now_dt.utcoffset().seconds == (time.timezone * -1))

	local_test_dt = local_datetime(test_dt)
	assert(local_test_dt.timetz().utcoffset().seconds == (time.timezone * -1))
	compare_local_test_dt = test_dt + datetime.timedelta(seconds=(time.timezone * -1))
	assert(compare_local_test_dt.year == local_test_dt.year)
	assert(compare_local_test_dt.month == local_test_dt.month)
	assert(compare_local_test_dt.day == local_test_dt.day)
	assert(compare_local_test_dt.hour == local_test_dt.hour)
	assert(compare_local_test_dt.minute == local_test_dt.minute)
	assert(compare_local_test_dt.second == local_test_dt.second)

	local_test_dt = local_datetime(test_dt, utc_value=False)
	assert(local_test_dt.timetz().utcoffset().seconds == (time.timezone * -1))
	assert(local_test_dt.year == 1970)
	assert(local_test_dt.month == 9)
	assert(local_test_dt.day == 8)
	assert(local_test_dt.hour == 7)
	assert(local_test_dt.minute == 0)
	assert(local_test_dt.second == 0)
