
import pytest

from wasp_general.types.tree import WUnbalancedTreeNode


class TestWUnbalancedTreeNode:

	def test(self):
		node_a = WUnbalancedTreeNode('a')
		assert(node_a.node_id() == 'a')
		assert(node_a.parent_node() is None)
		assert(node_a.node_content() is None)
		node_a.set_node_content(1)
		assert(node_a.node_content() == 1)
		assert(node_a.node('a') == node_a)
		pytest.raises(KeyError, node_a.node, 'b')

		node_b = WUnbalancedTreeNode('b')
		assert(node_b.parent_node() is None)
		assert(node_b.node('b') == node_b)
		pytest.raises(KeyError, node_b.node, 'a')
		node_a.set_parent(node_b)
		assert(node_b.node('a') == node_a)
		pytest.raises(KeyError, node_a.node, 'b')

		node_a.set_parent(None)
		assert(node_b.node('b') == node_b)
		assert(node_a.node('a') == node_a)
		pytest.raises(KeyError, node_b.node, 'a')
		pytest.raises(KeyError, node_a.node, 'b')

		node_c1 = WUnbalancedTreeNode('c', node_a)
		assert(node_a.node('a') == node_a)
		assert(node_a.node('c') == node_c1)

		node_c2 = WUnbalancedTreeNode('c', node_b)
		assert(node_b.node('b') == node_b)
		assert(node_b.node('c') == node_c2)

		pytest.raises(ValueError, node_b.set_parent, node_a)

		pytest.raises(TypeError, node_a.set_parent, 1)
		pytest.raises(TypeError, node_a._add_child, 1)
