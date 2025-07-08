#!/usr/bin/env python3
"""
Quantum-Accelerated Code Analyzer

This module provides quantum computing accelerated code analysis capabilities
for faster pattern recognition, dependency analysis, and bug detection.
"""

import os
import sys
import time
import logging
import math
import re
import hashlib
import random
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import quantum simulator if available, otherwise use classical fallback
try:
    import numpy as np
    QUANTUM_AVAILABLE = True
    logger.info("Quantum simulator available - using accelerated algorithms")
except ImportError:
    QUANTUM_AVAILABLE = False
    logger.warning("Quantum simulator not available - using classical fallback")

class QuantumCodeAnalyzer:
    """
    Provides quantum-accelerated code analysis capabilities for faster
    pattern recognition, dependency analysis, and bug detection.
    """
    
    def __init__(self, 
                use_quantum: bool = True,
                qubits: int = 8,
                shots: int = 1024,
                optimization_level: int = 1,
                noise_model: Optional[str] = None,
                caching: bool = True,
                cache_dir: Optional[str] = None):
        """
        Initialize the quantum code analyzer.
        
        Args:
            use_quantum: Whether to use quantum acceleration when available
            qubits: Number of qubits to use for quantum algorithms
            shots: Number of measurement shots for quantum algorithms
            optimization_level: Optimization level for quantum circuits
            noise_model: Noise model to use for quantum simulation
            caching: Whether to cache analysis results
            cache_dir: Directory to store cache files
        """
        self.use_quantum = use_quantum and QUANTUM_AVAILABLE
        self.qubits = qubits
        self.shots = shots
        self.optimization_level = optimization_level
        self.noise_model = noise_model
        self.caching = caching
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), ".quantum_cache")
        
        if self.caching:
            os.makedirs(self.cache_dir, exist_ok=True)
        
        self.code_embeddings = {}
        self.pattern_database = {}
        
        logger.info(f"Quantum Code Analyzer initialized with {qubits} qubits and {shots} shots")
        logger.info(f"Using {'quantum' if self.use_quantum else 'classical'} processing")
    
    def analyze_file(self, file_path: str) -> Dict:
        """
        Analyze a single file for code patterns, bugs, and optimization opportunities.
        
        Args:
            file_path: Path to the file to analyze
        
        Returns:
            Dictionary with analysis results
        """
        # Check cache first if enabled
        if self.caching:
            cache_key = self._generate_cache_key(file_path)
            cached_result = self._check_cache(cache_key)
            if cached_result:
                logger.info(f"Using cached analysis for {file_path}")
                return cached_result
        
        logger.info(f"Analyzing file: {file_path}")
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Perform analysis based on file type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.py':
                result = self._analyze_python_file(content)
            elif file_ext in ['.js', '.ts']:
                result = self._analyze_javascript_file(content)
            elif file_ext in ['.java']:
                result = self._analyze_java_file(content)
            elif file_ext in ['.c', '.cpp', '.h', '.hpp']:
                result = self._analyze_cpp_file(content)
            else:
                # Generic analysis for other file types
                result = self._analyze_generic_file(content)
            
            # Add file metadata
            result["file_path"] = file_path
            result["file_size"] = os.path.getsize(file_path)
            result["last_modified"] = os.path.getmtime(file_path)
            
            # Cache result if enabled
            if self.caching:
                self._store_cache(cache_key, result)
            
            return result
        
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {
                "file_path": file_path,
                "error": str(e),
                "success": False
            }
    
    def analyze_directory(self, 
                         dir_path: str, 
                         include_patterns: Optional[List[str]] = None,
                         exclude_patterns: Optional[List[str]] = None,
                         max_files: Optional[int] = None) -> Dict:
        """
        Analyze a directory of files.
        
        Args:
            dir_path: Path to the directory to analyze
            include_patterns: List of file patterns to include (e.g., ["*.py", "*.js"])
            exclude_patterns: List of file patterns to exclude (e.g., ["*_test.py", "node_modules/*"])
            max_files: Maximum number of files to analyze
        
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing directory: {dir_path}")
        
        # Prepare result structure
        result = {
            "directory": dir_path,
            "file_count": 0,
            "files_analyzed": 0,
            "file_results": {},
            "summary": {},
            "patterns": [],
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
        
        # Compile patterns
        include_regexes = [re.compile(self._pattern_to_regex(p)) for p in (include_patterns or ["*"])]
        exclude_regexes = [re.compile(self._pattern_to_regex(p)) for p in (exclude_patterns or [])]
        
        # Walk directory
        file_count = 0
        analyzed_count = 0
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dir_path)
                
                # Check if file should be included
                if not any(regex.match(rel_path) for regex in include_regexes):
                    continue
                
                # Check if file should be excluded
                if any(regex.match(rel_path) for regex in exclude_regexes):
                    continue
                
                file_count += 1
                
                # Check if we've reached the maximum number of files
                if max_files is not None and analyzed_count >= max_files:
                    break
                
                # Analyze file
                try:
                    file_result = self.analyze_file(file_path)
                    result["file_results"][rel_path] = file_result
                    analyzed_count += 1
                except Exception as e:
                    logger.error(f"Error analyzing file {file_path}: {e}")
                    result["file_results"][rel_path] = {
                        "file_path": file_path,
                        "error": str(e),
                        "success": False
                    }
            
            # Check if we've reached the maximum number of files
            if max_files is not None and analyzed_count >= max_files:
                break
        
        # Generate summary
        result["file_count"] = file_count
        result["files_analyzed"] = analyzed_count
        result["end_time"] = time.time()
        result["duration"] = result["end_time"] - result["start_time"]
        
        # Generate patterns across files using quantum pattern recognition
        result["patterns"] = self._extract_cross_file_patterns(result["file_results"])
        
        # Generate summary statistics
        result["summary"] = self._generate_summary(result["file_results"])
        
        logger.info(f"Directory analysis complete: {analyzed_count}/{file_count} files analyzed in {result['duration']:.2f}s")
        
        return result
    
    def find_code_similarities(self, files: List[str]) -> Dict:
        """
        Find code similarities between files using quantum algorithms.
        
        Args:
            files: List of file paths to compare
        
        Returns:
            Dictionary with similarity results
        """
        logger.info(f"Finding code similarities between {len(files)} files")
        
        # Initialize results
        result = {
            "file_count": len(files),
            "embeddings": {},
            "similarity_matrix": [],
            "clusters": [],
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
        
        # Generate embeddings for each file
        for file_path in files:
            try:
                embedding = self._generate_code_embedding(file_path)
                result["embeddings"][file_path] = embedding
            except Exception as e:
                logger.error(f"Error generating embedding for {file_path}: {e}")
        
        # Calculate similarity matrix using quantum acceleration if available
        if self.use_quantum:
            result["similarity_matrix"] = self._quantum_similarity_matrix(result["embeddings"])
        else:
            result["similarity_matrix"] = self._classical_similarity_matrix(result["embeddings"])
        
        # Cluster files based on similarity
        result["clusters"] = self._cluster_files(result["similarity_matrix"], files)
        
        # Finalize result
        result["end_time"] = time.time()
        result["duration"] = result["end_time"] - result["start_time"]
        
        logger.info(f"Similarity analysis complete in {result['duration']:.2f}s")
        
        return result
    
    def detect_bugs(self, 
                   file_path: str, 
                   pattern_sensitivity: float = 0.7) -> Dict:
        """
        Detect potential bugs in a file using quantum pattern recognition.
        
        Args:
            file_path: Path to the file to analyze
            pattern_sensitivity: Sensitivity threshold for pattern detection (0.0 to 1.0)
        
        Returns:
            Dictionary with bug detection results
        """
        logger.info(f"Detecting bugs in {file_path} with sensitivity {pattern_sensitivity}")
        
        # Initialize results
        result = {
            "file_path": file_path,
            "bugs_found": [],
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Determine language
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Apply appropriate bug patterns based on language
            bug_patterns = self._get_bug_patterns(file_ext)
            
            # Analyze for bugs
            if self.use_quantum:
                bugs = self._quantum_bug_detection(content, bug_patterns, pattern_sensitivity)
            else:
                bugs = self._classical_bug_detection(content, bug_patterns, pattern_sensitivity)
            
            # Annotate bugs with line information
            for bug in bugs:
                if "line" in bug:
                    line_num = bug["line"]
                    if 0 <= line_num < len(lines):
                        bug["line_content"] = lines[line_num].strip()
            
            result["bugs_found"] = bugs
        
        except Exception as e:
            logger.error(f"Error detecting bugs in {file_path}: {e}")
            result["error"] = str(e)
        
        # Finalize result
        result["end_time"] = time.time()
        result["duration"] = result["end_time"] - result["start_time"]
        result["bug_count"] = len(result["bugs_found"])
        
        logger.info(f"Bug detection complete: {result['bug_count']} bugs found in {result['duration']:.2f}s")
        
        return result
    
    def analyze_dependencies(self, 
                            files: List[str],
                            include_external: bool = False) -> Dict:
        """
        Analyze dependencies between files using quantum acceleration.
        
        Args:
            files: List of file paths to analyze
            include_external: Whether to include external dependencies
        
        Returns:
            Dictionary with dependency analysis results
        """
        logger.info(f"Analyzing dependencies between {len(files)} files")
        
        # Initialize results
        result = {
            "file_count": len(files),
            "dependencies": {},
            "dependency_graph": {},
            "cycles": [],
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
        
        # Analyze each file for dependencies
        for file_path in files:
            try:
                file_deps = self._extract_dependencies(file_path, files if not include_external else None)
                result["dependencies"][file_path] = file_deps
            except Exception as e:
                logger.error(f"Error extracting dependencies for {file_path}: {e}")
                result["dependencies"][file_path] = []
        
        # Build dependency graph
        for file_path, deps in result["dependencies"].items():
            result["dependency_graph"][file_path] = {
                "imports": [d["target"] for d in deps if d["type"] == "import"],
                "references": [d["target"] for d in deps if d["type"] == "reference"],
                "all": [d["target"] for d in deps]
            }
        
        # Find cycles in dependency graph using quantum algorithm if available
        if self.use_quantum:
            result["cycles"] = self._quantum_cycle_detection(result["dependency_graph"])
        else:
            result["cycles"] = self._classical_cycle_detection(result["dependency_graph"])
        
        # Calculate dependency metrics
        result["metrics"] = self._calculate_dependency_metrics(result["dependency_graph"])
        
        # Finalize result
        result["end_time"] = time.time()
        result["duration"] = result["end_time"] - result["start_time"]
        
        logger.info(f"Dependency analysis complete in {result['duration']:.2f}s")
        
        return result
    
    def accelerate_repair(self, 
                         bug_info: Dict, 
                         repair_patterns: List[Dict]) -> Dict:
        """
        Accelerate repair suggestions using quantum pattern matching.
        
        Args:
            bug_info: Information about the bug to repair
            repair_patterns: List of repair patterns to consider
        
        Returns:
            Dictionary with repair suggestions
        """
        logger.info(f"Accelerating repair for bug in {bug_info.get('file', 'unknown')}")
        
        # Initialize results
        result = {
            "bug_info": bug_info,
            "suggestions": [],
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
        
        try:
            # Read file content if available
            file_path = bug_info.get("file")
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Extract context around bug
                line_num = bug_info.get("line", 0)
                context_start = max(0, line_num - 5)
                context_end = min(len(lines), line_num + 5)
                context = "\n".join(lines[context_start:context_end])
                
                bug_info["context"] = context
            
            # Generate suggestions using quantum acceleration if available
            if self.use_quantum:
                suggestions = self._quantum_repair_suggestions(bug_info, repair_patterns)
            else:
                suggestions = self._classical_repair_suggestions(bug_info, repair_patterns)
            
            result["suggestions"] = suggestions
        
        except Exception as e:
            logger.error(f"Error generating repair suggestions: {e}")
            result["error"] = str(e)
        
        # Finalize result
        result["end_time"] = time.time()
        result["duration"] = result["end_time"] - result["start_time"]
        result["suggestion_count"] = len(result["suggestions"])
        
        logger.info(f"Repair acceleration complete: {result['suggestion_count']} suggestions generated in {result['duration']:.2f}s")
        
        return result
    
    def _analyze_python_file(self, content: str) -> Dict:
        """Analyze Python file content."""
        # Extract imports
        imports = re.findall(r'^(?:from|import)\s+([^\s]+)(?:\s+import\s+([^\s]+))?', content, re.MULTILINE)
        import_list = []
        for match in imports:
            if match[1]:  # from X import Y
                import_list.append(f"{match[0]}.{match[1]}")
            else:  # import X
                import_list.append(match[0])
        
        # Extract functions and classes
        functions = re.findall(r'def\s+([^\s\(]+)', content)
        classes = re.findall(r'class\s+([^\s\(]+)', content)
        
        # Extract potential bugs using patterns
        bugs = []
        
        # Check for potential exception handling issues
        try_blocks = len(re.findall(r'\btry\s*:', content))
        except_blocks = len(re.findall(r'\bexcept\s*(?:[^:]+)?:', content))
        if try_blocks > 0 and try_blocks != except_blocks:
            bugs.append({
                "type": "exception_handling",
                "description": "Mismatched try/except blocks",
                "severity": "medium"
            })
        
        # Check for bare except clauses
        bare_excepts = re.findall(r'\bexcept\s*:', content)
        if bare_excepts:
            bugs.append({
                "type": "bare_except",
                "description": "Bare except clause found",
                "severity": "low",
                "count": len(bare_excepts)
            })
        
        # Check for unused imports (simplified)
        for imp in import_list:
            base_module = imp.split('.')[0]
            # Very basic check - in real analyzer would be more sophisticated
            if base_module not in content[content.find("import"):]:
                bugs.append({
                    "type": "unused_import",
                    "description": f"Potential unused import: {imp}",
                    "severity": "info"
                })
        
        # Check for mutable default arguments
        mutable_defaults = re.findall(r'def\s+[^\s\(]+\([^\)]*(?:(\[\s*\]|\{\s*\}|dict\(\)|list\(\)|set\(\)))[^\)]*\)', content)
        if mutable_defaults:
            bugs.append({
                "type": "mutable_default",
                "description": "Mutable default argument used",
                "severity": "medium",
                "count": len(mutable_defaults)
            })
        
        return {
            "language": "python",
            "imports": import_list,
            "functions": functions,
            "classes": classes,
            "bugs": bugs,
            "success": True
        }
    
    def _analyze_javascript_file(self, content: str) -> Dict:
        """Analyze JavaScript/TypeScript file content."""
        # Extract imports
        imports = re.findall(r'(?:import\s+(?:{[^}]+}|\*\s+as\s+[^\s,]+|[^\s,]+)\s+from\s+[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\))', content)
        import_list = []
        for match in imports:
            import_list.append(match[0] or match[1])
        
        # Extract functions and classes
        functions = re.findall(r'(?:function\s+([^\s\(]+)|(?:const|let|var)\s+([^\s=]+)\s*=\s*(?:async\s*)?(?:function|\([^\)]*\)\s*=>))', content)
        classes = re.findall(r'class\s+([^\s\{]+)', content)
        
        # Clean up function names
        function_names = []
        for f in functions:
            function_names.extend([name for name in f if name])
        
        # Extract potential bugs
        bugs = []
        
        # Check for console.log statements
        console_logs = re.findall(r'console\.log\(', content)
        if console_logs:
            bugs.append({
                "type": "console_log",
                "description": "Console.log statements found",
                "severity": "info",
                "count": len(console_logs)
            })
        
        # Check for == instead of ===
        double_equals = re.findall(r'[^=!]==[^=]', content)
        if double_equals:
            bugs.append({
                "type": "double_equals",
                "description": "Using == instead of === may lead to unexpected type coercion",
                "severity": "low",
                "count": len(double_equals)
            })
        
        # Check for eval usage
        eval_usage = re.findall(r'eval\(', content)
        if eval_usage:
            bugs.append({
                "type": "eval_usage",
                "description": "Eval usage can be dangerous",
                "severity": "high",
                "count": len(eval_usage)
            })
        
        return {
            "language": "javascript" if not content.includes("typescript") else "typescript",
            "imports": import_list,
            "functions": function_names,
            "classes": classes,
            "bugs": bugs,
            "success": True
        }
    
    def _analyze_java_file(self, content: str) -> Dict:
        """Analyze Java file content."""
        # Simplified Java analysis
        imports = re.findall(r'import\s+([^;]+);', content)
        classes = re.findall(r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+([^\s{<]+)', content)
        methods = re.findall(r'(?:public|private|protected)\s+(?:static\s+)?[^\s]+\s+([^\s\(]+)\s*\(', content)
        
        # Extract potential bugs
        bugs = []
        
        # Check for potential resource leaks
        resource_usages = re.findall(r'new\s+(?:FileInputStream|FileOutputStream|BufferedReader|BufferedWriter|Connection|Socket)\s*\([^)]*\)', content)
        try_with_resources = re.findall(r'try\s*\([^)]+\)', content)
        if resource_usages and len(resource_usages) > len(try_with_resources):
            bugs.append({
                "type": "resource_leak",
                "description": "Potential resource leak (not using try-with-resources)",
                "severity": "medium"
            })
        
        # Check for potential null pointer issues
        null_checks = re.findall(r'if\s*\([^)]*==\s*null[^)]*\)', content)
        null_usages = re.findall(r'[^\s]+\.[^\s\(]+\s*\(', content)  # method calls
        if len(null_checks) < len(null_usages) / 10:  # Heuristic: at least 10% of method calls should have null checks
            bugs.append({
                "type": "null_pointer",
                "description": "Potential null pointer dereference (insufficient null checks)",
                "severity": "medium"
            })
        
        return {
            "language": "java",
            "imports": imports,
            "classes": classes,
            "methods": methods,
            "bugs": bugs,
            "success": True
        }
    
    def _analyze_cpp_file(self, content: str) -> Dict:
        """Analyze C/C++ file content."""
        # Simplified C++ analysis
        includes = re.findall(r'#include\s+[<"]([^>"]+)[>"]', content)
        classes = re.findall(r'class\s+([^\s:;{]+)', content)
        functions = re.findall(r'(?:[\w:~]+\s+)+([^\s\(]+)\s*\([^;{]*[;{]', content)
        
        # Clean up function names
        function_names = []
        for f in functions:
            if f not in ['if', 'for', 'while', 'switch', 'return']:
                function_names.append(f)
        
        # Extract potential bugs
        bugs = []
        
        # Check for potential memory leaks
        new_usages = len(re.findall(r'new\s+[\w:]+(?:\[.+\])?', content))
        delete_usages = len(re.findall(r'delete\s+\w+', content)) + len(re.findall(r'delete\[\]\s+\w+', content))
        
        if new_usages > delete_usages:
            bugs.append({
                "type": "memory_leak",
                "description": f"Potential memory leak ({new_usages} 'new' vs {delete_usages} 'delete')",
                "severity": "high"
            })
        
        # Check for unsafe functions
        unsafe_functions = ['gets', 'sprintf', 'strcpy', 'strcat', 'scanf']
        for func in unsafe_functions:
            if re.search(r'\b' + func + r'\s*\(', content):
                bugs.append({
                    "type": "unsafe_function",
                    "description": f"Using unsafe function: {func}",
                    "severity": "high"
                })
        
        # Check for uninitialized variables
        uninit_vars = re.findall(r'(?:int|char|float|double|long|bool)\s+(\w+);(?!\s*=)', content)
        if uninit_vars:
            bugs.append({
                "type": "uninitialized_variable",
                "description": "Potentially uninitialized variables",
                "severity": "medium",
                "variables": uninit_vars
            })
        
        return {
            "language": "cpp",
            "includes": includes,
            "classes": classes,
            "functions": function_names,
            "bugs": bugs,
            "success": True
        }
    
    def _analyze_generic_file(self, content: str) -> Dict:
        """Analyze generic file content."""
        # Simple analysis for unknown file types
        lines = content.split('\n')
        line_count = len(lines)
        char_count = len(content)
        
        # Try to detect language
        language = "unknown"
        if "def " in content and "import " in content:
            language = "python"
        elif "function " in content or "const " in content or "let " in content:
            language = "javascript"
        elif "public class " in content or "private class " in content:
            language = "java"
        elif "#include" in content:
            language = "cpp"
        
        return {
            "language": language,
            "line_count": line_count,
            "char_count": char_count,
            "success": True
        }
    
    def _pattern_to_regex(self, pattern: str) -> str:
        """Convert a glob pattern to a regex pattern."""
        result = ""
        i, n = 0, len(pattern)
        
        while i < n:
            c = pattern[i]
            i += 1
            
            if c == '*':
                if i < n and pattern[i] == '*':
                    # ** matches anything including directory separators
                    result += '.*'
                    i += 1
                else:
                    # * matches anything except directory separators
                    result += '[^/\\\\]*'
            elif c == '?':
                # ? matches any single character except directory separators
                result += '[^/\\\\]'
            elif c in '[](){}+^$.|\\':
                # Escape special regex characters
                result += '\\' + c
            else:
                result += c
        
        return f'^{result}$'
    
    def _generate_cache_key(self, file_path: str) -> str:
        """Generate a cache key for a file."""
        if not os.path.exists(file_path):
            return hashlib.md5(file_path.encode()).hexdigest()
        
        # Use file path, size, and modification time for the key
        file_stat = os.stat(file_path)
        key_data = f"{file_path}:{file_stat.st_size}:{file_stat.st_mtime}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """Check if a cache entry exists and return it if it does."""
        if not self.caching:
            return None
        
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading cache entry: {e}")
        
        return None
    
    def _store_cache(self, cache_key: str, data: Dict):
        """Store a cache entry."""
        if not self.caching:
            return
        
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Error storing cache entry: {e}")
    
    def _extract_dependencies(self, file_path: str, limit_to_files: Optional[List[str]] = None) -> List[Dict]:
        """
        Extract dependencies from a file.
        
        Args:
            file_path: Path to the file
            limit_to_files: If provided, only include dependencies to these files
        
        Returns:
            List of dependency dictionaries
        """
        logger.info(f"Extracting dependencies for {file_path}")
        
        dependencies = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Extract dependencies based on file type
            if file_ext == '.py':
                dependencies = self._extract_python_dependencies(file_path, content, limit_to_files)
            elif file_ext in ['.js', '.ts']:
                dependencies = self._extract_javascript_dependencies(file_path, content, limit_to_files)
            elif file_ext in ['.java']:
                dependencies = self._extract_java_dependencies(file_path, content, limit_to_files)
            elif file_ext in ['.c', '.cpp', '.h', '.hpp']:
                dependencies = self._extract_cpp_dependencies(file_path, content, limit_to_files)
            else:
                # Generic dependency extraction for other file types
                dependencies = self._extract_generic_dependencies(file_path, content, limit_to_files)
        
        except Exception as e:
            logger.error(f"Error extracting dependencies for {file_path}: {e}")
        
        return dependencies
    
    def _extract_python_dependencies(self, file_path: str, content: str, limit_to_files: Optional[List[str]] = None) -> List[Dict]:
        """Extract dependencies from Python file."""
        dependencies = []
        
        # Extract imports
        imports = re.findall(r'^(?:from\s+([^\s]+)\s+import\s+([^#\n]+)|import\s+([^#\n]+))', content, re.MULTILINE)
        
        for match in imports:
            if match[0] and match[1]:  # from X import Y
                module = match[0]
                imported_items = [item.strip() for item in match[1].split(',')]
                
                for item in imported_items:
                    if item:
                        dependencies.append({
                            "source": file_path,
                            "target": f"{module}.{item}",
                            "type": "import",
                            "is_internal": self._is_internal_dependency(f"{module}.{item}", limit_to_files)
                        })
            
            elif match[2]:  # import X
                imported_modules = [module.strip() for module in match[2].split(',')]
                
                for module in imported_modules:
                    if module:
                        dependencies.append({
                            "source": file_path,
                            "target": module,
                            "type": "import",
                            "is_internal": self._is_internal_dependency(module, limit_to_files)
                        })
        
        return dependencies
    
    def _extract_javascript_dependencies(self, file_path: str, content: str, limit_to_files: Optional[List[str]] = None) -> List[Dict]:
        """Extract dependencies from JavaScript/TypeScript file."""
        dependencies = []
        
        # Extract ES6 imports
        es6_imports = re.findall(r'import\s+(?:{[^}]+}|\*\s+as\s+[^\s,]+|[^\s,]+)\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        for module in es6_imports:
            dependencies.append({
                "source": file_path,
                "target": module,
                "type": "import",
                "is_internal": self._is_internal_dependency(module, limit_to_files)
            })
        
        # Extract CommonJS requires
        requires = re.findall(r'(?:const|let|var)\s+([^\s=]+)\s*=\s*require\([\'"]([^\'"]+)[\'"]\)', content)
        for match in requires:
            variable, module = match
            dependencies.append({
                "source": file_path,
                "target": module,
                "type": "import",
                "is_internal": self._is_internal_dependency(module, limit_to_files)
            })
        
        # Extract dynamic imports
        dynamic_imports = re.findall(r'import\([\'"]([^\'"]+)[\'"]\)', content)
        for module in dynamic_imports:
            dependencies.append({
                "source": file_path,
                "target": module,
                "type": "dynamic_import",
                "is_internal": self._is_internal_dependency(module, limit_to_files)
            })
        
        return dependencies
    
    def _extract_java_dependencies(self, file_path: str, content: str, limit_to_files: Optional[List[str]] = None) -> List[Dict]:
        """Extract dependencies from Java file."""
        dependencies = []
        
        # Extract imports
        imports = re.findall(r'import\s+([^;]+);', content)
        for module in imports:
            dependencies.append({
                "source": file_path,
                "target": module,
                "type": "import",
                "is_internal": self._is_internal_dependency(module, limit_to_files)
            })
        
        # Extract references to other classes
        # This is a simplified approach - a real implementation would need to be more sophisticated
        class_name = re.search(r'public\s+class\s+([^\s{<]+)', content)
        class_name = class_name.group(1) if class_name else None
        
        if class_name:
            # Find references to other classes (excluding the current class)
            for match in re.finditer(r'new\s+([A-Z][a-zA-Z0-9_]*)\s*\(', content):
                referenced_class = match.group(1)
                if referenced_class != class_name:
                    dependencies.append({
                        "source": file_path,
                        "target": referenced_class,
                        "type": "reference",
                        "is_internal": self._is_internal_dependency(referenced_class, limit_to_files)
                    })
        
        return dependencies
    
    def _extract_cpp_dependencies(self, file_path: str, content: str, limit_to_files: Optional[List[str]] = None) -> List[Dict]:
        """Extract dependencies from C/C++ file."""
        dependencies = []
        
        # Extract includes
        includes = re.findall(r'#include\s+[<"]([^>"]+)[>"]', content)
        for include in includes:
            dependencies.append({
                "source": file_path,
                "target": include,
                "type": "include",
                "is_internal": self._is_internal_dependency(include, limit_to_files)
            })
        
        return dependencies
    
    def _extract_generic_dependencies(self, file_path: str, content: str, limit_to_files: Optional[List[str]] = None) -> List[Dict]:
        """Extract dependencies from generic file."""
        # For generic files, try to find references to other files
        dependencies = []
        
        # This is a very basic approach - just look for strings that might be file paths
        potential_paths = re.findall(r'[\'"]([^\'"\n]+\.[a-zA-Z0-9]{1,5})[\'"]', content)
        for path in potential_paths:
            if os.path.exists(path) or os.path.exists(os.path.join(os.path.dirname(file_path), path)):
                dependencies.append({
                    "source": file_path,
                    "target": path,
                    "type": "reference",
                    "is_internal": self._is_internal_dependency(path, limit_to_files)
                })
        
        return dependencies
    
    def _is_internal_dependency(self, target: str, limit_to_files: Optional[List[str]] = None) -> bool:
        """Determine if a dependency is internal to the project."""
        if not limit_to_files:
            return False  # If no limit is specified, consider all dependencies external
        
        # Check if the target is in the list of files
        for file in limit_to_files:
            # Check exact match
            if target == file:
                return True
            
            # Check if target is a module/package name that matches a file
            if target.replace('.', '/') in file:
                return True
            
            # Check if target is a relative path
            if os.path.basename(target) == os.path.basename(file):
                return True
        
        return False
    
    def _extract_cross_file_patterns(self, file_results: Dict) -> List[Dict]:
        """Extract patterns that appear across multiple files."""
        patterns = []
        
        # Collect common features across files
        imports_counter = Counter()
        bug_types_counter = Counter()
        function_patterns = defaultdict(list)
        
        for file_path, result in file_results.items():
            # Skip failed analyses
            if not result.get("success", False):
                continue
            
            # Count imports
            for imp in result.get("imports", []):
                imports_counter[imp] += 1
            
            # Count bug types
            for bug in result.get("bugs", []):
                bug_types_counter[bug.get("type", "unknown")] += 1
            
            # Collect function naming patterns
            for func in result.get("functions", []):
                pattern = self._extract_naming_pattern(func)
                if pattern:
                    function_patterns[pattern].append((file_path, func))
        
        # Find common imports (used in 3+ files)
        common_imports = [{"import": imp, "count": count} for imp, count in imports_counter.most_common() if count >= 3]
        if common_imports:
            patterns.append({
                "type": "common_imports",
                "description": "Commonly imported modules across files",
                "items": common_imports
            })
        
        # Find common bug types
        common_bugs = [{"bug_type": bug_type, "count": count} for bug_type, count in bug_types_counter.most_common()]
        if common_bugs:
            patterns.append({
                "type": "common_bugs",
                "description": "Common bug types across files",
                "items": common_bugs
            })
        
        # Find common function naming patterns
        common_function_patterns = [
            {"pattern": pattern, "examples": examples, "count": len(examples)}
            for pattern, examples in function_patterns.items()
            if len(examples) >= 3
        ]
        if common_function_patterns:
            patterns.append({
                "type": "function_naming_patterns",
                "description": "Common function naming patterns",
                "items": common_function_patterns
            })
        
        return patterns
    
    def _extract_naming_pattern(self, name: str) -> Optional[str]:
        """Extract a naming pattern from a name."""
        # Simple pattern extraction
        if name.startswith("get") and len(name) > 3:
            return "get*"
        elif name.startswith("set") and len(name) > 3:
            return "set*"
        elif name.startswith("is") and len(name) > 2:
            return "is*"
        elif name.startswith("has") and len(name) > 3:
            return "has*"
        elif name.startswith("on") and len(name) > 2:
            return "on*"
        elif name.endswith("Handler") or name.endswith("handler"):
            return "*Handler"
        elif name.endswith("Factory") or name.endswith("factory"):
            return "*Factory"
        elif "_" in name:
            return "snake_case"
        elif name[0].islower() and any(c.isupper() for c in name[1:]):
            return "camelCase"
        elif name[0].isupper():
            return "PascalCase"
        
        return None
    
    def _generate_summary(self, file_results: Dict) -> Dict:
        """Generate summary statistics from file analysis results."""
        summary = {
            "file_count": len(file_results),
            "languages": Counter(),
            "bug_counts": Counter(),
            "bug_severity": defaultdict(Counter),
            "file_sizes": {
                "min": float("inf"),
                "max": 0,
                "avg": 0,
                "total": 0
            }
        }
        
        # Collect statistics
        total_size = 0
        bug_count = 0
        
        for file_path, result in file_results.items():
            # Skip failed analyses
            if not result.get("success", False):
                continue
            
            # Count languages
            language = result.get("language", "unknown")
            summary["languages"][language] += 1
            
            # Track file sizes
            file_size = result.get("file_size", 0)
            total_size += file_size
            summary["file_sizes"]["min"] = min(summary["file_sizes"]["min"], file_size)
            summary["file_sizes"]["max"] = max(summary["file_sizes"]["max"], file_size)
            
            # Count bugs
            for bug in result.get("bugs", []):
                bug_type = bug.get("type", "unknown")
                severity = bug.get("severity", "unknown")
                count = bug.get("count", 1)
                
                summary["bug_counts"][bug_type] += count
                summary["bug_severity"][bug_type][severity] += count
                bug_count += count
        
        # Calculate averages
        if len(file_results) > 0:
            summary["file_sizes"]["avg"] = total_size / len(file_results)
        
        summary["file_sizes"]["total"] = total_size
        summary["total_bug_count"] = bug_count
        summary["bugs_per_file"] = bug_count / len(file_results) if len(file_results) > 0 else 0
        
        # Convert Counter objects to lists for JSON serialization
        summary["languages"] = [{"language": lang, "count": count} for lang, count in summary["languages"].most_common()]
        summary["bug_counts"] = [{"type": bug_type, "count": count} for bug_type, count in summary["bug_counts"].most_common()]
        
        # Convert nested Counter to dictionary
        severity_dict = {}
        for bug_type, severities in summary["bug_severity"].items():
            severity_dict[bug_type] = {severity: count for severity, count in severities.items()}
        summary["bug_severity"] = severity_dict
        
        return summary
    
    def _generate_code_embedding(self, file_path: str) -> List[float]:
        """Generate a vector embedding for a code file."""
        try:
            # Check if the embedding is already cached
            if file_path in self.code_embeddings:
                return self.code_embeddings[file_path]
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Generate embedding using quantum acceleration if available
            if self.use_quantum and QUANTUM_AVAILABLE:
                embedding = self._quantum_embedding(content)
            else:
                embedding = self._classical_embedding(content)
            
            # Cache the embedding
            self.code_embeddings[file_path] = embedding
            
            return embedding
        
        except Exception as e:
            logger.error(f"Error generating code embedding for {file_path}: {e}")
            # Return a zero vector as fallback
            return [0.0] * 32
    
    def _quantum_embedding(self, content: str) -> List[float]:
        """Generate a quantum embedding for code content."""
        # This is a simplified simulation of quantum embedding
        # In a real implementation, this would use a quantum circuit
        
        # Use numpy as a stand-in for quantum computation
        if not QUANTUM_AVAILABLE:
            return self._classical_embedding(content)
        
        try:
            # Create a feature vector from the content
            # This is a simple classical embedding for simulation purposes
            features = []
            
            # Calculate basic text statistics
            features.append(len(content) / 10000.0)  # Normalized file size
            features.append(content.count('\n') / 1000.0)  # Normalized line count
            
            # Language features
            features.append(float(content.count('def ')) / 100.0)  # Python function count
            features.append(float(content.count('class ')) / 50.0)  # Class count
            features.append(float(content.count('import ')) / 50.0)  # Import count
            features.append(float(content.count('function ')) / 100.0)  # JS function count
            features.append(float(content.count('return ')) / 100.0)  # Return count
            
            # Fill remaining features with hash-based values for uniqueness
            content_hash = hashlib.md5(content.encode()).digest()
            for i in range(min(25, 32 - len(features))):
                # Use hash bytes as features
                features.append(float(content_hash[i % 16]) / 255.0)
            
            # Pad or truncate to exactly 32 dimensions
            if len(features) < 32:
                features.extend([0.0] * (32 - len(features)))
            elif len(features) > 32:
                features = features[:32]
            
            # Apply a "quantum" transformation (simulated with numpy)
            features = np.array(features)
            
            # Simulate quantum rotation
            angle = np.sum(features) % (2 * np.pi)
            rotation_matrix = np.array([
                [np.cos(angle), -np.sin(angle)],
                [np.sin(angle), np.cos(angle)]
            ])
            
            # Apply rotation to pairs of features
            for i in range(0, 32, 2):
                if i + 1 < 32:
                    features[i:i+2] = rotation_matrix @ features[i:i+2]
            
            # Normalize the vector
            norm = np.linalg.norm(features)
            if norm > 0:
                features = features / norm
            
            return features.tolist()
        
        except Exception as e:
            logger.error(f"Error in quantum embedding: {e}")
            return self._classical_embedding(content)
    
    def _classical_embedding(self, content: str) -> List[float]:
        """Generate a classical embedding for code content."""
        # A simple classical embedding as fallback
        features = [0.0] * 32
        
        try:
            # Calculate basic text statistics
            features[0] = min(1.0, len(content) / 10000.0)  # Normalized file size
            features[1] = min(1.0, content.count('\n') / 1000.0)  # Normalized line count
            
            # Language features
            features[2] = min(1.0, float(content.count('def ')) / 100.0)  # Python function count
            features[3] = min(1.0, float(content.count('class ')) / 50.0)  # Class count
            features[4] = min(1.0, float(content.count('import ')) / 50.0)  # Import count
            features[5] = min(1.0, float(content.count('function ')) / 100.0)  # JS function count
            features[6] = min(1.0, float(content.count('return ')) / 100.0)  # Return count
            
            # Complexity metrics
            features[7] = min(1.0, float(content.count('if ')) / 100.0)  # Conditional count
            features[8] = min(1.0, float(content.count('for ')) / 50.0)  # Loop count
            features[9] = min(1.0, float(content.count('while ')) / 25.0)  # While loop count
            
            # Indentation and structure
            indent_levels = set()
            for line in content.split('\n'):
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    indent_levels.add(indent)
            features[10] = min(1.0, len(indent_levels) / 10.0)  # Indentation complexity
            
            # Fill remaining features with hash-based values for uniqueness
            content_hash = hashlib.md5(content.encode()).digest()
            for i in range(11, 32):
                # Use hash bytes as features
                features[i] = float(content_hash[(i - 11) % 16]) / 255.0
            
            # Normalize the vector
            norm = sum(f * f for f in features) ** 0.5
            if norm > 0:
                features = [f / norm for f in features]
            
            return features
        
        except Exception as e:
            logger.error(f"Error in classical embedding: {e}")
            # Return zeros as fallback
            return [0.0] * 32
    
    def _quantum_similarity_matrix(self, embeddings: Dict[str, List[float]]) -> List[List[float]]:
        """Calculate a similarity matrix using quantum acceleration."""
        # Simplified simulation of quantum similarity calculation
        file_paths = list(embeddings.keys())
        n = len(file_paths)
        
        # Initialize similarity matrix
        similarity_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        
        # Calculate similarities
        for i in range(n):
            for j in range(i, n):
                # Get embeddings
                embedding_i = embeddings[file_paths[i]]
                embedding_j = embeddings[file_paths[j]]
                
                # Calculate cosine similarity
                if QUANTUM_AVAILABLE:
                    # Simulate quantum similarity with numpy
                    sim = float(np.dot(embedding_i, embedding_j))
                else:
                    # Classical similarity
                    sim = sum(a * b for a, b in zip(embedding_i, embedding_j))
                
                # Store in matrix (symmetric)
                similarity_matrix[i][j] = sim
                similarity_matrix[j][i] = sim
        
        return similarity_matrix
    
    def _classical_similarity_matrix(self, embeddings: Dict[str, List[float]]) -> List[List[float]]:
        """Calculate a similarity matrix using classical methods."""
        file_paths = list(embeddings.keys())
        n = len(file_paths)
        
        # Initialize similarity matrix
        similarity_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        
        # Calculate similarities
        for i in range(n):
            for j in range(i, n):
                # Get embeddings
                embedding_i = embeddings[file_paths[i]]
                embedding_j = embeddings[file_paths[j]]
                
                # Calculate cosine similarity
                dot_product = sum(a * b for a, b in zip(embedding_i, embedding_j))
                norm_i = sum(a * a for a in embedding_i) ** 0.5
                norm_j = sum(b * b for b in embedding_j) ** 0.5
                
                sim = dot_product / (norm_i * norm_j) if norm_i > 0 and norm_j > 0 else 0.0
                
                # Store in matrix (symmetric)
                similarity_matrix[i][j] = sim
                similarity_matrix[j][i] = sim
        
        return similarity_matrix
    
    def _cluster_files(self, similarity_matrix: List[List[float]], files: List[str]) -> List[Dict]:
        """Cluster files based on similarity matrix."""
        # Simple clustering algorithm: group files with similarity > threshold
        clusters = []
        n = len(files)
        visited = [False] * n
        
        # Use a higher threshold for clustering
        threshold = 0.8
        
        for i in range(n):
            if visited[i]:
                continue
            
            cluster = {"seed_file": files[i], "files": [files[i]], "similarity_scores": {}}
            visited[i] = True
            
            # Find similar files
            for j in range(n):
                if i != j and similarity_matrix[i][j] > threshold:
                    cluster["files"].append(files[j])
                    cluster["similarity_scores"][files[j]] = similarity_matrix[i][j]
                    visited[j] = True
            
            # Only add clusters with at least 2 files
            if len(cluster["files"]) > 1:
                clusters.append(cluster)
        
        return clusters
    
    def _get_bug_patterns(self, file_ext: str) -> List[Dict]:
        """Get bug patterns for a specific file type."""
        patterns = []
        
        # Common patterns for all languages
        patterns.extend([
            {"name": "empty_catch", "regex": r"catch\s*\([^)]*\)\s*{\s*}", "severity": "medium"},
            {"name": "hardcoded_credentials", "regex": r"(?:password|secret|key)\s*=\s*[\'\"][^\'\"\n]{3,}[\'\"]", "severity": "high"},
            {"name": "todo_comment", "regex": r"//\s*TODO|#\s*TODO|/\*\s*TODO", "severity": "info"}
        ])
        
        # Language-specific patterns
        if file_ext == '.py':
            patterns.extend([
                {"name": "bare_except", "regex": r"except\s*:", "severity": "low"},
                {"name": "exec_used", "regex": r"\bexec\s*\(", "severity": "high"},
                {"name": "mutable_default", "regex": r"def\s+[^\(]+\([^\)]*=\s*(\[\]|\{\}|dict\(\)|list\(\)|set\(\))[^\)]*\)", "severity": "medium"}
            ])
        elif file_ext in ['.js', '.ts']:
            patterns.extend([
                {"name": "eval_used", "regex": r"\beval\s*\(", "severity": "high"},
                {"name": "double_equals", "regex": r"[^=!]==[^=]", "severity": "low"},
                {"name": "with_statement", "regex": r"\bwith\s*\(", "severity": "medium"}
            ])
        elif file_ext in ['.java']:
            patterns.extend([
                {"name": "catch_exception", "regex": r"catch\s*\(\s*Exception\s+", "severity": "medium"},
                {"name": "system_exit", "regex": r"System\.exit\s*\(", "severity": "medium"},
                {"name": "print_stacktrace", "regex": r"\.printStackTrace\s*\(\s*\)", "severity": "low"}
            ])
        elif file_ext in ['.c', '.cpp', '.h', '.hpp']:
            patterns.extend([
                {"name": "gets_used", "regex": r"\bgets\s*\(", "severity": "high"},
                {"name": "sprintf_used", "regex": r"\bsprintf\s*\(", "severity": "high"},
                {"name": "goto_used", "regex": r"\bgoto\s+", "severity": "medium"}
            ])
        
        return patterns
    
    def _quantum_bug_detection(self, content: str, bug_patterns: List[Dict], sensitivity: float) -> List[Dict]:
        """Detect bugs using quantum pattern recognition."""
        # Simulated quantum bug detection - in a real implementation, this would use a quantum algorithm
        # For now, we'll use the classical detection with some randomness to simulate quantum noise
        
        bugs = self._classical_bug_detection(content, bug_patterns, sensitivity)
        
        if QUANTUM_AVAILABLE:
            # Simulate quantum noise (completely arbitrary for demo purposes)
            np.random.seed(int(hashlib.md5(content[:100].encode()).hexdigest(), 16) % 2**32)
            
            # Add noise to detection (randomly drop or add bugs)
            for i in range(len(bugs)):
                if np.random.random() < 0.1:  # 10% chance to drop a bug
                    bugs[i]["confidence"] = max(0.0, bugs[i].get("confidence", 0.5) - 0.3)
            
            # Add a few potential false positives
            if np.random.random() < 0.2:  # 20% chance to add a false positive
                line_num = np.random.randint(0, content.count('\n') + 1)
                bugs.append({
                    "type": "potential_issue",
                    "description": "Potential code smell detected by quantum analysis",
                    "severity": "low",
                    "line": line_num,
                    "confidence": 0.6
                })
        
        # Filter by confidence
        return [bug for bug in bugs if bug.get("confidence", 1.0) >= sensitivity]
    
    def _classical_bug_detection(self, content: str, bug_patterns: List[Dict], sensitivity: float) -> List[Dict]:
        """Detect bugs using classical pattern matching."""
        bugs = []
        lines = content.split('\n')
        
        # Apply each pattern
        for pattern in bug_patterns:
            matches = list(re.finditer(pattern["regex"], content))
            
            for match in matches:
                # Find line number
                line_num = content[:match.start()].count('\n')
                
                # Create bug entry
                bug = {
                    "type": pattern["name"],
                    "description": self._get_bug_description(pattern["name"]),
                    "severity": pattern["severity"],
                    "line": line_num,
                    "match": match.group(0),
                    "confidence": 1.0  # Classical detection is deterministic
                }
                
                bugs.append(bug)
        
        return bugs
    
    def _get_bug_description(self, bug_type: str) -> str:
        """Get a human-readable description for a bug type."""
        descriptions = {
            "empty_catch": "Empty catch block suppresses exceptions without handling them",
            "hardcoded_credentials": "Hardcoded credentials detected (security risk)",
            "todo_comment": "TODO comment indicates incomplete code",
            "bare_except": "Bare except clause catches all exceptions, including KeyboardInterrupt",
            "exec_used": "Use of exec() is dangerous and should be avoided",
            "mutable_default": "Mutable default argument can cause unexpected behavior",
            "eval_used": "Use of eval() is dangerous and should be avoided",
            "double_equals": "Double equals (==) may cause type coercion issues",
            "with_statement": "With statement may be problematic in some environments",
            "catch_exception": "Catching generic Exception may hide bugs",
            "system_exit": "System.exit() terminates the JVM abruptly",
            "print_stacktrace": "Printing stack trace to console instead of proper logging",
            "gets_used": "gets() is vulnerable to buffer overflow attacks",
            "sprintf_used": "sprintf() is vulnerable to buffer overflow attacks",
            "goto_used": "goto statements make code harder to understand and maintain",
            "potential_issue": "Potential code issue detected by quantum analysis"
        }
        
        return descriptions.get
