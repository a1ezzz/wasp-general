
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
		assert(node_a.has_node('a') is True)
		pytest.raises(KeyError, node_a.node, 'b')
		assert(node_a.has_node('b') is False)
		assert(node_a.has_children() is False)

		node_b = WUnbalancedTreeNode('b')
		assert(node_b.parent_node() is None)
		assert(node_b.node('b') == node_b)
		assert(node_b.has_node('b') is True)
		pytest.raises(KeyError, node_b.node, 'a')
		assert(node_b.has_node('a') is False)
		node_a.set_parent(node_b)
		assert(node_b.node('a') == node_a)
		assert(node_b.has_node('a') is True)
		pytest.raises(KeyError, node_a.node, 'b')
		assert(node_a.has_node('b') is False)
		assert(node_a.has_children() is False)
		assert(node_b.has_children() is True)

		node_a.set_parent(None)
		assert(node_b.node('b') == node_b)
		assert(node_b.has_node('b') is True)
		assert(node_a.node('a') == node_a)
		assert(node_a.has_node('a') is True)
		pytest.raises(KeyError, node_b.node, 'a')
		assert(node_b.has_node('a') is False)
		pytest.raises(KeyError, node_a.node, 'b')
		assert(node_a.has_node('b') is False)
		assert(node_a.has_children() is False)
		assert(node_b.has_children() is False)

		node_c1 = WUnbalancedTreeNode('c', node_a)
		assert(node_a.node('a') == node_a)
		assert(node_a.has_node('a') is True)
		assert(node_a.node('c') == node_c1)
		assert(node_a.has_node('c') is True)
		assert(node_a.has_children() is True)
		assert(node_b.has_children() is False)
		assert(node_c1.has_children() is False)

		node_c2 = WUnbalancedTreeNode('c', node_b)
		assert(node_b.node('b') == node_b)
		assert(node_b.has_node('b') is True)
		assert(node_b.node('c') == node_c2)
		assert(node_b.has_node('c') is True)
		assert(node_a.has_children() is True)
		assert(node_b.has_children() is True)
		assert(node_c2.has_children() is False)
		assert(node_c1.has_children() is False)

		pytest.raises(ValueError, node_b.set_parent, node_a)

		pytest.raises(TypeError, node_a.set_parent, 1)
		pytest.raises(TypeError, node_a._add_child, 1)

	def test_iter(self):
		node_a = WUnbalancedTreeNode('a')
		node_b = WUnbalancedTreeNode('b', node_a)
		node_c = WUnbalancedTreeNode('c', node_a)
		node_d = WUnbalancedTreeNode('d', node_b)

		pytest.raises(KeyError, list, node_a.to_node('e'))

		assert(list(node_a.to_parent()) == [node_a])
		assert(list(node_a.to_node('a')) == [node_a])
		assert(list(node_a.to_node('b')) == [node_a, node_b])
		assert(list(node_a.to_node('c')) == [node_a, node_c])
		assert(list(node_a.to_node('d')) == [node_a, node_b, node_d])
		assert(set(node_a.children()) == {node_b, node_c})

		assert(list(node_b.to_parent()) == [node_b, node_a])
		pytest.raises(KeyError, list, node_b.to_node('a'))
		assert(list(node_b.to_node('b')) == [node_b])
		pytest.raises(KeyError, list, node_b.to_node('c'))
		assert(list(node_b.to_node('d')) == [node_b, node_d])
		assert(set(node_b.children()) == {node_d})

		assert(list(node_c.to_parent()) == [node_c, node_a])
		pytest.raises(KeyError, list, node_c.to_node('a'))
		pytest.raises(KeyError, list, node_c.to_node('b'))
		assert(list(node_c.to_node('c')) == [node_c])
		pytest.raises(KeyError, list, node_c.to_node('d'))
		assert(set(node_c.children()) == set())

		assert(list(node_d.to_parent()) == [node_d, node_b, node_a])
		pytest.raises(KeyError, list, node_d.to_node('a'))
		pytest.raises(KeyError, list, node_d.to_node('b'))
		pytest.raises(KeyError, list, node_d.to_node('c'))
		assert(list(node_d.to_node('d')) == [node_d])
		assert(set(node_d.children()) == set())

		all_nodes_a = [x.node_id() for x in node_a.all_nodes()]
		all_nodes_a.sort()
		assert(all_nodes_a == ['a', 'b', 'c', 'd'])

		all_nodes_b = [x.node_id() for x in node_b.all_nodes()]
		all_nodes_b.sort()
		assert(all_nodes_b == ['b', 'd'])

		all_nodes_c = [x.node_id() for x in node_c.all_nodes()]
		all_nodes_c.sort()
		assert(all_nodes_c == ['c'])

		all_nodes_d = [x.node_id() for x in node_d.all_nodes()]
		all_nodes_d.sort()
		assert(all_nodes_d == ['d'])

		node_b.set_parent(None)
		assert(list(node_a.to_parent()) == [node_a])
		assert(list(node_a.to_node('a')) == [node_a])
		pytest.raises(KeyError, list, node_a.to_node('b'))
		assert(list(node_a.to_node('c')) == [node_a, node_c])
		pytest.raises(KeyError, list, node_a.to_node('d'))

	def test_clone(self):
		node_a = WUnbalancedTreeNode(' a ')
		node_b = WUnbalancedTreeNode('b', node_a)
		node_c = WUnbalancedTreeNode('c', node_a)
		node_d = WUnbalancedTreeNode('d', node_b)

		cloned_a = node_a.clone()
		assert(isinstance(cloned_a, WUnbalancedTreeNode) is True)
		cloned_b = cloned_a.node('b')
		cloned_c = cloned_a.node('c')
		cloned_d = cloned_a.node('d')
		assert(list(cloned_d.to_parent()) == [cloned_d, cloned_b, cloned_a])
		assert(list(cloned_c.to_parent()) == [cloned_c, cloned_a])

		cloned_a.set_node_content(1)
		assert(cloned_a.node_content() == 1)
		assert(node_a.node_content() is None)
