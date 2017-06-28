# -*- coding: utf-8 -*-
# wasp_general/network/messenger/transport.py
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

from wasp_general.verify import verify_type

from wasp_general.network.messenger.proto import WMessengerOnionLayerProto, WMessengerOnionSessionProto
from wasp_general.network.messenger.proto import WMessengerEnvelopeProto
from wasp_general.network.messenger.envelope import WMessengerBytesEnvelope

from wasp_general.network.service import WZMQHandler, WZMQSyncAgent


class WMessengerSendAgentLayer(WMessengerOnionLayerProto):

	__layer_name__ = "com.binblob.wasp-general.send-agent-layer"
	""" Layer name
	"""

	def __init__(self):
		WMessengerOnionLayerProto.__init__(self, WMessengerSendAgentLayer.__layer_name__)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerBytesEnvelope, send_agent=WZMQHandler.SendAgent, handler=WZMQHandler)
	def process(self, envelope, session, send_agent=None, handler=None, **kwargs):
		send_agent.send(handler, envelope.message())
		return envelope


class WMessengerSyncReceiveAgentLayer(WMessengerOnionLayerProto):
	__layer_name__ = "com.binblob.wasp-general.sync-receive-agent-layer"
	""" Layer name
	"""

	def __init__(self):
		WMessengerOnionLayerProto.__init__(self, WMessengerSyncReceiveAgentLayer.__layer_name__)

	@verify_type('paranoid', session=WMessengerOnionSessionProto)
	@verify_type(envelope=WMessengerEnvelopeProto, receive_agent=WZMQSyncAgent, timeout=(int, float, None))
	@verify_type(copy_meta=(bool, None))
	def process(self, envelope, session, receive_agent=None, timeout=None, copy_meta=None, **kwargs):
		timeout = timeout if timeout is not None else receive_agent.timeout()
		if receive_agent.event().wait(timeout) is not True:
			raise TimeoutError('Response timeout')
		meta = None
		if copy_meta is not None and copy_meta is True:
			meta = envelope
		return WMessengerBytesEnvelope(data=b''.join(receive_agent.data()), meta=meta)
