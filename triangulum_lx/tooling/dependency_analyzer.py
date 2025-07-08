"""
Dependency analyzer for Triangulum.

Analyzes and maps dependencies between files to enable cascade-aware repairs.
"""

import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
import networkx as nx
import json

# Setup logging
logger = logging.getLogger("triangulum.dependency_analyzer")


class DependencyAnalyzer:
    """
    Analyzes dependencies between files in a codebase.
    
    This builds a dependency graph that represents imports and module relationships
    to enable cascade-aware repairs.
    """
    
    def __init__(self, 
                repo_path: str = ".",
                include_patterns: List[str] = None,
                exclude_patterns: List[str] = None):
        """
        Initialize the dependency analyzer.
        
        Args:
            repo_path: Path to the repository
            include_patterns: List of patterns to include
            exclude_patterns: List of patterns to exclude
        """
        self.repo_path = Path(repo_path)
        self.include_patterns = include_patterns or ["*.py", "*.js", "*.ts", "*.java", "*.go"]
        self.exclude_patterns = exclude_patterns or ["node_modules/**", "venv/**", "dist/**"]
        
        # The dependency graph
        self.graph = nx.DiGraph()
        
        # File to module mapping
        self.file_to_module: Dict[str, str] = {}
        self.module_to_file: Dict[str, str] = {}
        
        # Cache for imports
        self._import_cache: Dict[str, List[str]] = {}
    
    def build_graph(self) -> nx.DiGraph:
        """
        Build the dependency graph for the repository.
        
        Returns:
            Directed graph representing dependencies
        """
        self._find_all_files()
        self._analyze_dependencies()
        return self.graph
    
    def _find_all_files(self) -> None:
        """Find all files matching patterns."""
        import fnmatch
        
        logger.info(f"Scanning for files in {self.repo_path}")
        
        # Collect all files
        all_files = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.repo_path)
                
                # Check if file matches include patterns
                included = any(fnmatch.fnmatch(rel_path, pat) for pat in self.include_patterns)
                
                # Check if file matches exclude patterns
                excluded = any(fnmatch.fnmatch(rel_path, pat) for pat in self.exclude_patterns)
                
                if included and not excluded:
                    all_files.append(rel_path)
        
        logger.info(f"Found {len(all_files)} files to analyze")
        
        # Add all files to the graph
        for file in all_files:
            self.graph.add_node(file)
            self._map_file_to_module(file)
    
    def _map_file_to_module(self, file_path: str) -> None:
        """
        Map a file path to a module name.
        
        Args:
            file_path: Relative file path
        """
        # Python-specific mapping
        if file_path.endswith(".py"):
            # Convert path to module notation
            module_path = file_path.replace("/", ".").replace("\\", ".")
            # Remove .py extension
            module = module_path[:-3]
            # Handle __init__.py files
            if module.endswith(".__init__"):
                module = module[:-9]
                
            self.file_to_module[file_path] = module
            self.module_to_file[module] = file_path
            
        # JavaScript/TypeScript mapping
        elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            # Remove extension
            base_path = file_path.rsplit(".", 1)[0]
            # Handle index files
            if base_path.endswith("/index") or base_path.endswith("\\index"):
                base_path = base_path[:-6]
                
            module_name = base_path
            self.file_to_module[file_path] = module_name
            self.module_to_file[module_name] = file_path
    
    def _analyze_dependencies(self) -> None:
        """Analyze dependencies between files."""
        for file_path in list(self.graph.nodes):
            imports = self._extract_imports(file_path)
            
            for imported in imports:
                # If the import can be mapped to a file, add an edge
                if imported in self.module_to_file:
                    imported_file = self.module_to_file[imported]
                    # Add edge: file_path depends on imported_file
                    self.graph.add_edge(file_path, imported_file)
    
    def _extract_imports(self, file_path: str) -> List[str]:
        """
        Extract imports from a file.
        
        Args:
            file_path: File to extract imports from
            
        Returns:
            List of imported modules
        """
        # Check cache
        if file_path in self._import_cache:
            return self._import_cache[file_path]
        
        full_path = self.repo_path / file_path
        imports = []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if file_path.endswith(".py"):
                imports = self._extract_python_imports(content)
            elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
                imports = self._extract_js_imports(content)
            elif file_path.endswith((".java")):
                imports = self._extract_java_imports(content)
            elif file_path.endswith((".go")):
                imports = self._extract_go_imports(content)
                
        except Exception as e:
            logger.warning(f"Failed to extract imports from {file_path}: {e}")
        
        # Cache the result
        self._import_cache[file_path] = imports
        return imports
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract Python import statements."""
        imports = []
        
        # Match import statements
        import_pattern = r'^import\s+([\w.]+)(?:\s+as\s+\w+)?'
        from_pattern = r'^from\s+([\w.]+)\s+import'
        
        for line in content.split("\n"):
            line = line.strip()
            
            # Match import statements
            match = re.match(import_pattern, line)
            if match:
                imports.append(match.group(1))
                continue
                
            # Match from ... import statements
            match = re.match(from_pattern, line)
            if match:
                imports.append(match.group(1))
                
        return imports
    
    def _extract_js_imports(self, content: str) -> List[str]:
        """Extract JavaScript/TypeScript import statements."""
        imports = []
        
        # Match ES6 import statements
        import_pattern = r'import\s+.+\s+from\s+[\'"]([\.\/\w-]+)[\'"]'
        require_pattern = r'(?:const|let|var)\s+.+\s+=\s+require\([\'"]([\.\/\w-]+)[\'"]\)'
        
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))
            
        for match in re.finditer(require_pattern, content):
            imports.append(match.group(1))
            
        return imports
    
    def _extract_java_imports(self, content: str) -> List[str]:
        """Extract Java import statements."""
        imports = []
        
        # Match Java import statements
        import_pattern = r'import\s+([\w.]+)(?:\s*\*)?;'
        
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))
            
        return imports
    
    def _extract_go_imports(self, content: str) -> List[str]:
        """Extract Go import statements."""
        imports = []
        
        # Match Go import statements
        import_pattern = r'import\s+\(\s*((?:.|\n)+?)\s*\)'
        single_import_pattern = r'import\s+(?:"([^"]+)"|(\w+)\s+"([^"]+)")'
        
        # Multi-line imports
        for block_match in re.finditer(import_pattern, content):
            block = block_match.group(1)
            for line in block.split("\n"):
                line = line.strip()
                if line and not line.startswith("//"):
                    # Extract the import path
                    if '"' in line:
                        path = line.split('"')[1]
                        imports.append(path)
        
        # Single imports
        for match in re.finditer(single_import_pattern, content):
            if match.group(1):  # Simple case: import "path"
                imports.append(match.group(1))
            else:  # Named import: import alias "path"
                imports.append(match.group(3))
                
        return imports
    
    def get_dependent_files(self, file_path: str) -> Set[str]:
        """
        Get all files that depend on the given file.
        
        Args:
            file_path: File to find dependencies for
            
        Returns:
            Set of file paths that depend on the given file
        """
        if file_path not in self.graph:
            return set()
            
        # Files that import the target file (incoming edges)
        return set(self.graph.predecessors(file_path))
    
    def get_dependencies(self, file_path: str) -> Set[str]:
        """
        Get all files that the given file depends on.
        
        Args:
            file_path: File to find dependencies for
            
        Returns:
            Set of file paths that the given file depends on
        """
        if file_path not in self.graph:
            return set()
            
        # Files imported by the target file (outgoing edges)
        return set(self.graph.successors(file_path))
    
    def get_strongly_connected_components(self) -> List[Set[str]]:
        """
        Get strongly connected components in the dependency graph.
        
        Returns:
            List of sets containing nodes in each SCC
        """
        return list(nx.strongly_connected_components(self.graph))
    
    def get_repair_batches(self) -> List[Set[str]]:
        """
        Get optimal repair batches.
        
        Uses Tarjan's algorithm to find SCCs, then uses topological sort
        to determine the optimal repair order.
        
        Returns:
            List of sets of files, where each set is a repair batch
        """
        # Get strongly connected components
        sccs = list(nx.strongly_connected_components(self.graph))
        
        # Create a condensation graph (each SCC becomes a node)
        condensation = nx.condensation(self.graph, sccs)
        
        # Get topological sort of the condensation graph
        try:
            topo_order = list(nx.topological_sort(condensation))
        except nx.NetworkXUnfeasible:
            # Handle cycles if any remain (shouldn't happen after SCC)
            logger.warning("Cycles detected in condensation graph; using approximate ordering")
            topo_order = list(range(len(sccs)))
        
        # Return SCCs in topological order
        return [sccs[component_id] for component_id in topo_order]
    
    def save_graph(self, output_file: str = "dependency_graph.json") -> None:
        """
        Save the dependency graph to a file.
        
        Args:
            output_file: Path to save the graph to
        """
        # Convert the graph to a dictionary
        data = {
            "nodes": list(self.graph.nodes()),
            "edges": list(self.graph.edges())
        }
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved dependency graph to {output_file}")
    
    def load_graph(self, input_file: str) -> bool:
        """
        Load the dependency graph from a file.
        
        Args:
            input_file: Path to load the graph from
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            # Read from file
            with open(input_file, 'r') as f:
                data = json.load(f)
            
            # Create a new graph
            self.graph = nx.DiGraph()
            
            # Add nodes and edges
            self.graph.add_nodes_from(data["nodes"])
            self.graph.add_edges_from(data["edges"])
            
            logger.info(f"Loaded dependency graph from {input_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load dependency graph: {e}")
            return False


