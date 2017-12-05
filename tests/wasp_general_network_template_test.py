# -*- coding: utf-8 -*-

import pytest

from mako.template import Template
from mako.lookup import TemplateCollection

from wasp_general.network.template import WTemplate, WMakoTemplate, WTemplateText, WTemplateFile
from wasp_general.network.template import WTemplateLookup


def test_abstract():
	pytest.raises(TypeError, WTemplate)
	pytest.raises(NotImplementedError, WTemplate.template, None)


class TestWMakoTemplateWrapper:

	def test_template(self):
		t = Template(text='code')
		wr = WMakoTemplate(t)
		assert(isinstance(wr, WMakoTemplate) is True)
		assert(isinstance(wr, WTemplate) is True)
		assert(wr.template() == t)


class TestWWebTemplateText:

	def test_template(self):
		t = WTemplateText('template code')
		assert(isinstance(t, WTemplateText) is True)
		assert(isinstance(t, WTemplate) is True)
		assert(t.template().render() == 'template code')


class TestWWebTemplateFile:

	def test_template(self, tmpdir):
		f = tmpdir.join('tmp')
		f.write('template')

		t = WTemplateFile(f.strpath)
		assert(isinstance(t, WTemplateFile) is True)
		assert(isinstance(t, WTemplate) is True)
		assert(t.template().render() == 'template')


class TestWWebTemplateLookup:

	class Collection(TemplateCollection):

		def get_template(self, uri, relativeto=None):
			return WTemplateText('tmpl: ' + uri)

	def test_template(self):
		collection = TestWWebTemplateLookup.Collection()
		t = WTemplateLookup('uri1', collection)

		assert(isinstance(t, WTemplateLookup) is True)
		assert(isinstance(t, WTemplate) is True)
		assert(t.template().render() == 'tmpl: uri1')
