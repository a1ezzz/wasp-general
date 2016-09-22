# -*- coding: utf-8 -*-

import pytest

from wasp_general.types.binarray import WBinArray


class TestWBinArray:
	def test_init(self):
		pytest.raises(TypeError, WBinArray, 0.1)
		pytest.raises(ValueError, WBinArray, -1)
		pytest.raises(ValueError, WBinArray, 1, 0)
		assert(isinstance(WBinArray(0, 1), WBinArray) is True)

	def test_len(self):
		assert(len(WBinArray(0, 5)) == 5)
		assert(len(WBinArray(0)) == 1)
		assert(len(WBinArray(4)) == 3)

	def test_str(self):
		assert(str(WBinArray(0, 8)) == '00000000')
		assert(str(WBinArray(3)) == '11')
		assert(str(WBinArray(3, 8)) == '00000011')

	def test_int(self):
		assert(int(WBinArray(5)) == 5)

	def test___getitem__(self):
		assert(WBinArray(6)[2] == 0)
		assert(WBinArray(4)[0] == 1)
		pytest.raises(IndexError, WBinArray(3, 8).__getitem__, 10)
		assert(isinstance(WBinArray(3, 8)[5:], WBinArray) is True)
		assert(str(WBinArray(3, 8)[5:]) == '011')
		assert(str(WBinArray(3, 8)[:4]) == '0000')
		assert(str(WBinArray(3, 8)[3:7]) == '0001')
		assert(isinstance(WBinArray(3, 8)[7:], WBinArray) is True)
		pytest.raises(IndexError, WBinArray(3, 8).__getitem__, slice(10, None))
		pytest.raises(IndexError, WBinArray(3, 8).__getitem__, slice(-1, None))

	def test___setitem__(self):
		a = WBinArray(0, 4)
		a[0] = 1
		assert(int(a) == 8)
		a[0] = 0
		assert(int(a) == 0)
		a[0] = 2
		assert(int(a) == 8)
		pytest.raises(TypeError, "a[0] = 0.1")
		pytest.raises(ValueError, "a[0] = -1")
		pytest.raises(IndexError, "a[-1] = 0")
		pytest.raises(IndexError, "a[8] = 0")

		pytest.raises(OverflowError, "a[0] = 20")
		a = WBinArray(0)
		a[0] = 20

	def test_add_sub(self):
		assert(isinstance(WBinArray(0) + 0, int) is True)
		assert(isinstance(WBinArray(0) - 0, int) is True)
		assert((WBinArray(4) + 2) == 6)
		assert((WBinArray(4) + WBinArray(3)) == 7)
		assert((WBinArray(4) - 2) == 2)
		assert((WBinArray(4) - 6) == -2)
		assert((WBinArray(4) - WBinArray(6)) == -2)

	def test_resize(self):
		a = WBinArray(1, 1)
		pytest.raises(IndexError, a.__getitem__, 2)
		a.resize(3)
		assert(a[2] == 1)
		a.resize(1)
		pytest.raises(IndexError, a.__getitem__, 2)
		assert(a[0] == 1)

	def test_split(self):
		assert(int(WBinArray(13).split(2)[0]) == 3)
		assert(int(WBinArray(13).split(2)[1]) == 1)
		assert(int(WBinArray(17).split(2)[0]) == 1)
		assert(int(WBinArray(17).split(2)[1]) == 0)
		assert(int(WBinArray(17).split(2)[2]) == 1)

	def test_concat(self):
		pytest.raises(TypeError, WBinArray(3, 2).concat, 10)
		assert(int(WBinArray(3, 2).concat(WBinArray(1, 2))) == 13)

		pytest.raises(TypeError, WBinArray(3, 2).rconcat, 10)
		assert(int(WBinArray(3, 2).rconcat(WBinArray(1, 2))) == 7)

	def test_extend(self):
		assert(int(WBinArray(3, 2).extend(WBinArray(1, 2), WBinArray(1))) == 27)

	def test_swipe(self):
		assert(int(WBinArray(13, 4).swipe()) == 11)

	def test_join(self):
		assert(WBinArray.join() is None)
		assert(int(WBinArray(3, 2)) == int(WBinArray.join(WBinArray(3, 2))))
		assert(int(WBinArray.join(WBinArray(3, 2), WBinArray(1, 2))) == 13)
