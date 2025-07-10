"""
Dependency Graph Builder and Analyzer for Triangulum.

Builds and analyzes dependency graphs between files to enable cascade-aware repairs.
"""

import re
import os
import logging
import time # Added import
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
import networkx as nx
import json
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque # Keep for parsers if still needed

# Setup logging
logger = logging.getLogger("triangulum.dependency_graph")

from triangulum_lx.tooling.fs_ops import atomic_write
from triangulum_lx.core.fs_state import FileSystemStateCache

# --- Import canonical graph models ---
from .graph_models import (
    LanguageType,
    FileNode,
    DependencyType,
    DependencyMetadata,
    DependencyGraph # Canonical DependencyGraph
)
# --- End Import canonical graph models ---

class BaseDependencyParser:
    """Base class for language-specific dependency parsers."""
    def __init__(self):
        self.language = LanguageType.UNKNOWN

    def parse_file(self, file_path: str, root_dir: str) -> List[Tuple[str, DependencyMetadata]]:
        raise NotImplementedError("Subclasses must implement parse_file")

    def can_parse(self, file_path: str) -> bool:
        extension = os.path.splitext(file_path)[1].lower()
        # Assuming LanguageType.from_extension is part of graph_models.LanguageType
        return LanguageType.from_extension(extension) == self.language

class PythonDependencyParser(BaseDependencyParser):
    """Parser for extracting dependencies from Python files."""
    def __init__(self):
        super().__init__()
        self.language = LanguageType.PYTHON

    def parse_file(self, file_path: str, root_dir: str) -> List[Tuple[str, DependencyMetadata]]:
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
                        if dep: dependencies.append(dep)
                elif isinstance(node, ast.ImportFrom):
                    level = node.level # 0 for absolute, 1 for '.', 2 for '..'
                    module_name_in_from = node.module  # e.g., 'config' in 'from .config import X', or None in 'from . import helpers'

                    current_file_path_obj = Path(file_path)
                    current_dir_parts = list(current_file_path_obj.parent.parts) # e.g., ['mypackage', 'utils']

                    base_path_parts = []
                    if level > 0: # Relative import
                        # For 'from .mod import X', level=1. slice_idx = len(current_dir_parts)
                        # For 'from ..mod import X', level=2. slice_idx = len(current_dir_parts) - 1
                        slice_idx = len(current_dir_parts) - (level - 1)
                        if slice_idx < 0:
                            logger.debug(f"Relative import level {level} is too high for path {file_path} with current_dir_parts {current_dir_parts}")
                            continue
                        base_path_parts = current_dir_parts[:slice_idx]

                    # If level is 0 (absolute import), base_path_parts remains empty, module_name_in_from is the start.

                    for alias in node.names: # ast.alias objects (name, asname)
                        imported_symbol_name = alias.name # The name being imported, could be module or variable/class/func

                        module_to_resolve_parts = list(base_path_parts) # Start with relative base

                        if module_name_in_from: # e.g., 'from .config import X' or 'from package import module'
                            module_to_resolve_parts.extend(module_name_in_from.split('.'))
                            symbol_for_metadata = imported_symbol_name # We are importing a symbol from this module
                        else: # e.g., 'from . import helpers' or 'from . import subpackage.module'
                              # Here, imported_symbol_name is the module/package relative to base_path_parts
                            module_to_resolve_parts.append(imported_symbol_name)
                            symbol_for_metadata = None # We are importing the module itself as the primary target

                        # Filter out empty parts that might arise from ".." resolving to above project root if not careful,
                        # or from multiple dots in module_name_in_from.
                        module_to_resolve_parts_cleaned = [part for part in module_to_resolve_parts if part]
                        if not module_to_resolve_parts_cleaned:
                            logger.debug(f"Could not determine module to resolve for import in {file_path} (line {node.lineno})")
                            continue

                        module_to_resolve_str = ".".join(module_to_resolve_parts_cleaned)

                        dep = self._process_import(module_to_resolve_str, node.lineno, file_path, root_dir,
                                                   is_from=True, symbol=symbol_for_metadata)
                        if dep:
                            dependencies.append(dep)
        except Exception as e:
            logger.warning(f"Error parsing Python file {file_path}: {str(e)}", exc_info=True) # Add exc_info
        return dependencies

    def _process_import(self, module_name: str, line_no: int, current_file_path: str, root_dir: str, is_from: bool = False, symbol: Optional[str] = None) -> Optional[Tuple[str, DependencyMetadata]]:
        if self._is_standard_lib(module_name) or self._is_external_lib(module_name):
            return None
        resolved_target_path = self._module_to_path(module_name, root_dir, Path(current_file_path).parent.as_posix())
        if not resolved_target_path:
            return None
        symbols = [symbol] if symbol else []
        # Use canonical DependencyMetadata and DependencyType
        metadata = DependencyMetadata(
            dependency_type=DependencyType.IMPORT,
            source_lines=[line_no], symbols=symbols, verified=False, confidence=0.8,
            additional_info={"is_from_import": is_from, "original_import_name": module_name}
        )
        return resolved_target_path, metadata

    def _is_standard_lib(self, module_name: str) -> bool:
        std_libs_prefixes = {"os", "sys", "time", "datetime", "math", "random", "re", "json", "collections", "itertools", "functools", "logging", "io", "pathlib", "threading", "multiprocessing", "concurrent", "subprocess", "tempfile", "shutil", "pickle", "csv", "hashlib", "uuid", "argparse", "enum", "ast", "unittest", "doctest", "zipfile", "tarfile", "gzip", "bz2", "lzma", "socket", "ssl", "http", "urllib", "xml", "ctypes", "struct", "select", "asyncio"}
        return module_name.split('.')[0] in std_libs_prefixes

    def _is_external_lib(self, module_name: str) -> bool:
        external_libs_prefixes = {"numpy", "pandas", "matplotlib", "scipy", "sklearn", "tensorflow", "torch", "django", "flask", "requests", "bs4", "sqlalchemy", "pytest", "networkx", "openai", "werkzeug"}
        return module_name.split('.')[0] in external_libs_prefixes

    def _module_to_path(self, module_name: str, root_dir: str, current_file_dir_rel: str) -> Optional[str]:
        if not module_name: # An empty module name might occur from `from . import foo` at root.
            # If current_file_dir_rel is '.' or empty, this means current file is at root.
            # An import like `from . import bar` at root would mean module `bar`.
            # This case should ideally be handled by `full_module_name` construction.
            # If module_name is truly empty, it's likely an unresolvable scenario for this simplified resolver.
            return None

        parts = module_name.split('.')
        potential_path_from_root_parts = parts
        path_py = Path(root_dir, *potential_path_from_root_parts).with_suffix(".py")
        if path_py.exists():
            return path_py.relative_to(root_dir).as_posix()
        path_init = Path(root_dir, *potential_path_from_root_parts, "__init__.py")
        if path_init.exists():
            return path_init.relative_to(root_dir).as_posix()
        return None

