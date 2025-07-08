"""
Metrics collection and analysis for the verification system.

This module provides classes and functions for collecting, analyzing, and
reporting metrics about the verification process, including success rates,
performance metrics, and other statistics.
"""

import time
import logging
import json
import os
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class VerificationMetrics:
    """
    Collects and analyzes metrics about the verification process.
    
    This class provides methods to track various metrics about the verification
    process, including success rates, performance metrics, and other statistics.
    It also provides methods to analyze these metrics and generate reports.
    """
    
    def __init__(self, metrics_path: Optional[str] = None):
        """
        Initialize the verification metrics.
        
        Args:
            metrics_path: Path to save metrics data (optional)
        """
        self.metrics_path = metrics_path or os.path.join(
            os.getcwd(), ".triangulum", "metrics", "verification")
        
        # Create the metrics directory if it doesn't exist
        os.makedirs(self.metrics_path, exist_ok=True)
        
        # Initialize metrics data structures
        self.total_verifications = 0
        self.successful_verifications = 0
        self.failed_verifications = 0
        self.verification_times = []
        self.bug_type_stats = defaultdict(lambda: {"count": 0, "success": 0})
        self.false_positives = 0
        self.false_negatives = 0
        self.check_stats = defaultdict(lambda: {"count": 0, "success": 0})
        self.language_stats = defaultdict(lambda: {"count": 0, "success": 0})
        self.failure_reasons = defaultdict(int)
        
        # Verification session tracking
        self.current_session = None
        self.session_start_time = None
        self.sessions = []
    
    def start_session(self, session_id: Optional[str] = None):
        """
        Start a new verification session.
        
        Args:
            session_id: ID for the session (generated if not provided)
        """
        if self.current_session:
            # End the current session before starting a new one
            self.end_session()
        
        # Generate a session ID if one was not provided
        if not session_id:
            session_id = f"session_{int(time.time())}"
        
        self.current_session = {
            "id": session_id,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "verifications": [],
            "success_rate": 0.0,
            "avg_verification_time": 0.0,
            "total_verifications": 0,
            "successful_verifications": 0,
            "failed_verifications": 0
        }
        
        self.session_start_time = time.time()
    
    def end_session(self):
        """End the current verification session."""
        if not self.current_session:
            return
        
        # Record the end time
        self.current_session["end_time"] = datetime.now().isoformat()
        
        # Calculate session-level metrics
        total = len(self.current_session["verifications"])
        successful = sum(1 for v in self.current_session["verifications"] if v["success"])
        
        self.current_session["total_verifications"] = total
        self.current_session["successful_verifications"] = successful
        self.current_session["failed_verifications"] = total - successful
        
        if total > 0:
            self.current_session["success_rate"] = successful / total
        
        # Calculate average verification time
        if total > 0:
            times = [v["duration"] for v in self.current_session["verifications"] if "duration" in v]
            if times:
                self.current_session["avg_verification_time"] = sum(times) / len(times)
        
        # Add the session to the list of sessions
        self.sessions.append(self.current_session)
        
        # Save the session data
        self._save_session_data(self.current_session)
        
        # Reset the current session
        self.current_session = None
        self.session_start_time = None
    
    def _save_session_data(self, session: Dict[str, Any]):
        """
        Save session data to a file.
        
        Args:
            session: Session data to save
        """
        try:
            # Create a filename based on the session ID
            filename = f"{session['id']}.json"
            filepath = os.path.join(self.metrics_path, filename)
            
            # Save the data to a JSON file
            with open(filepath, 'w') as f:
                json.dump(session, f, indent=2)
            
            logger.info(f"Saved verification session data to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save verification session data: {e}")
    
    def start_verification(self, implementation_id: str, bug_type: str, language: str):
        """
        Record the start of a verification.
        
        Args:
            implementation_id: ID of the implementation being verified
            bug_type: Type of bug being fixed
            language: Programming language of the code
        """
        # Create a verification record
        verification = {
            "implementation_id": implementation_id,
            "bug_type": bug_type,
            "language": language,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "success": False,
            "duration": 0.0,
            "checks": {},
            "issues": []
        }
        
        if self.current_session:
            self.current_session["verifications"].append(verification)
        
        return verification
    
    def end_verification(
        self,
        verification: Dict[str, Any],
        success: bool,
        checks: Dict[str, Dict[str, Any]],
        issues: Optional[List[str]] = None
    ):
        """
        Record the end of a verification.
        
        Args:
            verification: Verification record
            success: Whether the verification was successful
            checks: Results of individual checks
            issues: List of issues found (optional)
        """
        # Update the verification record
        verification["end_time"] = datetime.now().isoformat()
        verification["success"] = success
        verification["checks"] = checks
        verification["issues"] = issues or []
        
        # Calculate duration
        start_time = datetime.fromisoformat(verification["start_time"])
        end_time = datetime.fromisoformat(verification["end_time"])
        duration = (end_time - start_time).total_seconds()
        verification["duration"] = duration
        
        # Update global metrics
        self.total_verifications += 1
        if success:
            self.successful_verifications += 1
        else:
            self.failed_verifications += 1
        
        self.verification_times.append(duration)
        
        # Update bug type stats
        bug_type = verification["bug_type"]
        self.bug_type_stats[bug_type]["count"] += 1
        if success:
            self.bug_type_stats[bug_type]["success"] += 1
        
        # Update language stats
        language = verification["language"]
        self.language_stats[language]["count"] += 1
        if success:
            self.language_stats[language]["success"] += 1
        
        # Update check stats
        for check_name, check_result in checks.items():
            self.check_stats[check_name]["count"] += 1
            if check_result.get("success", False):
                self.check_stats[check_name]["success"] += 1
        
        # Update failure reasons
        if not success and issues:
            for issue in issues:
                self.failure_reasons[self._categorize_issue(issue)] += 1
    
    def _categorize_issue(self, issue: str) -> str:
        """
        Categorize an issue into a standard failure reason.
        
        Args:
            issue: The issue message
            
        Returns:
            Standardized failure reason
        """
        # Define categories and their keywords
        categories = {
            "syntax_error": ["syntax error", "syntax", "parsing error", "parse error"],
            "test_failure": ["test failed", "assertion failed", "expected", "but got"],
            "type_error": ["type error", "type mismatch", "expected type"],
            "null_pointer": ["null pointer", "none type", "nullpointerexception"],
            "resource_leak": ["resource leak", "not closed", "unclosed"],
            "security_issue": ["security", "vulnerability", "injection", "credentials"],
            "compilation_error": ["compilation error", "compiler error", "failed to compile"],
            "runtime_error": ["runtime error", "exception occurred", "crashed"]
        }
        
        # Try to match the issue to a category
        lower_issue = issue.lower()
        for category, keywords in categories.items():
            if any(keyword in lower_issue for keyword in keywords):
                return category
        
        # If no match, return a generic category
        return "other_issue"
    
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
        
        # Calculate success rates for each bug type
        bug_type_success_rates = {}
        for bug_type, stats in self.bug_type_stats.items():
            if stats["count"] > 0:
                bug_type_success_rates[bug_type] = stats["success"] / stats["count"]
            else:
                bug_type_success_rates[bug_type] = 0
        
        # Calculate success rates for each language
        language_success_rates = {}
        for language, stats in self.language_stats.items():
            if stats["count"] > 0:
                language_success_rates[language] = stats["success"] / stats["count"]
            else:
                language_success_rates[language] = 0
        
        # Calculate overall success rate
        success_rate = self.successful_verifications / self.total_verifications if self.total_verifications > 0 else 0
        
        return {
            "total_verifications": self.total_verifications,
            "successful_verifications": self.successful_verifications,
            "failed_verifications": self.failed_verifications,
            "success_rate": success_rate,
            "avg_verification_time": avg_time,
            "false_positive_rate": self.false_positives / self.total_verifications if self.total_verifications > 0 else 0,
            "false_negative_rate": self.false_negatives / self.total_verifications if self.total_verifications > 0 else 0,
            "bug_type_success_rates": bug_type_success_rates,
            "language_success_rates": language_success_rates,
            "check_success_rates": check_success_rates,
            "top_failure_reasons": self._get_top_failure_reasons(5),
            "sessions": len(self.sessions),
            "session_metrics": self._get_session_metrics()
        }
    
    def _get_top_failure_reasons(self, n: int) -> Dict[str, int]:
        """
        Get the top N failure reasons.
        
        Args:
            n: Number of top reasons to return
            
        Returns:
            Dictionary of top failure reasons
        """
        # Sort the failure reasons by count
        sorted_reasons = sorted(
            self.failure_reasons.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return the top N reasons
        return dict(sorted_reasons[:n])
    
    def _get_session_metrics(self) -> Dict[str, Any]:
        """
        Get metrics across all sessions.
        
        Returns:
            Dictionary of session metrics
        """
        if not self.sessions:
            return {}
        
        # Calculate average metrics across all sessions
        total_verifications = sum(s["total_verifications"] for s in self.sessions)
        successful_verifications = sum(s["successful_verifications"] for s in self.sessions)
        
        avg_success_rate = sum(s["success_rate"] for s in self.sessions) / len(self.sessions)
        avg_verification_time = sum(s["avg_verification_time"] for s in self.sessions) / len(self.sessions)
        
        return {
            "total_sessions": len(self.sessions),
            "total_verifications": total_verifications,
            "successful_verifications": successful_verifications,
            "failed_verifications": total_verifications - successful_verifications,
            "avg_success_rate": avg_success_rate,
            "avg_verification_time": avg_verification_time
        }
    
    def save_metrics(self, filepath: Optional[str] = None):
        """
        Save the metrics to a file.
        
        Args:
            filepath: Path to save the metrics to (optional)
        """
        if filepath is None:
            # Generate a default filepath
            filepath = os.path.join(
                self.metrics_path,
                f"verification_metrics_{int(time.time())}.json"
            )
        
        try:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Get the metrics summary
            summary = self.get_summary()
            
            # Save the metrics to a JSON file
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Saved verification metrics to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save verification metrics: {e}")
    
    def load_metrics(self, filepath: str) -> Dict[str, Any]:
        """
        Load metrics from a file.
        
        Args:
            filepath: Path to load the metrics from
            
        Returns:
            Loaded metrics data
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Loaded verification metrics from {filepath}")
            return data
        except Exception as e:
            logger.error(f"Failed to load verification metrics: {e}")
            return {}
