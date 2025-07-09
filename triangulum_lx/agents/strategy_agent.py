"""
Strategy Formulation Agent

This agent specializes in devising repair strategies for identified bugs.
It analyzes bug reports, code context, and historical patterns to formulate
an effective repair strategy with context-aware optimization and learning
from past successes and failures.
"""

import logging
import json
import os
import re
import ast
import datetime
import pickle
import statistics
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any, Optional, Union, Callable
from dataclasses import dataclass, field

from .base_agent import BaseAgent
from .message import AgentMessage, MessageType, ConfidenceLevel
# from .message_bus import MessageBus # Old
from .enhanced_message_bus import EnhancedMessageBus # New
from ..core.exceptions import TriangulumError

logger = logging.getLogger(__name__)

@dataclass
class StrategyPerformanceRecord:
    """Record of a strategy's performance over time."""
    strategy_id: str
    bug_type: str
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime.datetime] = None
    avg_confidence: float = 0.0
    verification_scores: List[float] = field(default_factory=list)
    implementation_times: List[float] = field(default_factory=list)
    code_contexts: List[str] = field(default_factory=list)
    
    @property
    def total_uses(self) -> int:
        """Get the total number of times this strategy was used."""
        return self.success_count + self.failure_count
    
    @property
    def success_rate(self) -> float:
        """Get the success rate of this strategy."""
        if self.total_uses == 0:
            return 0.0
        return self.success_count / self.total_uses
    
    def update_with_result(
        self, 
        success: bool, 
        confidence: float, 
        verification_score: Optional[float] = None,
        implementation_time: Optional[float] = None,
        code_context: Optional[str] = None
    ) -> None:
        """
        Update the performance record with a new result.
        
        Args:
            success: Whether the strategy was successful
            confidence: The confidence level assigned to the strategy
            verification_score: Score from verification (optional)
            implementation_time: Time taken to implement (optional)
            code_context: Context hash for the code (optional)
        """
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        self.last_used = datetime.datetime.now()
        
        # Update average confidence (weighted by number of uses)
        total = self.total_uses
        self.avg_confidence = ((self.avg_confidence * (total - 1)) + confidence) / total
        
        # Add optional metrics if provided
        if verification_score is not None:
            self.verification_scores.append(verification_score)
        
        if implementation_time is not None:
            self.implementation_times.append(implementation_time)
        
        if code_context is not None and code_context not in self.code_contexts:
            self.code_contexts.append(code_context)

@dataclass
class BugPatternRecord:
    """Record of a bug pattern's characteristics and frequency."""
    pattern_id: str
    occurrences: int = 0
    signatures: Set[str] = field(default_factory=set)
    successful_strategies: Dict[str, int] = field(default_factory=dict)
    code_contexts: Dict[str, int] = field(default_factory=dict)
    
    def add_occurrence(
        self, 
        signature: str, 
        code_context: Optional[str] = None,
        successful_strategy: Optional[str] = None
    ) -> None:
        """
        Add an occurrence of this bug pattern.
        
        Args:
            signature: Signature of the bug instance
            code_context: Context in which the bug occurred (optional)
            successful_strategy: ID of the strategy that fixed the bug (optional)
        """
        self.occurrences += 1
        self.signatures.add(signature)
        
        if code_context:
            self.code_contexts[code_context] = self.code_contexts.get(code_context, 0) + 1
        
        if successful_strategy:
            self.successful_strategies[successful_strategy] = self.successful_strategies.get(successful_strategy, 0) + 1


