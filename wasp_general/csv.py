# -*- coding: utf-8 -*-
# wasp_general/csv.py
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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import csv

from wasp_general.verify import verify_type, verify_value


class WCSVExporter:

	@verify_type(titles=bool)
	def __init__(self, output_obj, titles=True, **csv_fmtparams):
		self.__output_obj = output_obj
		self.__titles = titles
		self.__csv_fmtparams = csv_fmtparams
		self.__csv_writer = None
		self.__omitted_fields = set()

	def output_obj(self):
		return self.__output_obj

	def titles(self):
		return self.__titles

	def csv_fmtparams(self):
		return self.__csv_fmtparams

	@verify_type(field_name=str)
	@verify_value(field_name=lambda x: len(x) > 0)
	def omit_field(self, field_name):
		self.__omitted_fields.add(field_name)

	def omitted_fields(self):
		return tuple(self.__omitted_fields)

	@verify_type(dict_record=dict)
	def export(self, dict_record):
		dict_record = self.__filter_field(dict_record)
		if self.__csv_writer is None:
			self.export_titles(dict_record)
		self.__check_record(dict_record)
		self.__csv_writer.writerow(dict_record)

	@verify_type(dict_record=dict)
	def export_titles(self, dict_record):
		if self.__csv_writer is not None:
			raise RuntimeError('Unable to export titles multiple time')
		fields = dict_record.keys()
		self.__csv_writer = csv.DictWriter(self.output_obj(), fieldnames=fields, **self.csv_fmtparams())
		if self.titles() is True:
			self.__csv_writer.writeheader()

	@verify_type(dict_record=dict)
	def __filter_field(self, dict_record):
		result = dict_record.copy()
		for field in self.omitted_fields():
			if field in result.keys():
				result.pop(field)
		return result

	@verify_type(dict_record=dict)
	def __check_record(self, dict_record):
		for key, value in dict_record.items():
			if isinstance(key, str) is False:
				raise TypeError('Invalid field name')
			if value is not None and isinstance(value, (str, int, float)) is False:
				raise TypeError('Invalid value for field "%s"' % key)
