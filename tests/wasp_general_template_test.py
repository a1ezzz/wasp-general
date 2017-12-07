# -*- coding: utf-8 -*-

import pytest

from mako.template import Template
from mako.lookup import TemplateCollection

from wasp_general.template import WTemplate, WMakoTemplate, WTemplateText, WTemplateFile
from wasp_general.template import WTemplateLookup, WTemplateRenderer


def test_abstract():
	pytest.raises(TypeError, WTemplate)
	pytest.raises(NotImplementedError, WTemplate.template, None)


class TestWMakoTemplate:

	def test_template(self):
		t = Template(text='code')
		wr = WMakoTemplate(t)
		assert(isinstance(wr, WMakoTemplate) is True)
		assert(isinstance(wr, WTemplate) is True)
		assert(wr.template() == t)


class TestWTemplateText:

	def test_template(self):
		t = WTemplateText('template code')
		assert(isinstance(t, WTemplateText) is True)
		assert(isinstance(t, WTemplate) is True)
		assert(t.template().render() == 'template code')


class TestWTemplateFile:

	def test_template(self, tmpdir):
		f = tmpdir.join('tmp')
		f.write('template')

		t = WTemplateFile(f.strpath)
		assert(isinstance(t, WTemplateFile) is True)
		assert(isinstance(t, WTemplate) is True)
		assert(t.template().render() == 'template')


class TestWTemplateLookup:

	class Collection(TemplateCollection):

		def get_template(self, uri, relativeto=None):
			return WTemplateText('tmpl: ' + uri).template()

	def test_template(self):
		collection = TestWTemplateLookup.Collection()
		t = WTemplateLookup('uri1', collection)

		assert(isinstance(t, WTemplateLookup) is True)
		assert(isinstance(t, WTemplate) is True)
		assert(t.template().render() == 'tmpl: uri1')


class TestWTemplateRenderer:

	def test_renderer(self):
		template = WTemplateText('test code')
		renderer = WTemplateRenderer(template)
		assert(renderer.template() == template.template())
		assert(renderer.context() == {})
		assert(renderer.render() == 'test code')

		template = WTemplateText('var a is ${a}')
		renderer = WTemplateRenderer(template, context={'a': 1})
		assert(renderer.render() == 'var a is 1')

		renderer.update_context(a='2')
		assert(renderer.render() == 'var a is 2')
