# -*- coding: utf-8 -*-

from wasp_general.template import WTemplateText

from wasp_general.command.command import WCommand
from wasp_general.command.template_command import WTemplateResultCommand, WCommandResultTemplate


class TestWTemplateResultCommand:

	def test(self):
		template = WTemplateText('hello: ${var}')

		template_result_cmd = WTemplateResultCommand(template, 'test')
		assert(isinstance(template_result_cmd, WTemplateResultCommand) is True)
		assert(isinstance(template_result_cmd, WCommand) is True)
		assert(template_result_cmd.template() == template)
		assert(template_result_cmd.template_context() == {})

		template_result_cmd = WTemplateResultCommand(template, 'test', template_context={'var': 'world'})
		assert(template_result_cmd.template_context() == {'var': 'world'})

		result = template_result_cmd.result_template()
		assert(isinstance(result, WCommandResultTemplate) is True)
		assert(str(result) == 'hello: world')

		assert(template_result_cmd.match('test') is True)
		assert(template_result_cmd.match('test', 'foo') is False)

		result = template_result_cmd._exec('test')
		assert(isinstance(result, WCommandResultTemplate) is True)
		assert(str(result) == 'hello: world')
