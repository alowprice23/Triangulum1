"""
Implementation Agent

This agent specializes in implementing repair strategies provided by the Strategy Agent.
It generates the actual code changes needed to fix bugs in the codebase with advanced
code analysis, runtime environment detection, and robust validation.
"""

import logging
import os
import ast
import re
import difflib
import sys
import platform
import subprocess
import tempfile
import time
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional, Union, Callable

from .base_agent import BaseAgent
from .message import AgentMessage, MessageType, ConfidenceLevel
from .message_bus import MessageBus
from ..core.exceptions import TriangulumError, ImplementationError

logger = logging.getLogger(__name__)


class ImplementationMetrics:
    """Metrics for tracking implementation performance and success rates."""
    
    def __init__(self):
        """Initialize the metrics container."""
        self.total_implementations = 0
        self.successful_implementations = 0
        self.failed_implementations = 0
        self.implementation_times = []
        self.patch_sizes = []
        self.file_counts = []
        self.validation_success_rate = 0.0
        self.rollback_count = 0
        self.language_stats = {}
        self.bug_type_stats = {}
        self.start_time = None
        self.end_time = None
    
    def start_implementation(self):
        """Record the start of an implementation."""
        self.start_time = time.time()
    
    def end_implementation(self, success: bool, files_changed: int, patch_size: int, language: str, bug_type: str):
        """
        Record the end of an implementation.
        
        Args:
            success: Whether the implementation was successful
            files_changed: Number of files changed
            patch_size: Size of the patch in bytes
            language: Programming language of the implementation
            bug_type: Type of bug fixed
        """
        self.end_time = time.time()
        
        # Update implementation count
        self.total_implementations += 1
        if success:
            self.successful_implementations += 1
        else:
            self.failed_implementations += 1
        
        # Record implementation time
        if self.start_time is not None:
            self.implementation_times.append(self.end_time - self.start_time)
        
        # Record patch metrics
        self.patch_sizes.append(patch_size)
        self.file_counts.append(files_changed)
        
        # Update language statistics
        if language in self.language_stats:
            self.language_stats[language] += 1
        else:
            self.language_stats[language] = 1
        
        # Update bug type statistics
        if bug_type in self.bug_type_stats:
            self.bug_type_stats[bug_type] += 1
        else:
            self.bug_type_stats[bug_type] = 1
    
    def record_validation(self, success: bool):
        """
        Record a validation result.
        
        Args:
            success: Whether the validation was successful
        """
        # Update validation success rate
        if self.total_implementations > 0:
            if success:
                # Weighted average to account for new validation
                self.validation_success_rate = (
                    (self.validation_success_rate * (self.total_implementations - 1) + 1) / 
                    self.total_implementations
                )
            else:
                self.validation_success_rate = (
                    (self.validation_success_rate * (self.total_implementations - 1)) / 
                    self.total_implementations
                )
    
    def record_rollback(self):
        """Record a rollback operation."""
        self.rollback_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the implementation metrics.
        
        Returns:
            Dictionary containing the metrics summary
        """
        avg_time = sum(self.implementation_times) / len(self.implementation_times) if self.implementation_times else 0
        avg_patch_size = sum(self.patch_sizes) / len(self.patch_sizes) if self.patch_sizes else 0
        avg_files = sum(self.file_counts) / len(self.file_counts) if self.file_counts else 0
        
        return {
            "total_implementations": self.total_implementations,
            "success_rate": self.successful_implementations / self.total_implementations if self.total_implementations > 0 else 0,
            "avg_implementation_time": avg_time,
            "avg_patch_size": avg_patch_size,
            "avg_files_changed": avg_files,
            "validation_success_rate": self.validation_success_rate,
            "rollback_rate": self.rollback_count / self.total_implementations if self.total_implementations > 0 else 0,
            "language_distribution": self.language_stats,
            "bug_type_distribution": self.bug_type_stats
        }


class ImplementationAgent(BaseAgent):
    """
    Agent for implementing repair strategies and generating code fixes.
    
    This agent takes a repair strategy as input and produces actual code changes
    that can be applied to fix the bug. It performs advanced code analysis, generates
    language-specific patches, validates them, and provides detailed implementation
    with backup and rollback capabilities.
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_type: str = "implementation",
        message_bus: Optional[MessageBus] = None,
        subscribed_message_types: Optional[List[MessageType]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Implementation Agent.
        
        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            agent_type: Type of the agent
            message_bus: Message bus for agent communication
            subscribed_message_types: Types of messages this agent subscribes to
            config: Agent configuration dictionary
        """
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            message_bus=message_bus,
            subscribed_message_types=subscribed_message_types or [
                MessageType.TASK_REQUEST,
                MessageType.QUERY,
                MessageType.TASK_RESULT,
                MessageType.STATUS_UPDATE
            ],
            config=config
        )
        
        # Default configurations
        self.max_file_size = self.config.get("max_file_size", 1024 * 1024)  # 1 MB
        self.max_patch_size = self.config.get("max_patch_size", 1024 * 50)  # 50 KB
        self.backup_files = self.config.get("backup_files", True)
        self.backup_dir = self.config.get("backup_dir", ".triangulum/backups")
        self.validate_patches = self.config.get("validate_patches", True)
        self.progressive_patching = self.config.get("progressive_patching", True)
        self.sandbox_execution = self.config.get("sandbox_execution", True)
        self.max_validation_attempts = self.config.get("max_validation_attempts", 3)
        
        # Runtime environment information
        self.runtime_info = self._detect_runtime_environment()
        
        # Create metrics collector
        self.metrics = ImplementationMetrics()
        
        # Store implementations for learning and history
        self.implementation_history = {}
        self.successful_implementations = {}
        self.rollback_history = {}
        
        # Create backup directory if it doesn't exist
        if self.backup_files:
            os.makedirs(self.backup_dir, exist_ok=True)
    
    def _detect_runtime_environment(self) -> Dict[str, Any]:
        """
        Detect the runtime environment for tailoring implementations.
        
        Returns:
            Dictionary with runtime environment information
        """
        runtime_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "compilers": {},
            "interpreters": {},
            "build_tools": {},
            "detected_languages": []
        }
        
        # Detect language support
        language_commands = {
            "python": "python --version",
            "node": "node --version",
            "java": "java -version",
            "javac": "javac -version",
            "gcc": "gcc --version",
            "g++": "g++ --version",
            "clang": "clang --version",
            "dotnet": "dotnet --version",
            "php": "php --version",
            "ruby": "ruby --version",
            "go": "go version",
            "rust": "rustc --version",
            "swift": "swift --version",
            "npm": "npm --version",
            "pip": "pip --version",
            "mvn": "mvn --version",
            "gradle": "gradle --version",
            "make": "make --version",
            "cmake": "cmake --version"
        }
        
        for tool, command in language_commands.items():
            try:
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    # Extract version from output
                    version = result.stdout.strip() or result.stderr.strip()
                    
                    # Categorize the tool
                    if tool in ["python", "node", "java", "php", "ruby", "go", "rust", "swift"]:
                        runtime_info["interpreters"][tool] = version
                        runtime_info["detected_languages"].append(tool)
                    elif tool in ["javac", "gcc", "g++", "clang", "dotnet"]:
                        runtime_info["compilers"][tool] = version
                    elif tool in ["npm", "pip", "mvn", "gradle", "make", "cmake"]:
                        runtime_info["build_tools"][tool] = version
            
            except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                # Failed to detect this tool
                pass
        
        return runtime_info
    
    def implement_strategy(
        self,
        strategy: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Implement a repair strategy and generate code changes.
        
        Args:
            strategy: The repair strategy from the Strategy Agent
            additional_context: Additional context for implementation (optional)
            
        Returns:
            Implementation details including patches
        """
        logger.info(f"Implementing strategy: {strategy.get('name', 'Unknown')}")
        
        if not strategy or not isinstance(strategy, dict):
            raise ValueError("Invalid strategy provided")
        
        bug_type = strategy.get("bug_type")
        bug_location = strategy.get("bug_location")
        
        if not bug_location or not os.path.isfile(bug_location):
            raise ValueError(f"Invalid file location: {bug_location}")
        
        # Start metrics tracking
        self.metrics.start_implementation()
        
        try:
            # Advanced code analysis
            ast_analysis_results = self._perform_advanced_code_analysis(strategy)
            
            # Load the affected files
            file_content_map = self._load_affected_files(strategy)
            
            # Generate implementation based on the bug type
            implementation_func = self._get_implementation_function(bug_type)
            
            # Prepare additional context with runtime information
            enhanced_context = additional_context or {}
            enhanced_context.update({
                "runtime_info": self.runtime_info,
                "ast_analysis": ast_analysis_results
            })
            
            # Call the appropriate implementation function
            implementation = implementation_func(
                strategy=strategy,
                file_content_map=file_content_map,
                additional_context=enhanced_context
            )
            
            # Validate the implementation
            if self.validate_patches:
                validation_result = self._validate_implementation(implementation)
                implementation["validation_result"] = validation_result
                
                # Record validation metrics
                self.metrics.record_validation(validation_result.get("success", False))
            
            # Add general metadata
            implementation["strategy_id"] = strategy.get("id")
            implementation["bug_type"] = bug_type
            implementation["bug_location"] = bug_location
            implementation["timestamp"] = self._get_timestamp()
            implementation["implementation_id"] = self._generate_implementation_id(strategy, implementation)
            implementation["confidence_level"] = self._calculate_confidence_level(implementation)
            implementation["runtime_environment"] = self.runtime_info
            
            # Store implementation in history
            self.implementation_history[implementation["implementation_id"]] = implementation
            
            # Complete metrics tracking
            patch_size = self._calculate_patch_size(implementation)
            files_changed = len(implementation.get("patches", []))
            language = self._determine_language(bug_location)
            
            self.metrics.end_implementation(
                success=True,
                files_changed=files_changed,
                patch_size=patch_size,
                language=language,
                bug_type=bug_type
            )
            
            return implementation
            
        except Exception as e:
            logger.error(f"Error implementing strategy: {str(e)}")
            
            # Record failed implementation
            self.metrics.end_implementation(
                success=False,
                files_changed=0,
                patch_size=0,
                language=self._determine_language(bug_location),
                bug_type=bug_type
            )
            
            # Create an empty implementation with error information
            return self._create_empty_implementation(
                strategy,
                f"Implementation failed: {str(e)}"
            )
    
    def _perform_advanced_code_analysis(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform advanced code analysis for better patch generation.
        
        Args:
            strategy: The repair strategy
            
        Returns:
            Analysis results
        """
        bug_location = strategy.get("bug_location")
        bug_line = strategy.get("bug_line", 0)
        
        if not bug_location or not os.path.isfile(bug_location):
            return {}
        
        analysis_results = {
            "ast_data": {},
            "variable_usage": {},
            "function_calls": {},
            "control_flow": {},
            "dependencies": {},
            "data_flow": {},
            "context_code": {},
            "potential_fixes": []
        }
        
        try:
            # Read the file content
            with open(bug_location, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Store the context code around the bug
            lines = content.splitlines()
            context_start = max(0, bug_line - 15)
            context_end = min(len(lines), bug_line + 15)
            analysis_results["context_code"] = {
                "lines": lines[context_start:context_end],
                "start_line": context_start + 1,
                "end_line": context_end,
                "bug_line_content": lines[bug_line - 1] if 0 < bug_line <= len(lines) else ""
            }
            
            # Check file extension to determine language
            language = self._determine_language(bug_location)
            analysis_results["language"] = language
            
            # Identify additional files that might be affected
            affected_files = strategy.get("affected_files", [])
            if bug_location not in affected_files:
                affected_files.append(bug_location)
            
            # Load imports to detect dependencies
            analysis_results["dependencies"] = self._analyze_dependencies(bug_location, content)
            
            # Language-specific analysis
            if language == "python":
                python_analysis = self._analyze_python_code(content, bug_line, strategy)
                analysis_results.update(python_analysis)
            elif language == "javascript" or language == "typescript":
                js_analysis = self._analyze_js_code(content, bug_line, strategy)
                analysis_results.update(js_analysis)
            elif language == "java":
                java_analysis = self._analyze_java_code(content, bug_line, strategy)
                analysis_results.update(java_analysis)
            
            # Detect potential fixes based on bug type
            bug_type = strategy.get("bug_type", "unknown")
            bug_code = lines[bug_line - 1] if 0 < bug_line <= len(lines) else ""
            potential_fixes = self._generate_potential_fixes(bug_type, bug_code, language, analysis_results)
            analysis_results["potential_fixes"] = potential_fixes
            
        except Exception as e:
            logger.error(f"Error during advanced code analysis: {str(e)}")
            analysis_results["error"] = str(e)
        
        return analysis_results
    
    def _analyze_dependencies(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Analyze dependencies between files and modules.
        
        Args:
            file_path: Path to the file
            content: Content of the file
            
        Returns:
            Dependency analysis results
        """
        dependencies = {
            "imports": [],
            "imported_modules": [],
            "imported_from": []
        }
        
        language = self._determine_language(file_path)
        
        # Extract imports based on language
        if language == "python":
            # Match import statements
            import_pattern = r'^import\s+([\w\.]+)(?:\s+as\s+(\w+))?'
            from_import_pattern = r'^from\s+([\w\.]+)\s+import\s+(.+)$'
            
            lines = content.splitlines()
            
            for line in lines:
                line = line.strip()
                
                # Match 'import module' statements
                import_match = re.match(import_pattern, line)
                if import_match:
                    module = import_match.group(1)
                    alias = import_match.group(2) if import_match.group(2) else None
                    dependencies["imports"].append({
                        "module": module,
                        "alias": alias,
                        "type": "import"
                    })
                    dependencies["imported_modules"].append(module)
                
                # Match 'from module import names' statements
                from_match = re.match(from_import_pattern, line)
                if from_match:
                    module = from_match.group(1)
                    imported_items = [i.strip() for i in from_match.group(2).split(',')]
                    
                    dependencies["imports"].append({
                        "module": module,
                        "imported_items": imported_items,
                        "type": "from_import"
                    })
                    dependencies["imported_modules"].append(module)
                    for item in imported_items:
                        name = item.split(' as ')[0].strip()
                        dependencies["imported_from"].append({
                            "name": name,
                            "module": module
                        })
        
        elif language == "javascript" or language == "typescript":
            # Match import statements in JS/TS
            import_pattern = r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]'
            require_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*require\([\'"]([^\'"]+)[\'"]\)'
            
            lines = content.splitlines()
            
            for line in lines:
                line = line.strip()
                
                # Match ES6 imports
                for match in re.finditer(import_pattern, line):
                    imported_items = [i.strip() for i in match.group(1).split(',')]
                    module = match.group(2)
                    
                    dependencies["imports"].append({
                        "module": module,
                        "imported_items": imported_items,
                        "type": "es6_import"
                    })
                    dependencies["imported_modules"].append(module)
                
                # Match CommonJS requires
                require_match = re.match(require_pattern, line)
                if require_match:
                    variable = require_match.group(1)
                    module = require_match.group(2)
                    
                    dependencies["imports"].append({
                        "module": module,
                        "variable": variable,
                        "type": "require"
                    })
                    dependencies["imported_modules"].append(module)
        
        elif language == "java":
            # Match import statements in Java
            import_pattern = r'import\s+([\w\.]+\*?);'
            
            lines = content.splitlines()
            
            for line in lines:
                line = line.strip()
                
                # Match Java imports
                import_match = re.match(import_pattern, line)
                if import_match:
                    module = import_match.group(1)
                    
                    dependencies["imports"].append({
                        "module": module,
                        "type": "java_import"
                    })
                    dependencies["imported_modules"].append(module)
        
        return dependencies
    
    def _analyze_python_code(self, content: str, bug_line: int, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze Python code for advanced code insights.
        
        Args:
            content: Python file content
            bug_line: Line number of the bug
            strategy: The repair strategy
            
        Returns:
            Python-specific analysis results
        """
        python_analysis = {
            "ast_data": {},
            "variable_usage": {},
            "function_calls": {},
            "control_flow": {},
            "data_flow": {}
        }
        
        # Parse Python AST
        try:
            tree = ast.parse(content)
            
            # Extract function and class definitions
            functions = []
            classes = []
            variables = []
            function_calls = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    function_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": node.end_lineno if hasattr(node, 'end_lineno') else None,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                        "returns": self._get_return_annotation(node) if hasattr(node, 'returns') and node.returns else None,
                        "docstring": ast.get_docstring(node)
                    }
                    
                    # Extract function body and detect return statements
                    returns = []
                    for n in ast.walk(node):
                        if isinstance(n, ast.Return) and hasattr(n, 'lineno'):
                            returns.append({
                                "line": n.lineno,
                                "has_value": n.value is not None
                            })
                    
                    function_info["returns_points"] = returns
                    functions.append(function_info)
                
                elif isinstance(node, ast.ClassDef):
                    class_methods = []
                    for n in node.body:
                        if isinstance(n, ast.FunctionDef):
                            class_methods.append(n.name)
                    
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": node.end_lineno if hasattr(node, 'end_lineno') else None,
                        "bases": [
                            base.id if isinstance(base, ast.Name) else "complex_base" 
                            for base in node.bases
                        ],
                        "methods": class_methods,
                        "docstring": ast.get_docstring(node)
                    })
                
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.append({
                                "name": target.id,
                                "line": node.lineno,
                                "type": self._infer_variable_type(node.value)
                            })
                
                elif isinstance(node, ast.Call) and hasattr(node, 'lineno'):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                        func_name = f"{node.func.value.id}.{node.func.attr}"
                    
                    if func_name:
                        function_calls.append({
                            "name": func_name,
                            "line": node.lineno,
                            "args_count": len(node.args),
                            "keywords": [kw.arg for kw in node.keywords if kw.arg]
                        })
            
            # Find variable usage around the bug line
            bug_context_range = 15  # Look 15 lines around the bug
            line_start = max(1, bug_line - bug_context_range)
            line_end = bug_line + bug_context_range
            
            variables_in_context = []
            for var in variables:
                if line_start <= var["line"] <= line_end:
                    variables_in_context.append(var)
            
            # Find function calls around the bug line
            calls_in_context = []
            for call in function_calls:
                if line_start <= call["line"] <= line_end:
                    calls_in_context.append(call)
            
            # Add results to analysis
            python_analysis["ast_data"] = {
                "functions": functions,
                "classes": classes,
                "variables": variables,
                "function_calls": function_calls
            }
            
            python_analysis["variable_usage"] = {
                "context_variables": variables_in_context
            }
            
            python_analysis["function_calls"] = {
                "context_calls": calls_in_context
            }
            
            # Find the containing function or class
            containing_function = None
            for func in functions:
                if func["line"] <= bug_line and (func["end_line"] is None or func["end_line"] >= bug_line):
                    containing_function = func
                    break
            
            containing_class = None
            for cls in classes:
                if cls["line"] <= bug_line and (cls["end_line"] is None or cls["end_line"] >= bug_line):
                    containing_class = cls
                    break
            
            python_analysis["control_flow"] = {
                "containing_function": containing_function,
                "containing_class": containing_class
            }
            
            # Advanced data flow analysis
            python_analysis["data_flow"] = self._analyze_python_data_flow(tree, bug_line)
            
        except SyntaxError as e:
            # If AST parsing fails, fallback to simpler analysis
            python_analysis["parsing_error"] = f"AST parsing failed due to syntax errors: {str(e)}"
            
            # Attempt regex-based simpler analysis
            simple_analysis = self._analyze_python_with_regex(content, bug_line)
            python_analysis.update(simple_analysis)
        
        return python_analysis
    
    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract the name of a decorator."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_attribute_name(decorator)}"
        return "unknown_decorator"
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Recursively extract the full name of an attribute."""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return f"unknown.{node.attr}"
    
    def _get_return_annotation(self, node: ast.FunctionDef) -> str:
        """Extract the return type annotation from a function definition."""
        if isinstance(node.returns, ast.Name):
            return node.returns.id
        elif isinstance(node.returns, ast.Attribute):
            return self._get_attribute_name(node.returns)
        elif isinstance(node.returns, ast.Subscript):
            # Handle generic types like List[str]
            if isinstance(node.returns.value, ast.Name):
                return f"{node.returns.value.id}[...]"
            elif isinstance(node.returns.value, ast.Attribute):
                return f"{self._get_attribute_name(node.returns.value)}[...]"
        return "unknown"
    
    def _infer_variable_type(self, value_node: ast.expr) -> str:
        """Infer the type of a variable based on its assigned value."""
        if isinstance(value_node, ast.Num):
            return "int" if isinstance(value_node.n, int) else "float"
        elif isinstance(value_node, ast.Str):
            return "str"
        elif isinstance(value_node, ast.List):
            return "list"
        elif isinstance(value_node, ast.Dict):
            return "dict"
        elif isinstance(value_node, ast.Set):
            return "set"
        elif isinstance(value_node, ast.Tuple):
            return "tuple"
        elif isinstance(value_node, ast.NameConstant) and value_node.value is None:
            return "None"
        elif isinstance(value_node, ast.NameConstant):
            if value_node.value is True or value_node.value is False:
                return "bool"
        elif isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                return value_node.func.id
            elif isinstance(value_node.func, ast.Attribute):
                return self._get_attribute_name(value_node.func)
        return "unknown"
    
    def _analyze_python_data_flow(self, tree: ast.AST, bug_line: int) -> Dict[str, Any]:
        """
        Analyze Python data flow to understand variable dependencies.
        
        Args:
            tree: AST of the Python code
            bug_line: Line number of the bug
            
        Returns:
            Data flow analysis results
        """
        data_flow = {
            "variable_dependencies": {},
            "variable_mutations": [],
            "function_dependencies": {}
        }
        
        # Simple variable dependency tracking
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and hasattr(node, 'lineno'):
                # Skip nodes that are far from the bug line
                if abs(node.lineno - bug_line) > 30:
                    continue
                
                # Get the names being assigned to
                target_names = []
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        target_names.append(target.id)
                
                # Find dependencies in the right side
                dependencies = []
                for subnode in ast.walk(node.value):
                    if isinstance(subnode, ast.Name):
                        dependencies.append(subnode.id)
                
                # Record dependencies for each assigned variable
                for name in target_names:
                    data_flow["variable_dependencies"][name] = list(set(dependencies))
                    
                    # Record the assignment as a mutation
                    data_flow["variable_mutations"].append({
                        "variable": name,
                        "line": node.lineno,
                        "dependencies": list(set(dependencies))
                    })
        
        # Function call dependencies
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node, 'lineno'):
                # Skip nodes that are far from the bug line
                if abs(node.lineno - bug_line) > 30:
                    continue
                
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    func_name = f"{node.func.value.id}.{node.func.attr}"
                
                if func_name:
                    # Find variables used in arguments
                    arg_variables = []
                    for arg in node.args:
                        for subnode in ast.walk(arg):
                            if isinstance(subnode, ast.Name):
                                arg_variables.append(subnode.id)
                    
                    # Record function dependencies
                    data_flow["function_dependencies"][func_name] = {
                        "line": node.lineno,
                        "arg_variables": list(set(arg_variables))
                    }
        
        return data_flow
    
    def _analyze_python_with_regex(self, content: str, bug_line: int) -> Dict[str, Any]:
        """
        Analyze Python code using regex patterns when AST parsing fails.
        
        Args:
            content: Python file content
            bug_line: Line number of the bug
            
        Returns:
            Regex-based analysis results
        """
        regex_analysis = {
            "functions": [],
            "classes": [],
            "imports": []
        }
        
        lines = content.splitlines()
        
        # Find function definitions
        function_pattern = r'^\s*def\s+(\w+)\s*\((.*?)\):'
        for i, line in enumerate(lines, 1):
            match = re.match(function_pattern, line)
            if match:
                func_name = match.group(1)
                args_str = match.group(2).strip()
                args = [arg.strip().split('=')[0].strip() for arg in args_str.split(',') if arg.strip()]
                
                regex_analysis["functions"].append({
                    "name": func_name,
                    "line": i,
                    "args": args
                })
        
        # Find class definitions
        class_pattern = r'^\s*class\s+(\w+)(?:\((.*?)\))?:'
        for i, line in enumerate(lines, 1):
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(1)
                bases_str = match.group(2) or ""
                bases = [base.strip() for base in bases_str.split(',') if base.strip()]
                
                regex_analysis["classes"].append({
                    "name": class_name,
                    "line": i,
                    "bases": bases
                })
        
        # Find imports
        import_pattern = r'^\s*import\s+([\w\.]+)(?:\s+as\s+(\w+))?'
        from_import_pattern = r'^\s*from\s+([\w\.]+)\s+import\s+(.+)$'
        
        for i, line in enumerate(lines, 1):
            # Match 'import module' statements
            import_match = re.match(import_pattern, line)
            if import_match:
                module = import_match.group(1)
                alias = import_match.group(2) if import_match.group(2) else None
                
                regex_analysis["imports"].append({
                    "module": module,
                    "alias": alias,
                    "type": "import",
                    "line": i
                })
            
            # Match 'from module import names' statements
            from_match = re.match(from_import_pattern, line)
            if from_match:
                module = from_match.group(1)
                imported_items = [item.strip() for item in from_match.group(2).split(',')]
                
                regex_analysis["imports"].append({
                    "module": module,
                    "imported_items": imported_items,
                    "type": "from_import",
                    "line": i
                })
        
        return {"regex_analysis": regex_analysis}
    
    def _analyze_js_code(self, content: str, bug_line: int, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze JavaScript/TypeScript code for advanced code insights.
        
        Args:
            content: JavaScript file content
            bug_line: Line number of the bug
            strategy: The repair strategy
            
        Returns:
            JavaScript-specific analysis results
        """
        # JavaScript/TypeScript analysis placeholder
        # In a real implementation, this would use a JS parser like Esprima
        js_analysis = {
            "functions": [],
            "classes": [],
            "imports": [],
            "exports": []
        }
        
        lines = content.splitlines()
        
        # Find function declarations and expressions
        function_patterns = [
            r'function\s+(\w+)\s*\((.*?)\)', # function declarations
            r'(?:const|let|var)\s+(\w+)\s*=\s*function\s*\((.*?)\)', # function expressions
            r'(?:const|let|var)\s+(\w+)\s*=\s*\((.*?)\)\s*=>' # arrow functions
        ]
        
        for pattern in function_patterns:
            for i, line in enumerate(lines, 1):
                for match in re.finditer(pattern, line):
                    func_name = match.group(1)
                    args_str = match.group(2).strip()
                    args = [arg.strip().split('=')[0].strip() for arg in args_str.split(',') if arg.strip()]
                    
                    js_analysis["functions"].append({
                        "name": func_name,
                        "line": i,
                        "args": args
                    })
        
        # Find class declarations
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{'
        for i, line in enumerate(lines, 1):
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(1)
                parent_class = match.group(2) if match.group(2) else None
                
                js_analysis["classes"].append({
                    "name": class_name,
                    "line": i,
                    "extends": parent_class
                })
        
        # Find imports
        import_patterns = [
            r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]', # named imports
            r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]', # default imports
            r'(?:const|let|var)\s+(\w+)\s*=\s*require\([\'"]([^\'"]+)[\'"]\)' # CommonJS require
        ]
        
        for pattern in import_patterns:
            for i, line in enumerate(lines, 1):
                for match in re.finditer(pattern, line):
                    if '{' in pattern:  # named imports
                        imported_items = [item.strip() for item in match.group(1).split(',')]
                        module = match.group(2)
                        
                        js_analysis["imports"].append({
                            "type": "named_import",
                            "imported_items": imported_items,
                            "module": module,
                            "line": i
                        })
                    else:  # default import or require
                        name = match.group(1)
                        module = match.group(2)
                        
                        js_analysis["imports"].append({
                            "type": "default_import" if "import" in pattern else "require",
                            "name": name,
                            "module": module,
                            "line": i
                        })
        
            # Find exports
        export_patterns = [
            r'export\s+(?:default\s+)?(?:function|class)\s+(\w+)', # export function/class
            r'export\s+(?:const|let|var)\s+(\w+)', # export variable
            r'export\s+default\s+(\w+)' # export default
        ]
        
        return js_analysis
    
    def _analyze_java_code(self, content: str, bug_line: int, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze Java code for advanced code insights.
        
        Args:
            content: Java file content
            bug_line: Line number of the bug
            strategy: The repair strategy
            
        Returns:
            Java-specific analysis results
        """
        # Java analysis placeholder
        # In a real implementation, this would use a Java parser
        java_analysis = {
            "classes": [],
            "methods": [],
            "imports": []
        }
        
        return java_analysis
    
    def _generate_potential_fixes(self, bug_type: str, bug_code: str, language: str, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate potential fixes based on bug type and analysis.
        
        Args:
            bug_type: Type of bug
            bug_code: The buggy code line
            language: Programming language
            analysis_results: Results from code analysis
            
        Returns:
            List of potential fixes
        """
        potential_fixes = []
        
        if bug_type == "null_pointer":
            var_name = self._extract_variable_from_null_pointer(bug_code)
            
            if var_name:
                if language == "python":
                    potential_fixes.append({
                        "description": f"Add None check for {var_name}",
                        "code": f"if {var_name} is not None:",
                        "confidence": 0.9
                    })
                elif language == "java" or language == "javascript":
                    potential_fixes.append({
                        "description": f"Add null check for {var_name}",
                        "code": f"if ({var_name} != null) {{",
                        "confidence": 0.9
                    })
        
        elif bug_type == "resource_leak":
            resource_var = self._extract_variable_assignment(bug_code)
            
            if resource_var:
                if language == "python":
                    potential_fixes.append({
                        "description": f"Use 'with' statement for {resource_var}",
                        "code": f"with open(...) as {resource_var}:",
                        "confidence": 0.85
                    })
                elif language == "java":
                    potential_fixes.append({
                        "description": f"Use try-with-resources for {resource_var}",
                        "code": f"try (Resource {resource_var} = new Resource()) {{",
                        "confidence": 0.85
                    })
        
        elif bug_type == "sql_injection":
            if language == "python":
                potential_fixes.append({
                    "description": "Use parameterized query",
                    "code": "cursor.execute(query, params)",
                    "confidence": 0.9
                })
            elif language == "java":
                potential_fixes.append({
                    "description": "Use PreparedStatement",
                    "code": "PreparedStatement stmt = conn.prepareStatement(query);",
                    "confidence": 0.9
                })
        
        return potential_fixes
    
    def _generate_implementation_id(self, strategy: Dict[str, Any], implementation: Dict[str, Any]) -> str:
        """
        Generate a unique ID for the implementation.
        
        Args:
            strategy: The repair strategy
            implementation: The implementation details
            
        Returns:
            Unique implementation ID
        """
        # Create a hash of the strategy ID, bug location, and timestamp
        strategy_id = strategy.get("id", "unknown")
        bug_location = strategy.get("bug_location", "unknown")
        timestamp = implementation.get("timestamp", self._get_timestamp())
        
        # Create a string to hash
        hash_str = f"{strategy_id}:{bug_location}:{timestamp}"
        
        # Generate a hash
        hash_obj = hashlib.md5(hash_str.encode())
        hash_hex = hash_obj.hexdigest()
        
        return f"impl_{hash_hex[:12]}"
    
    def _calculate_confidence_level(self, implementation: Dict[str, Any]) -> float:
        """
        Calculate a confidence level for the implementation.
        
        Args:
            implementation: The implementation details
            
        Returns:
            Confidence level between 0 and 1
        """
        # Start with a base confidence
        base_confidence = 0.8
        
        # Adjust based on validation result
        validation_result = implementation.get("validation_result", {})
        if validation_result:
            if validation_result.get("success", False):
                base_confidence += 0.1
            else:
                base_confidence -= 0.3
        
        # Adjust based on patch complexity
        patches = implementation.get("patches", [])
        if len(patches) > 5:
            # More complex changes reduce confidence
            base_confidence -= 0.1
        
        # Clamp to [0.1, 0.95] range
        return max(0.1, min(0.95, base_confidence))
    
    def _calculate_patch_size(self, implementation: Dict[str, Any]) -> int:
        """
        Calculate the total size of all patches in the implementation.
        
        Args:
            implementation: The implementation details
            
        Returns:
            Size in bytes
        """
        total_size = 0
        
        for patch in implementation.get("patches", []):
            for change in patch.get("changes", []):
                content = change.get("content", "")
                if isinstance(content, str):
                    total_size += len(content.encode('utf-8'))
        
        return total_size
    
    def _validate_implementation(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an implementation before applying it.
        
        Args:
            implementation: The implementation to validate
            
        Returns:
            Validation result
        """
        # Initialize validation result
        validation_result = {
            "success": True,
            "validation_checks": [],
            "errors": []
        }
        
        # Syntax validation
        syntax_result = self._validate_syntax(implementation)
        validation_result["validation_checks"].append({
            "type": "syntax",
            "success": syntax_result["success"],
            "details": syntax_result
        })
        
        if not syntax_result["success"]:
            validation_result["success"] = False
            validation_result["errors"].extend(syntax_result.get("errors", []))
        
        # Patch consistency validation
        consistency_result = self._validate_patch_consistency(implementation)
        validation_result["validation_checks"].append({
            "type": "consistency",
            "success": consistency_result["success"],
            "details": consistency_result
        })
        
        if not consistency_result["success"]:
            validation_result["success"] = False
            validation_result["errors"].extend(consistency_result.get("errors", []))
        
        # Return the validation result
        return validation_result
    
    def _validate_syntax(self, implementation: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate the syntax of patches in the implementation.
        
        Args:
            implementation: The implementation to validate
            
        Returns:
            Validation result with success flag and any errors
        """
        result = {
            "success": True,
            "files_checked": [],
            "errors": []
        }
        
        for patch in implementation.get("patches", []):
            file_path = patch.get("file_path")
            changes = patch.get("changes", [])
            
            if not file_path or not os.path.isfile(file_path):
                result["errors"].append(f"File not found: {file_path}")
                result["success"] = False
                continue
            
            # Read the current file content
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # Apply changes in a temporary copy
            try:
                new_content = self._apply_patch_changes(current_content, changes)
                
                # Check syntax based on file type
                language = self._determine_language(file_path)
                
                if language == "python":
                    # Check Python syntax
                    try:
                        ast.parse(new_content)
                        result["files_checked"].append({
                            "file": file_path,
                            "success": True
                        })
                    except SyntaxError as e:
                        result["success"] = False
                        result["errors"].append(f"Python syntax error in {file_path}: {str(e)}")
                        result["files_checked"].append({
                            "file": file_path,
                            "success": False,
                            "error": str(e)
                        })
                
                # Add syntax checking for other languages as needed
                
            except Exception as e:
                result["success"] = False
                result["errors"].append(f"Error applying changes to {file_path}: {str(e)}")
        
        return result
    
    def _validate_patch_consistency(self, implementation: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate the consistency of patches across files.
        
        Args:
            implementation: The implementation to validate
            
        Returns:
            Validation result with success flag and any errors
        """
        result = {
            "success": True,
            "errors": [],
            "warnings": []
        }
        
        # Check for inconsistent changes
        file_paths = set()
        patches_by_file = {}
        
        for patch in implementation.get("patches", []):
            file_path = patch.get("file_path")
            if file_path:
                file_paths.add(file_path)
                # Group patches by file path
                if file_path in patches_by_file:
                    patches_by_file[file_path].append(patch)
                else:
                    patches_by_file[file_path] = [patch]
        
        # Look for duplicate file paths in patches
        for file_path, patches in patches_by_file.items():
            if len(patches) > 1:
                # Check for overlapping changes in the same file
                line_ranges = []
                for patch in patches:
                    for change in patch.get("changes", []):
                        change_type = change.get("type", "")
                        start_line = change.get("start_line", 0)
                        
                        if change_type == "replace_lines":
                            end_line = change.get("end_line", start_line)
                            line_ranges.append((start_line, end_line))
                        elif change_type == "insert_lines":
                            line_ranges.append((start_line, start_line))
                
                # Sort line ranges by start line
                line_ranges.sort()
                
                # Check for overlaps
                for i in range(len(line_ranges) - 1):
                    if line_ranges[i][1] >= line_ranges[i+1][0]:
                        result["success"] = False
                        result["errors"].append(
                            f"Overlapping changes in file {file_path} at lines {line_ranges[i]} and {line_ranges[i+1]}"
                        )
        
        # Check if all files actually exist
        for file_path in file_paths:
            if not file_path or not os.path.isfile(file_path):
                result["success"] = False
                result["errors"].append(f"File not found: {file_path}")
        
        return result
    
    def apply_implementation(
        self,
        implementation: Dict[str, Any],
        dry_run: bool = False,
        progressive: bool = None,
        validate_after_each_file: bool = None
    ) -> Dict[str, Any]:
        """
        Apply the implementation to the actual code files with backup and validation.
        
        Args:
            implementation: The implementation details including patches
            dry_run: If True, don't actually modify files (default: False)
            progressive: If True, apply patches progressively and validate after each (default: self.progressive_patching)
            validate_after_each_file: If True, validate after each file modification (default: self.validate_patches)
            
        Returns:
            Result of the application
        """
        logger.info(f"Applying implementation, dry_run={dry_run}")
        implementation_id = implementation.get("implementation_id", self._generate_implementation_id(
            {"id": implementation.get("strategy_id", "unknown")}, implementation
        ))
        
        # Set defaults from agent configuration if not provided
        if progressive is None:
            progressive = self.progressive_patching
        
        if validate_after_each_file is None:
            validate_after_each_file = self.validate_patches
        
        # Prepare the result dictionary
        result = {
            "implementation_id": implementation_id,
            "status": "no_changes",
            "message": "No patches to apply",
            "files_modified": [],
            "files_failed": [],
            "dry_run": dry_run,
            "backups_created": [],
            "validation_results": []
        }
        
        patches = implementation.get("patches", [])
        if not patches:
            return result
        
        # Validate implementation before applying
        if self.validate_patches and not dry_run:
            validation_result = self._validate_implementation(implementation)
            result["validation_results"].append(validation_result)
            
            if not validation_result.get("success", False):
                result["status"] = "validation_failed"
                result["message"] = f"Implementation validation failed: {validation_result.get('errors', [])}"
                return result
        
        # Sort patches by file path and then by line number
        sorted_patches = sorted(
            patches, 
            key=lambda p: (p.get("file_path", ""), min(c.get("start_line", 0) for c in p.get("changes", []) if c))
        )
        
        # Prepare backup directory for this implementation
        backup_dir = os.path.join(self.backup_dir, implementation_id)
        if self.backup_files and not dry_run:
            os.makedirs(backup_dir, exist_ok=True)
        
        # Track original content for potential rollback
        original_contents = {}
        
        # Apply patches progressively if requested
        for patch_index, patch in enumerate(sorted_patches):
            file_path = patch.get("file_path")
            changes = patch.get("changes", [])
            
            if not file_path or not os.path.isfile(file_path):
                result["files_failed"].append({
                    "file_path": file_path,
                    "reason": "File not found"
                })
                continue
            
            try:
                # Read the current file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()
                
                # Store original content for potential rollback
                original_contents[file_path] = current_content
                
                # Create backup if needed
                if not dry_run and self.backup_files:
                    # Create a backup in the backup directory
                    backup_filename = os.path.basename(file_path)
                    backup_path = os.path.join(backup_dir, f"{backup_filename}.bak")
                    
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(current_content)
                    
                    result["backups_created"].append({
                        "original_file": file_path,
                        "backup_path": backup_path
                    })
                
                # Apply changes to get new content
                new_content = self._apply_patch_changes(current_content, changes)
                
                # Write the modified content
                if not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    result["files_modified"].append({
                        "file_path": file_path,
                        "changes_applied": len(changes)
                    })
                    
                    # Validate after each file if progressive validation is enabled
                    if validate_after_each_file:
                        # Check syntax of the modified file
                        file_validation = self._validate_file_syntax(file_path)
                        result["validation_results"].append({
                            "file": file_path,
                            "success": file_validation["success"],
                            "details": file_validation
                        })
                        
                        # If validation failed and not in dry run mode, rollback this file
                        if not file_validation["success"]:
                            logger.warning(f"Validation failed for {file_path}, rolling back")
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(original_contents[file_path])
                            
                            result["files_failed"].append({
                                "file_path": file_path,
                                "reason": f"Validation failed: {file_validation.get('errors', [])}"
                            })
                            
                            # Remove from modified files
                            result["files_modified"] = [f for f in result["files_modified"] if f["file_path"] != file_path]
                
                # If using progressive application, validate after each patch
                if progressive and not dry_run and patch_index < len(sorted_patches) - 1:
                    # Validate the current state of the implementation
                    progressive_validation = self._validate_implementation(implementation)
                    result["validation_results"].append(progressive_validation)
                    
                    if not progressive_validation.get("success", False):
                        logger.warning(f"Progressive validation failed after patch {patch_index + 1}/{len(sorted_patches)}")
                        # We'll continue with the next patch, but record the failure
                        result["warnings"] = result.get("warnings", []) + [
                            f"Progressive validation failed after patch {patch_index + 1}/{len(sorted_patches)}"
                        ]
            
            except Exception as e:
                logger.error(f"Error applying changes to {file_path}: {str(e)}")
                result["files_failed"].append({
                    "file_path": file_path,
                    "reason": str(e)
                })
                
                # Rollback this file if not in dry run mode
                if not dry_run and file_path in original_contents:
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(original_contents[file_path])
                        logger.info(f"Rolled back changes to {file_path} due to error")
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback changes to {file_path}: {str(rollback_error)}")
                        result["errors"] = result.get("errors", []) + [
                            f"Failed to rollback changes to {file_path}: {str(rollback_error)}"
                        ]
        
        # Determine final status
        if not result["files_failed"] and result["files_modified"]:
            result["status"] = "success"
            result["message"] = f"Modified {len(result['files_modified'])} files successfully"
            
            # Record successful implementation
            if not dry_run:
                self.successful_implementations[implementation_id] = {
                    "implementation": implementation,
                    "result": result,
                    "timestamp": self._get_timestamp(),
                    "verified": False
                }
        elif result["files_modified"] and result["files_failed"]:
            result["status"] = "partial_success"
            result["message"] = f"Modified {len(result['files_modified'])} files, {len(result['files_failed'])} failed"
        else:
            result["status"] = "failed"
            result["message"] = f"Failed to modify any files, {len(result['files_failed'])} failures"
        
        return result
    
    def rollback_implementation(self, implementation_id: str) -> Dict[str, Any]:
        """
        Rollback an implementation using backups.
        
        Args:
            implementation_id: The ID of the implementation to rollback
            
        Returns:
            Result of the rollback operation
        """
        logger.info(f"Rolling back implementation: {implementation_id}")
        
        # Initialize result
        result = {
            "implementation_id": implementation_id,
            "status": "not_found",
            "message": f"Implementation {implementation_id} not found",
            "files_restored": [],
            "files_failed": []
        }
        
        # Find the implementation
        implementation_record = self.successful_implementations.get(implementation_id)
        if not implementation_record:
            return result
        
        # Get the implementation result which contains backup information
        implementation_result = implementation_record.get("result", {})
        backups = implementation_result.get("backups_created", [])
        
        if not backups:
            result["status"] = "no_backups"
            result["message"] = f"No backups found for implementation {implementation_id}"
            return result
        
        # Restore from backups
        for backup in backups:
            original_file = backup.get("original_file")
            backup_path = backup.get("backup_path")
            
            if not original_file or not backup_path or not os.path.isfile(backup_path):
                result["files_failed"].append({
                    "file_path": original_file,
                    "backup_path": backup_path,
                    "reason": "Backup file not found"
                })
                continue
            
            try:
                # Read backup content
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                
                # Restore original file
                with open(original_file, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
                
                result["files_restored"].append({
                    "file_path": original_file,
                    "backup_path": backup_path
                })
            
            except Exception as e:
                logger.error(f"Error restoring {original_file} from {backup_path}: {str(e)}")
                result["files_failed"].append({
                    "file_path": original_file,
                    "backup_path": backup_path,
                    "reason": str(e)
                })
        
        # Determine final status
        if not result["files_failed"] and result["files_restored"]:
            result["status"] = "success"
            result["message"] = f"Restored {len(result['files_restored'])} files successfully"
            
            # Record rollback
            self.metrics.record_rollback()
            self.rollback_history[implementation_id] = {
                "rollback_result": result,
                "timestamp": self._get_timestamp()
            }
            
            # Remove from successful implementations
            self.successful_implementations.pop(implementation_id, None)
            
        elif result["files_restored"] and result["files_failed"]:
            result["status"] = "partial_success"
            result["message"] = f"Restored {len(result['files_restored'])} files, {len(result['files_failed'])} failed"
        else:
            result["status"] = "failed"
            result["message"] = f"Failed to restore any files, {len(result['files_failed'])} failures"
        
        return result
    
    def _validate_file_syntax(self, file_path: str) -> Dict[str, Any]:
        """
        Validate the syntax of a single file.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Validation result
        """
        result = {
            "success": True,
            "file": file_path,
            "errors": []
        }
        
        if not os.path.isfile(file_path):
            result["success"] = False
            result["errors"].append(f"File not found: {file_path}")
            return result
        
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check syntax based on file type
            language = self._determine_language(file_path)
            
            if language == "python":
                # Check Python syntax
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    result["success"] = False
                    result["errors"].append(f"Python syntax error: {str(e)}")
            
            # Add syntax checking for other languages as needed
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"Error reading or parsing file: {str(e)}")
        
        return result
    
    def get_implementation_status(
        self,
        implementation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific implementation.
        
        Args:
            implementation_id: The ID of the implementation
            
        Returns:
            The implementation status or None if not found
        """
        return self.successful_implementations.get(implementation_id)
    
    def _load_affected_files(self, strategy: Dict[str, Any]) -> Dict[str, str]:
        """
        Load the content of all affected files in the strategy.
        
        Args:
            strategy: The repair strategy
            
        Returns:
            Dictionary mapping file paths to their content
        """
        file_content_map = {}
        
        # Always include the bug location file
        bug_location = strategy.get("bug_location")
        if bug_location and os.path.isfile(bug_location):
            try:
                with open(bug_location, 'r', encoding='utf-8') as f:
                    file_content_map[bug_location] = f.read()
            except Exception as e:
                logger.error(f"Error reading file {bug_location}: {e}")
        
        # Include other affected files
        affected_files = strategy.get("affected_files", [])
        for file_path in affected_files:
            if file_path != bug_location and os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content_map[file_path] = f.read()
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
        
        return file_content_map
    
    def _get_implementation_function(self, bug_type: str):
        """
        Get the appropriate implementation function for the bug type.
        
        Args:
            bug_type: The type of bug
            
        Returns:
            Function to implement the fix for this bug type
        """
        # Map bug types to implementation functions
        implementation_map = {
            "null_pointer": self._implement_null_pointer_fix,
            "resource_leak": self._implement_resource_leak_fix,
            "sql_injection": self._implement_sql_injection_fix,
            "hardcoded_credentials": self._implement_hardcoded_credentials_fix,
            "exception_swallowing": self._implement_exception_swallowing_fix
        }
        
        # Return the specific implementation function or default to generic
        return implementation_map.get(bug_type, self._implement_generic_fix)
    
    def _implement_null_pointer_fix(
        self,
        strategy: Dict[str, Any],
        file_content_map: Dict[str, str],
        additional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implement a fix for null pointer bugs.
        
        Args:
            strategy: The repair strategy
            file_content_map: Map of file paths to content
            additional_context: Additional context for implementation
            
        Returns:
            Implementation details
        """
        bug_location = strategy.get("bug_location")
        bug_line = strategy.get("bug_line", 0)
        bug_code = strategy.get("bug_code", "")
        file_content = file_content_map.get(bug_location, "")
        
        # If no content found, return empty implementation
        if not file_content:
            return self._create_empty_implementation(strategy, "File content not available")
        
        # Parse the file to find the buggy code
        lines = file_content.splitlines()
        
        # Check if the bug line number is valid
        if bug_line <= 0 or bug_line > len(lines):
            return self._create_empty_implementation(strategy, "Invalid line number")
        
        # Extract variable names involved in the null pointer dereference
        var_name = self._extract_variable_from_null_pointer(bug_code)
        
        if not var_name:
            return self._create_empty_implementation(strategy, "Unable to identify variable name")
        
        # Generate patches
        patches = []
        
        # Find the context around the bug
        context_start = max(0, bug_line - 10)
        context_end = min(len(lines), bug_line + 10)
        
        # Find the function or method containing the bug
        function_info = self._find_containing_function(
            file_content, bug_line, parse=True)
        
        if function_info:
            function_name = function_info.get("name", "unknown_function")
            function_start = function_info.get("start_line", bug_line)
            function_end = function_info.get("end_line", bug_line + 5)
            
            # Create a patch for the function
            changes = []
            
            # Create changes for null check before variable access
            original_line = lines[bug_line - 1]
            indentation = re.match(r'^(\s*)', original_line).group(1)
            
            # Determine language (default to Python)
            language = self._determine_language(bug_location)
            
            if language == "python":
                # Python implementation
                null_check_code = f"{indentation}if {var_name} is not None:\n"
                null_check_code += f"{indentation}    {original_line.strip()}\n"
                null_check_code += f"{indentation}else:\n"
                null_check_code += f"{indentation}    # Handle None case\n"
                null_check_code += f"{indentation}    return None  # Or appropriate default value"
                
                changes.append({
                    "type": "replace_lines",
                    "start_line": bug_line,
                    "end_line": bug_line,
                    "content": null_check_code
                })
            elif language == "java" or language == "javascript":
                # Java/JavaScript implementation
                null_check_code = f"{indentation}if ({var_name} != null) {{\n"
                null_check_code += f"{indentation}    {original_line.strip()}\n"
                null_check_code += f"{indentation}}} else {{\n"
                null_check_code += f"{indentation}    // Handle null case\n"
                null_check_code += f"{indentation}    return null;  // Or appropriate default value\n"
                null_check_code += f"{indentation}}}"
                
                changes.append({
                    "type": "replace_lines",
                    "start_line": bug_line,
                    "end_line": bug_line,
                    "content": null_check_code
                })
            
            patches.append({
                "file_path": bug_location,
                "changes": changes,
                "function": function_name
            })
        
        # Create implementation details
        implementation = {
            "patches": patches,
            "language": self._determine_language(bug_location),
            "description": f"Added null check for variable '{var_name}' before accessing its properties",
            "approach": "Defensive programming with null/None check",
            "risk_level": "low"
        }
        
        return implementation
    
    def _implement_resource_leak_fix(
        self,
        strategy: Dict[str, Any],
        file_content_map: Dict[str, str],
        additional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implement a fix for resource leak bugs.
        
        Args:
            strategy: The repair strategy
            file_content_map: Map of file paths to content
            additional_context: Additional context for implementation
            
        Returns:
            Implementation details
        """
        bug_location = strategy.get("bug_location")
        bug_line = strategy.get("bug_line", 0)
        bug_code = strategy.get("bug_code", "")
        file_content = file_content_map.get(bug_location, "")
        
        # If no content found, return empty implementation
        if not file_content:
            return self._create_empty_implementation(strategy, "File content not available")
        
        # Parse the file to find the buggy code
        lines = file_content.splitlines()
        
        # Check if the bug line number is valid
        if bug_line <= 0 or bug_line > len(lines):
            return self._create_empty_implementation(strategy, "Invalid line number")
        
        # Extract resource name from the line (e.g., the file variable)
        resource_var = self._extract_variable_assignment(bug_code)
        
        if not resource_var:
            return self._create_empty_implementation(strategy, "Unable to identify resource variable")
        
        # Determine language
        language = self._determine_language(bug_location)
        
        # Find the function containing the resource usage
        function_info = self._find_containing_function(
            file_content, bug_line, parse=True)
        
        if not function_info:
            return self._create_empty_implementation(strategy, "Unable to find containing function")
        
        function_name = function_info.get("name", "unknown_function")
        function_start = function_info.get("start_line", bug_line)
        function_end = function_info.get("end_line", bug_line + 20)
        function_lines = lines[function_start - 1:function_end]
        
        # Determine the resource type and operation
        resource_type = ""
        resource_op = ""
        
        if "open(" in bug_code:
            resource_type = "file"
            resource_op = "open"
        
        # Generate patches based on language and resource type
        patches = []
        changes = []
        
        if language == "python" and resource_type == "file":
            # In Python, we'll use 'with' statement for file resources
            original_code_block = self._extract_resource_usage_block(
                function_lines, resource_var)
            
            # Get indentation from the original line
            original_line = lines[bug_line - 1]
            indentation = re.match(r'^(\s*)', original_line).group(1)
            
            # Extract parameters from the open call
            open_params = self._extract_function_params(bug_code, "open")
            
            if len(open_params) >= 2:
                filename, mode = open_params[:2]
                
                # Create with statement
                with_statement = f"{indentation}with open({filename}, {mode}) as {resource_var}:\n"
                
                # Identify all the lines using the resource and indent them
                usage_lines = []
                for i, line in enumerate(function_lines):
                    if resource_var in line and i > (bug_line - function_start):
                        # Skip the line with resource declaration
                        if not line.strip().startswith(f"{resource_var} = open("):
                            usage_lines.append(f"{indentation}    {line.strip()}")
                
                # If we found usage lines, add them to the with statement
                if usage_lines:
                    with_statement += "\n".join(usage_lines)
                else:
                    # No usage found, add a placeholder
                    with_statement += f"{indentation}    # Use the {resource_var} here\n"
                    with_statement += f"{indentation}    pass"
                
                # Create the changes
                changes.append({
                    "type": "replace_lines",
                    "start_line": bug_line,
                    "end_line": bug_line + len(original_code_block) - 1,
                    "content": with_statement
                })
        
        # If changes were generated, add them to patches
        if changes:
            patches.append({
                "file_path": bug_location,
                "changes": changes,
                "function": function_name
            })
        
        # Create implementation details
        implementation = {
            "patches": patches,
            "language": language,
            "description": f"Fixed resource leak by using appropriate resource management pattern for {resource_var}",
            "approach": "Context manager for resource management",
            "risk_level": "low"
        }
        
        return implementation
    
    def _implement_sql_injection_fix(
        self,
        strategy: Dict[str, Any],
        file_content_map: Dict[str, str],
        additional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implement a fix for SQL injection bugs.
        
        Args:
            strategy: The repair strategy
            file_content_map: Map of file paths to content
            additional_context: Additional context for implementation
            
        Returns:
            Implementation details
        """
        bug_location = strategy.get("bug_location")
        bug_line = strategy.get("bug_line", 0)
        bug_code = strategy.get("bug_code", "")
        file_content = file_content_map.get(bug_location, "")
        
        # If no content found, return empty implementation
        if not file_content:
            return self._create_empty_implementation(strategy, "File content not available")
        
        # Parse the file to find the buggy code
        lines = file_content.splitlines()
        
        # Check if the bug line number is valid
        if bug_line <= 0 or bug_line > len(lines):
            return self._create_empty_implementation(strategy, "Invalid line number")
        
        # Find the query and the concatenated variables
        query_info = self._extract_sql_query_info(bug_code)
        
        if not query_info:
            return self._create_empty_implementation(strategy, "Unable to identify SQL query")
        
        # Determine language
        language = self._determine_language(bug_location)
        
        # Find the function containing the SQL query
        function_info = self._find_containing_function(
            file_content, bug_line, parse=True)
        
        if not function_info:
            return self._create_empty_implementation(strategy, "Unable to find containing function")
        
        function_name = function_info.get("name", "unknown_function")
        
        # Generate patches based on language
        patches = []
        changes = []
        
        if language == "python":
            # In Python, we'll use parameterized queries
            query_var = query_info.get("query_var", "")
            query_string = query_info.get("query_string", "")
            params = query_info.get("parameters", [])
            
            if query_string and params:
                # Get indentation from the original line
                original_line = lines[bug_line - 1]
                indentation = re.match(r'^(\s*)', original_line).group(1)
                
                # Replace string concatenation with parameter placeholders
                new_query_string = query_string
                for param in params:
                    # Replace with %s or ? placeholder (depends on DB library)
                    new_query_string = new_query_string.replace(f"+ {param} +", ", %s, ")
                    new_query_string = new_query_string.replace(f"+ {param}", ", %s")
                    new_query_string = new_query_string.replace(f"{param} +", "%s, ")
                
                # Clean up any duplicate commas
                new_query_string = re.sub(r',\s*,', ',', new_query_string)
                
                # Create new parameterized query
                if query_var:
                    new_line = f"{indentation}{query_var} = {new_query_string}"
                else:
                    new_line = f"{indentation}{new_query_string}"
                
                # Create parameter tuple line
                params_line = f"{indentation}params = ({', '.join(params)})"
                
                # Find and update the execute line
                execute_line = None
                for i, line in enumerate(lines[bug_line:bug_line + 10]):
                    if "execute(" in line and query_var in line:
                        execute_line = bug_line + i
                        break
                
                changes.append({
                    "type": "replace_lines",
                    "start_line": bug_line,
                    "end_line": bug_line,
                    "content": f"{new_line}\n{params_line}"
                })
                
                if execute_line:
                    original_execute = lines[execute_line - 1]
                    indentation = re.match(r'^(\s*)', original_execute).group(1)
                    
                    # Update execute to use params
                    if "execute(" in original_execute:
                        new_execute = original_execute.replace(f"execute({query_var})", f"execute({query_var}, params)")
                        
                        changes.append({
                            "type": "replace_lines",
                            "start_line": execute_line,
                            "end_line": execute_line,
                            "content": new_execute
                        })
        
        # If changes were generated, add them to patches
        if changes:
            patches.append({
                "file_path": bug_location,
                "changes": changes,
                "function": function_name
            })
        
        # Create implementation details
        implementation = {
            "patches": patches,
            "language": language,
            "description": "Fixed SQL injection vulnerability by using parameterized queries",
            "approach": "Parameterized queries for SQL injection prevention",
            "risk_level": "medium"
        }
        
        return implementation
    
    def _implement_hardcoded_credentials_fix(
        self,
        strategy: Dict[str, Any],
        file_content_map: Dict[str, str],
        additional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implement a fix for hardcoded credentials bugs.
        
        Args:
            strategy: The repair strategy
            file_content_map: Map of file paths to content
            additional_context: Additional context for implementation
            
        Returns:
            Implementation details
        """
        bug_location = strategy.get("bug_location")
        bug_line = strategy.get("bug_line", 0)
        bug_code = strategy.get("bug_code", "")
        file_content = file_content_map.get(bug_location, "")
        
        # If no content found, return empty implementation
        if not file_content:
            return self._create_empty_implementation(strategy, "File content not available")
        
        # Parse the file to find the buggy code
        lines = file_content.splitlines()
        
        # Check if the bug line number is valid
        if bug_line <= 0 or bug_line > len(lines):
            return self._create_empty_implementation(strategy, "Invalid line number")
        
        # Extract credential variable name and value
        cred_info = self._extract_credential_info(bug_code)
        
        if not cred_info:
            return self._create_empty_implementation(strategy, "Unable to identify credential information")
        
        # Determine language
        language = self._determine_language(bug_location)
        
        # Find the function containing the hardcoded credentials
        function_info = self._find_containing_function(
            file_content, bug_line, parse=True)
        
        function_name = function_info.get("name", "unknown_function") if function_info else "unknown_function"
        
        # Generate patches based on language
        patches = []
        changes = []
        imports_changes = []
        
        if language == "python":
            # In Python, we'll use environment variables
            var_name = cred_info.get("variable", "")
            var_type = cred_info.get("type", "")
            
            if var_name:
                # Get indentation from the original line
                original_line = lines[bug_line - 1]
                indentation = re.match(r'^(\s*)', original_line).group(1)
                
                # Create environment variable name
                env_var_name = f"{var_name.upper()}"
                
                # Add import for os module if not already imported
                if "import os" not in file_content and "from os import" not in file_content:
                    imports_changes.append({
                        "type": "insert_lines",
                        "start_line": 1,
                        "content": "import os"
                    })
                
                # Create new line using environment variable
                new_line = f"{indentation}{var_name} = os.environ.get('{env_var_name}')"
                
                # Add a fallback if needed
                if var_type == "password":
                    new_line += f" or '' # TODO: Remove fallback in production"
                
                changes.append({
                    "type": "replace_lines",
                    "start_line": bug_line,
                    "end_line": bug_line,
                    "content": new_line
                })
                
                # Add a comment about setting the environment variable
                env_comment = (
                    f"{indentation}# NOTE: Set the {env_var_name} environment variable before running\n"
                    f"{indentation}# e.g., export {env_var_name}=your_secret_value"
                )
                
                changes.append({
                    "type": "insert_lines",
                    "start_line": bug_line,
                    "content": env_comment
                })
        
        # If imports_changes were generated, add them to patches
        if imports_changes:
            patches.append({
                "file_path": bug_location,
                "changes": imports_changes,
                "description": "Added necessary imports for environment variables"
            })
        
        # If changes were generated, add them to patches
        if changes:
            patches.append({
                "file_path": bug_location,
                "changes": changes,
                "function": function_name
            })
        
        # Create implementation details
        implementation = {
            "patches": patches,
            "language": language,
            "description": "Replaced hardcoded credentials with environment variables",
            "approach": "Environment variables for secure credential management",
            "risk_level": "medium",
            "additional_steps": [
                "Set up environment variables on the target system",
                "Consider using a secure vault for production environments",
                "Update documentation with information about required environment variables"
            ]
        }
        
        return implementation
    
    def _implement_exception_swallowing_fix(
        self,
        strategy: Dict[str, Any],
        file_content_map: Dict[str, str],
        additional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implement a fix for exception swallowing bugs.
        
        Args:
            strategy: The repair strategy
            file_content_map: Map of file paths to content
            additional_context: Additional context for implementation
            
        Returns:
            Implementation details
        """
        bug_location = strategy.get("bug_location")
        bug_line = strategy.get("bug_line", 0)
        bug_code = strategy.get("bug_code", "")
        file_content = file_content_map.get(bug_location, "")
        
        # If no content found, return empty implementation
        if not file_content:
            return self._create_empty_implementation(strategy, "File content not available")
        
        # Parse the file to find the buggy code
        lines = file_content.splitlines()
        
        # Check if the bug line number is valid
        if bug_line <= 0 or bug_line > len(lines):
            return self._create_empty_implementation(strategy, "Invalid line number")
        
        # Determine language
        language = self._determine_language(bug_location)
        
        # Find the try-except block
        except_block = self._find_except_block(lines, bug_line)
        
        if not except_block:
            return self._create_empty_implementation(strategy, "Unable to find except block")
        
        # Find the function containing the try-except
        function_info = self._find_containing_function(
            file_content, bug_line, parse=True)
        
        function_name = function_info.get("name", "unknown_function") if function_info else "unknown_function"
        
        # Generate patches based on language
        patches = []
        changes = []
        imports_changes = []
        
        if language == "python":
            # Find the exception type
            exception_type = self._extract_exception_type(bug_code)
            
            # Get the line where the except block starts
            except_start = except_block.get("start_line")
            except_end = except_block.get("end_line")
            
            # Get indentation
            original_line = lines[except_start - 1]
            indentation = re.match(r'^(\s*)', original_line).group(1)
            
            # Check if logging is already imported
            if "import logging" not in file_content and "from logging import" not in file_content:
                imports_changes.append({
                    "type": "insert_lines",
                    "start_line": 1,
                    "content": "import logging"
                })
            
            # Determine the except block's content
            except_content = lines[except_start:except_end + 1]
            
            # Create new except block with proper logging
            if exception_type == "Exception":
                variable_name = "e"
                new_except_content = f"{indentation}except {exception_type} as {variable_name}:\n"
                new_except_content += f"{indentation}    # Log the exception\n"
                new_except_content += f"{indentation}    logging.error(f\"Error during operation: {{{variable_name}}}\")\n"
                new_except_content += f"{indentation}    # Consider re-raising or proper handling\n"
                new_except_content += f"{indentation}    return None  # Or appropriate error value"
            else:
                # Handle specific exception types
                variable_name = "e"
                new_except_content = f"{indentation}except {exception_type} as {variable_name}:\n"
                new_except_content += f"{indentation}    # Log the specific exception\n"
                new_except_content += f"{indentation}    logging.error(f\"Error during operation: {{{variable_name}}}\")\n"
                new_except_content += f"{indentation}    # Handle this specific error case\n"
                new_except_content += f"{indentation}    return None  # Or appropriate error value"
            
            changes.append({
                "type": "replace_lines",
                "start_line": except_start,
                "end_line": except_end,
                "content": new_except_content
            })
        
        # If imports_changes were generated, add them to patches
        if imports_changes:
            patches.append({
                "file_path": bug_location,
                "changes": imports_changes,
                "description": "Added necessary imports for exception handling"
            })
        
        # If changes were generated, add them to patches
        if changes:
            patches.append({
                "file_path": bug_location,
                "changes": changes,
                "function": function_name
            })
        
        # Create implementation details
        implementation = {
            "patches": patches,
            "language": language,
            "description": "Fixed exception swallowing by adding proper logging and error handling",
            "approach": "Robust exception handling with logging",
            "risk_level": "low"
        }
        
        return implementation
    
    def _implement_generic_fix(
        self,
        strategy: Dict[str, Any],
        file_content_map: Dict[str, str],
        additional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implement a generic fix for bugs that don't have a specific implementation.
        
        Args:
            strategy: The repair strategy
            file_content_map: Map of file paths to content
            additional_context: Additional context for implementation
            
        Returns:
            Implementation details
        """
        bug_location = strategy.get("bug_location")
        bug_line = strategy.get("bug_line", 0)
        bug_code = strategy.get("bug_code", "")
        file_content = file_content_map.get(bug_location, "")
        
        # If no content found, return empty implementation
        if not file_content:
            return self._create_empty_implementation(strategy, "File content not available")
        
        # Parse the file to find the buggy code
        lines = file_content.splitlines()
        
        # Check if the bug line number is valid
        if bug_line <= 0 or bug_line > len(lines):
            return self._create_empty_implementation(strategy, "Invalid line number")
        
        # Find the function or method containing the bug
        function_info = self._find_containing_function(
            file_content, bug_line, parse=True)
        
        function_name = function_info.get("name", "unknown_function") if function_info else "unknown_function"
        
        # Generate a generic comment explaining the issue
        original_line = lines[bug_line - 1]
        indentation = re.match(r'^(\s*)', original_line).group(1)
        
        # Create a comment to explain the issue
        comment = f"{indentation}# FIXME: Potential bug: {strategy.get('description', 'Unknown issue')}\n"
        
        # Generate patches
        patches = []
        changes = [{
            "type": "insert_lines",
            "start_line": bug_line,
            "content": comment
        }]
        
        patches.append({
            "file_path": bug_location,
            "changes": changes,
            "function": function_name
        })
        
        # Create implementation details
        implementation = {
            "patches": patches,
            "language": self._determine_language(bug_location),
            "description": "Added a comment to highlight the potential issue",
            "approach": "Manual review required",
            "risk_level": "medium",
            "additional_steps": [
                "Review the highlighted code manually",
                "Implement a proper fix based on the strategy's suggestions"
            ]
        }
        
        return implementation
    
    def _extract_variable_from_null_pointer(self, code: str) -> Optional[str]:
        """
        Extract the variable name involved in a null pointer dereference.
        
        Args:
            code: The code line with the null pointer dereference
            
        Returns:
            The variable name or None if not found
        """
        # Simple pattern matching to extract variable name
        # This is a basic implementation - in practice would need more sophisticated parsing
        
        # Pattern: variable.property
        property_access_match = re.search(r'(\w+)\.\w+', code)
        if property_access_match:
            return property_access_match.group(1)
        
        # Pattern: variable.method()
        method_call_match = re.search(r'(\w+)\.\w+\(', code)
        if method_call_match:
            return method_call_match.group(1)
        
        # Pattern: variable['key']
        dictionary_access_match = re.search(r'(\w+)\[', code)
        if dictionary_access_match:
            return dictionary_access_match.group(1)
        
        return None
    
    def _determine_language(self, file_path: str) -> str:
        """
        Determine the programming language based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            The programming language (python, java, javascript, etc.)
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        language_map = {
            '.py': 'python',
            '.java': 'java',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.rb': 'ruby',
            '.go': 'go',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php'
        }
        
        return language_map.get(extension, 'unknown')
    
    def _find_containing_function(
        self,
        file_content: str,
        line_number: int,
        parse: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Find the function or method containing the specified line.
        
        Args:
            file_content: The content of the file
            line_number: The line number to look for
            parse: Whether to use AST parsing (True) or simple heuristics (False)
            
        Returns:
            A dictionary with function information or None if not found
        """
        if not file_content or line_number <= 0:
            return None
        
        # If using AST parsing and it's a Python file
        if parse:
            try:
                tree = ast.parse(file_content)
                
                # Find all function definitions
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        start_line = node.lineno
                        # Find the last line of the function
                        end_line = 0
                        for child in ast.walk(node):
                            if hasattr(child, 'lineno'):
                                end_line = max(end_line, child.lineno)
                        
                        # If the line is within the function
                        if start_line <= line_number <= end_line:
                            return {
                                "name": node.name,
                                "start_line": start_line,
                                "end_line": end_line,
                                "type": node.__class__.__name__
                            }
            except SyntaxError:
                # If AST parsing fails, fall back to heuristics
                pass
        
        # Fall back to simple heuristics
        lines = file_content.splitlines()
        
        # Look for function definition patterns
        function_start_pattern = re.compile(r'^\s*(def|function|class|public|private|protected)\s+(\w+)')
        block_start_pattern = re.compile(r'[{:]$')
        
        # Find the function containing the line
        current_function = None
        current_start = 0
        indentation_level = None
        
        for i, line in enumerate(lines, 1):
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check for function definition
            match = function_start_pattern.match(line)
            if match and block_start_pattern.search(line):
                current_function = match.group(2)
                current_start = i
                indentation_level = len(line) - len(line.lstrip())
            
            # If we've found a function and reached our target line
            if current_function and i >= line_number:
                # Estimate the end of the function based on indentation
                for j, end_line in enumerate(lines[i:], i):
                    if end_line.strip() and len(end_line) - len(end_line.lstrip()) <= indentation_level:
                        return {
                            "name": current_function,
                            "start_line": current_start,
                            "end_line": j - 1,
                            "type": "function"
                        }
                
                # If we reached the end of the file
                return {
                    "name": current_function,
                    "start_line": current_start,
                    "end_line": len(lines),
                    "type": "function"
                }
        
        return None
    
    def _extract_resource_usage_block(
        self,
        function_lines: List[str],
        resource_var: str
    ) -> List[str]:
        """
        Extract the block of code that uses a resource variable.
        
        Args:
            function_lines: Lines of the function containing the resource
            resource_var: The name of the resource variable
            
        Returns:
            Lines of code that use the resource variable
        """
        usage_block = []
        in_usage_block = False
        resource_declaration_pattern = re.compile(rf'{resource_var}\s*=')
        
        for line in function_lines:
            # Start of resource usage block
            if resource_declaration_pattern.search(line):
                in_usage_block = True
                usage_block.append(line)
                continue
            
            # Inside resource usage block
            if in_usage_block:
                usage_block.append(line)
                
                # Check for end of usage (e.g., resource.close())
                if f"{resource_var}.close()" in line:
                    break
        
        return usage_block if usage_block else [f"{resource_var} = ..."]
    
    def _extract_function_params(self, code: str, function_name: str) -> List[str]:
        """
        Extract parameters from a function call.
        
        Args:
            code: The code line with the function call
            function_name: The name of the function
            
        Returns:
            List of parameter strings
        """
        pattern = rf'{function_name}\s*\(([^)]*)\)'
        match = re.search(pattern, code)
        
        if not match:
            return []
        
        # Extract parameters
        params_str = match.group(1)
        
        # Handle empty parameters
        if not params_str.strip():
            return []
        
        # Split by comma but respect quotes and nested parentheses
        params = []
        current_param = ""
        paren_level = 0
        in_string = False
        string_delimiter = None
        
        for char in params_str:
            if char == ',' and paren_level == 0 and not in_string:
                params.append(current_param.strip())
                current_param = ""
                continue
            
            current_param += char
            
            if char in ('"', "'") and (not in_string or char == string_delimiter):
                in_string = not in_string
                if in_string:
                    string_delimiter = char
                else:
                    string_delimiter = None
            elif char == '(' and not in_string:
                paren_level += 1
            elif char == ')' and not in_string:
                paren_level -= 1
        
        # Add the last parameter
        if current_param.strip():
            params.append(current_param.strip())
        
        return params
    
    def _find_except_block(
        self,
        lines: List[str],
        except_line: int
    ) -> Optional[Dict[str, int]]:
        """
        Find the start and end lines of an except block.
        
        Args:
            lines: Lines of code to search
            except_line: The line number where 'except' keyword appears
            
        Returns:
            Dictionary with start_line and end_line, or None if not found
        """
        if except_line <= 0 or except_line > len(lines):
            return None
        
        # The line should have 'except' keyword
        if 'except' not in lines[except_line - 1]:
            return None
        
        # Get the indentation level of the except line
        except_indentation = len(lines[except_line - 1]) - len(lines[except_line - 1].lstrip())
        
        # Find the end of the except block
        end_line = except_line
        for i in range(except_line, len(lines)):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                end_line = i
                continue
            
            # If we find a line with same or less indentation, it's the end
            if line.strip() and len(line) - len(line.lstrip()) <= except_indentation:
                break
            
            end_line = i
        
        return {
            "start_line": except_line,
            "end_line": end_line
        }
    
    def _extract_exception_type(self, code: str) -> str:
        """
        Extract the exception type from an except statement.
        
        Args:
            code: The code line with the except statement
            
        Returns:
            The exception type or 'Exception' if not found
        """
        pattern = r'except\s+(\w+(\.\w+)*)(\s+as\s+\w+)?:'
        match = re.search(pattern, code)
        
        if match:
            return match.group(1)
        
        return "Exception"
    
    def _extract_variable_assignment(self, code: str) -> Optional[str]:
        """
        Extract the variable name from an assignment statement.
        
        Args:
            code: The code line with the assignment
            
        Returns:
            The variable name or None if not found
        """
        pattern = r'(\w+)\s*='
        match = re.search(pattern, code)
        
        if match:
            return match.group(1)
        
        return None
    
    def _extract_sql_query_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Extract information about a SQL query from code.
        
        Args:
            code: The code line with the SQL query
            
        Returns:
            Dictionary with query information or None if not found
        """
        # Look for variable assignment
        var_pattern = r'(\w+)\s*=\s*["\'](.+?)["\'](.*)'
        var_match = re.search(var_pattern, code)
        
        if var_match:
            query_var = var_match.group(1)
            query_string = var_match.group(2)
            remainder = var_match.group(3)
            
            # Extract parameters from string concatenation
            params = []
            param_pattern = r'\s*\+\s*(\w+)'
            for param_match in re.finditer(param_pattern, remainder):
                params.append(param_match.group(1))
            
            return {
                "query_var": query_var,
                "query_string": query_string,
                "parameters": params
            }
        
        # Direct query execution
        direct_pattern = r'execute\(["\'](.+?)["\'](.*)'
        direct_match = re.search(direct_pattern, code)
        
        if direct_match:
            query_string = direct_match.group(1)
            remainder = direct_match.group(2)
            
            # Extract parameters from string concatenation
            params = []
            param_pattern = r'\s*\+\s*(\w+)'
            for param_match in re.finditer(param_pattern, remainder):
                params.append(param_match.group(1))
            
            return {
                "query_var": None,
                "query_string": query_string,
                "parameters": params
            }
        
        return None
    
    def _extract_credential_info(self, code: str) -> Optional[Dict[str, str]]:
        """
        Extract credential information from code.
        
        Args:
            code: The code line with the credential
            
        Returns:
            Dictionary with credential information or None if not found
        """
        # Look for variable assignment with string value
        var_pattern = r'(\w+)\s*=\s*["\'](.+?)["\']'
        var_match = re.search(var_pattern, code)
        
        if var_match:
            var_name = var_match.group(1)
            var_value = var_match.group(2)
            
            # Determine the type of credential
            cred_type = "unknown"
            if var_name.lower() in ("password", "passwd", "pwd", "pass", "secret", "key", "token"):
                cred_type = "password"
            elif var_name.lower() in ("username", "user", "uname", "login", "userid"):
                cred_type = "username"
            elif var_name.lower() in ("api_key", "apikey", "api", "access_key", "accesskey"):
                cred_type = "api_key"
            
            return {
                "variable": var_name,
                "value": var_value,
                "type": cred_type
            }
        
        return None
    
    def _apply_patch_changes(self, content: str, changes: List[Dict[str, Any]]) -> str:
        """
        Apply changes to file content.
        
        Args:
            content: The original file content
            changes: List of change operations
            
        Returns:
            The modified file content
        """
        # Split the content into lines
        lines = content.splitlines()
        
        # Sort changes by line number in descending order to avoid index shifts
        sorted_changes = sorted(changes, key=lambda c: c.get("start_line", 0), reverse=True)
        
        for change in sorted_changes:
            change_type = change.get("type", "")
            
            if change_type == "replace_lines":
                start_line = change.get("start_line", 0)
                end_line = change.get("end_line", start_line)
                
                if start_line <= 0 or start_line > len(lines) + 1:
                    continue
                
                # Adjust for 0-based indexing
                start_idx = start_line - 1
                end_idx = min(end_line, len(lines))
                
                # Replace the specified lines
                new_content = change.get("content", "")
                new_lines = new_content.splitlines()
                
                lines[start_idx:end_idx] = new_lines
            
            elif change_type == "insert_lines":
                start_line = change.get("start_line", 0)
                
                if start_line <= 0 or start_line > len(lines) + 1:
                    continue
                
                # Adjust for 0-based indexing
                start_idx = start_line - 1
                
                # Insert the specified lines
                new_content = change.get("content", "")
                new_lines = new_content.splitlines()
                
                lines[start_idx:start_idx] = new_lines
            
            elif change_type == "delete_lines":
                start_line = change.get("start_line", 0)
                end_line = change.get("end_line", start_line)
                
                if start_line <= 0 or start_line > len(lines):
                    continue
                
                # Adjust for 0-based indexing
                start_idx = start_line - 1
                end_idx = min(end_line, len(lines))
                
                # Delete the specified lines
                lines[start_idx:end_idx] = []
        
        # Join the lines back into a single string
        return "\n".join(lines)
    
    def _create_empty_implementation(
        self,
        strategy: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """
        Create an empty implementation when implementation is not possible.
        
        Args:
            strategy: The repair strategy
            reason: The reason why implementation is not possible
            
        Returns:
            Empty implementation details
        """
        return {
            "patches": [],
            "language": "unknown",
            "description": f"Could not implement fix: {reason}",
            "approach": "Not implemented",
            "risk_level": "high",
            "error": reason
        }
    
    def _get_timestamp(self) -> str:
        """
        Get the current timestamp in ISO format.
        
        Returns:
            Current timestamp
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _handle_task_request(self, message: AgentMessage) -> None:
        """
        Handle a task request message.
        
        Args:
            message: The task request message
        """
        content = message.content
        action = content.get("action", "")
        
        if action == "implement_strategy":
            strategy = content.get("strategy")
            additional_context = content.get("additional_context")
            
            if not strategy:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": "strategy is required"
                    }
                )
                return
            
            try:
                implementation = self.implement_strategy(
                    strategy=strategy,
                    additional_context=additional_context
                )
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.TASK_RESULT,
                    content={
                        "status": "success",
                        "implementation": implementation
                    }
                )
            except Exception as e:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
        
        elif action == "apply_implementation":
            implementation = content.get("implementation")
            dry_run = content.get("dry_run", False)
            
            if not implementation:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": "implementation is required"
                    }
                )
                return
            
            try:
                result = self.apply_implementation(
                    implementation=implementation,
                    dry_run=dry_run
                )
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.TASK_RESULT,
                    content={
                        "status": "success",
                        "result": result
                    }
                )
            except Exception as e:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
        
        else:
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={
                    "status": "error",
                    "error": f"Unknown action: {action}"
                }
            )
    
    def _handle_query(self, message: AgentMessage) -> None:
        """
        Handle a query message.
        
        Args:
            message: The query message
        """
        content = message.content
        query_type = content.get("query_type", "")
        
        if query_type == "get_implementation_status":
            implementation_id = content.get("implementation_id")
            
            if not implementation_id:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": "implementation_id is required"
                    }
                )
                return
            
            status = self.get_implementation_status(implementation_id)
            
            self.send_response(
                original_message=message,
                message_type=MessageType.QUERY_RESPONSE,
                content={
                    "status": "success" if status else "not_found",
                    "implementation_status": status
                }
            )
        
        else:
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={
                    "status": "error",
                    "error": f"Unknown query type: {query_type}"
                }
            )
    
    def _handle_other_message(self, message: AgentMessage) -> None:
        """
        Handle other types of messages.
        
        Args:
            message: The message to handle
        """
        # Handle task results from other agents
        if message.message_type == MessageType.TASK_RESULT:
            content = message.content
            
            # If it's a verification result for one of our implementations
            if "verification_result" in content and "implementation_id" in content:
                implementation_id = content["implementation_id"]
                success = content.get("success", False)
                
                if success and implementation_id in self.successful_implementations:
                    # Update the implementation status
                    self.successful_implementations[implementation_id]["verified"] = True
                    self.successful_implementations[implementation_id]["verification_result"] = content
        
        # Let the base class handle other message types
        super()._handle_other_message(message)
