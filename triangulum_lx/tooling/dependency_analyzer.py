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

# --- Stubs for graph_models ---
# These would ideally be imported from a graph_models.py, but are stubbed here for consolidation.
from enum import Enum
from dataclasses import dataclass, field
import time

class LanguageType(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    UNKNOWN = "unknown"

    @staticmethod
    def from_extension(ext: str) -> 'LanguageType':
        ext = ext.lower()
        if ext == ".py": return LanguageType.PYTHON
        if ext == ".js" or ext == ".jsx": return LanguageType.JAVASCRIPT
        if ext == ".ts" or ext == ".tsx": return LanguageType.TYPESCRIPT
        if ext == ".java": return LanguageType.JAVA
        if ext == ".go": return LanguageType.GO
        return LanguageType.UNKNOWN

@dataclass
class FileNode:
    path: str # Relative path from repo root
    language: LanguageType = LanguageType.UNKNOWN
    last_modified: float = field(default_factory=time.time)
    # Other attributes like hash, size could be added

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        if isinstance(other, FileNode):
            return self.path == other.path
        return False
    
    def to_dict(self):
        return {"path": self.path, "language": self.language.value, "last_modified": self.last_modified}

    def has_changed(self, root_dir: str) -> bool:
        full_path = os.path.join(root_dir, self.path)
        if not os.path.exists(full_path):
            return True # File deleted
        return os.path.getmtime(full_path) > self.last_modified


class DependencyType(Enum):
    IMPORT = "import"
    FUNCTION_CALL = "function_call"
    CLASS_INHERITANCE = "class_inheritance"
    UNKNOWN = "unknown"

@dataclass
class DependencyMetadata:
    dependency_type: DependencyType = DependencyType.UNKNOWN
    source_lines: List[int] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list) # e.g., imported functions/classes
    verified: bool = False
    confidence: float = 0.0
    additional_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "dependency_type": self.dependency_type.value,
            "source_lines": self.source_lines,
            "symbols": self.symbols,
            "verified": self.verified,
            "confidence": self.confidence,
            "additional_info": self.additional_info,
        }

@dataclass
class DependencyEdge:
    source: str  # path of source FileNode
    target: str  # path of target FileNode
    metadata: DependencyMetadata = field(default_factory=DependencyMetadata)

class DependencyGraph: # Simplified stub, actual is more complex
    def __init__(self):
        self._graph = nx.DiGraph()
        self._nodes: Dict[str, FileNode] = {}

    def add_node(self, node: FileNode):
        if node.path not in self._nodes:
            self._nodes[node.path] = node
            self._graph.add_node(node.path, **node.to_dict())

    def get_node(self, path: str) -> Optional[FileNode]:
        return self._nodes.get(path)

    def add_edge(self, source_path: str, target_path: str, metadata: DependencyMetadata):
        if source_path in self._nodes and target_path in self._nodes:
            self._graph.add_edge(source_path, target_path, **metadata.to_dict())

    def __contains__(self, path: str) -> bool:
        return path in self._nodes

    def transitive_dependents(self, path: str) -> Set[str]:
        if path not in self._graph:
            return set()
        return set(nx.ancestors(self._graph, path))

    def find_cycles(self) -> List[List[str]]:
        return list(nx.simple_cycles(self._graph))
    
    def to_json(self, indent=None): # Simplified
        return json.dumps({
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [(u,v,data) for u,v,data in self._graph.edges(data=True)]
        }, indent=indent)

    @staticmethod
    def from_json(json_str): # Simplified
        # Actual implementation would reconstruct nodes and graph
        logger.warning("DependencyGraph.from_json is a simplified stub and does not fully reconstruct.")
        return DependencyGraph()

# --- End Stubs for graph_models ---

