# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.web.debug import WWebDebugInfo
from wasp_general.network.web.proto import WWebSessionProto
from wasp_general.network.web.request import WWebRequest
from wasp_general.network.web.response import WWebResponse


def test_abstract():

	class Session(WWebSessionProto):

		def client_address(self):
			pass

		def server_address(self):
			pass

		def protocol(self):
			pass

		def protocol_version(self):
			pass

		def read_request(self):
			pass

		def write_response(self, request, response):
			pass

		def session_close(self):
			pass

	pytest.raises(TypeError, WWebDebugInfo)
	pytest.raises(NotImplementedError, WWebDebugInfo.session_id, None)
	pytest.raises(
		NotImplementedError, WWebDebugInfo.request, None, None, WWebRequest(Session(), 'GET', '/'), '2', 'https'
	)
	pytest.raises(NotImplementedError, WWebDebugInfo.response, None, None, WWebResponse())
	pytest.raises(NotImplementedError, WWebDebugInfo.target_route, None, None, None)
	pytest.raises(NotImplementedError, WWebDebugInfo.exception, None, None, ValueError(''))
	pytest.raises(NotImplementedError, WWebDebugInfo.finalize, None, None)
