"""
Python-specific verification plugins for VerifyX.

This module contains verification plugins for Python code, including syntax checking,
security scanning, and style checking.
"""

import ast
import logging
import time
import re
from typing import Dict, Any, List, Optional

from ..core import (
    VerifierPlugin,
    VerificationContext,
    CodeArtifact,
    VerificationResult,
    VerificationStatus,
    MetricDefinition
)
from ..metrics import MetricsCollector

logger = logging.getLogger(__name__)


class PythonSyntaxVerifier(VerifierPlugin):
    """
    Verifies Python code for syntax errors.
    
    This plugin uses Python's built-in abstract syntax tree (AST) parser to
    check if the code is syntactically valid.
    """
    
    def __init__(self, context: VerificationContext):
        """
        Initialize the Python syntax verifier.
        
        Args:
            context: The verification context
        """
        super().__init__(context)
        self.metrics_collector = MetricsCollector(namespace="verification.python.syntax")
    
    async def verify(self, artifact: CodeArtifact) -> VerificationResult:
        """
        Verify the Python code for syntax errors.
        
        Args:
            artifact: The code artifact to verify
            
        Returns:
            The verification result
        """
        logger.info(f"Verifying Python syntax for {artifact.file_path}")
        
        start_time = time.time()
        issues = []
        
        # Use Python's built-in AST parser to check syntax
        try:
            ast.parse(artifact.content)
            success = True
            status = VerificationStatus.SUCCESS
        except SyntaxError as e:
            # Record the syntax error
            issues.append({
                "message": f"Syntax error at line {e.lineno}, column {e.offset}: {e.msg}",
                "line": e.lineno,
                "column": e.offset,
                "code": e.msg,
                "severity": "error"
            })
            success = False
            status = VerificationStatus.FAILURE
        except Exception as e:
            # Record any other errors
            issues.append({
                "message": f"Error parsing code: {str(e)}",
                "severity": "error"
            })
            success = False
            status = VerificationStatus.ERROR
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record metrics
        self.metrics_collector.record_counter(
            "verification.count", 
            1, 
            {"success": str(success)}
        )
        self.metrics_collector.record_histogram(
            "verification.duration_ms",
            duration_ms
        )
        
        # Create recommendations if there are issues
        recommendations = []
        if not success:
            recommendations.append({
                "message": "Fix syntax errors to ensure the code can be parsed and executed",
                "priority": "high"
            })
        
        # Create the verification result
        result = VerificationResult(
            artifact_id=artifact.id,
            plugin_id=f"python.syntax",
            status=status,
            success=success,
            confidence=1.0 if success else 0.0,
            issues=issues,
            recommendations=recommendations,
            metrics={
                "duration_ms": duration_ms,
                "issues_count": len(issues)
            },
            duration_ms=duration_ms,
            details={
                "parser": "ast.parse",
                "python_version": "3.x"
            }
        )
        
        return result
    
    def register_metrics(self) -> List[MetricDefinition]:
        """
        Define metrics that this plugin will report.
        
        Returns:
            List of metric definitions
        """
        return [
            MetricDefinition(
                name="verification.count",
                description="Number of verification runs",
                unit="count",
                type="counter",
                labels=["success"]
            ),
            MetricDefinition(
                name="verification.duration_ms",
                description="Verification duration in milliseconds",
                unit="ms",
                type="histogram"
            )
        ]


