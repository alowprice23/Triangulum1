"""
Thought Chain - Main component of the Thought-Chaining Mechanism.

This module defines the ThoughtChain class, which manages collections of ChainNodes
that represent chains of reasoning. ThoughtChain enables agents to build on each
other's thoughts in a structured, coherent way, facilitating complex collaborative
reasoning processes.

The module also includes persistence functionality to save and load thought chains
from disk, allowing for reasoning continuity across sessions.
"""

import json
import uuid
import time
import logging
import os
import io
import gzip
import shutil
import threading
import glob
from typing import Dict, List, Set, Any, Optional, Tuple, Iterator, Union, Callable
from collections import deque
from datetime import datetime
from pathlib import Path

from triangulum_lx.agents.chain_node import ChainNode, ThoughtType, RelationshipType

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_STORAGE_DIR = os.path.join(os.path.expanduser("~"), ".triangulum", "thought_chains")
DEFAULT_BACKUP_COUNT = 5
DEFAULT_COMPRESSION_THRESHOLD = 1024 * 1024  # 1MB


class TraversalOrder:
    """Enumeration of traversal orders for thought chains."""
    
    DEPTH_FIRST = "depth_first"
    BREADTH_FIRST = "breadth_first"
    CHRONOLOGICAL = "chronological"
    REVERSE_CHRONOLOGICAL = "reverse_chronological"
    CONFIDENCE = "confidence"


class ValidationError(Exception):
    """Exception raised when a thought chain validation fails."""
    pass


class PersistenceError(Exception):
    """Exception raised when thought chain persistence operations fail."""
    pass


