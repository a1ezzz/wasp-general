# -*- coding: utf-8 -*-
# wasp_general/config.py
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

from configparser import ConfigParser
import os

from wasp_general.verify import verify_type, verify_value


class WConfig(ConfigParser):
	""" Improved ConfigParser. Has single method to merge config data (see :meth:`.WConfig.merge` method) and
	method, that split coma-separated option value (see :meth:`.WConfig.split_option` method).
	"""

	@verify_type(section=str, option=str)
	def split_option(self, section, option):
		""" Return list of strings that are made by splitting coma-separated option value. Method returns
		empty list if option value is empty string

		:param section: option section name
		:param option: option name
		:return: list of strings
		"""
		value = self[section][option].strip()
		if value == "":
			return []
		return [x.strip() for x in (value.split(","))]

	@verify_type(config=(str, ConfigParser))
	@verify_value(config=lambda x: isinstance(x, ConfigParser) or os.path.isfile(x))
	def merge(self, config):
		""" Load configuration from given configuration.

		:param config: config to load. If config is a string type, then it's treated as .ini filename
		:return: None
		"""
		if isinstance(config, ConfigParser) is True:
			self.update(config)
		elif isinstance(config, str):
			self.read(config)