# --- Copied from dependency_graph.py ---
import ast # Added for PythonDependencyParser
from concurrent.futures import ThreadPoolExecutor, as_completed # Added for DependencyGraphBuilder
from collections import defaultdict, deque # Potentially used by graph algorithms if not already imported

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
        Parse a Python file and extract its dependencies (imports) and definitions (functions, classes).
        
        Args:
            file_path: Path to the file to parse (relative to root_dir)
            root_dir: The root directory of the project for resolving imports

        Returns:
            List of (target_path, metadata) tuples representing import dependencies.
            Function and class definitions are logged for now.
        """
        dependencies = []
        defined_functions = []
        defined_classes = []
        # TODO: Store function_calls if needed for deeper analysis later
        # function_calls_info = []


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

                    # Determine the full module name for relative imports
                    if level > 0: # Relative import
                        # current_file_path is relative to root_dir
                        base_path_parts = list(Path(file_path).parent.parts)
                        if level > len(base_path_parts) and base_path_parts != ['.']: # e.g. from ....foo import bar
                             logger.warning(f"Relative import level {level} too deep for path {file_path} in {module_name}")
                             continue

                        # Adjust base_path_parts based on level
                        # For 'from . import foo', level=1, base_path_parts is unchanged
                        # For 'from .. import foo', level=2, base_path_parts loses one element
                        eff_base_parts = base_path_parts[:len(base_path_parts) - (level -1)]

                        # Construct the module path from parts
                        if not module_name: # e.g. from . import foo
                            imported_module_path_parts = eff_base_parts
                        else: # e.g. from .bar import foo
                            imported_module_path_parts = eff_base_parts + module_name.split('.')

                        # Filter out empty strings that might result from splitting an empty module_name
                        imported_module_path_parts = [part for part in imported_module_path_parts if part]

                        full_module_name = ".".join(imported_module_path_parts)

                    else: # Absolute import
                        full_module_name = module_name

                    for name_obj in node.names: # Changed from 'name' to 'name_obj' to avoid conflict
                        symbol = name_obj.name
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

                elif isinstance(node, ast.FunctionDef):
                    # Record defined function
                    # For methods, node.name is the method name. Class name is from parent ClassDef.
                    qualname = node.name
                    current_node = node
                    # Walk up to find class context for methods
                    # This is a simplified way to get a "qualified" name for methods.
                    # A full type analyzer would do this more robustly.
                    # For now, just storing the name.
                    # Path(file_path).name could be added to qualname for more uniqueness if needed.
                    defined_functions.append(qualname)

                elif isinstance(node, ast.ClassDef):
                    # Record defined class
                    defined_classes.append(node.name)
            
            if defined_functions:
                logger.debug(f"File {file_path} defines functions: {', '.join(defined_functions)}")
            if defined_classes:
                logger.debug(f"File {file_path} defines classes: {', '.join(defined_classes)}")

            # TODO: The FileNode associated with file_path should be updated with this info.
            # This requires DependencyGraphBuilder to pass this info to graph.add_node or a new method.
            # For now, this info is logged.
        
        except Exception as e:
            logger.warning(f"Error parsing Python file {file_path}: {str(e)}")

        return [dep for dep in dependencies if dep is not None]

    def _process_import(
        self,
        module_name: str,
        line_no: int,
        current_file_path: str, # relative to root_dir
        root_dir: str,
        is_from: bool = False,
        symbol: Optional[str] = None
    ) -> Optional[Tuple[str, DependencyMetadata]]:
        # Skip standard library and common external libraries for internal dependency graph
        # This check might need to be more sophisticated or configurable
        if self._is_standard_lib(module_name) or self._is_external_lib(module_name):
            return None

        # Resolve module name to a file path (relative to root_dir)
        resolved_target_path = self._module_to_path(module_name, root_dir, Path(current_file_path).parent.as_posix())
        if not resolved_target_path:
            # logger.debug(f"Could not resolve module '{module_name}' imported in '{current_file_path}' to a file.")
            return None

        symbols = [symbol] if symbol else []

        metadata = DependencyMetadata(
            dependency_type=DependencyType.IMPORT,
            source_lines=[line_no],
            symbols=symbols,
            verified=False, # Verification would require deeper analysis or type checking
            confidence=0.8, # Confidence might vary based on resolution success
            additional_info={"is_from_import": is_from, "original_import_name": module_name}
        )

        return resolved_target_path, metadata

    def _is_standard_lib(self, module_name: str) -> bool:
        # Simplified check, a more comprehensive list or method (like stdlib_list package) would be better
        std_libs_prefixes = {
            "os", "sys", "time", "datetime", "math", "random", "re", "json",
            "collections", "itertools", "functools", "logging", "io", "pathlib",
            "threading", "multiprocessing", "concurrent", "subprocess", "tempfile",
            "shutil", "pickle", "csv", "hashlib", "uuid", "argparse", "enum", "ast",
            "unittest", "doctest", "zipfile", "tarfile", "gzip", "bz2", "lzma",
            "socket", "ssl", "http", "urllib", "xml", "ctypes", "struct", "select",
            "asyncio"
        }
        return module_name.split('.')[0] in std_libs_prefixes

    def _is_external_lib(self, module_name: str) -> bool:
        # This is highly project-specific and would ideally come from requirements.txt or similar
        # For now, a small, common list.
        external_libs_prefixes = {
            "numpy", "pandas", "matplotlib", "scipy", "sklearn", "tensorflow",
            "torch", "django", "flask", "requests", "bs4", "sqlalchemy", "pytest",
            "networkx", "openai", "werkzeug" # networkx was added
        }
        return module_name.split('.')[0] in external_libs_prefixes

    def _module_to_path(self, module_name: str, root_dir: str, current_file_dir_rel: str) -> Optional[str]:
        """
        Resolves a module name to its corresponding file path, relative to root_dir.
        Handles both absolute and relative-style module paths post-processing by ImportFrom.
        """
        if not module_name: # Should not happen if called correctly
            return None

        parts = module_name.split('.')

        # Try as absolute path from root_dir
        # e.g. 'project.utils.helpers' -> project/utils/helpers.py or project/utils/helpers/__init__.py
        potential_path_from_root_parts = parts

        # Path for .py file
        path_py = Path(root_dir, *potential_path_from_root_parts).with_suffix(".py")
        if path_py.exists():
            return path_py.relative_to(root_dir).as_posix()
        
        # Path for __init__.py in a directory
        path_init = Path(root_dir, *potential_path_from_root_parts, "__init__.py")
        if path_init.exists():
            return path_init.relative_to(root_dir).as_posix()

        # Python's import resolution can be complex, especially with sys.path modifications,
        # .pth files, and editable installs. This is a simplified resolver.
        # For truly robust resolution, one might need to simulate Python's import machinery
        # or use tools like `importlib.util.find_spec`, but that requires more context.

        # logger.debug(f"Failed to resolve module '{module_name}' (current_file_dir_rel: {current_file_dir_rel})")
        return None


class JavaScriptDependencyParser(BaseDependencyParser):
    """Parser for extracting dependencies from JavaScript/TypeScript files."""

    def __init__(self, lang_type=LanguageType.JAVASCRIPT): # Allow TypeScript to reuse
        """Initialize the parser."""
        super().__init__()
        self.language = lang_type
        
        # Regex for various import/require forms
        # Catches:
        # import ... from 'module_path';
        # import 'module_path';
        # const ... = require('module_path');
        # export ... from 'module_path'; (handled by specific export regex)
        self.import_regex = re.compile(
            r'(?:import\s+(?:[^;]*\s+from\s+)?[\'"]([^\'"\n]+)[\'"])|'  # import ... from 'path', import 'path'
            r'(?:require\s*\(\s*[\'"]([^\'"\n]+)[\'"]\s*\))'              # require('path')
        )
        self.export_from_regex = re.compile(
            r'export\s+(?:[^;]*\s+from\s+)?[\'"]([^\'"\n]+)[\'"]' # export ... from 'path'
        )

    def parse_file(self, file_path: str, root_dir: str) -> List[Tuple[str, DependencyMetadata]]:
        dependencies = []
        full_path = os.path.join(root_dir, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Iterate over lines to get line numbers, though regex works on full content
            lines = content.splitlines()
            current_offset = 0

            for line_no_idx, line_content in enumerate(lines):
                line_no = line_no_idx + 1 # 1-based line number

                # Process imports
                for match in self.import_regex.finditer(line_content):
                    # Group 1 is for import from 'path' or import 'path', group 2 for require('path')
                    module_specifier = match.group(1) or match.group(2)
                    if module_specifier:
                        dep = self._process_import(module_specifier, line_no, file_path, root_dir, is_export=False)
                        if dep:
                            dependencies.append(dep)
                
                # Process exports from
                for match in self.export_from_regex.finditer(line_content):
                    module_specifier = match.group(1)
                    if module_specifier:
                        dep = self._process_import(module_specifier, line_no, file_path, root_dir, is_export=True)
                        if dep:
                            dependencies.append(dep)
                current_offset += len(line_content) + 1

        except Exception as e:
            logger.warning(f"Error parsing JS/TS file {file_path}: {str(e)}")
        
        return dependencies
    
    def _process_import(
        self,
        module_specifier: str,
        line_no: int,
        current_file_path: str, # relative to root_dir
        root_dir: str,
        is_export: bool = False
    ) -> Optional[Tuple[str, DependencyMetadata]]:
        # Skip absolute paths, URLs, or Node built-in modules (basic check)
        if not module_specifier.startswith('.') or ':' in module_specifier:
            return None # Not a relative file path we can resolve easily
        
        # Resolve module_specifier to a file path (relative to root_dir)
        resolved_target_path = self._resolve_import_path(module_specifier, Path(current_file_path).parent.as_posix(), root_dir)
        if not resolved_target_path:
            # logger.debug(f"Could not resolve module '{module_specifier}' imported in '{current_file_path}' to a file.")
            return None
        
        metadata = DependencyMetadata(
            dependency_type=DependencyType.IMPORT,
            source_lines=[line_no],
            symbols=[], # JS/TS parsing for specific symbols is more complex
            verified=False,
            confidence=0.7, # Confidence lower due to complex JS/TS resolution
            additional_info={"is_export_from": is_export, "original_import_specifier": module_specifier}
        )

        return resolved_target_path, metadata
    
    def _resolve_import_path(self, module_specifier: str, current_file_dir_rel: str, root_dir: str) -> Optional[str]:
        """
        Resolves a JS/TS module specifier to its corresponding file path, relative to root_dir.
        """
        # Normalize: current_file_dir_rel is dir of current file, module_specifier is like './foo' or '../bar/baz'
        # Path(root_dir, current_file_dir_rel, module_specifier) gives absolute path to target module (without extension)
        base_target_path = Path(root_dir, current_file_dir_rel, module_specifier).resolve()

        # Extensions to try, in order of preference for this parser
        if self.language == LanguageType.TYPESCRIPT:
            extensions_to_try = [".ts", ".tsx", ".js", ".jsx", ".json"]
        else: # JavaScript
            extensions_to_try = [".js", ".jsx", ".json"]

        # Check path as a file with extensions
        for ext in extensions_to_try:
            potential_file_path = base_target_path.with_suffix(ext)
            if potential_file_path.is_file() and potential_file_path.is_relative_to(root_dir):
                return potential_file_path.relative_to(root_dir).as_posix()

        # Check path as a directory (look for index file)
        if base_target_path.is_dir():
            for ext in extensions_to_try:
                potential_index_path = base_target_path / f"index{ext}"
                if potential_index_path.is_file() and potential_index_path.is_relative_to(root_dir):
                    return potential_index_path.relative_to(root_dir).as_posix()
        
        # logger.debug(f"Failed to resolve JS/TS module '{module_specifier}' from '{current_file_dir_rel}'")
        return None

class TypeScriptDependencyParser(JavaScriptDependencyParser):
    """Parser for extracting dependencies from TypeScript files. Inherits JS logic."""
    def __init__(self):
        super().__init__(lang_type=LanguageType.TYPESCRIPT)


class ParserRegistry:
    """Registry of available dependency parsers."""

    def __init__(self):
        """Initialize the registry with default parsers."""
        self.parsers: List[BaseDependencyParser] = [
            PythonDependencyParser(),
            JavaScriptDependencyParser(), # Will handle .js, .jsx
            TypeScriptDependencyParser(), # Will handle .ts, .tsx
        ]

    def get_parser_for_file(self, file_path: str) -> Optional[BaseDependencyParser]:
        # Determine language from extension to select parser more directly
        lang_type = LanguageType.from_extension(os.path.splitext(file_path)[1])
        for parser in self.parsers:
            if parser.language == lang_type:
                if parser.can_parse(file_path): # Double check, though language match should be enough
                    return parser
        # Fallback if direct language match fails or for .jsx/.tsx if not explicitly handled by language match
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        logger.debug(f"No parser found for file: {file_path} (lang_type: {lang_type})")
        return None

    def register_parser(self, parser: BaseDependencyParser) -> None:
        # Could add logic to avoid duplicate language parsers or prioritize
        self.parsers.append(parser)


class DependencyGraphBuilder:
    """
    Builder for constructing dependency graphs from codebases.
    Uses the stubbed DependencyGraph and FileNode models.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_workers: int = 4, # os.cpu_count() or similar might be better
        parser_registry: Optional[ParserRegistry] = None
    ):
        self.cache_dir = cache_dir
        if cache_dir:
            Path(cache_dir).mkdir(parents=True, exist_ok=True) # Use Pathlib
        
        self.max_workers = max_workers
        self.parser_registry = parser_registry or ParserRegistry()

    def build_graph(
        self,
        root_dir: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        incremental: bool = True, # Default to True for efficiency
        previous_graph_data: Optional[Dict[str, Any]] = None, # For loading cached/previous graph
    ) -> DependencyGraph: # Returns our stubbed DependencyGraph
        start_time = time.time()

        # Initialize graph: from previous data or new
        graph = DependencyGraph() # Using our stubbed graph
        if incremental and previous_graph_data:
            # Simplified: real version would reconstruct graph from previous_graph_data
            # For this merge, we'll assume previous_graph_data helps identify changed files only
            logger.info("Incremental build with previous graph data (simplified).")
            # In a full impl, you'd use DependencyGraph.from_json(previous_graph_data) or similar

        # Find all relevant files
        all_repo_files = self._find_files(root_dir, include_patterns, exclude_patterns)
        logger.info(f"Found {len(all_repo_files)} files to potentially analyze in {root_dir}")

        files_to_process_paths = set(all_repo_files)
        if incremental and previous_graph_data: # And previous_graph is properly loaded
            # This part needs the actual previous_graph object to compare FileNodes
            # For now, if incremental, we'll just process all found files if no proper previous_graph
            # A proper incremental check:
            # current_file_nodes = {fp: FileNode(path=fp, language=LanguageType.from_extension(fp), last_modified=os.path.getmtime(Path(root_dir, fp))) for fp in all_repo_files}
            # changed_files_paths = self._identify_changed_files_from_data(current_file_nodes, previous_graph_data, root_dir)
            # files_to_process_paths = changed_files_paths
            # logger.info(f"Incremental analysis: {len(files_to_process_paths)} files to re-process.")
            pass # Simplified incremental logic for now

        # Add all file nodes to the graph first (ensures all potential targets exist)
        for file_path_rel in all_repo_files:
            lang = LanguageType.from_extension(os.path.splitext(file_path_rel)[1])
            # Use Path for robust joining and mtime fetching
            abs_file_path = Path(root_dir, file_path_rel)
            node = FileNode(path=file_path_rel, language=lang, last_modified=abs_file_path.stat().st_mtime if abs_file_path.exists() else time.time())
            graph.add_node(node) # Uses our stubbed graph's add_node
            
        # Process files for dependencies
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_file_for_builder, file_path_rel, graph, root_dir): file_path_rel
                for file_path_rel in files_to_process_paths
            }
            
            for future in as_completed(future_to_file):
                file_path_task = future_to_file[future]
                try:
                    future.result() # result is None, dependencies are added to graph directly
                except Exception as e:
                    logger.error(f"Error processing file {file_path_task} in executor: {str(e)}", exc_info=True)

        end_time = time.time()
        logger.info(f"Graph construction completed in {end_time - start_time:.2f} seconds. Graph has {len(graph._nodes)} nodes and {len(graph._graph.edges)} edges.")

        if self.cache_dir:
            self._cache_graph_data(graph, root_dir) # Saves data from our stubbed graph

        return graph # Return our stubbed DependencyGraph instance
    
    def _find_files(
        self,
        root_dir: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[str]: # Returns list of relative paths
        import fnmatch # Ensure fnmatch is available
        
        # More common defaults, especially for source code
        include_patterns = include_patterns or ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx', '*.java', '*.go', '*.html', '*.css']
        exclude_patterns = exclude_patterns or ['**/node_modules/**', '**/__pycache__/**', '**/.git/**', '**/dist/**', '**/build/**']
        
        found_files_rel_paths = []

        for dirpath_str, _, filenames in os.walk(root_dir):
            dirpath = Path(dirpath_str)
            # Check if current directory path itself matches any exclude pattern
            if any(fnmatch.fnmatch(dirpath.as_posix(), pattern.replace('**/', '')) for pattern in exclude_patterns if pattern.endswith('/**')): # Simplified check for dir exclusion
                 continue

            for filename in filenames:
                file_path_abs = dirpath / filename
                file_path_rel = file_path_abs.relative_to(root_dir).as_posix() # Use POSIX style for consistency

                is_excluded = any(fnmatch.fnmatch(file_path_rel, pattern) or fnmatch.fnmatch(filename, pattern) for pattern in exclude_patterns)
                if is_excluded:
                    continue
                
                is_included = any(fnmatch.fnmatch(file_path_rel, pattern) or fnmatch.fnmatch(filename, pattern) for pattern in include_patterns)
                if is_included:
                    found_files_rel_paths.append(file_path_rel)

        return found_files_rel_paths

    def _identify_changed_files_from_data(
        self,
        current_file_nodes: Dict[str, FileNode], # path -> FileNode
        previous_graph_nodes_data: List[Dict[str, Any]], # List of node dicts from cached graph
        root_dir: str # Not strictly needed if FileNode.has_changed is not used
    ) -> Set[str]: # Returns set of relative paths
        changed_files_paths = set()
        previous_nodes_map = {node_data['path']: node_data for node_data in previous_graph_nodes_data}

        for rel_path, current_node in current_file_nodes.items():
            prev_node_data = previous_nodes_map.get(rel_path)
            if not prev_node_data:
                changed_files_paths.add(rel_path) # New file
                continue

            # Compare modification times or hashes (last_modified is used here)
            if current_node.last_modified > prev_node_data.get('last_modified', 0):
                changed_files_paths.add(rel_path)

        # Add deleted files (present in previous_graph_nodes_data but not in current_file_nodes)
        for rel_path in previous_nodes_map.keys():
            if rel_path not in current_file_nodes:
                changed_files_paths.add(rel_path) # Deleted file (though processing it might mean removing from graph)

        return changed_files_paths

    def _process_file_for_builder(self, file_path_rel: str, graph: DependencyGraph, root_dir: str) -> None:
        """ Helper to be called by the executor, adds dependencies to the shared graph. """
        parser = self.parser_registry.get_parser_for_file(file_path_rel)
        if not parser:
            # logger.debug(f"No parser found for {file_path_rel}, skipping dependency extraction.")
            return

        try:
            # Ensure root_dir is absolute for robust path operations inside parsers
            abs_root_dir = Path(root_dir).resolve().as_posix()
            dependencies = parser.parse_file(file_path_rel, abs_root_dir) # parser expects root_dir for its own resolutions

            for target_path_rel, metadata in dependencies:
                # Ensure target_path_rel is in the graph (should have been added in the first loop of build_graph)
                if target_path_rel in graph: # Check against stubbed graph's __contains__
                    graph.add_edge(file_path_rel, target_path_rel, metadata) # Uses stubbed graph's add_edge
                else:
                    logger.warning(f"Target dependency '{target_path_rel}' for '{file_path_rel}' not found in graph nodes. Skipping edge.")
        except Exception as e:
            logger.error(f"Error parsing dependencies for file {file_path_rel}: {str(e)}", exc_info=True)

    def _cache_graph_data(self, graph: DependencyGraph, root_dir: str) -> None: # Operates on stubbed graph
        if not self.cache_dir:
            return

        # Create a more descriptive cache name, perhaps incorporating root_dir's basename
        # Hashing the full root_dir path can lead to very long filenames if it's deep
        root_dir_hash_part = str(hash(Path(root_dir).resolve().as_posix()))[-8:] # Use last 8 chars of hash
        cache_name = f"dep_graph_cache_{Path(root_dir).name}_{root_dir_hash_part}.json"
        cache_path = Path(self.cache_dir, cache_name)

        try:
            # graph.to_json() is from our stubbed DependencyGraph
            with open(cache_path, 'w', encoding='utf-8') as f: # Ensure utf-8
                f.write(graph.to_json(indent=2))
            logger.info(f"Cached dependency graph data to {cache_path}")
        except Exception as e:
            logger.error(f"Error caching graph data: {str(e)}", exc_info=True)

    def load_cached_graph_data(self, root_dir: str) -> Optional[Dict[str, Any]]: # Returns dict for simplified incremental
        if not self.cache_dir:
            return None

        root_dir_hash_part = str(hash(Path(root_dir).resolve().as_posix()))[-8:]
        cache_name = f"dep_graph_cache_{Path(root_dir).name}_{root_dir_hash_part}.json"
        cache_path = Path(self.cache_dir, cache_name)

        if not cache_path.exists():
            logger.info(f"No cache file found at {cache_path}")
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f: # Ensure utf-8
                data = json.load(f) # Returns a dictionary
            logger.info(f"Loaded cached dependency graph data from {cache_path}")
            return data
        except Exception as e:
            logger.error(f"Error loading cached graph data from {cache_path}: {str(e)}", exc_info=True)
            return None

# --- End Copied from dependency_graph.py ---


class DependencyAnalyzer: # This class will now use the DependencyGraph produced by DependencyGraphBuilder
    """
    Analyzes a pre-built dependency graph to provide insights.
    """
    
    def __init__(self, graph: DependencyGraph): # Takes our stubbed DependencyGraph
        """
        Initialize the dependency analyzer with a pre-built graph.

        Args:
            graph: A DependencyGraph instance built by DependencyGraphBuilder.
        """
        self.graph_model = graph # Store the custom DependencyGraph model
        self._networkx_graph = None # Lazy loaded networkx representation for analysis

        # Initialize the networkx graph representation immediately for simplicity here,
        # or make it a property that converts on first access.
        self._build_networkx_representation()

    def _build_networkx_representation(self):
        """Converts the internal DependencyGraph model to a NetworkX DiGraph."""
        self._networkx_graph = nx.DiGraph()
        if self.graph_model and hasattr(self.graph_model, '_nodes') and hasattr(self.graph_model, '_graph'):
            for node_path, f_node_obj in self.graph_model._nodes.items():
                self._networkx_graph.add_node(node_path, **f_node_obj.to_dict())

            # Assuming self.graph_model._graph is already a networkx graph with edge data
            # If DependencyGraph stores edges differently, this needs adjustment.
            # The stubbed DependencyGraph._graph IS a networkx graph.
            for u, v, data in self.graph_model._graph.edges(data=True):
                 self._networkx_graph.add_edge(u, v, **data)
        else:
            logger.warning("DependencyGraph model is not as expected for NetworkX conversion.")


    @property
    def nx_graph(self) -> nx.DiGraph:
        """Provides access to the NetworkX graph representation."""
        if self._networkx_graph is None:
            self._build_networkx_representation()
        if self._networkx_graph is None: # If still None after build attempt
            logger.error("Failed to build NetworkX representation. Returning empty graph.")
            return nx.DiGraph() # Return empty graph to avoid None errors
        return self._networkx_graph

    # Methods to be kept/adapted:
    # get_dependent_files, get_dependencies, get_strongly_connected_components, get_repair_batches
    # save_graph, load_graph (will be removed as builder handles caching)

    # Methods to be merged from original dependency_graph.py's DependencyAnalyzer:
    # visualize_graph, calculate_centrality, find_cycles (already covered by SCC),
    # prioritize_files, get_most_central_files, get_impact_score

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
        if file_path not in self.nx_graph:
            logger.warning(f"File '{file_path}' not found in the NetworkX graph for get_dependent_files.")
            return set()
        return set(self.nx_graph.predecessors(file_path))
    
    def get_dependencies(self, file_path: str) -> Set[str]:
        """
        Get all files that the given file depends on.
        
        Args:
            file_path: File to find dependencies for
            
        Returns:
            Set of file paths that the given file depends on
        """
        if file_path not in self.nx_graph:
            logger.warning(f"File '{file_path}' not found in the NetworkX graph for get_dependencies.")
            return set()
            
        # Files imported by the target file (outgoing edges)
        return set(self.nx_graph.successors(file_path))
    
    def get_strongly_connected_components(self) -> List[Set[str]]:
        """
        Get strongly connected components in the dependency graph.
        
        Returns:
            List of sets containing nodes in each SCC
        """
        return list(nx.strongly_connected_components(self.nx_graph))
    
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
        sccs = self.get_strongly_connected_components() # Uses the adapted method

        # Create a condensation graph (each SCC becomes a node)
        # The condensation graph maps nodes to an integer ID representing their SCC
        condensation_graph_nx = nx.condensation(self.nx_graph, sccs=sccs)

        try:
            # The nodes in condensation_graph_nx are integers (SCC IDs).
            # We need to map these back to the actual sets of files.
            topo_order_scc_ids = list(nx.topological_sort(condensation_graph_nx))

            # scc_map maps the integer ID from condensation_graph_nx to the actual SCC (set of file paths)
            # This relies on the order of SCCs returned by nx.strongly_connected_components
            # and how nx.condensation labels its nodes.
            # A more robust way: nx.condensation returns a mapping as its second value if sccmap=True
            # However, the default behavior with precomputed sccs should align.
            # Let's assume sccs are indexed 0 to N-1 corresponding to condensation graph nodes.

            scc_id_to_files_map = {i: scc_set for i, scc_set in enumerate(sccs)}

            ordered_batches = [scc_id_to_files_map[scc_id] for scc_id in topo_order_scc_ids if scc_id in scc_id_to_files_map]
            return ordered_batches

        except nx.NetworkXUnfeasible:
            logger.warning("Cycles detected in condensation graph (should not happen if SCCs are correct); returning SCCs as batches without strict topological order.")
            return sccs # Fallback: return SCCs as batches, order might not be optimal
    
    # save_graph and load_graph are removed as caching is handled by DependencyGraphBuilder.
    # The analyzer now operates on an in-memory graph passed to it.

    # --- Methods to merge from original dependency_graph.py's DependencyAnalyzer ---
    def visualize_graph(self, output_path: str, layout: str = 'spring') -> None:
        """Visualizes the NetworkX graph using matplotlib."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.error("Matplotlib not installed. Cannot visualize graph. Please install matplotlib.")
            return

        G = self.nx_graph # Use the property
        
        if not G.nodes():
            logger.warning("Graph is empty. Nothing to visualize.")
            return

        plt.figure(figsize=(20, 20))
        
        try:
            if layout == 'spring':
                pos = nx.spring_layout(G, k=0.15, iterations=20)
            elif layout == 'circular':
                pos = nx.circular_layout(G)
            elif layout == 'kamada_kawai':
                # Kamada-Kawai can be slow on very large graphs
                if len(G) > 500:
                    logger.warning("Kamada-Kawai layout might be slow for large graphs. Consider 'spring'.")
                pos = nx.kamada_kawai_layout(G)
            else: # Default to spring
                pos = nx.spring_layout(G)
        except Exception as e:
            logger.error(f"Error computing layout '{layout}': {e}. Defaulting to spring layout.")
            pos = nx.spring_layout(G) # Fallback
            
        nx.draw(G, pos, with_labels=True, node_size=max(50, 2000/len(G) if len(G)>0 else 50),
                font_size=max(6, 100/len(G) if len(G)>0 else 8), arrows=True, alpha=0.8, width=0.5)
        plt.savefig(output_path)
        plt.close()
        logger.info(f"Graph visualization saved to {output_path}")

    def calculate_centrality(self) -> Dict[str, Dict[str, float]]:
        """Calculates various centrality measures for nodes in the graph."""
        G = self.nx_graph
        if not G.nodes(): return {}

        centrality = {}
        try:
            in_degree = nx.in_degree_centrality(G)
            out_degree = nx.out_degree_centrality(G)
            betweenness = nx.betweenness_centrality(G) # Can be slow
            pagerank = nx.pagerank(G) # Can be slow
        except Exception as e:
            logger.error(f"Error calculating one or more centrality measures: {e}. Results may be incomplete.")
            # Initialize with defaults to avoid crashing later parts
            in_degree = {n: 0.0 for n in G.nodes()}
            out_degree = {n: 0.0 for n in G.nodes()}
            betweenness = {n: 0.0 for n in G.nodes()}
            pagerank = {n: 0.0 for n in G.nodes()}

        for node in G.nodes():
            centrality[node] = {
                'in_degree': in_degree.get(node, 0.0),
                'out_degree': out_degree.get(node, 0.0),
                'betweenness': betweenness.get(node, 0.0),
                'pagerank': pagerank.get(node, 0.0),
            }
        return centrality
    
    def prioritize_files(
        self,
        files_to_prioritize: List[str], # Changed name for clarity
        prioritization_strategy: str = 'pagerank',
        additional_weights: Optional[Dict[str, float]] = None
    ) -> List[str]:
        """Prioritizes a list of files based on a given strategy and the graph structure."""
        G = self.nx_graph
        if not G.nodes() or not files_to_prioritize:
            return files_to_prioritize # Return original if no graph or no files

        additional_weights = additional_weights or {}
        scores = {f: 0.0 for f in files_to_prioritize} # Initialize scores for all relevant files

        try:
            if prioritization_strategy == 'pagerank':
                computed_scores = nx.pagerank(G)
            elif prioritization_strategy == 'in_degree':
                computed_scores = {n: d for n, d in G.in_degree()} # Use raw degree, not centrality for direct count
            elif prioritization_strategy == 'out_degree':
                computed_scores = {n: d for n, d in G.out_degree()}
            elif prioritization_strategy == 'betweenness':
                computed_scores = nx.betweenness_centrality(G)
            else: # Default to no graph-based scoring, only additional_weights
                computed_scores = {n: 0.0 for n in G.nodes()}
        except Exception as e:
            logger.error(f"Error calculating scores for '{prioritization_strategy}': {e}. Using zero scores.")
            computed_scores = {n: 0.0 for n in G.nodes()}

        for f in files_to_prioritize:
            if f in G: # Only consider files present in the graph for graph-based scores
                scores[f] = computed_scores.get(f, 0.0) + additional_weights.get(f, 0.0)
            else:
                scores[f] = additional_weights.get(f, 0.0) # Use only additional weight if not in graph
        
        return sorted(files_to_prioritize, key=lambda f: scores.get(f, 0.0), reverse=True)

    def get_most_central_files(self, n: int = 10, metric: str = 'pagerank') -> List[Tuple[str, float]]:
        """Gets the top N most central files based on a specified metric."""
        G = self.nx_graph
        if not G.nodes(): return []

        scores = {}
        try:
            if metric == 'pagerank':
                scores = nx.pagerank(G)
            elif metric == 'in_degree': # Using raw degree as it's often more intuitive for "central"
                scores = {node: G.in_degree(node) for node in G.nodes()}
            elif metric == 'out_degree':
                scores = {node: G.out_degree(node) for node in G.nodes()}
            elif metric == 'betweenness':
                scores = nx.betweenness_centrality(G)
            else:
                logger.warning(f"Unknown centrality metric: {metric}. Defaulting to PageRank.")
                scores = nx.pagerank(G) # Fallback
        except Exception as e:
            logger.error(f"Error calculating '{metric}' scores: {e}. Returning empty list.")
            return []
            
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_impact_score(self, file_path: str, max_depth: Optional[int] = None) -> float:
        """
        Calculates an impact score for a file, considering both its centrality (PageRank)
        and the number of files that depend on it (descendants/successors in dependency graph).
        """
        G = self.nx_graph
        if file_path not in G:
            return 0.0

        # Number of files that this file directly or indirectly depends on (its dependencies)
        # This is nx.descendants in a typical import graph (A imports B => A -> B, B is descendant of A by this def)
        # However, for "impact", we want files that depend on `file_path`. These are ANCESTORS if edges are A -> B (A imports B).
        # If edges are B <- A (B is imported by A), then they are DESCENDANTS.
        # Our graph is file_path -> imported_file. So, files depending on file_path are its PREDECESSORS (ancestors).

        dependents_on_file = set(nx.ancestors(G, file_path)) # Files that depend on file_path
        num_dependents = len(dependents_on_file)

        try:
            pagerank_scores = nx.pagerank(G)
            pr_score = pagerank_scores.get(file_path, 0.0)
        except Exception as e:
            logger.warning(f"Could not calculate PageRank for impact score of {file_path}: {e}. Using 0 for PR component.")
            pr_score = 0.0

        # Normalize num_dependents: (0.0 to 1.0 range)
        # Max dependents could be total nodes - 1.
        total_nodes = len(G)
        normalized_dependents = num_dependents / max(total_nodes - 1, 1) if total_nodes > 1 else 0.0

        # Weighted score: 70% dependents, 30% pagerank
        # Pagerank is already normalized (sums to 1 over all nodes, or roughly 1/N on average for each node)
        # To make pr_score more comparable for weighting, we can scale it.
        # A simple approach: if average PR is 1/N, multiply by N to get "average" node to 1.
        # This can be too volatile if N is small or PR distribution is very skewed.
        # Let's keep PR as is, its relative value is what matters.

        impact_score = (0.7 * normalized_dependents) + (0.3 * pr_score * total_nodes if total_nodes > 0 else 0.3 * pr_score)
        # Multiplying pr_score by total_nodes attempts to scale it roughly to the order of 1 for an "average" node.
        return impact_score


def analyze_dependencies(repo_path: str = ".", # Kept for backward compatibility or high-level API
                        include_patterns: List[str] = None,
                        exclude_patterns: List[str] = None,
                        cache_dir: Optional[str] = None, # Allow specifying cache dir
                        incremental: bool = True,
                        max_workers: int = 4
                        ) -> DependencyAnalyzer: # Returns the refactored DependencyAnalyzer
    """
    High-level function to build a dependency graph and return an analyzer for it.
    
    Args:
        repo_path: Path to the repository.
        include_patterns: List of file patterns to include.
        exclude_patterns: List of file patterns to exclude.
        cache_dir: Directory for caching the graph. Defaults to None (no cache).
        incremental: Whether to perform an incremental build if cached data is available.
        max_workers: Number of worker threads for parallel processing.
        
    Returns:
        DependencyAnalyzer instance initialized with the built graph.
    """
    logger.info(f"Starting dependency analysis for repository: {repo_path}")

    # Initialize the graph builder
    builder = DependencyGraphBuilder(
        cache_dir=cache_dir,
        max_workers=max_workers
        # ParserRegistry is default
    )

    # Try to load cached graph data for incremental builds
    previous_graph_data = None
    if incremental and cache_dir:
        logger.info(f"Attempting to load cached graph data from: {cache_dir}")
        previous_graph_data = builder.load_cached_graph_data(repo_path)
        if previous_graph_data:
            logger.info("Successfully loaded cached graph data.")
        else:
            logger.info("No valid cached graph data found or cache_dir not specified.")

    # Build the graph (DependencyGraph stub instance)
    # The builder's build_graph now returns our stubbed DependencyGraph
    dependency_graph_model = builder.build_graph(
        root_dir=repo_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        incremental=incremental, # Builder handles logic with previous_graph_data
        previous_graph_data=previous_graph_data
    )
    
    logger.info(f"Dependency graph built. Nodes: {len(dependency_graph_model._nodes)}, Edges: {len(dependency_graph_model._graph.edges)}.")

    # Initialize the analyzer with the built graph model
    analyzer = DependencyAnalyzer(graph=dependency_graph_model)

    logger.info("DependencyAnalyzer initialized.")
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
