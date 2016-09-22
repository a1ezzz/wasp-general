# -*- coding: utf-8 -*-

import pytest

from wasp_general.types.binarray import WBinArray
from wasp_general.types.bytearray import WFixedSizeByteArray


class TestWFixedSizeByteArray:

	def test_init(self):
		pytest.raises(ValueError, WFixedSizeByteArray, 0, WBinArray(1))
		pytest.raises(ValueError, WFixedSizeByteArray, 0, WBinArray(300))
		pytest.raises(OverflowError, WFixedSizeByteArray, 1, b'12')
		assert(isinstance(WFixedSizeByteArray(0), WFixedSizeByteArray) is True)
		assert(isinstance(WFixedSizeByteArray(1), WFixedSizeByteArray) is True)
		assert(isinstance(WFixedSizeByteArray(1, WBinArray(0)), WFixedSizeByteArray) is True)
		assert(isinstance(WFixedSizeByteArray(1, 0), WFixedSizeByteArray) is True)

	def test_bin_array(self):
		assert(isinstance(WFixedSizeByteArray(1, 1).bin_array(), list))
		assert(len((WFixedSizeByteArray(2, 1).bin_array())) == 2)
		assert(int((WFixedSizeByteArray(2, 1).bin_array()[0])) == 0)
		assert(int((WFixedSizeByteArray(2, 1).bin_array()[1])) == 1)

	def test_bin_value(self):
		assert(isinstance(WFixedSizeByteArray(1, 1).bin_value(), WBinArray))
		assert(str(WFixedSizeByteArray(1, 1).bin_value()) == '00000001')
		assert(str(WFixedSizeByteArray(2, 1).bin_value()) == '0000000000000001')

	def test_resize(self):
		a = WFixedSizeByteArray(0)
		pytest.raises(IndexError, a.__getitem__, 0)
		a.resize(1)
		assert(int(a[0]) == 0)
		pytest.raises(ValueError, a.resize, 0)

	def test_len(self):
		assert(len(WFixedSizeByteArray(0)) == 0)
		assert(len(WFixedSizeByteArray(1)) == 1)

	def test_str(self):
		assert(str(WFixedSizeByteArray(2, 1)) == "['00000000', '00000001']")

	def test_swipe(self):
		assert(str(WFixedSizeByteArray(2, 1).swipe()) == "['00000001', '00000000']")

	def test_getitem(self):
		assert(int(WFixedSizeByteArray(2, 256)[0]) == 1)
		assert(int(WFixedSizeByteArray(2, 256)[1]) == 0)
		assert(isinstance(WFixedSizeByteArray(3, 65536)[:2], list))
		assert(len(WFixedSizeByteArray(3, 65536)[:2]) == 2)
		assert(int(WBinArray.join(*WFixedSizeByteArray(3, 65536)[:2])) == 256)
		assert(int(WBinArray.join(*WFixedSizeByteArray(3, 65536)[1:])) == 0)

	def test_setitem(self):
		a = WFixedSizeByteArray(1)
		pytest.raises(IndexError, a.__setitem__, 2, 5)
		a[0] = WBinArray(1)
		assert(int(a[0]) == 1)
		a[0] = WBinArray(1, 8)
		assert(int(a[0]) == 1)
		a[0] = 1
		assert(int(a[0]) == 1)
		pytest.raises(ValueError, a.__setitem__, 0, 257)
		pytest.raises(ValueError, a.__setitem__, 0, WBinArray(257))
		a[0] = WBinArray(254, 9)
		assert(int(a[0]) == 254)

	def test_bytes(self):
		a = WFixedSizeByteArray(3)
		a[0] = 97
		a[1] = 115
		a[2] = 100
		assert(bytes(a) == b'asd')