class PythonSecurityVerifier(VerifierPlugin):
    """
    Verifies Python code for security vulnerabilities.
    
    This plugin checks for common security issues in Python code, such as
    hardcoded credentials, use of dangerous functions, etc.
    """
    
    def __init__(self, context: VerificationContext):
        """
        Initialize the Python security verifier.
        
        Args:
            context: The verification context
        """
        super().__init__(context)
        self.metrics_collector = MetricsCollector(namespace="verification.python.security")
        
        # Patterns for security issues
        self.patterns = {
            "hardcoded_password": r'password\s*=\s*[\'"][^\'"]+[\'"]',
            "hardcoded_api_key": r'api_key\s*=\s*[\'"][^\'"]+[\'"]',
            "sql_injection": r'execute\s*\(\s*[\'"][^\'"]*(SELECT|INSERT|UPDATE|DELETE).*\%.*[\'"]',
            "eval_usage": r'eval\s*\(',
            "exec_usage": r'exec\s*\(',
            "pickle_usage": r'pickle\.loads\s*\(',
            "shell_injection": r'os\.system\s*\(\s*[^\)]+\)',
            "temp_file_vulnerability": r'tempfile\.mktemp\s*\(',
        }
    
    async def verify(self, artifact: CodeArtifact) -> VerificationResult:
        """
        Verify the Python code for security vulnerabilities.
        
        Args:
            artifact: The code artifact to verify
            
        Returns:
            The verification result
        """
        logger.info(f"Verifying Python security for {artifact.file_path}")
        
        start_time = time.time()
        issues = []
        
        # Check for each security pattern
        for issue_type, pattern in self.patterns.items():
            for i, line in enumerate(artifact.content.splitlines()):
                line_num = i + 1
                matches = re.findall(pattern, line)
                for match in matches:
                    issues.append({
                        "message": f"Potential security issue: {issue_type}",
                        "line": line_num,
                        "code": match,
                        "severity": "high",
                        "type": issue_type
                    })
        
        success = len(issues) == 0
        status = VerificationStatus.SUCCESS if success else VerificationStatus.FAILURE
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record metrics
        self.metrics_collector.record_counter(
            "verification.count", 
            1, 
            {"success": str(success)}
        )
        self.metrics_collector.record_histogram(
            "verification.duration_ms",
            duration_ms
        )
        
        # Count issues by type
        issue_types = {}
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            if issue_type not in issue_types:
                issue_types[issue_type] = 0
            issue_types[issue_type] += 1
            
            # Record each issue type
            self.metrics_collector.record_counter(
                f"issues.{issue_type}",
                1
            )
        
        # Create recommendations if there are issues
        recommendations = []
        if not success:
            recommendations.append({
                "message": "Fix security vulnerabilities to prevent potential attacks",
                "priority": "high"
            })
            
            for issue_type, count in issue_types.items():
                if issue_type == "hardcoded_password" or issue_type == "hardcoded_api_key":
                    recommendations.append({
                        "message": "Use environment variables or a secure configuration store for secrets",
                        "priority": "high",
                        "type": issue_type
                    })
                elif issue_type == "sql_injection":
                    recommendations.append({
                        "message": "Use parameterized queries instead of string formatting in SQL",
                        "priority": "high",
                        "type": issue_type
                    })
                elif issue_type == "eval_usage" or issue_type == "exec_usage":
                    recommendations.append({
                        "message": "Avoid using eval() or exec() as they can execute arbitrary code",
                        "priority": "high",
                        "type": issue_type
                    })
        
        # Create the verification result
        result = VerificationResult(
            artifact_id=artifact.id,
            plugin_id=f"python.security",
            status=status,
            success=success,
            confidence=0.8,  # Security analysis is not 100% accurate
            issues=issues,
            recommendations=recommendations,
            metrics={
                "duration_ms": duration_ms,
                "issues_count": len(issues),
                "issue_types": issue_types
            },
            duration_ms=duration_ms,
            details={
                "patterns_checked": list(self.patterns.keys())
            }
        )
        
        return result
    
    def register_metrics(self) -> List[MetricDefinition]:
        """
        Define metrics that this plugin will report.
        
        Returns:
            List of metric definitions
        """
        return [
            MetricDefinition(
                name="verification.count",
                description="Number of verification runs",
                unit="count",
                type="counter",
                labels=["success"]
            ),
            MetricDefinition(
                name="verification.duration_ms",
                description="Verification duration in milliseconds",
                unit="ms",
                type="histogram"
            ),
            MetricDefinition(
                name="issues.hardcoded_password",
                description="Count of hardcoded password issues",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="issues.hardcoded_api_key",
                description="Count of hardcoded API key issues",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="issues.sql_injection",
                description="Count of SQL injection vulnerabilities",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="issues.eval_usage",
                description="Count of eval() usages",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="issues.exec_usage",
                description="Count of exec() usages",
                unit="count",
                type="counter"
            )
        ]


