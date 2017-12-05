# -*- coding: utf-8 -*-

import pytest

from wasp_general.network.web.proto import WWebResponseProto
from wasp_general.network.template import WTemplate, WTemplateText
from wasp_general.network.web.template_response import WWebTemplateResponse


class TestWWebTemplateResponse:

	class CorruptedTemplate(WTemplate):

		def template(self):
			return

	def test_response(self):
		response = WWebTemplateResponse(WTemplateText('code'))

		assert(isinstance(response, WWebTemplateResponse) is True)
		assert(isinstance(response, WWebResponseProto) is True)
		assert(response.response_data() == 'code')

		response = WWebTemplateResponse(TestWWebTemplateResponse.CorruptedTemplate())
		pytest.raises(TypeError, response.response_data)
