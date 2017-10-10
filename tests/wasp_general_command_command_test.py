# -*- coding: utf-8 -*-

import pytest

from wasp_general.command.command import WCommandResult, WCommandProto, WCommand, WCommandSelector
from wasp_general.command.command import WCommandPrioritizedSelector, WCommandSet, WReduceCommand


def test_abstract():
	pytest.raises(TypeError, WCommandResult.VarSerializationHelper)
	pytest.raises(NotImplementedError, WCommandResult.VarSerializationHelper.serialize, None, None)
	pytest.raises(NotImplementedError, WCommandResult.VarSerializationHelper.deserialize, None, None)

	pytest.raises(TypeError, WCommandProto)
	pytest.raises(NotImplementedError, WCommandProto.match, None)
	pytest.raises(NotImplementedError, WCommandProto.exec, None)

	pytest.raises(TypeError, WCommand)
	pytest.raises(NotImplementedError, WCommand._exec, None)


class TestWCommandResult:

	def test(self):
		assert(WCommandResult('foo').output == 'foo')
		assert(WCommandResult('foo', 1).error == 1)

		command_result = WCommandResult(var1=1, var2='q')
		assert(command_result.serialize_var() == {'var1': 1, 'var2': 'q'})

		class A:
			def __eq__(self, other):
				return isinstance(other, A)

		class AHelper(WCommandResult.VarSerializationHelper):

			def serialize(self, var_value):
				return 'A'

			def deserialize(self, serialized_value):
				return A()

		command_result = WCommandResult(var1=1, var2='q', var3=A())
		assert (command_result.serialize_var(var3=AHelper()) == {'var1': 1, 'var2': 'q', 'var3': 'A'})
		pytest.raises(TypeError, command_result.serialize_var, var3=1)

		result_env = WCommandResult.deserialize_env({'var1': 1, 'var2': 'q'})
		assert(result_env == {'var1': 1, 'var2': 'q'})

		result_env = WCommandResult.deserialize_env({'var1': 1, 'var2': 'q', 'var3': 'B'}, var3=AHelper())
		assert(result_env == {'var1': 1, 'var2': 'q', 'var3': A()})
		pytest.raises(TypeError, WCommandResult.deserialize_env, {'var1': 1}, var1='')


class TestWCommandProto:

	def test(self):
		split_result = WCommandProto.split_command('call "function 1" with\t0.1 "test words"')
		assert(split_result == ['call', 'function 1', 'with', '0.1', 'test words'])
		join_result = WCommandProto.join_tokens(*split_result)
		assert(join_result == "call 'function 1' with 0.1 'test words'")


class TestWCommand:

	class Command(WCommand):

		def _exec(self, *command_tokens):
			return WCommandResult('OK')

	def test(self):
		command = TestWCommand.Command('create', 'world')
		assert(isinstance(command, WCommand) is True)
		assert(isinstance(command, WCommandProto) is True)

		assert(command.match('create', 'world', 'new world') is True)
		assert(command.match('update', 'world') is False)
		assert(command.match('create') is False)
		assert(TestWCommand.Command('create').match('create') is True)

		result = command.exec('create', 'world', '2.0')
		assert(isinstance(result, WCommandResult) is True)
		assert(result.output == 'OK')

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
		assert(isinstance(result, WCommandResult) is True)
		assert(result.output == 'OK')

		pytest.raises(WCommandSet.NoCommandFound, command_set.exec, 'hello world')


class TestWReduceCommand:

	def test(self):
		command_selector = WCommandSelector()
		pytest.raises(RuntimeError, WReduceCommand, command_selector)
		reduce_command = WReduceCommand(command_selector, 'section1')

		assert(reduce_command.match('section1', 'hello') is False)
		assert(reduce_command.match('section1', 'test') is False)
		assert(reduce_command.match('section2', 'hello') is False)
		pytest.raises(RuntimeError, reduce_command.exec, 'section1', 'hello')
		pytest.raises(RuntimeError, reduce_command.exec, 'section1', 'test')
		pytest.raises(RuntimeError, reduce_command.exec, 'section2', 'hello')

		command_selector.add(TestWCommand.Command('hello'))
		assert(reduce_command.match('section1', 'hello') is True)
		assert(reduce_command.match('section1', 'test') is False)
		assert(reduce_command.match('section2', 'hello') is False)

		result = reduce_command.exec('section1', 'hello')
		assert(isinstance(result, WCommandResult) is True)
		assert(result.output == 'OK')
