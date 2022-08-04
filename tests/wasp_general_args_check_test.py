# -*- coding: utf-8 -*-

import pytest

from wasp_general.args.check import WArgumentRestrictionException, WArgumentsRestrictionProto, WArgumentsChecker
from wasp_general.args.check import WRequiredArguments, WConflictedArguments, WSupportedArguments, WNotNullArguments
from wasp_general.args.check import WOneOfArgument, WArgumentDependency, WArgumentOneOfDependency
from wasp_general.args.check import WArgumentRERestriction


def test_exceptions():
	assert(issubclass(WArgumentRestrictionException, Exception) is True)


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

		class E(WArgumentRestrictionException):
			pass

		class C(WArgumentsRestrictionProto):

			def check(self, arguments):
				if 'a' in arguments and arguments['a'] == 'foo':
					raise E('!')

		checker = WArgumentsChecker(C())
		checker.check({})
		pytest.raises(E, checker.check, {'a': 'foo'})
		checker.check({'a': 'bar'})


class TestWRequiredArguments:

	def test(self):
		assert(isinstance(WRequiredArguments(), WArgumentsRestrictionProto) is True)
		WRequiredArguments().check({})
		WRequiredArguments().check({'a': 'foo'})
		WRequiredArguments().check({'a': 'foo', 'b': 'bar'})

		pytest.raises(WArgumentRestrictionException, WRequiredArguments('a').check, {})
		WRequiredArguments('a').check({'a': 'foo'})
		WRequiredArguments('a').check({'a': 'foo', 'b': 'bar'})

		pytest.raises(WArgumentRestrictionException, WRequiredArguments('a', 'b').check, {})
		pytest.raises(WArgumentRestrictionException, WRequiredArguments('a', 'b').check, {'a': 'foo'})
		WRequiredArguments('a').check({'a': 'foo', 'b': 'bar'})


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
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})


class TestWSupportedArguments:

	def test(self):
		assert(isinstance(WSupportedArguments(), WArgumentsRestrictionProto) is True)

		WSupportedArguments().check({})
		pytest.raises(WArgumentRestrictionException, WSupportedArguments().check, {'a': 'foo'})
		pytest.raises(WArgumentRestrictionException, WSupportedArguments().check, {'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionException, WSupportedArguments().check, {'a': 'foo', 'c': 'zzz'})

		WSupportedArguments('a').check({})
		WSupportedArguments('a').check({'a': 'foo'})
		pytest.raises(WArgumentRestrictionException, WSupportedArguments('a').check, {'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionException, WSupportedArguments('a').check, {'a': 'foo', 'c': 'zzz'})

		WSupportedArguments('a', 'b').check({})
		WSupportedArguments('a', 'b').check({'a': 'foo'})
		WSupportedArguments('a', 'b').check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionException, WSupportedArguments('a', 'b').check, {'a': 'foo', 'c': 'zzz'})


class TestWNotNullArguments:

	def test(self):
		assert(isinstance(WNotNullArguments(), WArgumentsRestrictionProto) is True)
		WNotNullArguments().check({})
		WNotNullArguments().check({'a': None})
		WNotNullArguments().check({'a': None, 'b': 'bar'})
		WNotNullArguments().check({'a': 'foo', 'c': None})

		r = WNotNullArguments('a')
		r.check({})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': None})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': None, 'b': 'bar'})
		r.check({'a': 'foo', 'c': None})


class TestWOneOfArgument:

	def test(self):
		assert(isinstance(WOneOfArgument(), WArgumentsRestrictionProto) is True)

		r = WOneOfArgument()
		r.check({})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		r.check({'b': 'foo'})

		r = WOneOfArgument('a')
		pytest.raises(WArgumentRestrictionException, r.check, {})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		pytest.raises(WArgumentRestrictionException, r.check, {'b': 'foo'})

		r = WOneOfArgument('a', 'b')
		pytest.raises(WArgumentRestrictionException, r.check, {})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		r.check({'b': 'foo'})

		r = WOneOfArgument('a', 'b', exact_one=True)
		pytest.raises(WArgumentRestrictionException, r.check, {})
		r.check({'a': 'foo'})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo', 'b': 'bar', 'c': 'zzz'})
		r.check({'b': 'foo'})


class TestWArgumentDependency:

	def test(self):
		assert(isinstance(WArgumentDependency('a'), WArgumentsRestrictionProto) is True)

		r = WArgumentDependency('a')
		r.check({})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

		r = WArgumentDependency('a', 'b')
		r.check({})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})


class TestWArgumentOneOfDependency:

	def test(self):
		assert(isinstance(WArgumentOneOfDependency('a'), WArgumentsRestrictionProto) is True)

		r = WArgumentOneOfDependency('a')
		r.check({})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

		r = WArgumentOneOfDependency('a', exact_one=True)
		r.check({})
		r.check({'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

		r = WArgumentOneOfDependency('a', 'b')
		r.check({})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

		r = WArgumentOneOfDependency('a', 'b', exact_one=True)
		r.check({})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

		r = WArgumentOneOfDependency('a', 'b', 'c')
		r.check({})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		r.check({'a': 'foo', 'b': 'bar', 'c': 'zzz'})

		r = WArgumentOneOfDependency('a', 'b', 'c', exact_one=True)
		r.check({})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo'})
		r.check({'a': 'foo', 'b': 'bar'})
		r.check({'a': 'foo', 'c': 'zzz'})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo', 'b': 'bar', 'c': 'zzz'})


class TestWArgumentRERestriction:

	def test(self):
		r = WArgumentRERestriction('a', '^\\d+$')
		r.check({})
		r.check({'a': '11'})
		pytest.raises(Exception, r.check, {'a': 1})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': 'foo'})
		pytest.raises(WArgumentRestrictionException, r.check, {'a': None})

		r = WArgumentRERestriction('a', '^\\d+$', required=True)
		pytest.raises(WArgumentRestrictionException, r.check, {})
		r.check({'a': '11'})

		r = WArgumentRERestriction('a', '^\\d+$', nullable=True)
		r.check({})
		r.check({'a': '11'})
		r.check({'a': None})
