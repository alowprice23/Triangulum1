"""
Graph models for code dependency analysis.

This module provides the data structures and models used for representing
and analyzing dependencies between files in a codebase.
"""

from enum import Enum, auto
from typing import Dict, List, Set, Optional, Any, Tuple, Iterator, NamedTuple
import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path


class DependencyType(Enum):
    """Types of dependencies between files."""
    IMPORT = auto()           # Direct import statement
    INHERITANCE = auto()      # Class inheritance
    FUNCTION_CALL = auto()    # Function/method call
    VARIABLE_USE = auto()     # Variable reference
    TYPE_REFERENCE = auto()   # Type annotation or reference
    IMPLICIT = auto()         # Implicit dependency (e.g., through configuration)
    UNKNOWN = auto()          # Unknown dependency type


class LanguageType(Enum):
    """Supported programming languages for dependency analysis."""
    PYTHON = auto()
    JAVASCRIPT = auto()
    TYPESCRIPT = auto()
    JAVA = auto()
    CPP = auto()
    GO = auto()
    RUST = auto()
    UNKNOWN = auto()

    @classmethod
    def from_extension(cls, extension: str) -> 'LanguageType':
        """Determine language type from file extension."""
        ext_map = {
            '.py': cls.PYTHON,
            '.js': cls.JAVASCRIPT,
            '.jsx': cls.JAVASCRIPT,
            '.ts': cls.TYPESCRIPT,
            '.tsx': cls.TYPESCRIPT,
            '.java': cls.JAVA,
            '.cpp': cls.CPP,
            '.cc': cls.CPP,
            '.hpp': cls.CPP,
            '.h': cls.CPP,
            '.go': cls.GO,
            '.rs': cls.RUST,
        }
        return ext_map.get(extension.lower(), cls.UNKNOWN)

    @classmethod
    def from_str(cls, s: str) -> 'LanguageType':
        """Determine language type from a string."""
        s_upper = s.upper()
        for member in cls:
            if member.name == s_upper:
                return member
        return cls.UNKNOWN


@dataclass
class DependencyMetadata:
    """Metadata for a dependency relationship."""
    dependency_type: DependencyType
    source_lines: List[int] = field(default_factory=list)  # Line numbers where dependency appears
    symbols: List[str] = field(default_factory=list)      # Symbols involved in the dependency
    verified: bool = False                               # Whether dependency has been verified
    confidence: float = 1.0                             # Confidence score (0.0-1.0)
    additional_info: Dict[str, Any] = field(default_factory=dict)  # Additional dependency information

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "dependency_type": self.dependency_type.name,
            "source_lines": self.source_lines,
            "symbols": self.symbols,
            "verified": self.verified,
            "confidence": self.confidence,
            "additional_info": self.additional_info
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DependencyMetadata':
        """Create instance from dictionary representation."""
        return cls(
            dependency_type=DependencyType[data["dependency_type"]],
            source_lines=data.get("source_lines", []),
            symbols=data.get("symbols", []),
            verified=data.get("verified", False),
            confidence=data.get("confidence", 1.0),
            additional_info=data.get("additional_info", {})
        )


