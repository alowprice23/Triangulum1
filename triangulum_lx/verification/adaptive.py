"""
Adaptive verification system for intelligent test generation.

This module provides adaptive testing capabilities that adjust verification
strategies based on the context of the code, bug type, and previous results.
It enables more targeted and efficient verification that learns from past
verification sessions.
"""

import logging
import os
import json
import time
import random
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from pathlib import Path
from collections import defaultdict

from .metrics import VerificationMetrics

logger = logging.getLogger(__name__)

class AdaptiveVerifier:
    """
    Adaptive verification system that learns from previous verification results.
    
    This class provides methods to adjust verification strategies based on
    the context of the code, bug type, and previous results. It enables more
    targeted and efficient verification that learns from past verification sessions.
    """
    
    def __init__(self, metrics: Optional[VerificationMetrics] = None):
        """
        Initialize the adaptive verifier.
        
        Args:
            metrics: Verification metrics for learning (optional)
        """
        self.metrics = metrics or VerificationMetrics()
        self.history = []
        self.strategy_performance = defaultdict(lambda: defaultdict(list))
        self.bug_specific_strategies = defaultdict(dict)
        
        # Load strategies from history if available
        self._load_strategies()
    
    def _load_strategies(self, strategy_path: Optional[str] = None):
        """
        Load verification strategies from saved data.
        
        Args:
            strategy_path: Path to load strategies from (optional)
        """
        default_path = os.path.join(
            os.getcwd(), ".triangulum", "verification", "strategies.json")
        path = strategy_path or default_path
        
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                if "bug_specific_strategies" in data:
                    self.bug_specific_strategies = defaultdict(dict, data["bug_specific_strategies"])
                
                if "strategy_performance" in data:
                    # Convert the nested dictionaries back to defaultdict
                    for bug_type, strategies in data["strategy_performance"].items():
                        for strategy, results in strategies.items():
                            self.strategy_performance[bug_type][strategy] = results
                
                logger.info(f"Loaded verification strategies from {path}")
            except Exception as e:
                logger.error(f"Failed to load verification strategies: {e}")
    
    def save_strategies(self, strategy_path: Optional[str] = None):
        """
        Save verification strategies to a file.
        
        Args:
            strategy_path: Path to save strategies to (optional)
        """
        default_path = os.path.join(
            os.getcwd(), ".triangulum", "verification", "strategies.json")
        path = strategy_path or default_path
        
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Convert defaultdicts to regular dicts for JSON serialization
            data = {
                "bug_specific_strategies": dict(self.bug_specific_strategies),
                "strategy_performance": {
                    bug_type: dict(strategies)
                    for bug_type, strategies in self.strategy_performance.items()
                }
            }
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved verification strategies to {path}")
        except Exception as e:
            logger.error(f"Failed to save verification strategies: {e}")
    
    def select_verification_strategy(
        self,
        bug_type: str,
        code_context: Dict[str, Any],
        exploration_factor: float = 0.2
    ) -> Dict[str, Any]:
        """
        Select an appropriate verification strategy based on bug type and context.
        
        Args:
            bug_type: Type of bug being fixed
            code_context: Context information about the code
            exploration_factor: Factor for exploring new strategies (0-1)
            
        Returns:
            Selected verification strategy
        """
        available_strategies = self._get_available_strategies(bug_type, code_context)
        
        # If no strategies are available, use a default strategy
        if not available_strategies:
            return self._get_default_strategy(bug_type)
        
        # Decide whether to explore a new strategy or exploit the best known strategy
        if random.random() < exploration_factor:
            # Exploration: try a random strategy
            return random.choice(available_strategies)
        else:
            # Exploitation: use the best known strategy
            return self._get_best_strategy(bug_type, available_strategies)
    
    def _get_available_strategies(
        self,
        bug_type: str,
        code_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get available verification strategies for a bug type and context.
        
        Args:
            bug_type: Type of bug being fixed
            code_context: Context information about the code
            
        Returns:
            List of available verification strategies
        """
        language = code_context.get("language", "unknown")
        
        # Start with general strategies for the bug type
        strategies = []
        
        # Add default strategies based on bug type
        if bug_type in self.bug_specific_strategies:
            strategies.extend(self.bug_specific_strategies[bug_type].values())
        
        # Adjust strategies based on the code context
        # For example, add language-specific strategies
        language_specific = self._get_language_specific_strategies(bug_type, language)
        if language_specific:
            strategies.extend(language_specific)
        
        return strategies
    
    def _get_language_specific_strategies(
        self,
        bug_type: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """
        Get language-specific verification strategies.
        
        Args:
            bug_type: Type of bug being fixed
            language: Programming language
            
        Returns:
            List of language-specific verification strategies
        """
        strategies = []
        
        # Null pointer strategies
        if bug_type == "null_pointer":
            if language == "python":
                strategies.append({
                    "name": "python_null_check",
                    "checks": ["syntax", "unit_tests", "edge_cases"],
                    "test_generators": ["input_fuzzing", "type_mutation"],
                    "priority_checks": ["null_input_handling", "edge_case_handling"]
                })
            elif language in ["javascript", "typescript"]:
                strategies.append({
                    "name": "js_null_check",
                    "checks": ["syntax", "unit_tests", "edge_cases"],
                    "test_generators": ["undefined_checks", "null_checks"],
                    "priority_checks": ["null_input_handling", "undefined_handling"]
                })
            elif language == "java":
                strategies.append({
                    "name": "java_null_check",
                    "checks": ["compile", "unit_tests", "static_analysis"],
                    "test_generators": ["nullpointer_tests", "optional_usage"],
                    "priority_checks": ["null_input_handling", "exception_handling"]
                })
        
        # Resource leak strategies
        elif bug_type == "resource_leak":
            if language == "python":
                strategies.append({
                    "name": "python_resource_management",
                    "checks": ["context_manager_usage", "exception_handling", "resource_tracking"],
                    "test_generators": ["exception_path_tests", "resource_leak_detector"],
                    "priority_checks": ["resource_closing", "exception_path_handling"]
                })
            elif language == "java":
                strategies.append({
                    "name": "java_resource_management",
                    "checks": ["try_with_resources", "finally_blocks", "resource_tracking"],
                    "test_generators": ["exception_path_tests", "resource_leak_detector"],
                    "priority_checks": ["resource_closing", "exception_path_handling"]
                })
        
        # SQL injection strategies
        elif bug_type == "sql_injection":
            if language == "python":
                strategies.append({
                    "name": "python_sql_injection",
                    "checks": ["parameterized_queries", "input_validation", "security_analysis"],
                    "test_generators": ["sql_injection_fuzzer", "security_scanner"],
                    "priority_checks": ["query_parameterization", "input_sanitization"]
                })
            elif language in ["javascript", "typescript"]:
                strategies.append({
                    "name": "js_sql_injection",
                    "checks": ["parameterized_queries", "orm_usage", "security_analysis"],
                    "test_generators": ["sql_injection_fuzzer", "security_scanner"],
                    "priority_checks": ["query_parameterization", "input_sanitization"]
                })
        
        # Exception swallowing strategies
        elif bug_type == "exception_swallowing":
            if language == "python":
                strategies.append({
                    "name": "python_exception_handling",
                    "checks": ["exception_logging", "exception_propagation", "error_handling"],
                    "test_generators": ["exception_path_tests", "logging_verification"],
                    "priority_checks": ["exception_logging", "exception_propagation"]
                })
        
        return strategies
    
    def _get_default_strategy(self, bug_type: str) -> Dict[str, Any]:
        """
        Get a default verification strategy for a bug type.
        
        Args:
            bug_type: Type of bug being fixed
            
        Returns:
            Default verification strategy
        """
        # Default strategies for different bug types
        default_strategies = {
            "null_pointer": {
                "name": "default_null_check",
                "checks": ["syntax", "unit_tests", "edge_cases"],
                "test_generators": ["input_fuzzing"],
                "priority_checks": ["null_input_handling"]
            },
            "resource_leak": {
                "name": "default_resource_management",
                "checks": ["resource_tracking", "exception_handling"],
                "test_generators": ["exception_path_tests"],
                "priority_checks": ["resource_closing"]
            },
            "sql_injection": {
                "name": "default_sql_injection",
                "checks": ["parameterized_queries", "input_validation"],
                "test_generators": ["sql_injection_fuzzer"],
                "priority_checks": ["query_parameterization"]
            },
            "hardcoded_credentials": {
                "name": "default_credential_management",
                "checks": ["credential_extraction", "environment_variables"],
                "test_generators": ["credential_scanner"],
                "priority_checks": ["credential_externalization"]
            },
            "exception_swallowing": {
                "name": "default_exception_handling",
                "checks": ["exception_logging", "exception_propagation"],
                "test_generators": ["exception_path_tests"],
                "priority_checks": ["exception_logging"]
            }
        }
        
        # Return the default strategy for the bug type, or a generic default
        return default_strategies.get(bug_type, {
            "name": "generic_default",
            "checks": ["syntax", "unit_tests"],
            "test_generators": ["basic_tests"],
            "priority_checks": ["basic_functionality"]
        })
    
    def _get_best_strategy(
        self,
        bug_type: str,
        available_strategies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get the best known strategy based on past performance.
        
        Args:
            bug_type: Type of bug being fixed
            available_strategies: List of available strategies
            
        Returns:
            Best verification strategy
        """
        if not available_strategies:
            return self._get_default_strategy(bug_type)
        
        # If we have performance data for this bug type
        if bug_type in self.strategy_performance:
            # Calculate the average success rate for each strategy
            strategy_scores = {}
            
            for strategy in available_strategies:
                strategy_name = strategy["name"]
                
                if strategy_name in self.strategy_performance[bug_type]:
                    # Get the success rate for this strategy
                    results = self.strategy_performance[bug_type][strategy_name]
                    if results:
                        success_rate = sum(1 for r in results if r) / len(results)
                        strategy_scores[strategy_name] = success_rate
            
            # If we have scores, return the strategy with the highest score
            if strategy_scores:
                best_strategy_name = max(strategy_scores, key=strategy_scores.get)
                for strategy in available_strategies:
                    if strategy["name"] == best_strategy_name:
                        return strategy
        
        # If we don't have performance data, return a random strategy
        return random.choice(available_strategies)
    
    def update_strategy_performance(
        self,
        bug_type: str,
        strategy_name: str,
        success: bool
    ):
        """
        Update the performance data for a strategy.
        
        Args:
            bug_type: Type of bug being fixed
            strategy_name: Name of the strategy used
            success: Whether the verification was successful
        """
        self.strategy_performance[bug_type][strategy_name].append(success)
        
        # Limit the history size to avoid memory issues
        max_history = 100
        if len(self.strategy_performance[bug_type][strategy_name]) > max_history:
            self.strategy_performance[bug_type][strategy_name] = self.strategy_performance[bug_type][strategy_name][-max_history:]
        
        # Save the updated strategies
        self.save_strategies()
    
    def generate_adaptive_test_suite(
        self,
        bug_type: str,
        code_context: Dict[str, Any],
        implementation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate an adaptive test suite based on bug type and context.
        
        Args:
            bug_type: Type of bug being fixed
            code_context: Context information about the code
            implementation: Implementation details
            
        Returns:
            Generated test suite
        """
        # Select a verification strategy
        strategy = self.select_verification_strategy(bug_type, code_context)
        
        # Generate a test suite based on the strategy
        test_suite = {
            "strategy": strategy,
            "tests": []
        }
        
        # Generate tests based on the strategy
        for test_generator in strategy["test_generators"]:
            if test_generator == "input_fuzzing":
                test_suite["tests"].extend(self._generate_input_fuzzing_tests(bug_type, code_context, implementation))
            elif test_generator == "exception_path_tests":
                test_suite["tests"].extend(self._generate_exception_path_tests(bug_type, code_context, implementation))
            elif test_generator == "sql_injection_fuzzer":
                test_suite["tests"].extend(self._generate_sql_injection_tests(bug_type, code_context, implementation))
            elif test_generator == "credential_scanner":
                test_suite["tests"].extend(self._generate_credential_tests(bug_type, code_context, implementation))
            # Add more test generators as needed
        
        return test_suite
    
    def _generate_input_fuzzing_tests(
        self,
        bug_type: str,
        code_context: Dict[str, Any],
        implementation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate input fuzzing tests.
        
        Args:
            bug_type: Type of bug being fixed
            code_context: Context information about the code
            implementation: Implementation details
            
        Returns:
            List of generated tests
        """
        tests = []
        
        # Extract function name and parameters from the code context
        function_name = code_context.get("function_name", "target_function")
        language = code_context.get("language", "python")
        
        # Generate tests for null pointer bug
        if bug_type == "null_pointer":
            # Test with None input
            tests.append({
                "name": "test_null_input",
                "type": "unit_test",
                "language": language,
                "code": self._generate_test_code(
                    language,
                    function_name,
                    "None" if language == "python" else "null",
                    "Should handle null input without crashing"
                )
            })
            
            # Test with empty container
            tests.append({
                "name": "test_empty_container",
                "type": "unit_test",
                "language": language,
                "code": self._generate_test_code(
                    language,
                    function_name,
                    "[]" if language == "python" else "[]",
                    "Should handle empty container without crashing"
                )
            })
            
            # Test with empty string
            tests.append({
                "name": "test_empty_string",
                "type": "unit_test",
                "language": language,
                "code": self._generate_test_code(
                    language,
                    function_name,
                    "''" if language == "python" else "''",
                    "Should handle empty string without crashing"
                )
            })
        
        return tests
    
    def _generate_exception_path_tests(
        self,
        bug_type: str,
        code_context: Dict[str, Any],
        implementation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate exception path tests.
        
        Args:
            bug_type: Type of bug being fixed
            code_context: Context information about the code
            implementation: Implementation details
            
        Returns:
            List of generated tests
        """
        tests = []
        
        # Extract function name and parameters from the code context
        function_name = code_context.get("function_name", "target_function")
        language = code_context.get("language", "python")
        
        # Generate tests for resource leak bug
        if bug_type == "resource_leak":
            # Test with exception during resource use
            if language == "python":
                tests.append({
                    "name": "test_exception_during_resource_use",
                    "type": "unit_test",
                    "language": language,
                    "code": f"""
def test_exception_during_resource_use(self):
    # Mock the resource to raise an exception during use
    mock_resource = MagicMock()
    mock_resource.read.side_effect = Exception("Test exception")
    
    # Patch the open function to return our mock
    with patch('builtins.open', return_value=mock_resource):
        try:
            {function_name}('test_file.txt')
        except Exception:
            # Exception is expected, but the resource should still be closed
            pass
        
        # Verify that close was called despite the exception
        mock_resource.close.assert_called_once()
"""
                })
        
        # Generate tests for exception swallowing bug
        elif bug_type == "exception_swallowing":
            if language == "python":
                tests.append({
                    "name": "test_exception_logging",
                    "type": "unit_test",
                    "language": language,
                    "code": f"""
def test_exception_logging(self):
    # Mock the logging function
    with patch('logging.error') as mock_log:
        # Force an exception to occur
        with patch('builtins.open', side_effect=Exception("Test exception")):
            try:
                {function_name}('test_file.txt')
            except Exception:
                # The exception should be re-raised after logging
                pass
            
            # Verify that the exception was logged
            mock_log.assert_called()
"""
                })
        
        return tests
    
    def _generate_sql_injection_tests(
        self,
        bug_type: str,
        code_context: Dict[str, Any],
        implementation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate SQL injection tests.
        
        Args:
            bug_type: Type of bug being fixed
            code_context: Context information about the code
            implementation: Implementation details
            
        Returns:
            List of generated tests
        """
        tests = []
        
        # Extract function name and parameters from the code context
        function_name = code_context.get("function_name", "target_function")
        language = code_context.get("language", "python")
        
        # Generate tests for SQL injection bug
        if bug_type == "sql_injection":
            if language == "python":
                tests.append({
                    "name": "test_sql_injection_prevention",
                    "type": "unit_test",
                    "language": language,
                    "code": f"""
def test_sql_injection_prevention(self):
    # Mock the database connection and cursor
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
        self.assertNotIn(malicious_input, query, "Malicious input should not be directly in the query string")
"""
                })
        
        return tests
    
    def _generate_credential_tests(
        self,
        bug_type: str,
        code_context: Dict[str, Any],
        implementation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate credential tests.
        
        Args:
            bug_type: Type of bug being fixed
            code_context: Context information about the code
            implementation: Implementation details
            
        Returns:
            List of generated tests
        """
        tests = []
        
        # Extract function name and parameters from the code context
        function_name = code_context.get("function_name", "target_function")
        language = code_context.get("language", "python")
        
        # Generate tests for hardcoded credentials bug
        if bug_type == "hardcoded_credentials":
            if language == "python":
                tests.append({
                    "name": "test_no_hardcoded_credentials",
                    "type": "unit_test",
                    "language": language,
                    "code": f"""
def test_no_hardcoded_credentials(self):
    # Get the source code of the function
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
"""
                })
                
                tests.append({
                    "name": "test_environment_variable_usage",
                    "type": "unit_test",
                    "language": language,
                    "code": f"""
def test_environment_variable_usage(self):
    # Mock environment variables
    test_creds = "test_password"
    env_vars = {{"PASSWORD": test_creds, "API_KEY": "test_key"}}
    
    # Patch os.environ to return our test values
    with patch.dict('os.environ', env_vars):
        result = {function_name}()
        
        # Verify that the function returns a result using the environment variables
        self.assertIsNotNone(result, "Function should use environment variables and return a result")
"""
                })
        
        return tests
    
    def _generate_test_code(
        self,
        language: str,
        function_name: str,
        test_input: str,
        description: str
    ) -> str:
        """
        Generate test code for a specific language.
        
        Args:
            language: Programming language
            function_name: Name of the function to test
            test_input: Input to test with
            description: Description of the test
            
        Returns:
            Generated test code
        """
        if language == "python":
            return f"""
def test_{function_name}_with_{test_input.replace("'", "").replace("[", "").replace("]", "")}(self):
    \"\"\"Test {function_name} with {test_input} input. {description}\"\"\"
    try:
        result = {function_name}({test_input})
        # Function should handle the input without raising an exception
        self.assertTrue(True)  # If we get here, the test passes
    except Exception as e:
        self.fail(f"Function raised an exception with {test_input} input: {{e}}")
"""
        elif language in ["javascript", "typescript"]:
            return f"""
it('should handle {test_input} input correctly', () => {{
    // {description}
    expect(() => {function_name}({test_input})).to.not.throw();
}});
"""
        else:
            # Default to python if language is not supported
            return f"// Test {function_name} with {test_input} input - {description}"