class JavaScriptDependencyParser(BaseDependencyParser):
    def __init__(self, lang_type=LanguageType.JAVASCRIPT):
        super().__init__()
        self.language = lang_type
        self.import_regex = re.compile(r'(?:import\s+(?:[^;]*\s+from\s+)?[\'"]([^\'"\n]+)[\'"])|(?:require\s*\(\s*[\'"]([^\'"\n]+)[\'"]\s*\))')
        self.export_from_regex = re.compile(r'export\s+(?:[^;]*\s+from\s+)?[\'"]([^\'"\n]+)[\'"]')

    def parse_file(self, file_path: str, root_dir: str) -> List[Tuple[str, DependencyMetadata]]:
        dependencies = []
        full_path = os.path.join(root_dir, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f: content = f.read()
            lines = content.splitlines()
            for line_no_idx, line_content in enumerate(lines):
                line_no = line_no_idx + 1
                for match in self.import_regex.finditer(line_content):
                    module_specifier = match.group(1) or match.group(2)
                    if module_specifier:
                        dep = self._process_import(module_specifier, line_no, file_path, root_dir, is_export=False)
                        if dep: dependencies.append(dep)
                for match in self.export_from_regex.finditer(line_content):
                    module_specifier = match.group(1)
                    if module_specifier:
                        dep = self._process_import(module_specifier, line_no, file_path, root_dir, is_export=True)
                        if dep: dependencies.append(dep)
        except Exception as e:
            logger.warning(f"Error parsing JS/TS file {file_path}: {str(e)}")
        return dependencies

    def _process_import(self, module_specifier: str, line_no: int, current_file_path: str, root_dir: str, is_export: bool = False) -> Optional[Tuple[str, DependencyMetadata]]:
        if not module_specifier.startswith('.') or ':' in module_specifier: return None
        resolved_target_path = self._resolve_import_path(module_specifier, Path(current_file_path).parent.as_posix(), root_dir)
        if not resolved_target_path: return None
        metadata = DependencyMetadata(dependency_type=DependencyType.IMPORT, source_lines=[line_no], symbols=[], verified=False, confidence=0.7, additional_info={"is_export_from": is_export, "original_import_specifier": module_specifier})
        return resolved_target_path, metadata

    def _resolve_import_path(self, module_specifier: str, current_file_dir_rel: str, root_dir: str) -> Optional[str]:
        base_target_path = Path(root_dir, current_file_dir_rel, module_specifier).resolve()
        extensions_to_try = [".ts", ".tsx", ".js", ".jsx", ".json"] if self.language == LanguageType.TYPESCRIPT else [".js", ".jsx", ".json"]
        for ext in extensions_to_try:
            potential_file_path = base_target_path.with_suffix(ext)
            if potential_file_path.is_file() and str(potential_file_path).startswith(str(Path(root_dir).resolve())): # Check if it's within root
                return potential_file_path.relative_to(root_dir).as_posix()
        if base_target_path.is_dir():
            for ext in extensions_to_try:
                potential_index_path = base_target_path / f"index{ext}"
                if potential_index_path.is_file() and str(potential_index_path).startswith(str(Path(root_dir).resolve())):
                    return potential_index_path.relative_to(root_dir).as_posix()
        return None

class TypeScriptDependencyParser(JavaScriptDependencyParser):
    def __init__(self):
        super().__init__(lang_type=LanguageType.TYPESCRIPT)

class ParserRegistry:
    def __init__(self):
        self.parsers: List[BaseDependencyParser] = [PythonDependencyParser(), JavaScriptDependencyParser(), TypeScriptDependencyParser()]
    def get_parser_for_file(self, file_path: str) -> Optional[BaseDependencyParser]:
        lang_type = LanguageType.from_extension(os.path.splitext(file_path)[1])
        for parser in self.parsers:
            if parser.language == lang_type and parser.can_parse(file_path): return parser
        for parser in self.parsers: # Fallback for complex extensions like .jsx
            if parser.can_parse(file_path): return parser
        logger.debug(f"No parser found for file: {file_path} (lang_type: {lang_type.name if lang_type else 'N/A'})")
        return None
    def register_parser(self, parser: BaseDependencyParser): self.parsers.append(parser)

class DependencyGraphBuilder:
    def __init__(self, cache_dir: Optional[str] = None, max_workers: int = 4, parser_registry: Optional[ParserRegistry] = None, fs_cache: Optional[FileSystemStateCache] = None):
        self.cache_dir = cache_dir
        if cache_dir: Path(cache_dir).mkdir(parents=True, exist_ok=True) # Direct mkdir for setup
        self.max_workers = max_workers
        self.parser_registry = parser_registry or ParserRegistry()
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()

    def build_graph(self, root_dir: str, include_patterns: Optional[List[str]] = None, exclude_patterns: Optional[List[str]] = None, incremental: bool = True, previous_graph_json_str: Optional[str] = None) -> DependencyGraph:
        start_time = time.time()
        graph: DependencyGraph
        if incremental and previous_graph_json_str:
            try:
                graph = DependencyGraph.from_json(previous_graph_json_str)
                logger.info("Successfully loaded and parsed previous graph from JSON string for incremental build.")
            except Exception as e:
                logger.warning(f"Failed to load previous graph from JSON string: {e}. Performing full build.")
                graph = DependencyGraph(version="1.0")
        else:
            graph = DependencyGraph(version="1.0") # Use canonical constructor, pass version
            if incremental: logger.info("No previous graph data, performing full build.")

        all_repo_files_rel_paths = self._find_files(root_dir, include_patterns, exclude_patterns)
        logger.info(f"Found {len(all_repo_files_rel_paths)} files to potentially analyze in {root_dir}")
        files_to_reprocess_paths: Set[str] = set(all_repo_files_rel_paths)

        if incremental and graph.version != "0.0_initial": # Check a field that indicates it's not a fresh graph
            changed_or_new_files = set()
            current_files_map: Dict[str, FileNode] = {}
            for rel_path in all_repo_files_rel_paths:
                abs_path = Path(root_dir, rel_path)
                if not abs_path.exists(): continue
                lang = LanguageType.from_extension(os.path.splitext(rel_path)[1])
                # Create canonical FileNode. Path for hashing should be absolute.
                node = FileNode(path=str(abs_path), language=lang, module_name=None)
                node.path = rel_path # Set path to relative for graph storage
                current_files_map[rel_path] = node
                prev_node_obj = graph.get_node(rel_path)
                if not prev_node_obj or node.file_hash != prev_node_obj.file_hash:
                    changed_or_new_files.add(rel_path)

            deleted_files = set(graph._nodes.keys()) - set(all_repo_files_rel_paths)
            if deleted_files:
                logger.info(f"Incremental: {len(deleted_files)} files deleted.")
                for df_path in deleted_files: graph.remove_node(df_path)

            files_to_reprocess_paths = changed_or_new_files
            logger.info(f"Incremental analysis: {len(files_to_reprocess_paths)} changed/new files to re-process.")

            for rel_path in all_repo_files_rel_paths:
                if rel_path in current_files_map: graph.add_node(current_files_map[rel_path])
        else:
            for file_path_rel in all_repo_files_rel_paths:
                lang = LanguageType.from_extension(os.path.splitext(file_path_rel)[1])
                abs_path = Path(root_dir, file_path_rel)
                node = FileNode(path=str(abs_path), language=lang, module_name=None)
                node.path = file_path_rel # Store relative path
                graph.add_node(node)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self._process_file_for_builder, rel_path, graph, root_dir): rel_path for rel_path in files_to_reprocess_paths}
            for future in as_completed(future_to_file):
                try: future.result()
                except Exception as e: logger.error(f"Error processing file {future_to_file[future]} in executor: {e}", exc_info=True)

        end_time = time.time()
        logger.info(f"Graph construction completed in {end_time - start_time:.2f} seconds. Graph has {len(graph)} nodes.")
        if self.cache_dir: self._cache_graph_data(graph, root_dir)
        return graph

    def _find_files(self, root_dir: str, include_patterns: Optional[List[str]], exclude_patterns: Optional[List[str]]) -> List[str]:
        import fnmatch
        include_patterns = include_patterns or ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx', '*.java', '*.go']
        # More robust default exclusions
        default_excludes = ['.git/', 'node_modules/', '__pycache__/', 'dist/', 'build/', '*.pyc', '*.pyo', '*.pyd', '*.class', '*.o', '*.obj', '*.so', '*.dll', '*.exe']
        effective_exclude_patterns = default_excludes + (exclude_patterns or [])

        found_files_rel_paths = []
        abs_root_dir = Path(root_dir).resolve()

        for dirpath_str, dirnames, filenames in os.walk(abs_root_dir, topdown=True):
            # Prune dirnames based on exclude patterns
            dirnames[:] = [d for d in dirnames if not any(fnmatch.fnmatch(d, pat.strip('*/')) or fnmatch.fnmatch(Path(dirpath_str, d).relative_to(abs_root_dir).as_posix() + '/', pat) for pat in effective_exclude_patterns if pat.endswith('/'))]

            for filename in filenames:
                file_path_abs = Path(dirpath_str, filename)
                file_path_rel = file_path_abs.relative_to(abs_root_dir).as_posix()

                is_excluded = any(fnmatch.fnmatch(file_path_rel, pat) or fnmatch.fnmatch(filename, pat.lstrip('**/')) for pat in effective_exclude_patterns)
                if is_excluded: continue

                if any(fnmatch.fnmatch(filename, pat) or fnmatch.fnmatch(file_path_rel, pat) for pat in include_patterns):
                    found_files_rel_paths.append(file_path_rel)
        return found_files_rel_paths

    def _process_file_for_builder(self, file_path_rel: str, graph: DependencyGraph, root_dir: str) -> None:
        parser = self.parser_registry.get_parser_for_file(file_path_rel)
        if not parser: return
        try:
            abs_root_dir = Path(root_dir).resolve().as_posix()
            # Clear old outgoing edges for this file before adding new ones in incremental mode
            # This requires a method in DependencyGraph or careful handling here.
            # For now, assuming add_edge overwrites or this is handled by reprocessing logic.
            # A robust way: graph.remove_outgoing_edges(file_path_rel) if such method exists.
            # If not, the current `add_edge` in canonical graph just overwrites, which is fine if all deps are found again.

            dependencies = parser.parse_file(file_path_rel, abs_root_dir)
            for target_path_rel, metadata in dependencies:
                if target_path_rel in graph: # Check against canonical graph
                    graph.add_edge(file_path_rel, target_path_rel, metadata) # Use canonical add_edge
                else:
                    logger.warning(f"Target dependency '{target_path_rel}' for '{file_path_rel}' not found in graph. Skipping edge.")
        except Exception as e:
            logger.error(f"Error parsing dependencies for {file_path_rel}: {e}", exc_info=True)

    def _cache_graph_data(self, graph: DependencyGraph, root_dir: str) -> None:
        if not self.cache_dir: return
        root_dir_hash_part = str(hash(Path(root_dir).resolve().as_posix()))[-8:]
        cache_name = f"dep_graph_cache_{Path(root_dir).name}_{root_dir_hash_part}.json"
        cache_path = Path(self.cache_dir, cache_name)
        try:
            graph_json_content = graph.to_json(indent=2) # Use canonical to_json
            atomic_write(str(cache_path), graph_json_content.encode('utf-8'))
            self.fs_cache.invalidate(str(cache_path))
            logger.info(f"Cached dependency graph data to {cache_path} using atomic_write")
        except Exception as e:
            logger.error(f"Error caching graph data: {e}", exc_info=True)

    def load_cached_graph_json_str(self, root_dir: str) -> Optional[str]:
        if not self.cache_dir: return None
        root_dir_hash_part = str(hash(Path(root_dir).resolve().as_posix()))[-8:]
        cache_name = f"dep_graph_cache_{Path(root_dir).name}_{root_dir_hash_part}.json"
        cache_path = Path(self.cache_dir, cache_name)

        # Use cache to check existence
        if not self.fs_cache.exists(str(cache_path)): # Check cache first
            # If cache says no, double check filesystem directly before giving up
            if not cache_path.exists():
                logger.info(f"No cache file found at {cache_path} (checked cache then FS).")
                return None
            else: # Cache was stale
                logger.warning(f"Cache indicated {cache_path} absent, but it exists. Invalidating and proceeding to load.")
                self.fs_cache.invalidate(str(cache_path)) # Correct the cache

        # At this point, file should exist if we are to load it
        try:
            with open(cache_path, 'r', encoding='utf-8') as f: json_str = f.read()
            logger.info(f"Loaded cached dependency graph JSON string from {cache_path}")
            return json_str
        except Exception as e:
            logger.error(f"Error loading cached graph JSON string from {cache_path}: {e}", exc_info=True)
            return None