class ThoughtChainPersistence:
    """
    Handles persistence operations for thought chains.
    
    This class provides static methods for saving and loading thought chains
    from disk, with support for versioning, compression, and thread safety.
    """
    
    # Thread lock for file operations
    _file_locks = {}
    _lock_lock = threading.Lock()
    
    @staticmethod
    def get_file_lock(filepath):
        """Get a thread lock for a specific file path."""
        with ThoughtChainPersistence._lock_lock:
            if filepath not in ThoughtChainPersistence._file_locks:
                ThoughtChainPersistence._file_locks[filepath] = threading.Lock()
            return ThoughtChainPersistence._file_locks[filepath]
    
    @staticmethod
    def save_to_file(chain: 'ThoughtChain', filepath: str, compress: bool = False, 
                   create_backup: bool = True, max_backups: int = DEFAULT_BACKUP_COUNT) -> str:
        """
        Save a thought chain to a file.
        
        Args:
            chain: The thought chain to save
            filepath: Path to save the file to
            compress: Whether to compress the file
            create_backup: Whether to create a backup of existing file
            max_backups: Maximum number of backup versions to keep
            
        Returns:
            str: Path to the saved file
            
        Raises:
            PersistenceError: If saving fails
        """
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            # Acquire lock for this file
            file_lock = ThoughtChainPersistence.get_file_lock(filepath)
            with file_lock:
                # Create backup if requested and file exists
                if create_backup and os.path.exists(filepath):
                    ThoughtChainPersistence._create_backup(filepath, max_backups)
                
                # Convert chain to JSON
                chain_json = chain.to_json()
                
                # Determine whether to compress based on size and compress flag
                should_compress = compress
                if not should_compress and len(chain_json) > DEFAULT_COMPRESSION_THRESHOLD:
                    should_compress = True
                    logger.info(f"Auto-compressing thought chain {chain.chain_id} due to size")
                
                # Write to file with or without compression
                if should_compress:
                    if not filepath.endswith('.gz'):
                        filepath += '.gz'
                    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                        f.write(chain_json)
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(chain_json)
                
                return filepath
        
        except Exception as e:
            error_msg = f"Failed to save thought chain {chain.chain_id} to {filepath}: {str(e)}"
            logger.error(error_msg)
            raise PersistenceError(error_msg) from e
    
    @staticmethod
    def load_from_file(filepath: str) -> 'ThoughtChain':
        """
        Load a thought chain from a file.
        
        Args:
            filepath: Path to load the file from
            
        Returns:
            ThoughtChain: The loaded thought chain
            
        Raises:
            PersistenceError: If loading fails
            FileNotFoundError: If the file doesn't exist
        """
        try:
            # Check if file exists
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Thought chain file {filepath} not found")
            
            # Acquire lock for this file
            file_lock = ThoughtChainPersistence.get_file_lock(filepath)
            with file_lock:
                # Determine if file is compressed
                is_compressed = filepath.endswith('.gz')
                
                # Read file
                if is_compressed:
                    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                        chain_json = f.read()
                else:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        chain_json = f.read()
                
                # Convert JSON to ThoughtChain
                return ThoughtChain.from_json(chain_json)
        
        except Exception as e:
            error_msg = f"Failed to load thought chain from {filepath}: {str(e)}"
            logger.error(error_msg)
            raise PersistenceError(error_msg) from e
    
    @staticmethod
    def _create_backup(filepath: str, max_backups: int) -> str:
        """
        Create a backup of an existing file.
        
        Args:
            filepath: Path to the file to back up
            max_backups: Maximum number of backup versions to keep
            
        Returns:
            str: Path to the backup file
        """
        try:
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            base, ext = os.path.splitext(filepath)
            if ext == '.gz':
                base, inner_ext = os.path.splitext(base)
                ext = inner_ext + ext
            
            backup_path = f"{base}.{timestamp}{ext}"
            
            # Copy the file
            shutil.copy2(filepath, backup_path)
            
            # Clean up old backups if needed
            ThoughtChainPersistence._cleanup_old_backups(filepath, max_backups)
            
            return backup_path
        
        except Exception as e:
            logger.warning(f"Failed to create backup of {filepath}: {str(e)}")
            return ""
    
    @staticmethod
    def _cleanup_old_backups(filepath: str, max_backups: int) -> None:
        """
        Clean up old backup files, keeping only the most recent ones.
        
        Args:
            filepath: Path to the original file
            max_backups: Maximum number of backup versions to keep
        """
        try:
            # Get all backup files
            base, ext = os.path.splitext(filepath)
            if ext == '.gz':
                base, inner_ext = os.path.splitext(base)
                ext = inner_ext + ext
            
            # Create pattern to match backup files with timestamps
            pattern = f"{base}.[0-9]{{14}}{ext}"
            backup_files = glob.glob(pattern)
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Make sure we have more files than our max before removing any
            if len(backup_files) > max_backups:
                # Remove excess backups
                for old_backup in backup_files[max_backups:]:
                    os.remove(old_backup)
                    logger.debug(f"Removed old backup: {old_backup}")
        
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups for {filepath}: {str(e)}")
    
    @staticmethod
    def list_available_chains(directory: str = DEFAULT_STORAGE_DIR) -> List[Dict[str, Any]]:
        """
        List all available thought chains in the storage directory.
        
        Args:
            directory: Directory to search for thought chains
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries with chain metadata
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            # Get all JSON and gzipped JSON files
            json_files = glob.glob(os.path.join(directory, "**", "*.json"), recursive=True)
            gz_files = glob.glob(os.path.join(directory, "**", "*.json.gz"), recursive=True)
            
            # Combine and process files
            result = []
            for filepath in json_files + gz_files:
                try:
                    # Quick read of metadata only
                    metadata = ThoughtChainPersistence._read_chain_metadata(filepath)
                    if metadata:
                        metadata["filepath"] = filepath
                        result.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to read metadata from {filepath}: {str(e)}")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to list available chains in {directory}: {str(e)}")
            return []
    
    @staticmethod
    def _read_chain_metadata(filepath: str) -> Dict[str, Any]:
        """
        Read basic metadata from a thought chain file without loading the entire chain.
        
        Args:
            filepath: Path to the thought chain file
            
        Returns:
            Dict[str, Any]: Dictionary with chain metadata, or empty dict if reading fails
        """
        try:
            # Determine if file is compressed
            is_compressed = filepath.endswith('.gz')
            
            # Open file
            if is_compressed:
                f = gzip.open(filepath, 'rt', encoding='utf-8')
            else:
                f = open(filepath, 'r', encoding='utf-8')
            
            # Read beginning of file to extract basic metadata
            with f:
                # Read only enough to get metadata
                data = json.loads(f.read(4096))
                
                # Extract basic metadata
                metadata = {
                    "chain_id": data.get("chain_id", "unknown"),
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "node_count": len(data.get("nodes", {})),
                    "schema_version": data.get("schema_version", "unknown")
                }
                
                return metadata
        
        except Exception as e:
            logger.debug(f"Failed to read metadata from {filepath}: {str(e)}")
            return {}


class ThoughtChain:
    """
    Manages a chain of connected thoughts represented as ChainNodes.
    
    ThoughtChain provides methods for creating, traversing, and manipulating chains
    of reasoning, enabling agents to collaboratively build structured thought processes.
    """
    
    def __init__(self, 
                 chain_id: Optional[str] = None, 
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a thought chain.
        
        Args:
            chain_id: Unique identifier for the chain (generated if not provided)
            name: Human-readable name for the chain
            description: Description of the chain's purpose or content
            metadata: Additional metadata for the chain
        """
        self.chain_id = chain_id or str(uuid.uuid4())
        self.name = name or f"ThoughtChain-{self.chain_id[:8]}"
        self.description = description or ""
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = self.created_at
        
        # Main data structure: map of node_id to ChainNode
        self._nodes: Dict[str, ChainNode] = {}
        
        # Root nodes (those without parents in this chain)
        self._root_node_ids: Set[str] = set()
        
        # Leaf nodes (those without children in this chain)
        self._leaf_node_ids: Set[str] = set()
        
        # Schema version
        self.schema_version = "1.0"
    
    def add_node(self, node: ChainNode, parent_id: Optional[str] = None, 
                relationship: Optional[RelationshipType] = None) -> str:
        """
        Add a node to the chain.
        
        Args:
            node: The ChainNode to add
            parent_id: Optional ID of the parent node to connect to
            relationship: Type of relationship to the parent (required if parent_id is provided)
            
        Returns:
            str: ID of the added node
            
        Raises:
            ValueError: If parent_id is provided but doesn't exist in the chain
            ValueError: If parent_id is provided but relationship is not
        """
        # Check if we already have this node
        if node.node_id in self._nodes:
            logger.warning(f"Node {node.node_id} already exists in chain {self.chain_id}")
            return node.node_id
        
        # If parent_id is provided, connect to the parent
        if parent_id:
            if parent_id not in self._nodes:
                raise ValueError(f"Parent node {parent_id} does not exist in chain {self.chain_id}")
            
            if relationship is None:
                raise ValueError("Relationship must be provided when connecting to a parent")
            
            # Connect the nodes
            parent_node = self._nodes[parent_id]
            parent_node.add_child(node.node_id, relationship)
            node.add_parent(parent_id, relationship)
            
            # If this was a leaf node, it's not anymore
            if parent_id in self._leaf_node_ids:
                self._leaf_node_ids.remove(parent_id)
        else:
            # No parent means this is a root node
            self._root_node_ids.add(node.node_id)
        
        # This is a leaf node until it gets children
        self._leaf_node_ids.add(node.node_id)
        
        # Add the node to the chain
        self._nodes[node.node_id] = node
        
        # Update timestamp
        self.updated_at = time.time()
        
        return node.node_id
    
    def remove_node(self, node_id: str, reconnect_orphans: bool = True) -> bool:
        """
        Remove a node from the chain.
        
        Args:
            node_id: ID of the node to remove
            reconnect_orphans: If True, reconnect orphaned children to the node's parents
            
        Returns:
            bool: True if the node was removed, False if it wasn't in the chain
        """
        if node_id not in self._nodes:
            return False
        
        node = self._nodes[node_id]
        
        # Update parents to remove this node as a child
        for parent_id in node.parent_ids:
            if parent_id in self._nodes:
                self._nodes[parent_id].remove_child(node_id)
                
                # If the parent now has no children, it's a leaf
                if not self._nodes[parent_id].child_ids:
                    self._leaf_node_ids.add(parent_id)
        
        # Update children to remove this node as a parent
        for child_id in node.child_ids:
            if child_id in self._nodes:
                self._nodes[child_id].remove_parent(node_id)
                
                # If the child now has no parents, it's a root or orphan
                if not self._nodes[child_id].parent_ids:
                    if reconnect_orphans and node.parent_ids:
                        # Connect the orphan to this node's parents
                        for parent_id in node.parent_ids:
                            if parent_id in self._nodes:
                                relationship = node.get_relationship_to(parent_id)
                                if relationship:
                                    self._nodes[child_id].add_parent(parent_id, relationship)
                                    self._nodes[parent_id].add_child(child_id, relationship)
                    else:
                        # This is now a root node
                        self._root_node_ids.add(child_id)
        
        # Remove the node from root/leaf sets if present
        if node_id in self._root_node_ids:
            self._root_node_ids.remove(node_id)
        if node_id in self._leaf_node_ids:
            self._leaf_node_ids.remove(node_id)
        
        # Remove the node from the chain
        del self._nodes[node_id]
        
        # Update timestamp
        self.updated_at = time.time()
        
        return True
    
    def get_node(self, node_id: str) -> Optional[ChainNode]:
        """
        Get a node by ID.
        
        Args:
            node_id: ID of the node to get
            
        Returns:
            ChainNode or None: The node if it exists, None otherwise
        """
        return self._nodes.get(node_id)
    
    def add_relationship(self, source_id: str, target_id: str, 
                        relationship: RelationshipType) -> bool:
        """
        Add a relationship between two existing nodes.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            relationship: Type of relationship
            
        Returns:
            bool: True if the relationship was added, False if either node doesn't exist
            
        Raises:
            ValueError: If adding the relationship would create a cycle
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return False
        
        # Check for cycles (except for PARALLEL relationships which don't imply hierarchy)
        if relationship != RelationshipType.PARALLEL:
            if self._would_create_cycle(source_id, target_id):
                raise ValueError(f"Adding relationship from {source_id} to {target_id} would create a cycle")
        
        # Add the relationship
        self._nodes[source_id].add_child(target_id, relationship)
        self._nodes[target_id].add_parent(source_id, relationship)
        
        # Update root and leaf sets
        if target_id in self._root_node_ids:
            self._root_node_ids.remove(target_id)
        if source_id in self._leaf_node_ids:
            self._leaf_node_ids.remove(source_id)
        
        # Update timestamp
        self.updated_at = time.time()
        
        return True
    
    def remove_relationship(self, source_id: str, target_id: str) -> bool:
        """
        Remove a relationship between two nodes.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            
        Returns:
            bool: True if the relationship was removed, False if it didn't exist
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return False
        
        source_node = self._nodes[source_id]
        target_node = self._nodes[target_id]
        
        # Check if the relationship exists
        if target_id not in source_node.child_ids or source_id not in target_node.parent_ids:
            return False
        
        # Remove the relationship
        source_node.remove_child(target_id)
        target_node.remove_parent(source_id)
        
        # Update root and leaf sets
        if not target_node.parent_ids:
            self._root_node_ids.add(target_id)
        if not source_node.child_ids:
            self._leaf_node_ids.add(source_id)
        
        # Update timestamp
        self.updated_at = time.time()
        
        return True
    
    def traverse(self, 
                order: str = TraversalOrder.DEPTH_FIRST, 
                start_node_id: Optional[str] = None,
                filter_fn: Optional[Callable[[ChainNode], bool]] = None) -> Iterator[ChainNode]:
        """
        Traverse the chain in the specified order.
        
        Args:
            order: Traversal order (one of TraversalOrder values)
            start_node_id: ID of the node to start from (uses all roots if None)
            filter_fn: Optional function to filter nodes during traversal
            
        Yields:
            ChainNode: Nodes in the traversal order
            
        Raises:
            ValueError: If start_node_id is provided but doesn't exist in the chain
        """
        if start_node_id and start_node_id not in self._nodes:
            raise ValueError(f"Start node {start_node_id} does not exist in chain {self.chain_id}")
        
        # Use all root nodes if no start node is provided
        start_nodes = [self._nodes[start_node_id]] if start_node_id else [self._nodes[nid] for nid in self._root_node_ids]
        
        if not start_nodes:
            # No nodes to traverse
            return
        
        if order == TraversalOrder.DEPTH_FIRST:
            yield from self._traverse_depth_first(start_nodes, filter_fn)
        elif order == TraversalOrder.BREADTH_FIRST:
            yield from self._traverse_breadth_first(start_nodes, filter_fn)
        elif order == TraversalOrder.CHRONOLOGICAL:
            yield from self._traverse_chronological(ascending=True, filter_fn=filter_fn)
        elif order == TraversalOrder.REVERSE_CHRONOLOGICAL:
            yield from self._traverse_chronological(ascending=False, filter_fn=filter_fn)
        elif order == TraversalOrder.CONFIDENCE:
            yield from self._traverse_by_confidence(filter_fn=filter_fn)
        else:
            raise ValueError(f"Unknown traversal order: {order}")
    
    def _traverse_depth_first(self, 
                            start_nodes: List[ChainNode],
                            filter_fn: Optional[Callable[[ChainNode], bool]] = None) -> Iterator[ChainNode]:
        """
        Perform a depth-first traversal of the chain.
        
        Args:
            start_nodes: List of nodes to start from
            filter_fn: Optional function to filter nodes during traversal
            
        Yields:
            ChainNode: Nodes in depth-first order
        """
        visited = set()
        stack = list(start_nodes)
        
        while stack:
            node = stack.pop()
            
            if node.node_id in visited:
                continue
            
            visited.add(node.node_id)
            
            if filter_fn is None or filter_fn(node):
                yield node
            
            # Add children in reverse order so they're processed in original order
            children = [self._nodes[child_id] for child_id in node.child_ids if child_id in self._nodes]
            stack.extend(reversed(children))
    
    def _traverse_breadth_first(self, 
                              start_nodes: List[ChainNode],
                              filter_fn: Optional[Callable[[ChainNode], bool]] = None) -> Iterator[ChainNode]:
        """
        Perform a breadth-first traversal of the chain.
        
        Args:
            start_nodes: List of nodes to start from
            filter_fn: Optional function to filter nodes during traversal
            
        Yields:
            ChainNode: Nodes in breadth-first order
        """
        visited = set()
        queue = deque(start_nodes)
        
        while queue:
            node = queue.popleft()
            
            if node.node_id in visited:
                continue
            
            visited.add(node.node_id)
            
            if filter_fn is None or filter_fn(node):
                yield node
            
            # Add children to the queue
            for child_id in node.child_ids:
                if child_id in self._nodes and child_id not in visited:
                    queue.append(self._nodes[child_id])
    
    def _traverse_chronological(self, 
                              ascending: bool = True,
                              filter_fn: Optional[Callable[[ChainNode], bool]] = None) -> Iterator[ChainNode]:
        """
        Traverse nodes in chronological or reverse chronological order.
        
        Args:
            ascending: If True, traverse oldest to newest; if False, newest to oldest
            filter_fn: Optional function to filter nodes during traversal
            
        Yields:
            ChainNode: Nodes in chronological order
        """
        # Sort nodes by timestamp
        sorted_nodes = sorted(self._nodes.values(), key=lambda n: n.timestamp, reverse=not ascending)
        
        for node in sorted_nodes:
            if filter_fn is None or filter_fn(node):
                yield node
    
    def _traverse_by_confidence(self, 
                              filter_fn: Optional[Callable[[ChainNode], bool]] = None) -> Iterator[ChainNode]:
        """
        Traverse nodes in order of decreasing confidence.
        
        Args:
            filter_fn: Optional function to filter nodes during traversal
            
        Yields:
            ChainNode: Nodes in confidence order (highest confidence first)
        """
        # Sort nodes by confidence (handling None values)
        def confidence_key(node: ChainNode) -> float:
            return node.confidence if node.confidence is not None else -1
        
        sorted_nodes = sorted(self._nodes.values(), key=confidence_key, reverse=True)
        
        for node in sorted_nodes:
            if filter_fn is None or filter_fn(node):
                # Skip nodes with no confidence unless specifically requested
                if node.confidence is not None:
                    yield node
    
    def find_nodes(self, 
                  thought_type: Optional[ThoughtType] = None,
                  author_agent_id: Optional[str] = None,
                  min_confidence: Optional[float] = None,
                  max_confidence: Optional[float] = None,
                  keyword: Optional[str] = None) -> List[ChainNode]:
        """
        Find nodes matching the specified criteria.
        
        Args:
            thought_type: Filter by thought type
            author_agent_id: Filter by author agent ID
            min_confidence: Filter by minimum confidence
            max_confidence: Filter by maximum confidence
            keyword: Filter by keyword in content
            
        Returns:
            List[ChainNode]: Nodes matching the criteria
        """
        results = []
        
        for node in self._nodes.values():
            # Apply filters
            if thought_type and node.thought_type != thought_type:
                continue
            
            if author_agent_id and node.author_agent_id != author_agent_id:
                continue
            
            if min_confidence is not None and (node.confidence is None or node.confidence < min_confidence):
                continue
            
            if max_confidence is not None and (node.confidence is None or node.confidence > max_confidence):
                continue
            
            if keyword:
                # Check if the keyword appears in any content values
                content_str = str(node.content)
                if keyword.lower() not in content_str.lower():
                    continue
            
            results.append(node)
        
        return results
    
    def find_paths(self, source_id: str, target_id: str) -> List[List[str]]:
        """
        Find all paths between two nodes.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            
        Returns:
            List[List[str]]: List of paths (each path is a list of node IDs)
            
        Raises:
            ValueError: If either node doesn't exist in the chain
        """
        if source_id not in self._nodes:
            raise ValueError(f"Source node {source_id} does not exist in chain {self.chain_id}")
        
        if target_id not in self._nodes:
            raise ValueError(f"Target node {target_id} does not exist in chain {self.chain_id}")
        
        # Use depth-first search to find paths
        paths = []
        visited = set()
        
        def dfs(current_id: str, path: List[str]):
            """Recursive depth-first search for paths."""
            path.append(current_id)
            visited.add(current_id)
            
            if current_id == target_id:
                # Found a path to the target
                paths.append(path.copy())
            else:
                # Continue the search with children
                for child_id in self._nodes[current_id].child_ids:
                    if child_id in self._nodes and child_id not in visited:
                        dfs(child_id, path)
            
            # Backtrack
            path.pop()
            visited.remove(current_id)
        
        # Start the search
        dfs(source_id, [])
        
        return paths
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the integrity of the chain.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation errors)
        """
        errors = []
        
        # Check for consistency between nodes and relationships
        for node_id, node in self._nodes.items():
            # Check that all parent nodes exist and have this node as a child
            for parent_id in node.parent_ids:
                if parent_id not in self._nodes:
                    errors.append(f"Node {node_id} has nonexistent parent {parent_id}")
                elif node_id not in self._nodes[parent_id].child_ids:
                    errors.append(f"Inconsistent relationship: {parent_id} is not linked to {node_id} as child")
            
            # Check that all child nodes exist and have this node as a parent
            for child_id in node.child_ids:
                if child_id not in self._nodes:
                    errors.append(f"Node {node_id} has nonexistent child {child_id}")
                elif node_id not in self._nodes[child_id].parent_ids:
                    errors.append(f"Inconsistent relationship: {child_id} is not linked to {node_id} as parent")
            
            # Check that all relationships have valid targets
            for rel_id in node.relationships:
                if rel_id not in node.parent_ids and rel_id not in node.child_ids:
                    errors.append(f"Node {node_id} has relationship to {rel_id} but it's neither parent nor child")
        
        # Check for cycles (except for PARALLEL relationships)
        for node_id in self._nodes:
            for child_id in self._nodes[node_id].child_ids:
                if child_id in self._nodes and self._nodes[node_id].get_relationship_to(child_id) != RelationshipType.PARALLEL:
                    if self._has_path(child_id, node_id, exclude_parallel=True):
                        errors.append(f"Cycle detected: {node_id} -> {child_id} -> ... -> {node_id}")
        
        # Check root and leaf sets for consistency
        computed_roots = {node_id for node_id, node in self._nodes.items() if not node.parent_ids}
        if computed_roots != self._root_node_ids:
            errors.append(f"Inconsistent root nodes: computed {computed_roots}, stored {self._root_node_ids}")
        
        computed_leaves = {node_id for node_id, node in self._nodes.items() if not node.child_ids}
        if computed_leaves != self._leaf_node_ids:
            errors.append(f"Inconsistent leaf nodes: computed {computed_leaves}, stored {self._leaf_node_ids}")
        
        return len(errors) == 0, errors
    
    def _would_create_cycle(self, source_id: str, target_id: str) -> bool:
        """
        Check if adding a relationship from source to target would create a cycle.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            
        Returns:
            bool: True if adding the relationship would create a cycle
        """
        # If target is already an ancestor of source, adding this link would create a cycle
        return self._has_path(target_id, source_id, exclude_parallel=True)
    
    def _has_path(self, source_id: str, target_id: str, exclude_parallel: bool = False) -> bool:
        """
        Check if there's a path from source to target.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            exclude_parallel: If True, don't follow PARALLEL relationships
            
        Returns:
            bool: True if there's a path from source to target
        """
        visited = set()
        queue = deque([source_id])
        
        while queue:
            node_id = queue.popleft()
            
            if node_id == target_id:
                return True
            
            if node_id in visited:
                continue
            
            visited.add(node_id)
            
            if node_id in self._nodes:
                for child_id in self._nodes[node_id].child_ids:
                    if exclude_parallel:
                        rel = self._nodes[node_id].get_relationship_to(child_id)
                        if rel == RelationshipType.PARALLEL:
                            continue
                    queue.append(child_id)
        
        return False
    
    def merge(self, other_chain: 'ThoughtChain', connect_roots: bool = False, 
             root_relationship: Optional[RelationshipType] = None) -> None:
        """
        Merge another thought chain into this one.
        
        Args:
            other_chain: The chain to merge into this one
            connect_roots: If True, connect this chain's leaves to the other chain's roots
            root_relationship: Relationship type to use when connecting roots (required if connect_roots is True)
            
        Raises:
            ValueError: If connect_roots is True but root_relationship is None
        """
        if connect_roots and root_relationship is None:
            raise ValueError("root_relationship must be provided when connect_roots is True")
        
        # Copy nodes from the other chain
        for node_id, node in other_chain._nodes.items():
            if node_id not in self._nodes:
                # Create a copy to avoid modifying the original
                node_copy = ChainNode.from_dict(node.to_dict())
                
                # Clear relationships that might not be valid in this chain
                node_copy.parent_ids = set()
                node_copy.child_ids = set()
                node_copy.relationships = {}
                
                # Add the node without connections
                self._nodes[node_id] = node_copy
                self._root_node_ids.add(node_id)
                self._leaf_node_ids.add(node_id)
        
        # Reconnect relationships within the other chain
        for node_id, node in other_chain._nodes.items():
            our_node = self._nodes[node_id]
            
            for child_id in node.child_ids:
                if child_id in self._nodes:
                    relationship = node.get_relationship_to(child_id)
                    if relationship:
                        our_node.add_child(child_id, relationship)
                        self._nodes[child_id].add_parent(node_id, relationship)
                        
                        # Update root and leaf sets
                        if child_id in self._root_node_ids:
                            self._root_node_ids.remove(child_id)
                        if node_id in self._leaf_node_ids:
                            self._leaf_node_ids.remove(node_id)
        
        # Connect this chain's leaves to the other chain's roots if requested
        if connect_roots and root_relationship:
            for leaf_id in list(self._leaf_node_ids):  # Copy to avoid modification during iteration
                for root_id in other_chain._root_node_ids:
                    if leaf_id != root_id and root_id in self._nodes:  # Avoid self-links
                        self._nodes[leaf_id].add_child(root_id, root_relationship)
                        self._nodes[root_id].add_parent(leaf_id, root_relationship)
                        
                        # Update root and leaf sets
                        if root_id in self._root_node_ids:
                            self._root_node_ids.remove(root_id)
                        if leaf_id in self._leaf_node_ids:
                            self._leaf_node_ids.remove(leaf_id)
        
        # Update timestamp
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the thought chain to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the chain
        """
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "nodes": {node_id: node.to_dict() for node_id, node in self._nodes.items()},
            "root_node_ids": list(self._root_node_ids),
            "leaf_node_ids": list(self._leaf_node_ids),
            "schema_version": self.schema_version
        }
    
    def to_json(self) -> str:
        """
        Convert the thought chain to a JSON string.
        
        Returns:
            str: JSON representation of the chain
        """
        return json.dumps(self.to_dict())
    
    def save_to_file(self, filepath: Optional[str] = None, compress: bool = False,
                   storage_dir: str = DEFAULT_STORAGE_DIR, 
                   create_backup: bool = True,
                   max_backups: int = DEFAULT_BACKUP_COUNT) -> str:
        """
        Save the thought chain to a file.
        
        Args:
            filepath: Path to save the file to. If None, a default path is generated.
            compress: Whether to compress the file.
            storage_dir: Directory to save the file in if filepath is None.
            create_backup: Whether to create a backup of existing file.
            max_backups: Maximum number of backup versions to keep.
            
        Returns:
            str: Path to the saved file.
            
        Raises:
            PersistenceError: If saving fails.
        """
        # Generate filepath if not provided
        if filepath is None:
            # Create storage directory if it doesn't exist
            os.makedirs(storage_dir, exist_ok=True)
            
            # Use chain_id for filename
            filename = f"{self.chain_id}.json"
            filepath = os.path.join(storage_dir, filename)
        
        # Use persistence class to save
        return ThoughtChainPersistence.save_to_file(
            self, filepath, compress, create_backup, max_backups
        )
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'ThoughtChain':
        """
        Load a thought chain from a file.
        
        Args:
            filepath: Path to load the file from.
            
        Returns:
            ThoughtChain: The loaded thought chain.
            
        Raises:
            PersistenceError: If loading fails.
            FileNotFoundError: If the file doesn't exist.
        """
        return ThoughtChainPersistence.load_from_file(filepath)
    
    @classmethod
    def list_available_chains(cls, directory: str = DEFAULT_STORAGE_DIR) -> List[Dict[str, Any]]:
        """
        List all available thought chains in the storage directory.
        
        Args:
            directory: Directory to search for thought chains.
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries with chain metadata.
        """
        return ThoughtChainPersistence.list_available_chains(directory)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThoughtChain':
        """
        Create a thought chain from a dictionary representation.
        
        Args:
            data: Dictionary representation of the chain
            
        Returns:
            ThoughtChain: Instantiated thought chain
        """
        chain = cls(
            chain_id=data.get("chain_id"),
            name=data.get("name"),
            description=data.get("description"),
            metadata=data.get("metadata", {})
        )
        
        chain.created_at = data.get("created_at", time.time())
        chain.updated_at = data.get("updated_at", time.time())
        chain.schema_version = data.get("schema_version", "1.0")
        
        # Add nodes without connections
        for node_id, node_data in data.get("nodes", {}).items():
            node = ChainNode.from_dict(node_data)
            chain._nodes[node_id] = node
        
        # Set root and leaf node sets
        chain._root_node_ids = set(data.get("root_node_ids", []))
        chain._leaf_node_ids = set(data.get("leaf_node_ids", []))
        
        # Reconnect relationships
        for node_id, node in chain._nodes.items():
            # Clear existing relationships
            node.parent_ids = set()
            node.child_ids = set()
            node.relationships = {}
            
            # Restore from the original data
            node_data = data["nodes"][node_id]
            
            if "parent_ids" in node_data:
                for parent_id in node_data["parent_ids"]:
                    if parent_id in chain._nodes:
                        relationship = RelationshipType(node_data["relationships"].get(parent_id, "sequence"))
                        node.add_parent(parent_id, relationship)
            
            if "child_ids" in node_data:
                for child_id in node_data["child_ids"]:
                    if child_id in chain._nodes:
                        relationship = RelationshipType(node_data["relationships"].get(child_id, "sequence"))
                        node.add_child(child_id, relationship)
        
        return chain
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ThoughtChain':
        """
        Create a thought chain from a JSON string.
        
        Args:
            json_str: JSON representation of the chain
            
        Returns:
            ThoughtChain: Instantiated thought chain
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __len__(self) -> int:
        """
        Get the number of nodes in the chain.
        
        Returns:
            int: Number of nodes
        """
        return len(self._nodes)
    
    def __contains__(self, node_id: str) -> bool:
        """
        Check if a node is in the chain.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            bool: True if the node is in the chain
        """
        return node_id in self._nodes
    
    def __iter__(self) -> Iterator[ChainNode]:
        """
        Iterate over all nodes in the chain.
        
        Yields:
            ChainNode: Nodes in the chain
        """
        for node in self._nodes.values():
            yield node
