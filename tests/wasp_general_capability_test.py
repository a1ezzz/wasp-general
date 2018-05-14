# -*- coding: utf-8 -*-

import pytest
from abc import ABCMeta

from wasp_general.capability import WCapabilitiesHolderMeta, WCapabilitiesHolder


class TestWCapabilitiesHolderMeta:

	def test(self):
		assert(issubclass(WCapabilitiesHolderMeta, ABCMeta) is True)
		assert(callable(WCapabilitiesHolderMeta.capability) is True)


class TestWCapabilitiesHolder:

	def test(self):
		c_h = WCapabilitiesHolder()
		assert(c_h.__class_capabilities__ == {})

		class A(WCapabilitiesHolder):

			@WCapabilitiesHolderMeta.capability('bar')
			def foo(self, *args):
				return list(args)

		a = A()
		assert(a.capability('foo') is None)
		assert(a.capability('bar') is not None)
		assert(a.capability('bar') == a.foo)
		assert(a.foo(1, 2, 3) == [1, 2, 3])
		assert(a.capability('bar')(1, 2, 3) == [1, 2, 3])

		class B(WCapabilitiesHolder):

			@WCapabilitiesHolderMeta.capability('foo')
			def bar(self, *args):
				result = list(args)
				result.reverse()
				return result

		b = B()
		assert(b.capability('bar') is None)
		assert(b.capability('foo') is not None)
		assert(b.capability('foo') == b.bar)
		assert(b.bar(1, 2, 3) == [3, 2, 1])
		assert(b.capability('foo')(1, 2, 3) == [3, 2, 1])

		class C(A, B):
			pass

		c = C()
		assert(c.capability('bar') == c.foo)
		assert(c.capability('bar') is not None)
		assert(c.foo(1, 2, 3) == [1, 2, 3])
		assert(c.capability('bar')(1, 2, 3) == [1, 2, 3])
		assert(c.capability('foo') == c.bar)
		assert(c.capability('foo') is not None)
		assert(c.bar(1, 2, 3) == [3, 2, 1])
		assert(c.capability('foo')(1, 2, 3) == [3, 2, 1])

		class D(WCapabilitiesHolder):

			@WCapabilitiesHolderMeta.capability('bar')
			def foo_enhanced(self, *args):
				return list(args)

		pytest.raises(ValueError, "class E(A, D): pass")

		class E(A, D):

			def foo(self, *args):
				return A.foo(self, *args)

			def foo_enhanced(self, *args):
				return D.foo_enhanced(self, *args)

		e = E()
		assert(e.foo(1, 2, 3) == [1, 2, 3])
		assert(e.foo_enhanced(1, 2, 3) == [1, 2, 3])
