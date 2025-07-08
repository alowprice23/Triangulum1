"""
Thought Chain Manager - Manages creation and extension of thought chains.

This module provides a centralized manager for thought chains, allowing agents to
create, extend, and query thought chains in a collaborative reasoning environment.
"""

import logging
import time
import uuid
import json
import os
import threading
from typing import Dict, List, Optional, Set, Any, Tuple, Callable, Union
from pathlib import Path
from functools import lru_cache
from collections import defaultdict

from triangulum_lx.agents.chain_node import ChainNode, ThoughtType, RelationshipType
from triangulum_lx.agents.thought_chain import ThoughtChain, TraversalOrder
from triangulum_lx.agents.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class ChainBranch:
    """
    Represents a branch within a thought chain.
    
    A branch is a sequence of connected thoughts that form a particular line of reasoning.
    Branches can be created, merged, and compared to track different reasoning paths.
    """
    
    def __init__(self, 
                branch_id: Optional[str] = None, 
                name: Optional[str] = None,
                chain_id: Optional[str] = None,
                root_node_id: Optional[str] = None,
                node_ids: Optional[List[str]] = None,
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a chain branch.
        
        Args:
            branch_id: Unique identifier for the branch
            name: Human-readable name for the branch
            chain_id: ID of the parent chain
            root_node_id: ID of the root node of this branch
            node_ids: List of node IDs in this branch
            metadata: Additional metadata for the branch
        """
        self.branch_id = branch_id or str(uuid.uuid4())
        self.name = name or f"Branch-{self.branch_id[:8]}"
        self.chain_id = chain_id
        self.root_node_id = root_node_id
        self.node_ids = node_ids or []
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = self.created_at
    
    def add_node(self, node_id: str) -> None:
        """
        Add a node to this branch.
        
        Args:
            node_id: ID of the node to add
        """
        if node_id not in self.node_ids:
            self.node_ids.append(node_id)
            self.updated_at = time.time()
    
    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node from this branch.
        
        Args:
            node_id: ID of the node to remove
            
        Returns:
            bool: True if the node was removed, False if it wasn't in the branch
        """
        if node_id in self.node_ids:
            self.node_ids.remove(node_id)
            self.updated_at = time.time()
            return True
        return False
    
    def contains_node(self, node_id: str) -> bool:
        """
        Check if this branch contains a node.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            bool: True if the branch contains the node
        """
        return node_id in self.node_ids
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the branch to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the branch
        """
        return {
            "branch_id": self.branch_id,
            "name": self.name,
            "chain_id": self.chain_id,
            "root_node_id": self.root_node_id,
            "node_ids": self.node_ids,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChainBranch':
        """
        Create a branch from a dictionary representation.
        
        Args:
            data: Dictionary representation of the branch
            
        Returns:
            ChainBranch: Instantiated branch
        """
        return cls(
            branch_id=data.get("branch_id"),
            name=data.get("name"),
            chain_id=data.get("chain_id"),
            root_node_id=data.get("root_node_id"),
            node_ids=data.get("node_ids", []),
            metadata=data.get("metadata", {})
        )


class ReasoningContext:
    """
    Maintains context for a reasoning process within a thought chain.
    
    The reasoning context tracks the current state, assumptions, constraints,
    and other relevant information for a reasoning process, providing continuity
    and coherence in collaborative reasoning.
    """
    
    def __init__(self, 
                context_id: Optional[str] = None,
                name: Optional[str] = None,
                chain_id: Optional[str] = None,
                current_branch_id: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a reasoning context.
        
        Args:
            context_id: Unique identifier for the context
            name: Human-readable name for the context
            chain_id: ID of the associated chain
            current_branch_id: ID of the current active branch
            metadata: Additional metadata for the context
        """
        self.context_id = context_id or str(uuid.uuid4())
        self.name = name or f"Context-{self.context_id[:8]}"
        self.chain_id = chain_id
        self.current_branch_id = current_branch_id
        self.metadata = metadata or {}
        self.state: Dict[str, Any] = {}
        self.assumptions: List[Dict[str, Any]] = []
        self.constraints: List[Dict[str, Any]] = []
        self.goals: List[Dict[str, Any]] = []
        self.created_at = time.time()
        self.updated_at = self.created_at
    
    def update_state(self, key: str, value: Any) -> None:
        """
        Update a state variable in the context.
        
        Args:
            key: Key of the state variable
            value: New value for the state variable
        """
        self.state[key] = value
        self.updated_at = time.time()
    
    def remove_state(self, key: str) -> bool:
        """
        Remove a state variable from the context.
        
        Args:
            key: Key of the state variable to remove
            
        Returns:
            bool: True if the variable was removed, False if it wasn't in the state
        """
        if key in self.state:
            del self.state[key]
            self.updated_at = time.time()
            return True
        return False
    
    def add_assumption(self, assumption: Dict[str, Any]) -> None:
        """
        Add an assumption to the context.
        
        Args:
            assumption: Dictionary describing the assumption
        """
        self.assumptions.append(assumption)
        self.updated_at = time.time()
    
    def add_constraint(self, constraint: Dict[str, Any]) -> None:
        """
        Add a constraint to the context.
        
        Args:
            constraint: Dictionary describing the constraint
        """
        self.constraints.append(constraint)
        self.updated_at = time.time()
    
    def add_goal(self, goal: Dict[str, Any]) -> None:
        """
        Add a goal to the context.
        
        Args:
            goal: Dictionary describing the goal
        """
        self.goals.append(goal)
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the context to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the context
        """
        return {
            "context_id": self.context_id,
            "name": self.name,
            "chain_id": self.chain_id,
            "current_branch_id": self.current_branch_id,
            "metadata": self.metadata,
            "state": self.state,
            "assumptions": self.assumptions,
            "constraints": self.constraints,
            "goals": self.goals,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReasoningContext':
        """
        Create a context from a dictionary representation.
        
        Args:
            data: Dictionary representation of the context
            
        Returns:
            ReasoningContext: Instantiated context
        """
        context = cls(
            context_id=data.get("context_id"),
            name=data.get("name"),
            chain_id=data.get("chain_id"),
            current_branch_id=data.get("current_branch_id"),
            metadata=data.get("metadata", {})
        )
        
        context.state = data.get("state", {})
        context.assumptions = data.get("assumptions", [])
        context.constraints = data.get("constraints", [])
        context.goals = data.get("goals", [])
        context.created_at = data.get("created_at", time.time())
        context.updated_at = data.get("updated_at", time.time())
        
        return context


class ThoughtChainManager:
    """
    Manages creation, extension, and querying of thought chains.
    
    This class serves as the main interface for agents to interact with thought chains,
    providing methods to create new chains, add thoughts to existing chains, and find
    relevant thoughts and chains. It supports advanced features like branching, merging,
    and context tracking for sophisticated reasoning workflows.
    """
    
    def __init__(self, 
                storage_dir: Optional[str] = None,
                enable_caching: bool = True,
                cache_size: int = 128,
                memory_manager: Optional[MemoryManager] = None):
        """
        Initialize the thought chain manager.
        
        Args:
            storage_dir: Optional directory for storing thought chains
            enable_caching: Whether to enable caching for performance optimization
            cache_size: Size of the LRU cache for frequently accessed nodes
            memory_manager: Optional memory manager for token-efficient retrieval
        """
        self.chains: Dict[str, ThoughtChain] = {}
        self.chains_by_name: Dict[str, str] = {}  # name -> chain_id
        self.agents_active_chains: Dict[str, Set[str]] = {}  # agent_id -> set of chain_ids
        self.storage_dir = storage_dir
        
        # Branch management
        self.branches: Dict[str, ChainBranch] = {}  # branch_id -> ChainBranch
        self.chain_branches: Dict[str, Set[str]] = {}  # chain_id -> set of branch_ids
        
        # Reasoning context tracking
        self.contexts: Dict[str, ReasoningContext] = {}  # context_id -> ReasoningContext
        self.chain_contexts: Dict[str, Set[str]] = {}  # chain_id -> set of context_ids
        
        # Performance optimization
        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self._node_cache: Dict[str, Dict[str, ChainNode]] = {}  # chain_id -> (node_id -> ChainNode)
        self._access_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))  # chain_id -> (node_id -> count)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Memory manager integration
        self.memory_manager = memory_manager or MemoryManager()
        
        if storage_dir:
            # Create storage directory if it doesn't exist
            Path(storage_dir).mkdir(parents=True, exist_ok=True)
    
    def create_chain(self, 
                    name: str, 
                    description: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    creator_agent_id: Optional[str] = None,
                    create_default_branch: bool = True,
                    create_context: bool = True) -> str:
        """
        Create a new thought chain.
        
        Args:
            name: Name of the chain
            description: Optional description of the chain
            metadata: Optional metadata for the chain
            creator_agent_id: ID of the agent creating the chain
            create_default_branch: Whether to create a default branch
            create_context: Whether to create a default reasoning context
            
        Returns:
            str: ID of the newly created chain
            
        Raises:
            ValueError: If a chain with the given name already exists
        """
        with self._lock:
            if name in self.chains_by_name:
                raise ValueError(f"Chain with name '{name}' already exists")
            
            # Create a new chain
            chain = ThoughtChain(
                name=name,
                description=description or "",
                metadata=metadata or {}
            )
            
            chain_id = chain.chain_id
            
            # Store the chain
            self.chains[chain_id] = chain
            self.chains_by_name[name] = chain_id
            
            # Track agent's active chains
            if creator_agent_id:
                if creator_agent_id not in self.agents_active_chains:
                    self.agents_active_chains[creator_agent_id] = set()
                self.agents_active_chains[creator_agent_id].add(chain_id)
            
            # Initialize cache for this chain
            if self.enable_caching:
                self._node_cache[chain_id] = {}
            
            # Create a default branch if requested
            if create_default_branch:
                branch = ChainBranch(
                    name="main",
                    chain_id=chain_id,
                    metadata={"default": True, "creator_agent_id": creator_agent_id}
                )
                
                self.branches[branch.branch_id] = branch
                
                if chain_id not in self.chain_branches:
                    self.chain_branches[chain_id] = set()
                
                self.chain_branches[chain_id].add(branch.branch_id)
            
            # Create a default reasoning context if requested
            if create_context:
                context = ReasoningContext(
                    name="main",
                    chain_id=chain_id,
                    current_branch_id=branch.branch_id if create_default_branch else None,
                    metadata={"default": True, "creator_agent_id": creator_agent_id}
                )
                
                self.contexts[context.context_id] = context
                
                if chain_id not in self.chain_contexts:
                    self.chain_contexts[chain_id] = set()
                
                self.chain_contexts[chain_id].add(context.context_id)
            
            logger.info(f"Created new thought chain: {name} (ID: {chain_id})")
            
            # Save the chain if storage is enabled
            if self.storage_dir:
                self._save_chain(chain)
                
                # Save branches and contexts
                if create_default_branch or create_context:
                    self._save_chain_metadata(chain_id)
            
            return chain_id
    
    def add_thought(self, 
                   chain_id: str,
                   thought_type: ThoughtType,
                   content: Dict[str, Any],
                   author_agent_id: str,
                   parent_id: Optional[str] = None,
                   relationship: Optional[RelationshipType] = None,
                   confidence: Optional[float] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   branch_id: Optional[str] = None,
                   context_id: Optional[str] = None) -> str:
        """
        Add a thought to an existing chain.
        
        Args:
            chain_id: ID of the chain to add the thought to
            thought_type: Type of thought
            content: Content of the thought
            author_agent_id: ID of the agent creating the thought
            parent_id: Optional ID of the parent thought
            relationship: Relationship to the parent thought (required if parent_id is provided)
            confidence: Optional confidence level (0.0 to 1.0)
            metadata: Optional metadata for the thought
            branch_id: Optional ID of the branch to add the thought to
            context_id: Optional ID of the reasoning context for this thought
            
        Returns:
            str: ID of the newly created thought node
            
        Raises:
            ValueError: If the chain does not exist or if parent_id is provided but relationship is not
        """
        with self._lock:
            # Check if the chain exists
            if chain_id not in self.chains:
                raise ValueError(f"Chain with ID '{chain_id}' does not exist")
            
            # Check if parent_id is provided but relationship is not
            if parent_id and not relationship:
                raise ValueError("Relationship must be provided when adding a thought with a parent")
            
            # Get the chain
            chain = self.chains[chain_id]
            
            # If branch_id is not provided but context_id is, use the context's current branch
            if not branch_id and context_id and context_id in self.contexts:
                branch_id = self.contexts[context_id].current_branch_id
            
            # If branch_id is provided, check if it exists and belongs to this chain
            if branch_id:
                if branch_id not in self.branches:
                    raise ValueError(f"Branch with ID '{branch_id}' does not exist")
                if self.branches[branch_id].chain_id != chain_id:
                    raise ValueError(f"Branch '{branch_id}' does not belong to chain '{chain_id}'")
            
            # If no branch is specified, try to find the default branch for this chain
            if not branch_id and chain_id in self.chain_branches:
                for branch_id_candidate in self.chain_branches[chain_id]:
                    branch = self.branches[branch_id_candidate]
                    if branch.metadata.get("default", False):
                        branch_id = branch_id_candidate
                        break
            
            # Create a new thought node
            node = ChainNode(
                thought_type=thought_type,
                content=content,
                author_agent_id=author_agent_id,
                confidence=confidence,
                metadata=metadata or {}
            )
            
            # Add additional metadata for context tracking
            if branch_id:
                node.metadata["branch_id"] = branch_id
            if context_id:
                node.metadata["context_id"] = context_id
            
            # Add the node to the chain
            node_id = chain.add_node(node, parent_id=parent_id, relationship=relationship)
            
            # Add to cache if enabled
            if self.enable_caching and chain_id in self._node_cache:
                self._node_cache[chain_id][node_id] = node
                self._access_counts[chain_id][node_id] += 1
            
            # Add to branch if specified
            if branch_id:
                self.branches[branch_id].add_node(node_id)
                
                # If this is the first node in the branch and it has no parent, set it as the root
                if not self.branches[branch_id].root_node_id and not parent_id:
                    self.branches[branch_id].root_node_id = node_id
            
            # Update context if specified
            if context_id and context_id in self.contexts:
                # Update context state with latest thought
                self.contexts[context_id].update_state("latest_thought_id", node_id)
                self.contexts[context_id].update_state("latest_thought_type", thought_type.value)
                self.contexts[context_id].update_state("latest_author", author_agent_id)
            
            # Track agent's active chains
            if author_agent_id not in self.agents_active_chains:
                self.agents_active_chains[author_agent_id] = set()
            self.agents_active_chains[author_agent_id].add(chain_id)
            
            logger.info(f"Added thought to chain {chain.name} (ID: {chain_id}): {thought_type.value} by {author_agent_id}")
            
            # Save the chain if storage is enabled
            if self.storage_dir:
                self._save_chain(chain)
                
                # Save branch and context if specified
                if branch_id or context_id:
                    self._save_chain_metadata(chain_id)
            
            return node_id
    
    def get_chain(self, chain_id: str) -> Optional[ThoughtChain]:
        """
        Get a thought chain by ID.
        
        Args:
            chain_id: ID of the chain to get
            
        Returns:
            ThoughtChain or None: The chain if it exists, None otherwise
        """
        return self.chains.get(chain_id)
    
    def get_chain_by_name(self, name: str) -> Optional[ThoughtChain]:
        """
        Get a thought chain by name.
        
        Args:
            name: Name of the chain to get
            
        Returns:
            ThoughtChain or None: The chain if it exists, None otherwise
        """
        chain_id = self.chains_by_name.get(name)
        if chain_id:
            return self.chains.get(chain_id)
        return None
    
    def get_thought(self, chain_id: str, node_id: str) -> Optional[ChainNode]:
        """
        Get a thought node from a chain.
        
        Args:
            chain_id: ID of the chain
            node_id: ID of the thought node
            
        Returns:
            ChainNode or None: The thought node if it exists, None otherwise
        """
        with self._lock:
            # Check cache first if enabled
            if self.enable_caching and chain_id in self._node_cache and node_id in self._node_cache[chain_id]:
                # Update access count
                self._access_counts[chain_id][node_id] += 1
                return self._node_cache[chain_id][node_id]
            
            # Get from chain
            chain = self.get_chain(chain_id)
            if chain:
                node = chain.get_node(node_id)
                
                # Add to cache if enabled
                if self.enable_caching and node and chain_id in self._node_cache:
                    # Check if cache is full
                    if len(self._node_cache[chain_id]) >= self.cache_size:
                        # Evict least recently used node
                        self._evict_lru_node(chain_id)
                    
                    self._node_cache[chain_id][node_id] = node
                    self._access_counts[chain_id][node_id] = 1
                
                return node
            
            return None
    
    def list_chains(self) -> List[Dict[str, Any]]:
        """
        List all thought chains.
        
        Returns:
            List[Dict[str, Any]]: List of chain metadata
        """
        return [
            {
                "chain_id": chain.chain_id,
                "name": chain.name,
                "description": chain.description,
                "node_count": len(chain),
                "created_at": chain.created_at,
                "updated_at": chain.updated_at
            }
            for chain in self.chains.values()
        ]
    
    def get_agent_chains(self, agent_id: str) -> List[ThoughtChain]:
        """
        Get all chains that an agent has contributed to.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List[ThoughtChain]: List of chains the agent has contributed to
        """
        if agent_id not in self.agents_active_chains:
            return []
        
        return [
            self.chains[chain_id]
            for chain_id in self.agents_active_chains[agent_id]
            if chain_id in self.chains
        ]
    
    def search_thoughts(self, 
                       query: str, 
                       chain_ids: Optional[List[str]] = None,
                       thought_type: Optional[ThoughtType] = None,
                       author_agent_id: Optional[str] = None,
                       min_confidence: Optional[float] = None) -> List[Tuple[str, ChainNode]]:
        """
        Search for thoughts across all chains or specified chains.
        
        Args:
            query: Query string to search for
            chain_ids: Optional list of chain IDs to search in (if None, search all chains)
            thought_type: Optional thought type to filter by
            author_agent_id: Optional author agent ID to filter by
            min_confidence: Optional minimum confidence level to filter by
            
        Returns:
            List[Tuple[str, ChainNode]]: List of (chain_id, node) tuples matching the query
        """
        results = []
        
        # Determine which chains to search
        chains_to_search = []
        if chain_ids:
            chains_to_search = [self.chains[cid] for cid in chain_ids if cid in self.chains]
        else:
            chains_to_search = list(self.chains.values())
        
        # Search each chain
        for chain in chains_to_search:
            for node in chain:
                # Check if the node matches all criteria
                matches = True
                
                # Check thought type
                if thought_type and node.thought_type != thought_type:
                    matches = False
                
                # Check author
                if author_agent_id and node.author_agent_id != author_agent_id:
                    matches = False
                
                # Check confidence
                if min_confidence is not None and (node.confidence is None or node.confidence < min_confidence):
                    matches = False
                
                # Check query string - simplified approach that will definitely work
                if query:
                    # Convert to lowercase for case-insensitive matching
                    query_lower = query.lower()
                    
                    # Get a string representation of the entire content
                    content_str = str(node.content).lower()
                    
                    # Directly check if query is in the string representation
                    if query_lower not in content_str:
                        matches = False
                
                # Add to results if all criteria match
                if matches:
                    results.append((chain.chain_id, node))
        
        return results
    
    def find_related_thoughts(self, 
                            chain_id: str, 
                            node_id: str,
                            max_distance: int = 2,
                            include_ancestors: bool = True,
                            include_descendants: bool = True) -> List[ChainNode]:
        """
        Find thoughts related to a specific thought.
        
        Args:
            chain_id: ID of the chain
            node_id: ID of the thought node
            max_distance: Maximum distance (number of hops) to consider
            include_ancestors: Whether to include ancestor nodes
            include_descendants: Whether to include descendant nodes
            
        Returns:
            List[ChainNode]: List of related thoughts
        """
        chain = self.get_chain(chain_id)
        if not chain or node_id not in chain:
            return []
        
        # Get the starting node
        start_node = chain.get_node(node_id)
        if not start_node:
            return []
        
        # Find related nodes
        related_nodes = []
        visited = {node_id}
        queue = [(node_id, 0)]  # (node_id, distance)
        
        while queue:
            current_id, distance = queue.pop(0)
            
            if distance > max_distance:
                continue
            
            current_node = chain.get_node(current_id)
            if not current_node:
                continue
            
            # Skip the starting node
            if current_id != node_id:
                related_nodes.append(current_node)
            
            # Add parents to queue if including ancestors
            if include_ancestors:
                for parent_id in current_node.parent_ids:
                    if parent_id not in visited and parent_id in chain:
                        visited.add(parent_id)
                        queue.append((parent_id, distance + 1))
            
            # Add children to queue if including descendants
            if include_descendants:
                for child_id in current_node.child_ids:
                    if child_id not in visited and child_id in chain:
                        visited.add(child_id)
                        queue.append((child_id, distance + 1))
        
        return related_nodes
    
    def merge_chains(self, 
                   source_chain_id: str, 
                   target_chain_id: str,
                   connect_roots: bool = False,
                   root_relationship: Optional[RelationshipType] = None) -> bool:
        """
        Merge one chain into another.
        
        Args:
            source_chain_id: ID of the source chain to merge from
            target_chain_id: ID of the target chain to merge into
            connect_roots: Whether to connect the source chain's roots to the target chain's leaves
            root_relationship: Relationship type to use when connecting roots (required if connect_roots is True)
            
        Returns:
            bool: True if the merge was successful, False otherwise
            
        Raises:
            ValueError: If either chain does not exist or if connect_roots is True but root_relationship is None
        """
        # Check if both chains exist
        if source_chain_id not in self.chains:
            raise ValueError(f"Source chain with ID '{source_chain_id}' does not exist")
        
        if target_chain_id not in self.chains:
            raise ValueError(f"Target chain with ID '{target_chain_id}' does not exist")
        
        # Check if connect_roots is True but root_relationship is None
        if connect_roots and not root_relationship:
            raise ValueError("root_relationship must be provided when connect_roots is True")
        
        # Get the chains
        source_chain = self.chains[source_chain_id]
        target_chain = self.chains[target_chain_id]
        
        # Merge the source chain into the target chain
        try:
            target_chain.merge(source_chain, connect_roots=connect_roots, root_relationship=root_relationship)
            
            # Save the target chain if storage is enabled
            if self.storage_dir:
                self._save_chain(target_chain)
            
            # Update agents active chains
            for agent_id, chain_ids in self.agents_active_chains.items():
                if source_chain_id in chain_ids:
                    chain_ids.add(target_chain_id)
            
            logger.info(f"Merged chain {source_chain.name} into {target_chain.name}")
            
            # Optionally delete the source chain after merging
            # self.delete_chain(source_chain_id)
            
            return True
        except Exception as e:
            logger.error(f"Error merging chains: {e}")
            return False
    
    def delete_chain(self, chain_id: str) -> bool:
        """
        Delete a thought chain.
        
        Args:
            chain_id: ID of the chain to delete
            
        Returns:
            bool: True if the chain was deleted, False if it didn't exist
        """
        if chain_id not in self.chains:
            return False
        
        # Get the chain before removing it
        chain = self.chains[chain_id]
        
        # Remove the chain
        del self.chains[chain_id]
        
        # Remove the chain from chains_by_name
        for name, cid in list(self.chains_by_name.items()):
            if cid == chain_id:
                del self.chains_by_name[name]
        
        # Remove the chain from agents_active_chains
        for agent_id, chain_ids in self.agents_active_chains.items():
            if chain_id in chain_ids:
                chain_ids.remove(chain_id)
        
        # Delete the chain file if storage is enabled
        if self.storage_dir:
            chain_file = Path(self.storage_dir) / f"{chain_id}.json"
            if chain_file.exists():
                chain_file.unlink()
        
        logger.info(f"Deleted thought chain: {chain.name} (ID: {chain_id})")
        
        return True
    
    def validate_all_chains(self) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate all thought chains.
        
        Returns:
            Dict[str, Tuple[bool, List[str]]]: Dictionary mapping chain IDs to (is_valid, errors) tuples
        """
        results = {}
        
        for chain_id, chain in self.chains.items():
            is_valid, errors = chain.validate()
            results[chain_id] = (is_valid, errors)
            
            if not is_valid:
                logger.warning(f"Chain {chain.name} (ID: {chain_id}) has validation errors: {errors}")
        
        return results
    
    def load_chains(self) -> int:
        """
        Load thought chains from storage.
        
        Returns:
            int: Number of chains loaded
        """
        if not self.storage_dir:
            logger.warning("Cannot load chains: storage_dir not specified")
            return 0
        
        storage_path = Path(self.storage_dir)
        if not storage_path.exists():
            logger.warning(f"Storage directory does not exist: {self.storage_dir}")
            return 0
        
        # Clear existing chains
        self.chains.clear()
        self.chains_by_name.clear()
        self.agents_active_chains.clear()
        
        # Load chains from storage
        count = 0
        # Only load files that are chain files (not metadata files)
        for chain_file in storage_path.glob("*.json"):
            # Skip metadata files
            if chain_file.name.endswith("_metadata.json"):
                continue
                
            try:
                # Load the chain from file
                with open(chain_file, "r") as f:
                    chain_data = json.load(f)
                
                # Create a ThoughtChain from the data
                chain = ThoughtChain.from_dict(chain_data)
                
                # Store the chain
                self.chains[chain.chain_id] = chain
                self.chains_by_name[chain.name] = chain.chain_id
                
                # Update agents active chains
                for node in chain:
                    agent_id = node.author_agent_id
                    if agent_id not in self.agents_active_chains:
                        self.agents_active_chains[agent_id] = set()
                    self.agents_active_chains[agent_id].add(chain.chain_id)
                
                # Load the chain's metadata (branches and contexts)
                self._load_chain_metadata(chain.chain_id)
                
                count += 1
            except Exception as e:
                logger.error(f"Error loading chain from {chain_file}: {e}")
        
        logger.info(f"Loaded {count} thought chains from storage")
        
        return count
    
    def create_branch(self, 
                     chain_id: str,
                     name: str,
                     root_node_id: Optional[str] = None,
                     parent_branch_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     creator_agent_id: Optional[str] = None) -> str:
        """
        Create a new branch in a thought chain.
        
        Args:
            chain_id: ID of the chain to create the branch in
            name: Name of the branch
            root_node_id: Optional ID of the root node for this branch
            parent_branch_id: Optional ID of the parent branch to fork from
            metadata: Optional metadata for the branch
            creator_agent_id: ID of the agent creating the branch
            
        Returns:
            str: ID of the newly created branch
            
        Raises:
            ValueError: If the chain does not exist or if parent_branch_id is provided but doesn't exist
        """
        with self._lock:
            # Check if the chain exists
            if chain_id not in self.chains:
                raise ValueError(f"Chain with ID '{chain_id}' does not exist")
            
            # Get the chain
            chain = self.chains[chain_id]
            
            # Create branch metadata
            branch_metadata = metadata or {}
            if creator_agent_id:
                branch_metadata["creator_agent_id"] = creator_agent_id
            
            # Create a new branch
            branch = ChainBranch(
                name=name,
                chain_id=chain_id,
                root_node_id=root_node_id,
                metadata=branch_metadata
            )
            
            # If parent branch is specified, copy nodes from parent
            if parent_branch_id:
                if parent_branch_id not in self.branches:
                    raise ValueError(f"Parent branch with ID '{parent_branch_id}' does not exist")
                
                parent_branch = self.branches[parent_branch_id]
                
                # Check if parent branch belongs to this chain
                if parent_branch.chain_id != chain_id:
                    raise ValueError(f"Parent branch '{parent_branch_id}' does not belong to chain '{chain_id}'")
                
                # Copy nodes from parent branch
                branch.node_ids = parent_branch.node_ids.copy()
                
                # If no root node specified, use parent's root
                if not branch.root_node_id and parent_branch.root_node_id:
                    branch.root_node_id = parent_branch.root_node_id
            
            # Store the branch
            self.branches[branch.branch_id] = branch
            
            # Associate branch with chain
            if chain_id not in self.chain_branches:
                self.chain_branches[chain_id] = set()
            
            self.chain_branches[chain_id].add(branch.branch_id)
            
            logger.info(f"Created new branch '{name}' (ID: {branch.branch_id}) in chain {chain.name}")
            
            # Save branch metadata if storage is enabled
            if self.storage_dir:
                self._save_chain_metadata(chain_id)
            
            return branch.branch_id
    
    def get_branch(self, branch_id: str) -> Optional[ChainBranch]:
        """
        Get a branch by ID.
        
        Args:
            branch_id: ID of the branch to get
            
        Returns:
            ChainBranch or None: The branch if it exists, None otherwise
        """
        return self.branches.get(branch_id)
    
    def get_chain_branches(self, chain_id: str) -> List[ChainBranch]:
        """
        Get all branches for a chain.
        
        Args:
            chain_id: ID of the chain
            
        Returns:
            List[ChainBranch]: List of branches for the chain
        """
        if chain_id not in self.chain_branches:
            return []
        
        return [
            self.branches[branch_id]
            for branch_id in self.chain_branches[chain_id]
            if branch_id in self.branches
        ]
    
    def merge_branches(self,
                      source_branch_id: str,
                      target_branch_id: str,
                      strategy: str = "union") -> bool:
        """
        Merge one branch into another.
        
        Args:
            source_branch_id: ID of the source branch to merge from
            target_branch_id: ID of the target branch to merge into
            strategy: Merge strategy ("union", "intersection", or "override")
            
        Returns:
            bool: True if the merge was successful, False otherwise
            
        Raises:
            ValueError: If either branch does not exist or if strategy is invalid
        """
        with self._lock:
            # Check if both branches exist
            if source_branch_id not in self.branches:
                raise ValueError(f"Source branch with ID '{source_branch_id}' does not exist")
            
            if target_branch_id not in self.branches:
                raise ValueError(f"Target branch with ID '{target_branch_id}' does not exist")
            
            # Check if branches belong to the same chain
            source_branch = self.branches[source_branch_id]
            target_branch = self.branches[target_branch_id]
            
            if source_branch.chain_id != target_branch.chain_id:
                raise ValueError("Branches must belong to the same chain")
            
            # Apply merge strategy
            if strategy == "union":
                # Combine all nodes from both branches
                for node_id in source_branch.node_ids:
                    if node_id not in target_branch.node_ids:
                        target_branch.add_node(node_id)
            elif strategy == "intersection":
                # Keep only nodes that are in both branches
                target_branch.node_ids = [
                    node_id for node_id in target_branch.node_ids
                    if node_id in source_branch.node_ids
                ]
            elif strategy == "override":
                # Replace target branch nodes with source branch nodes
                target_branch.node_ids = source_branch.node_ids.copy()
                target_branch.root_node_id = source_branch.root_node_id
            else:
                raise ValueError(f"Invalid merge strategy: {strategy}")
            
            # Update timestamp
            target_branch.updated_at = time.time()
            
            logger.info(f"Merged branch {source_branch.name} into {target_branch.name} using strategy '{strategy}'")
            
            # Save branch metadata if storage is enabled
            if self.storage_dir:
                self._save_chain_metadata(target_branch.chain_id)
            
            return True
    
    def delete_branch(self, branch_id: str, delete_nodes: bool = False) -> bool:
        """
        Delete a branch.
        
        Args:
            branch_id: ID of the branch to delete
            delete_nodes: Whether to delete nodes that only exist in this branch
            
        Returns:
            bool: True if the branch was deleted, False if it didn't exist
        """
        with self._lock:
            if branch_id not in self.branches:
                return False
            
            branch = self.branches[branch_id]
            chain_id = branch.chain_id
            
            # Remove branch from chain associations
            if chain_id in self.chain_branches:
                self.chain_branches[chain_id].discard(branch_id)
                
                # If no branches left for this chain, remove the chain entry
                if not self.chain_branches[chain_id]:
                    del self.chain_branches[chain_id]
            
            # Delete nodes if requested
            if delete_nodes and chain_id in self.chains:
                chain = self.chains[chain_id]
                
                for node_id in branch.node_ids:
                    # Check if node is in other branches
                    in_other_branch = False
                    
                    if chain_id in self.chain_branches:
                        for other_branch_id in self.chain_branches[chain_id]:
                            if other_branch_id != branch_id and other_branch_id in self.branches:
                                if node_id in self.branches[other_branch_id].node_ids:
                                    in_other_branch = True
                                    break
                    
                    # Delete node if it's not in other branches
                    if not in_other_branch:
                        chain.remove_node(node_id)
                        
                        # Remove from cache if enabled
                        if self.enable_caching and chain_id in self._node_cache and node_id in self._node_cache[chain_id]:
                            del self._node_cache[chain_id][node_id]
                            if node_id in self._access_counts[chain_id]:
                                del self._access_counts[chain_id][node_id]
            
            # Remove branch from contexts
            for context_id, context in self.contexts.items():
                if context.current_branch_id == branch_id:
                    context.current_branch_id = None
            
            # Remove branch
            del self.branches[branch_id]
            
            logger.info(f"Deleted branch {branch.name} (ID: {branch_id})")
            
            # Save metadata if storage is enabled
            if self.storage_dir:
                self._save_chain_metadata(chain_id)
            
            return True
    
    def create_context(self,
                      chain_id: str,
                      name: str,
                      current_branch_id: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None,
                      creator_agent_id: Optional[str] = None) -> str:
        """
        Create a new reasoning context for a chain.
        
        Args:
            chain_id: ID of the chain to create the context for
            name: Name of the context
            current_branch_id: Optional ID of the current branch for this context
            metadata: Optional metadata for the context
            creator_agent_id: ID of the agent creating the context
            
        Returns:
            str: ID of the newly created context
            
        Raises:
            ValueError: If the chain does not exist
        """
        with self._lock:
            # Check if the chain exists
            if chain_id not in self.chains:
                raise ValueError(f"Chain with ID '{chain_id}' does not exist")
            
            # Check if branch exists and belongs to this chain
            if current_branch_id:
                if current_branch_id not in self.branches:
                    raise ValueError(f"Branch with ID '{current_branch_id}' does not exist")
                
                branch = self.branches[current_branch_id]
                if branch.chain_id != chain_id:
                    raise ValueError(f"Branch '{current_branch_id}' does not belong to chain '{chain_id}'")
            
            # Create context metadata
            context_metadata = metadata or {}
            if creator_agent_id:
                context_metadata["creator_agent_id"] = creator_agent_id
            
            # Create a new context
            context = ReasoningContext(
                name=name,
                chain_id=chain_id,
                current_branch_id=current_branch_id,
                metadata=context_metadata
            )
            
            # Store the context
            self.contexts[context.context_id] = context
            
            # Associate context with chain
            if chain_id not in self.chain_contexts:
                self.chain_contexts[chain_id] = set()
            
            self.chain_contexts[chain_id].add(context.context_id)
            
            logger.info(f"Created new context '{name}' (ID: {context.context_id}) for chain {self.chains[chain_id].name}")
            
            # Save context metadata if storage is enabled
            if self.storage_dir:
                self._save_chain_metadata(chain_id)
            
            return context.context_id
    
    def get_context(self, context_id: str) -> Optional[ReasoningContext]:
        """
        Get a reasoning context by ID.
        
        Args:
            context_id: ID of the context to get
            
        Returns:
            ReasoningContext or None: The context if it exists, None otherwise
        """
        return self.contexts.get(context_id)
    
    def get_chain_contexts(self, chain_id: str) -> List[ReasoningContext]:
        """
        Get all reasoning contexts for a chain.
        
        Args:
            chain_id: ID of the chain
            
        Returns:
            List[ReasoningContext]: List of contexts for the chain
        """
        if chain_id not in self.chain_contexts:
            return []
        
        return [
            self.contexts[context_id]
            for context_id in self.chain_contexts[chain_id]
            if context_id in self.contexts
        ]
    
    def update_context(self, 
                      context_id: str, 
                      state_updates: Optional[Dict[str, Any]] = None,
                      assumptions: Optional[List[Dict[str, Any]]] = None,
                      constraints: Optional[List[Dict[str, Any]]] = None,
                      goals: Optional[List[Dict[str, Any]]] = None,
                      current_branch_id: Optional[str] = None) -> bool:
        """
        Update a reasoning context.
        
        Args:
            context_id: ID of the context to update
            state_updates: Optional dictionary of state updates
            assumptions: Optional list of assumptions to add
            constraints: Optional list of constraints to add
            goals: Optional list of goals to add
            current_branch_id: Optional ID of the new current branch
            
        Returns:
            bool: True if the context was updated, False if it doesn't exist
            
        Raises:
            ValueError: If current_branch_id is provided but doesn't exist
        """
        with self._lock:
            if context_id not in self.contexts:
                return False
            
            context = self.contexts[context_id]
            
            # Check if branch exists and belongs to the context's chain
            if current_branch_id:
                if current_branch_id not in self.branches:
                    raise ValueError(f"Branch with ID '{current_branch_id}' does not exist")
                
                branch = self.branches[current_branch_id]
                if branch.chain_id != context.chain_id:
                    raise ValueError(f"Branch '{current_branch_id}' does not belong to the context's chain")
                
                context.current_branch_id = current_branch_id
            
            # Update state
            if state_updates:
                for key, value in state_updates.items():
                    context.update_state(key, value)
            
            # Add assumptions
            if assumptions:
                for assumption in assumptions:
                    context.add_assumption(assumption)
            
            # Add constraints
            if constraints:
                for constraint in constraints:
                    context.add_constraint(constraint)
            
            # Add goals
            if goals:
                for goal in goals:
                    context.add_goal(goal)
            
            # Save context metadata if storage is enabled
            if self.storage_dir:
                self._save_chain_metadata(context.chain_id)
            
            return True
    
    def delete_context(self, context_id: str) -> bool:
        """
        Delete a reasoning context.
        
        Args:
            context_id: ID of the context to delete
            
        Returns:
            bool: True if the context was deleted, False if it didn't exist
        """
        with self._lock:
            if context_id not in self.contexts:
                return False
            
            context = self.contexts[context_id]
            chain_id = context.chain_id
            
            # Remove context from chain associations
            if chain_id in self.chain_contexts:
                self.chain_contexts[chain_id].discard(context_id)
                
                # If no contexts left for this chain, remove the chain entry
                if not self.chain_contexts[chain_id]:
                    del self.chain_contexts[chain_id]
            
            # Remove context
            del self.contexts[context_id]
            
            logger.info(f"Deleted context {context.name} (ID: {context_id})")
            
            # Save metadata if storage is enabled
            if self.storage_dir:
                self._save_chain_metadata(chain_id)
            
            return True
    
    def get_token_efficient_context(self, 
                                  chain_id: str, 
                                  token_limit: int = 4000,
                                  branch_id: Optional[str] = None,
                                  context_id: Optional[str] = None) -> List[ChainNode]:
        """
        Get a token-efficient context from a chain using the memory manager.
        
        Args:
            chain_id: ID of the chain to get context from
            token_limit: Maximum number of tokens to retrieve
            branch_id: Optional ID of the branch to limit context to
            context_id: Optional ID of the reasoning context to use for retrieval
            
        Returns:
            List[ChainNode]: List of thought nodes forming the context
        """
        with self._lock:
            # Check if the chain exists
            if chain_id not in self.chains:
                return []
            
            chain = self.chains[chain_id]
            
            # Create a conversation memory-like structure for the memory manager
            class ChainMemory:
                def __init__(self, chain, branch_id=None):
                    self.chain = chain
                    self.branch_id = branch_id
                    self.conversation_id = chain.chain_id
                    self.metadata = {}
                    
                    # Get messages (nodes) for this chain/branch
                    if branch_id and branch_id in self.chain._branches:
                        self.messages = [chain.get_node(node_id) for node_id in chain._branches[branch_id]]
                    else:
                        self.messages = list(chain)
            
            # Create a memory object
            memory = ChainMemory(chain, branch_id)
            
            # Get the reasoning context if specified
            context_obj = self.contexts.get(context_id) if context_id else None
            
            # Determine retrieval strategy and parameters based on context
            if context_obj:
                # Extract reference content from context
                reference_content = {
                    "latest_thought_id": context_obj.state.get("latest_thought_id"),
                    "latest_thought_type": context_obj.state.get("latest_thought_type"),
                    "latest_author": context_obj.state.get("latest_author"),
                    "assumptions": context_obj.assumptions,
                    "constraints": context_obj.constraints,
                    "goals": context_obj.goals
                }
                
                # Use hybrid retrieval based on context
                nodes = self.memory_manager.get_context(
                    memory, 
                    self.memory_manager.RetrievalStrategy.HYBRID,
                    token_limit=token_limit,
                    reference_content=reference_content
                )
            else:
                # Default to recency-based retrieval
                nodes = self.memory_manager.get_context(
                    memory,
                    self.memory_manager.RetrievalStrategy.RECENCY,
                    token_limit=token_limit
                )
            
            return nodes
    
    def optimize_chain(self, chain_id: str) -> bool:
        """
        Optimize a chain for memory usage and performance.
        
        Args:
            chain_id: ID of the chain to optimize
            
        Returns:
            bool: True if the optimization was successful
        """
        with self._lock:
            # Check if the chain exists
            if chain_id not in self.chains:
                return False
            
            chain = self.chains[chain_id]
            
            # Clear the node cache for this chain
            if self.enable_caching and chain_id in self._node_cache:
                self._node_cache[chain_id].clear()
                self._access_counts[chain_id].clear()
            
            # Reset internal data structures for better memory usage
            nodes_copy = {node_id: node for node_id, node in chain._nodes.items()}
            chain._nodes.clear()
            chain._nodes.update(nodes_copy)
            
            # Save the optimized chain if storage is enabled
            if self.storage_dir:
                self._save_chain(chain)
            
            logger.info(f"Optimized chain {chain.name} (ID: {chain_id})")
            
            return True
    
    def _evict_lru_node(self, chain_id: str) -> None:
        """
        Evict the least recently used node from the cache.
        
        Args:
            chain_id: ID of the chain to evict from
        """
        if chain_id not in self._node_cache or not self._node_cache[chain_id]:
            return
        
        # Find the node with the lowest access count
        min_count = float('inf')
        min_node_id = None
        
        for node_id, count in self._access_counts[chain_id].items():
            if count < min_count and node_id in self._node_cache[chain_id]:
                min_count = count
                min_node_id = node_id
        
        # Remove the node from cache
        if min_node_id:
            del self._node_cache[chain_id][min_node_id]
            del self._access_counts[chain_id][min_node_id]
    
    def _save_chain(self, chain: ThoughtChain) -> bool:
        """
        Save a thought chain to storage.
        
        Args:
            chain: The thought chain to save
            
        Returns:
            bool: True if the chain was saved successfully, False otherwise
        """
        if not self.storage_dir:
            return False
        
        storage_path = Path(self.storage_dir)
        if not storage_path.exists():
            storage_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Convert the chain to a dictionary
            chain_data = chain.to_dict()
            
            # Save the chain to file
            chain_file = storage_path / f"{chain.chain_id}.json"
            with open(chain_file, "w") as f:
                json.dump(chain_data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving chain {chain.name} (ID: {chain.chain_id}): {e}")
            return False
    
    def _save_chain_metadata(self, chain_id: str) -> bool:
        """
        Save branch and context metadata for a chain.
        
        Args:
            chain_id: ID of the chain to save metadata for
            
        Returns:
            bool: True if the metadata was saved successfully, False otherwise
        """
        if not self.storage_dir:
            return False
        
        storage_path = Path(self.storage_dir)
        if not storage_path.exists():
            storage_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Gather branch data
            branch_data = []
            if chain_id in self.chain_branches:
                for branch_id in self.chain_branches[chain_id]:
                    if branch_id in self.branches:
                        branch_data.append(self.branches[branch_id].to_dict())
            
            # Gather context data
            context_data = []
            if chain_id in self.chain_contexts:
                for context_id in self.chain_contexts[chain_id]:
                    if context_id in self.contexts:
                        context_data.append(self.contexts[context_id].to_dict())
            
            # Create metadata
            metadata = {
                "chain_id": chain_id,
                "branches": branch_data,
                "contexts": context_data,
                "updated_at": time.time()
            }
            
            # Save metadata to file
            metadata_file = storage_path / f"{chain_id}_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving metadata for chain {chain_id}: {e}")
            return False
    
    def _load_chain_metadata(self, chain_id: str) -> bool:
        """
        Load branch and context metadata for a chain.
        
        Args:
            chain_id: ID of the chain to load metadata for
            
        Returns:
            bool: True if the metadata was loaded successfully, False otherwise
        """
        if not self.storage_dir:
            return False
        
        metadata_file = Path(self.storage_dir) / f"{chain_id}_metadata.json"
        if not metadata_file.exists():
            return False
        
        try:
            # Load metadata from file
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            
            # Load branches
            for branch_data in metadata.get("branches", []):
                branch = ChainBranch.from_dict(branch_data)
                self.branches[branch.branch_id] = branch
                
                if chain_id not in self.chain_branches:
                    self.chain_branches[chain_id] = set()
                
                self.chain_branches[chain_id].add(branch.branch_id)
            
            # Load contexts
            for context_data in metadata.get("contexts", []):
                context = ReasoningContext.from_dict(context_data)
                self.contexts[context.context_id] = context
                
                if chain_id not in self.chain_contexts:
                    self.chain_contexts[chain_id] = set()
                
                self.chain_contexts[chain_id].add(context.context_id)
            
            return True
        except Exception as e:
            logger.error(f"Error loading metadata for chain {chain_id}: {e}")
            return False
