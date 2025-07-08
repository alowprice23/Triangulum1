"""
Unit tests for the chain node module.

This module contains tests for the ChainNode class, verifying that it
correctly represents nodes in a thought chain.
"""

import unittest
import time
import json
from copy import deepcopy

from triangulum_lx.agents.chain_node import ChainNode, ThoughtType, RelationshipType


class TestThoughtType(unittest.TestCase):
    """Test case for the ThoughtType enum."""
    
    def test_thought_types(self):
        """Test that all thought types are defined."""
        # Verify all expected thought types exist
        self.assertEqual(ThoughtType.OBSERVATION.value, "observation")
        self.assertEqual(ThoughtType.HYPOTHESIS.value, "hypothesis")
        self.assertEqual(ThoughtType.EVIDENCE.value, "evidence")
        self.assertEqual(ThoughtType.INFERENCE.value, "inference")
        self.assertEqual(ThoughtType.QUESTION.value, "question")
        self.assertEqual(ThoughtType.ANSWER.value, "answer")
        self.assertEqual(ThoughtType.ARGUMENT.value, "argument")
        self.assertEqual(ThoughtType.COUNTERARGUMENT.value, "counterargument")
        self.assertEqual(ThoughtType.ACTION.value, "action")
        self.assertEqual(ThoughtType.CONCLUSION.value, "conclusion")
        self.assertEqual(ThoughtType.REFLECTION.value, "reflection")
        self.assertEqual(ThoughtType.CONTEXT.value, "context")


class TestRelationshipType(unittest.TestCase):
    """Test case for the RelationshipType enum."""
    
    def test_relationship_types(self):
        """Test that all relationship types are defined."""
        # Verify all expected relationship types exist
        self.assertEqual(RelationshipType.SUPPORTS.value, "supports")
        self.assertEqual(RelationshipType.CONTRADICTS.value, "contradicts")
        self.assertEqual(RelationshipType.EXTENDS.value, "extends")
        self.assertEqual(RelationshipType.QUESTIONS.value, "questions")
        self.assertEqual(RelationshipType.ANSWERS.value, "answers")
        self.assertEqual(RelationshipType.DERIVES_FROM.value, "derives_from")
        self.assertEqual(RelationshipType.ALTERNATIVE_TO.value, "alternative_to")
        self.assertEqual(RelationshipType.SPECIALIZES.value, "specializes")
        self.assertEqual(RelationshipType.GENERALIZES.value, "generalizes")
        self.assertEqual(RelationshipType.SEQUENCE.value, "sequence")
        self.assertEqual(RelationshipType.PARALLEL.value, "parallel")


