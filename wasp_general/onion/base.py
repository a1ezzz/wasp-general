# -*- coding: utf-8 -*-
# wasp_general/onion/base.py
#
# Copyright (C) 2017-2019 the wasp-general authors and contributors
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
import re
import asyncio

from wasp_general.onion.proto import WEnvelopeProto, WOnionSessionFlowProto, WOnionProto, WOnionLayerProto
from wasp_general.verify import verify_type, verify_value, verify_subclass


class WEnvelope(WEnvelopeProto):
	""" Simple :class:`.WEnvelopeProto` class implementation
	"""

	@verify_type('strict', layer_name=(str, None), previous_meta=(WEnvelopeProto, None))
	def __init__(self, data, layer_name=None, layer_meta=None, previous_meta=None):
		""" Construct new envelope

		:param data: data to process or a final result
		:type data: any

		:param layer_name: name of a layer that has been produced this envelope (None if this envelope was not
		returned by a layer)
		:type layer_name: str | None

		:param layer_meta: meta information about processing. If the "layer_name" argument is not set then this
		value is omitted
		:type layer_meta: any

		:param previous_meta: envelope from which meta should be copied (usually it is a "previous" envelope
		with information about layers has been processed before)
		:type previous_meta: WEnvelopeProto | None
		"""
		self.__data = data

		if previous_meta is None:
			self.__meta = tuple()
		elif isinstance(previous_meta, WEnvelope) is True:
			self.__meta = previous_meta._copy_meta()
		else:
			self.__meta = tuple(previous_meta.layers())

		if layer_name is not None:
			self.__meta = self.__meta + ((layer_name, layer_meta), )

	def data(self):
		""" Return envelope's data

		:rtype: any
		"""
		return self.__data

	@verify_type('strict', layer_name=(str, None))
	@verify_value('strict', layer_name=lambda x: x is None or len(x) > 0)
	def layers(self, layer_name=None):
		""" :meth:`.WEnvelopeProto.layers` method implementation
		:type layer_name: str | None
		:rtype: generator
		"""
		iterable = self.__meta if layer_name is None else filter(lambda x: x[0] == layer_name, self.__meta)
		for i in iterable:
			yield i

	def _copy_meta(self):
		""" Return a copy of this envelope's meta data

		:rtype: tuple
		"""
		return tuple(self.__meta)


# noinspection PyAbstractClass
class WOnionBaseSessionFlow(WOnionSessionFlowProto):
	""" This class extends the :class:`.WOnionSessionFlowProto` abstract class by defining a single useful method
	"""

	@classmethod
	@verify_type('strict', session_flow=WOnionSessionFlowProto, envelope=WEnvelopeProto)
	async def iterate_inner_flow(cls, session_flow, envelope):
		""" Iterate over a specified session flow and an envelope. This method is helpful for
		the :meth:`.WOnionSessionFlowProto.iterate` method implementation

		:param session_flow:
		:type session_flow: WOnionSessionFlowProto

		:param envelope:
		:type envelope: WEnvelopeProto

		:rtype: async generator
		"""
		loop = asyncio.get_event_loop()
		envelope_future = loop.create_future()
		# noinspection PyTypeChecker
		async for layer_info, inner_envelope_future in session_flow.iterate(envelope):
			yield layer_info, envelope_future
			await envelope_future
			inner_envelope_future.set_result(envelope_future.result())
			envelope_future = loop.create_future()


class WOnionDirectSessionFlow(WOnionBaseSessionFlow):
	""" A simple :class:`.WOnionSessionFlowProto` class implementation that iterates directly over
	a specified layers, which may be set as :class:`.WOnionSessionFlowProto.LayerInfo` objects or as
	:class:`.WOnionSessionFlowProto` objects
	"""

	@verify_type('strict', info=(WOnionSessionFlowProto.LayerInfo, WOnionSessionFlowProto))
	def __init__(self, *info):
		""" Create new session flow

		:param info: layers that this flow should iterate over
		:type info: WOnionSessionFlowProto.LayerInfo | WOnionSessionFlowProt
		"""
		WOnionBaseSessionFlow.__init__(self)
		self.__info = info

	@verify_type('paranoid', envelope=WEnvelopeProto)
	async def iterate(self, envelope):
		""" :meth:`.WOnionSessionFlowProto.iterate` method implementation
		:type envelope: WEnvelopeProto
		:rtype: async generator
		"""
		loop = asyncio.get_event_loop()
		for i in self.__info:
			if isinstance(i, WOnionSessionFlowProto.LayerInfo):
				envelope_future = loop.create_future()
				yield i, envelope_future
				await envelope_future
				envelope = envelope_future.result()
			else:
				async for j in self.iterate_inner_flow(i, envelope):
					yield j


