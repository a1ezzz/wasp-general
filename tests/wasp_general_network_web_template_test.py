# -*- coding: utf-8 -*-

import pytest

from mako.template import Template
from mako.lookup import TemplateCollection

from wasp_general.network.web.proto import WWebResponseProto
from wasp_general.network.web.template import WWebTemplate, WMakoTemplateWrapper, WWebTemplateText, WWebTemplateFile
from wasp_general.network.web.template import WWebTemplateLookup, WWebTemplateResponse


def test_abstract():
	pytest.raises(TypeError, WWebTemplate)
	pytest.raises(NotImplementedError, WWebTemplate.template, None)


class TestWMakoTemplateWrapper:

	def test_template(self):
		t = Template(text='code')
		wr = WMakoTemplateWrapper(t)
		assert(isinstance(wr, WMakoTemplateWrapper) is True)
		assert(isinstance(wr, WWebTemplate) is True)
		assert(wr.template() == t)


class TestWWebTemplateText:

	def test_template(self):
		t = WWebTemplateText('template code')
		assert(isinstance(t, WWebTemplateText) is True)
		assert(isinstance(t, WWebTemplate) is True)
		assert(t.template().render() == 'template code')


class TestWWebTemplateFile:

	def test_template(self, tmpdir):
		f = tmpdir.join('tmp')
		f.write('template')

		t = WWebTemplateFile(f.strpath)
		assert(isinstance(t, WWebTemplateFile) is True)
		assert(isinstance(t, WWebTemplate) is True)
		assert(t.template().render() == 'template')


class TestWWebTemplateLookup:

	class Collection(TemplateCollection):

		def get_template(self, uri, relativeto=None):
			return WWebTemplateText('tmpl: ' + uri)

	def test_template(self):
		collection = TestWWebTemplateLookup.Collection()
		t = WWebTemplateLookup('uri1', collection)

		assert(isinstance(t, WWebTemplateLookup) is True)
		assert(isinstance(t, WWebTemplate) is True)
		assert(t.template().render() == 'tmpl: uri1')


class TestWWebTemplateResponse:

	class CorruptedTemplate(WWebTemplate):

		def template(self):
			return

	def test_response(self):
		response = WWebTemplateResponse(WWebTemplateText('code'))

		assert(isinstance(response, WWebTemplateResponse) is True)
		assert(isinstance(response, WWebResponseProto) is True)
		assert(response.response_data() == 'code')

		response = WWebTemplateResponse(TestWWebTemplateResponse.CorruptedTemplate())
		pytest.raises(TypeError, response.response_data)
