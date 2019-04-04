# -*- coding: utf-8 -*-
# wasp_general/args/cast.py
#
# Copyright (C) 2017-2019 the wasp-general authors and contributors
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

import re
from abc import abstractmethod, ABCMeta
from enum import Enum
from locale import atof, localeconv

from wasp_general.verify import verify_type, verify_value, verify_subclass


class WArgumentCastingError(Exception):
	""" This exception is raised if some error is happened during value casting
	"""
	pass


class WArgumentCastingHelperProto(metaclass=ABCMeta):
	""" This is a prototype for helper that may cast string value into other type
	"""

	@abstractmethod
	@verify_type('strict', value=str)
	def cast(self, value):
		""" Cast the specified value

		:param value: value to cast
		:type value: str

		:rtype: any
		"""
		raise NotImplementedError('This method is abstract')


class WArgumentCastingFnHelper(WArgumentCastingHelperProto):
	""" This class will cast values with a specified function and may validate result
	"""

	@verify_value('strict', casting_fn=lambda x: x is None or callable(x))
	@verify_value('strict', validate_fn=lambda x: x is None or callable(x))
	def __init__(self, casting_fn=None, validate_fn=None):
		""" Create new casting object

		:param casting_fn: function that accepts single argument that will cast str object into required type.
		If it is not specified, then no casting is made and value is returned as is
		:type casting_fn: callable

		:param validate_fn: function that accepts single argument (casted value) that will raise exception
		if a casted value is invalid. If it is not specified then no validation is made
		:type validate_fn: callable
		"""
		WArgumentCastingHelperProto.__init__(self)
		self.__casting_fn = casting_fn
		self.__validate_fn = validate_fn

	def casting_function(self):
		""" Return function that is used for value casting

		:rtype: callable | None
		"""
		return self.__casting_fn

	def validate_function(self):
		""" Return function that is used for casted value validation

		:rtype: callable | None
		"""
		return self.__validate_fn

	@verify_type('strict', value=str)
	def cast(self, value):
		""" :meth:`.WArgumentCastingHelperProto.cast` method implementation
		:type value: str
		:rtype: any
		"""
		casting_fn = self.casting_function()
		if casting_fn is not None:
			value = casting_fn(value)
		validate_fn = self.validate_function()
		if validate_fn is not None:
			if validate_fn(value) is not True:
				raise WArgumentCastingError('Argument has invalid value')
		return value


class WStringArgumentCastingHelper(WArgumentCastingFnHelper):
	""" This class is may be used not for str value casting but for str validation mostly
	"""

	@verify_value('paranoid', validate_fn=lambda x: x is None or callable(x))
	def __init__(self, validate_fn=None):
		""" Create new casting object

		:param validate_fn: if specified then this function is used for value validation
		:type validate_fn: callable | None
		"""
		WArgumentCastingFnHelper.__init__(self, validate_fn=validate_fn)


class WIntegerArgumentCastingHelper(WArgumentCastingFnHelper):
	""" This class may be used for casting a value from str type to int type
	"""

	@verify_type('strict', base=int)
	@verify_value('paranoid', validate_fn=lambda x: x is None or callable(x))
	@verify_value('strict', base=lambda x: x > 0)
	def __init__(self, base=10, validate_fn=None):
		""" Create new casting object

		:param base: integer base (like 8 or 10 or 16)
		:type base: int

		:param validate_fn: if specified then this function is used for value validation
		:type validate_fn: callable | None
		"""
		self.__base = base
		WArgumentCastingFnHelper.__init__(self, casting_fn=self._cast_string, validate_fn=validate_fn)

	@verify_type('strict', value=str)
	def _cast_string(self, value):
		try:
			return int(value, base=self.__base)
		except ValueError:
			raise WArgumentCastingError(
				'Unable to cast value "%s" to integer (with base %i)' % (value, self.__base)
			)


