# -*- coding: utf-8 -*-

import pytest

from wasp_general.args.check import WArgumentRestrictionError, WArgumentsRestrictionProto, WArgumentsChecker
from wasp_general.args.check import WArgumentRequirements, WConflictedArguments, WSupportedArguments, WNotNullArguments
from wasp_general.args.check import WArgumentRERestriction


def test_exceptions():
	assert(issubclass(WArgumentRestrictionError, Exception) is True)


def test_abstract():
	pytest.raises(TypeError, WArgumentsRestrictionProto)
	pytest.raises(NotImplementedError, WArgumentsRestrictionProto.check, None, {})


class TestWArgumentsChecker:

	def test(self):
		checker = WArgumentsChecker()
		assert(isinstance(checker, WArgumentsRestrictionProto) is True)
		checker.check({})
		checker.check({'a': 'foo'})
		checker.check({'a': 'bar'})

		class E(WArgumentRestrictionError):
			pass

		class C(WArgumentsRestrictionProto):

			def check(self, arguments):
				if 'a' in arguments and arguments['a'] == 'foo':
					raise E('!')

		checker = WArgumentsChecker(C())
		checker.check({})
		pytest.raises(E, checker.check, {'a': 'foo'})
		checker.check({'a': 'bar'})


class TestWConflictedArguments:

	def test(self):
		assert(isinstance(WConflictedArguments(), WArgumentsRestrictionProto) is True)
		WConflictedArguments().check({})
		WConflictedArguments().check({'a': 'foo'})
		WConflictedArguments().check({'a': 'foo', 'b': 'bar'})
		WConflictedArguments().check({'a': 'foo', 'c': 'zzz'})

		WConflictedArguments('a').check({})
		WConflictedArguments('a').check({'a': 'foo'})
		WConflictedArguments('a').check({'a': 'foo', 'b': 'bar'})
		WConflictedArguments('a').check({'a': 'foo', 'c': 'zzz'})

		r = WConflictedArguments('a', 'b')
		r.check({})
		r.check({'a': 'foo'})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})


class TestWSupportedArguments:

	def test(self):
		assert(isinstance(WSupportedArguments(), WArgumentsRestrictionProto) is True)

		WSupportedArguments().check({})
		pytest.raises(WArgumentRestrictionError, WSupportedArguments().check, {'a': 'foo'})
		pytest.raises(WArgumentRestrictionError, WSupportedArguments().check, {'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionError, WSupportedArguments().check, {'a': 'foo', 'c': 'zzz'})

		WSupportedArguments('a').check({})
		WSupportedArguments('a').check({'a': 'foo'})
		pytest.raises(WArgumentRestrictionError, WSupportedArguments('a').check, {'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionError, WSupportedArguments('a').check, {'a': 'foo', 'c': 'zzz'})

		WSupportedArguments('a', 'b').check({})
		WSupportedArguments('a', 'b').check({'a': 'foo'})
		WSupportedArguments('a', 'b').check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionError, WSupportedArguments('a', 'b').check, {'a': 'foo', 'c': 'zzz'})


class TestWNotNullArguments:

	def test(self):
		assert(isinstance(WNotNullArguments(), WArgumentsRestrictionProto) is True)
		WNotNullArguments().check({})
		WNotNullArguments().check({'a': None})
		WNotNullArguments().check({'a': None, 'b': 'bar'})
		WNotNullArguments().check({'a': 'foo', 'c': None})

		r = WNotNullArguments('a')
		r.check({})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': None})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': None, 'b': 'bar'})
		r.check({'a': 'foo', 'c': None})


class TestWArgumentRequirements:

	def test_all_dependencies(self):
		assert(isinstance(WArgumentRequirements('a'), WArgumentsRestrictionProto) is True)

		r = WArgumentRequirements('a')
		pytest.raises(WArgumentRestrictionError, r.check, {})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

		r = WArgumentRequirements('a', 'b')
		pytest.raises(WArgumentRestrictionError, r.check, {})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

		r = WArgumentRequirements('a', 'b', main_argument='c')
		r.check({})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

	def test_n_of_dependencies(self):
		r = WArgumentRequirements(occurrences=1)
		r.check({})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		r.check({'b': 'foo'})

		r = WArgumentRequirements('a', occurrences=1)
		pytest.raises(WArgumentRestrictionError, r.check, {})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		pytest.raises(WArgumentRestrictionError, r.check, {'b': 'foo'})

		r = WArgumentRequirements('a', 'b', occurrences=1)
		pytest.raises(WArgumentRestrictionError, r.check, {})
		r.check({'a': 'foo'})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		r.check({'b': 'foo'})

		r = WArgumentRequirements('a', 'b', occurrences=1, exact_occurrences=False)
		pytest.raises(WArgumentRestrictionError, r.check, {})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		r.check({'b': 'foo'})

		r = WArgumentRequirements('a', 'b', 'd', occurrences=2)
		pytest.raises(WArgumentRestrictionError, r.check, {})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		pytest.raises(WArgumentRestrictionError, r.check, {'b': 'foo'})

		r = WArgumentRequirements('a', 'b', 'd', main_argument='c', occurrences=2)
		r.check({})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		r.check({'b': 'foo'})


class TestWArgumentRERestriction:

	def test(self):
		r = WArgumentRERestriction('a', '^\\d+$')
		r.check({})
		r.check({'a': '11'})
		pytest.raises(Exception, r.check, {'a': 1})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': 'foo'})
		pytest.raises(WArgumentRestrictionError, r.check, {'a': None})

		r = WArgumentRERestriction('a', '^\\d+$', required=True)
		pytest.raises(WArgumentRestrictionError, r.check, {})
		r.check({'a': '11'})

		r = WArgumentRERestriction('a', '^\\d+$', nullable=True)
		r.check({})
		r.check({'a': '11'})
		r.check({'a': None})
