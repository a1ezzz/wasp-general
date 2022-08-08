# -*- coding: utf-8 -*-

import pytest
import os
from inspect import isfunction

from wasp_general.verify import Verifier, TypeVerifier, SubclassVerifier, ValueVerifier
from wasp_general.verify import verify_type, verify_subclass, verify_value


@pytest.fixture
def verifier_env(request):
    env_value = os.environ[Verifier.__environment_var__] if Verifier.__environment_var__ in os.environ else None
    if Verifier.__environment_var__ in os.environ:
        del os.environ[Verifier.__environment_var__]

    def fin():
        if env_value is None and Verifier.__environment_var__ in os.environ:
            del os.environ[Verifier.__environment_var__]
        elif env_value is not None:
            os.environ[Verifier.__environment_var__] = env_value

    request.addfinalizer(fin)


def fn_name_checker():
    pass


class FNameChecker:
    @staticmethod
    def foo():
        pass

    @classmethod
    def bar(cls):
        pass

    def zzz(self):
        pass


@pytest.mark.usefixtures('verifier_env')
class TestVerifier:

    def test_decorate_disabled(self):
        with pytest.raises(KeyError):
            a = os.environ[Verifier.__environment_var__]  # noqa: F841

        assert(Verifier().decorate_disabled() is False)
        assert(Verifier('test_tag1').decorate_disabled() is True)
        assert(Verifier('test_tag1', 'test_tag2').decorate_disabled() is True)

        os.environ[Verifier.__environment_var__] = 'foo:bar:test_tag1:value3'
        assert(Verifier().decorate_disabled() is False)
        assert(Verifier('test_tag1').decorate_disabled() is False)
        assert(Verifier('test_tag1', 'test_tag2').decorate_disabled() is False)

        os.environ[Verifier.__environment_var__] = 'foo:bar:test_tag1:value3:test_tag2'
        assert(Verifier().decorate_disabled() is False)
        assert(Verifier('test_tag1').decorate_disabled() is False)
        assert(Verifier('test_tag1', 'test_tag2').decorate_disabled() is False)

        os.environ[Verifier.__environment_var__] = 'foo:bar:value3'
        assert(Verifier().decorate_disabled() is False)
        assert(Verifier('test_tag1').decorate_disabled() is True)
        assert(Verifier('test_tag1', 'test_tag2').decorate_disabled() is True)

        os.environ[Verifier.__environment_var__] = 'foo:bar:*:value3'
        assert(Verifier().decorate_disabled() is False)
        assert(Verifier('test_tag1').decorate_disabled() is False)
        assert(Verifier('test_tag1', 'test_tag2').decorate_disabled() is False)

    def test_check(self):
        check = Verifier().check(None, '', lambda x: None)
        assert(isfunction(check) is True)

    def test_decorator(self):
        with pytest.raises(KeyError):
            a = os.environ[Verifier.__environment_var__]  # noqa: F841

        def foo(a, b, c, d=None, **kwargs):
            '''
            multi-line
            bla-bla docstring
            '''
            pass

        verifier = Verifier()

        assert(verifier.decorator()(foo) != foo)
        verifier.decorate_disabled = lambda: True
        assert(verifier.decorator()(foo) == foo)
        verifier = Verifier()

        def exc():
            raise TypeError('text exception')

        default_check = lambda x: None
        exc_check = lambda x: exc() if x == 3 else None
        a_spec = lambda x: 111
        verifier.check = lambda s, n, f: exc_check if n == 'a' or n == 'd' or n == 'e' else default_check
        decorated_foo = verifier.decorator(a=a_spec, c=1, d=1, e=1)(foo)

        decorated_foo(1, 2, 3, d=4)
        pytest.raises(TypeError, decorated_foo, 3, 2, 3, d=4)
        pytest.raises(TypeError, decorated_foo, 1, 2, 3, d=3)
        decorated_foo(1, 2, 3, d=4, e=5)
        pytest.raises(TypeError, decorated_foo, 1, 2, 3, d=4, e=3)

    def test_function_name(self):

        assert(Verifier.function_name(FNameChecker.foo) == 'FNameChecker.foo')
        assert(Verifier.function_name(FNameChecker.bar) == 'FNameChecker.bar')
        assert(Verifier.function_name(FNameChecker.zzz) == 'FNameChecker.zzz')

        c = FNameChecker()
        assert(Verifier.function_name(c.foo) == 'FNameChecker.foo')
        assert(Verifier.function_name(c.bar) == 'FNameChecker.bar')
        assert(Verifier.function_name(c.zzz) == 'FNameChecker.zzz')


