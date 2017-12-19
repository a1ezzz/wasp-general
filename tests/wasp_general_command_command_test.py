# -*- coding: utf-8 -*-

import pytest

from wasp_general.command.command import WCommandProto, WCommand, WCommandSelector, WCommandPrioritizedSelector
from wasp_general.command.command import WCommandSet, WCommandAlias, WReduceCommand
from wasp_general.command.proto import WCommandResultProto
from wasp_general.command.result import WPlainCommandResult


def test_abstract():
	pytest.raises(TypeError, WCommandProto)
	pytest.raises(NotImplementedError, WCommandProto.match, None)
	pytest.raises(NotImplementedError, WCommandProto.exec, None)

	pytest.raises(TypeError, WCommand)
	pytest.raises(NotImplementedError, WCommand._exec, None)

	pytest.raises(TypeError, WCommandAlias)
	pytest.raises(NotImplementedError, WCommandAlias.mutate_command_tokens, None)


class TestWCommandProto:

	def test(self):
		split_result = WCommandProto.split_command('call "function 1" with\t0.1 "test words"')
		assert(split_result == ['call', 'function 1', 'with', '0.1', 'test words'])
		join_result = WCommandProto.join_tokens(*split_result)
		assert(join_result == "call 'function 1' with 0.1 'test words'")


class TestWCommand:

	class Command(WCommand):

		def _exec(self, *command_tokens):
			return WPlainCommandResult('OK')

	def test(self):
		command = TestWCommand.Command('create', 'world')
		assert(isinstance(command, WCommand) is True)
		assert(isinstance(command, WCommandProto) is True)

		assert(command.match('create', 'world', 'new world') is True)
		assert(command.match('update', 'world') is False)
		assert(command.match('create') is False)
		assert(TestWCommand.Command('create').match('create') is True)

		result = command.exec('create', 'world', '2.0')
		assert(isinstance(result, WCommandResultProto) is True)
		assert(str(result) == 'OK')

		pytest.raises(RuntimeError, command.exec, 'update')


class TestWCommandSelector:

	def test(self):
		create_cmd = TestWCommand.Command('create')
		create_world_cmd = TestWCommand.Command('create', 'world')

		command_selector = WCommandSelector()
		assert(len(command_selector) == 0)
		command_selector.add(create_cmd)
		assert(len(command_selector) == 1)
		command_selector.add(create_world_cmd)
		assert(len(command_selector) == 2)
		assert(command_selector.select('create') == create_cmd)
		assert(command_selector.select('create', 'world') == create_cmd)

		command_selector = WCommandSelector()
		command_selector.add(create_world_cmd)
		command_selector.add(create_cmd)
		assert(command_selector.select('create') == create_cmd)
		assert(command_selector.select('create', 'world') == create_world_cmd)

		assert(command_selector.select('update') is None)


class TestWCommandPrioritizedSelector:

	def test(self):
		create_cmd = TestWCommand.Command('create')
		create_world_cmd = TestWCommand.Command('create', 'world')

		command_selector = WCommandPrioritizedSelector()
		assert(len(command_selector) == 0)
		assert(isinstance(command_selector, WCommandPrioritizedSelector) is True)
		assert(isinstance(command_selector, WCommandSelector) is True)

		command_selector.add(create_cmd)
		assert(len(command_selector) == 1)
		command_selector.add(create_world_cmd)
		assert(len(command_selector) == 2)
		assert(command_selector.select('create') == create_cmd)
		assert(command_selector.select('create', 'world') == create_cmd)

		command_selector = WCommandPrioritizedSelector()
		command_selector.add(create_cmd)
		command_selector.add_prioritized(create_world_cmd, -1)
		assert(command_selector.select('create') == create_cmd)
		assert(command_selector.select('create', 'world') == create_world_cmd)


class TestWCommandSet:

	class Command(WCommand):

		def _exec(self, *command_tokens, **command_env):
			return WPlainCommandResult('context set', sec_var='1')

	def test(self):
		command_set = WCommandSet()
		assert(isinstance(command_set.commands(), WCommandSelector) is True)
		assert(isinstance(command_set.commands(), WCommandPrioritizedSelector) is False)

		create_cmd = TestWCommand.Command('create')
		create_world_cmd = TestWCommand.Command('create', 'world')
		command_selector = WCommandPrioritizedSelector()
		command_selector.add(create_cmd)
		command_selector.add_prioritized(create_world_cmd, -1)

		command_set = WCommandSet(command_selector)
		assert(command_set.commands() == command_selector)

		result = command_set.exec('create world 2.0')
		assert(isinstance(result, WCommandResultProto) is True)
		assert(str(result) == 'OK')

		pytest.raises(WCommandSet.NoCommandFound, command_set.exec, 'hello world')

		command_set = WCommandSet()
		assert(command_set.tracked_vars() == tuple())
		assert(command_set.has_var('sec_var') is False)

		command_set = WCommandSet(tracked_vars=('sec_var', ))
		assert(command_set.tracked_vars() == ('sec_var', ))
		assert(command_set.has_var('sec_var') is False)

		set_command = TestWCommandSet.Command('set')
		command_set.commands().add(set_command)
		assert(command_set.has_var('sec_var') is False)

		command_set.exec('set')
		assert(command_set.has_var('sec_var') is True)
		assert(command_set.var_value('sec_var') == '1')


class TestWCommandAlias:

	class Command(WCommandAlias):

		def mutate_command_tokens(self, *command_tokens):
			result = ['foo']
			result.extend(command_tokens)
			result.append('bar')
			return result

	def test(self):
		command_selector = WCommandSelector()
		cmd_alias = TestWCommandAlias.Command(command_selector)
		assert(isinstance(cmd_alias, TestWCommandAlias.Command) is True)
		assert(isinstance(cmd_alias, WCommandAlias) is True)
		assert(isinstance(cmd_alias, WCommandProto) is True)
		assert(cmd_alias.selector() == command_selector)
		assert(cmd_alias.match('test') is False)

		command_selector.add(TestWCommand.Command('test'))
		assert(cmd_alias.match('test') is False)

		command_selector.add(TestWCommand.Command('foo', 'test', 'bar'))
		assert(cmd_alias.match('test') is True)

		result = cmd_alias.exec('test')
		assert(isinstance(result, WCommandResultProto) is True)
		assert(str(result) == 'OK')

		def mutation_error_fn(*command_tokens):
			return

		cmd_alias.mutate_command_tokens = mutation_error_fn
		assert (cmd_alias.match('test') is False)
		pytest.raises(RuntimeError, cmd_alias.exec, 'test')


class TestWReduceCommand:

	def test(self):
		command_selector = WCommandSelector()
		pytest.raises(RuntimeError, WReduceCommand, command_selector)

		reduce_command = WReduceCommand(command_selector, 'section1', 'section2')
		assert(isinstance(reduce_command, WReduceCommand) is True)
		assert(isinstance(reduce_command, WCommandAlias) is True)
		assert(reduce_command.reduce_tokens() == ('section1', 'section2'))

		assert(reduce_command.mutate_command_tokens('hello') is None)
		assert(reduce_command.mutate_command_tokens('section1', 'hello', 'world') == ('hello', 'world'))
		assert(reduce_command.mutate_command_tokens('section2', 'hello', 'world') == ('hello', 'world'))
