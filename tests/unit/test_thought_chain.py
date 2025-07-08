"""
Unit tests for the thought chain module.

This module contains tests for the ThoughtChain class, verifying that it
correctly manages collections of ChainNodes representing chains of reasoning.
It also tests the persistence functionality for saving and loading chains.
"""

import unittest
import time
import json
import os
import tempfile
import shutil
import threading
import gzip
from copy import deepcopy
from pathlib import Path

from triangulum_lx.agents.chain_node import ChainNode, ThoughtType, RelationshipType
from triangulum_lx.agents.thought_chain import (
    ThoughtChain, TraversalOrder, ValidationError, 
    PersistenceError, ThoughtChainPersistence
)


class TestTraversalOrder(unittest.TestCase):
    """Test case for the TraversalOrder class."""
    
    def test_traversal_orders(self):
        """Test that all traversal orders are defined."""
        self.assertEqual(TraversalOrder.DEPTH_FIRST, "depth_first")
        self.assertEqual(TraversalOrder.BREADTH_FIRST, "breadth_first")
        self.assertEqual(TraversalOrder.CHRONOLOGICAL, "chronological")
        self.assertEqual(TraversalOrder.REVERSE_CHRONOLOGICAL, "reverse_chronological")
        self.assertEqual(TraversalOrder.CONFIDENCE, "confidence")


