# -*- coding: utf-8 -*-
# wasp_general/template.py
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

from abc import ABCMeta, abstractmethod
import io
from mako.template import Template
from mako.lookup import TemplateCollection
from mako.runtime import Context

from wasp_general.verify import verify_type, verify_value


class WTemplate(metaclass=ABCMeta):

	@abstractmethod
	def template(self):
		raise NotImplementedError('This method is abstract')


class WMakoTemplate(WTemplate):

	@verify_type(template=Template)
	def __init__(self, template):
		self.__template = template

	def template(self):
		return self.__template


class WTemplateText(WTemplate):

	@verify_type(text_template=str)
	def __init__(self, text_template, **kwargs):
		WTemplate.__init__(self)
		self.__template = Template(text=text_template, **kwargs)

	def template(self):
		return self.__template


class WTemplateFile(WTemplate):

	@verify_type(template_filename=str)
	@verify_value(template_filename=lambda x: len(x) > 0)
	def __init__(self, template_filename, **kwargs):
		WTemplate.__init__(self)
		self.__template = Template(filename=template_filename, **kwargs)

	def template(self):
		return self.__template


class WTemplateLookup(WTemplate):

	@verify_type(template_id=str, template_collection=TemplateCollection)
	def __init__(self, template_id, template_collection):
		WTemplate.__init__(self)
		self.__template_id = template_id
		self.__collection = template_collection

	def template(self):
		return self.__collection.get_template(self.__template_id)


class WTemplateRenderer:

	@verify_type(template=WTemplate, context=(None, dict))
	def __init__(self, template, context=None):
		self.__template = template
		self.__context = context if context is not None else {}

	def template(self):
		return self.__template.template()

	def context(self):
		return self.__context

	def update_context(self, **context_vars):
		self.__context.update(context_vars)

	def render(self, **context_vars):
		template = self.template()
		buffer = io.StringIO()
		context = self.context()
		context.update(context_vars)
		context = Context(buffer, **context)
		template.render_context(context)
		return buffer.getvalue()
