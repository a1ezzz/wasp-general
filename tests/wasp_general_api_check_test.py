# -*- coding: utf-8 -*-

import pytest

from wasp_general.api.check import WArgsRestrictionError, WArgsRestrictionProto, WChainChecker, WConflictedArgs
from wasp_general.api.check import WSupportedArgs, WArgsRequirements, WArgsValueRestriction
from wasp_general.api.check import WNotNullValues, WArgsValueRegExp


def test_exceptions():
	assert(issubclass(WArgsRestrictionError, Exception) is True)


def test_abstract():
	pytest.raises(TypeError, WArgsRestrictionProto)
	pytest.raises(NotImplementedError, WArgsRestrictionProto.check, None)

	pytest.raises(TypeError, WArgsValueRestriction)
	pytest.raises(NotImplementedError, WArgsValueRestriction.check_value, None, 1)


class TestWChainChecker:

	def test(self):
		checker = WChainChecker()
		assert(isinstance(checker, WArgsRestrictionProto) is True)
		checker.check()
		checker.check(a='foo')
		checker.check(a='bar')

		class E(WArgsRestrictionError):
			pass

		class C(WArgsRestrictionProto):

			def check(self, *args, **kwargs):
				if 'a' in kwargs and kwargs['a'] == 'foo':
					raise E('!')

		checker = WChainChecker(C())
		checker.check()
		pytest.raises(E, checker.check, a='foo')
		checker.check(a='bar')


class TestWConflictedArguments:

	def test(self):
		assert(isinstance(WConflictedArgs(), WArgsRestrictionProto) is True)
		assert(WConflictedArgs().conflicted_arguments() == set())
		WConflictedArgs().check()
		WConflictedArgs().check(a='foo')
		WConflictedArgs().check(a='foo', b='bar')
		WConflictedArgs().check(a='foo', c='zzz')

		WConflictedArgs('a').check()
		assert(WConflictedArgs('a').conflicted_arguments() == {'a', })
		WConflictedArgs('a').check(a='foo')
		WConflictedArgs('a').check(a='foo', b='bar')
		WConflictedArgs('a').check(a='foo', c='zzz')

		r = WConflictedArgs('a', 'b')
		assert(WConflictedArgs('a', 'b').conflicted_arguments() == {'a', 'b'})
		r.check()
		r.check(a='foo')
		pytest.raises(WArgsRestrictionError, r.check, a='foo', b='bar')
		r.check(a='foo', c='zzz')


class TestWSupportedArgs:

	def test(self):
		assert(isinstance(WSupportedArgs(), WArgsRestrictionProto) is True)

		WSupportedArgs().check()
		assert(WSupportedArgs().supported_arguments() == set())
		pytest.raises(WArgsRestrictionError, WSupportedArgs().check, a='foo')
		pytest.raises(WArgsRestrictionError, WSupportedArgs().check, a='foo', b='bar')
		pytest.raises(WArgsRestrictionError, WSupportedArgs().check, a='foo', c='zzz')

		assert(WSupportedArgs('a').supported_arguments() == {'a', })
		WSupportedArgs('a').check()
		WSupportedArgs('a').check(a='foo')
		pytest.raises(WArgsRestrictionError, WSupportedArgs('a').check, a='foo', b='bar')
		pytest.raises(WArgsRestrictionError, WSupportedArgs('a').check, a='foo', c='zzz')

		assert(WSupportedArgs('a', 'b').supported_arguments() == {'a', 'b'})
		WSupportedArgs('a', 'b').check()
		WSupportedArgs('a', 'b').check(a='foo')
		WSupportedArgs('a', 'b').check(a='foo', b='bar')

		pytest.raises(WArgsRestrictionError, WSupportedArgs('a', 'b').check, a='foo', c='zzz')


