# -*- coding: utf-8 -*-

import pytest

from wasp_general.crypto.random import random_bits, random_int, random_bytes


def test_random_bits():
	assert(isinstance(random_bits(3), int) is True)
	assert(random_bits(0) == 0)
	assert(random_bits(10) != random_bits(10))


def test_random_int():
	assert(isinstance(random_int(10), int) is True)
	assert(random_int(0) == 0)
	assert(random_int(1000) != random_int(1000))
	assert(random_int(10) <= 10)


def test_random_bytes():
	pytest.raises(TypeError, random_bytes)
	pytest.raises(TypeError, random_bytes, '1')
	pytest.raises(ValueError, random_bytes, -1)

	assert(isinstance(random_bytes(0), bytes) is True)
	assert(isinstance(random_bytes(3), bytes) is True)
	assert(random_bytes(0) == b'')
	assert(len(random_bytes(10)) == 10)
	assert(random_bytes(10) != random_bytes(10))