class DependencyAnalyzer:
    def __init__(self, graph: DependencyGraph): # Takes canonical DependencyGraph
        self.graph_model = graph
        self._networkx_graph: Optional[nx.DiGraph] = None # Type hint

    def _ensure_networkx_graph(self):
        if self._networkx_graph is None:
            self._networkx_graph = nx.DiGraph()
            if self.graph_model:
                for f_node_obj in self.graph_model.nodes(): # Use canonical nodes()
                    attrs = f_node_obj.to_dict()
                    attrs['language'] = f_node_obj.language.name # Ensure string for nx
                    self._networkx_graph.add_node(f_node_obj.path, **attrs)
                for edge in self.graph_model.edges(): # Use canonical edges()
                    meta_dict = edge.metadata.to_dict()
                    meta_dict['dependency_type'] = edge.metadata.dependency_type.name # Ensure string
                    self._networkx_graph.add_edge(edge.source, edge.target, **meta_dict)
            else:
                logger.warning("DependencyGraph model is None, NetworkX graph will be empty.")

    @property
    def nx_graph(self) -> nx.DiGraph:
        self._ensure_networkx_graph()
        if self._networkx_graph is None: # Should be initialized by _ensure_networkx_graph
             logger.error("Networkx graph is None even after _ensure_networkx_graph call!")
             return nx.DiGraph() # Return empty graph to prevent errors
        return self._networkx_graph

    def get_dependent_files(self, file_path: str) -> Set[str]:
        self._ensure_networkx_graph()
        if file_path not in self.nx_graph:
            logger.warning(f"File '{file_path}' not found in NX graph for get_dependent_files.")
            return set()
        return set(self.nx_graph.predecessors(file_path))

    def get_dependencies(self, file_path: str) -> Set[str]:
        self._ensure_networkx_graph()
        if file_path not in self.nx_graph:
            logger.warning(f"File '{file_path}' not found in NX graph for get_dependencies.")
            return set()
        return set(self.nx_graph.successors(file_path))

    def get_strongly_connected_components(self) -> List[Set[str]]:
        self._ensure_networkx_graph()
        if not self.nx_graph or not self.nx_graph.nodes(): return []
        return list(nx.strongly_connected_components(self.nx_graph))

    def get_repair_batches(self) -> List[Set[str]]:
        self._ensure_networkx_graph()
        if not self.nx_graph or not self.nx_graph.nodes(): return []
        sccs = self.get_strongly_connected_components()
        if not sccs:
            if nx.is_directed_acyclic_graph(self.nx_graph):
                 return [{node} for node in nx.topological_sort(self.nx_graph)]
            return []
        condensation_graph_nx = nx.condensation(self.nx_graph, sccs=sccs)
        try:
            topo_order_scc_ids = list(nx.topological_sort(condensation_graph_nx))
            scc_id_to_files_map = {i: scc_set for i, scc_set in enumerate(sccs)}
            return [scc_id_to_files_map[scc_id] for scc_id in topo_order_scc_ids if scc_id in scc_id_to_files_map]
        except nx.NetworkXUnfeasible:
            logger.warning("Cycles in condensation graph; returning SCCs without strict topological order.")
            return sccs

    def visualize_graph(self, output_path: str, layout: str = 'spring') -> None:
        self._ensure_networkx_graph()
        if not self.nx_graph or not self.nx_graph.nodes():
            logger.warning("Graph is empty. Nothing to visualize.")
            return
        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(20, 20))
            if layout == 'spring': pos = nx.spring_layout(self.nx_graph, k=0.15, iterations=20)
            elif layout == 'circular': pos = nx.circular_layout(self.nx_graph)
            elif layout == 'kamada_kawai':
                if len(self.nx_graph) > 500: logger.warning("Kamada-Kawai slow for large graphs.")
                pos = nx.kamada_kawai_layout(self.nx_graph)
            else: pos = nx.spring_layout(self.nx_graph)
            nx.draw(self.nx_graph, pos, with_labels=True, node_size=max(50, int(2000/len(self.nx_graph)) if len(self.nx_graph)>0 else 50), font_size=max(6, int(100/len(self.nx_graph)) if len(self.nx_graph)>0 else 8), arrows=True, alpha=0.8, width=0.5)
            plt.savefig(output_path)
            plt.close()
            logger.info(f"Graph visualization saved to {output_path}")
        except ImportError: logger.error("Matplotlib not installed. Cannot visualize graph.")
        except Exception as e: logger.error(f"Error visualizing graph: {e}", exc_info=True)

    def calculate_centrality(self) -> Dict[str, Dict[str, float]]:
        self._ensure_networkx_graph()
        G = self.nx_graph
        if not G or not G.nodes(): return {}
        centrality = {}
        try:
            in_degree = nx.in_degree_centrality(G)
            out_degree = nx.out_degree_centrality(G)
            betweenness = nx.betweenness_centrality(G) if len(G) < 1000 else {n: 0.0 for n in G.nodes()}
            if len(G) >= 1000: logger.warning("Skipping betweenness centrality for large graph.")
            pagerank = nx.pagerank(G)
            for node in G.nodes():
                centrality[node] = {'in_degree': in_degree.get(node,0.0), 'out_degree': out_degree.get(node,0.0), 'betweenness': betweenness.get(node,0.0), 'pagerank': pagerank.get(node,0.0)}
        except Exception as e: logger.error(f"Error calculating centrality: {e}", exc_info=True)
        return centrality

    def prioritize_files(self, files_to_prioritize: List[str], prioritization_strategy: str = 'pagerank', additional_weights: Optional[Dict[str, float]] = None) -> List[str]:
        self._ensure_networkx_graph()
        G = self.nx_graph
        if not G or not G.nodes() or not files_to_prioritize: return files_to_prioritize
        additional_weights = additional_weights or {}
        scores = {f: 0.0 for f in files_to_prioritize}
        try:
            if prioritization_strategy == 'pagerank': computed_scores = nx.pagerank(G)
            elif prioritization_strategy == 'in_degree': computed_scores = {n: d for n, d in G.in_degree()}
            elif prioritization_strategy == 'out_degree': computed_scores = {n: d for n, d in G.out_degree()}
            elif prioritization_strategy == 'betweenness':
                if len(G) < 1000: computed_scores = nx.betweenness_centrality(G)
                else: logger.warning("Skipping betweenness for prioritization on large graph."); computed_scores = {n:0.0 for n in G.nodes()}
            else: computed_scores = {n: 0.0 for n in G.nodes()}
            for f_path in files_to_prioritize:
                scores[f_path] = (computed_scores.get(f_path, 0.0) if f_path in G else 0.0) + additional_weights.get(f_path, 0.0)
        except Exception as e: logger.error(f"Error calculating scores for {prioritization_strategy}: {e}", exc_info=True)
        return sorted(files_to_prioritize, key=lambda f_path: scores.get(f_path, 0.0), reverse=True)

    def get_most_central_files(self, n: int = 10, metric: str = 'pagerank') -> List[Tuple[str, float]]:
        self._ensure_networkx_graph()
        G = self.nx_graph
        if not G or not G.nodes(): return []
        scores = {}
        try:
            if metric == 'pagerank': scores = nx.pagerank(G)
            elif metric == 'in_degree': scores = {node: G.in_degree(node) for node in G.nodes()}
            elif metric == 'out_degree': scores = {node: G.out_degree(node) for node in G.nodes()}
            elif metric == 'betweenness':
                if len(G) < 1000: scores = nx.betweenness_centrality(G)
                else: logger.warning("Skipping betweenness for get_most_central_files on large graph."); scores = {node:0.0 for node in G.nodes()}
            else: logger.warning(f"Unknown centrality: {metric}. Defaulting to PageRank."); scores = nx.pagerank(G)
        except Exception as e: logger.error(f"Error calculating {metric} scores: {e}", exc_info=True); return []
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_impact_score(self, file_path: str, max_depth: Optional[int] = None) -> float:
        self._ensure_networkx_graph()
        G = self.nx_graph
        if file_path not in G: return 0.0
        dependents_on_file = set(nx.ancestors(G, file_path))
        num_dependents = len(dependents_on_file)
        try:
            pagerank_scores = nx.pagerank(G)
            pr_score = pagerank_scores.get(file_path, 0.0)
        except Exception as e: logger.warning(f"Could not calc PageRank for {file_path}: {e}. Using 0."); pr_score = 0.0
        total_nodes = len(G)
        normalized_dependents = num_dependents / max(total_nodes - 1, 1) if total_nodes > 1 else 0.0
        return (0.7 * normalized_dependents) + (0.3 * pr_score)