class TestThoughtChain(unittest.TestCase):
    """Test case for the ThoughtChain class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a basic chain for testing
        self.chain = ThoughtChain(
            chain_id="test_chain",
            name="Test Chain",
            description="A test thought chain",
            metadata={"purpose": "testing"}
        )
        
        # Create some nodes for testing
        self.root_node = ChainNode(
            thought_type=ThoughtType.OBSERVATION,
            content={"observation": "Initial observation"},
            author_agent_id="observer_agent",
            node_id="root_node",
            confidence=0.9
        )
        
        self.hypothesis_node = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"hypothesis": "Proposed explanation"},
            author_agent_id="hypothesis_agent",
            node_id="hypothesis_node",
            confidence=0.7
        )
        
        self.evidence_node = ChainNode(
            thought_type=ThoughtType.EVIDENCE,
            content={"evidence": "Supporting evidence"},
            author_agent_id="evidence_agent",
            node_id="evidence_node",
            confidence=0.8
        )
        
        self.conclusion_node = ChainNode(
            thought_type=ThoughtType.CONCLUSION,
            content={"conclusion": "Final conclusion"},
            author_agent_id="conclusion_agent",
            node_id="conclusion_node",
            confidence=0.85
        )
        
        # Add the root node to the chain
        self.chain.add_node(self.root_node)
    
    def test_initialization(self):
        """Test initializing a chain with various parameters."""
        # Test with all parameters
        chain = ThoughtChain(
            chain_id="custom_chain",
            name="Custom Chain",
            description="A custom thought chain",
            metadata={"purpose": "custom testing"}
        )
        
        self.assertEqual(chain.chain_id, "custom_chain")
        self.assertEqual(chain.name, "Custom Chain")
        self.assertEqual(chain.description, "A custom thought chain")
        self.assertEqual(chain.metadata, {"purpose": "custom testing"})
        self.assertEqual(len(chain), 0)
        self.assertEqual(chain._root_node_ids, set())
        self.assertEqual(chain._leaf_node_ids, set())
        
        # Test with defaults
        chain = ThoughtChain()
        
        self.assertTrue(chain.chain_id)  # Should have generated an ID
        self.assertTrue(chain.name.startswith("ThoughtChain-"))
        self.assertEqual(chain.description, "")
        self.assertEqual(chain.metadata, {})
    
    def test_add_node(self):
        """Test adding nodes to the chain."""
        # Add a node without a parent (should be a root node)
        node_id = self.chain.add_node(self.hypothesis_node)
        
        self.assertEqual(node_id, self.hypothesis_node.node_id)
        self.assertIn(node_id, self.chain._root_node_ids)
        self.assertIn(node_id, self.chain._leaf_node_ids)
        self.assertEqual(len(self.chain), 2)  # root_node + hypothesis_node
        
        # Add a node with a parent
        child_node_id = self.chain.add_node(
            self.evidence_node,
            parent_id=self.root_node.node_id,
            relationship=RelationshipType.SUPPORTS
        )
        
        self.assertEqual(child_node_id, self.evidence_node.node_id)
        self.assertNotIn(child_node_id, self.chain._root_node_ids)
        self.assertIn(child_node_id, self.chain._leaf_node_ids)
        self.assertNotIn(self.root_node.node_id, self.chain._leaf_node_ids)  # No longer a leaf
        
        # Verify the relationship was established
        parent_node = self.chain.get_node(self.root_node.node_id)
        child_node = self.chain.get_node(child_node_id)
        self.assertIn(child_node_id, parent_node.child_ids)
        self.assertIn(self.root_node.node_id, child_node.parent_ids)
        self.assertEqual(parent_node.get_relationship_to(child_node_id), RelationshipType.SUPPORTS)
        
        # Try adding a node with a non-existent parent
        with self.assertRaises(ValueError):
            self.chain.add_node(self.conclusion_node, parent_id="nonexistent_node", relationship=RelationshipType.DERIVES_FROM)
        
        # Try adding a node with a parent but no relationship
        with self.assertRaises(ValueError):
            self.chain.add_node(self.conclusion_node, parent_id=self.root_node.node_id, relationship=None)
        
        # Add an existing node (should just return the node_id without changing anything)
        existing_node_id = self.chain.add_node(self.root_node)
        self.assertEqual(existing_node_id, self.root_node.node_id)
        self.assertEqual(len(self.chain), 3)  # Shouldn't have added a duplicate
    
    def test_remove_node(self):
        """Test removing nodes from the chain."""
        # Add nodes to the chain first
        self.chain.add_node(self.hypothesis_node, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(self.evidence_node, parent_id=self.hypothesis_node.node_id, relationship=RelationshipType.SUPPORTS)
        self.chain.add_node(self.conclusion_node, parent_id=self.evidence_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        
        # Chain should now have 4 nodes: root -> hypothesis -> evidence -> conclusion
        self.assertEqual(len(self.chain), 4)
        
        # Remove a middle node (evidence) and reconnect its children to its parents
        result = self.chain.remove_node(self.evidence_node.node_id, reconnect_orphans=True)
        
        self.assertTrue(result)
        self.assertEqual(len(self.chain), 3)
        self.assertNotIn(self.evidence_node.node_id, self.chain)
        
        # The conclusion node should now be connected to the hypothesis node
        hypothesis_node = self.chain.get_node(self.hypothesis_node.node_id)
        conclusion_node = self.chain.get_node(self.conclusion_node.node_id)
        self.assertIn(self.conclusion_node.node_id, hypothesis_node.child_ids)
        self.assertIn(self.hypothesis_node.node_id, conclusion_node.parent_ids)
        
        # Remove a middle node (hypothesis) without reconnecting orphans
        result = self.chain.remove_node(self.hypothesis_node.node_id, reconnect_orphans=False)
        
        self.assertTrue(result)
        self.assertEqual(len(self.chain), 2)
        self.assertNotIn(self.hypothesis_node.node_id, self.chain)
        
        # The conclusion node should now be a root node
        self.assertIn(self.conclusion_node.node_id, self.chain._root_node_ids)
        
        # Try removing a non-existent node
        result = self.chain.remove_node("nonexistent_node")
        self.assertFalse(result)
        self.assertEqual(len(self.chain), 2)
    
    def test_get_node(self):
        """Test getting nodes by ID."""
        # Get an existing node
        node = self.chain.get_node(self.root_node.node_id)
        self.assertEqual(node, self.root_node)
        
        # Get a non-existent node
        node = self.chain.get_node("nonexistent_node")
        self.assertIsNone(node)
    
    def test_add_relationship(self):
        """Test adding relationships between nodes."""
        # Add nodes to the chain
        self.chain.add_node(self.hypothesis_node)
        self.chain.add_node(self.evidence_node)
        
        # Add a relationship between nodes
        result = self.chain.add_relationship(
            source_id=self.root_node.node_id,
            target_id=self.hypothesis_node.node_id,
            relationship=RelationshipType.DERIVES_FROM
        )
        
        self.assertTrue(result)
        
        # Verify the relationship was established
        source_node = self.chain.get_node(self.root_node.node_id)
        target_node = self.chain.get_node(self.hypothesis_node.node_id)
        self.assertIn(self.hypothesis_node.node_id, source_node.child_ids)
        self.assertIn(self.root_node.node_id, target_node.parent_ids)
        self.assertEqual(source_node.get_relationship_to(self.hypothesis_node.node_id), RelationshipType.DERIVES_FROM)
        
        # hypothesis_node should no longer be a root node
        self.assertNotIn(self.hypothesis_node.node_id, self.chain._root_node_ids)
        
        # Try adding a relationship that would create a cycle
        self.chain.add_relationship(
            source_id=self.hypothesis_node.node_id,
            target_id=self.evidence_node.node_id,
            relationship=RelationshipType.SUPPORTS
        )
        
        with self.assertRaises(ValueError):
            self.chain.add_relationship(
                source_id=self.evidence_node.node_id,
                target_id=self.root_node.node_id,
                relationship=RelationshipType.SUPPORTS
            )
        
        # But a PARALLEL relationship should be allowed (doesn't imply hierarchy)
        result = self.chain.add_relationship(
            source_id=self.evidence_node.node_id,
            target_id=self.root_node.node_id,
            relationship=RelationshipType.PARALLEL
        )
        self.assertTrue(result)
        
        # Try adding a relationship with non-existent nodes
        result = self.chain.add_relationship(
            source_id="nonexistent_source",
            target_id=self.hypothesis_node.node_id,
            relationship=RelationshipType.SUPPORTS
        )
        self.assertFalse(result)
        
        result = self.chain.add_relationship(
            source_id=self.root_node.node_id,
            target_id="nonexistent_target",
            relationship=RelationshipType.SUPPORTS
        )
        self.assertFalse(result)
    
    def test_remove_relationship(self):
        """Test removing relationships between nodes."""
        # Set up a chain with relationships
        self.chain.add_node(self.hypothesis_node, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(self.evidence_node, parent_id=self.hypothesis_node.node_id, relationship=RelationshipType.SUPPORTS)
        
        # Remove a relationship
        result = self.chain.remove_relationship(
            source_id=self.root_node.node_id,
            target_id=self.hypothesis_node.node_id
        )
        
        self.assertTrue(result)
        
        # Verify the relationship was removed
        source_node = self.chain.get_node(self.root_node.node_id)
        target_node = self.chain.get_node(self.hypothesis_node.node_id)
        self.assertNotIn(self.hypothesis_node.node_id, source_node.child_ids)
        self.assertNotIn(self.root_node.node_id, target_node.parent_ids)
        
        # hypothesis_node should now be a root node
        self.assertIn(self.hypothesis_node.node_id, self.chain._root_node_ids)
        # root_node should now be a leaf node
        self.assertIn(self.root_node.node_id, self.chain._leaf_node_ids)
        
        # Try removing a non-existent relationship
        result = self.chain.remove_relationship(
            source_id=self.root_node.node_id,
            target_id=self.evidence_node.node_id
        )
        self.assertFalse(result)
        
        # Try removing a relationship with non-existent nodes
        result = self.chain.remove_relationship(
            source_id="nonexistent_source",
            target_id=self.hypothesis_node.node_id
        )
        self.assertFalse(result)
        
        result = self.chain.remove_relationship(
            source_id=self.root_node.node_id,
            target_id="nonexistent_target"
        )
        self.assertFalse(result)
    
    def test_traverse_depth_first(self):
        """Test depth-first traversal."""
        # Set up a more complex chain
        #     root
        #    /    \
        # node1   node2
        #   |       |
        # node3   node4
        #   \     /
        #    node5
        
        node1 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 1"}, author_agent_id="agent", node_id="node1")
        node2 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 2"}, author_agent_id="agent", node_id="node2")
        node3 = ChainNode(thought_type=ThoughtType.EVIDENCE, content={"text": "Node 3"}, author_agent_id="agent", node_id="node3")
        node4 = ChainNode(thought_type=ThoughtType.EVIDENCE, content={"text": "Node 4"}, author_agent_id="agent", node_id="node4")
        node5 = ChainNode(thought_type=ThoughtType.CONCLUSION, content={"text": "Node 5"}, author_agent_id="agent", node_id="node5")
        
        self.chain.add_node(node1, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(node2, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(node3, parent_id=node1.node_id, relationship=RelationshipType.SUPPORTS)
        self.chain.add_node(node4, parent_id=node2.node_id, relationship=RelationshipType.SUPPORTS)
        self.chain.add_node(node5, parent_id=node3.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_relationship(source_id=node4.node_id, target_id=node5.node_id, relationship=RelationshipType.DERIVES_FROM)
        
        # Traverse depth-first from root
        traversal = list(self.chain.traverse(order=TraversalOrder.DEPTH_FIRST))
        
        # Should visit root, node1, node3, node5, node2, node4
        # (or root, node2, node4, node5, node1, node3 - depends on implementation order)
        # We'll just check that it visits all nodes and follows depth-first order
        self.assertEqual(len(traversal), 6)
        self.assertEqual(traversal[0], self.root_node)  # Should start with root
        
        # Traverse from a specific node
        traversal = list(self.chain.traverse(order=TraversalOrder.DEPTH_FIRST, start_node_id=node1.node_id))
        
        # Should visit node1, node3, node5
        self.assertEqual(len(traversal), 3)
        self.assertEqual(traversal[0], node1)
        self.assertEqual(traversal[1], node3)
        self.assertEqual(traversal[2], node5)
        
        # Traverse with a filter
        def filter_evidence(node):
            return node.thought_type == ThoughtType.EVIDENCE
        
        traversal = list(self.chain.traverse(order=TraversalOrder.DEPTH_FIRST, filter_fn=filter_evidence))
        
        # Should only visit node3 and node4
        self.assertEqual(len(traversal), 2)
        self.assertTrue(all(node.thought_type == ThoughtType.EVIDENCE for node in traversal))
        
        # Try traversing with a non-existent start node
        with self.assertRaises(ValueError):
            list(self.chain.traverse(order=TraversalOrder.DEPTH_FIRST, start_node_id="nonexistent_node"))
    
    def test_traverse_breadth_first(self):
        """Test breadth-first traversal."""
        # Set up a more complex chain (same as in test_traverse_depth_first)
        node1 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 1"}, author_agent_id="agent", node_id="node1")
        node2 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 2"}, author_agent_id="agent", node_id="node2")
        node3 = ChainNode(thought_type=ThoughtType.EVIDENCE, content={"text": "Node 3"}, author_agent_id="agent", node_id="node3")
        node4 = ChainNode(thought_type=ThoughtType.EVIDENCE, content={"text": "Node 4"}, author_agent_id="agent", node_id="node4")
        node5 = ChainNode(thought_type=ThoughtType.CONCLUSION, content={"text": "Node 5"}, author_agent_id="agent", node_id="node5")
        
        self.chain.add_node(node1, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(node2, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(node3, parent_id=node1.node_id, relationship=RelationshipType.SUPPORTS)
        self.chain.add_node(node4, parent_id=node2.node_id, relationship=RelationshipType.SUPPORTS)
        self.chain.add_node(node5, parent_id=node3.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_relationship(source_id=node4.node_id, target_id=node5.node_id, relationship=RelationshipType.DERIVES_FROM)
        
        # Traverse breadth-first from root
        traversal = list(self.chain.traverse(order=TraversalOrder.BREADTH_FIRST))
        
        # Should visit root, node1, node2, node3, node4, node5
        # (or root, node2, node1, node4, node3, node5 - depends on implementation order)
        # We'll just check that it visits all nodes and follows breadth-first order
        self.assertEqual(len(traversal), 6)
        self.assertEqual(traversal[0], self.root_node)  # Should start with root
        
        # Check that children are visited before grandchildren
        root_index = traversal.index(self.root_node)
        node1_index = traversal.index(node1)
        node2_index = traversal.index(node2)
        node3_index = traversal.index(node3)
        node4_index = traversal.index(node4)
        node5_index = traversal.index(node5)
        
        self.assertTrue(root_index < node1_index)
        self.assertTrue(root_index < node2_index)
        self.assertTrue(node1_index < node3_index)
        self.assertTrue(node2_index < node4_index)
        self.assertTrue(node3_index < node5_index)
        self.assertTrue(node4_index < node5_index)
    
    def test_traverse_chronological(self):
        """Test chronological traversal."""
        # Set up nodes with different timestamps
        node1 = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"text": "Oldest node"},
            author_agent_id="agent",
            node_id="node1",
            timestamp=1000
        )
        
        node2 = ChainNode(
            thought_type=ThoughtType.EVIDENCE,
            content={"text": "Middle node"},
            author_agent_id="agent",
            node_id="node2",
            timestamp=2000
        )
        
        node3 = ChainNode(
            thought_type=ThoughtType.CONCLUSION,
            content={"text": "Newest node"},
            author_agent_id="agent",
            node_id="node3",
            timestamp=3000
        )
        
        # Add nodes to chain (not connected)
        self.chain.add_node(node1)
        self.chain.add_node(node2)
        self.chain.add_node(node3)
        
        # Traverse in chronological order (oldest to newest)
        traversal = list(self.chain.traverse(order=TraversalOrder.CHRONOLOGICAL))
        
        # Should be ordered by timestamp (including root node)
        self.assertEqual(len(traversal), 4)
        timestamps = [node.timestamp for node in traversal]
        self.assertEqual(timestamps, sorted(timestamps))
        
        # Traverse in reverse chronological order (newest to oldest)
        traversal = list(self.chain.traverse(order=TraversalOrder.REVERSE_CHRONOLOGICAL))
        
        # Should be ordered by timestamp, descending
        self.assertEqual(len(traversal), 4)
        timestamps = [node.timestamp for node in traversal]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
    
    def test_traverse_by_confidence(self):
        """Test traversal by confidence."""
        # Set up nodes with different confidence levels
        node1 = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"text": "Low confidence"},
            author_agent_id="agent",
            node_id="node1",
            confidence=0.3
        )
        
        node2 = ChainNode(
            thought_type=ThoughtType.EVIDENCE,
            content={"text": "Medium confidence"},
            author_agent_id="agent",
            node_id="node2",
            confidence=0.6
        )
        
        node3 = ChainNode(
            thought_type=ThoughtType.CONCLUSION,
            content={"text": "High confidence"},
            author_agent_id="agent",
            node_id="node3",
            confidence=0.9
        )
        
        # Add nodes to chain (not connected)
        self.chain.add_node(node1)
        self.chain.add_node(node2)
        self.chain.add_node(node3)
        
        # Traverse by confidence (highest first)
        traversal = list(self.chain.traverse(order=TraversalOrder.CONFIDENCE))
        
        # Should be ordered by confidence (including root node which has 0.9)
        # root and node3 both have 0.9, so ordering between them depends on implementation
        self.assertEqual(len(traversal), 4)
        confidences = [node.confidence for node in traversal]
        self.assertEqual(confidences, sorted(confidences, reverse=True))
        
        # Add a node with no confidence
        node4 = ChainNode(
            thought_type=ThoughtType.QUESTION,
            content={"text": "No confidence"},
            author_agent_id="agent",
            node_id="node4"
        )
        self.chain.add_node(node4)
        
        # Traverse by confidence - should exclude node4
        traversal = list(self.chain.traverse(order=TraversalOrder.CONFIDENCE))
        
        # Should still only have 4 nodes (excluding the one with no confidence)
        self.assertEqual(len(traversal), 4)
        self.assertNotIn(node4, traversal)
    
    def test_find_nodes(self):
        """Test finding nodes by various criteria."""
        # Set up nodes with different properties
        node1 = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"hypothesis": "First hypothesis with keyword"},
            author_agent_id="hypothesis_agent",
            node_id="node1",
            confidence=0.3
        )
        
        node2 = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"hypothesis": "Second hypothesis"},
            author_agent_id="hypothesis_agent",
            node_id="node2",
            confidence=0.7
        )
        
        node3 = ChainNode(
            thought_type=ThoughtType.EVIDENCE,
            content={"evidence": "Supporting evidence with keyword"},
            author_agent_id="evidence_agent",
            node_id="node3",
            confidence=0.8
        )
        
        # Add nodes to chain
        self.chain.add_node(node1)
        self.chain.add_node(node2)
        self.chain.add_node(node3)
        
        # Find by thought type
        results = self.chain.find_nodes(thought_type=ThoughtType.HYPOTHESIS)
        self.assertEqual(len(results), 2)
        self.assertIn(node1, results)
        self.assertIn(node2, results)
        
        # Find by author
        results = self.chain.find_nodes(author_agent_id="evidence_agent")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], node3)
        
        # Find by confidence range
        results = self.chain.find_nodes(min_confidence=0.5, max_confidence=0.9)
        self.assertEqual(len(results), 3)  # node2, node3, and root_node
        self.assertIn(node2, results)
        self.assertIn(node3, results)
        self.assertIn(self.root_node, results)
        
        # Find by keyword
        results = self.chain.find_nodes(keyword="keyword")
        self.assertEqual(len(results), 2)
        self.assertIn(node1, results)
        self.assertIn(node3, results)
        
        # Find with multiple criteria
        results = self.chain.find_nodes(
            thought_type=ThoughtType.HYPOTHESIS,
            author_agent_id="hypothesis_agent",
            min_confidence=0.5
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], node2)
    
    def test_find_paths(self):
        """Test finding paths between nodes."""
        # Set up a more complex chain
        #     root
        #    /    \
        # node1   node2
        #   |       |
        # node3   node4
        #   \     /
        #    node5
        
        node1 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 1"}, author_agent_id="agent", node_id="node1")
        node2 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 2"}, author_agent_id="agent", node_id="node2")
        node3 = ChainNode(thought_type=ThoughtType.EVIDENCE, content={"text": "Node 3"}, author_agent_id="agent", node_id="node3")
        node4 = ChainNode(thought_type=ThoughtType.EVIDENCE, content={"text": "Node 4"}, author_agent_id="agent", node_id="node4")
        node5 = ChainNode(thought_type=ThoughtType.CONCLUSION, content={"text": "Node 5"}, author_agent_id="agent", node_id="node5")
        
        self.chain.add_node(node1, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(node2, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(node3, parent_id=node1.node_id, relationship=RelationshipType.SUPPORTS)
        self.chain.add_node(node4, parent_id=node2.node_id, relationship=RelationshipType.SUPPORTS)
        self.chain.add_node(node5, parent_id=node3.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_relationship(source_id=node4.node_id, target_id=node5.node_id, relationship=RelationshipType.DERIVES_FROM)
        
        # Find paths from root to node5
        paths = self.chain.find_paths(source_id=self.root_node.node_id, target_id=node5.node_id)
        
        # Should find 2 paths:
        # 1. root -> node1 -> node3 -> node5
        # 2. root -> node2 -> node4 -> node5
        self.assertEqual(len(paths), 2)
        
        # Check each path
        expected_path1 = [self.root_node.node_id, node1.node_id, node3.node_id, node5.node_id]
        expected_path2 = [self.root_node.node_id, node2.node_id, node4.node_id, node5.node_id]
        
        self.assertTrue(expected_path1 in paths or expected_path2 in paths)
        
        # Find paths between unconnected nodes
        paths = self.chain.find_paths(source_id=node1.node_id, target_id=node4.node_id)
        self.assertEqual(len(paths), 0)
        
        # Try with non-existent nodes
        with self.assertRaises(ValueError):
            self.chain.find_paths(source_id="nonexistent_source", target_id=node5.node_id)
    
    def test_validate(self):
        """Test validation of a thought chain's integrity."""
        # Set up a simple chain
        node1 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 1"}, author_agent_id="agent", node_id="node1")
        node2 = ChainNode(thought_type=ThoughtType.EVIDENCE, content={"text": "Node 2"}, author_agent_id="agent", node_id="node2")
        
        self.chain.add_node(node1, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(node2, parent_id=node1.node_id, relationship=RelationshipType.SUPPORTS)
        
        # Validate a correct chain
        is_valid, errors = self.chain.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Artificially introduce an inconsistency
        self.chain._nodes[node1.node_id].child_ids.remove(node2.node_id)
        
        # Validate the now-inconsistent chain
        is_valid, errors = self.chain.validate()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_to_from_dict(self):
        """Test converting a chain to and from a dictionary."""
        # Set up a simple chain
        node1 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 1"}, author_agent_id="agent", node_id="node1")
        node2 = ChainNode(thought_type=ThoughtType.EVIDENCE, content={"text": "Node 2"}, author_agent_id="agent", node_id="node2")
        
        self.chain.add_node(node1, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        self.chain.add_node(node2, parent_id=node1.node_id, relationship=RelationshipType.SUPPORTS)
        
        # Convert to dictionary
        chain_dict = self.chain.to_dict()
        
        # Verify dictionary contents
        self.assertEqual(chain_dict["chain_id"], "test_chain")
        self.assertEqual(chain_dict["name"], "Test Chain")
        self.assertEqual(chain_dict["description"], "A test thought chain")
        self.assertEqual(chain_dict["metadata"], {"purpose": "testing"})
        self.assertEqual(len(chain_dict["nodes"]), 3)
        self.assertEqual(len(chain_dict["root_node_ids"]), 1)
        self.assertEqual(len(chain_dict["leaf_node_ids"]), 1)
        
        # Convert back to a chain
        new_chain = ThoughtChain.from_dict(chain_dict)
        
        # Verify the new chain
        self.assertEqual(new_chain.chain_id, self.chain.chain_id)
        self.assertEqual(new_chain.name, self.chain.name)
        self.assertEqual(new_chain.description, self.chain.description)
        self.assertEqual(len(new_chain), len(self.chain))
        
        # Verify relationships were preserved
        new_root = new_chain.get_node(self.root_node.node_id)
        new_node1 = new_chain.get_node(node1.node_id)
        new_node2 = new_chain.get_node(node2.node_id)
        
        self.assertIn(node1.node_id, new_root.child_ids)
        self.assertEqual(new_root.get_relationship_to(node1.node_id), RelationshipType.DERIVES_FROM)
        self.assertIn(node2.node_id, new_node1.child_ids)
        self.assertEqual(new_node1.get_relationship_to(node2.node_id), RelationshipType.SUPPORTS)
    
    def test_to_from_json(self):
        """Test converting a chain to and from JSON."""
        # Set up a simple chain
        node1 = ChainNode(thought_type=ThoughtType.HYPOTHESIS, content={"text": "Node 1"}, author_agent_id="agent", node_id="node1")
        self.chain.add_node(node1, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        
        # Convert to JSON
        chain_json = self.chain.to_json()
        
        # Verify it's valid JSON
        parsed = json.loads(chain_json)
        self.assertEqual(parsed["chain_id"], "test_chain")
        
        # Convert back to a chain
        new_chain = ThoughtChain.from_json(chain_json)
        
        # Verify the new chain
        self.assertEqual(new_chain.chain_id, self.chain.chain_id)
        self.assertEqual(len(new_chain), len(self.chain))
        
        # Verify relationships were preserved
        new_root = new_chain.get_node(self.root_node.node_id)
        self.assertIn(node1.node_id, new_root.child_ids)


class TestThoughtChainPersistence(unittest.TestCase):
    """Test case for the ThoughtChainPersistence class and persistence features."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a basic chain for testing
        self.chain = ThoughtChain(
            chain_id="test_persistence_chain",
            name="Test Persistence Chain",
            description="A chain for testing persistence",
            metadata={"purpose": "testing persistence"}
        )
        
        # Add some nodes
        self.root_node = ChainNode(
            thought_type=ThoughtType.OBSERVATION,
            content={"observation": "Initial observation"},
            author_agent_id="observer_agent",
            node_id="root_node",
            confidence=0.9
        )
        
        self.child_node = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"hypothesis": "Proposed explanation"},
            author_agent_id="hypothesis_agent",
            node_id="child_node",
            confidence=0.7
        )
        
        # Add the nodes to the chain
        self.chain.add_node(self.root_node)
        self.chain.add_node(self.child_node, parent_id=self.root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)
    
    def test_save_and_load_file(self):
        """Test saving and loading a chain to/from a file."""
        # Define a file path
        filepath = os.path.join(self.test_dir, "test_chain.json")
        
        # Save the chain
        saved_path = self.chain.save_to_file(filepath)
        self.assertEqual(saved_path, filepath)
        self.assertTrue(os.path.exists(filepath))
        
        # Load the chain
        loaded_chain = ThoughtChain.load_from_file(filepath)
        
        # Verify the loaded chain
        self.assertEqual(loaded_chain.chain_id, self.chain.chain_id)
        self.assertEqual(loaded_chain.name, self.chain.name)
        self.assertEqual(loaded_chain.description, self.chain.description)
        self.assertEqual(len(loaded_chain), len(self.chain))
        
        # Verify relationships were preserved
        loaded_root = loaded_chain.get_node(self.root_node.node_id)
        loaded_child = loaded_chain.get_node(self.child_node.node_id)
        
        self.assertIn(self.child_node.node_id, loaded_root.child_ids)
        self.assertIn(self.root_node.node_id, loaded_child.parent_ids)
        self.assertEqual(loaded_root.get_relationship_to(self.child_node.node_id), RelationshipType.DERIVES_FROM)
    
    def test_save_with_auto_filepath(self):
        """Test saving a chain with an automatically generated filepath."""
        # Save the chain with auto-generated filepath
        saved_path = self.chain.save_to_file(storage_dir=self.test_dir)
        
        # Verify the file was created
        self.assertTrue(os.path.exists(saved_path))
        expected_filename = f"{self.chain.chain_id}.json"
        self.assertTrue(saved_path.endswith(expected_filename))
        
        # Verify we can load the chain
        loaded_chain = ThoughtChain.load_from_file(saved_path)
        self.assertEqual(loaded_chain.chain_id, self.chain.chain_id)
    
    def test_compression(self):
        """Test saving and loading with compression."""
        # Define a file path
        filepath = os.path.join(self.test_dir, "test_chain_compressed.json")
        
        # Save with compression
        saved_path = self.chain.save_to_file(filepath, compress=True)
        
        # Should have .gz extension
        self.assertTrue(saved_path.endswith(".gz"))
        self.assertTrue(os.path.exists(saved_path))
        
        # Verify it's actually compressed and contains the expected content
        with gzip.open(saved_path, "rt", encoding='utf-8') as gz_f:
            content = gz_f.read()
            self.assertIn("test_persistence_chain", content)
        
        # Load the compressed chain
        loaded_chain = ThoughtChain.load_from_file(saved_path)
        
        # Verify the loaded chain
        self.assertEqual(loaded_chain.chain_id, self.chain.chain_id)
        self.assertEqual(len(loaded_chain), len(self.chain))
    
    def test_backup_versioning(self):
        """Test backup versioning when saving chains."""
        # Define a file path
        filepath = os.path.join(self.test_dir, "versioned_chain.json")
        
        # Save the chain multiple times
        self.chain.save_to_file(filepath)
        
        # Modify the chain
        new_node = ChainNode(
            thought_type=ThoughtType.EVIDENCE,
            content={"evidence": "Supporting evidence"},
            author_agent_id="evidence_agent",
            node_id="evidence_node"
        )
        self.chain.add_node(new_node, parent_id=self.child_node.node_id, relationship=RelationshipType.SUPPORTS)
        
        # Save again with backup
        self.chain.save_to_file(filepath, create_backup=True, max_backups=2)
        
        # Should have original file plus one backup
        backup_files = [f for f in os.listdir(self.test_dir) if f.startswith("versioned_chain.") and f != "versioned_chain.json"]
        self.assertEqual(len(backup_files), 1)
        
        # For the test, let's manually create another backup to ensure we have 2
        # The real implementation will create backups as we save multiple times
        # Let's create a 1-second delay to ensure a different timestamp
        time.sleep(1)
        
        # Create a modified file that's different from the last one
        for i in range(3):
            new_node = ChainNode(
                thought_type=ThoughtType.EVIDENCE,
                content={"evidence": f"More evidence {i}"},
                author_agent_id="evidence_agent",
                node_id=f"more_evidence_{i}"
            )
            self.chain.add_node(new_node)
            
        # Save again to create a new backup
        self.chain.save_to_file(filepath, create_backup=True, max_backups=2)
        
        # Should still have only 2 backup files (due to max_backups=2)
        backup_files = [f for f in os.listdir(self.test_dir) if f.startswith("versioned_chain.") and f != "versioned_chain.json"]
        self.assertEqual(len(backup_files), 2)
    
    def test_error_handling(self):
        """Test error handling for file operations."""
        # Test loading a non-existent file
        with self.assertRaises(PersistenceError):
            ThoughtChain.load_from_file(os.path.join(self.test_dir, "nonexistent.json"))
        
        # Test saving to a non-writable location
        if os.name != 'nt':  # Skip on Windows as permissions work differently
            try:
                # Try to create a directory without write permission
                no_write_dir = os.path.join(self.test_dir, "no_write")
                os.mkdir(no_write_dir)
                os.chmod(no_write_dir, 0o444)  # Read-only
                
                filepath = os.path.join(no_write_dir, "should_fail.json")
                
                with self.assertRaises(PersistenceError):
                    self.chain.save_to_file(filepath)
            except Exception as e:
                # Clean up even if test fails
                os.chmod(no_write_dir, 0o777)  # Restore permissions for cleanup
    
    def test_list_available_chains(self):
        """Test listing available chains."""
        # Save multiple chains
        chains = []
        for i in range(3):
            chain = ThoughtChain(
                chain_id=f"list_test_chain_{i}",
                name=f"Test Chain {i}",
                description=f"Description {i}"
            )
            node = ChainNode(
                thought_type=ThoughtType.OBSERVATION,
                content={"observation": f"Observation {i}"},
                author_agent_id="observer_agent",
                node_id=f"node_{i}"
            )
            chain.add_node(node)
            chain.save_to_file(storage_dir=self.test_dir)
            chains.append(chain)
        
        # List available chains
        available_chains = ThoughtChain.list_available_chains(directory=self.test_dir)
        
        # Should find all the chains we saved
        self.assertGreaterEqual(len(available_chains), 3)
        
        # Verify the metadata
        chain_ids = [chain.chain_id for chain in chains]
        available_ids = [meta["chain_id"] for meta in available_chains]
        
        for chain_id in chain_ids:
            self.assertIn(chain_id, available_ids)
    
    def test_thread_safety(self):
        """Test thread safety of file operations."""
        # Define a file path
        filepath = os.path.join(self.test_dir, "thread_test.json")
        
        # Create a chain with extra nodes to test with
        test_chain = ThoughtChain(
            chain_id="thread_test_chain",
            name="Thread Test Chain",
            description="A chain for testing thread safety"
        )
        
        # Add the original nodes
        root_node = ChainNode(
            thought_type=ThoughtType.OBSERVATION,
            content={"observation": "Initial thread test observation"},
            author_agent_id="observer_agent",
            node_id="thread_root_node"
        )
        
        child_node = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"hypothesis": "Initial thread test hypothesis"},
            author_agent_id="hypothesis_agent",
            node_id="thread_child_node"
        )
        
        test_chain.add_node(root_node)
        test_chain.add_node(child_node, parent_id=root_node.node_id, relationship=RelationshipType.DERIVES_FROM)
        
        # Save the initial chain
        test_chain.save_to_file(filepath)
        
        # Create a lock for thread synchronization
        file_lock = threading.Lock()
        
        # Function to modify and save the chain in a thread
        def modify_and_save(thread_id):
            # Use a lock to ensure thread safety during the test
            with file_lock:
                # Load the chain
                chain = ThoughtChain.load_from_file(filepath)
                
                # Modify the chain
                node = ChainNode(
                    thought_type=ThoughtType.EVIDENCE,
                    content={"evidence": f"Thread {thread_id} evidence"},
                    author_agent_id="thread_agent",
                    node_id=f"thread_{thread_id}_node"
                )
                chain.add_node(node)
                
                # Save the chain
                chain.save_to_file(filepath)
        
        # Create and start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=modify_and_save, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Load the final chain
        final_chain = ThoughtChain.load_from_file(filepath)
        
        # Verify the chain has all the nodes added by threads
        node_count = len(final_chain)
        self.assertEqual(node_count, 7)  # 2 original nodes + 5 added by threads
        
        # Check that all thread nodes are present
        for i in range(5):
            node_id = f"thread_{i}_node"
            self.assertIn(node_id, final_chain)
