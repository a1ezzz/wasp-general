# -*- coding: utf-8 -*-
# wasp_general/network/web/template_response.py
#
# Copyright (C) 2016 the wasp-general authors and contributors
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

import io
from mako.template import Template
from mako.runtime import Context

from wasp_general.verify import verify_type

from wasp_general.template import WTemplate

from wasp_general.network.web.headers import WHTTPHeaders
from wasp_general.network.web.response import WWebResponse
from wasp_general.template import WTemplateRenderer


class WWebTemplateResponse(WTemplateRenderer, WWebResponse):

	@verify_type('paranoid', status=(int, None), template=WTemplate, context=(None, dict))
	@verify_type('paranoid', headers=(WHTTPHeaders, None))
	def __init__(self, template, context=None, status=None, headers=None):
		WTemplateRenderer.__init__(self, template, context=context)
		WWebResponse.__init__(self, status=status, headers=(headers if headers is not None else WHTTPHeaders()))

		if self.headers()['Content-Type'] is None:
			self.headers().add_headers('Content-Type', 'text/html')

	def response_data(self):
		return self.render()
