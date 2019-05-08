# -*- coding: utf-8 -*-
# wasp_general/types/tree.py
#
# Copyright (C) 2019 the wasp-general authors and contributors
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

from wasp_general.verify import verify_type


class WUnbalancedTreeNode:
	""" Simple unbalanced tree implementation. If this class is used widely, then consider to use external libraries
	like 'networkx'
	"""

	@verify_type('strict', node_id=str)
	def __init__(self, node_id, parent_node=None, node_content=None):
		""" Create new tree node

		:param node_id: id that must be unique within a single tree
		:type node_id: str

		:param parent_node: parent node
		:type parent_node: WUnbalancedTreeNode | None

		:param node_content: any node content
		"""
		self.__node_id = node_id
		self.__parent_node = None
		self.__node_content = node_content
		self.__children = {}

		self._path_cache = {}

		self.set_parent(parent_node)

	def node_id(self):
		""" Return node id

		:rtype: str
		"""
		return self.__node_id

	def node_content(self):
		""" Return node content
		"""
		return self.__node_content

	def set_node_content(self, node_content):
		""" Set content for this node

		:param node_content: value to set

		:rtype: None
		"""
		self.__node_content = node_content

	def parent_node(self):
		""" Return parent node

		:rtype: WUnbalancedTreeNode
		"""
		return self.__parent_node

	def _add_child(self, child_node):
		""" Add new direct child

		:param child_node: child to add
		:type child_node: WUnbalancedTreeNode

		:rtype: None
		"""
		if not isinstance(child_node, WUnbalancedTreeNode):
			raise TypeError('"child_node" type is invalid it must be WUnbalancedTreeNode class')

		tree_nodes = set(self._path_cache.keys())
		tree_nodes.add(self.__node_id)

		child_tree_nodes = set(child_node._path_cache.keys())
		child_node_id = child_node.node_id()
		child_tree_nodes.add(child_node_id)

		common_nodes = tree_nodes.intersection(child_tree_nodes)

		if common_nodes:
			raise ValueError(
				'Unable to merge node because parent and child trees have common nodes: %s' %
				', '.join(common_nodes)
			)

		self.__children[child_node_id] = child_node

		def propagate_cache(parent, child):
			"""
			:type parent: WUnbalancedTreeNode
			:type child: WUnbalancedTreeNode
			"""
			propagate_id = child.node_id()
			parent._path_cache[child_node_id] = propagate_id
			parent._path_cache.update({x: propagate_id for x in child_node._path_cache})
			return parent, parent.parent_node()

		previous_node, next_node = propagate_cache(self, child_node)
		while next_node is not None:
			previous_node, next_node = propagate_cache(next_node, previous_node)

	@verify_type('strict', child_node_id=str)
	def _remove_child(self, child_node_id):
		""" Remove direct child

		:param child_node_id: id of a child to remove
		:type child_node_id: str

		:rtype: None
		"""
		self._path_cache = {x: y for x, y in self._path_cache.items() if y != child_node_id}
		self.__children.pop(child_node_id)

	def set_parent(self, parent_node=None):
		""" 'Detach' from a current parent and add a new one (if specified)

		:param parent_node: new parent node. If it is not specified then parent will not be set
		:type parent_node: WUnbalancedTreeNode | None

		:rtype: None
		"""

		if parent_node is not None and not isinstance(parent_node, WUnbalancedTreeNode):
			raise TypeError('"parent_node" type is invalid it must be WUnbalancedTreeNode class')

		if self.__parent_node:
			self.__parent_node._remove_child(self.node_id())

		self.__parent_node = parent_node
		if self.__parent_node:
			self.__parent_node._add_child(self)

	@verify_type('strict', node_id=str)
	def node(self, node_id):
		""" Return node by its id. It may be this node, direct children or grand-children

		:param node_id: id of a node to retrieve
		:type node_id: str

		:rtype: WUnbalancedTreeNode
		"""
		if node_id == self.node_id():
			return self
		if node_id in self._path_cache:
			return self.__children[self._path_cache[node_id]].node(node_id)

		raise KeyError('Unable to find "%s" node' % node_id)

	@verify_type('strict', node_id=str)
	def has_node(self, node_id):
		""" Check whether this or children nodes have the specified node

		:param node_id: node to check
		:type node_id: str

		:rtype: bool
		"""
		return node_id == self.node_id() or node_id in self._path_cache

	def to_parent(self):
		""" Return generator that will iterate over all the parent node up to the root node. The first element is this
		node

		:rtype: generator
		"""
		node = self
		yield node
		while node.parent_node() is not None:
			node = node.parent_node()
			yield node

	@verify_type('strict', node_id=str)
	def to_node(self, node_id):
		""" Return generator that will iterate from this node to the specified child node. The first element is this
		node

		:param node_id: child node that is should be iterated to
		:type node_id: str

		:rtype: generator
		"""

		def node_iter(node):
			"""
			:type node: WUnbalancedTreeNode
			"""
			if node.node_id() == node_id:
				return

			child_id = node._path_cache[node_id]
			child_node = node.node(child_id)
			return child_node

		if not self.has_node(node_id):
			raise KeyError('Unable to find the specified node - "%s"' % node_id)

		yield self
		next_node = node_iter(self)
		while next_node is not None:
			yield next_node
			next_node = node_iter(next_node)
