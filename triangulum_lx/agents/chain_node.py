"""
Chain Node - Core component of the Thought-Chaining Mechanism.

This module defines the ChainNode class, which represents individual reasoning steps
within a thought chain. Nodes can be connected to form complex reasoning chains that
enable agents to collaboratively build on each other's thoughts in a structured way.
"""

import uuid
import time
import enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set, Union


class ThoughtType(enum.Enum):
    """Types of thoughts that can be represented in a chain node."""
    
    OBSERVATION = "observation"       # Direct observation from data or context
    HYPOTHESIS = "hypothesis"         # Proposed explanation or idea
    EVIDENCE = "evidence"             # Supporting information for a hypothesis
    INFERENCE = "inference"           # Logical conclusion derived from evidence or other thoughts
    QUESTION = "question"             # Question or inquiry that requires investigation
    ANSWER = "answer"                 # Response to a question
    ARGUMENT = "argument"             # Logical reasoning connecting thoughts
    COUNTERARGUMENT = "counterargument"  # Opposing argument or refutation
    ACTION = "action"                 # Suggested action or step to take
    CONCLUSION = "conclusion"         # Final determination or outcome
    REFLECTION = "reflection"         # Meta-cognitive thought about the reasoning process
    CONTEXT = "context"               # Background information or context


class RelationshipType(enum.Enum):
    """Types of relationships between chain nodes."""
    
    SUPPORTS = "supports"             # Node supports or provides evidence for parent
    CONTRADICTS = "contradicts"       # Node contradicts or refutes parent
    EXTENDS = "extends"               # Node extends or elaborates on parent
    QUESTIONS = "questions"           # Node questions or challenges parent
    ANSWERS = "answers"               # Node answers a question in parent
    DERIVES_FROM = "derives_from"     # Node is derived from or follows from parent
    ALTERNATIVE_TO = "alternative_to"  # Node provides alternative to parent
    SPECIALIZES = "specializes"       # Node specializes or narrows parent
    GENERALIZES = "generalizes"       # Node generalizes or broadens parent
    SEQUENCE = "sequence"             # Node follows parent in a sequence
    PARALLEL = "parallel"             # Node runs parallel to parent (concurrent thought)


