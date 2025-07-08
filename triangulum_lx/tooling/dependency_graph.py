"""
Dependency graph implementation for large-scale codebase analysis.

This module provides functionality to build and analyze dependency graphs
for large codebases, supporting incremental analysis and prioritization.
"""

import os
import re
import ast
import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Iterator, Union, Callable
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import networkx as nx

from .graph_models import (
    DependencyGraph, FileNode, DependencyMetadata, 
    DependencyType, LanguageType, DependencyEdge
)

logger = logging.getLogger(__name__)


class BaseDependencyParser:
    """Base class for language-specific dependency parsers."""
    
    def __init__(self):
        """Initialize the parser."""
        self.language = LanguageType.UNKNOWN
    
    def parse_file(self, file_path: str, root_dir: str) -> List[Tuple[str, DependencyMetadata]]:
        """
        Parse a file and extract its dependencies.
        
        Args:
            file_path: Path to the file to parse
            root_dir: The root directory of the project for resolving imports
            
        Returns:
            List of (target_path, metadata) tuples representing dependencies
        """
        raise NotImplementedError("Subclasses must implement parse_file")
    
    def can_parse(self, file_path: str) -> bool:
        """
        Check if this parser can parse the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this parser can parse the file, False otherwise
        """
        extension = os.path.splitext(file_path)[1].lower()
        return LanguageType.from_extension(extension) == self.language


class PythonDependencyParser(BaseDependencyParser):
    """Parser for extracting dependencies from Python files."""
    
    def __init__(self):
        """Initialize the parser."""
        super().__init__()
        self.language = LanguageType.PYTHON
    
    def parse_file(self, file_path: str, root_dir: str) -> List[Tuple[str, DependencyMetadata]]:
        """
        Parse a Python file and extract its dependencies.
        
        Args:
            file_path: Path to the file to parse (relative to root_dir)
            root_dir: The root directory of the project for resolving imports
            
        Returns:
            List of (target_path, metadata) tuples representing dependencies
        """
        dependencies = []
        full_path = os.path.join(root_dir, file_path)
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=full_path)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        module_name = name.name
                        dep = self._process_import(module_name, node.lineno, file_path, root_dir)
                        if dep:
                            dependencies.append(dep)
                
                elif isinstance(node, ast.ImportFrom):
                    level = node.level
                    module_name = node.module or ''
                    
                    for name in node.names:
                        symbol = name.name
                        if level > 0:
                            base_path = Path(file_path).parent
                            for _ in range(level - 1):
                                base_path = base_path.parent
                            
                            relative_module_path = ".".join(base_path.parts)
                            full_module_name = f"{relative_module_path}.{module_name}" if module_name else relative_module_path
                        else:
                            full_module_name = module_name

                        dep = self._process_import(
                            full_module_name,
                            node.lineno,
                            file_path,
                            root_dir,
                            is_from=True,
                            symbol=symbol
                        )
                        if dep:
                            dependencies.append(dep)
        
        except Exception as e:
            logger.warning(f"Error parsing Python file {file_path}: {str(e)}")
        
        return [dep for dep in dependencies if dep is not None]

    def _process_import(
        self, 
        module_name: str, 
        line_no: int,
        current_file_path: str,
        root_dir: str,
        is_from: bool = False, 
        symbol: Optional[str] = None
    ) -> Optional[Tuple[str, DependencyMetadata]]:
        if self._is_standard_lib(module_name) or self._is_external_lib(module_name):
            return None
        
        file_path = self._module_to_path(module_name, root_dir, os.path.dirname(current_file_path))
        if not file_path:
            return None
        
        symbols = [symbol] if symbol else []
        
        metadata = DependencyMetadata(
            dependency_type=DependencyType.IMPORT,
            source_lines=[line_no],
            symbols=symbols,
            verified=True,
            confidence=1.0,
            additional_info={"is_from_import": is_from}
        )
        
        return file_path, metadata

    def _is_standard_lib(self, module_name: str) -> bool:
        std_libs = {
            "os", "sys", "time", "datetime", "math", "random", "re", "json",
            "collections", "itertools", "functools", "logging", "io", "pathlib",
            "threading", "multiprocessing", "concurrent", "subprocess", "tempfile",
            "shutil", "pickle", "csv", "hashlib", "uuid", "argparse", "enum"
        }
        return module_name.split('.')[0] in std_libs

    def _is_external_lib(self, module_name: str) -> bool:
        external_libs = {
            "numpy", "pandas", "matplotlib", "scipy", "sklearn", "tensorflow",
            "torch", "django", "flask", "requests", "bs4", "sqlalchemy", "pytest",
            "networkx", "asyncio", "aiohttp", "openai"
        }
        return module_name.split('.')[0] in external_libs

    def _module_to_path(self, module_name: str, root_dir: str, current_dir: str) -> Optional[str]:
        if ' ' in module_name:
            module_name = module_name.split(' ')[0]

        parts = module_name.split('.')
        
        potential_path_from_root = os.path.join(root_dir, *parts)
        
        path = potential_path_from_root + '.py'
        if os.path.exists(path):
            return os.path.relpath(path, root_dir)
        
        path = os.path.join(potential_path_from_root, '__init__.py')
        if os.path.exists(path):
            return os.path.relpath(path, root_dir)

        potential_path_from_current = os.path.join(root_dir, current_dir, *parts)
        path = potential_path_from_current + '.py'
        if os.path.exists(path):
            return os.path.relpath(path, root_dir)
            
        path = os.path.join(potential_path_from_current, '__init__.py')
        if os.path.exists(path):
            return os.path.relpath(path, root_dir)

        return None