@dataclass
class FileNode:
    """A node in the dependency graph representing a file."""
    path: str
    language: LanguageType
    module_name: Optional[str] = None
    last_modified: float = field(default_factory=time.time)
    file_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize derived fields after instance creation."""
        if not self.file_hash and Path(self.path).exists():
            self.update_hash()
    
    def update_hash(self) -> str:
        """Update and return the file hash based on current content."""
        try:
            content = Path(self.path).read_bytes()
            self.file_hash = hashlib.sha256(content).hexdigest()
            self.last_modified = Path(self.path).stat().st_mtime
            return self.file_hash
        except (FileNotFoundError, PermissionError):
            return self.file_hash or ""
    
    def has_changed(self) -> bool:
        """Check if the file has changed since last hash calculation."""
        if not self.file_hash or not Path(self.path).exists():
            return True
        
        current_mtime = Path(self.path).stat().st_mtime
        if current_mtime > self.last_modified:
            current_hash = hashlib.sha256(Path(self.path).read_bytes()).hexdigest()
            return current_hash != self.file_hash
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "path": self.path,
            "language": self.language.name,
            "module_name": self.module_name,
            "last_modified": self.last_modified,
            "file_hash": self.file_hash,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileNode':
        """Create instance from dictionary representation."""
        return cls(
            path=data["path"],
            language=LanguageType[data["language"]],
            module_name=data.get("module_name"),
            last_modified=data.get("last_modified", time.time()),
            file_hash=data.get("file_hash"),
            metadata=data.get("metadata", {})
        )


class DependencyEdge(NamedTuple):
    """An edge in the dependency graph representing a dependency between files."""
    source: str  # Path of the source file
    target: str  # Path of the target file
    metadata: DependencyMetadata


class DependencyGraph:
    """
    A directed graph representing dependencies between files in a codebase.
    
    The graph structure is optimized for common dependency analysis operations
    such as finding all dependencies of a file, finding all files that depend
    on a given file, and detecting cycles.
    """
    
    def __init__(self, version: str = "1.0"):
        """Initialize an empty dependency graph."""
        self._nodes: Dict[str, FileNode] = {}  # path -> FileNode
        self._outgoing: Dict[str, Dict[str, DependencyMetadata]] = {}  # source -> {target -> metadata}
        self._incoming: Dict[str, Dict[str, DependencyMetadata]] = {}  # target -> {source -> metadata}
        self.created_at = time.time()
        self.modified_at = self.created_at
        self.version = version
    
    def add_node(self, node: FileNode) -> None:
        """
        Add a node to the graph.
        
        Args:
            node: The FileNode to add
        """
        self._nodes[node.path] = node
        if node.path not in self._outgoing:
            self._outgoing[node.path] = {}
        if node.path not in self._incoming:
            self._incoming[node.path] = {}
        self.modified_at = time.time()
    
    def add_edge(self, source: str, target: str, metadata: DependencyMetadata) -> None:
        """
        Add an edge to the graph.
        
        Args:
            source: Path of the source file
            target: Path of the target file
            metadata: Metadata describing the dependency
        """
        # Ensure nodes exist
        if source not in self._nodes or target not in self._nodes:
            raise ValueError(f"Both source and target nodes must exist in the graph")
        
        # Add the edge
        self._outgoing.setdefault(source, {})[target] = metadata
        self._incoming.setdefault(target, {})[source] = metadata
        self.modified_at = time.time()
    
    def get_node(self, path: str) -> Optional[FileNode]:
        """
        Get a node by path.
        
        Args:
            path: Path of the file
            
        Returns:
            FileNode if it exists, None otherwise
        """
        return self._nodes.get(path)
    
    def get_edge(self, source: str, target: str) -> Optional[DependencyMetadata]:
        """
        Get the metadata for an edge.
        
        Args:
            source: Path of the source file
            target: Path of the target file
            
        Returns:
            DependencyMetadata if the edge exists, None otherwise
        """
        if source in self._outgoing and target in self._outgoing[source]:
            return self._outgoing[source][target]
        return None
    
    def get_outgoing_edges(self, source: str) -> Dict[str, DependencyMetadata]:
        """
        Get all outgoing edges from a node.
        
        Args:
            source: Path of the source file
            
        Returns:
            Dictionary mapping target paths to dependency metadata
        """
        return self._outgoing.get(source, {}).copy()
    
    def get_incoming_edges(self, target: str) -> Dict[str, DependencyMetadata]:
        """
        Get all incoming edges to a node.
        
        Args:
            target: Path of the target file
            
        Returns:
            Dictionary mapping source paths to dependency metadata
        """
        return self._incoming.get(target, {}).copy()

    def successors(self, path: str) -> Iterator[str]:
        """
        Get an iterator over the successors of a node.
        
        Args:
            path: Path of the file
            
        Returns:
            Iterator over the successors of the node
        """
        return iter(self._outgoing.get(path, {}))
    
    def remove_node(self, path: str) -> None:
        """
        Remove a node and all its edges from the graph.
        
        Args:
            path: Path of the file to remove
        """
        if path not in self._nodes:
            return
        
        # Remove all outgoing edges
        for target in list(self._outgoing.get(path, {}).keys()):
            if target in self._incoming and path in self._incoming[target]:
                del self._incoming[target][path]
        
        # Remove all incoming edges
        for source in list(self._incoming.get(path, {}).keys()):
            if source in self._outgoing and path in self._outgoing[source]:
                del self._outgoing[source][path]
        
        # Remove the node
        del self._nodes[path]
        if path in self._outgoing:
            del self._outgoing[path]
        if path in self._incoming:
            del self._incoming[path]
        
        self.modified_at = time.time()
    
    def has_path(self, source: str, target: str, max_depth: int = 100) -> bool:
        """
        Check if there is a path from source to target.
        
        Args:
            source: Path of the source file
            target: Path of the target file
            max_depth: Maximum path length to consider
            
        Returns:
            True if there is a path, False otherwise
        """
        if source not in self._nodes or target not in self._nodes:
            return False
        
        if source == target:
            return True
        
        visited = set()
        queue = [(source, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            
            if current == target:
                return True
            
            if current in visited or depth >= max_depth:
                continue
            
            visited.add(current)
            
            for next_node in self._outgoing.get(current, {}):
                if next_node not in visited:
                    queue.append((next_node, depth + 1))
        
        return False
    
    def find_cycles(self) -> List[List[str]]:
        """
        Find all cycles in the graph.
        
        Returns:
            List of cycles, where each cycle is a list of node paths
        """
        cycles = []
        visited = set()
        path = []
        path_set = set()
        
        def dfs(node):
            if node in path_set:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            path_set.add(node)
            
            for next_node in self._outgoing.get(node, {}):
                dfs(next_node)
            
            path.pop()
            path_set.remove(node)
        
        for node in self._nodes:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def get_subgraph(self, paths: List[str]) -> 'DependencyGraph':
        """
        Extract a subgraph containing only the specified nodes and their edges.
        
        Args:
            paths: List of file paths to include
            
        Returns:
            A new DependencyGraph containing only the specified nodes and edges between them
        """
        subgraph = DependencyGraph()
        
        # Add nodes
        for path in paths:
            if path in self._nodes:
                subgraph.add_node(self._nodes[path])
        
        # Add edges
        for source in paths:
            for target in self._outgoing.get(source, {}):
                if target in paths:
                    subgraph.add_edge(source, target, self._outgoing[source][target])
        
        return subgraph
    
    def transitive_dependencies(self, path: str) -> Set[str]:
        """
        Get all transitive dependencies of a file.
        
        Args:
            path: Path of the file
            
        Returns:
            Set of paths of all files that this file directly or indirectly depends on
        """
        if path not in self._nodes:
            return set()
        
        result = set()
        queue = [path]
        visited = set()
        
        while queue:
            current = queue.pop(0)
            
            if current in visited:
                continue
            
            visited.add(current)
            
            for target in self._outgoing.get(current, {}):
                result.add(target)
                if target not in visited:
                    queue.append(target)
        
        return result
    
    def transitive_dependents(self, path: str) -> Set[str]:
        """
        Get all transitive dependents of a file.
        
        Args:
            path: Path of the file
            
        Returns:
            Set of paths of all files that directly or indirectly depend on this file
        """
        if path not in self._nodes:
            return set()
        
        result = set()
        queue = [path]
        visited = set()
        
        while queue:
            current = queue.pop(0)
            
            if current in visited:
                continue
            
            visited.add(current)
            
            for source in self._incoming.get(current, {}):
                result.add(source)
                if source not in visited:
                    queue.append(source)
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the graph to a dictionary representation.
        
        Returns:
            Dictionary representation of the graph
        """
        # Convert nodes
        nodes_dict = {path: node.to_dict() for path, node in self._nodes.items()}
        
        # Convert edges
        edges_list = []
        for source, targets in self._outgoing.items():
            for target, metadata in targets.items():
                edges_list.append({
                    "source": source,
                    "target": target,
                    "metadata": metadata.to_dict()
                })
        
        return {
            "version": self.version,
            "nodes": nodes_dict,
            "edges": edges_list,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DependencyGraph':
        """
        Create a graph from a dictionary representation.
        
        Args:
            data: Dictionary representation of the graph
            
        Returns:
            Reconstructed DependencyGraph
        """
        graph = cls(version=data.get("version", "1.0"))
        
        # Set timestamps
        graph.created_at = data.get("created_at", time.time())
        graph.modified_at = data.get("modified_at", time.time())
        
        # Add nodes
        for path, node_data in data.get("nodes", {}).items():
            graph.add_node(FileNode.from_dict(node_data))
        
        # Add edges
        for edge_data in data.get("edges", []):
            source = edge_data["source"]
            target = edge_data["target"]
            metadata = DependencyMetadata.from_dict(edge_data["metadata"])
            try:
                graph.add_edge(source, target, metadata)
            except ValueError:
                # Skip edges with missing nodes
                pass
        
        return graph
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Convert the graph to a JSON string.
        
        Args:
            indent: Indentation level for formatting
            
        Returns:
            JSON string representation of the graph
        """
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DependencyGraph':
        """
        Create a graph from a JSON string.
        
        Args:
            json_str: JSON string representation of the graph
            
        Returns:
            Reconstructed DependencyGraph
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __len__(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self._nodes)
    
    def __contains__(self, path: str) -> bool:
        """Check if a node exists in the graph."""
        return path in self._nodes
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over node paths in the graph."""
        return iter(self._nodes)
    
    def nodes(self) -> Iterator[FileNode]:
        """Iterate over nodes in the graph."""
        return iter(self._nodes.values())
    
    def edges(self) -> Iterator[DependencyEdge]:
        """Iterate over edges in the graph."""
        for source, targets in self._outgoing.items():
            for target, metadata in targets.items():
                yield DependencyEdge(source, target, metadata)
