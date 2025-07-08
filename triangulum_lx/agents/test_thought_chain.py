"""
Test Thought Chain for Triangulum Agentic System Testing

This module provides a simple thought chain implementation for testing purposes.
"""

import uuid
import time
from typing import Dict, List, Any, Optional


class ThoughtNode:
    """A node in a thought chain representing a single step in the reasoning process."""
    
    def __init__(
        self,
        content: Any,
        thought_type: str = "general",
        agent_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None
    ):
        """Initialize a thought node."""
        self.node_id = node_id or str(uuid.uuid4())
        self.content = content
        self.thought_type = thought_type
        self.agent_id = agent_id
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}
        self.children: List[str] = []  # IDs of child nodes
        self.parent_id: Optional[str] = None  # ID of parent node
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "thought_type": self.thought_type,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "children": self.children,
            "parent_id": self.parent_id
        }


class ThoughtChain:
    """A chain of thoughts representing the reasoning process."""
    
    def __init__(
        self,
        chain_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a thought chain."""
        self.chain_id = chain_id or str(uuid.uuid4())
        self.name = name or f"Chain-{self.chain_id[:8]}"
        self.metadata = metadata or {}
        self.nodes: Dict[str, ThoughtNode] = {}  # Map of node ID to node
        self.root_id: Optional[str] = None  # ID of the root node
        self.last_node_id: Optional[str] = None  # ID of the most recently added node
        self.creation_time = time.time()
        self.last_update_time = self.creation_time
    
    def add_thought(
        self,
        content: Any,
        thought_type: str = "general",
        agent_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a thought to the chain.
        
        Args:
            content: The content of the thought
            thought_type: The type of thought
            agent_id: ID of the agent that generated the thought
            parent_id: ID of the parent thought
            metadata: Additional metadata for the thought
            
        Returns:
            The ID of the newly created thought node
        """
        # Create a new thought node
        node = ThoughtNode(
            content=content,
            thought_type=thought_type,
            agent_id=agent_id,
            metadata=metadata
        )
        
        # Determine parent node
        if parent_id is None:
            if self.root_id is None:
                # This is the first node in the chain
                self.root_id = node.node_id
            else:
                # No parent specified, use the last node as parent
                parent_id = self.last_node_id
        
        # Set parent-child relationship
        if parent_id is not None and parent_id in self.nodes:
            node.parent_id = parent_id
            self.nodes[parent_id].children.append(node.node_id)
        
        # Add the node to the chain
        self.nodes[node.node_id] = node
        
        # Update last node
        self.last_node_id = node.node_id
        
        # Update chain metadata
        self.last_update_time = time.time()
        
        return node.node_id
    
    def get_node(self, node_id: str) -> Optional[ThoughtNode]:
        """Get a thought node by ID."""
        return self.nodes.get(node_id)
    
    def get_root_node(self) -> Optional[ThoughtNode]:
        """Get the root thought node."""
        if self.root_id:
            return self.nodes.get(self.root_id)
        return None
    
    def get_last_node(self) -> Optional[ThoughtNode]:
        """Get the most recently added thought node."""
        if self.last_node_id:
            return self.nodes.get(self.last_node_id)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the thought chain to a dictionary representation."""
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "metadata": self.metadata,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "root_id": self.root_id,
            "last_node_id": self.last_node_id,
            "creation_time": self.creation_time,
            "last_update_time": self.last_update_time
        }


class ThoughtChainManager:
    """Manager for creating and tracking thought chains."""
    
    def __init__(self):
        """Initialize the thought chain manager."""
        self.chains: Dict[str, ThoughtChain] = {}
    
    def create_chain(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ThoughtChain:
        """Create a new thought chain."""
        chain = ThoughtChain(name=name, metadata=metadata)
        self.chains[chain.chain_id] = chain
        return chain
    
    def get_chain(self, chain_id: str) -> Optional[ThoughtChain]:
        """Get a thought chain by ID."""
        return self.chains.get(chain_id)
    
    def list_chains(self) -> List[Dict[str, Any]]:
        """List all thought chains with basic information."""
        return [
            {
                "chain_id": chain.chain_id,
                "name": chain.name,
                "node_count": len(chain.nodes),
                "creation_time": chain.creation_time,
                "last_update_time": chain.last_update_time
            }
            for chain in self.chains.values()
        ]
