# -*- coding: utf-8 -*-
# wasp_general/<FILENAME>.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# Wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from wasp_general.verify import verify_type

from wasp_general.crypto.sha import WSHA


class WHash:
	""" Class that aggregates different hash-generators. This class is should be used if there is a need to address
	digest generator by its name. As a result - generator (PyCrypto class) is returned. Different PyCrypto classes
	(generators) may have different functions or may have different arguments - this is not a problem, since there
	are SHA-generators only.

	This class may be very much different in a future (like in case of adding new hash-generator).
	"""

	__hash_map__ = {x: WSHA.hash_generator(WSHA.digest_size(x)) for x in WSHA.available_names()}
	""" Available hash generators map 'hash function name' - 'PyCrypto hash class'
	"""

	@staticmethod
	@verify_type(name=str)
	def generator(name):
		""" Return generator by its name

		:param name: name of hash-generator

		:return: PyCrypto class
		"""
		name = name.upper()
		if name not in WHash.__hash_map__.keys():
			raise ValueError('Hash generator "%s" not available' % name)
		return WHash.__hash_map__[name]

	@staticmethod
	def available_generators():
		""" Return names of availalble generators

		:return: tuple of str
		"""
		return tuple(WHash.__hash_map__.keys())
