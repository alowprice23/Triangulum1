"""
Core functionality for the advanced verification system.

This module provides the core components of the enhanced verification system,
including test generation, property-based testing, and secure sandbox execution.
"""

import os
import sys
import ast
import tempfile
import shutil
import subprocess
import logging
import json
import platform
import random
import string
import re
from typing import Dict, List, Any, Optional, Tuple, Callable, Set, Union
from pathlib import Path
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CodeArtifact(ABC):
    """Represents a piece of code to be verified."""
    def __init__(self, artifact_id: str, file_path: str, content: str):
        self.id = artifact_id
        self.file_path = file_path
        self.content = content

class VerificationContext:
    """Holds context for a verification run."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config

class VerificationResult:
    """Holds the result of a verification check."""
    def __init__(self, artifact_id: str, plugin_id: str, status: 'VerificationStatus', success: bool, confidence: float, issues: List[Dict], recommendations: List[Dict], metrics: Dict, duration_ms: int, details: Dict):
        self.artifact_id = artifact_id
        self.plugin_id = plugin_id
        self.status = status
        self.success = success
        self.confidence = confidence
        self.issues = issues
        self.recommendations = recommendations
        self.metrics = metrics
        self.duration_ms = duration_ms
        self.details = details

class VerificationStatus:
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ERROR = "ERROR"

class MetricDefinition:
    def __init__(self, name: str, description: str, unit: str, type: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.unit = unit
        self.type = type
        self.labels = labels or []

class VerifierPlugin(ABC):
    """Abstract base class for all verifier plugins."""
    def __init__(self, context: VerificationContext):
        self.context = context

    @abstractmethod
    async def verify(self, artifact: CodeArtifact) -> VerificationResult:
        """Perform verification on a code artifact."""
        pass

    def register_metrics(self) -> List[MetricDefinition]:
        """Define metrics that this plugin will report."""
        return []

class VerificationEnvironment:
    """
    Manages the verification environment setup and configuration.
    
    This class is responsible for setting up the environment needed for verification,
    including creating sandboxes, installing dependencies, and configuring the
    runtime environment.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the verification environment.
        
        Args:
            config: Configuration for the environment
        """
        self.config = config or {}
        self.sandbox_path = None
        self.runtime_info = self._detect_runtime()
        
    def _detect_runtime(self) -> Dict[str, Any]:
        """
        Detect the runtime environment information.
        
        Returns:
            Dictionary with runtime environment details
        """
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "python_path": sys.executable,
            "available_tools": self._detect_available_tools()
        }
    
    def _detect_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Detect available tools in the environment.
        
        Returns:
            Dictionary of tool names to availability and version info
        """
        tools = {}
        
        # Testing tools
        testing_tools = ["pytest", "unittest", "nose2", "coverage"]
        for tool in testing_tools:
            tools[tool] = self._check_tool_availability(tool)
        
        # Linting tools
        linting_tools = ["flake8", "pylint", "mypy", "black", "isort"]
        for tool in linting_tools:
            tools[tool] = self._check_tool_availability(tool)
        
        # Security tools
        security_tools = ["bandit", "safety"]
        for tool in security_tools:
            tools[tool] = self._check_tool_availability(tool)
        
        # Property-based testing tools
        property_tools = ["hypothesis"]
        for tool in property_tools:
            # Check if Python package is installed
            try:
                subprocess.run(
                    [sys.executable, "-c", f"import {tool}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=2
                )
                tools[tool] = {"available": True}
            except (subprocess.SubprocessError, FileNotFoundError):
                tools[tool] = {"available": False}
        
        return tools
    
    def _check_tool_availability(self, tool: str) -> Dict[str, Any]:
        """
        Check if a command-line tool is available.
        
        Args:
            tool: Name of the tool to check
            
        Returns:
            Dictionary with availability and version information
        """
        result = {"available": False, "version": None}
        
        try:
            # Try running the tool with version flag
            process = subprocess.run(
                [tool, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2,
                text=True
            )
            
            if process.returncode == 0:
                result["available"] = True
                # Extract version from output
                output = process.stdout.strip() or process.stderr.strip()
                result["version"] = output
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return result
    
    def setup_sandbox(
        self,
        affected_files: List[str],
        project_root: Optional[str] = None
    ) -> str:
        """
        Set up a sandbox environment for verification.
        
        Args:
            affected_files: List of file paths affected by the implementation
            project_root: Root directory of the project (optional)
            
        Returns:
            Path to the created sandbox
        """
        # Create a temporary directory for the sandbox
        self.sandbox_path = tempfile.mkdtemp(prefix="triangulum_verification_")
        
        # Copy the affected files to the sandbox
        for file_path in affected_files:
            if os.path.isfile(file_path):
                # Create the directory structure in the sandbox
                rel_path = os.path.relpath(file_path, project_root) if project_root else file_path
                sandbox_file_path = os.path.join(self.sandbox_path, rel_path)
                os.makedirs(os.path.dirname(sandbox_file_path), exist_ok=True)
                
                # Copy the file
                shutil.copy2(file_path, sandbox_file_path)
        
        # Set up the verification environment
        self._setup_environment()
        
        return self.sandbox_path
    
    def _setup_environment(self):
        """Set up the verification environment in the sandbox."""
        if not self.sandbox_path:
            raise ValueError("Sandbox path not set. Call setup_sandbox first.")
        
        # Create directories for test artifacts
        test_dir = os.path.join(self.sandbox_path, ".verification")
        os.makedirs(test_dir, exist_ok=True)
        
        # Set up virtual environment if configured
        if self.config.get("use_virtualenv", False):
            try:
                venv_dir = os.path.join(self.sandbox_path, ".venv")
                subprocess.run(
                    [sys.executable, "-m", "venv", venv_dir],
                    check=True
                )
                
                # Store the path to the virtual environment python
                if platform.system() == "Windows":
                    self.python_path = os.path.join(venv_dir, "Scripts", "python.exe")
                else:
                    self.python_path = os.path.join(venv_dir, "bin", "python")
                
                # Install required packages
                if "requirements" in self.config:
                    requirements = self.config["requirements"]
                    subprocess.run(
                        [self.python_path, "-m", "pip", "install"] + requirements,
                        check=True
                    )
            except subprocess.SubprocessError as e:
                logger.warning(f"Failed to set up virtual environment: {e}")
                # Fall back to system Python
                self.python_path = sys.executable
        else:
            # Use system Python
            self.python_path = sys.executable
    
    def cleanup(self):
        """Clean up the sandbox environment."""
        if self.sandbox_path and os.path.exists(self.sandbox_path):
            try:
                shutil.rmtree(self.sandbox_path)
                self.sandbox_path = None
            except Exception as e:
                logger.warning(f"Failed to clean up sandbox: {e}")
    
    def get_sandbox_path(self, rel_path: str) -> str:
        """
        Get the absolute path to a file in the sandbox.
        
        Args:
            rel_path: Relative path within the sandbox
            
        Returns:
            Absolute path to the file in the sandbox
        """
        if not self.sandbox_path:
            raise ValueError("Sandbox not set up")
        
        return os.path.join(self.sandbox_path, rel_path)
    
    def execute_in_sandbox(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a command in the sandbox environment.
        
        Args:
            command: Command to execute as a list of strings
            cwd: Working directory within the sandbox (relative to sandbox root)
            timeout: Timeout in seconds
            env: Additional environment variables
            
        Returns:
            Dictionary with execution results
        """
        if not self.sandbox_path:
            raise ValueError("Sandbox not set up")
        
        result = {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": None
        }
        
        try:
            # Set working directory
            working_dir = self.sandbox_path
            if cwd:
                working_dir = os.path.join(self.sandbox_path, cwd)
                if not os.path.exists(working_dir):
                    os.makedirs(working_dir, exist_ok=True)
            
            # Set up environment variables
            env_vars = os.environ.copy()
            if env:
                env_vars.update(env)
            
            # Execute the command
            process = subprocess.run(
                command,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
                env=env_vars
            )
            
            result["returncode"] = process.returncode
            result["stdout"] = process.stdout
            result["stderr"] = process.stderr
            result["success"] = process.returncode == 0
        
        except subprocess.TimeoutExpired as e:
            result["error"] = f"Command timed out after {timeout} seconds"
        except Exception as e:
            result["error"] = str(e)
        
        return result


class TestGenerator:
    """
    Generates tests for verifying bug fixes.
    
    This class provides methods to generate different types of tests,
    including unit tests, property-based tests, and regression tests,
    based on the context of the bug being fixed.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the test generator.
        
        Args:
            config: Configuration for test generation
        """
        self.config = config or {}
    
    def generate_tests(
        self,
        bug_type: str,
        bug_location: str,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None,
        existing_tests: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate tests for a specific bug fix.
        
        Args:
            bug_type: Type of the bug being fixed
            bug_location: Location of the bug in the code
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            existing_tests: List of existing test files (optional)
            
        Returns:
            Dictionary with generated tests
        """
        result = {
            "unit_tests": [],
            "property_tests": [],
            "regression_tests": [],
            "integration_tests": []
        }
        
        # Generate unit tests
        unit_tests = self.generate_unit_tests(
            bug_type, bug_location, implementation, strategy)
        if unit_tests:
            result["unit_tests"].append(unit_tests)
        
        # Generate property-based tests if appropriate for the bug type
        if bug_type in ["null_pointer", "resource_leak", "sql_injection"]:
            property_tests = self.generate_property_tests(
                bug_type, bug_location, implementation, strategy)
            if property_tests:
                result["property_tests"].append(property_tests)
        
        # Generate regression tests based on existing tests
        if existing_tests:
            regression_tests = self.generate_regression_tests(
                bug_type, bug_location, implementation, existing_tests)
            if regression_tests:
                result["regression_tests"].append(regression_tests)
        
        # Generate integration tests for specific bug types
        if bug_type in ["resource_leak", "sql_injection", "hardcoded_credentials"]:
            integration_tests = self.generate_integration_tests(
                bug_type, bug_location, implementation, strategy)
            if integration_tests:
                result["integration_tests"].append(integration_tests)
        
        return result
    
    def generate_property_tests(
        self,
        bug_type: str,
        bug_location: str,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate property-based tests for a bug fix.
        
        Args:
            bug_type: Type of the bug being fixed
            bug_location: Location of the bug in the code
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Dictionary with property test details
        """
        # Implementation would go here
        return {}
    
    def generate_regression_tests(
        self,
        bug_type: str,
        bug_location: str,
        implementation: Dict[str, Any],
        existing_tests: List[str]
    ) -> Dict[str, Any]:
        """
        Generate regression tests for a bug fix.
        
        Args:
            bug_type: Type of the bug being fixed
            bug_location: Location of the bug in the code
            implementation: Implementation details
            existing_tests: List of existing test files
            
        Returns:
            Dictionary with regression test details
        """
        # Implementation would go here
        return {}
    
    def generate_integration_tests(
        self,
        bug_type: str,
        bug_location: str,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate integration tests for a bug fix.
        
        Args:
            bug_type: Type of the bug being fixed
            bug_location: Location of the bug in the code
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Dictionary with integration test details
        """
        # Implementation would go here
        return {}
    
    def generate_unit_tests(
        self,
        bug_type: str,
        bug_location: str,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate unit tests for a bug fix.
        
        Args:
            bug_type: Type of the bug being fixed
            bug_location: Location of the bug in the code
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Dictionary with unit test details
        """
        # Extract file extension to determine language
        _, ext = os.path.splitext(bug_location)
        language = self._determine_language(ext)
        
        if language == "python":
            return self._generate_python_unit_tests(bug_type, bug_location, implementation, strategy)
        elif language in ["javascript", "typescript"]:
            return self._generate_js_unit_tests(bug_type, bug_location, implementation, strategy)
        else:
            return {"error": f"Unsupported language for test generation: {language}"}
    
    def _determine_language(self, extension: str) -> str:
        """
        Determine the programming language based on file extension.
        
        Args:
            extension: File extension (including the dot)
            
        Returns:
            Language name
        """
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cs": "csharp",
            ".php": "php",
            ".rb": "ruby",
            ".go": "go"
        }
        
        return language_map.get(extension.lower(), "unknown")
    
    def _generate_python_unit_tests(
        self,
        bug_type: str,
        bug_location: str,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate Python unit tests for a bug fix.
        
        Args:
            bug_type: Type of the bug being fixed
            bug_location: Location of the bug in the code
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Dictionary with Python unit test details
        """
        # Generate a test file name based on the bug location
        base_name = os.path.basename(bug_location)
        module_name = os.path.splitext(base_name)[0]
        test_file_name = f"test_generated_{module_name}.py"
        
        # Generate a class name for the test
        class_name = f"Test{module_name.title().replace('_', '')}"
        
        # Generate test methods based on bug type
        test_methods = []
        
        if bug_type == "null_pointer":
            test_methods.append(self._generate_null_pointer_test(implementation, strategy))
        elif bug_type == "resource_leak":
            test_methods.append(self._generate_resource_leak_test(implementation, strategy))
        elif bug_type == "sql_injection":
            test_methods.append(self._generate_sql_injection_test(implementation, strategy))
        elif bug_type == "hardcoded_credentials":
            test_methods.append(self._generate_hardcoded_credentials_test(implementation, strategy))
        elif bug_type == "exception_swallowing":
            test_methods.append(self._generate_exception_swallowing_test(implementation, strategy))
        
        # Generate the test file content
        test_content = f"""
import unittest
import sys
import os
import re
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the module being tested
try:
    from {module_name} import *
except ImportError:
    # Try relative import if direct import fails
    module_path = os.path.abspath("{bug_location}")
    module_dir = os.path.dirname(module_path)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    from {module_name} import *


class {class_name}(unittest.TestCase):
    \"\"\"Tests for the fixed {bug_type} bug in {module_name}.\"\"\"
    
    def setUp(self):
        \"\"\"Set up test environment.\"\"\"
        pass
    
    def tearDown(self):
        \"\"\"Clean up after tests.\"\"\"
        pass
    
{os.linesep.join(test_methods)}

if __name__ == "__main__":
    unittest.main()
"""
        
        return {
            "file_name": test_file_name,
            "content": test_content,
            "class_name": class_name,
            "bug_type": bug_type,
            "language": "python"
        }
    
    def _generate_null_pointer_test(
        self,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a test method for a null pointer bug fix.
        
        Args:
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Test method as a string
        """
        # Extract function name from implementation if available
        function_name = "function_with_null_check"
        if strategy and "function_name" in strategy:
            function_name = strategy["function_name"]
        
        return f"""    def test_null_input_handling(self):
        \"\"\"Test that None input is handled correctly.\"\"\"
        # The function should not raise an exception when given None
        try:
            result = {function_name}(None)
            # Function should return None or a default value, not raise an exception
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"Function raised an exception with None input: {{e}}")
            
    def test_valid_input_handling(self):
        \"\"\"Test that valid input works correctly after the fix.\"\"\"
        # Create a valid test input
        test_input = {{"key": "value"}}
        
        # The function should work with valid input
        result = {function_name}(test_input)
        self.assertEqual(result, "value")"""
    
    def _generate_resource_leak_test(
        self,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a test method for a resource leak bug fix.
        
        Args:
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Test method as a string
        """
        # Extract function name from implementation if available
        function_name = "function_with_resource"
        if strategy and "function_name" in strategy:
            function_name = strategy["function_name"]
        
        return f"""    def test_resource_properly_closed(self):
        \"\"\"Test that resources are properly closed.\"\"\"
        # Mock the resource to track if it's closed
        mock_resource = MagicMock()
        
        # Patch the open function to return our mock
        with patch('builtins.open', return_value=mock_resource):
            # Call the function that should manage the resource
            {function_name}('test_file.txt')
            
            # Verify that close was called
            mock_resource.close.assert_called_once()
            
    def test_resource_closed_on_exception(self):
        \"\"\"Test that resources are closed even when exceptions occur.\"\"\"
        # Mock the resource to track if it's closed
        mock_resource = MagicMock()
        mock_resource.read.side_effect = Exception("Test exception")
        
        # Patch the open function to return our mock
        with patch('builtins.open', return_value=mock_resource):
            # Call the function that should manage the resource
            # It should handle the exception and still close the resource
            try:
                {function_name}('test_file.txt')
            except Exception:
                # Exception might be re-raised, that's fine
                pass
                
            # Verify that close was called despite the exception
            mock_resource.close.assert_called_once()"""
    
    def _generate_sql_injection_test(
        self,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a test method for an SQL injection bug fix.
        
        Args:
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Test method as a string
        """
        # Extract function name from implementation if available
        function_name = "function_with_sql_query"
        if strategy and "function_name" in strategy:
            function_name = strategy["function_name"]
        
        return f"""    def test_sql_injection_prevention(self):
        \"\"\"Test that SQL injection is prevented.\"\"\"
        # Mock the cursor and connection
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Patch the database connection function
        with patch('sqlite3.connect', return_value=mock_connection):
            # Call the function with a malicious input
            malicious_input = "user' OR '1'='1"
            {function_name}(malicious_input)
            
            # Verify that parameters were passed separately, not concatenated
            execute_call_args = mock_cursor.execute.call_args
            # First argument should be the SQL query
            query = execute_call_args[0][0]
            # Second argument should be the parameters
            params = execute_call_args[0][1] if len(execute_call_args[0]) > 1 else None
            
            # Check that parameters are passed separately
            self.assertIsNotNone(params, "Parameters should be passed separately to prevent SQL injection")
            
            # Make sure the malicious input is not directly in the query string
            self.assertNotIn(malicious_input, query, "Malicious input should not be directly in the query string")"""
    
    def _generate_hardcoded_credentials_test(
        self,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a test method for a hardcoded credentials bug fix.
        
        Args:
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Test method as a string
        """
        # Extract function name from implementation if available
        function_name = "function_with_credentials"
        if strategy and "function_name" in strategy:
            function_name = strategy["function_name"]
        
        return f"""    def test_no_hardcoded_credentials(self):
        \"\"\"Test that credentials are not hardcoded.\"\"\"
        # Get the source code of the module
        import inspect
        source_code = inspect.getsource({function_name})
        
        # Check for common credential patterns
        credential_patterns = [
            r"password\\s*=\\s*['\\\"]\\w+['\\\"]",
            r"api_key\\s*=\\s*['\\\"]\\w+['\\\"]",
            r"secret\\s*=\\s*['\\\"]\\w+['\\\"]",
            r"token\\s*=\\s*['\\\"]\\w+['\\\"]"
        ]
        
        for pattern in credential_patterns:
            matches = re.findall(pattern, source_code, re.IGNORECASE)
            self.assertEqual(len(matches), 0, f"Found potential hardcoded credential: {{matches}}")
    
    def test_environment_variable_usage(self):
        \"\"\"Test that environment variables are used for credentials.\"\"\"
        # Mock environment variables
        test_creds = "test_password"
        env_vars = {{"PASSWORD": test_creds, "API_KEY": "test_key"}}
        
        # Patch os.environ to return our test values
        with patch.dict('os.environ', env_vars):
            # Call the function and check if it uses environment variables
            result = {function_name}()
            
            # This assertion depends on what the function returns
            # Adjust as needed based on the actual function
            self.assertIsNotNone(result, "Function should use environment variables and return a result")"""
    
    def _generate_exception_swallowing_test(
        self,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a test method for an exception swallowing bug fix.
        
        Args:
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Test method as a string
        """
        # Extract function name from implementation if available
        function_name = "function_with_exception_handling"
        if strategy and "function_name" in strategy:
            function_name = strategy["function_name"]
        
        return f"""    def test_exception_properly_handled(self):
        \"\"\"Test that exceptions are properly handled, not swallowed.\"\"\"
        # Create a function that will raise an exception
        def raise_exception(*args, **kwargs):
            raise ValueError("Test exception")
        
        # Mock a dependency to raise an exception
        with patch('builtins.open', side_effect=raise_exception):
            # Call the function that should handle the exception
            try:
                {function_name}('test_file.txt')
                # If we get here, the exception was swallowed
                self.fail("Function should not swallow exceptions without proper handling")
            except Exception as e:
                # Exception should be re-raised or logged
                self.assertIsInstance(e, ValueError)
    
    def test_exception_logging(self):
        \"\"\"Test that exceptions are logged before being re-raised.\"\"\"
        # Create a function that will raise an exception
        def raise_exception(*args, **kwargs):
            raise ValueError("Test exception")
        
        # Mock the logging function
        with patch('logging.error') as mock_log, patch('builtins.open', side_effect=raise_exception):
            # Call the function that should log the exception
            try:
                {function_name}('test_file.txt')
            except Exception:
                # Exception is expected to be re-raised
                pass
                
            # Verify that the exception was logged
            mock_log.assert_called()"""

    def _generate_js_unit_tests(
        self,
        bug_type: str,
        bug_location: str,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate JavaScript unit tests for a bug fix.
        
        Args:
            bug_type: Type of the bug being fixed
            bug_location: Location of the bug in the code
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            
        Returns:
            Dictionary with JavaScript unit test details
        """
        # Generate a test file name based on the bug location
        base_name = os.path.basename(bug_location)
        module_name = os.path.splitext(base_name)[0]
        test_file_name = f"{module_name}.test.js"
        
        # Generate test methods based on bug type
        test_methods = []
        
        if bug_type == "null_pointer":
            test_methods.append(self._generate_js_null_pointer_test(implementation, strategy, module_name))
        elif bug_type == "resource_leak":
            test_methods.append(self._generate_js_resource_leak_test(implementation, strategy, module_name))
        # Add more JS test generators as needed
        
        # Generate the test file content
        test_content = f"""
const {{ expect }} = require('chai');
const sinon = require('sinon');
const {{ {module_name} }} = require('./{module_name}');

describe('{module_name} Tests', () => {{
    beforeEach(() => {{
        // Set up before each test
    }});
    
    afterEach(() => {{
        // Clean up after each test
        sinon.restore();
    }});
    
{os.linesep.join(test_methods)}
}});
"""
        
        return {
            "file_name": test_file_name,
            "content": test_content,
            "module_name": module_name,
            "bug_type": bug_type,
            "language": "javascript"
        }
    
    def _generate_js_null_pointer_test(
        self,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None,
        module_name: str = ""
    ) -> str:
        """
        Generate a JavaScript test for a null pointer bug fix.
        
        Args:
            implementation: Implementation details
            strategy: Strategy used to fix the bug (optional)
            module_name: Name of the module being tested
            
        Returns:
            Test method as a string
        """
        # Extract function name from implementation if available
        function_name = "functionWithNullCheck"
        if strategy and "function_name" in strategy:
            function_name = strategy["function_name"]
        
        return f"""    it('should handle null input correctly', () => {{
        // The function should not throw an exception when given null
        expect(() => {module_name}.{function_name}(null)).to.not.throw();
        
        // Function should return null or a default value
        const result = {module_name}.{function_name}(null);
        expect(result).to.not.be.undefined;
    }});
    
    it('should handle valid input correctly', () => {{
        // Create a valid test input
        const testInput = {{ key: 'value' }};
        
        // The function should work with valid input
        const result = {module_name}.{function_name}(testInput);
        expect(result).to.equal('value');
    }});"""
