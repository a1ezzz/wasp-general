# -*- coding: utf-8 -*-
# wasp_general/template_command.py
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

from wasp_general.verify import verify_type
from wasp_general.command.result import WPlainCommandResult
from wasp_general.command.command import WCommand
from wasp_general.template import WTemplateRenderer, WTemplate


class WCommandResultTemplate(WPlainCommandResult, WTemplateRenderer):

	@verify_type('paranoid', template=WTemplate)
	def __init__(self, template, **command_env):
		WPlainCommandResult.__init__(self, '', **command_env)
		WTemplateRenderer.__init__(self, template)
		self.__template = template

	def __str__(self):
		return self.render()


class WTemplateResultCommand(WCommand):
	""" Simple command that returns "template-result", that can be "rendered" to str object later. In most time,
	this and derived classes return static template, which result is the same. The only requirement for execution
	of this command is to full command match. If :class:`.WTemplateResultCommand` was constructed with tokens like
	"foo", "bar" then only "foo bar" command will be matched.  (Note. For example, if :class:`.WCommand` object
	was constructed with tokens: "foo", "bar", then any of the following commands will be matched: "foo bar",
	"foo bar 1", "foo bar 2 3".)
	"""

	@verify_type('paranoid', command_tokens=str)
	@verify_type(template=WTemplate, template_context=(dict, None))
	def __init__(self, template, *command_tokens, template_context=None):
		""" Create new static template command

		:param template: template to use as result
		:param command_tokens: tokens that is used for command matching
		:param template_context: context that is used for rendering the template
		"""
		WCommand.__init__(self, *command_tokens)
		self.__template = template
		self.__template_context = template_context if template_context is not None else {}

	def template(self):
		""" Return template object (that will be used in result)

		:return: WTemplate
		"""
		return self.__template

	def template_context(self):
		""" Return context with which template will be rendered

		:return: dict
		"""
		return self.__template_context

	def result_template(self, *command_tokens, **command_env):
		""" Generate template result. command_tokens and command_env arguments are used for template
		detailing

		:param command_tokens: same as command_tokens in :meth:`.WCommandProto.match` and \
		:meth:`.WCommandProto.exec` methods (so as :meth:`.WCommand._exec`)
		:param command_env: same as command_env in :meth:`.WCommandProto.match` and \
		:meth:`.WCommandProto.exec` methods (so as :meth:`.WCommand._exec`)

		:return: WCommandResultTemplate
		"""
		result = WCommandResultTemplate(self.template())
		result.update_context(**self.template_context())
		return result

	def match(self, *command_tokens, **command_env):
		""" same as :meth:`.WCommand.meth` method, but checks for extra arguments also (no extra arguments is
		allowed)
		"""
		if command_tokens == self.command():
			return True
		return False

	def _exec(self, *command_tokens, **command_env):
		""" :meth:`.WCommand._exec` implementation
		"""
		return self.result_template(*command_tokens, **command_env)
