# -*- coding: utf-8 -*-

import pytest

from wasp_general.command.command import WCommandProto, WCommand, WCommandResult, WCommandPrioritizedSelector
from wasp_general.command.command import WCommandSet

from wasp_general.command.context import WContextProto, WContext, WCommandContextAdapter, WCommandContext
from wasp_general.command.context import WCommandContextResult, WCommandContextSet


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


class TestWCommandContextRequest:

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

		def _exec(self, *command_tokens):
			return WCommandResult('OK')

	class Adapter(WCommandContextAdapter):
		def adapt(self, *command_tokens, request_context=None):
			if request_context is None:
				return command_tokens

			result = [request_context.context_value()]
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
		request_context = WContext('context', 'hello')
		assert(command.match('world', request_context=request_context) is True)

		assert(command2.exec('hello', 'world').output == 'OK')
		assert(command.exec('world', request_context=request_context).output == 'OK')
		pytest.raises(RuntimeError, command.exec, 'hello', 'world')


class TestWCommandContextResult:

	def test(self):
		context_request1 = WContext('hello')
		context_request2 = WContext('world', 'context-value', context_request1)
		command_result = WCommandContextResult('output', 1, context_request2)

		assert(isinstance(command_result, WCommandContextResult) is True)
		assert(isinstance(command_result, WCommandResult) is True)
		assert (isinstance(command_result.context, WContext) is True)
		assert(WContext.export_context(command_result.context) == (('hello', None), ('world', 'context-value')))
		assert(command_result.output == 'output')
		assert(command_result.error == 1)


class TestWCommandContextSet:

	class Command(WCommand):

		def _exec(self, *command_tokens, **command_env):
			return WCommandResult('simple OK')

	def test(self):
		selector = WCommandPrioritizedSelector()
		command_set = WCommandContextSet(selector)
		assert(command_set.commands() == selector)

		command_set = WCommandContextSet()
		assert(command_set.context() is None)

		base_command = TestWCommandContext.Command('hello', 'world')
		adapter = TestWCommandContext.Adapter(WContext.specification('context'))
		command = WCommandContext(base_command, adapter)
		simple_command = TestWCommandContextSet.Command('create', 'world')
		command_set.commands().add(command)
		command_set.commands().add(simple_command)

		set_command = TestWCommandContextSet.Command('set')

		def test_exec1(token, **kw):
			return WCommandContextResult(output='context set', context=WContext('context', 'hello'))
		set_command._exec = test_exec1

		command_set.commands().add(set_command)

		assert(command_set.exec('create world').output == 'simple OK')

		assert(command_set.context() is None)
		result = command_set.exec('set')
		assert(result.output == 'context set')
		assert(command_set.context() is not None)
		assert(command_set.context().context_name() == 'context')
		assert(command_set.context().context_value() == 'hello')

		result = command_set.exec('world')
		assert(result.output == 'OK')

		pytest.raises(WCommandSet.NoCommandFound, command_set.exec, 'foo')