class PythonStyleVerifier(VerifierPlugin):
    """
    Verifies Python code for style issues.
    
    This plugin checks for adherence to coding style guidelines, such as
    PEP 8, line length limits, etc.
    """
    
    def __init__(self, context: VerificationContext):
        """
        Initialize the Python style verifier.
        
        Args:
            context: The verification context
        """
        super().__init__(context)
        self.metrics_collector = MetricsCollector(namespace="verification.python.style")
        
        # Style rules
        self.max_line_length = context.config.get("max_line_length", 79)
        self.indentation_spaces = context.config.get("indentation_spaces", 4)
        
        # Style patterns
        self.patterns = {
            "trailing_whitespace": r'[ \t]+$',
            "mixed_tabs_spaces": r'^ *\t',
            "multiple_imports": r'import\s+([^,\s]+,\s*)+([^,\s]+)'
        }
    
    async def verify(self, artifact: CodeArtifact) -> VerificationResult:
        """
        Verify the Python code for style issues.
        
        Args:
            artifact: The code artifact to verify
            
        Returns:
            The verification result
        """
        logger.info(f"Verifying Python style for {artifact.file_path}")
        
        start_time = time.time()
        issues = []
        
        # Check line length
        for i, line in enumerate(artifact.content.splitlines()):
            line_num = i + 1
            
            # Check line length
            if len(line) > self.max_line_length:
                issues.append({
                    "message": f"Line too long ({len(line)} > {self.max_line_length})",
                    "line": line_num,
                    "severity": "low",
                    "type": "line_too_long"
                })
            
            # Check other style patterns
            for issue_type, pattern in self.patterns.items():
                if re.search(pattern, line):
                    issues.append({
                        "message": f"Style issue: {issue_type}",
                        "line": line_num,
                        "severity": "low",
                        "type": issue_type
                    })
            
            # Check indentation
            if line.strip() and line.startswith(" "):
                spaces = len(line) - len(line.lstrip(" "))
                if spaces % self.indentation_spaces != 0:
                    issues.append({
                        "message": f"Indentation not a multiple of {self.indentation_spaces} spaces",
                        "line": line_num,
                        "severity": "low",
                        "type": "indentation"
                    })
        
        # Determine overall success
        # Style issues are warnings, not errors, so they don't fail verification
        success = True
        status = VerificationStatus.SUCCESS
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record metrics
        self.metrics_collector.record_counter(
            "verification.count", 
            1, 
            {"success": str(success)}
        )
        self.metrics_collector.record_histogram(
            "verification.duration_ms",
            duration_ms
        )
        
        # Count issues by type
        issue_types = {}
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            if issue_type not in issue_types:
                issue_types[issue_type] = 0
            issue_types[issue_type] += 1
            
            # Record each issue type
            self.metrics_collector.record_counter(
                f"issues.{issue_type}",
                1
            )
        
        # Create recommendations if there are issues
        recommendations = []
        if issues:
            recommendations.append({
                "message": "Follow PEP 8 style guidelines for better code readability",
                "priority": "low"
            })
            
            if issue_types.get("line_too_long", 0) > 0:
                recommendations.append({
                    "message": f"Keep lines under {self.max_line_length} characters",
                    "priority": "low",
                    "type": "line_too_long"
                })
            
            if issue_types.get("trailing_whitespace", 0) > 0:
                recommendations.append({
                    "message": "Remove trailing whitespace",
                    "priority": "low",
                    "type": "trailing_whitespace"
                })
        
        # Create the verification result
        result = VerificationResult(
            artifact_id=artifact.id,
            plugin_id=f"python.style",
            status=status,
            success=success,
            confidence=0.9,
            issues=issues,
            recommendations=recommendations,
            metrics={
                "duration_ms": duration_ms,
                "issues_count": len(issues),
                "issue_types": issue_types
            },
            duration_ms=duration_ms,
            details={
                "max_line_length": self.max_line_length,
                "indentation_spaces": self.indentation_spaces
            }
        )
        
        return result
    
    def register_metrics(self) -> List[MetricDefinition]:
        """
        Define metrics that this plugin will report.
        
        Returns:
            List of metric definitions
        """
        return [
            MetricDefinition(
                name="verification.count",
                description="Number of verification runs",
                unit="count",
                type="counter",
                labels=["success"]
            ),
            MetricDefinition(
                name="verification.duration_ms",
                description="Verification duration in milliseconds",
                unit="ms",
                type="histogram"
            ),
            MetricDefinition(
                name="issues.line_too_long",
                description="Count of lines exceeding maximum length",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="issues.trailing_whitespace",
                description="Count of trailing whitespace issues",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="issues.mixed_tabs_spaces",
                description="Count of mixed tabs and spaces issues",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="issues.indentation",
                description="Count of indentation issues",
                unit="count",
                type="counter"
            )
        ]