class TestWArgsRequirements:

	def test_all_dependencies(self):
		assert(isinstance(WArgsRequirements('a'), WArgsRestrictionProto) is True)
		r = WArgsRequirements()
		assert(r.conditional_argument() is None)
		assert(r.requirements() == set())
		assert(r.occurrences() is None)
		assert(r.exact_occurrences() is None)
		r.check()
		r.check(a='foo')
		r.check(a='foo', b='bar')
		r.check(a='foo', c='zzz')
		r.check(a='foo', b='bar', c='zzz')

		r = WArgsRequirements('a')
		assert(r.conditional_argument() is None)
		assert(r.requirements() == {'a', })
		assert(r.occurrences() is None)
		assert(r.exact_occurrences() is None)
		pytest.raises(WArgsRestrictionError, r.check)
		r.check(a='foo')
		r.check(a='foo', b='bar')
		r.check(a='foo', c='zzz')
		r.check(a='foo', b='bar', c='zzz')

		r = WArgsRequirements('a', 'b')
		assert(r.conditional_argument() is None)
		assert(r.requirements() == {'a', 'b'})
		assert(r.occurrences() is None)
		assert(r.exact_occurrences() is None)
		pytest.raises(WArgsRestrictionError, r.check)
		pytest.raises(WArgsRestrictionError, r.check, a='foo')
		r.check(a='foo', b='bar')
		pytest.raises(WArgsRestrictionError, r.check, a='foo', c='zzz')
		r.check(a='foo', b='bar', c='zzz')

		r = WArgsRequirements('a', 'b', conditional_argument='c')
		assert(r.conditional_argument() == 'c')
		assert(r.requirements() == {'a', 'b'})
		assert(r.occurrences() is None)
		assert(r.exact_occurrences() is None)
		r.check()
		r.check(a='foo')
		r.check(a='foo', b='bar')
		pytest.raises(WArgsRestrictionError, r.check, a='foo', c='zzz')
		r.check(a='foo', b='bar', c='zzz')

		pytest.raises(ValueError, WArgsRequirements, 'a', conditional_argument='a')

	def test_n_of_dependencies(self):
		pytest.raises(ValueError, WArgsRequirements, occurrences=1)
		pytest.raises(ValueError, WArgsRequirements, 'a', occurrences=2)

		r = WArgsRequirements('a', occurrences=1)
		assert(r.conditional_argument() is None)
		assert(r.requirements() == {'a', })
		assert(r.occurrences() == 1)
		assert(r.exact_occurrences() is True)
		pytest.raises(WArgsRestrictionError, r.check)
		r.check(a='foo')
		r.check(a='foo', b='bar')
		r.check(a='foo', c='zzz')
		r.check(a='foo', b='bar', c='zzz')
		pytest.raises(WArgsRestrictionError, r.check, b='foo')

		r = WArgsRequirements('a', 'b', occurrences=1)
		assert(r.conditional_argument() is None)
		assert(r.requirements() == {'a', 'b'})
		assert(r.occurrences() == 1)
		assert(r.exact_occurrences() is True)
		pytest.raises(WArgsRestrictionError, r.check)
		r.check(a='foo')
		pytest.raises(WArgsRestrictionError, r.check, a='foo', b='bar')
		r.check(a='foo', c='zzz')
		pytest.raises(WArgsRestrictionError, r.check, a='foo', b='bar', c='zzz')
		r.check(b='foo')

		r = WArgsRequirements('a', 'b', occurrences=1, exact_occurrences=False)
		assert(r.conditional_argument() is None)
		assert(r.requirements() == {'a', 'b'})
		assert(r.occurrences() == 1)
		assert(r.exact_occurrences() is False)
		pytest.raises(WArgsRestrictionError, r.check)
		r.check(a='foo')
		r.check(a='foo', b='bar')
		r.check(a='foo', c='zzz')
		r.check(a='foo', b='bar', c='zzz')
		r.check(b='foo')

		r = WArgsRequirements('a', 'b', 'd', occurrences=2)
		assert(r.conditional_argument() is None)
		assert(r.requirements() == {'a', 'b', 'd'})
		assert(r.occurrences() == 2)
		assert(r.exact_occurrences() is True)
		pytest.raises(WArgsRestrictionError, r.check)
		pytest.raises(WArgsRestrictionError, r.check, a='foo')
		r.check(a='foo', b='bar')
		pytest.raises(WArgsRestrictionError, r.check, a='foo', c='zzz')
		r.check(a='foo', b='bar', c='zzz')
		pytest.raises(WArgsRestrictionError, r.check, b='foo')

		r = WArgsRequirements('a', 'b', 'd', conditional_argument='c', occurrences=2)
		assert(r.conditional_argument() == 'c')
		assert(r.requirements() == {'a', 'b', 'd'})
		assert(r.occurrences() == 2)
		assert(r.exact_occurrences() is True)
		r.check()
		r.check(a='foo')
		r.check(a='foo', b='bar')
		pytest.raises(WArgsRestrictionError, r.check, a='foo', c='zzz')
		r.check(a='foo', b='bar', c='zzz')
		r.check(b='foo')


