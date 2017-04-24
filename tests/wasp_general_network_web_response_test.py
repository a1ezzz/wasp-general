# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.web.response import WWebResponse
from wasp_general.network.web.headers import WHTTPHeaders


class TestWWebResponse:

	def test_response(self):
		assert(isinstance(WWebResponse(), WWebResponse) is True)
		assert(WWebResponse().__pushed_responses__() == tuple())
		assert(WWebResponse(status=301).status() == 301)
		assert(WWebResponse(response_data=b'data!').response_data() == b'data!')
		assert(WWebResponse(headers=WHTTPHeaders(headers1='value')).headers()['headers1'] == ('value',))

		response = WWebResponse()
		pushed_response1 = WWebResponse()
		pushed_response2 = WWebResponse()
		response.__push__(pushed_response1, pushed_response2)
		assert(response.__pushed_responses__() == (pushed_response1, pushed_response2))