class TestChainNode(unittest.TestCase):
    """Test case for the ChainNode class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a basic node for testing
        self.node = ChainNode(
            thought_type=ThoughtType.OBSERVATION,
            content={"text": "This is an observation"},
            author_agent_id="test_agent"
        )
    
    def test_initialization(self):
        """Test initializing a node with various parameters."""
        # Test required parameters
        node = ChainNode(
            thought_type=ThoughtType.OBSERVATION,
            content={"text": "This is an observation"},
            author_agent_id="test_agent"
        )
        self.assertEqual(node.thought_type, ThoughtType.OBSERVATION)
        self.assertEqual(node.content, {"text": "This is an observation"})
        self.assertEqual(node.author_agent_id, "test_agent")
        
        # Test with optional parameters
        custom_node_id = "custom_id"
        custom_timestamp = time.time() - 3600  # 1 hour ago
        custom_confidence = 0.85
        custom_metadata = {"source": "test", "importance": "high"}
        
        node = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"hypothesis": "This might be the cause"},
            author_agent_id="hypothesis_agent",
            node_id=custom_node_id,
            timestamp=custom_timestamp,
            confidence=custom_confidence,
            metadata=custom_metadata
        )
        
        self.assertEqual(node.thought_type, ThoughtType.HYPOTHESIS)
        self.assertEqual(node.content, {"hypothesis": "This might be the cause"})
        self.assertEqual(node.author_agent_id, "hypothesis_agent")
        self.assertEqual(node.node_id, custom_node_id)
        self.assertEqual(node.timestamp, custom_timestamp)
        self.assertEqual(node.confidence, custom_confidence)
        self.assertEqual(node.metadata, custom_metadata)
        
        # Check default values
        self.assertEqual(node.parent_ids, set())
        self.assertEqual(node.child_ids, set())
        self.assertEqual(node.relationships, {})
        self.assertEqual(node.schema_version, "1.0")
    
    def test_validation(self):
        """Test validation of node structure and content."""
        # Test invalid thought_type
        with self.assertRaises(ValueError):
            ChainNode(
                thought_type="not_an_enum",
                content={"text": "Invalid node"},
                author_agent_id="test_agent"
            )
        
        # Test invalid content
        with self.assertRaises(ValueError):
            ChainNode(
                thought_type=ThoughtType.OBSERVATION,
                content="not_a_dict",
                author_agent_id="test_agent"
            )
        
        # Test missing author_agent_id
        with self.assertRaises(ValueError):
            ChainNode(
                thought_type=ThoughtType.OBSERVATION,
                content={"text": "No author"},
                author_agent_id=""
            )
        
        # Test invalid confidence
        with self.assertRaises(ValueError):
            ChainNode(
                thought_type=ThoughtType.OBSERVATION,
                content={"text": "Invalid confidence"},
                author_agent_id="test_agent",
                confidence=1.5  # Should be between 0 and 1
            )
    
    def test_relationship_validation(self):
        """Test validation of relationships."""
        node = ChainNode(
            thought_type=ThoughtType.OBSERVATION,
            content={"text": "Relationship test"},
            author_agent_id="test_agent"
        )
        
        # Add a parent and child
        parent_id = "parent_node"
        child_id = "child_node"
        
        # Set up relationships without using add_parent/add_child
        node.parent_ids.add(parent_id)
        node.child_ids.add(child_id)
        
        # This should fail validation because relationships are not set up
        with self.assertRaises(ValueError):
            # Invalid relationship type
            node.relationships[parent_id] = "not_an_enum"
            node.validate()
        
        # Fix the relationships
        node.relationships = {}
        node.relationships[parent_id] = RelationshipType.DERIVES_FROM
        node.relationships[child_id] = RelationshipType.EXTENDS
        
        # This should pass
        self.assertTrue(node.validate())
        
        # Test relationship to non-existent node
        node.relationships["nonexistent_node"] = RelationshipType.SUPPORTS
        with self.assertRaises(ValueError):
            node.validate()
    
    def test_add_parent(self):
        """Test adding a parent node."""
        parent_id = "parent_node"
        relationship = RelationshipType.DERIVES_FROM
        
        self.node.add_parent(parent_id, relationship)
        
        # Check that the parent was added
        self.assertIn(parent_id, self.node.parent_ids)
        self.assertEqual(self.node.relationships[parent_id], relationship)
    
    def test_add_child(self):
        """Test adding a child node."""
        child_id = "child_node"
        relationship = RelationshipType.EXTENDS
        
        self.node.add_child(child_id, relationship)
        
        # Check that the child was added
        self.assertIn(child_id, self.node.child_ids)
        self.assertEqual(self.node.relationships[child_id], relationship)
    
    def test_remove_parent(self):
        """Test removing a parent node."""
        parent_id = "parent_node"
        relationship = RelationshipType.DERIVES_FROM
        
        # Add a parent first
        self.node.add_parent(parent_id, relationship)
        self.assertIn(parent_id, self.node.parent_ids)
        
        # Remove the parent
        self.node.remove_parent(parent_id)
        
        # Check that the parent was removed
        self.assertNotIn(parent_id, self.node.parent_ids)
        self.assertNotIn(parent_id, self.node.relationships)
        
        # Try removing a non-existent parent (should not raise an error)
        self.node.remove_parent("nonexistent_parent")
    
    def test_remove_child(self):
        """Test removing a child node."""
        child_id = "child_node"
        relationship = RelationshipType.EXTENDS
        
        # Add a child first
        self.node.add_child(child_id, relationship)
        self.assertIn(child_id, self.node.child_ids)
        
        # Remove the child
        self.node.remove_child(child_id)
        
        # Check that the child was removed
        self.assertNotIn(child_id, self.node.child_ids)
        self.assertNotIn(child_id, self.node.relationships)
        
        # Try removing a non-existent child (should not raise an error)
        self.node.remove_child("nonexistent_child")
    
    def test_to_dict(self):
        """Test converting a node to a dictionary."""
        # Create a node with various attributes
        node = ChainNode(
            thought_type=ThoughtType.HYPOTHESIS,
            content={"hypothesis": "This might be the cause"},
            author_agent_id="hypothesis_agent",
            node_id="test_node_id",
            confidence=0.75,
            metadata={"source": "experiment"}
        )
        
        # Add a parent and child
        node.add_parent("parent_id", RelationshipType.DERIVES_FROM)
        node.add_child("child_id", RelationshipType.SUPPORTS)
        
        # Convert to dictionary
        node_dict = node.to_dict()
        
        # Check all fields
        self.assertEqual(node_dict["thought_type"], "hypothesis")
        self.assertEqual(node_dict["content"], {"hypothesis": "This might be the cause"})
        self.assertEqual(node_dict["author_agent_id"], "hypothesis_agent")
        self.assertEqual(node_dict["node_id"], "test_node_id")
        self.assertEqual(node_dict["confidence"], 0.75)
        self.assertEqual(node_dict["metadata"], {"source": "experiment"})
        self.assertEqual(node_dict["parent_ids"], ["parent_id"])
        self.assertEqual(node_dict["child_ids"], ["child_id"])
        self.assertEqual(node_dict["relationships"], {"parent_id": "derives_from", "child_id": "supports"})
        self.assertEqual(node_dict["schema_version"], "1.0")
    
    def test_from_dict(self):
        """Test creating a node from a dictionary."""
        # Create a dictionary representation
        node_dict = {
            "thought_type": "inference",
            "content": {"inference": "Based on the evidence, we can infer..."},
            "author_agent_id": "inference_agent",
            "node_id": "inference_node_id",
            "timestamp": 1625097600,
            "confidence": 0.9,
            "metadata": {"reasoning": "deductive"},
            "parent_ids": ["evidence_node_1", "evidence_node_2"],
            "child_ids": ["conclusion_node"],
            "relationships": {
                "evidence_node_1": "supports",
                "evidence_node_2": "supports",
                "conclusion_node": "derives_from"
            },
            "schema_version": "1.0"
        }
        
        # Create a node from the dictionary
        node = ChainNode.from_dict(node_dict)
        
        # Check that all fields were set correctly
        self.assertEqual(node.thought_type, ThoughtType.INFERENCE)
        self.assertEqual(node.content, {"inference": "Based on the evidence, we can infer..."})
        self.assertEqual(node.author_agent_id, "inference_agent")
        self.assertEqual(node.node_id, "inference_node_id")
        self.assertEqual(node.timestamp, 1625097600)
        self.assertEqual(node.confidence, 0.9)
        self.assertEqual(node.metadata, {"reasoning": "deductive"})
        self.assertEqual(node.parent_ids, {"evidence_node_1", "evidence_node_2"})
        self.assertEqual(node.child_ids, {"conclusion_node"})
        self.assertEqual(node.relationships["evidence_node_1"], RelationshipType.SUPPORTS)
        self.assertEqual(node.relationships["evidence_node_2"], RelationshipType.SUPPORTS)
        self.assertEqual(node.relationships["conclusion_node"], RelationshipType.DERIVES_FROM)
        self.assertEqual(node.schema_version, "1.0")
    
    def test_serialization_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        # Create a complex node
        original_node = ChainNode(
            thought_type=ThoughtType.ARGUMENT,
            content={"argument": "The main argument is...", "supporting_points": ["point1", "point2"]},
            author_agent_id="argument_agent",
            node_id="argument_node_id",
            confidence=0.85,
            metadata={"style": "persuasive", "audience": "technical"}
        )
        original_node.add_parent("premise_node", RelationshipType.DERIVES_FROM)
        original_node.add_child("conclusion_node", RelationshipType.SUPPORTS)
        
        # Convert to dictionary
        node_dict = original_node.to_dict()
        
        # Convert back to a node
        recreated_node = ChainNode.from_dict(node_dict)
        
        # Check that the recreated node matches the original
        self.assertEqual(recreated_node.thought_type, original_node.thought_type)
        self.assertEqual(recreated_node.content, original_node.content)
        self.assertEqual(recreated_node.author_agent_id, original_node.author_agent_id)
        self.assertEqual(recreated_node.node_id, original_node.node_id)
        self.assertEqual(recreated_node.confidence, original_node.confidence)
        self.assertEqual(recreated_node.metadata, original_node.metadata)
        self.assertEqual(recreated_node.parent_ids, original_node.parent_ids)
        self.assertEqual(recreated_node.child_ids, original_node.child_ids)
        
        # Check relationships
        for node_id, relationship in original_node.relationships.items():
            self.assertEqual(recreated_node.relationships[node_id], relationship)
    
    def test_get_relationship_to(self):
        """Test getting the relationship to another node."""
        # Add a parent and child with different relationships
        parent_id = "parent_node"
        child_id = "child_node"
        parent_relationship = RelationshipType.DERIVES_FROM
        child_relationship = RelationshipType.SUPPORTS
        
        self.node.add_parent(parent_id, parent_relationship)
        self.node.add_child(child_id, child_relationship)
        
        # Check relationships
        self.assertEqual(self.node.get_relationship_to(parent_id), parent_relationship)
        self.assertEqual(self.node.get_relationship_to(child_id), child_relationship)
        
        # Check non-existent relationship
        self.assertIsNone(self.node.get_relationship_to("nonexistent_node"))
    
    def test_is_parent_of(self):
        """Test checking if a node is a parent of another."""
        child_id = "child_node"
        self.node.add_child(child_id, RelationshipType.SUPPORTS)
        
        # The node should be a parent of the child
        self.assertTrue(self.node.is_parent_of(child_id))
        
        # The node should not be a parent of a non-existent node
        self.assertFalse(self.node.is_parent_of("nonexistent_node"))
    
    def test_is_child_of(self):
        """Test checking if a node is a child of another."""
        parent_id = "parent_node"
        self.node.add_parent(parent_id, RelationshipType.DERIVES_FROM)
        
        # The node should be a child of the parent
        self.assertTrue(self.node.is_child_of(parent_id))
        
        # The node should not be a child of a non-existent node
        self.assertFalse(self.node.is_child_of("nonexistent_node"))
    
    def test_update_content(self):
        """Test updating the content of a node."""
        original_content = self.node.content
        new_content = {"text": "Updated observation", "additional_info": "More details"}
        
        # Update the content
        self.node.update_content(new_content)
        
        # Check that the content was updated
        self.assertEqual(self.node.content, new_content)
        self.assertNotEqual(self.node.content, original_content)
        
        # Try updating with invalid content (not a dict)
        with self.assertRaises(ValueError):
            self.node.update_content("invalid_content")
    
    def test_update_confidence(self):
        """Test updating the confidence of a node."""
        # Node starts with no confidence
        self.assertIsNone(self.node.confidence)
        
        # Update confidence
        new_confidence = 0.75
        self.node.update_confidence(new_confidence)
        
        # Check that confidence was updated
        self.assertEqual(self.node.confidence, new_confidence)
        
        # Try updating with invalid confidence
        with self.assertRaises(ValueError):
            self.node.update_confidence(1.5)
        with self.assertRaises(ValueError):
            self.node.update_confidence(-0.1)


if __name__ == "__main__":
    unittest.main()
