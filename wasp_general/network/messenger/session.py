# -*- coding: utf-8 -*-
# wasp_general/network/messenger/session.py
#
# Copyright (C) 2017 the wasp-general authors and contributors
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

# noinspection PyUnresolvedReferences
from wasp_general.version import __author__, __version__, __credits__, __license__, __copyright__, __email__
# noinspection PyUnresolvedReferences
from wasp_general.version import __status__

import re
from abc import ABCMeta, abstractmethod

from wasp_general.verify import verify_type
from wasp_general.network.messenger.proto import WMessengerEnvelopeProto, WMessengerOnionSessionFlowProto
from wasp_general.network.messenger.proto import WMessengerOnionSessionProto, WMessengerOnionProto
from wasp_general.network.messenger.envelope import WMessengerTextEnvelope, WMessengerBytesEnvelope


class WMessengerOnionSessionFlow(WMessengerOnionSessionFlowProto):
	""" Simple :class:`.WMessengerOnionSessionFlowProto` implementation. This class returns iterator, that was
	given in constructor
	"""

	@verify_type(iterator=WMessengerOnionSessionFlowProto.Iterator)
	def __init__(self, iterator):
		""" Construct new session flow

		:param iterator: flow iterator
		"""
		WMessengerOnionSessionFlowProto.__init__(self)
		self.__iterator = iterator

	@verify_type('paranoid', envelope=WMessengerEnvelopeProto)
	def iterator(self, envelope):
		""" :meth:`.WMessengerOnionSessionFlowProto.iterator` implementation
		"""
		return self.__iterator

	@classmethod
	@verify_type(info=WMessengerOnionSessionFlowProto.IteratorInfo)
	def sequence(cls, *info):
		""" Useful method to generate iterator. It is generated by chaining the given info. If no info is
		specified, then None is returned

		:param info: iterator info sequence
		:return: WMessengerOnionSessionFlowProto.Iterator or None
		"""
		if len(info) == 0:
			return

		info = list(info)
		info.reverse()

		result = WMessengerOnionSessionFlowProto.Iterator(
			info[0].layer_name(), **info[0].layer_args()
		)

		for i in range(1, len(info)):
			result = WMessengerOnionSessionFlowProto.Iterator(
				info[i].layer_name(), next_iterator=result, **info[i].layer_args()
			)

		return result

	@staticmethod
	@verify_type('paranoid', info=WMessengerOnionSessionFlowProto.IteratorInfo)
	def sequence_flow(*info):
		""" Same method as :meth:`.WMessengerOnionSessionFlow.sequence`, but as a result
		:class:`.WMessengerOnionSessionFlow` object created (if no info is specified, then None is returned)

		:param info: iterator info sequence
		:return: WMessengerOnionSessionFlow or None
		"""
		if len(info) > 0:
			return WMessengerOnionSessionFlow(WMessengerOnionSessionFlow.sequence(*info))