class WFloatArgumentCastingHelper(WArgumentCastingFnHelper):
	""" This class may be used for casting a value from str type to float type
	"""

	@verify_type('strict', decimal_point_char=(str, None))
	@verify_value('strict', decimal_point_char=lambda x: x is None or len(x) == 1)
	@verify_value('paranoid', validate_fn=lambda x: x is None or callable(x))
	def __init__(self, validate_fn=None, decimal_point_char=None):
		""" Create new casting object

		:param validate_fn: if specified then this function is used for value validation
		:type validate_fn: callable | None

		:param decimal_point_char: if specified then this char will be used for decimal point (default
		value is a char from locale)
		:type decimal_point_char: str | None
		"""
		self.__decimal_point_char = decimal_point_char
		WArgumentCastingFnHelper.__init__(
			self, casting_fn=self._cast_string, validate_fn=validate_fn
		)

	@verify_type('strict', value=str)
	def _cast_string(self, value):
		""" Cast str to float

		:param value: value to cast
		:type value: str

		:rtype: float
		"""
		if self.__decimal_point_char is not None:
			locale_decimal_point = localeconv()['decimal_point']
			value = value.replace(self.__decimal_point_char, locale_decimal_point, 1)
		return atof(value)


class WByteSizeArgumentHelper(WFloatArgumentCastingHelper):
	""" This class may be used for casting data size as a string (like '10.1KiB') to a number of bytes (float).
	Since string may be used to define data rate this value may be a fraction.
	"""

	__data_size_re__ = re.compile('^(\\d+((\\.|,|)[\\d]*)?)((K|M|G|T|Ki|Mi|Gi|Ti|)B?)?$')
	""" Regular expression that is used for data size parsing
	"""

	@verify_type('strict', value=str)
	def _cast_string(self, value):
		""" Cast str (as a data size) to float

		:param value: value to cast
		:type value: str

		:rtype: float
		"""
		data_size_re = WByteSizeArgumentHelper.__data_size_re__.search(value)
		if data_size_re is None:
			raise WArgumentCastingError('Invalid data size')

		result = WFloatArgumentCastingHelper._cast_string(self, data_size_re.group(1))
		suffix = data_size_re.group(5)
		if suffix is not None:
			if suffix == 'K':
				result *= (10 ** 3)
			elif suffix == 'M':
				result *= (10 ** 6)
			elif suffix == 'G':
				result *= (10 ** 9)
			elif suffix == 'T':
				result *= (10 ** 12)
			elif suffix == 'Ki':
				result *= (1 << 10)
			elif suffix == 'Mi':
				result *= (1 << 20)
			elif suffix == 'Gi':
				result *= (1 << 30)
			elif suffix == 'Ti':
				result *= (1 << 40)
		return result


class WEnumArgumentHelper(WArgumentCastingFnHelper):
	""" This class may cast a value from str type to Enum type (which values are str type)
	"""

	@verify_subclass('strict', enum_cls=Enum)
	def __init__(self, enum_cls):
		""" Create new casting object

		:param enum_cls: enum to which str value will be casted
		:type enum_cls: Enum
		"""
		WArgumentCastingFnHelper.__init__(self, casting_fn=self._cast_string)
		for item in enum_cls:
			if isinstance(item.value, str) is False:
				raise TypeError('Enum fields must be str type')
		self.__enum_cls = enum_cls
		self.__values = {x.value for x in self.__enum_cls.__members__.values()}

	@verify_type('strict', value=str)
	def _cast_string(self, value):
		""" Cast str to Enum

		:param value: value to cast
		:type value: str

		:rtype: Enum
		"""
		if value not in self.__values:
			raise WArgumentCastingError('Unknown value spotted')
		return self.__enum_cls(value)


class WRegExpArgumentHelper(WArgumentCastingFnHelper):
	""" This class may cast a value from str type to tuple of str which is made by parsing with regular expression
	"""

	@verify_type('strict', regexp=str)
	def __init__(self, regexp):
		""" Create new casting object

		:param regexp: regular expression to be used for parsing
		:type regexp: str
		"""
		WArgumentCastingFnHelper.__init__(self, casting_fn=self._cast_string)
		self.__regexp = re.compile(regexp)

	def re(self):
		""" Return compiled regular expression object

		:rtype: re object
		"""
		return self.__regexp

	@verify_type('strict', value=str)
	def _cast_string(self, value):
		""" Parse string with regular expression

		:param value: value to parse
		:type value: str

		:rtype: tuple[str]
		"""
		result = self.re().search(value)
		if result is None:
			raise WArgumentCastingError('Value does not match regexp')
		return result.groups()
