# -*- coding: utf-8 -*-
# wasp_general/network/messenger/packers.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
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

import json
from datetime import datetime

from wasp_general.verify import verify_type

from wasp_general.datetime import utc_datetime

from wasp_general.network.messenger.proto import WMessengerEnvelopeProto, WMessengerOnionSessionProto
from wasp_general.network.messenger.layers import WMessengerOnionPackerLayerProto
from wasp_general.network.messenger.envelope import WMessengerEnvelope, WMessengerTextEnvelope


class WMessengerJSONPacker(WMessengerOnionPackerLayerProto):

	__layer_name__ = "com.binblob.wasp-general.json-packer-layer"
	""" Layer name
	"""

	class JSONEncoder(json.encoder.JSONEncoder):

		def default(self, o):
			if isinstance(o, set) is True:
				return list(o)
			elif isinstance(o, bytes):
				return [x for x in o]
			elif isinstance(o, datetime):
				return utc_datetime(o, local_value=False).isoformat()
			return json.encoder.JSONEncoder.default(self, o)

	def __init__(self):
		""" Construct new layer
		"""
		WMessengerOnionPackerLayerProto.__init__(self, WMessengerJSONPacker.__layer_name__)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerEnvelopeProto)
	def pack(self, envelope, session, **kwargs):
		json_data = json.dumps(envelope.message(), cls=WMessengerJSONPacker.JSONEncoder)
		return WMessengerTextEnvelope(json_data, meta=envelope)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerTextEnvelope)
	def unpack(self, envelope, session, **kwargs):
		return WMessengerEnvelope(json.loads(envelope.message()), meta=envelope)