class JavaScriptDependencyParser(BaseDependencyParser):
    """Parser for extracting dependencies from JavaScript files."""
    
    def __init__(self):
        """Initialize the parser."""
        super().__init__()
        self.language = LanguageType.JAVASCRIPT
        
        self.import_regex = re.compile(
            r'(?:import\s+(?:(?:\{[^}]*\})|(?:[^{}\s]+))\s+from\s+[\'"]([^\'"]*)[\'"]);?'
            r'|(?:import\s+[\'"]([^\'"]*)[\'"];?)'
            r'|(?:require\([\'"]([^\'"]*)[\'"]\))'
        )
        
        self.export_from_regex = re.compile(
            r'export\s+(?:\{[^}]*\})\s+from\s+[\'"]([^\'"]*)[\'"];?'
        )
    
    def parse_file(self, file_path: str, root_dir: str) -> List[Tuple[str, DependencyMetadata]]:
        dependencies = []
        full_path = os.path.join(root_dir, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for i, line in enumerate(content.splitlines()):
                line_no = i + 1
                
                for match in self.import_regex.finditer(line):
                    module_path = match.group(1) or match.group(2) or match.group(3)
                    if module_path:
                        dep = self._process_import(module_path, line_no, file_path, root_dir)
                        if dep:
                            dependencies.append(dep)
                
                for match in self.export_from_regex.finditer(line):
                    module_path = match.group(1)
                    if module_path:
                        dep = self._process_import(module_path, line_no, file_path, root_dir, is_export=True)
                        if dep:
                            dependencies.append(dep)
        
        except Exception as e:
            logger.warning(f"Error parsing JavaScript file {file_path}: {str(e)}")
        
        return dependencies
    
    def _process_import(
        self, 
        module_path: str, 
        line_no: int,
        current_file_path: str,
        root_dir: str,
        is_export: bool = False
    ) -> Optional[Tuple[str, DependencyMetadata]]:
        if not module_path.startswith('.'):
            return None
        
        file_path = self._resolve_import_path(module_path, os.path.dirname(current_file_path), root_dir)
        if not file_path:
            return None
        
        metadata = DependencyMetadata(
            dependency_type=DependencyType.IMPORT,
            source_lines=[line_no],
            symbols=[],
            verified=True,
            confidence=0.9,
            additional_info={"is_export": is_export}
        )
        
        return file_path, metadata
    
    def _resolve_import_path(self, module_path: str, current_dir: str, root_dir: str) -> Optional[str]:
        resolved_path = os.path.normpath(os.path.join(current_dir, module_path))
        
        possible_paths = [
            resolved_path,
            f"{resolved_path}.js",
            f"{resolved_path}.jsx",
            os.path.join(resolved_path, "index.js"),
            os.path.join(resolved_path, "index.jsx")
        ]
        
        for path in possible_paths:
            if os.path.exists(os.path.join(root_dir, path)):
                return path
        
        return None


class TypeScriptDependencyParser(JavaScriptDependencyParser):
    """Parser for extracting dependencies from TypeScript files."""
    
    def __init__(self):
        """Initialize the parser."""
        super().__init__()
        self.language = LanguageType.TYPESCRIPT
    
    def _resolve_import_path(self, module_path: str, current_dir: str, root_dir: str) -> Optional[str]:
        js_path = super()._resolve_import_path(module_path, current_dir, root_dir)
        if js_path:
            return js_path
        
        resolved_path = os.path.normpath(os.path.join(current_dir, module_path))

        possible_paths = [
            f"{resolved_path}.ts",
            f"{resolved_path}.tsx",
            os.path.join(resolved_path, "index.ts"),
            os.path.join(resolved_path, "index.tsx")
        ]
        
        for path in possible_paths:
            if os.path.exists(os.path.join(root_dir, path)):
                return path
        
        return None


class ParserRegistry:
    """Registry of available dependency parsers."""
    
    def __init__(self):
        """Initialize the registry with default parsers."""
        self.parsers: List[BaseDependencyParser] = [
            PythonDependencyParser(),
            JavaScriptDependencyParser(),
            TypeScriptDependencyParser(),
        ]
    
    def get_parser_for_file(self, file_path: str) -> Optional[BaseDependencyParser]:
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        return None
    
    def register_parser(self, parser: BaseDependencyParser) -> None:
        self.parsers.append(parser)


class DependencyGraphBuilder:
    """
    Builder for constructing dependency graphs from codebases.
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_workers: int = 4,
        parser_registry: Optional[ParserRegistry] = None
    ):
        self.cache_dir = cache_dir
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        
        self.max_workers = max_workers
        self.parser_registry = parser_registry or ParserRegistry()
    
    def build_graph(
        self,
        root_dir: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        incremental: bool = True,
        previous_graph: Optional[DependencyGraph] = None,
    ) -> DependencyGraph:
        start_time = time.time()
        
        graph = previous_graph or DependencyGraph()
        
        files = self._find_files(root_dir, include_patterns, exclude_patterns)
        logger.info(f"Found {len(files)} files to analyze")
        
        if incremental and previous_graph:
            files_to_process = self._identify_changed_files(files, previous_graph, root_dir)
            dependent_files = set()
            for file_path in files_to_process:
                if file_path in previous_graph:
                    dependents = previous_graph.transitive_dependents(file_path)
                    dependent_files.update(dependents)
            files_to_process.update(dependent_files)
            
            for path in list(previous_graph):
                if path not in files:
                    previous_graph.remove_node(path)
            
            logger.info(f"Incremental analysis: processing {len(files_to_process)} changed files")
        else:
            files_to_process = set(files)
            logger.info(f"Full analysis: processing all {len(files)} files")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for file_path in files:
                language = LanguageType.from_extension(os.path.splitext(file_path)[1])
                node = FileNode(path=file_path, language=language)
                graph.add_node(node)
            
            future_to_file = {
                executor.submit(self._process_file, file_path, graph, root_dir): file_path
                for file_path in files_to_process
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
        
        end_time = time.time()
        logger.info(f"Graph construction completed in {end_time - start_time:.2f} seconds")
        
        if self.cache_dir:
            self._cache_graph(graph, root_dir)
        
        return graph
    
    def _find_files(
        self,
        root_dir: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[str]:
        import fnmatch
        
        include_patterns = include_patterns or ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx', '*.java']
        exclude_patterns = exclude_patterns or ['**/node_modules/**', '**/__pycache__/**', '**/.git/**']
        
        files = []
        
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if any(fnmatch.fnmatch(dirpath, pattern) for pattern in exclude_patterns):
                continue
            
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                
                if not any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
                    continue
                
                if any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns):
                    continue
                
                rel_path = os.path.relpath(file_path, root_dir)
                files.append(rel_path)
        
        return files
    
    def _identify_changed_files(
        self,
        files: List[str],
        previous_graph: DependencyGraph,
        root_dir: str
    ) -> Set[str]:
        changed_files = set()
        
        for file_path in files:
            if file_path not in previous_graph:
                changed_files.add(file_path)
                continue
            
            node = previous_graph.get_node(file_path)
            if node and node.has_changed(root_dir):
                changed_files.add(file_path)
        
        return changed_files
    
    def _process_file(self, file_path: str, graph: DependencyGraph, root_dir: str) -> None:
        parser = self.parser_registry.get_parser_for_file(file_path)
        if not parser:
            return
        
        try:
            dependencies = parser.parse_file(file_path, root_dir)
            
            for target_path, metadata in dependencies:
                if target_path in graph:
                    graph.add_edge(file_path, target_path, metadata)
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
    
    def _cache_graph(self, graph: DependencyGraph, root_dir: str) -> None:
        if not self.cache_dir:
            return
        
        cache_name = f"dependency_graph_{hash(root_dir)}.json"
        cache_path = os.path.join(self.cache_dir, cache_name)
        
        try:
            with open(cache_path, 'w') as f:
                f.write(graph.to_json(indent=2))
            logger.info(f"Cached dependency graph to {cache_path}")
        except Exception as e:
            logger.error(f"Error caching graph: {str(e)}")
    
    def load_cached_graph(self, root_dir: str) -> Optional[DependencyGraph]:
        if not self.cache_dir:
            return None
        
        cache_name = f"dependency_graph_{hash(root_dir)}.json"
        cache_path = os.path.join(self.cache_dir, cache_name)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                graph = DependencyGraph.from_json(f.read())
            logger.info(f"Loaded cached dependency graph from {cache_path}")
            return graph
        except Exception as e:
            logger.error(f"Error loading cached graph: {str(e)}")
            return None


class DependencyAnalyzer:
    """
    Analyzer for extracting insights from dependency graphs.
    """
    def visualize_graph(self, output_path: str, layout: str = 'spring') -> None:
        import matplotlib.pyplot as plt

        G = self.networkx_graph
        
        plt.figure(figsize=(20, 20))
        
        if layout == 'spring':
            pos = nx.spring_layout(G, k=0.15, iterations=20)
        elif layout == 'circular':
            pos = nx.circular_layout(G)
        elif layout == 'kamada_kawai':
            pos = nx.kamada_kawai_layout(G)
        else:
            pos = nx.spring_layout(G)
            
        nx.draw(G, pos, with_labels=True, node_size=50, font_size=8, arrows=True)
        plt.savefig(output_path)
        plt.close()
    
    def __init__(self, graph: DependencyGraph):
        self.graph = graph
        self._networkx_graph = None
    
    @property
    def networkx_graph(self) -> nx.DiGraph:
        if self._networkx_graph is None:
            self._networkx_graph = nx.DiGraph()
            
            for node_path in self.graph:
                node = self.graph.get_node(node_path)
                if node:
                    self._networkx_graph.add_node(node.path, **node.to_dict())

            for edge in self.graph.edges():
                self._networkx_graph.add_edge(
                    edge.source, edge.target, 
                    **edge.metadata.to_dict()
                )
        
        return self._networkx_graph
    
    def calculate_centrality(self) -> Dict[str, Dict[str, float]]:
        G = self.networkx_graph
        
        in_degree = nx.in_degree_centrality(G)
        out_degree = nx.out_degree_centrality(G)
        betweenness = nx.betweenness_centrality(G)
        
        try:
            pagerank = nx.pagerank(G)
        except:
            pagerank = {node: 0.0 for node in G.nodes()}
        
        centrality = {}
        for node in G.nodes():
            centrality[node] = {
                'in_degree': in_degree.get(node, 0.0),
                'out_degree': out_degree.get(node, 0.0),
                'betweenness': betweenness.get(node, 0.0),
                'pagerank': pagerank.get(node, 0.0),
            }
        
        return centrality
    
    def find_cycles(self) -> List[List[str]]:
        return self.graph.find_cycles()
    
    def prioritize_files(
        self,
        files: List[str],
        prioritization_strategy: str = 'pagerank',
        additional_weights: Optional[Dict[str, float]] = None
    ) -> List[str]:
        if not files:
            return []
        
        additional_weights = additional_weights or {}
        
        if prioritization_strategy == 'pagerank':
            try:
                pagerank = nx.pagerank(self.networkx_graph)
                scores = {f: pagerank.get(f, 0.0) + additional_weights.get(f, 0.0) for f in files}
            except:
                in_degree = nx.in_degree_centrality(self.networkx_graph)
                scores = {f: in_degree.get(f, 0.0) + additional_weights.get(f, 0.0) for f in files}
        
        elif prioritization_strategy == 'in_degree':
            in_degree = nx.in_degree_centrality(self.networkx_graph)
            scores = {f: in_degree.get(f, 0.0) + additional_weights.get(f, 0.0) for f in files}
        
        elif prioritization_strategy == 'out_degree':
            out_degree = nx.out_degree_centrality(self.networkx_graph)
            scores = {f: out_degree.get(f, 0.0) + additional_weights.get(f, 0.0) for f in files}
        
        elif prioritization_strategy == 'betweenness':
            betweenness = nx.betweenness_centrality(self.networkx_graph)
            scores = {f: betweenness.get(f, 0.0) + additional_weights.get(f, 0.0) for f in files}
        
        else:
            scores = {f: additional_weights.get(f, 0.0) for f in files}
        
        return sorted(files, key=lambda f: scores.get(f, 0.0), reverse=True)
    
    def get_most_central_files(self, n: int = 10, metric: str = 'pagerank') -> List[Tuple[str, float]]:
        if metric == 'pagerank':
            try:
                scores = nx.pagerank(self.networkx_graph)
            except:
                scores = nx.in_degree_centrality(self.networkx_graph)
        
        elif metric == 'in_degree':
            scores = nx.in_degree_centrality(self.networkx_graph)
        
        elif metric == 'out_degree':
            scores = nx.out_degree_centrality(self.networkx_graph)
        
        elif metric == 'betweenness':
            scores = nx.betweenness_centrality(self.networkx_graph)
        
        else:
            raise ValueError(f"Unknown centrality metric: {metric}")
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]
    
    def get_strongly_connected_components(self) -> List[Set[str]]:
        return list(nx.strongly_connected_components(self.networkx_graph))
    
    def get_impact_score(self, file_path: str) -> float:
        if file_path not in self.graph:
            return 0.0
        
        dependents = self.graph.transitive_dependents(file_path)
        num_dependents = len(dependents)
        
        try:
            pagerank = nx.pagerank(self.networkx_graph)
            pr_score = pagerank.get(file_path, 0.0)
        except:
            in_degree = nx.in_degree_centrality(self.networkx_graph)
            pr_score = in_degree.get(file_path, 0.0)
        
        dependent_weight = 0.7 * (num_dependents / max(len(self.graph), 1))
        centrality_weight = 0.3 * pr_score
        
        return dependent_weight + centrality_weight