class TestTypeVerifier:

    def test_check(self):

        def foo(a, b, c, d=None, **kwargs):
            '''
            multi-line
            bla-bla docstring
            '''
            pass

        verifier = TypeVerifier()

        with pytest.raises(RuntimeError):
            verifier.decorator(a=None)(foo)

        with pytest.raises(RuntimeError):
            verifier.decorator(a=(str, None, 1))(foo)

        decorated_foo = verifier.decorator(a=int, b=(str, None), c=[str, int], d=(str, int, None), e=float)(foo)
        decorated_foo(1, None, 'f')
        decorated_foo(1, None, 1, d='o')
        decorated_foo(1, None, 'o', d=5, e=.1)

        with pytest.raises(TypeError):
            decorated_foo('b', None, 'f')

        with pytest.raises(TypeError):
            decorated_foo(1, 4, 'o')

        with pytest.raises(TypeError):
            decorated_foo(1, None, None)

        with pytest.raises(TypeError):
            decorated_foo(1, None, 'o', d=.1)

        with pytest.raises(TypeError):
            decorated_foo(1, None, 'b', e='a')

        def foo(*args):
            pass

        decorated_foo = verifier.decorator(args=int)(foo)
        decorated_foo()
        decorated_foo(1, 2, 3)
        pytest.raises(TypeError, decorated_foo, 0.1)
        pytest.raises(TypeError, decorated_foo, 1, 0.1, 4)

        def foo(x, *args):
            pass

        decorated_foo = verifier.decorator(args=(int, float))(foo)
        decorated_foo('')
        decorated_foo('', 0.1, 2, 3)
        pytest.raises(TypeError, decorated_foo, '', '')


class TestSubclassVerifier:

    def test_check(self):

        def foo(a, b, c, d=None, **kwargs):
            '''
            multi-line
            bla-bla docstring
            '''
            pass

        verifier = SubclassVerifier()

        with pytest.raises(RuntimeError):
            verifier.decorator(a=None)(foo)

        with pytest.raises(RuntimeError):
            verifier.decorator(a=(str, None, 1))(foo)

        class A:
            pass

        class B(A):
            pass

        class C(A):
            pass

        class D:
            pass

        decorated_foo = verifier.decorator(a=A, c=(B, C), d=[B, None], e=C)(foo)
        decorated_foo(A, None, B)
        decorated_foo(B, None, B)
        decorated_foo(A, None, B, d=B)
        decorated_foo(A, None, C, d=B)
        decorated_foo(A, None, B, d=None, e=C)

        with pytest.raises(TypeError):
            decorated_foo(D, None, B)

        with pytest.raises(TypeError):
            decorated_foo(A, None, A)

        with pytest.raises(TypeError):
            decorated_foo(A, None, None)

        with pytest.raises(TypeError):
            decorated_foo(A, None, B, d=C)

        with pytest.raises(TypeError):
            decorated_foo(A, None, B, d=B, e=A)


class TestValueVerifier:

    def test_check(self):

        def foo(a, b, c, d=None, **kwargs):
            '''
            multi-line
            bla-bla docstring
            '''
            pass

        verifier = ValueVerifier()

        with pytest.raises(RuntimeError):
            verifier.decorator(a=1)(foo)

        with pytest.raises(RuntimeError):
            verifier.decorator(a=(1,))(foo)

        decorated_foo = verifier.decorator(
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
