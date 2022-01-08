# -*- coding: utf-8 -*-
# wasp_general/api/onion.py
#
# Copyright (C) 2017, 2021, 2022 the wasp-general authors and contributors
# <see AUTHORS file>
#
# This file is part of wasp-general.
#
# wasp-general is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wasp-general is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wasp-general.  If not, see <http://www.gnu.org/licenses/>.

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from inspect import isawaitable
import typing

from wasp_general.verify import verify_type, verify_value


class AOnionSessionProto(metaclass=ABCMeta):
	""" Class represent a single processing session. Inside an onion, this class process a single message.
	"""

	@abstractmethod
	async def process(self, data):
		""" Process data and generate response

		:param data: data that is passed to the first function as is
		:type data: any

		:return: Return the last function result
		:rtype: any
		"""
		raise NotImplementedError('This method is abstract')


class AOnionSessionFlowProto(metaclass=ABCMeta):
	""" This class is used in the following class :class:`.WOnionSessionProto` to determine functions execution order.
	"""

	@abstractmethod
	def next(self, data):
		""" Return a pair (tuple) of a function to call (callable object) that should process the specified data and
		the next session flow (:class`.WOnionSessionFlowProto` class) that will define functions that will be next

		If a function is None then there is nothing to do now (but the next session flow should be checked)
		If a session flow is None then processing is complete

		:param data: previous function result
		:type data: any

		:rtype: (callable | None, WOnionSessionFlowProto | None)
		"""
		raise NotImplementedError('This method is abstract')


class WOnionSession(AOnionSessionProto):
	""" :class:`.WOnionSessionProto` class implementation. This class executes functions in order they described
	in the :class:`.WOnionSessionFlowProto` class
	"""

	@verify_type('strict', session_flow=AOnionSessionFlowProto)
	def __init__(self, session_flow):
		""" Construct new session

		:param session_flow: defines function execution order
		:type session_flow: WOnionSessionFlowProto
		"""
		self.__session_flow = session_flow

	async def process(self, data):
		""" :meth:`.WOnionSessionProto.process` method implementation.
		"""

		next_flow = self.__session_flow
		while next_flow is not None:
			layer_fn, next_flow = next_flow.next(data)
			if layer_fn is not None:
				data = layer_fn(data)
				if isawaitable(data):
					data = await data

		return data


class WOnionSequenceFlow(AOnionSessionFlowProto):
	""" Simple :class:`.WOnionSessionFlowProto` implementation. This class "executes" functions one after one
	"""

	@verify_value('strict', fn=lambda x: callable(x))
	def __init__(self, *fn):
		""" Construct new session flow

		:param info: functions to be called
		:type info: callable
		"""
		AOnionSessionFlowProto.__init__(self)
		self.__fn = fn

	def next(self, data):
		""" :meth:`.WOnionSessionFlowProto.iterator` implementation
		"""
		if not len(self.__fn):
			raise IndexError('There are no functions anymore')

		next_flow = WOnionSequenceFlow(*(self.__fn[1:])) if len(self.__fn) > 1 else None
		info = self.__fn[0]
		return info, next_flow


class WOnionConditionalSequenceFlow(AOnionSessionFlowProto):
	""" Simple :class:`.WOnionSessionFlowProto` implementation. This class choose a next session flow by
	conditional checking
	"""

	@dataclass
	class Comparator:
		compare_fn: typing.Callable  # function that returns True/False on "(data)" arguments
		on_true: AOnionSessionFlowProto = None  # session that should be followed on True result of compare_fn
		on_false: AOnionSessionFlowProto = None  # session that should be followed on False result of compare_fn

	@verify_type('strict', comparators=Comparator, default_flow=(AOnionSessionFlowProto, None))
	def __init__(self, *comparators, default_flow=None):
		""" Construct new session flow

		:param comparators: checkers
		:type comparators: WOnionConditionalSequenceFlow.Comparator

		:param default_flow: default flow if no other flows were suitable
		:type default_flow: AOnionSessionFlowProto | None
		"""
		AOnionSessionFlowProto.__init__(self)
		self.__comparators = comparators
		self.__default_flow = default_flow

	def next(self, data):
		""" :meth:`.WOnionSessionFlowProto.iterator` implementation
		"""

		for comp in self.__comparators:
			result = comp.on_true if comp.compare_fn(data) else comp.on_false
			if result:
				return None, result

		if self.__default_flow is None:
			raise IndexError('There is no default flow')
		return None, self.__default_flow