def analyze_dependencies(repo_path: str = ".", include_patterns: List[str] = None, exclude_patterns: Optional[List[str]] = None, cache_dir: Optional[str] = None, incremental: bool = True, max_workers: int = 4) -> DependencyAnalyzer:
    logger.info(f"Starting dependency analysis for repository: {repo_path}")
    builder = DependencyGraphBuilder(cache_dir=cache_dir, max_workers=max_workers)
    previous_graph_json_str = None
    if incremental and cache_dir:
        logger.info(f"Attempting to load cached graph data from: {cache_dir}")
        previous_graph_json_str = builder.load_cached_graph_json_str(repo_path)
        if previous_graph_json_str: logger.info("Successfully loaded cached graph data as JSON string.")
        else: logger.info("No valid cached graph data found or cache_dir not specified.")
    dependency_graph_model = builder.build_graph(root_dir=repo_path, include_patterns=include_patterns, exclude_patterns=exclude_patterns, incremental=incremental, previous_graph_json_str=previous_graph_json_str)
    logger.info(f"Dependency graph built. Nodes: {len(dependency_graph_model)}.")
    analyzer = DependencyAnalyzer(graph=dependency_graph_model)
    logger.info("DependencyAnalyzer initialized.")
    return analyzer

def get_repair_cascades(affected_files: List[str], repo_path: str = ".") -> List[Set[str]]:
    analyzer = analyze_dependencies(repo_path)
    return analyzer.get_repair_batches()
