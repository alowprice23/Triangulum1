"""
Triangulum Integrated System - Core integration point for the Triangulum self-healing system.

This module provides the TriangulumSystem class which integrates all components of the
Triangulum system, including code relationship analysis, system monitoring, self-healing,
and feedback collection.
"""

import os
import sys
import time
import json
import logging
import tempfile
from typing import Dict, List, Any, Optional, Union

# Core components
from triangulum_lx.core.engine import TriangulumEngine
from triangulum_lx.core.state import TriangulumState

# Monitoring
from triangulum_lx.monitoring.system_monitor import SystemMonitor

# Tooling
from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer
from triangulum_lx.tooling.relationship_context_provider import RelationshipContextProvider
from triangulum_lx.tooling.repair import PatcherAgent

# Human interaction
from triangulum_lx.human.feedback import FeedbackCollector

logger = logging.getLogger(__name__)

class TriangulumSystem:
    """
    Integrated Triangulum system that brings together all components.

    This class serves as the central integration point for all Triangulum components,
    providing a unified interface for code analysis, system monitoring, self-healing,
    and feedback collection.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Triangulum system.

        Args:
            config_path: Path to the configuration file (optional)
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize logging
        self._setup_logging()
        
        logger.info("Initializing Triangulum integrated system")
        
        # Initialize core components
        self.engine = TriangulumEngine()
        self.monitor = SystemMonitor(self.engine)
        self.relationship_analyzer = CodeRelationshipAnalyzer()
        self.relationship_provider = RelationshipContextProvider()
        self.feedback_collector = FeedbackCollector(
            db_path=self.config.get("feedback", {}).get("db_path")
        )
        self.patcher = PatcherAgent()
        
        # Start monitoring if enabled
        if self.config.get("monitoring", {}).get("enabled", True):
            interval = self.config.get("monitoring", {}).get("interval", 60)
            self.monitor.start_monitoring(interval=interval)
        
        logger.info("Triangulum system initialized successfully")

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.

        Args:
            config_path: Path to the configuration file

        Returns:
            Configuration dictionary
        """
        default_config = {
            "system": {
                "log_level": "INFO",
                "data_directory": "triangulum_data",
                "relationship_path": "triangulum_relationships.json"
            },
            "monitoring": {
                "enabled": True,
                "interval": 60
            },
            "feedback": {
                "enabled": True,
                "db_path": os.path.join("triangulum_data", "feedback.db")
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded configuration from {config_path}")
                    return config
            except Exception as e:
                logger.error(f"Error loading configuration from {config_path}: {e}")
                logger.warning("Using default configuration")
                return default_config
        else:
            if config_path:
                logger.warning(f"Configuration file {config_path} not found, using defaults")
            return default_config

    def _setup_logging(self):
        """Set up logging based on configuration."""
        log_level = getattr(logging, self.config.get("system", {}).get("log_level", "INFO"))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def analyze_code_relationships(self, target_dir: str) -> Dict[str, Any]:
        """
        Analyze code relationships in a directory.

        Args:
            target_dir: Directory to analyze

        Returns:
            Dictionary containing relationships between files
        """
        logger.info(f"Analyzing code relationships in {target_dir}")
        
        # Analyze the directory
        relationships = self.relationship_analyzer.analyze_directory(target_dir)
        
        # Save the relationships
        relationship_path = self.config.get("system", {}).get("relationship_path", "triangulum_relationships.json")
        self.relationship_analyzer.save_relationships(relationship_path)
        
        # Update the relationship provider
        self.relationship_provider.load_relationships(relationships)
        
        logger.info(f"Analyzed {len(relationships)} files")
        return relationships

    def diagnose_system(self, target_dir: str) -> Dict[str, Any]:
        """
        Diagnose the system for issues.

        Args:
            target_dir: Directory to diagnose

        Returns:
            Dictionary containing diagnosis results
        """
        logger.info(f"Diagnosing system: {target_dir}")
        
        # Check if we have relationships
        if not hasattr(self.relationship_provider, 'relationships') or not self.relationship_provider.relationships:
            self.analyze_code_relationships(target_dir)
        
        # Check system health
        health_check = self.monitor.check_health()
        
        # Analyze for common issues
        issues = self._detect_issues(target_dir)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues)
        
        # Compile diagnosis
        diagnosis = {
            "timestamp": time.time(),
            "target": target_dir,
            "health_check": health_check,
            "detected_issues": issues,
            "recommendations": recommendations
        }
        
        return diagnosis

    def _detect_issues(self, target_dir: str) -> List[Dict[str, Any]]:
        """
        Detect issues in the system.

        Args:
            target_dir: Directory to analyze

        Returns:
            List of detected issues
        """
        issues = []
        
        # Check code structure
        structure_issues = self._check_code_structure(target_dir)
        issues.extend(structure_issues)
        
        # Check for dependency issues
        dependency_issues = self._check_dependencies()
        issues.extend(dependency_issues)
        
        # Check for potential bugs
        bug_issues = self._check_for_bugs()
        issues.extend(bug_issues)
        
        return issues

    def _check_code_structure(self, target_dir: str) -> List[Dict[str, Any]]:
        """
        Check code structure for issues.

        Args:
            target_dir: Directory to check

        Returns:
            List of structure issues
        """
        issues = []
        
        # Check for missing required directories
        required_dirs = ["tests", "docs"]
        for required_dir in required_dirs:
            dir_path = os.path.join(target_dir, required_dir)
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                issues.append({
                    "type": "structure",
                    "severity": "medium",
                    "description": f"Missing expected directory: {required_dir}",
                    "location": required_dir
                })
        
        # Check for proper module structure
        if os.path.exists(os.path.join(target_dir, "triangulum_lx")):
            module_path = os.path.join(target_dir, "triangulum_lx")
            if not os.path.exists(os.path.join(module_path, "__init__.py")):
                issues.append({
                    "type": "structure",
                    "severity": "high",
                    "description": "Missing __init__.py in main package",
                    "location": "triangulum_lx/__init__.py"
                })
        
        return issues

    def _check_dependencies(self) -> List[Dict[str, Any]]:
        """
        Check for dependency issues.

        Returns:
            List of dependency issues
        """
        issues = []
        
        if hasattr(self.relationship_provider, 'relationships'):
            # Look for circular dependencies
            for file_path, info in self.relationship_provider.relationships.items():
                for imported_file in info.get("imports", []):
                    if imported_file in self.relationship_provider.relationships:
                        if file_path in self.relationship_provider.relationships[imported_file].get("imports", []):
                            issues.append({
                                "type": "dependency",
                                "severity": "high",
                                "description": f"Circular dependency detected between {os.path.basename(file_path)} and {os.path.basename(imported_file)}",
                                "location": file_path
                            })
        
        return issues

    def _check_for_bugs(self) -> List[Dict[str, Any]]:
        """
        Check for potential bugs.

        Returns:
            List of potential bug issues
        """
        # This would involve more sophisticated analysis
        # For now, we'll return an empty list
        return []

    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on detected issues.

        Args:
            issues: List of detected issues

        Returns:
            List of recommendations
        """
        recommendations = []
        
        for issue in issues:
            if issue["type"] == "structure":
                if "directory" in issue["description"]:
                    recommendations.append({
                        "action": "Create directory",
                        "details": f"Create the missing {issue['location']} directory",
                        "automated": True
                    })
                elif "__init__.py" in issue["description"]:
                    recommendations.append({
                        "action": "Create file",
                        "details": f"Create the missing {issue['location']} file",
                        "automated": True
                    })
            
            elif issue["type"] == "dependency":
                recommendations.append({
                    "action": "Refactor",
                    "details": f"Resolve circular dependency in {issue['location']}",
                    "automated": False
                })
        
        return recommendations

    def self_heal(self, target_dir: str, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Attempt to fix detected issues.

        Args:
            target_dir: Directory to heal
            issues: List of issues to fix

        Returns:
            Dictionary containing healing results
        """
        logger.info(f"Attempting self-healing on {target_dir}")
        
        healing_results = {
            "timestamp": time.time(),
            "target": target_dir,
            "issues_addressed": len(issues),
            "successful_fixes": 0,
            "failed_fixes": 0,
            "actions_taken": []
        }
        
        for issue in issues:
            result = self._attempt_fix(target_dir, issue)
            healing_results["actions_taken"].append(result)
            
            if result["success"]:
                healing_results["successful_fixes"] += 1
            else:
                healing_results["failed_fixes"] += 1
        
        return healing_results

    def _attempt_fix(self, target_dir: str, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to fix a specific issue.

        Args:
            target_dir: Directory to heal
            issue: Issue to fix

        Returns:
            Dictionary containing fix results
        """
        result = {
            "issue": issue,
            "success": False,
            "action_taken": None,
            "details": None
        }
        
        if issue["type"] == "structure":
            if "directory" in issue["description"]:
                # Create missing directory
                dir_path = os.path.join(target_dir, issue["location"])
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    result["success"] = True
                    result["action_taken"] = f"Created directory: {issue['location']}"
                    result["details"] = f"Directory {issue['location']} created successfully"
                except Exception as e:
                    result["details"] = f"Failed to create directory {issue['location']}: {e}"
            
            elif "__init__.py" in issue["description"]:
                # Create missing __init__.py file
                file_path = os.path.join(target_dir, issue["location"])
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'w') as f:
                        f.write(f'"""{os.path.basename(os.path.dirname(file_path))} package."""\n')
                    result["success"] = True
                    result["action_taken"] = f"Created file: {issue['location']}"
                    result["details"] = f"File {issue['location']} created successfully"
                except Exception as e:
                    result["details"] = f"Failed to create file {issue['location']}: {e}"
        
        elif issue["type"] == "dependency":
            # Dependency issues usually require manual intervention
            result["details"] = f"Circular dependency issues require manual refactoring: {issue['description']}"
        
        else:
            result["details"] = f"No automatic fix available for issue type: {issue['type']}"
        
        return result

    def run_with_goal(self, goal_path: str) -> Dict[str, Any]:
        """
        Run the system with a specific goal.

        Args:
            goal_path: Path to the goal file

        Returns:
            Dictionary containing results
        """
        logger.info(f"Running with goal: {goal_path}")
        
        # Run the engine with the goal
        self.engine.run(goal_path)
        
        # Wait for completion
        status = self.engine.get_status()
        while status.get("running", False):
            time.sleep(1)
            status = self.engine.get_status()
        
        # Compile results
        results = {
            "session_id": status.get("session_id"),
            "goal_file": goal_path,
            "engine_status": status,
            "completion_time": time.time()
        }
        
        return results

    def shutdown(self):
        """Shut down the system gracefully."""
        logger.info("Shutting down Triangulum system")
        
        # Stop monitoring
        if hasattr(self, 'monitor') and self.monitor:
            self.monitor.stop_monitoring()
        
        # Save relationships
        if hasattr(self, 'relationship_provider') and self.relationship_provider:
            self.relationship_provider.save_relationships()
        
        # Shut down engine
        if hasattr(self, 'engine') and self.engine:
            self.engine.shutdown()
        
        logger.info("Triangulum system shut down successfully")

    def record_feedback(self, content: str, feedback_type: str = "general", 
                      source: Optional[str] = None, rating: Optional[int] = None) -> int:
        """
        Record feedback from a user.

        Args:
            content: The feedback content
            feedback_type: Type of feedback (general, bug, feature, etc.)
            source: Source of the feedback (UI, API, etc.)
            rating: Numerical rating (e.g., 1-5)

        Returns:
            ID of the feedback entry
        """
        session_id = self.engine.get_status().get("session_id") if hasattr(self, 'engine') and self.engine else None
        
        feedback_id = self.feedback_collector.record_feedback(
            content=content,
            feedback_type=feedback_type,
            source=source,
            session_id=session_id,
            rating=rating
        )
        
        return feedback_id

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get the current status of the system.

        Returns:
            Dictionary containing system status
        """
        status = {
            "timestamp": time.time(),
            "engine_status": self.engine.get_status() if hasattr(self, 'engine') and self.engine else None,
            "health_status": self.monitor.get_health_status() if hasattr(self, 'monitor') and self.monitor else None,
            "relationship_status": {
                "files_analyzed": len(self.relationship_provider.relationships) if hasattr(self, 'relationship_provider') and hasattr(self.relationship_provider, 'relationships') else 0
            }
        }
        
        return status