def analyze_dependencies(repo_path: str = ".",
                        include_patterns: List[str] = None,
                        exclude_patterns: List[str] = None) -> DependencyAnalyzer:
    """
    Analyze dependencies in a repository.
    
    Args:
        repo_path: Path to the repository
        include_patterns: List of file patterns to include
        exclude_patterns: List of file patterns to exclude
        
    Returns:
        DependencyAnalyzer instance with the built graph
    """
    analyzer = DependencyAnalyzer(
        repo_path=repo_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns
    )
    
    analyzer.build_graph()
    return analyzer


def get_repair_cascades(affected_files: List[str], repo_path: str = ".") -> List[Set[str]]:
    """
    Get the optimal repair order for a set of affected files.
    
    Args:
        affected_files: List of files that need to be repaired
        repo_path: Path to the repository
        
    Returns:
        List of sets representing repair batches
    """
    # Build dependency graph
    analyzer = analyze_dependencies(repo_path)
    
    # Create subgraph with only the affected files
    subgraph = analyzer.graph.subgraph(affected_files)
    
    # Get strongly connected components
    sccs = list(nx.strongly_connected_components(subgraph))
    
    # Create a condensation graph (each SCC becomes a node)
    condensation = nx.condensation(subgraph, sccs)
    
    # Get topological sort of the condensation graph
    try:
        topo_order = list(nx.topological_sort(condensation))
    except nx.NetworkXUnfeasible:
        logger.warning("Cycles detected in condensation graph; using approximate ordering")
        topo_order = list(range(len(sccs)))
    
    # Return SCCs in topological order
    return [sccs[component_id] for component_id in topo_order]