class StrategyAgent(BaseAgent):
    """
    Agent for formulating repair strategies for identified bugs.
    
    This agent takes bug reports and code context as input and produces
    detailed repair strategies as output, which can then be used by the
    Implementation Agent to create actual patches.
    """
    AGENT_TYPE = "strategy_agent" # Or "strategy_formulation" if that's the canonical type name

    def __init__(
        self,
        agent_id: Optional[str] = None,
        # agent_type: str = "strategy_formulation", # Use AGENT_TYPE
        message_bus: Optional[EnhancedMessageBus] = None,
        # subscribed_message_types: Optional[List[MessageType]] = None, # Define in super()
        config: Optional[Dict[str, Any]] = None,
        **kwargs # To catch other BaseAgent params
    ):
        """
        Initialize the Strategy Formulation Agent.
        
        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            message_bus: Enhanced message bus for agent communication
            config: Agent configuration dictionary
        """
        super().__init__(
            agent_id=agent_id,
            agent_type=self.AGENT_TYPE, # Use class variable
            message_bus=message_bus,
            subscribed_message_types=[ # Define directly
                MessageType.TASK_REQUEST,
                MessageType.QUERY,
                MessageType.TASK_RESULT,
                MessageType.STATUS_UPDATE
            ],
            config=config,
            **kwargs # Pass through
        )
        
        # Strategy templates indexed by bug type
        self.strategy_templates = self._load_strategy_templates()
        
        # Historical successful strategies
        self.successful_strategies: Dict[str, Dict[str, Any]] = {}
        
        # Performance records for strategies
        self.strategy_performance: Dict[str, StrategyPerformanceRecord] = {}
        
        # Bug pattern records
        self.bug_patterns: Dict[str, BugPatternRecord] = {}
        
        # Pattern recognizers (pattern_id -> function that checks if a bug matches the pattern)
        self.pattern_recognizers: Dict[str, Callable[[Dict[str, Any]], bool]] = self._load_pattern_recognizers()
        
        # Strategy generation hooks for different bug types
        self.strategy_generators: Dict[str, Callable[[Dict[str, Any], Dict[str, str], Dict[str, Any]], Dict[str, Any]]] = {}
        
        # Learning settings
        self.enable_learning = self.config.get("enable_learning", True)
        self.learning_data_path = self.config.get("learning_data_path", "data/strategy_learning")
        self.min_success_threshold = self.config.get("min_success_threshold", 0.6)
        self.context_similarity_threshold = self.config.get("context_similarity_threshold", 0.7)
        
        # Load saved learning data if available and learning is enabled
        if self.enable_learning:
            self._load_learning_data()
    
    def _load_pattern_recognizers(self) -> Dict[str, Callable[[Dict[str, Any]], bool]]:
        """
        Load pattern recognizers for bug classification.
        
        Returns:
            Dictionary mapping pattern IDs to recognizer functions
        """
        recognizers = {}
        
        # Null pointer recognizer
        def null_pointer_recognizer(bug_report: Dict[str, Any]) -> bool:
            # Check description for null/None reference indicators
            description = bug_report.get("description", "").lower()
            error_type = bug_report.get("error_type", "").lower()
            code = bug_report.get("code", "").lower()
            
            null_indicators = [
                "null", "none", "nil", "undefined", "nullpointer", 
                "nullreference", "nonetype", "is none", "is null", 
                "cannot read property", "null reference", "null object",
                "attributeerror", "typeerror"
            ]
            
            # Check for null indicators in description, error type, and code
            for indicator in null_indicators:
                if indicator in description or indicator in error_type:
                    return True
            
            # Check for common null reference patterns in code
            code_patterns = [
                r'(\w+)\s*\.\s*\w+',  # variable.property
                r'(\w+)\s*\[\s*',     # variable[
                r'(\w+)\s*\(\s*\)'    # variable()
            ]
            
            for pattern in code_patterns:
                matches = re.findall(pattern, code)
                for match in matches:
                    if match and "none" in code.lower() or "null" in code.lower():
                        return True
            
            return False
        
        recognizers["null_pointer"] = null_pointer_recognizer
        
        # Resource leak recognizer
        def resource_leak_recognizer(bug_report: Dict[str, Any]) -> bool:
            description = bug_report.get("description", "").lower()
            code = bug_report.get("code", "").lower()
            
            leak_indicators = [
                "leak", "resource", "not closed", "unclosed", "file", "connection",
                "stream", "socket", "handle", "descriptor", "resource leak",
                "memory leak", "open file", "close()", "dispose()", "release",
                "with open", "filenotclosederror"
            ]
            
            # Check for leak indicators in description
            for indicator in leak_indicators:
                if indicator in description:
                    return True
            
            # Check for resource usage without proper closing
            if ("open(" in code or ".open(" in code) and ".close()" not in code:
                return True
            
            return False
        
        recognizers["resource_leak"] = resource_leak_recognizer
        
        # SQL injection recognizer
        def sql_injection_recognizer(bug_report: Dict[str, Any]) -> bool:
            description = bug_report.get("description", "").lower()
            code = bug_report.get("code", "").lower()
            
            injection_indicators = [
                "sql injection", "sqli", "injection", "sql", "database", "query",
                "prepared statement", "parameterized", "sanitize", "escape",
                "user input", "unsafe query", "security", "vulnerability"
            ]
            
            # Check for injection indicators in description
            for indicator in injection_indicators:
                if indicator in description:
                    return True
            
            # Check for string concatenation in SQL queries
            sql_keywords = ["select ", "insert ", "update ", "delete ", "from ", "where "]
            has_sql = any(keyword in code for keyword in sql_keywords)
            
            if has_sql and ("+" in code or "%" in code or ".format" in code or "f\"" in code or "f'" in code):
                return True
            
            return False
        
        recognizers["sql_injection"] = sql_injection_recognizer
        
        # Hardcoded credentials recognizer
        def hardcoded_credentials_recognizer(bug_report: Dict[str, Any]) -> bool:
            description = bug_report.get("description", "").lower()
            code = bug_report.get("code", "").lower()
            
            credential_indicators = [
                "password", "credential", "api key", "secret", "hardcoded", "hard-coded",
                "key", "token", "auth", "authentication", "apikey", "security", 
                "pwd", "passwd"
            ]
            
            # Check for credential indicators in description
            for indicator in credential_indicators:
                if indicator in description:
                    return True
            
            # Check for credential patterns in code
            credential_patterns = [
                r'password\s*=\s*[\'"](.*?)[\'"]',
                r'api_?key\s*=\s*[\'"](.*?)[\'"]',
                r'secret\s*=\s*[\'"](.*?)[\'"]',
                r'token\s*=\s*[\'"](.*?)[\'"]',
                r'auth\w*\s*=\s*[\'"](.*?)[\'"]'
            ]
            
            for pattern in credential_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    return True
            
            return False
        
        recognizers["hardcoded_credentials"] = hardcoded_credentials_recognizer
        
        # Exception swallowing recognizer
        def exception_swallowing_recognizer(bug_report: Dict[str, Any]) -> bool:
            description = bug_report.get("description", "").lower()
            code = bug_report.get("code", "").lower()
            
            swallow_indicators = [
                "exception", "swallow", "silent", "catch", "ignore", "suppress",
                "empty catch", "bare except", "pass", "except:", "try-except",
                "try/except", "error handling", "exception handling"
            ]
            
            # Check for swallow indicators in description
            for indicator in swallow_indicators:
                if indicator in description:
                    return True
            
            # Check for bare except blocks in code
            has_try = "try:" in code or "try {" in code
            has_except = "except:" in code or "except " in code or "} catch" in code
            has_pass = "pass" in code or "{}" in code
            
            if has_try and has_except and has_pass:
                return True
            
            return False
        
        recognizers["exception_swallowing"] = exception_swallowing_recognizer
        
        return recognizers
    
    def _load_learning_data(self) -> None:
        """
        Load learning data from disk if available.
        """
        if not self.enable_learning:
            return
        
        # Create directory if it doesn't exist
        os.makedirs(self.learning_data_path, exist_ok=True)
        
        # Load strategy performance records
        perf_path = os.path.join(self.learning_data_path, "strategy_performance.pkl")
        if os.path.exists(perf_path):
            try:
                with open(perf_path, 'rb') as f:
                    self.strategy_performance = pickle.load(f)
                logger.info(f"Loaded {len(self.strategy_performance)} strategy performance records")
            except Exception as e:
                logger.error(f"Error loading strategy performance data: {e}")
        
        # Load bug pattern records
        patterns_path = os.path.join(self.learning_data_path, "bug_patterns.pkl")
        if os.path.exists(patterns_path):
            try:
                with open(patterns_path, 'rb') as f:
                    self.bug_patterns = pickle.load(f)
                logger.info(f"Loaded {len(self.bug_patterns)} bug pattern records")
            except Exception as e:
                logger.error(f"Error loading bug pattern data: {e}")
    
    def _save_learning_data(self) -> None:
        """
        Save learning data to disk.
        """
        if not self.enable_learning:
            return
        
        # Create directory if it doesn't exist
        os.makedirs(self.learning_data_path, exist_ok=True)
        
        # Save strategy performance records
        perf_path = os.path.join(self.learning_data_path, "strategy_performance.pkl")
        try:
            with open(perf_path, 'wb') as f:
                pickle.dump(self.strategy_performance, f)
            logger.info(f"Saved {len(self.strategy_performance)} strategy performance records")
        except Exception as e:
            logger.error(f"Error saving strategy performance data: {e}")
        
        # Save bug pattern records
        patterns_path = os.path.join(self.learning_data_path, "bug_patterns.pkl")
        try:
            with open(patterns_path, 'wb') as f:
                pickle.dump(self.bug_patterns, f)
            logger.info(f"Saved {len(self.bug_patterns)} bug pattern records")
        except Exception as e:
            logger.error(f"Error saving bug pattern data: {e}")
    
    def update_strategy_performance(
        self, 
        strategy_id: str,
        success: bool,
        confidence: float,
        bug_type: str,
        verification_score: Optional[float] = None,
        implementation_time: Optional[float] = None,
        code_context: Optional[str] = None
    ) -> None:
        """
        Update performance records for a strategy based on results.
        
        Args:
            strategy_id: ID of the strategy
            success: Whether the strategy was successful
            confidence: Confidence level assigned to the strategy
            bug_type: Type of bug the strategy addresses
            verification_score: Score from verification (optional)
            implementation_time: Time taken to implement (optional)
            code_context: Context hash for the code (optional)
        """
        if not self.enable_learning:
            return
        
        # Get or create performance record
        if strategy_id in self.strategy_performance:
            perf_record = self.strategy_performance[strategy_id]
        else:
            perf_record = StrategyPerformanceRecord(
                strategy_id=strategy_id,
                bug_type=bug_type
            )
            self.strategy_performance[strategy_id] = perf_record
        
        # Update the record
        perf_record.update_with_result(
            success=success,
            confidence=confidence,
            verification_score=verification_score,
            implementation_time=implementation_time,
            code_context=code_context
        )
        
        # Update bug pattern record if successful
        if success and bug_type in self.bug_patterns and code_context:
            self.bug_patterns[bug_type].add_occurrence(
                signature=f"strategy_{strategy_id}",
                code_context=code_context,
                successful_strategy=strategy_id
            )
        
        # Save the updated data
        self._save_learning_data()
    
    def _load_strategy_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Load strategy templates from the config or use default templates.
        
        Returns:
            Dictionary mapping bug types to strategy templates
        """
        # Load from config if available
        templates = self.config.get("strategy_templates", {})
        
        # If no templates in config, use default templates
        if not templates:
            templates = {
                "null_pointer": {
                    "name": "Null Reference Prevention",
                    "description": "Strategy to prevent null/None reference errors",
                    "steps": [
                        "Identify variables that could be null/None",
                        "Add null/None checks before accessing properties",
                        "Implement proper error handling for null cases",
                        "Consider using Optional/Nullable types where appropriate"
                    ],
                    "code_patterns": {
                        "python": [
                            "if {variable} is not None:\n    {access_property}",
                            "{variable} = {variable} or {default_value}",
                            "try:\n    {access_property}\nexcept AttributeError:\n    {handle_error}"
                        ],
                        "java": [
                            "if ({variable} != null) {\n    {access_property}\n}",
                            "{variable} = Optional.ofNullable({variable}).orElse({default_value});",
                            "try {\n    {access_property}\n} catch (NullPointerException e) {\n    {handle_error}\n}"
                        ]
                    }
                },
                "resource_leak": {
                    "name": "Resource Management",
                    "description": "Strategy to ensure proper resource cleanup",
                    "steps": [
                        "Identify resource acquisition points",
                        "Ensure resources are properly closed in all execution paths",
                        "Use language-specific resource management patterns",
                        "Consider centralizing resource management"
                    ],
                    "code_patterns": {
                        "python": [
                            "with open({filename}, {mode}) as {variable}:\n    {use_resource}",
                            "try:\n    {resource} = {acquire_resource}\n    {use_resource}\nfinally:\n    {resource}.close()"
                        ],
                        "java": [
                            "try ({resource_type} {variable} = new {resource_type}({params})) {\n    {use_resource}\n}",
                            "finally {\n    if ({resource} != null) {\n        {resource}.close();\n    }\n}"
                        ]
                    }
                },
                "sql_injection": {
                    "name": "SQL Injection Prevention",
                    "description": "Strategy to prevent SQL injection vulnerabilities",
                    "steps": [
                        "Identify dynamic SQL queries",
                        "Replace string concatenation with parameterized queries",
                        "Use prepared statements or ORM libraries",
                        "Validate and sanitize user input"
                    ],
                    "code_patterns": {
                        "python": [
                            "cursor.execute({query}, ({param1}, {param2}, ...))",
                            "cursor.execute({query}, {{'param1': {value1}, 'param2': {value2}, ...}})"
                        ],
                        "java": [
                            "PreparedStatement stmt = connection.prepareStatement({query});\nstmt.setString(1, {param1});\nstmt.setInt(2, {param2});\n// ...",
                            "Query query = entityManager.createQuery({query});\nquery.setParameter({param_name}, {param_value});"
                        ]
                    }
                },
                "hardcoded_credentials": {
                    "name": "Secure Credential Management",
                    "description": "Strategy to eliminate hardcoded credentials",
                    "steps": [
                        "Identify hardcoded credentials",
                        "Move credentials to environment variables or config files",
                        "Use secure credential storage solutions",
                        "Implement proper secret rotation mechanisms"
                    ],
                    "code_patterns": {
                        "python": [
                            "import os\n{variable} = os.environ.get('{ENV_VAR_NAME}')",
                            "from configparser import ConfigParser\nconfig = ConfigParser()\nconfig.read('config.ini')\n{variable} = config.get('section', '{key}')"
                        ],
                        "java": [
                            "String {variable} = System.getenv(\"{ENV_VAR_NAME}\");",
                            "Properties props = new Properties();\nprops.load(new FileInputStream(\"config.properties\"));\nString {variable} = props.getProperty(\"{key}\");"
                        ]
                    }
                },
                "exception_swallowing": {
                    "name": "Proper Exception Handling",
                    "description": "Strategy to implement proper exception handling",
                    "steps": [
                        "Identify swallowed exceptions",
                        "Add appropriate logging for exceptions",
                        "Implement proper error handling or propagation",
                        "Consider using custom exceptions for better error classification"
                    ],
                    "code_patterns": {
                        "python": [
                            "try:\n    {code}\nexcept {exception_type} as e:\n    logging.error(f\"Error: {e}\")\n    {handle_error}",
                            "try:\n    {code}\nexcept {exception_type} as e:\n    raise CustomException(f\"Error during operation: {e}\") from e"
                        ],
                        "java": [
                            "try {\n    {code}\n} catch ({exception_type} e) {\n    logger.error(\"Error: {}\", e.getMessage());\n    {handle_error}\n}",
                            "try {\n    {code}\n} catch ({exception_type} e) {\n    throw new CustomException(\"Error during operation\", e);\n}"
                        ]
                    }
                },
                "generic": {
                    "name": "Generic Bug Fix",
                    "description": "General strategy for fixing unclassified bugs",
                    "steps": [
                        "Understand the root cause of the bug",
                        "Develop a minimal fix that addresses the specific issue",
                        "Add tests to verify the fix and prevent regression",
                        "Refactor if necessary to prevent similar bugs"
                    ],
                    "code_patterns": {}
                }
            }
        
        return templates
    
    def formulate_strategy(
        self,
        bug_report: Dict[str, Any],
        code_context: Dict[str, Any],
        relationship_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Formulate a repair strategy for a specific bug.
        
        Args:
            bug_report: The bug report from the Bug Detector Agent
            code_context: The relevant code context for the bug
            relationship_context: Additional context about code relationships (optional)
            
        Returns:
            A repair strategy
        """
        # Determine the bug type
        bug_type = self._determine_bug_type(bug_report)
        
        # Get the appropriate strategy template
        template = self.strategy_templates.get(bug_type, self.strategy_templates["generic"])
        
        # Get the programming language
        language = code_context.get("language", "python")
        
        # Generate a repair strategy based on the template
        strategy = self._generate_strategy_from_template(
            template=template,
            bug_report=bug_report,
            code_context=code_context,
            relationship_context=relationship_context,
            language=language
        )
        
        return strategy
    
    def evaluate_strategy(
        self,
        strategy: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a repair strategy against a set of constraints.
        
        Args:
            strategy: The repair strategy to evaluate
            constraints: Constraints to evaluate against (optional)
            
        Returns:
            Evaluation results
        """
        if not constraints:
            constraints = {
                "max_complexity": 5,
                "max_changes": 10,
                "max_files": 3,
                "restricted_areas": []
            }
        
        # Estimate complexity (1-10 scale)
        complexity = self._estimate_complexity(strategy)
        
        # Estimate number of changes required
        changes = len(strategy.get("repair_steps", []))
        
        # Estimate number of files affected
        affected_files = len(strategy.get("affected_files", []))
        
        # Check if the strategy affects restricted areas
        restricted_impact = False
        for file in strategy.get("affected_files", []):
            for area in constraints.get("restricted_areas", []):
                if area in file:
                    restricted_impact = True
                    break
        
        # Calculate overall score (0-100)
        max_score = 100
        score = max_score
        
        if complexity > constraints.get("max_complexity", 5):
            score -= (complexity - constraints.get("max_complexity", 5)) * 10
        
        if changes > constraints.get("max_changes", 10):
            score -= (changes - constraints.get("max_changes", 10)) * 5
        
        if affected_files > constraints.get("max_files", 3):
            score -= (affected_files - constraints.get("max_files", 3)) * 10
        
        if restricted_impact:
            score -= 30
        
        score = max(0, score)
        
        # Determine if the strategy is acceptable
        acceptable = score >= 60
        
        return {
            "score": score,
            "acceptable": acceptable,
            "complexity": complexity,
            "changes": changes,
            "affected_files": affected_files,
            "restricted_impact": restricted_impact,
            "issues": [] if acceptable else ["Strategy too complex", "Too many changes", "Too many files affected"]
        }
    
    def _determine_bug_type(self, bug_report: Dict[str, Any]) -> str:
        """
        Determine the type of bug from a bug report.
        
        Args:
            bug_report: The bug report from the Bug Detector Agent
            
        Returns:
            The bug type
        """
        # If the bug report has a specific pattern_id, use that
        if "pattern_id" in bug_report:
            return bug_report["pattern_id"]
        
        # If there's an error type, try to match it to a bug type
        if "error_type" in bug_report:
            error_type = bug_report["error_type"].lower()
            if "null" in error_type or "none" in error_type or "reference" in error_type:
                return "null_pointer"
            elif "resource" in error_type or "io" in error_type or "file" in error_type:
                return "resource_leak"
            elif "sql" in error_type or "database" in error_type or "query" in error_type:
                return "sql_injection"
            elif "security" in error_type or "credential" in error_type or "password" in error_type:
                return "hardcoded_credentials"
            elif "exception" in error_type or "error" in error_type or "swallow" in error_type:
                return "exception_swallowing"
        
        # If there's a description, try to match it to a bug type
        if "description" in bug_report:
            description = bug_report["description"].lower()
            if "null" in description or "none" in description or "reference" in description:
                return "null_pointer"
            elif "resource" in description or "leak" in description or "close" in description:
                return "resource_leak"
            elif "sql" in description or "injection" in description or "query" in description:
                return "sql_injection"
            elif "hardcoded" in description or "credential" in description or "password" in description:
                return "hardcoded_credentials"
            elif "exception" in description or "swallow" in description or "catch" in description:
                return "exception_swallowing"
        
        # Default to generic
        return "generic"
    
    def _generate_strategy_from_template(
        self,
        template: Dict[str, Any],
        bug_report: Dict[str, Any],
        code_context: Dict[str, Any],
        relationship_context: Optional[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """
        Generate a repair strategy from a template.
        
        Args:
            template: The strategy template
            bug_report: The bug report from the Bug Detector Agent
            code_context: The relevant code context for the bug
            relationship_context: Additional context about code relationships
            language: The programming language
            
        Returns:
            A repair strategy
        """
        # Extract relevant information from the bug report
        bug_type = self._determine_bug_type(bug_report)
        bug_location = bug_report.get("file", "")
        bug_line = bug_report.get("line", 0)
        bug_code = bug_report.get("code", "")
        bug_description = bug_report.get("description", "")
        bug_severity = bug_report.get("severity", "medium")
        
        # Determine which files will be affected
        affected_files = [bug_location]
        if relationship_context:
            # Add related files based on relationship context
            for file, relationships in relationship_context.get("file_relationships", {}).items():
                if file == bug_location:
                    for related_file in relationships:
                        if related_file not in affected_files:
                            affected_files.append(related_file)
        
        # Get code patterns for the language
        code_patterns = template.get("code_patterns", {}).get(language, [])
        
        # Generate repair steps
        repair_steps = []
        for step in template.get("steps", []):
            repair_steps.append({
                "description": step,
                "completed": False
            })
        
        # Generate code examples if patterns are available
        code_examples = []
        if code_patterns and bug_code:
            for pattern in code_patterns:
                # Extract variable names from the bug code
                # This is a simple implementation - a real one would use more sophisticated parsing
                variables = self._extract_variables(bug_code)
                
                # Replace placeholders in the pattern with actual variable names
                example = pattern
                for i, var in enumerate(variables):
                    placeholder = f"{{variable{i+1}}}" if i > 0 else "{variable}"
                    example = example.replace(placeholder, var)
                
                # Add file operations placeholders if this is a resource leak
                if bug_type == "resource_leak":
                    example = example.replace("{filename}", f'"{bug_location}"')
                    example = example.replace("{mode}", "'r'")
                    example = example.replace("{use_resource}", "data = " + variables[0] + ".read()")
                
                code_examples.append(example)
        
        # Build the complete strategy
        strategy = {
            "id": f"strategy_{bug_type}_{hash(bug_location + str(bug_line))}",
            "name": template.get("name", "Generic Fix"),
            "description": template.get("description", ""),
            "bug_type": bug_type,
            "bug_location": bug_location,
            "bug_line": bug_line,
            "bug_code": bug_code,
            "bug_description": bug_description,
            "bug_severity": bug_severity,
            "affected_files": affected_files,
            "repair_steps": repair_steps,
            "code_examples": code_examples,
            "estimated_complexity": self._estimate_complexity({"repair_steps": repair_steps, "affected_files": affected_files}),
            "confidence": self._calculate_confidence(bug_report, template),
            "timestamp": self._get_timestamp()
        }
        
        return strategy
    
    def _extract_variables(self, code: str) -> List[str]:
        """
        Extract variable names from a code snippet.
        
        Args:
            code: The code snippet
            
        Returns:
            List of variable names
        """
        # This is a simple implementation - a real one would use more sophisticated parsing
        import re
        
        variables = []
        
        # Find variable assignments
        assignment_pattern = r'(\w+)\s*='
        for match in re.finditer(assignment_pattern, code):
            variables.append(match.group(1))
        
        # Find function parameters
        function_pattern = r'def\s+\w+\(([^)]*)\)'
        for match in re.finditer(function_pattern, code):
            params = match.group(1).split(',')
            for param in params:
                param = param.strip()
                if param and param != 'self':
                    if ':' in param:  # Type annotations
                        param = param.split(':')[0].strip()
                    if '=' in param:  # Default values
                        param = param.split('=')[0].strip()
                    variables.append(param)
        
        # If no variables found, use generic names
        if not variables:
            variables = ["variable", "data", "resource"]
        
        return variables
    
    def _estimate_complexity(self, strategy: Dict[str, Any]) -> int:
        """
        Estimate the complexity of a repair strategy on a scale of 1-10.
        
        Args:
            strategy: The repair strategy
            
        Returns:
            Complexity score (1-10)
        """
        base_complexity = 1
        
        # Add complexity based on number of repair steps
        steps = len(strategy.get("repair_steps", []))
        if steps <= 2:
            base_complexity += 1
        elif steps <= 4:
            base_complexity += 2
        else:
            base_complexity += 3
        
        # Add complexity based on number of affected files
        files = len(strategy.get("affected_files", []))
        if files > 1:
            base_complexity += files - 1
        
        # Cap at 10
        return min(10, base_complexity)
    
    def _calculate_confidence(
        self,
        bug_report: Dict[str, Any],
        template: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence level for the strategy.
        
        Args:
            bug_report: The bug report
            template: The strategy template
            
        Returns:
            Confidence score between 0 and 1
        """
        # Start with a base confidence
        base_confidence = 0.7
        
        # Adjust based on the bug report's confidence (if available)
        if "confidence" in bug_report:
            base_confidence = bug_report["confidence"]
        
        # Adjust based on the bug type match
        bug_type = self._determine_bug_type(bug_report)
        if bug_type == "generic":
            base_confidence *= 0.8  # Less confident for generic bugs
        
        # Adjust based on the template's completeness
        if not template.get("code_patterns", {}):
            base_confidence *= 0.9  # Less confident without code patterns
        
        # Clamp to [0.1, 0.95] range
        return max(0.1, min(0.95, base_confidence))
    
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
        
        if action == "formulate_strategy":
            bug_report = content.get("bug_report")
            code_context = content.get("code_context")
            relationship_context = content.get("relationship_context")
            
            if not bug_report or not code_context:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": "bug_report and code_context are required"
                    }
                )
                return
            
            try:
                strategy = self.formulate_strategy(
                    bug_report=bug_report,
                    code_context=code_context,
                    relationship_context=relationship_context
                )
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.TASK_RESULT,
                    content={
                        "status": "success",
                        "strategy": strategy
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
        
        elif action == "evaluate_strategy":
            strategy = content.get("strategy")
            constraints = content.get("constraints")
            
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
                evaluation = self.evaluate_strategy(
                    strategy=strategy,
                    constraints=constraints
                )
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.TASK_RESULT,
                    content={
                        "status": "success",
                        "evaluation": evaluation
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
        
        if query_type == "get_strategy_templates":
            bug_type = content.get("bug_type")
            
            try:
                if bug_type:
                    template = self.strategy_templates.get(bug_type)
                    if template:
                        templates = {bug_type: template}
                    else:
                        templates = {}
                else:
                    templates = self.strategy_templates
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.QUERY_RESPONSE,
                    content={
                        "status": "success",
                        "templates": templates,
                        "template_count": len(templates)
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
        
        elif query_type == "get_successful_strategies":
            bug_type = content.get("bug_type")
            
            try:
                if bug_type:
                    strategies = {k: v for k, v in self.successful_strategies.items() if v.get("bug_type") == bug_type}
                else:
                    strategies = self.successful_strategies
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.QUERY_RESPONSE,
                    content={
                        "status": "success",
                        "strategies": strategies,
                        "strategy_count": len(strategies)
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
            
            # If it's a verification result for one of our strategies, update our knowledge
            if "verification_result" in content and "strategy_id" in content:
                strategy_id = content["strategy_id"]
                success = content.get("success", False)
                
                if success and strategy_id in self.successful_strategies:
                    # If the strategy was successful, mark it as verified
                    self.successful_strategies[strategy_id]["verified"] = True
        
        # Let the base class handle other message types
        super()._handle_other_message(message)
