# -*- coding: utf-8 -*-

import pytest
import os
from inspect import isfunction

from wasp_general.verify import Verificator, TypeVerificator, SubclassVerificator, ValueVerificator
from wasp_general.verify import verify_type, verify_subclass, verify_value


@pytest.fixture
def verificator_env(request):
	def fin():
		if Verificator.__default_environment_var__ in os.environ:
			del os.environ[Verificator.__default_environment_var__]
	request.addfinalizer(fin)


@pytest.mark.usefixtures('verificator_env')
class TestVerificator:

	def test_check_disabled(self):

		pytest.raises(KeyError, 'os.environ[Verificator.__default_environment_var__]')

		assert(Verificator().check_disabled() is False)
		assert(Verificator('test_tag1').check_disabled() is False)
		assert(Verificator('test_tag1', 'test_tag2').check_disabled() is False)

		os.environ[Verificator.__default_environment_var__] = 'foo:bar:test_tag1:value3'
		assert(Verificator().check_disabled() is False)
		assert(Verificator('test_tag1').check_disabled() is True)
		assert(Verificator('test_tag1', 'test_tag2').check_disabled() is False)

		os.environ[Verificator.__default_environment_var__] = 'foo:bar:test_tag1:value3:test_tag2'
		assert(Verificator().check_disabled() is False)
		assert(Verificator('test_tag1').check_disabled() is True)
		assert(Verificator('test_tag1', 'test_tag2').check_disabled() is True)

	def test_check(self):
		check = Verificator().check(None, '', lambda x: None)
		assert(isfunction(check) is True)

	def test_decorator(self):
		pytest.raises(KeyError, 'os.environ[Verificator.__default_environment_var__]')

		def foo(a, b, c, d=None, **kwargs):
			'''
			multi-line
			bla-bla docstring
			'''
			pass

		verificator = Verificator()

		assert(verificator.decorator()(foo) != foo)
		verificator.check_disabled = lambda: True
		assert(verificator.decorator()(foo) == foo)
		verificator = Verificator()

		def exc():
			raise TypeError('text exception')

		default_check = lambda x: None
		exc_check = lambda x: exc() if x == 3 else None
		a_spec = lambda x: 111
		verificator.check = lambda s, n, f: exc_check if n == 'a' or n == 'd' or n == 'e' else default_check
		decorated_foo = verificator.decorator(a=a_spec, c=1, d=1, e=1)(foo)

		decorated_foo(1, 2, 3, d=4)
		pytest.raises(TypeError, decorated_foo, 3, 2, 3, d=4)
		pytest.raises(TypeError, decorated_foo, 1, 2, 3, d=3)
		decorated_foo(1, 2, 3, d=4, e=5)
		pytest.raises(TypeError, decorated_foo, 1, 2, 3, d=4, e=3)


class TestTypeVerificator:

	def test_check(self):

		def foo(a, b, c, d=None, **kwargs):
			'''
			multi-line
			bla-bla docstring
			'''
			pass

		verificator = TypeVerificator()
		pytest.raises(RuntimeError, 'verificator.decorator(a=None)(foo)')
		pytest.raises(RuntimeError, 'verificator.decorator(a=(str, None, 1))(foo)')

		decorated_foo = verificator.decorator(a=int, b=(str, None), c=[str, int], d=(str, int, None), e=float)(foo)
		decorated_foo(1, None, 'f')
		decorated_foo(1, None, 1, d='o')
		decorated_foo(1, None, 'o', d=5, e=.1)

		pytest.raises(TypeError, "decorated_foo('b', None, 'f')")
		pytest.raises(TypeError, "decorated_foo(1, 4, 'o')")
		pytest.raises(TypeError, "decorated_foo(1, None, None)")
		pytest.raises(TypeError, "decorated_foo(1, None, 'o', d=.1)")
		pytest.raises(TypeError, "decorated_foo(1, None, 'b', e='a')")


class TestSubclassVerificator:

	def test_check(self):

		def foo(a, b, c, d=None, **kwargs):
			'''
			multi-line
			bla-bla docstring
			'''
			pass

		verificator = SubclassVerificator()
		pytest.raises(RuntimeError, 'verificator.decorator(a=None)(foo)')
		pytest.raises(RuntimeError, 'verificator.decorator(a=(str, None, 1))(foo)')

		class A:
			pass

		class B(A):
			pass

		class C(A):
			pass

		class D:
			pass

		decorated_foo = verificator.decorator(a=A, c=(B, C), d=[B, None], e=C)(foo)
		decorated_foo(A, None, B)
		decorated_foo(B, None, B)
		decorated_foo(A, None, B, d=B)
		decorated_foo(A, None, C, d=B)
		decorated_foo(A, None, B, d=None, e=C)

		pytest.raises(TypeError, "decorated_foo(D, None, B)")
		pytest.raises(TypeError, "decorated_foo(A, None, A)")
		pytest.raises(TypeError, "decorated_foo(A, None, None)")
		pytest.raises(TypeError, "decorated_foo(A, None, B, d=C)")
		pytest.raises(TypeError, "decorated_foo(A, None, B, d=B, e=A)")


class TestValueVerificator:

	def test_check(self):

		def foo(a, b, c, d=None, **kwargs):
			'''
			multi-line
			bla-bla docstring
			'''
			pass

		verificator = ValueVerificator()
		pytest.raises(RuntimeError, 'verificator.decorator(a=1)(foo)')
		pytest.raises(RuntimeError, 'verificator.decorator(a=(1,))(foo)')

		decorated_foo = verificator.decorator(
			a=(lambda x: x > 5, lambda x: x < 10),
			c=lambda x: x[:3] == 'foo', d=lambda x: x is not None, e=lambda x: x == 1
		)(foo)
		decorated_foo(6, 1, 'foo-asdaads', d=7)
		decorated_foo(6, 1, 'foo-asdaads', d='sss')
		decorated_foo(6, 1, 'foo-asdaads', d=0.1, e=1)

		pytest.raises(ValueError, decorated_foo, 6, None, 'foo-aaa')
		pytest.raises(ValueError, decorated_foo, 5, None, 'foo-aaa', d=5)
		pytest.raises(ValueError, decorated_foo, 10, None, 'foo-aaa', d=5)
		pytest.raises(ValueError, decorated_foo, 6, None, 'foo-aaa', d=5, e=7)


def test_verify():

	class A:
		a = 'foo'

	@verify_type(a=int, b=str, d=(int, None), e=float)
	@verify_subclass(c=A)
	@verify_value(a=(lambda x: x > 5, lambda x: x < 10), c=lambda x: x.a == 'foo', d=lambda x: x is None or x < 0)
	def foo(a, b, c, d=None, **kwargs):
		'''
		multi-line
		bla-bla docstring
		'''
		pass

	foo(6, 'bar', A)
	foo(7, 'bar', A, d=-1)
	foo(6, 'bar', A, e=0.1)

	pytest.raises(TypeError, foo, 'foo', 'bar', A)
	pytest.raises(TypeError, foo, 6, 'bar', int)
	pytest.raises(ValueError, foo, 3, 'bar', A)
	A.a = 'bar'
	pytest.raises(ValueError, foo, 6, 'bar', A)
	A.a = 'foo'
	pytest.raises(ValueError, foo, 6, 'bar', A, d=1)