class WMessengerOnionSessionFlowSequence(WMessengerOnionSessionFlowProto):
	""" Session flow that "iterates" over flows, that was given in constructor. So this class returns iterator, that
	smoothly iterates a iterator from the first given flow, then from the second one, and so on. If no flows are
	specified in a constructor, then :meth:`.WMessengerOnionSessionFlowSequence.iterator` method returns None.
	In :meth:`.WMessengerOnionSessionFlowSequence.iterator` method no iterator is returned if all of the given
	flows doesn't return iterator for the specified envelope.
	"""

	class FlowSequenceIterator(WMessengerOnionSessionFlowProto.Iterator):
		""" Iterator that has its own information and sequence of flows to iterate. During iteration (in
		:meth:`.WMessengerOnionSessionFlowSequence.FlowSequenceIterator.next` method) this class doesn't return
		the following iterator, but returns itself instead. By each
		:meth:`.WMessengerOnionSessionFlowSequence.FlowSequenceIterator.next` call this object saves a "real"
		iterator and saves its state (layer name and arguments), so when layer information is requested,
		information from the "real" iterator is returned
		"""
		@verify_type(info=WMessengerOnionSessionFlowProto.IteratorInfo, flows=WMessengerOnionSessionFlowProto)
		def __init__(self, info, *flows):
			""" Construct new iterator

			:param info: self information
			:param flows: flows to iterate sequentially
			"""
			WMessengerOnionSessionFlowProto.Iterator.__init__(self, info.layer_name(), **info.layer_args())

			self.__flows = list(flows)
			self.__current_flow = None
			self.__iterator = None

		@verify_type('paranoid', envelope=WMessengerEnvelopeProto)
		def __next_flow(self, envelope):
			""" Checks current state and finds next suitable "real" iterator

			:param envelope: original envelope from \
			:meth:`.WMessengerOnionSessionFlowSequence.FlowSequenceIterator.next` method
			:return: None
			"""
			self.__current_flow = (self.__current_flow + 1) if self.__current_flow is not None else 0
			if self.__current_flow < len(self.__flows):
				self.__iterator = self.__flows[self.__current_flow].iterator(envelope)
				if self.__iterator is None:
					self.__next_flow(envelope)

		@verify_type('paranoid', envelope=WMessengerEnvelopeProto)
		def next(self, envelope):
			""" :meth:`.WMessengerOnionSessionFlowProto.Iterator.next` implementation
			"""
			if self.__iterator is not None:
				self.__iterator = self.__iterator.next(envelope)

			if self.__iterator is None:
				self.__next_flow(envelope)

			if self.__iterator is not None:
				return self

		def layer_name(self):
			""" :meth:`.WMessengerOnionSessionFlowProto.IteratorInfo.layer_name` implementation
			"""
			if self.__current_flow is None:
				return WMessengerOnionSessionFlowProto.Iterator.layer_name(self)
			return self.__iterator.layer_name()

		def layer_args(self):
			""" :meth:`.WMessengerOnionSessionFlowProto.IteratorInfo.layer_args` implementation
			"""
			if self.__current_flow is None:
				return WMessengerOnionSessionFlowProto.Iterator.layer_args(self)
			return self.__iterator.layer_args()

	@verify_type(flows=WMessengerOnionSessionFlowProto)
	def __init__(self, *flows):
		""" Construct new session flow

		:param flows: flows to iterate
		"""
		WMessengerOnionSessionFlowProto.__init__(self)
		self.__flows = flows

	@verify_type('paranoid', envelope=WMessengerEnvelopeProto)
	def iterator(self, envelope):
		""" :meth:`WMessengerOnionSessionFlowProto.iterator` implementation
		"""
		iterator = WMessengerOnionSessionFlowSequence.FlowSequenceIterator(
			WMessengerOnionSessionFlowProto.IteratorInfo(''), *self.__flows
		)
		return iterator.next(envelope)


