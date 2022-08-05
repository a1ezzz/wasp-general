# -*- coding: utf-8 -*-

from decorator import decorator
import pytest

from wasp_general.api.capability import WCapabilityDescriptor, capability, WCapabilitiesHolderMeta, iscapable
from wasp_general.api.capability import WCapabilitiesHolder


class TestWCapabilityDescriptor:

	def test(self):
		class A:
			pass

		d = WCapabilityDescriptor(A, 'foo')
		assert(d.cls() is A)
		assert(d.name() == 'foo')


class TestWCapabilitiesHolderMeta:

	@staticmethod
	def dumb_decorator(f):
		def decorator_fn(f, *args, **kwargs):
			return f(*args, **kwargs)

		return decorator(decorator_fn)(f)

	def test(self):

		class A(metaclass=WCapabilitiesHolderMeta):

			@capability
			def foo(self):
				return 1

			def bar(self):
				return 2

		d = A.foo
		assert(isinstance(d, WCapabilityDescriptor) is True)
		assert(d.cls() is A)
		assert(d.name() == 'foo')

		with pytest.raises(TypeError):
			class B(metaclass=WCapabilitiesHolderMeta):
				@classmethod
				@capability
				def foo(cls):
					return 1

		class C(metaclass=WCapabilitiesHolderMeta):

			@TestWCapabilitiesHolderMeta.dumb_decorator
			@capability
			def foo(self):
				return 1

			@capability
			@TestWCapabilitiesHolderMeta.dumb_decorator
			def bar(self):
				return 2

			def zzz(self):
				return 3

		d = C.foo
		assert(isinstance(d, WCapabilityDescriptor) is True)
		assert(d.cls() is C)
		assert(d.name() == 'foo')

		d = C.bar
		assert(isinstance(d, WCapabilityDescriptor) is True)
		assert(d.cls() is C)
		assert(d.name() == 'bar')

		assert(isinstance(C.zzz, WCapabilityDescriptor) is False)

	def test_iscapable(self):
		class A(metaclass=WCapabilitiesHolderMeta):

			@TestWCapabilitiesHolderMeta.dumb_decorator
			@capability
			def foo(self):
				return 1

			@capability
			@TestWCapabilitiesHolderMeta.dumb_decorator
			def bar(self):
				return 2

			def zzz(self):
				return 3

		class B(A):

			def foo(self):
				return 4

		class C(A):

			def bar(self):
				return 5

		class D(A):

			def foo(self):
				return 6

			def bar(self):
				return 7

		a = A()
		b = B()
		c = C()
		d = D()

		assert(a.foo() == 1)
		assert(a.bar() == 2)
		assert(a.zzz() == 3)

		assert(b.foo() == 4)
		assert(b.bar() == 2)
		assert(b.zzz() == 3)

		assert(c.foo() == 1)
		assert(c.bar() == 5)
		assert(c.zzz() == 3)

		assert(d.foo() == 6)
		assert(d.bar() == 7)
		assert(d.zzz() == 3)

		assert(isinstance(A.foo, WCapabilityDescriptor) is True)
		assert(isinstance(A.bar, WCapabilityDescriptor) is True)
		assert(isinstance(A.zzz, WCapabilityDescriptor) is False)

		assert(isinstance(B.foo, WCapabilityDescriptor) is False)
		assert(isinstance(B.bar, WCapabilityDescriptor) is True)
		assert(isinstance(B.zzz, WCapabilityDescriptor) is False)

		assert(isinstance(C.foo, WCapabilityDescriptor) is True)
		assert(isinstance(C.bar, WCapabilityDescriptor) is False)
		assert(isinstance(C.zzz, WCapabilityDescriptor) is False)

		assert(isinstance(D.foo, WCapabilityDescriptor) is False)
		assert(isinstance(D.bar, WCapabilityDescriptor) is False)
		assert(isinstance(D.zzz, WCapabilityDescriptor) is False)

		assert(iscapable(A, A.foo) is False)
		assert(iscapable(A, A.bar) is False)
		assert(iscapable(A, B.bar) is False)
		assert(iscapable(A, C.foo) is False)

		assert(iscapable(a, A.foo) is False)
		assert(iscapable(a, A.bar) is False)
		assert(iscapable(a, B.bar) is False)
		assert(iscapable(a, C.foo) is False)

		assert(iscapable(B, A.foo) is True)
		assert(iscapable(B, A.bar) is False)
		assert(iscapable(B, B.bar) is False)
		assert(iscapable(B, C.foo) is True)

		assert(iscapable(b, A.foo) is True)
		assert(iscapable(b, A.bar) is False)
		assert(iscapable(b, B.bar) is False)
		assert(iscapable(b, C.foo) is True)

		assert(iscapable(C, A.foo) is False)
		assert(iscapable(C, A.bar) is True)
		assert(iscapable(C, B.bar) is True)
		assert(iscapable(C, C.foo) is False)

		assert(iscapable(c, A.foo) is False)
		assert(iscapable(c, A.bar) is True)
		assert(iscapable(c, B.bar) is True)
		assert(iscapable(c, C.foo) is False)

		assert(iscapable(D, A.foo) is True)
		assert(iscapable(D, A.bar) is True)
		assert(iscapable(D, B.bar) is True)
		assert(iscapable(D, C.foo) is True)

		assert(iscapable(d, A.foo) is True)
		assert(iscapable(d, A.bar) is True)
		assert(iscapable(d, B.bar) is True)
		assert(iscapable(d, C.foo) is True)


class TestWCapabilitiesHolder:

	def test(self):
		assert(isinstance(WCapabilitiesHolder, WCapabilitiesHolderMeta) is True)

		class A(WCapabilitiesHolder):
			@capability
			def foo(self):
				pass

			@capability
			def bar(self):
				pass

		class B(A):
			pass

		class C(A):

			def foo(self):
				pass

		a = A()
		b = B()
		c = C()

		assert(iscapable(a, A.foo) is False)
		assert(iscapable(b, A.foo) is False)
		assert(iscapable(c, A.foo) is True)

		assert(iscapable(A, A.foo) is False)
		assert(iscapable(B, A.foo) is False)
		assert(iscapable(C, A.foo) is True)

		assert(iscapable(a, A.bar) is False)
		assert(iscapable(b, A.bar) is False)
		assert(iscapable(c, A.bar) is False)

		assert(iscapable(A, A.bar) is False)
		assert(iscapable(B, A.bar) is False)
		assert(iscapable(C, A.bar) is False)

		assert(A.foo not in a)
		assert(A.foo not in b)
		assert(A.foo in c)

		assert(A.bar not in a)
		assert(A.bar not in a)
		assert(A.bar not in a)

		class A(WCapabilitiesHolder):
			@capability
			def foo(self):
				pass

			@capability
			def bar(self):
				pass

		assert(iscapable(c, A.foo) is False)
		assert(A.foo not in c)
