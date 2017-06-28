# -*- coding: utf-8 -*-
# wasp_general/network/web/template.py
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
from mako.lookup import TemplateCollection
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type, verify_value

from wasp_general.network.web.headers import WHTTPHeaders
from wasp_general.network.web.response import WWebResponse


class WWebTemplate(metaclass=ABCMeta):

	@abstractmethod
	def template(self):
		raise NotImplementedError('This method is abstract')


class WMakoTemplateWrapper(WWebTemplate):

	@verify_type(template=Template)
	def __init__(self, template):
		self.__template = template

	def template(self):
		return self.__template


class WWebTemplateText(WWebTemplate):

	@verify_type(text_template=str)
	def __init__(self, text_template, **kwargs):
		WWebTemplate.__init__(self)
		self.__template = Template(text=text_template, **kwargs)

	def template(self):
		return self.__template


class WWebTemplateFile(WWebTemplate):

	@verify_type(template_filename=str)
	@verify_value(template_filename=lambda x: len(x) > 0)
	def __init__(self, template_filename, **kwargs):
		WWebTemplate.__init__(self)
		self.__template = Template(filename=template_filename, **kwargs)

	def template(self):
		return self.__template


class WWebTemplateLookup(WWebTemplate):

	@verify_type(template_id=str, template_collection=TemplateCollection)
	def __init__(self, template_id, template_collection):
		WWebTemplate.__init__(self)
		self.__template_id = template_id
		self.__collection = template_collection

	def template(self):
		return self.__collection.get_template(self.__template_id).template()


class WWebTemplateResponse(WWebResponse):

	@verify_type('paranoid', status=(int, None))
	@verify_type(template=WWebTemplate, context=(None, dict), headers=(WHTTPHeaders, None))
	def __init__(self, template, context=None, status=None, headers=None):
		WWebResponse.__init__(self, status=status, headers=(headers if headers is not None else WHTTPHeaders()))
		self.__template = template
		self.__context = context if context is not None else {}
		if self.headers()['Content-Type'] is None:
			self.headers().add_headers('Content-Type', 'text/html')

	def response_data(self):
		return self.render()

	def render(self):
		template = self.__template.template()
		if isinstance(template, Template) is False:
			raise TypeError('Invalid template type')

		buffer = io.StringIO()
		context = Context(buffer, **self.__context)
		template.render_context(context)
		return buffer.getvalue()