class TestWArgsValueRestriction:

	def test(self):

		class A(WArgsValueRestriction):
			__checked_values__ = []

			def check_value(self, value, name=None):
				return self.__checked_values__.append((value, name))

		assert(A.__checked_values__ == [])

		a = A()
		a.check(1, 2, 3, foo='bar', zzz='mmm')
		assert(A.__checked_values__ == [])

		a = A('foo', 'qqq')
		a.check(1, 2, 3, foo='bar', zzz='mmm')
		assert(A.__checked_values__ == [('bar', 'foo')])
		A.__checked_values__ = []

		a = A(args_selection=WArgsValueRestriction.ArgsSelection.positional_args)
		a.check(1, 2, 3, foo='bar', zzz='mmm')
		assert(A.__checked_values__ == [(1, None), (2, None), (3, None)])
		A.__checked_values__ = []

		a = A('foo', 'qqq', args_selection=WArgsValueRestriction.ArgsSelection.positional_args)
		a.check(1, 2, 3, foo='bar', zzz='mmm')
		assert(A.__checked_values__ == [(1, None), (2, None), (3, None), ('bar', 'foo')])
		A.__checked_values__ = []

		a = A(args_selection=WArgsValueRestriction.ArgsSelection.kw_args)
		a.check(1, 2, 3, foo='bar', zzz='mmm')
		assert(A.__checked_values__ == [('bar', 'foo'), ('mmm', 'zzz')])
		A.__checked_values__ = []

		a = A('foo', 'qqq', args_selection=WArgsValueRestriction.ArgsSelection.kw_args)
		a.check(1, 2, 3, foo='bar', zzz='mmm')
		assert(A.__checked_values__ == [('bar', 'foo'), ('mmm', 'zzz')])
		A.__checked_values__ = []

		a = A(args_selection=WArgsValueRestriction.ArgsSelection.all)
		a.check(1, 2, 3, foo='bar', zzz='mmm')
		assert(A.__checked_values__ == [(1, None), (2, None), (3, None), ('bar', 'foo'), ('mmm', 'zzz')])
		A.__checked_values__ = []

		a = A('foo', 'qqq', args_selection=WArgsValueRestriction.ArgsSelection.all)
		a.check(1, 2, 3, foo='bar', zzz='mmm')
		assert(A.__checked_values__ == [(1, None), (2, None), (3, None), ('bar', 'foo'), ('mmm', 'zzz')])
		A.__checked_values__ = []


class TestWNotNullValues:

	def test(self):
		assert(isinstance(WNotNullValues(), WArgsValueRestriction) is True)
		WNotNullValues().check()
		WNotNullValues().check(a=None)
		WNotNullValues().check(a=None, b='bar')
		WNotNullValues().check(a='foo', c=None)

		r = WNotNullValues('a')
		r.check()
		pytest.raises(WArgsRestrictionError, r.check, a=None)
		pytest.raises(WArgsRestrictionError, r.check, a=None, b='bar')
		r.check(a='foo', c=None)

		r = WNotNullValues(args_selection=WArgsValueRestriction.ArgsSelection.positional_args)
		r.check()
		pytest.raises(WArgsRestrictionError, r.check, None)
		pytest.raises(WArgsRestrictionError, r.check, None, a='bar')
		r.check(1, a='foo')


class TestWArgsValueRegExp:

	def test(self):
		r = WArgsValueRegExp('^\\d+$', 'a')
		assert(isinstance(r, WArgsValueRestriction))
		r.check()
		r.check(a='11')
		pytest.raises(Exception, r.check, a=1)
		pytest.raises(WArgsRestrictionError, r.check, a='foo')
		pytest.raises(WArgsRestrictionError, r.check, a=None)
		r.check(None)

		r = WArgsValueRegExp('^\\d+$', args_selection=WArgsValueRestriction.ArgsSelection.positional_args)
		assert(isinstance(r, WArgsValueRestriction))
		r.check()
		r.check('11')
		pytest.raises(Exception, r.check, 1)
		pytest.raises(WArgsRestrictionError, r.check, 'foo')
		pytest.raises(WArgsRestrictionError, r.check, None)

		r = WArgsValueRegExp('^\\d+$', 'a', nullable=True)
		r.check()
		r.check(a='11')
		r.check(a=None)

		r = WArgsValueRegExp(
			'^\\d+$', nullable=True, args_selection=WArgsValueRestriction.ArgsSelection.positional_args
		)
		r.check()
		r.check('11')
		r.check(None)
