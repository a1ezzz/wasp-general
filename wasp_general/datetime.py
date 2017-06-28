# -*- coding: utf-8 -*-
# wasp_general/datetime.py
#
# Copyright (C) 2016 the wasp-general authors and contributors
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

import time
from datetime import datetime, timezone, timedelta

from wasp_general.verify import verify_type


def local_tz():
	""" Return current system timezone shift from UTC

	:return: datetime.timezone
	"""
	return timezone(timedelta(0, (time.timezone * -1)))


@verify_type(dt=(datetime, None), local_value=bool)
def utc_datetime(dt=None, local_value=True):
	""" Convert local datetime and/or datetime without timezone information to UTC datetime with timezone
	information.

	:param dt: local datetime to convert. If is None, then system datetime value is used
	:param local_value: whether dt is a datetime in system timezone or UTC datetime without timezone information
	:return: datetime in UTC with tz set
	"""
	# TODO: rename local_value to local_tz or in_local_tz
	if dt is None:
		return datetime.now(tz=timezone.utc)

	result = dt
	if result.utcoffset() is None:
		if local_value is False:
			return result.replace(tzinfo=timezone.utc)
		else:
			result = result.replace(tzinfo=local_tz())

	return result.astimezone(timezone.utc)


@verify_type(dt=(datetime, None), utc_value=bool)
def local_datetime(dt=None, utc_value=True):
	""" Convert UTC datetime and/or datetime without timezone information to local datetime with timezone
	information

	:param dt: datetime in UTC to convert. If is None, then system datetime value is used
	:param utc_value: whether dt is a datetime in UTC or in system timezone without timezone information
	:return: datetime for system (local) timezone with tz set
	"""
	# TODO: rename utc_value to utc_tz or in_utc_tz
	if dt is None:
		return datetime.now(tz=local_tz())

	result = dt
	if result.utcoffset() is None:
		if utc_value is False:
			return result.replace(tzinfo=local_tz())
		else:
			result = result.replace(tzinfo=timezone.utc)

	return result.astimezone(local_tz())
