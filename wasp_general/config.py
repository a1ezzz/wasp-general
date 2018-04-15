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

from configparser import ConfigParser, NoOptionError, NoSectionError
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

	@verify_type(config=ConfigParser, section_to=str, section_from=(str, None))
	def merge_section(self, config, section_to, section_from=None):
		""" Load configuration section from other configuration. If specified section doesn't exist in current
		configuration, then it will be added automatically.

		:param config: source configuration
		:param section_to: destination section name
		:param section_from: source section name (if it is None, then section_to is used as source section name)
		:return: None
		"""
		section_from = section_from if section_from is not None else section_to
		if section_from not in config.sections():
			raise ValueError('There is no such section "%s" in config' % section_from)

		if section_to not in self.sections():
			self.add_section(section_to)

		for option in config[section_from].keys():
			self.set(section_to, option, config[section_from][option])

	def select_options(self, section, options_prefix=None):
		""" Select options from section

		:param section: target section
		:param options_prefix: prefix of options that should be selected

		:return: WConfigSelection
		"""
		return WConfigSelection(self, section, options_prefix=options_prefix)


class WConfigSelection:
	""" Represent subset of options in a single configuration section. Has methods __str__, __int__, __float__,
	__bool__ that return option value with option name equals to options prefix.
	"""

	@verify_type(config=WConfig, section=str, options_prefix=(str, None))
	@verify_value(section=lambda x: len(x) > 0)
	def __init__(self, config, section, options_prefix=None):
		""" Create a configuration selection

		:param config: source configuration
		:param section: source section name
		:param options_prefix: name prefix of options that should be selected. If it is not specified, then \
		it is treated as empty string
		"""
		self.__config = config
		self.__section = section
		self.__options_prefix = options_prefix if options_prefix is not None else ''

		if self.__config.has_section(section) is False:
			raise NoSectionError('Invalid section "%s" was specified' % section)

	def config(self):
		""" Return source configuration

		:return: WConfig
		"""
		return self.__config

	def section(self):
		""" Return source section name

		:return: str
		"""
		return self.__section

	def option_prefix(self):
		""" Return name prefix of options that may be selected

		:return: str
		"""
		return self.__options_prefix

	def __option(self):
		""" Check and return option from section from configuration. Option name is equal to option prefix

		:return: tuple of section name and option prefix
		"""
		section = self.section()
		option = self.option_prefix()
		if self.config().has_option(section, option) is False:
			raise NoOptionError(option, section)
		return section, option

	def __str__(self):
		""" Return string value of this option

		:return: str
		"""
		section, option = self.__option()
		return self.config()[section][option]

	def __int__(self):
		""" Return integer value of this option

		:return: int
		"""
		section, option = self.__option()
		return self.config().getint(section, option)

	def __float__(self):
		""" Return float value of this option

		:return: float
		"""
		section, option = self.__option()
		return self.config().getfloat(section, option)

	def __bool__(self):
		""" Return boolean value of this option

		:return: bool
		"""
		section, option = self.__option()
		return self.config().getboolean(section, option)

	@verify_type(option_prefix=str)
	@verify_value(option_prefix=lambda x: len(x) > 0)
	def select_options(self, options_prefix):
		""" Select options from this selection, that are started with the specified prefix

		:param options_prefix: name prefix of options that should be selected
		:return: WConfigSelection
		"""
		return WConfigSelection(
			self.config(), self.section(), self.option_prefix() + options_prefix
		)

	@verify_type('paranoid', item=str)
	@verify_value('paranoid', item=lambda x: len(x) > 0)
	def __getitem__(self, item):
		""" Alias for :meth:`.WConfigSelection.select_options` method

		:param item:
		:return:
		"""
		return self.select_options(item)

	@verify_type(option_name=(str, None))
	def has_option(self, option_name=None):
		""" Check whether configuration selection has the specified option.

		:param option_name: option name to check. If no option is specified, then check is made for this option

		:return: bool
		"""
		if option_name is None:
			option_name = ''
		return self.config().has_option(self.section(), self.option_prefix() + option_name)
