# -*- coding: utf-8 -*-
# wasp_general/network/messenger/composer.py
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

# TODO: document the code
# TODO: write tests for the code

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

from enum import Enum

from wasp_general.verify import verify_type
from wasp_general.network.messenger.proto import WMessengerEnvelopeProto, WMessengerOnionSessionProto
from wasp_general.network.messenger.proto import WMessengerOnionLayerProto
from wasp_general.network.messenger.envelope import WMessengerEnvelope, WMessengerDictEnvelope
from wasp_general.composer import WComposerFactory


class WMessengerComposerLayer(WMessengerOnionLayerProto):

	__layer_name__ = "com.binblob.wasp-general.composer-packer-layer"
	""" Layer name
	"""

	class Mode(Enum):
		compose = 1
		decompose = 2

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionLayerProto.__init__(self, WMessengerComposerLayer.__layer_name__)

	@verify_type('paranoid', envelope=WMessengerEnvelopeProto, session=WMessengerOnionSessionProto, mode=Mode)
	@verify_type('paranoid', composer_factory=WComposerFactory)
	def process(self, envelope, session, mode=None, composer_factory=None,**kwargs):
		""" :meth:`.WMessengerOnionLayerProto.process` implementation
		"""
		if mode == WMessengerComposerLayer.Mode.compose:
			return self.compose(envelope, session, composer_factory, **kwargs)
		elif mode == WMessengerComposerLayer.Mode.decompose:
			return self.decompose(envelope, session, composer_factory, **kwargs)
		raise RuntimeError('Invalid mode was specified')

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerDictEnvelope, composer_factory=WComposerFactory)
	def compose(self, envelope, session, composer_factory, **kwargs):
		return WMessengerEnvelope(
			composer_factory.compose(envelope.message()),
			meta=envelope
		)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerEnvelopeProto, composer_factory=WComposerFactory)
	def decompose(self, envelope, session, composer_factory, **kwargs):
		return WMessengerDictEnvelope(
			composer_factory.decompose(envelope.message()),
			meta=envelope
		)