@dataclass
class ChainNode:
    """
    Represents a single node in a thought chain.
    
    A ChainNode encapsulates a single reasoning step or thought within a broader
    thought chain. It includes metadata about the thought, its relationships to other
    nodes, and the agent that produced it.
    """
    
    # Core fields
    thought_type: ThoughtType
    content: Dict[str, Any]
    author_agent_id: str
    
    # Optional fields with defaults
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Relationship fields (initialized empty)
    parent_ids: Set[str] = field(default_factory=set)
    child_ids: Set[str] = field(default_factory=set)
    relationships: Dict[str, RelationshipType] = field(default_factory=dict)
    
    # Versioning
    schema_version: str = "1.0"
    
    def __post_init__(self):
        """Validate the node after initialization."""
        self.validate()
    
    def validate(self) -> bool:
        """
        Validate the node structure and content.
        
        Returns:
            bool: True if the node is valid, raises ValueError otherwise
        """
        # Check required fields
        if not isinstance(self.thought_type, ThoughtType):
            raise ValueError(f"thought_type must be a ThoughtType enum, got {type(self.thought_type)}")
        
        if not isinstance(self.content, dict):
            raise ValueError(f"content must be a dictionary, got {type(self.content)}")
        
        if not self.author_agent_id:
            raise ValueError("author_agent_id is required")
        
        # Validate confidence if provided
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        # Validate relationships
        for node_id, relationship in self.relationships.items():
            if not isinstance(relationship, RelationshipType):
                raise ValueError(f"relationship must be a RelationshipType enum, got {type(relationship)}")
            
            # Ensure the node_id is in either parent_ids or child_ids
            if node_id not in self.parent_ids and node_id not in self.child_ids:
                raise ValueError(f"relationship target {node_id} must be in parent_ids or child_ids")
        
        return True
    
    def add_parent(self, parent_id: str, relationship: RelationshipType) -> None:
        """
        Add a parent node to this node.
        
        Args:
            parent_id: ID of the parent node
            relationship: Type of relationship to the parent
        """
        self.parent_ids.add(parent_id)
        self.relationships[parent_id] = relationship
    
    def add_child(self, child_id: str, relationship: RelationshipType) -> None:
        """
        Add a child node to this node.
        
        Args:
            child_id: ID of the child node
            relationship: Type of relationship to the child
        """
        self.child_ids.add(child_id)
        self.relationships[child_id] = relationship
    
    def remove_parent(self, parent_id: str) -> None:
        """
        Remove a parent node from this node.
        
        Args:
            parent_id: ID of the parent node to remove
        """
        if parent_id in self.parent_ids:
            self.parent_ids.remove(parent_id)
            if parent_id in self.relationships:
                del self.relationships[parent_id]
    
    def remove_child(self, child_id: str) -> None:
        """
        Remove a child node from this node.
        
        Args:
            child_id: ID of the child node to remove
        """
        if child_id in self.child_ids:
            self.child_ids.remove(child_id)
            if child_id in self.relationships:
                del self.relationships[child_id]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the node to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the node
        """
        result = asdict(self)
        
        # Convert Enum to string for JSON serialization
        result["thought_type"] = self.thought_type.value
        
        # Convert sets to lists for JSON serialization
        result["parent_ids"] = list(self.parent_ids)
        result["child_ids"] = list(self.child_ids)
        
        # Convert relationship Enums to strings
        result["relationships"] = {
            k: v.value for k, v in self.relationships.items()
        }
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChainNode':
        """
        Create a node from a dictionary representation.
        
        Args:
            data: Dictionary representation of the node
            
        Returns:
            ChainNode: Instantiated node object
        """
        # Handle thought_type conversion
        if isinstance(data.get("thought_type"), str):
            data["thought_type"] = ThoughtType(data["thought_type"])
        
        # Convert relationship values from strings to enums
        relationships = data.get("relationships", {})
        converted_relationships = {}
        for k, v in relationships.items():
            if isinstance(v, str):
                converted_relationships[k] = RelationshipType(v)
            else:
                converted_relationships[k] = v
        data["relationships"] = converted_relationships
        
        # Convert parent_ids and child_ids from lists to sets
        if "parent_ids" in data and isinstance(data["parent_ids"], list):
            data["parent_ids"] = set(data["parent_ids"])
        
        if "child_ids" in data and isinstance(data["child_ids"], list):
            data["child_ids"] = set(data["child_ids"])
        
        return cls(**data)
    
    def get_relationship_to(self, node_id: str) -> Optional[RelationshipType]:
        """
        Get the relationship type to another node.
        
        Args:
            node_id: ID of the other node
            
        Returns:
            RelationshipType or None: The relationship type if it exists, None otherwise
        """
        return self.relationships.get(node_id)
    
    def is_parent_of(self, node_id: str) -> bool:
        """
        Check if this node is a parent of the specified node.
        
        Args:
            node_id: ID of the potential child node
            
        Returns:
            bool: True if this node is a parent of the specified node
        """
        return node_id in self.child_ids
    
    def is_child_of(self, node_id: str) -> bool:
        """
        Check if this node is a child of the specified node.
        
        Args:
            node_id: ID of the potential parent node
            
        Returns:
            bool: True if this node is a child of the specified node
        """
        return node_id in self.parent_ids
    
    def update_content(self, content: Dict[str, Any]) -> None:
        """
        Update the content of this node.
        
        Args:
            content: New content for the node
        """
        self.content = content
        self.validate()
    
    def update_confidence(self, confidence: float) -> None:
        """
        Update the confidence score for this node.
        
        Args:
            confidence: New confidence score (0.0 to 1.0)
        """
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {confidence}")
        self.confidence = confidence
