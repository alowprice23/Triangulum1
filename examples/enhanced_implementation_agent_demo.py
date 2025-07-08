#!/usr/bin/env python3
"""
Enhanced Implementation Agent Demo

This script demonstrates the advanced capabilities of the enhanced Implementation Agent,
showcasing code analysis, patch generation, validation, backup/rollback mechanisms,
and metrics collection during bug fixing operations.
"""

import os
import sys
import logging
import json
import time
from pathlib import Path
import tempfile
import shutil
from typing import Dict, Any, List

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.implementation_agent import ImplementationAgent
from triangulum_lx.agents.message import MessageType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class DemoManager:
    """
    Manages the implementation agent demonstration, setting up test files,
    strategies, and handling the demonstration flow.
    """
    
    def __init__(self, demo_dir: str = None):
        """
        Initialize the demo manager.
        
        Args:
            demo_dir: Directory to store demo files (creates temp dir if None)
        """
        self.demo_dir = demo_dir or tempfile.mkdtemp(prefix="implementation_agent_demo_")
        self.test_files_dir = os.path.join(self.demo_dir, "test_files")
        os.makedirs(self.test_files_dir, exist_ok=True)
        
        # Create an implementation agent
        self.implementation_agent = ImplementationAgent(
            agent_id="demo_implementation_agent",
            config={
                "backup_dir": os.path.join(self.demo_dir, "backups"),
                "validate_patches": True,
                "progressive_patching": True
            }
        )
        
        # Track implementations for demonstrations
        self.implementations = {}
        self.application_results = {}
        
        logger.info(f"Demo initialized in directory: {self.demo_dir}")
    
    def setup_test_files(self):
        """Set up test files with known bugs for demonstration."""
        # Create test files with various issues
        self._create_test_file(
            "null_pointer_demo.py",
            """
def process_data(data):
    # Null pointer bug: data might be None
    return data.get('key')

def main():
    # This will cause a null pointer exception
    result = process_data(None)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""
        )
        
        self._create_test_file(
            "resource_leak_demo.py",
            """
def read_file_content(filename):
    # Resource leak: file is not properly closed
    f = open(filename, 'r')
    content = f.read()
    return content  # File is never closed

def main():
    content = read_file_content('example.txt')
    print(f"Content length: {len(content)}")

if __name__ == "__main__":
    main()
"""
        )
        
        self._create_test_file(
            "sql_injection_demo.py",
            """
import sqlite3

def get_user(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SQL Injection vulnerability
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result

def main():
    user = get_user("user1' OR '1'='1")  # Malicious input
    print(f"User: {user}")

if __name__ == "__main__":
    main()
"""
        )
        
        self._create_test_file(
            "hardcoded_credentials_demo.py",
            """
def connect_to_database():
    # Hardcoded credentials security issue
    username = "admin"
    password = "super_secret_password123"
    
    connection_string = f"mysql://{username}:{password}@localhost/mydb"
    return connection_string

def main():
    conn_str = connect_to_database()
    print(f"Connected with: {conn_str}")

if __name__ == "__main__":
    main()
"""
        )
        
        self._create_test_file(
            "exception_swallowing_demo.py",
            """
def divide(a, b):
    try:
        return a / b
    except Exception:
        # Exception swallowing: catching and ignoring the exception
        pass

def main():
    # This will silently fail
    result = divide(10, 0)
    # We never see that an error occurred
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""
        )
        
        logger.info(f"Created test files in {self.test_files_dir}")
    
    def _create_test_file(self, filename: str, content: str):
        """Create a test file with the given content."""
        file_path = os.path.join(self.test_files_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content.strip())
    
    def generate_repair_strategies(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate repair strategies for each test file.
        
        Returns:
            Dictionary mapping bug types to repair strategies
        """
        strategies = {}
        
        # Null pointer bug strategy
        strategies["null_pointer"] = {
            "id": "strategy_null_pointer",
            "name": "Fix null pointer bug",
            "description": "Add null check before accessing object properties",
            "bug_type": "null_pointer",
            "bug_location": os.path.join(self.test_files_dir, "null_pointer_demo.py"),
            "bug_line": 3,
            "bug_code": "return data.get('key')",
            "confidence": 0.9,
            "affected_files": [
                os.path.join(self.test_files_dir, "null_pointer_demo.py")
            ]
        }
        
        # Resource leak bug strategy
        strategies["resource_leak"] = {
            "id": "strategy_resource_leak",
            "name": "Fix resource leak bug",
            "description": "Use context manager to ensure file is closed",
            "bug_type": "resource_leak",
            "bug_location": os.path.join(self.test_files_dir, "resource_leak_demo.py"),
            "bug_line": 3,
            "bug_code": "f = open(filename, 'r')",
            "confidence": 0.9,
            "affected_files": [
                os.path.join(self.test_files_dir, "resource_leak_demo.py")
            ]
        }
        
        # SQL injection bug strategy
        strategies["sql_injection"] = {
            "id": "strategy_sql_injection",
            "name": "Fix SQL injection bug",
            "description": "Use parameterized queries instead of string concatenation",
            "bug_type": "sql_injection",
            "bug_location": os.path.join(self.test_files_dir, "sql_injection_demo.py"),
            "bug_line": 8,
            "bug_code": "query = \"SELECT * FROM users WHERE username = '\" + username + \"'\"",
            "confidence": 0.9,
            "affected_files": [
                os.path.join(self.test_files_dir, "sql_injection_demo.py")
            ]
        }
        
        # Hardcoded credentials bug strategy
        strategies["hardcoded_credentials"] = {
            "id": "strategy_hardcoded_credentials",
            "name": "Fix hardcoded credentials bug",
            "description": "Use environment variables for sensitive credentials",
            "bug_type": "hardcoded_credentials",
            "bug_location": os.path.join(self.test_files_dir, "hardcoded_credentials_demo.py"),
            "bug_line": 5,
            "bug_code": "password = \"super_secret_password123\"",
            "confidence": 0.9,
            "affected_files": [
                os.path.join(self.test_files_dir, "hardcoded_credentials_demo.py")
            ]
        }
        
        # Exception swallowing bug strategy
        strategies["exception_swallowing"] = {
            "id": "strategy_exception_swallowing",
            "name": "Fix exception swallowing bug",
            "description": "Add proper logging and error handling for exceptions",
            "bug_type": "exception_swallowing",
            "bug_location": os.path.join(self.test_files_dir, "exception_swallowing_demo.py"),
            "bug_line": 3,
            "bug_code": "except Exception:",
            "confidence": 0.9,
            "affected_files": [
                os.path.join(self.test_files_dir, "exception_swallowing_demo.py")
            ]
        }
        
        logger.info(f"Generated repair strategies for {len(strategies)} bug types")
        return strategies
    
    def run_implementation_demo(self, strategies: Dict[str, Dict[str, Any]]):
        """
        Run the implementation demo for each strategy.
        
        Args:
            strategies: Dictionary mapping bug types to repair strategies
        """
        for bug_type, strategy in strategies.items():
            logger.info(f"\n{'=' * 80}\nDemonstrating fix for {bug_type} bug\n{'=' * 80}")
            
            # Get the original file content
            bug_location = strategy.get("bug_location")
            with open(bug_location, 'r') as f:
                original_content = f.read()
            
            logger.info(f"Original code with {bug_type} bug:")
            logger.info(f"\n{original_content}\n")
            
            # Generate implementation for the strategy
            start_time = time.time()
            implementation = self.implementation_agent.implement_strategy(strategy)
            end_time = time.time()
            
            # Store the implementation
            self.implementations[bug_type] = implementation
            
            # Show implementation details
            logger.info(f"Implementation details for {bug_type} bug:")
            logger.info(f"Generated {len(implementation.get('patches', []))} patches")
            logger.info(f"Implementation approach: {implementation.get('approach')}")
            logger.info(f"Risk level: {implementation.get('risk_level')}")
            logger.info(f"Confidence level: {implementation.get('confidence_level', 0):.2f}")
            logger.info(f"Implementation time: {end_time - start_time:.2f} seconds\n")
            
            # Show patches
            for i, patch in enumerate(implementation.get("patches", [])):
                file_path = patch.get("file_path")
                changes = patch.get("changes", [])
                
                logger.info(f"Patch {i+1} for file: {os.path.basename(file_path)}")
                logger.info(f"Number of changes: {len(changes)}")
                
                for j, change in enumerate(changes):
                    change_type = change.get("type")
                    start_line = change.get("start_line")
                    
                    logger.info(f"  Change {j+1}: {change_type} at line {start_line}")
                    if change_type == "replace_lines":
                        logger.info(f"  New content: \n{change.get('content')}\n")
            
            # Apply the implementation
            logger.info(f"Applying implementation for {bug_type} bug...")
            
            application_result = self.implementation_agent.apply_implementation(
                implementation=implementation,
                dry_run=False,
                progressive=True,
                validate_after_each_file=True
            )
            
            # Store the application result
            self.application_results[bug_type] = application_result
            
            # Show application result
            logger.info(f"Implementation application result:")
            logger.info(f"Status: {application_result.get('status')}")
            logger.info(f"Message: {application_result.get('message')}")
            logger.info(f"Files modified: {len(application_result.get('files_modified', []))}")
            logger.info(f"Files failed: {len(application_result.get('files_failed', []))}")
            logger.info(f"Backups created: {len(application_result.get('backups_created', []))}")
            
            # Show the fixed file content
            if application_result.get("status") in ["success", "partial_success"]:
                with open(bug_location, 'r') as f:
                    fixed_content = f.read()
                
                logger.info(f"Fixed code for {bug_type} bug:")
                logger.info(f"\n{fixed_content}\n")
                
                # For demonstration purposes, revert to original
                with open(bug_location, 'w') as f:
                    f.write(original_content)
                logger.info(f"Reverted file to original content for next demo")
    
    def demonstrate_rollback(self):
        """Demonstrate the rollback functionality."""
        logger.info(f"\n{'=' * 80}\nDemonstrating rollback functionality\n{'=' * 80}")
        
        # Choose a strategy to apply and then rollback
        bug_type = "null_pointer"
        strategy = self.generate_repair_strategies()[bug_type]
        
        # Get the original file content
        bug_location = strategy.get("bug_location")
        with open(bug_location, 'r') as f:
            original_content = f.read()
        
        # Generate and apply implementation
        implementation = self.implementation_agent.implement_strategy(strategy)
        application_result = self.implementation_agent.apply_implementation(implementation)
        
        logger.info(f"Applied implementation for {bug_type} bug")
        logger.info(f"Implementation ID: {implementation.get('implementation_id')}")
        
        # Show the modified file
        with open(bug_location, 'r') as f:
            modified_content = f.read()
        
        logger.info(f"Modified content after implementation:")
        logger.info(f"\n{modified_content}\n")
        
        # Rollback the implementation
        rollback_result = self.implementation_agent.rollback_implementation(
            implementation_id=implementation.get("implementation_id")
        )
        
        logger.info(f"Rollback result:")
        logger.info(f"Status: {rollback_result.get('status')}")
        logger.info(f"Message: {rollback_result.get('message')}")
        logger.info(f"Files restored: {len(rollback_result.get('files_restored', []))}")
        
        # Show the content after rollback
        with open(bug_location, 'r') as f:
            rollback_content = f.read()
        
        logger.info(f"Content after rollback:")
        logger.info(f"\n{rollback_content}\n")
        
        # Verify that the rollback was successful
        is_successful = rollback_content == original_content
        logger.info(f"Rollback successful: {is_successful}")
    
    def demonstrate_metrics(self):
        """Demonstrate the metrics collection functionality."""
        logger.info(f"\n{'=' * 80}\nDemonstrating metrics collection\n{'=' * 80}")
        
        # Get metrics summary
        metrics_summary = self.implementation_agent.metrics.get_summary()
        
        logger.info(f"Implementation metrics summary:")
        logger.info(f"Total implementations: {metrics_summary.get('total_implementations')}")
        logger.info(f"Success rate: {metrics_summary.get('success_rate', 0):.2f}")
        logger.info(f"Average implementation time: {metrics_summary.get('avg_implementation_time', 0):.2f} seconds")
        logger.info(f"Average patch size: {metrics_summary.get('avg_patch_size', 0):.2f} bytes")
        logger.info(f"Average files changed: {metrics_summary.get('avg_files_changed', 0):.2f}")
        logger.info(f"Validation success rate: {metrics_summary.get('validation_success_rate', 0):.2f}")
        logger.info(f"Rollback rate: {metrics_summary.get('rollback_rate', 0):.2f}")
        
        # Show language and bug type distributions
        logger.info(f"Language distribution:")
        for language, count in metrics_summary.get("language_distribution", {}).items():
            logger.info(f"  {language}: {count}")
        
        logger.info(f"Bug type distribution:")
        for bug_type, count in metrics_summary.get("bug_type_distribution", {}).items():
            logger.info(f"  {bug_type}: {count}")
    
    def cleanup(self):
        """Clean up the demo directory."""
        logger.info(f"Cleaning up demo directory: {self.demo_dir}")
        shutil.rmtree(self.demo_dir, ignore_errors=True)


def main():
    """Main function to run the enhanced implementation agent demo."""
    logger.info("Starting Enhanced Implementation Agent Demo")
    
    # Create demo manager
    demo_manager = DemoManager()
    
    try:
        # Setup test files
        demo_manager.setup_test_files()
        
        # Generate repair strategies
        strategies = demo_manager.generate_repair_strategies()
        
        # Run implementation demo
        demo_manager.run_implementation_demo(strategies)
        
        # Demonstrate rollback
        demo_manager.demonstrate_rollback()
        
        # Demonstrate metrics
        demo_manager.demonstrate_metrics()
        
        logger.info("Enhanced Implementation Agent Demo completed successfully")
    
    finally:
        # Clean up
        demo_manager.cleanup()


if __name__ == "__main__":
    main()
