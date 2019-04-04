# -*- coding: utf-8 -*-

from enum import Enum
import re
import pytest

from wasp_general.args.cast import WArgumentCastingError, WArgumentCastingHelperProto, WArgumentCastingFnHelper
from wasp_general.args.cast import WStringArgumentCastingHelper, WIntegerArgumentCastingHelper
from wasp_general.args.cast import WFloatArgumentCastingHelper, WByteSizeArgumentHelper, WEnumArgumentHelper
from wasp_general.args.cast import WRegExpArgumentHelper


def test_exceptions():
	assert(issubclass(WArgumentCastingError, Exception) is True)


def test_abstract():
	pytest.raises(TypeError, WArgumentCastingHelperProto)
	pytest.raises(NotImplementedError, WArgumentCastingHelperProto.cast, None, '')


class TestWArgumentCastingFnHelper:

	def test(self):
		assert(isinstance(WArgumentCastingFnHelper(), WArgumentCastingHelperProto) is True)

		def int_cast_fn(x):
			return int(x)

		def validate_fn(x):
			return x > 10

		h = WArgumentCastingFnHelper(casting_fn=int_cast_fn, validate_fn=validate_fn)
		assert(h.casting_function() == int_cast_fn)
		assert(h.validate_function() == validate_fn)
		assert(h.cast('11') == 11)
		pytest.raises(WArgumentCastingError, h.cast, '9')

		h = WArgumentCastingFnHelper(casting_fn=int_cast_fn)
		assert(h.cast('11') == 11)
		assert(h.cast('9') == 9)

		h = WArgumentCastingFnHelper()
		assert(h.cast('11') == '11')
		assert(h.cast('9') == '9')

		h = WArgumentCastingFnHelper(validate_fn=lambda x: isinstance(x, str))
		assert(h.cast('11') == '11')
		assert(h.cast('9') == '9')

		h = WArgumentCastingFnHelper(validate_fn=lambda x: isinstance(x, str) and len(x) > 1)
		assert(h.cast('11') == '11')
		pytest.raises(WArgumentCastingError, h.cast, '9')


class TestWStringArgumentCastingHelper:

	def test(self):
		h = WStringArgumentCastingHelper()
		assert(isinstance(h, WArgumentCastingFnHelper) is True)
		assert(h.cast('11') == '11')
		assert(h.cast('9') == '9')

		h = WArgumentCastingFnHelper(validate_fn=lambda x: len(x) > 1)
		assert(h.cast('11') == '11')
		pytest.raises(WArgumentCastingError, h.cast, '9')


class TestWIntegerArgumentCastingHelper:

	def test(self):
		h = WIntegerArgumentCastingHelper()
		assert(isinstance(h, WArgumentCastingFnHelper) is True)
		assert(h.cast('11') == 11)
		assert(h.cast('9') == 9)
		pytest.raises(WArgumentCastingError, h.cast, 'abc')

		h = WIntegerArgumentCastingHelper(validate_fn=lambda x: x > 10)
		assert(h.cast('11') == 11)
		pytest.raises(WArgumentCastingError, h.cast, '9')

		assert(WIntegerArgumentCastingHelper(base=8).cast('11') == 9)
		assert(WIntegerArgumentCastingHelper(base=16).cast('11') == 17)


class TestWFloatArgumentCastingHelper:

	def test(self):
		h = WFloatArgumentCastingHelper()
		assert(isinstance(h, WArgumentCastingFnHelper) is True)
		assert(h.cast('1.1') == 1.1)
		assert(h.cast('0.9') == 0.9)

		h = WFloatArgumentCastingHelper(validate_fn=lambda x: x > 1)
		assert(h.cast('1.1') == 1.1)
		pytest.raises(WArgumentCastingError, h.cast, '0.9')

		pytest.raises(ValueError, h.cast, '0,9')
		h = WFloatArgumentCastingHelper(decimal_point_char=',')
		assert(h.cast('0,9') == 0.9)


class TestWByteSizeArgumentHelper:

	def test(self):
		h = WByteSizeArgumentHelper()
		assert(isinstance(h, WFloatArgumentCastingHelper) is True)
		pytest.raises(WArgumentCastingError, h.cast, '-1')
		assert(h.cast('10') == 10)
		assert(h.cast('10.1') == 10.1)
		assert(h.cast('10.1B') == 10.1)
		assert(h.cast('10.1K') == 10100)
		assert(h.cast('10.1KB') == 10100)
		assert(h.cast('10.1Ki') == 10342.4)
		assert(h.cast('10.1KiB') == 10342.4)
		assert(h.cast('10.1M') == 10100000)
		assert(h.cast('10.1MB') == 10100000)
		assert(h.cast('10.1Mi') == 10590617.6)
		assert(h.cast('10.1MiB') == 10590617.6)
		assert(h.cast('10.1G') == 10100000000)
		assert(h.cast('10.1GB') == 10100000000)
		assert(h.cast('10.1Gi') == 10844792422.4)
		assert(h.cast('10.1GiB') == 10844792422.4)
		assert(h.cast('10.1T') == 10100000000000)
		assert(h.cast('10.1TB') == 10100000000000)
		assert(h.cast('10.1Ti') == 11105067440537.6)
		assert(h.cast('10.1TiB') == 11105067440537.6)


class TestWEnumArgumentHelper:

	class A(Enum):
		a = 'foo'
		b = 'bar'

	class B(Enum):
		a = 'foo'
		b = 1

	def test(self):
		h = WEnumArgumentHelper(TestWEnumArgumentHelper.A)
		assert(isinstance(h, WArgumentCastingFnHelper) is True)
		assert(h.cast('foo') == TestWEnumArgumentHelper.A.a)
		assert(h.cast('bar') == TestWEnumArgumentHelper.A.b)
		pytest.raises(WArgumentCastingError, h.cast, 'zzz')

		pytest.raises(TypeError, WEnumArgumentHelper, TestWEnumArgumentHelper.B)


class TestWRegExpArgumentHelper:

	def test(self):
		h = WRegExpArgumentHelper('^(foo|bar)')
		assert(isinstance(h, WArgumentCastingFnHelper) is True)
		assert(h.cast('foo') == ('foo', ))
		assert(h.cast('bar-ddd111') == ('bar', ))

		h = WRegExpArgumentHelper('^(foo|bar)\\-(\\d+)')
		pytest.raises(WArgumentCastingError, h.cast, 'foo')
		assert(h.cast('foo-10') == ('foo', '10'))

		assert(isinstance(h.re(), type(re.compile('aaa'))) is True)
		assert(h.re().search('bar-20').groups() == ('bar', '20'))
		assert(h.re().match('zzz-30') is None)


class TestWCommandArgumentDescriptor:

	def test(self):
		pass


class TestWCommandArgumentParser:

	def test(self):
		pass