class WOnionConditionalSessionFlow(WOnionBaseSessionFlow):
	""" A conditional flow that choose one of the given flows. An exact flow depends on a given envelope. If there
	are no no suitable flow then a default one may be chosen
	"""

	class FlowSelector(metaclass=ABCMeta):
		""" Abstract class that checks envelope
		"""

		@abstractmethod
		@verify_type('strict', envelope=WEnvelopeProto)
		def flow(self, envelope):
			""" Check if there is a flow for a given envelope. This method returns
			:class:`.WOnionSessionFlowProto` if there is one, None - otherwise

			:param envelope: envelope to check
			:return: WOnionSessionFlowProto | None
			"""
			raise NotImplementedError('This method is abstract')

	class ReComparator(FlowSelector):
		""" Simple :class:`.WOnionConditionalSessionFlow.FlowSelector` implementation, that
		checks if envelope (text or binary) matches the given regular expression
		"""

		@verify_type('strict', pattern=(str, bytes))
		@verify_type('paranoid', next_flow=WOnionSessionFlowProto)
		def __init__(self, pattern, next_flow):
			""" Construct new comparator

			:param pattern: regular expression to check
			:type pattern: str | bytes

			:param next_flow: flow that will be chosen if an envelope matches a given pattern
			:type next_flow: WOnionSessionFlowProto
			"""
			WOnionConditionalSessionFlow.FlowSelector.__init__(self)
			self.__re = re.compile(pattern)
			self.__next_flow = next_flow

		@verify_type('strict', envelope=WEnvelopeProto)
		@verify_value('strict', envelope=lambda x: isinstance(x.data(), (str, bytes)))
		def flow(self, envelope):
			""" :meth:`.WOnionConditionalSessionFlow.FlowSelector.match` implementation
			"""
			if self.__re.match(envelope.data()) is not None:
				return self.__next_flow

	@verify_type('strict', selectors=FlowSelector, default_flow=(WOnionSessionFlowProto, None))
	def __init__(self, *selectors, default_flow=None):
		""" Construct new flow with the next flow selectors and a default flow

		:param selectors: this selectors are used for the next flow searching (the first one that matches
		a given envelope will be used)
		:type selectors: WOnionConditionalSessionFlow.FlowSelector

		:param default_flow: the next flow that will be used if no suitable flow were found in selectors
		:type default_flow: WOnionSessionFlowProto
		"""
		WOnionBaseSessionFlow.__init__(self)
		self.__selectors = selectors
		self.__default_flow = default_flow

	@verify_type('paranoid', envelope=WEnvelopeProto)
	async def iterate(self, envelope):
		""" :meth:`.WOnionSessionFlowProto.iterate` method implementation
		:type envelope: WEnvelopeProto
		:rtype: async generator
		"""
		next_flow = None
		for s in self.__selectors:
			next_flow = s.flow(envelope)
			if next_flow is not None:
				break

		if next_flow is None and self.__default_flow is not None:
			next_flow = self.__default_flow

		if next_flow is not None:
			async for j in self.iterate_inner_flow(next_flow, envelope):
				yield j


class WOnion(WOnionProto):
	""" Simple :class:`.WOnionProto` class implementation that stores layers and is able to process an envelope
	with a session flow
	"""

	@verify_subclass('paranoid', layers=WOnionLayerProto)
	def __init__(self, *layers):
		""" Construct new onion

		:param layers: layers to store
		:type layers: WOnionLayerProto
		"""
		self.__layers = {}
		self.add_layers(*layers)

	def layers_names(self):
		""" :meth:`.WOnionProto.layers_names` method implementation
		:rtype: tuple of str
		"""
		return tuple(self.__layers.keys())

	@verify_type('strict', layer_name=str)
	@verify_value('strict', layer_name=lambda x: len(x) > 0)
	def layer(self, layer_name):
		""" :meth:`.WOnionProto.layer` method implementation
		:type layer_name: str
		:rtype: WOnionLayerProto
		"""
		try:
			return self.__layers[layer_name]
		except KeyError:
			raise ValueError('No suitable layer were found for id: %s' % layer_name)

	@verify_type('strict', session_flow=WOnionSessionFlowProto, envelope=WEnvelopeProto)
	async def process(self, session_flow, envelope):
		""" :meth:`.WOnionProto.process` method implementation
		:type session_flow: WOnionSessionFlowProto
		:type envelope: WEnvelopeProto
		:rtype: WEnvelopeProto
		"""
		# noinspection PyTypeChecker
		async for next_layer, envelope_future in session_flow.iterate(envelope):
			layer_cls = self.layer(next_layer.layer_name())
			layer = layer_cls.layer(*next_layer.layer_args(), **next_layer.layer_kwargs())

			envelope = await layer.process(envelope)
			envelope_future.set_result(envelope)
		return envelope

	@verify_subclass('strict', layers=WOnionLayerProto)
	def add_layers(self, *layers):
		""" Append given layers to this onion

		:param layers: layer to add
		:type layers: WOnionLayerProto

		:return: None
		"""
		for layer in layers:
			if layer.name() in self.__layers.keys():
				raise ValueError('Layer "%s" already exists' % layer.name())
			self.__layers[layer.name()] = layer