class WMessengerOnionSessionFlexFlow(WMessengerOnionSessionFlowProto):
	""" Flexible flow that choose one of the given flows depends on the given envelope. Flows are passed as pairs
	(pair of flow and object that checks the envelope) and as default flow (flow that is selected, if envelope
	wasn't "matched" to any flow)
	"""

	class MessageComparator(metaclass=ABCMeta):
		""" Abstract class that checks envelope
		"""

		@abstractmethod
		@verify_type(envelope=WMessengerEnvelopeProto)
		def match(self, envelope):
			""" Check if envelope is suitable

			:param envelope: envelope to check
			:return: bool
			"""
			raise NotImplementedError('This method is abstract')

	class ReComparator(MessageComparator):
		""" Simple :class:`.WMessengerOnionSessionFlexFlow.MessageComparator` implementation, that
		checks if envelope (text or binary) matches the given regular expression
		"""

		@verify_type(pattern=(str, bytes))
		def __init__(self, pattern):
			""" Construct new comparator

			:param pattern: regular expression to check
			"""
			WMessengerOnionSessionFlexFlow.MessageComparator.__init__(self)
			self.__re = re.compile(pattern)

		@verify_type(envelope=(WMessengerTextEnvelope, WMessengerBytesEnvelope))
		def match(self, envelope):
			""" :meth:`.WMessengerOnionSessionFlexFlow.MessageComparator.match` implementation
			"""
			return self.__re.match(envelope.message()) is not None

	class FlowComparatorPair:
		""" Pair that links comparator and flow
		"""

		@verify_type(flow=WMessengerOnionSessionFlowProto)
		def __init__(self, comparator, flow):
			""" Construct new pair

			:param comparator: comparator, that checks envelope
			:param flow: flow to use
			"""
			if isinstance(comparator, WMessengerOnionSessionFlexFlow.MessageComparator) is False:
				raise TypeError('Invalid type for comparator argument')

			self.__comparator = comparator
			self.__flow = flow

		def comparator(self):
			""" Return comparator

			:return: WMessengerOnionSessionFlexFlow.MessageComparator
			"""
			return self.__comparator

		def flow(self):
			""" Return flow

			:return: WMessengerOnionSessionFlowProto
			"""
			return self.__flow

	@verify_type(default_flow=(WMessengerOnionSessionFlowProto, None))
	def __init__(self, *flow_comparator_pairs, default_flow=None):
		""" Construct new session flow

		:param flow_comparator_pairs: flows to check
		:param default_flow: default flow (if no flow is matched)
		"""
		WMessengerOnionSessionFlowProto.__init__(self)
		self.__pairs = []
		for pair in flow_comparator_pairs:
			if isinstance(pair, WMessengerOnionSessionFlexFlow.FlowComparatorPair) is False:
				raise TypeError('Invalid type for flow-comparator pair argument')
			self.__pairs.append(pair)
		self.__default_flow = default_flow

	@verify_type('paranoid', envelope=WMessengerEnvelopeProto)
	def iterator(self, envelope):
		""" :meth:`WMessengerOnionSessionFlowProto.iterator` implementation
		"""
		for pair in self.__pairs:
			if pair.comparator().match(envelope) is True:
				return pair.flow().iterator(envelope)

		if self.__default_flow is not None:
			return self.__default_flow.iterator(envelope)


class WMessengerOnionSession(WMessengerOnionSessionProto):
	""" :class:`.WMessengerOnionSessionProto` class implementation. This class executes layers from onion in order
	they described in :class:`.WMessengerOnionSessionFlow` class
	"""

	@verify_type(onion=WMessengerOnionProto, session_flow=WMessengerOnionSessionFlowProto)
	def __init__(self, onion, session_flow):
		""" Construct new session.

		:param onion: related onion
		:param session_flow: defines layers order to be executed
		"""
		self.__onion = onion
		self.__session_flow = session_flow

	def onion(self):
		""" :meth:`.WMessengerOnionSessionProto.onion` method implementation.
		"""
		return self.__onion

	def session_flow(self):
		""" Return related :class:`.WMessengerOnionSessionFlow` object
		:return: WMessengerOnionSessionFlow
		"""
		return self.__session_flow

	@verify_type('paranoid', envelope=WMessengerEnvelopeProto)
	def process(self, envelope):
		""" :meth:`.WMessengerOnionSessionProto.process` method implementation.
		"""

		def process_single_layer(iter_envelope, iter_obj):
			layer = self.onion().layer(iter_obj.layer_name())
			layer_args = iter_obj.layer_args()
			return layer.process(iter_envelope, self, **layer_args)

		iterator = self.session_flow().iterator(envelope)
		if iterator is not None:
			while iterator is not None:
				envelope = process_single_layer(envelope, iterator)
				iterator = iterator.next(envelope)
		return envelope
