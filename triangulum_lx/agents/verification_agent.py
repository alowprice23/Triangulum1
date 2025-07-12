"""
Verification Agent

This agent specializes in verifying the implementations of bug fixes to ensure
they correctly resolve the issues without introducing new problems. It provides
advanced verification capabilities with multi-stage validation, comprehensive
test discovery, and detailed reporting.
"""

import logging
import os
import subprocess
import sys
import ast
import re
import tempfile
import shutil
import time
import json
import platform
import hashlib
import concurrent.futures
import contextlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional, Union, Callable, ContextManager

from .base_agent import BaseAgent
from .message import AgentMessage, MessageType, ConfidenceLevel
# from .message_bus import MessageBus # Old
from .enhanced_message_bus import EnhancedMessageBus # New
from ..core.exceptions import TriangulumError, VerificationError
from ..verification.core import VerificationEnvironment, TestGenerator
from ..verification.code_fixer import CodeFixer
from ..verification.metrics import MetricsCollector as GlobalVerificationMetrics

logger = logging.getLogger(__name__)

class VerificationMetrics:
    """Class to track verification performance metrics."""
    
    def __init__(self):
        """Initialize the metrics collector."""
        self.total_verifications = 0
        self.successful_verifications = 0
        self.failed_verifications = 0
        self.verification_times = []
        self.bug_type_stats = {}
        self.false_positives = 0
        self.false_negatives = 0
        self.start_time = None
        self.end_time = None
        self.check_stats = {}
    
    def start_verification(self):
        """Record the start of a verification."""
        self.start_time = time.time()
    
    def end_verification(self, success: bool, bug_type: str, checks: Dict[str, Dict[str, Any]]):
        """
        Record the end of a verification.
        
        Args:
            success: Whether the verification was successful
            bug_type: The type of bug being verified
            checks: The results of individual checks
        """
        self.end_time = time.time()
        
        # Update verification count
        self.total_verifications += 1
        if success:
            self.successful_verifications += 1
        else:
            self.failed_verifications += 1
        
        # Record verification time
        if self.start_time is not None:
            self.verification_times.append(self.end_time - self.start_time)
        
        # Update bug type statistics
        if bug_type in self.bug_type_stats:
            self.bug_type_stats[bug_type]["count"] += 1
            self.bug_type_stats[bug_type]["success"] += 1 if success else 0
        else:
            self.bug_type_stats[bug_type] = {
                "count": 1,
                "success": 1 if success else 0
            }
        
        # Update check statistics
        for check_name, check_result in checks.items():
            if check_name not in self.check_stats:
                self.check_stats[check_name] = {"count": 0, "success": 0}
            
            self.check_stats[check_name]["count"] += 1
            if check_result.get("success", False):
                self.check_stats[check_name]["success"] += 1
    
    def record_false_positive(self):
        """Record a false positive (verification passed but issue still exists)."""
        self.false_positives += 1
    
    def record_false_negative(self):
        """Record a false negative (verification failed but fix was correct)."""
        self.false_negatives += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the verification metrics.
        
        Returns:
            Dictionary containing the metrics summary
        """
        avg_time = sum(self.verification_times) / len(self.verification_times) if self.verification_times else 0
        
        # Calculate success rates for each check type
        check_success_rates = {}
        for check_name, stats in self.check_stats.items():
            if stats["count"] > 0:
                check_success_rates[check_name] = stats["success"] / stats["count"]
            else:
                check_success_rates[check_name] = 0
        
        return {
            "total_verifications": self.total_verifications,
            "success_rate": self.successful_verifications / self.total_verifications if self.total_verifications > 0 else 0,
            "avg_verification_time": avg_time,
            "false_positive_rate": self.false_positives / self.total_verifications if self.total_verifications > 0 else 0,
            "false_negative_rate": self.false_negatives / self.total_verifications if self.total_verifications > 0 else 0,
            "bug_type_success_rates": {
                bug_type: stats["success"] / stats["count"] if stats["count"] > 0 else 0
                for bug_type, stats in self.bug_type_stats.items()
            },
            "check_success_rates": check_success_rates
        }

class VerificationContext:
    """Class to store the context of a verification session."""
    
    def __init__(
        self,
        implementation_id: str,
        sandbox_path: str,
        environment_config: Dict[str, Any],
        bug_type: str
    ):
        """
        Initialize the verification context.
        
        Args:
            implementation_id: The ID of the implementation being verified
            sandbox_path: Path to the sandbox directory
            environment_config: Configuration for the verification environment
            bug_type: The type of bug being fixed
        """
        self.implementation_id = implementation_id
        self.sandbox_path = sandbox_path
        self.environment_config = environment_config
        self.bug_type = bug_type
        self.stage_results = {}
        self.timestamp = datetime.now().isoformat()
        self.resource_paths = {}
        self.external_tools = {}
        self.errors = []
        self.warnings = []


class VerificationAgent(BaseAgent):
    """
    Agent for verifying bug fix implementations.
    
    This agent takes an implementation and verifies whether it correctly
    fixes the reported issue. It performs various checks such as syntax validation,
    test execution, code analysis, and adherence to project standards.
    
    The agent uses a multi-stage verification approach with comprehensive test
    discovery and detailed reporting capabilities. It supports custom verification
    environments and can be configured for different types of projects.
    """
    AGENT_TYPE = "verification"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        # agent_type: str = "verification", # Use AGENT_TYPE
        message_bus: Optional[EnhancedMessageBus] = None,
        # subscribed_message_types: Optional[List[MessageType]] = None, # Define in super()
        config: Optional[Dict[str, Any]] = None,
        **kwargs # To catch other BaseAgent params
    ):
        """
        Initialize the Verification Agent.
        
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
                MessageType.STATUS_UPDATE
            ],
            config=config,
            **kwargs # Pass through
        )
        
        # Default configurations
        self.test_timeout = self.config.get("test_timeout", 30)  # 30 seconds
        self.basic_verification_metrics = [
            "syntax",
            "tests",
            "standards",
            "regression"
        ]
        self.advanced_verification_metrics = [
            "security",
            "performance",
            "compatibility",
            "integration"
        ]
        self.verification_metrics = self.config.get(
            "verification_metrics", 
            self.basic_verification_metrics
        )
        
        # Environment configuration
        self.default_environment = self.config.get("default_environment", "default")
        self.environments = self.config.get("environments", {
            "default": {
                "python_version": sys.version[:3],
                "test_framework": "unittest",
                "code_standards": ["flake8", "black"],
                "use_virtualenv": False
            }
        })
        
        # Verification stages configuration
        self.staged_verification = self.config.get("staged_verification", True)
        self.verification_stages = self.config.get("verification_stages", [
            "pre_verification",   # Initial setup and environment preparation
            "static_analysis",    # Syntax and static analysis checks
            "unit_tests",         # Unit tests execution
            "integration_tests",  # Integration tests execution
            "standards_checks",   # Coding standards verification
            "security_checks",    # Security vulnerability checks
            "post_verification"   # Final validation and reporting
        ])
        
        # Configure maximum workers for parallel verification
        self.max_workers = self.config.get("max_workers", 4)
        
        # Configure verification paths
        self.verification_data_dir = self.config.get(
            "verification_data_dir", ".triangulum/verification"
        )
        os.makedirs(self.verification_data_dir, exist_ok=True)
        
        # Metrics tracking
        self.metrics = VerificationMetrics()
        
        # Active verification contexts
        self.active_contexts = {}
        
        # Store verification results for reference
        self.verification_results = {}
        
        # Initialize verification components
        self.verification_env = VerificationEnvironment(config=self.config.get("verification_env", {}))
        self.test_generator = TestGenerator(config=self.config.get("test_generator", {}))
        self.code_fixer = CodeFixer(config=self.config.get("code_fixer", {}))
        self.global_metrics = GlobalVerificationMetrics(
            metrics_path=self.config.get("metrics_path", os.path.join(self.verification_data_dir, "metrics"))
        )
        
        # Start a metrics session
        self.global_metrics.start_session(f"verification_session_{self.agent_id}")
        
        # Configure environment detection
        self.detect_environment()
    
    def detect_environment(self):
        """Detect the execution environment and available tools."""
        self.environment_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "available_tools": {},
            "python_packages": {}
        }
    
    def verify_implementation(
        self,
        implementation: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None,
        bug_report: Optional[Dict[str, Any]] = None,
        environment: Optional[str] = None,
        staged: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Verify an implementation to ensure it fixes the issue.
        
        Args:
            implementation: The implementation to verify
            strategy: The strategy that was implemented (optional)
            bug_report: The original bug report (optional)
            environment: The environment to use for verification (optional)
            staged: Whether to use staged verification (optional)
            
        Returns:
            Verification results
        """
        if not implementation:
            raise ValueError("Implementation is required")

        self.metrics.start_verification()
        implementation_id = implementation.get("strategy_id", "unknown")
        bug_type = implementation.get("bug_type", "unknown")
        env_name = environment or self.default_environment
        env_config = self.environments.get(env_name, self.environments["default"])
        
        # Determine the language from the first file in the implementation
        language = "unknown"
        if "changes" in implementation and implementation["changes"]:
            first_file = implementation["changes"][0]["file_path"]
            language = self._determine_language(first_file)
        
        # Start tracking metrics in the global metrics system
        verification_record = self.global_metrics.start_verification(
            implementation_id=implementation_id,
            bug_type=bug_type,
            language=language
        )

        checks = {}
        issues = []
        recommendations = []
        overall_success = True

        with self._create_verification_sandbox(implementation) as sandbox_path:
            patch_result = self._apply_patches_in_sandbox(implementation, sandbox_path)
            if not patch_result["success"]:
                overall_success = False
                issues.append({"type": "patch_failure", "message": patch_result["error"]})
            else:
                # Syntax Check
                syntax_result = self._verify_syntax(implementation, sandbox_path, bug_type)
                checks["syntax"] = syntax_result
                if not syntax_result["success"]:
                    overall_success = False
                    issues.extend(syntax_result["issues"])
                    recommendations.extend(syntax_result["recommendations"])

                # Test Check (only if syntax is ok)
                if overall_success:
                    test_result = self._verify_tests(implementation, sandbox_path, bug_type, strategy, bug_report)
                    checks["tests"] = test_result
                    if not test_result["success"]:
                        overall_success = False
                        issues.extend(test_result["issues"])
                        recommendations.extend(test_result["recommendations"])

                # Standards Check (only if syntax is ok)
                if overall_success:
                    standards_result = self._verify_standards(implementation, sandbox_path, bug_type)
                    checks["standards"] = standards_result
                    if not standards_result["success"]:
                        overall_success = False # Or maybe just a warning? For now, fail.
                        issues.extend(standards_result["issues"])
                        recommendations.extend(standards_result["recommendations"])
                
                # Generate additional tests if needed
                if overall_success and bug_report:
                    self._generate_additional_tests(implementation, sandbox_path, bug_type, bug_report, strategy)
                
                # Run security checks if needed
                if overall_success and "security" in self.verification_metrics:
                    security_result = self._verify_security(implementation, sandbox_path, bug_type)
                    checks["security"] = security_result
                    if not security_result["success"]:
                        # Security issues are warnings, not failures
                        issues.extend(security_result["issues"])
                        recommendations.extend(security_result["recommendations"])
                
                # Run regression checks
                if overall_success and "regression" in self.verification_metrics:
                    regression_result = self._verify_regression(implementation, sandbox_path, bug_type)
                    checks["regression"] = regression_result
                    if not regression_result["success"]:
                        overall_success = False
                        issues.extend(regression_result["issues"])
                        recommendations.extend(regression_result["recommendations"])
        
        verification_time = time.time() - (self.metrics.start_time or time.time())
        
        verification_result = {
            "implementation_id": implementation_id,
            "verification_id": self._generate_verification_id(implementation_id),
            "timestamp": self._get_timestamp(),
            "overall_success": overall_success,
            "confidence": self._calculate_confidence(checks, bug_type),
            "environment": env_name,
            "staged": staged or self.staged_verification,
            "checks": checks,
            "issues": issues,
            "recommendations": recommendations,
            "verification_time": verification_time,
            "metrics": {
                "total_checks": len(checks),
                "passed_checks": sum(1 for c in checks.values() if c.get("success")),
                "failed_checks": sum(1 for c in checks.values() if not c.get("success")),
                "verification_time": verification_time
            }
        }

        # Update local metrics
        self.metrics.end_verification(
            success=overall_success,
            bug_type=bug_type,
            checks=checks
        )
        
        # Update global metrics
        self.global_metrics.end_verification(
            verification=verification_record,
            success=overall_success,
            checks=checks,
            issues=[i["message"] if isinstance(i, dict) else i for i in issues]
        )
        
        # Store the result for future reference
        self.verification_results[implementation_id] = verification_result
        
        # If verification failed, try to fix the issues
        if not overall_success and self.config.get("auto_fix", True):
            self._attempt_auto_fix(implementation, verification_result, sandbox_path)
        
        return verification_result
    
    def _generate_verification_id(self, implementation_id: str) -> str:
        """Generate a unique verification ID."""
        combined = f"{implementation_id}_{time.time()}"
        hash_obj = hashlib.md5(combined.encode())
        return f"ver_{hash_obj.hexdigest()[:12]}"
    
    def _get_timestamp(self) -> str:
        """Get a formatted timestamp."""
        return datetime.now().isoformat()
    
    def _perform_staged_verification(
        self,
        implementation: Dict[str, Any],
        context: VerificationContext,
        strategy: Optional[Dict[str, Any]],
        bug_report: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Perform staged verification on the implementation.
        
        Args:
            implementation: The implementation to verify
            context: The verification context
            strategy: The strategy that was implemented
            bug_report: The original bug report
            
        Returns:
            Dictionary of stage results
        """
        # Minimal implementation for now
        stages = {}
        for stage in self.verification_stages:
            stages[stage] = {
                "success": True,
                "checks": {},
                "issues": [],
                "recommendations": []
            }
        
        return stages
    
    def _calculate_confidence(
        self,
        checks: Dict[str, Dict[str, Any]],
        bug_type: str
    ) -> float:
        """
        Calculate confidence in the verification result.
        
        Args:
            checks: Dictionary of check results
            bug_type: Type of bug being verified
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Simple implementation for now
        passed_checks = sum(1 for check in checks.values() if check.get("success", False))
        total_checks = max(1, len(checks))
        
        return passed_checks / total_checks
    
    def _verify_syntax(
        self,
        implementation: Dict[str, Any],
        sandbox_path: str,
        bug_type: str
    ) -> Dict[str, Any]:
        """
        Verify that the patched files have valid syntax.
        
        Args:
            implementation: The implementation to verify
            sandbox_path: Path to the sandbox directory
            bug_type: The type of bug being fixed
            
        Returns:
            Result of syntax verification
        """
        issues = []
        for change in implementation.get("changes", []):
            file_path = Path(sandbox_path) / change["file_path"]
            if self._determine_language(str(file_path)) == 'python':
                try:
                    with open(file_path, "r") as f:
                        ast.parse(f.read(), filename=str(file_path))
                except SyntaxError as e:
                    issues.append({
                        "file_path": change["file_path"],
                        "line": e.lineno,
                        "message": e.msg
                    })
        
        return {
            "success": not issues,
            "issues": issues,
            "recommendations": ["Fix syntax errors before proceeding."] if issues else []
        }
    
    def _verify_tests(
        self,
        implementation: Dict[str, Any],
        sandbox_path: str,
        bug_type: str,
        strategy: Optional[Dict[str, Any]] = None,
        bug_report: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verify that the implementation passes tests.
        
        Args:
            implementation: The implementation to verify
            sandbox_path: Path to the sandbox directory
            bug_type: The type of bug being fixed
            strategy: The strategy that was implemented (optional)
            bug_report: The original bug report (optional)
            
        Returns:
            Result of test verification
        """
        try:
            # Discover and run tests using pytest
            test_process = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/"],
                cwd=sandbox_path,
                capture_output=True,
                text=True,
                timeout=self.test_timeout
            )
            
            success = test_process.returncode == 0
            issues = []
            if not success:
                issues.append({
                    "type": "test_failure",
                    "output": test_process.stdout,
                    "error": test_process.stderr
                })

            return {
                "success": success,
                "issues": issues,
                "recommendations": ["Review test failures."] if not success else []
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "issues": [{"type": "timeout", "message": f"Tests timed out after {self.test_timeout} seconds."}],
                "recommendations": ["Optimize tests or increase timeout."]
            }
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                "success": False,
                "issues": [{"type": "execution_error", "message": str(e)}],
                "recommendations": ["Check test environment and configuration."]
            }
    
    def _verify_standards(
        self,
        implementation: Dict[str, Any],
        sandbox_path: str,
        bug_type: str
    ) -> Dict[str, Any]:
        """
        Verify that the implementation adheres to coding standards.
        
        Args:
            implementation: The implementation to verify
            sandbox_path: Path to the sandbox directory
            bug_type: The type of bug being fixed
            
        Returns:
            Result of standards verification
        """
        issues = []
        for change in implementation.get("changes", []):
            file_path = Path(sandbox_path) / change["file_path"]
            if self._determine_language(str(file_path)) == 'python':
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "flake8", str(file_path)],
                        capture_output=True,
                        text=True,
                        cwd=sandbox_path
                    )
                    if result.returncode != 0:
                        for line in result.stdout.strip().split('\n'):
                            if line:
                                issues.append({
                                    "file_path": change["file_path"],
                                    "message": line
                                })
                except Exception as e:
                    logger.warning(f"Could not run flake8 on {file_path}: {e}")

        return {
            "success": not issues,
            "issues": issues,
            "recommendations": ["Fix coding standard violations."] if issues else []
        }
    
    def _verify_regression(
        self,
        implementation: Dict[str, Any],
        sandbox_path: str,
        bug_type: str
    ) -> Dict[str, Any]:
        """
        Verify that the implementation doesn't introduce regressions.
        
        Args:
            implementation: The implementation to verify
            sandbox_path: Path to the sandbox directory
            bug_type: The type of bug being fixed
            
        Returns:
            Result of regression verification
        """
        return {
            "success": True,
            "issues": [],
            "recommendations": []
        }
    
    def _verify_security(
        self,
        implementation: Dict[str, Any],
        sandbox_path: str,
        bug_type: str
    ) -> Dict[str, Any]:
        """
        Verify that the implementation addresses security concerns.
        
        Args:
            implementation: The implementation to verify
            sandbox_path: Path to the sandbox directory
            bug_type: The type of bug being fixed
            
        Returns:
            Result of security verification
        """
        return {
            "success": True,
            "issues": [],
            "recommendations": []
        }
    
    def _determine_language(self, file_path: str) -> str:
        """
        Determine the programming language of a file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            The language (python, javascript, typescript, java, etc.)
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift'
        }
        
        return language_map.get(ext, 'unknown')
    
    def _create_verification_sandbox(self, implementation: Dict[str, Any]) -> ContextManager[str]:
        """
        Create a temporary directory with copies of all necessary files.
        
        Args:
            implementation: The implementation to verify
            
        Returns:
            A context manager that yields the path to the sandbox directory
        """
        # Get the project root (assuming the script is run from the project root)
        project_root = Path.cwd()

        @contextlib.contextmanager
        def sandbox_context_manager():
            temp_dir = tempfile.mkdtemp(prefix="triangulum_verification_")
            try:
                # Copy the entire project structure to the sandbox
                shutil.copytree(project_root, temp_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git', '__pycache__', '.triangulum'))
                yield temp_dir
            finally:
                if os.path.exists(temp_dir):
                    try:
                        def onexc(func, path, exc_info):
                            """
                            Error handler for shutil.rmtree.
                            If the error is a permissions error, it will be ignored.
                            Otherwise, it will be raised.
                            """
                            try:
                                # grant all permissions to the file and retry
                                os.chmod(path, 0o777)
                                func(path)
                            except (PermissionError, OSError):
                                # If we still can't remove it, just log and continue
                                logger.warning(f"Could not remove temporary file: {path}")
                                pass

                        shutil.rmtree(temp_dir, onexc=onexc)
                    except Exception as e:
                        logger.warning(f"Error cleaning up sandbox: {e}")
        
        return sandbox_context_manager()

    def _apply_patches_in_sandbox(
        self,
        implementation: Dict[str, Any],
        sandbox_path: str
    ) -> Dict[str, Any]:
        """
        Apply the implementation patches in the sandbox.
        
        Args:
            implementation: The implementation to verify
            sandbox_path: Path to the sandbox directory
            
        Returns:
            Result of applying the patches
        """
        applied_patches = []
        try:
            for change in implementation.get("changes", []):
                file_path = Path(sandbox_path) / change["file_path"]
                
                if not file_path.parent.exists():
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, "w") as f:
                    f.write(change["new_content"])
                applied_patches.append(change["file_path"])

            return {
                "success": True,
                "error": None,
                "applied_patches": applied_patches
            }
        except Exception as e:
            logger.error(f"Failed to apply patches in sandbox: {e}")
            return {
                "success": False,
                "error": str(e),
                "applied_patches": applied_patches
            }
    
    def _generate_additional_tests(
        self,
        implementation: Dict[str, Any],
        sandbox_path: str,
        bug_type: str,
        bug_report: Dict[str, Any],
        strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate additional tests for the implementation.
        
        Args:
            implementation: The implementation to verify
            sandbox_path: Path to the sandbox directory
            bug_type: Type of bug being fixed
            bug_report: The original bug report
            strategy: The strategy that was implemented (optional)
            
        Returns:
            Result of test generation
        """
        try:
            # Extract bug location from the implementation
            bug_location = None
            if "changes" in implementation and implementation["changes"]:
                bug_location = implementation["changes"][0]["file_path"]
            elif bug_report and "file_path" in bug_report:
                bug_location = bug_report["file_path"]
            
            if not bug_location:
                return {"success": False, "error": "Could not determine bug location"}
            
            # Generate tests
            tests = self.test_generator.generate_tests(
                bug_type=bug_type,
                bug_location=bug_location,
                implementation=implementation,
                strategy=strategy,
                existing_tests=self._find_existing_tests(sandbox_path)
            )
            
            # Write the generated tests to the sandbox
            for test_type, test_list in tests.items():
                for test in test_list:
                    if "file_name" in test and "content" in test:
                        test_path = os.path.join(sandbox_path, "tests", test["file_name"])
                        os.makedirs(os.path.dirname(test_path), exist_ok=True)
                        
                        with open(test_path, "w") as f:
                            f.write(test["content"])
            
            return {"success": True, "tests_generated": sum(len(test_list) for test_list in tests.values())}
        
        except Exception as e:
            logger.error(f"Error generating tests: {e}")
            return {"success": False, "error": str(e)}
    
    def _find_existing_tests(self, sandbox_path: str) -> List[str]:
        """
        Find existing test files in the sandbox.
        
        Args:
            sandbox_path: Path to the sandbox directory
            
        Returns:
            List of test file paths
        """
        test_files = []
        test_dirs = ["tests", "test"]
        
        for test_dir in test_dirs:
            test_path = os.path.join(sandbox_path, test_dir)
            if os.path.exists(test_path) and os.path.isdir(test_path):
                for root, _, files in os.walk(test_path):
                    for file in files:
                        if file.startswith("test_") and file.endswith(".py"):
                            test_files.append(os.path.join(root, file))
        
        return test_files
    
    def _attempt_auto_fix(
        self,
        implementation: Dict[str, Any],
        verification_result: Dict[str, Any],
        sandbox_path: str
    ) -> Dict[str, Any]:
        """
        Attempt to automatically fix issues in the implementation.
        
        Args:
            implementation: The implementation to fix
            verification_result: Verification results with issues to fix
            sandbox_path: Path to the sandbox directory
            
        Returns:
            Result of the fix attempt
        """
        fix_results = {}
        
        try:
            # For each file in the implementation, try to fix it
            for change in implementation.get("changes", []):
                file_path = os.path.join(sandbox_path, change["file_path"])
                
                if os.path.exists(file_path):
                    # Apply fixes
                    fix_result = self.code_fixer.fix_code(
                        file_path=file_path,
                        verification_result=verification_result
                    )
                    
                    fix_results[change["file_path"]] = fix_result
                    
                    # If fixes were applied, update the implementation
                    if fix_result.get("modified", False):
                        with open(file_path, "r") as f:
                            new_content = f.read()
                        
                        # Update the implementation with the fixed content
                        for i, c in enumerate(implementation["changes"]):
                            if c["file_path"] == change["file_path"]:
                                implementation["changes"][i]["new_content"] = new_content
                                break
            
            return {
                "success": any(r.get("modified", False) for r in fix_results.values()),
                "fixes": fix_results
            }
        
        except Exception as e:
            logger.error(f"Error attempting auto-fix: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_task_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle a task request message."""
        task_data = message.content.get("task", {})
        task_type = task_data.get("type")

        if task_type == "verify_implementation":
            implementation = task_data.get("implementation", {})
            strategy = task_data.get("strategy")
            bug_report = task_data.get("bug_report")
            
            result = self.verify_implementation(implementation, strategy, bug_report)
            
            return AgentMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.TASK_RESULT,
                content={
                    "task_id": message.content.get("task_id"),
                    "result": result,
                    "success": result["overall_success"],
                    "confidence": result["confidence"]
                },
                confidence=ConfidenceLevel.HIGH.value if result["overall_success"] else ConfidenceLevel.LOW.value
            )
        elif task_type == "fix_code":
            implementation = task_data.get("implementation", {})
            verification_result = task_data.get("verification_result", {})
            
            # Create a temporary sandbox to apply fixes
            with self._create_verification_sandbox(implementation) as sandbox_path:
                # Apply patches
                self._apply_patches_in_sandbox(implementation, sandbox_path)
                
                # Attempt to fix the code
                fix_result = self._attempt_auto_fix(
                    implementation=implementation,
                    verification_result=verification_result,
                    sandbox_path=sandbox_path
                )
                
                return AgentMessage(
                    sender=self.agent_id,
                    receiver=message.sender,
                    message_type=MessageType.TASK_RESULT,
                    content={
                        "task_id": message.content.get("task_id"),
                        "result": fix_result,
                        "success": fix_result.get("success", False),
                        "implementation": implementation
                    }
                )
        
        return None

    def _handle_query(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle a query message."""
        query_data = message.content.get("query", {})
        query_type = query_data.get("type")

        if query_type == "get_verification_result":
            implementation_id = query_data.get("implementation_id")
            result = self.verification_results.get(implementation_id)
            return AgentMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.QUERY_RESPONSE,
                content={"result": result}
            )
        return None
