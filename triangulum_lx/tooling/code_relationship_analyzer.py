"""
Code Relationship Analyzer - Analyzes relationships between code files.

This module analyzes Python files to determine import relationships, function
dependencies, and other code relationships to provide context for debugging
and self-healing.
"""

import os
import ast
import logging
import re
import json
from typing import Dict, List, Set, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class CodeRelationshipAnalyzer:
    """
    Analyzes code files to determine relationships between them, including imports,
    function calls, and other dependencies.
    """

    def __init__(self):
        """Initialize the CodeRelationshipAnalyzer."""
        self.relationships = {}
        self.import_map = {}  # Maps module names to file paths
        self.function_map = {}  # Maps function names to file paths

    def analyze_directory(self, directory: str) -> Dict[str, Any]:
        """
        Analyze all Python files in a directory to determine their relationships.

        Args:
            directory: Directory to analyze

        Returns:
            Dictionary mapping file paths to their relationships
        """
        logger.info(f"Analyzing directory: {directory}")
        self.relationships = {}
        self.import_map = {}
        self.function_map = {}

        # First pass: Collect all Python files and their module names
        all_files = self._collect_python_files(directory)
        self._build_module_map(all_files, directory)

        # Second pass: Analyze each file for imports and function definitions
        for file_path in all_files:
            self._analyze_file(file_path)

        # Third pass: Resolve function calls and build cross-references
        self._resolve_function_calls()

        logger.info(f"Analyzed {len(self.relationships)} files")
        return self.relationships

    def analyze_code_relationships(self, file_paths=None, base_dir: str = None, files=None, **kwargs) -> Dict[str, Any]:
        """
        Analyze relationships between given files.
        
        Args:
            file_paths: List of file paths to analyze (can also be passed as 'files')
            base_dir: Base directory for the files
            files: Alternative name for file_paths (for compatibility)
            **kwargs: Additional parameters (for future extension)
            
        Returns:
            Dictionary with relationship information
        """
        # Use files parameter if file_paths is not provided (for compatibility)
        if file_paths is None and files is not None:
            file_paths = files
        
        if not file_paths:
            logger.warning("No file paths provided for analysis")
            return {}
            
        logger.info(f"Analyzing code relationships for {len(file_paths)} files")
        self.relationships = {}
        self.import_map = {}
        self.function_map = {}
        
        # Ensure all paths are absolute
        absolute_paths = []
        for path in file_paths:
            if not os.path.isabs(path):
                if base_dir:
                    path = os.path.abspath(os.path.join(base_dir, path))
                else:
                    path = os.path.abspath(path)
            absolute_paths.append(path)
            
        # Build module map from the file paths
        self._build_module_map(absolute_paths, base_dir or os.getcwd())
        
        # Analyze each file
        for file_path in absolute_paths:
            if os.path.exists(file_path):
                self._analyze_file(file_path)
            else:
                logger.warning(f"File not found: {file_path}")
                
        # Resolve function calls
        self._resolve_function_calls()
        
        logger.info(f"Analyzed {len(self.relationships)} files for relationships")
        return self.relationships

    def _collect_python_files(self, directory: str) -> List[str]:
        """
        Collect all Python files in a directory.

        Args:
            directory: Directory to search

        Returns:
            List of Python file paths
        """
        python_files = []

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))

        return python_files

    def _build_module_map(self, files: List[str], base_dir: str) -> None:
        """
        Build a mapping from module names to file paths.

        Args:
            files: List of Python file paths
            base_dir: Base directory for the project
        """
        for file_path in files:
            rel_path = os.path.relpath(file_path, base_dir)
            # Convert path to module name (e.g., "foo/bar.py" -> "foo.bar")
            module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
            self.import_map[module_name] = file_path

            # Handle __init__.py files
            if os.path.basename(file_path) == '__init__.py':
                # Allow importing the directory itself
                dir_module = os.path.dirname(rel_path).replace(os.path.sep, '.')
                self.import_map[dir_module] = file_path

    def _analyze_file(self, file_path: str) -> None:
        """
        Analyze a Python file to determine its relationships.

        Args:
            file_path: Path to the Python file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Initialize relationships for this file
            self.relationships[file_path] = {
                'imports': [],
                'imported_by': [],
                'functions': [],
                'classes': [],
                'function_calls': {},
                'dependencies': []
            }

            # Parse the file
            tree = ast.parse(content, filename=file_path)

            # Analyze imports
            self._analyze_imports(file_path, tree)

            # Analyze function and class definitions
            self._analyze_definitions(file_path, tree)

            # Analyze function calls
            self._analyze_function_calls(file_path, tree)

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")

    def _analyze_imports(self, file_path: str, tree: ast.Module) -> None:
        """
        Analyze imports in a Python file.

        Args:
            file_path: Path to the Python file
            tree: AST of the Python file
        """
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imported_module = name.name
                    imports.append(imported_module)
                    if imported_module in self.import_map:
                        imported_file = self.import_map[imported_module]
                        if imported_file != file_path:  # Avoid self-imports
                            if imported_file not in self.relationships:
                                self.relationships[imported_file] = {
                                    'imports': [],
                                    'imported_by': [],
                                    'functions': [],
                                    'classes': [],
                                    'function_calls': {},
                                    'dependencies': []
                                }
                            if file_path not in self.relationships[imported_file]['imported_by']:
                                self.relationships[imported_file]['imported_by'].append(file_path)

                            if imported_file not in self.relationships[file_path]['imports']:
                                self.relationships[file_path]['imports'].append(imported_file)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_module = node.module
                    imports.append(imported_module)
                    if imported_module in self.import_map:
                        imported_file = self.import_map[imported_module]
                        if imported_file != file_path:  # Avoid self-imports
                            if imported_file not in self.relationships:
                                self.relationships[imported_file] = {
                                    'imports': [],
                                    'imported_by': [],
                                    'functions': [],
                                    'classes': [],
                                    'function_calls': {},
                                    'dependencies': []
                                }
                            if file_path not in self.relationships[imported_file]['imported_by']:
                                self.relationships[imported_file]['imported_by'].append(file_path)

                            if imported_file not in self.relationships[file_path]['imports']:
                                self.relationships[file_path]['imports'].append(imported_file)

    def _analyze_definitions(self, file_path: str, tree: ast.Module) -> None:
        """
        Analyze function and class definitions in a Python file.

        Args:
            file_path: Path to the Python file
            tree: AST of the Python file
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                self.relationships[file_path]['functions'].append(function_name)
                self.function_map[function_name] = file_path

            elif isinstance(node, ast.ClassDef):
                class_name = node.name
                self.relationships[file_path]['classes'].append(class_name)

                # Also map methods to this file
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_name = f"{class_name}.{item.name}"
                        self.function_map[method_name] = file_path

    def _analyze_function_calls(self, file_path: str, tree: ast.Module) -> None:
        """
        Analyze function calls in a Python file.

        Args:
            file_path: Path to the Python file
            tree: AST of the Python file
        """
        function_calls = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    # Direct function call: func()
                    function_name = node.func.id
                    if function_name not in function_calls:
                        function_calls[function_name] = 0
                    function_calls[function_name] += 1

                elif isinstance(node, ast.Attribute):
                    # Method call: obj.method()
                    if isinstance(node.func.value, ast.Name):
                        object_name = node.func.value.id
                        method_name = node.func.attr
                        full_name = f"{object_name}.{method_name}"
                        if full_name not in function_calls:
                            function_calls[full_name] = 0
                        function_calls[full_name] += 1

        self.relationships[file_path]['function_calls'] = function_calls

    def _resolve_function_calls(self) -> None:
        """
        Resolve function calls to determine file dependencies.
        """
        for file_path, info in self.relationships.items():
            for function_name, count in info['function_calls'].items():
                if function_name in self.function_map:
                    called_file = self.function_map[function_name]
                    if called_file != file_path:  # Avoid self-dependencies
                        if called_file not in info['dependencies']:
                            info['dependencies'].append(called_file)

    def save_relationships(self, output_path: str) -> None:
        """
        Save the analyzed relationships to a JSON file.

        Args:
            output_path: Path to save the relationships
        """
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.relationships, f, indent=2)

        logger.info(f"Saved relationships to {output_path}")

    def load_relationships(self, input_path: str) -> Dict[str, Any]:
        """
        Load relationships from a JSON file.

        Args:
            input_path: Path to load the relationships from

        Returns:
            Dictionary containing relationships
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            self.relationships = json.load(f)

        logger.info(f"Loaded relationships from {input_path}")
        return self.relationships

    def get_relationships(self) -> Dict[str, Any]:
        """
        Get the current relationships.

        Returns:
            Dictionary containing relationships
        """
        return self.relationships
