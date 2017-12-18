# -*- coding: utf-8 -*-

import pytest

from wasp_general.command.command import WCommandProto, WCommand, WCommandPrioritizedSelector
from wasp_general.command.command import WCommandSet
from wasp_general.command.result import WPlainCommandResult
from wasp_general.composer import WComposerProto

from wasp_general.command.context import WContextProto, WContext, WCommandContextAdapter, WCommandContext
from wasp_general.command.context import WContextComposer


def test_abstract():
	pytest.raises(TypeError, WContextProto)
	pytest.raises(NotImplementedError, WContextProto.context_name, None)
	pytest.raises(NotImplementedError, WContextProto.context_value, None)
	pytest.raises(NotImplementedError, WContextProto.linked_context, None)

	pytest.raises(TypeError, WCommandContextAdapter)
	pytest.raises(NotImplementedError, WCommandContextAdapter.adapt, None)


class TestWContextProto:

	class Context(WContextProto):

		def context_name(self):
			return 'context1'

		def context_value(self):
			return None

		def linked_context(self):
			return None

	def test(self):
		c1 = TestWContextProto.Context()
		assert(len(c1) == 1)

		c2 = TestWContextProto.Context()
		c2.linked_context = lambda: c1
		assert(len(c1) == 1)
		assert(len(c2) == 2)

		c3 = TestWContextProto.Context()
		c3.linked_context = lambda: c2
		assert(len(c1) == 1)
		assert(len(c2) == 2)
		assert(len(c3) == 3)


class TestWContext:

	def test(self):
		c_r1 = WContext('context1')
		assert(isinstance(c_r1, WContext) is True)
		assert(isinstance(c_r1, WContextProto) is True)
		assert(c_r1 != 1)

		assert(c_r1.context_name() == 'context1')
		assert(c_r1.context_value() is None)
		assert(c_r1.linked_context() is None)

		c_r2 = WContext('context2', 'context-value', c_r1)
		assert(c_r2.context_name() == 'context2')
		assert(c_r2.context_value() == 'context-value')
		assert(c_r2.linked_context() == c_r1)
		assert(c_r2 != c_r1)

		c_r3 = WContext('context1', None, c_r2)
		assert(c_r1 != c_r3)
		assert(c_r3 != c_r1)

		assert(WContext.export_context(c_r2) == (('context1', None), ('context2', 'context-value')))
		assert(WContext.export_context(None) is None)


class TestWContextComposer:

	def test(self):
		context1 = WContext('context1')
		context2 = WContext('context2', 'context-value', context1)

		composer = WContextComposer()
		assert(isinstance(composer, WContextComposer) is True)
		assert(isinstance(composer, WComposerProto) is True)

		decomposed_context = composer.decompose(context2)
		composed_context = composer.compose(decomposed_context)
		assert(composed_context == context2)


class TestWCommandContextAdapter:

	class Adapter(WCommandContextAdapter):

		def adapt(self, *command_tokens, request_context=None):
			if request_context is None:
				return command_tokens

			result = [request_context.context_name()]
			result.extend(command_tokens)
			return tuple(result)

	def test(self):
		spec = WContext.specification('context1', 'context2')
		a = TestWCommandContextAdapter.Adapter(spec)
		assert(isinstance(a, WCommandContextAdapter) is True)
		assert(a.specification() == spec)

		c_r1 = WContext('context1')
		c_r2 = WContext('context2', 'context-value', c_r1)

		assert(a.adapt('hello', 'world', request_context=c_r1) == ('context1', 'hello', 'world'))
		assert(a.adapt('hello', 'world', request_context=c_r2) == ('context2', 'hello', 'world'))

		assert(TestWCommandContextAdapter.Adapter(WContext.specification()).match() is True)
		assert(a.match() is False)
		assert(a.match(c_r1) is False)
		assert(a.match(c_r2) is True)


class TestWCommandContext:

	class Command(WCommand):

		def _exec(self, *command_tokens, **kwargs):
			return WPlainCommandResult('OK')

	class Adapter(WCommandContextAdapter):
		def adapt(self, *command_tokens, command_context=None):
			if command_context is None:
				return command_tokens

			result = [command_context.context_value()]
			result.extend(command_tokens)
			return tuple(result)

	def test(self):
		base_command = TestWCommandContext.Command('hello', 'world')
		adapter = TestWCommandContext.Adapter(WContext.specification('context'))
		command = WCommandContext(base_command, adapter)

		assert(isinstance(command, WCommandContext) is True)
		assert(isinstance(command, WCommandProto) is True)
		assert(command.original_command() == base_command)
		assert(command.adapter() == adapter)

		adapter2 = TestWCommandContext.Adapter(WContext.specification())
		command2 = WCommandContext(base_command, adapter2)
		assert(command2.match('hello', 'world', 'yeah') is True)
		assert(command.match('hello', 'world', 'yeah') is False)
		command_context = WContext('context', 'hello')
		assert(command.match('world', command_context=command_context) is True)

		assert(str(command2.exec('hello', 'world')) == 'OK')
		assert(str(command.exec('world', command_context=command_context)) == 'OK')
		pytest.raises(RuntimeError, command.exec, 'hello', 'world')
