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
		self._path_cache[child_node_id] = child_node_id
		self._path_cache.update({x: child_node_id for x in child_node._path_cache})

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
