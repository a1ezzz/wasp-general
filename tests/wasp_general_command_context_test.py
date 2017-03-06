# -*- coding: utf-8 -*-

import pytest

from wasp_general.command import WCommandProto, WCommand, WCommandResult, WCommandPrioritizedSelector, WCommandSet

from wasp_general.command_context import WCommandContextRequestProto, WCommandContextRequest, WContextSpecification
from wasp_general.command_context import WCommandContextAdapter, WCommandContext, WCommandContextResult
from wasp_general.command_context import WCommandContextSelector, WCommandContextSet


def test_abstract():
	pytest.raises(TypeError, WCommandContextRequestProto)
	pytest.raises(NotImplementedError, WCommandContextRequestProto.context_name, None)
	pytest.raises(NotImplementedError, WCommandContextRequestProto.context_value, None)
	pytest.raises(NotImplementedError, WCommandContextRequestProto.linked_context, None)

	pytest.raises(TypeError, WCommandContextAdapter)
	pytest.raises(NotImplementedError, WCommandContextAdapter.adapt, None)


class TestWCommandContextRequest:

	def test(self):
		c_r1 = WCommandContextRequest('context1')
		assert(isinstance(c_r1, WCommandContextRequest) is True)
		assert(isinstance(c_r1, WCommandContextRequestProto) is True)

		assert(c_r1.context_name() == 'context1')
		assert(c_r1.context_value() is None)
		assert(c_r1.linked_context() is None)

		c_r2 = WCommandContextRequest('context2', 'context-value', c_r1)
		assert(c_r2.context_name() == 'context2')
		assert(c_r2.context_value() == 'context-value')
		assert(c_r2.linked_context() == c_r1)


class TestWContextSpecification:

	def test(self):
		c_s = WContextSpecification()
		assert(len(c_s) == 0)
		assert([x for x in c_s] == [])

		c_s = WContextSpecification('context1', 'context2')
		assert(len(c_s) == 2)
		assert([x for x in c_s] == ['context1', 'context2'])


class TestWCommandContextAdapter:

	class Adapter(WCommandContextAdapter):

		def adapt(self, *command_tokens, request_context=None):
			if request_context is None:
				return command_tokens

			result = [request_context.context_name()]
			result.extend(command_tokens)
			return tuple(result)

	def test(self):
		spec = WContextSpecification('context1', 'context2')
		a = TestWCommandContextAdapter.Adapter(spec)
		assert(isinstance(a, WCommandContextAdapter) is True)
		assert(a.specification() == spec)

		c_r1 = WCommandContextRequest('context1')
		c_r2 = WCommandContextRequest('context2', 'context-value', c_r1)

		assert(a.adapt('hello', 'world', request_context=c_r1) == ('context1', 'hello', 'world'))
		assert(a.adapt('hello', 'world', request_context=c_r2) == ('context2', 'hello', 'world'))

		assert(TestWCommandContextAdapter.Adapter(WContextSpecification()).match() is True)
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
		adapter = TestWCommandContext.Adapter(WContextSpecification('context'))
		command = WCommandContext(base_command, adapter)

		assert(isinstance(command, WCommandContext) is True)
		assert(isinstance(command, WCommandProto) is True)
		assert(command.original_command() == base_command)
		assert(command.adapter() == adapter)

		adapter2 = TestWCommandContext.Adapter(WContextSpecification())
		command2 = WCommandContext(base_command, adapter2)
		assert(command2.match('hello', 'world', 'yeah') is True)
		assert(command.match('hello', 'world', 'yeah') is False)
		request_context = WCommandContextRequest('context', 'hello')
		assert(command.match_context('world', request_context=request_context) is True)

		assert(command2.exec('hello', 'world').output == 'OK')
		assert(command.exec_context('world', request_context=request_context).output == 'OK')
		pytest.raises(RuntimeError, command.exec, 'hello', 'world')


class TestWCommandContextResult:

	def test(self):
		cr = WCommandContextResult('hello', 'world', output='output', error=1)
		assert(isinstance(cr, WCommandContextResult) is True)
		assert(isinstance(cr, WCommandResult) is True)
		assert(cr.context == ('hello', 'world'))
		assert(cr.output == 'output')
		assert(cr.error == 1)


class TestWCommandContextSelector:

	class Command(WCommand):

		def _exec(self, *command_tokens):
			return WCommandResult('simple OK')

	def test(self):
		selector = WCommandContextSelector()
		assert(isinstance(selector, WCommandContextSelector) is True)
		assert(isinstance(selector, WCommandPrioritizedSelector) is True)

		base_command = TestWCommandContext.Command('hello', 'world')
		adapter = TestWCommandContext.Adapter(WContextSpecification('context'))
		command = WCommandContext(base_command, adapter)

		simply_command = TestWCommandContextSelector.Command('create', 'world')

		selector.add(command)
		selector.add(simply_command)

		assert(selector.select('create', 'world') == simply_command)
		assert(selector.select('world', request_context=WCommandContextRequest('context', 'hello')) == command)


class TestWCommandContextSet:

	def test(self):
		selector = WCommandContextSelector()
		command_set = WCommandContextSet(selector)
		assert(command_set.commands() == selector)

		base_command = TestWCommandContext.Command('hello', 'world')
		adapter = TestWCommandContext.Adapter(WContextSpecification('context'))
		command = WCommandContext(base_command, adapter)
		simply_command = TestWCommandContextSelector.Command('create', 'world')

		command_set = WCommandContextSet()
		command_set.commands().add(command)
		command_set.commands().add(simply_command)

		assert(command_set.exec_context('create world').output == 'simple OK')
		result = command_set.exec_context('world', request_context=WCommandContextRequest('context', 'hello'))
		assert(result.output == 'OK')

		pytest.raises(WCommandSet.NoCommandFound, command_set.exec_context, 'foo')
