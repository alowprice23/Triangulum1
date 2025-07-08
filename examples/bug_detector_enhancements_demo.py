#!/usr/bin/env python3
"""
Enhanced Bug Detector Demo

This script demonstrates the enhanced capabilities of the Bug Detector agent:
1. False positive reduction through multi-pass verification
2. Performance optimization for large codebases
3. Integration with the relationship analyst
4. Context-aware detection capabilities
5. Advanced bug classification and prioritization
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bug_detector_demo")

# Import specific modules directly to avoid problematic import chains
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent, BugType, DetectedBug
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.message_bus import MessageBus
from triangulum_lx.agents.message import MessageType


def create_test_files(temp_dir):
    """Create test files with deliberate bugs for demonstration."""
    logger.info("Creating test files with deliberate bugs...")
    
    # Create test directory structure
    os.makedirs(os.path.join(temp_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "src", "utils"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "src", "models"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "src", "controllers"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "tests"), exist_ok=True)
    
    # Create a database utility file with SQL injection vulnerability
    with open(os.path.join(temp_dir, "src", "utils", "database.py"), "w") as f:
        f.write("""# Database utility functions
import sqlite3

def get_connection():
    return sqlite3.connect("app.db")

def execute_query(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    finally:
        conn.close()

# VULNERABILITY: SQL Injection in direct string concatenation
def get_user_by_id(user_id):
    # This is vulnerable to SQL injection
    query = "SELECT * FROM users WHERE id = " + user_id
    return execute_query(query)

# Safe version using parameterized query
def get_user_by_id_safe(user_id):
    query = "SELECT * FROM users WHERE id = ?"
    return execute_query(query, (user_id,))
""")
    
    # Create a user model with null reference vulnerability
    with open(os.path.join(temp_dir, "src", "models", "user.py"), "w") as f:
        f.write("""# User model
class User:
    def __init__(self, id=None, name=None, email=None):
        self.id = id
        self.name = name
        self.email = email
        self.profile = None  # This will be None by default
    
    def get_profile_data(self):
        # VULNERABILITY: Null reference
        return self.profile.data  # This will cause a null reference if profile is None
    
    def get_profile_data_safe(self):
        # Safe version with null check
        if self.profile is not None:
            return self.profile.data
        return None
""")
    
    # Create a file handler with resource leak
    with open(os.path.join(temp_dir, "src", "utils", "file_handler.py"), "w") as f:
        f.write("""# File handler utilities
import os

# VULNERABILITY: Resource leak (file not closed)
def read_file_content(filename):
    f = open(filename, 'r')  # File is never closed
    content = f.read()
    return content

# Safe version using context manager
def read_file_content_safe(filename):
    with open(filename, 'r') as f:
        content = f.read()
    return content

def write_file_content(filename, content):
    with open(filename, 'w') as f:
        f.write(content)
""")
    
    # Create a controller with credential leak
    with open(os.path.join(temp_dir, "src", "controllers", "auth_controller.py"), "w") as f:
        f.write("""# Authentication controller
import hashlib
from src.models.user import User

# VULNERABILITY: Hardcoded credentials
def get_admin_credentials():
    return {
        "username": "admin",
        "password": "super_secure_password123"  # Hardcoded password
    }

def authenticate(username, password):
    # Hash the password (simplified)
    hashed = hashlib.sha256(password.encode()).hexdigest()
    
    # In a real app, we would check against a database
    if username == "admin" and hashed == "expected_hash":
        return User(1, "Admin", "admin@example.com")
    return None
""")
    
    # Create a test file that contains intentional issues for testing
    with open(os.path.join(temp_dir, "tests", "test_user.py"), "w") as f:
        f.write("""# User model tests
import unittest
from src.models.user import User

class TestUser(unittest.TestCase):
    def test_user_creation(self):
        user = User(1, "Test User", "test@example.com")
        self.assertEqual(user.id, 1)
        self.assertEqual(user.name, "Test User")
        self.assertEqual(user.email, "test@example.com")
    
    def test_null_profile(self):
        user = User(1, "Test User", "test@example.com")
        
        # This would normally cause an error, but it's intentional for testing
        try:
            data = user.profile.data  # Intentional null reference for testing
        except AttributeError:
            pass  # We expect this to fail
        
        # The safe version should work
        self.assertIsNone(user.get_profile_data_safe())

if __name__ == "__main__":
    unittest.main()
""")
    
    # Return the list of created files
    return [
        os.path.join(temp_dir, "src", "utils", "database.py"),
        os.path.join(temp_dir, "src", "models", "user.py"),
        os.path.join(temp_dir, "src", "utils", "file_handler.py"),
        os.path.join(temp_dir, "src", "controllers", "auth_controller.py"),
        os.path.join(temp_dir, "tests", "test_user.py")
    ]


def run_analysis_and_display_results(bug_detector, files, temp_dir):
    """Run bug detection on files and display the results."""
    logger.info("Running Bug Detector analysis...")
    
    # Analyze each file individually and show results
    print("\n=== Individual File Analysis ===")
    all_bugs = {}
    
    for file_path in files:
        rel_path = os.path.relpath(file_path, temp_dir)
        print(f"\nAnalyzing: {rel_path}")
        
        # Detect bugs with verification
        bugs = bug_detector.detect_bugs_in_file(
            file_path=file_path,
            verify_bugs=True
        )
        
        all_bugs[rel_path] = bugs
        
        if bugs:
            print(f"Found {len(bugs)} potential issues:")
            for i, bug in enumerate(bugs, 1):
                severity = bug.get("severity", "medium")
                bug_type = bug.get("bug_type", "unknown")
                line = bug.get("line_number", bug.get("line", 0))
                confidence = bug.get("confidence", 0.5)
                
                # Format with severity-based coloring (would work in terminals with color support)
                severity_color = {
                    "critical": "\033[91m",  # Red
                    "high": "\033[93m",      # Yellow
                    "medium": "\033[94m",    # Blue
                    "low": "\033[92m",       # Green
                }
                
                end_color = "\033[0m"
                severity_str = f"{severity_color.get(severity, '')}{severity.upper()}{end_color}"
                
                print(f"  {i}. {severity_str} ({confidence:.2f} confidence): {bug_type} at line {line}")
                print(f"     {bug.get('description', '')}")
                print(f"     Remediation: {bug.get('remediation', '')}")
        else:
            print("No issues found.")
    
    # Run folder-level analysis with parallel processing
    print("\n=== Folder-Level Analysis (with parallel processing) ===")
    start_time = time.time()
    
    folder_result = bug_detector.detect_bugs_in_folder(
        folder_path=temp_dir,
        recursive=True,
        parallel=True,
        max_workers=3
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"Analysis completed in {elapsed_time:.2f} seconds")
    print(f"Files analyzed: {folder_result['files_analyzed']}")
    print(f"Files with bugs: {folder_result['files_with_bugs']}")
    print(f"Total bugs found: {folder_result['total_bugs']}")
    
    # Show bug classification (if available)
    if hasattr(bug_detector, '_classify_bug_priority') and folder_result['total_bugs'] > 0:
        print("\n=== Bug Classification and Prioritization ===")
        # Get a sample bug for demonstration
        sample_file = next(iter(folder_result['bugs_by_file']))
        sample_bugs = folder_result['bugs_by_file'][sample_file]
        
        if sample_bugs:
            # Convert to DetectedBug object if needed
            if isinstance(sample_bugs[0], dict):
                from triangulum_lx.agents.bug_detector_agent import DetectedBug
                sample_bug = bug_detector._convert_to_detected_bug(sample_bugs[0])
            else:
                sample_bug = sample_bugs[0]
            
            # Get relationship context
            rel_context = bug_detector._get_relationship_context(sample_bug.file_path)
            
            # Classify the bug
            impact = bug_detector._classify_bug_impact(sample_bug, rel_context)
            priority = bug_detector._classify_bug_priority(sample_bug, rel_context)
            
            print(f"Sample bug from {sample_file}:")
            print(f"  Type: {sample_bug.bug_type.value}")
            print(f"  Base Severity: {sample_bug.severity}")
            print(f"  Classified Impact: {impact}")
            print(f"  Priority Score (1-10): {priority}")
            print(f"  Confidence: {sample_bug.confidence:.2f}")
            
            if rel_context:
                print(f"  Dependencies: {len(rel_context.get('dependencies', []))}")
                print(f"  Dependents: {len(rel_context.get('dependents', []))}")
                print(f"  Is central: {rel_context.get('is_central', False)}")
    
    return all_bugs, folder_result


def main():
    """Main function to run the demo."""
    print("Enhanced Bug Detector Demo")
    print("==========================")
    
    # Create a temporary directory for test files
    import tempfile
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Create test files
        files = create_test_files(temp_dir)
        
        # Set up the message bus
        message_bus = MessageBus()
        
        # Set up the relationship analyst
        relationship_analyst = RelationshipAnalystAgent(
            agent_id="relationship_analyst",
            message_bus=message_bus
        )
        
        # Set up the bug detector with enhancements
        bug_detector = BugDetectorAgent(
            agent_id="bug_detector",
            message_bus=message_bus,
            relationship_analyst_agent=relationship_analyst,
            enable_context_aware_detection=True,
            enable_multi_pass_verification=True,
            false_positive_threshold=0.8,
            use_ast_parsing=True
        )
        
        # Let the relationship analyst build the relationship graph
        logger.info("Building code relationship graph...")
        for file_path in files:
            relationship_analyst.analyze_file(file_path)
        
        # Run the demo analysis
        all_bugs, folder_result = run_analysis_and_display_results(bug_detector, files, temp_dir)
        
        # Demonstrate false positive reduction
        print("\n=== False Positive Reduction ===")
        print("Analyzing test files which may contain intentional issues...")
        
        test_files = [f for f in files if "tests/" in f]
        test_bugs_before = []
        
        for file_path in test_files:
            # Analyze without false positive reduction
            bugs = bug_detector.detect_bugs_in_file(
                file_path=file_path,
                verify_bugs=False
            )
            test_bugs_before.extend(bugs)
        
        test_bugs_after = []
        for file_path in test_files:
            # Analyze with false positive reduction
            bugs = bug_detector.detect_bugs_in_file(
                file_path=file_path,
                verify_bugs=True
            )
            test_bugs_after.extend(bugs)
        
        print(f"Bugs found in test files WITHOUT false positive reduction: {len(test_bugs_before)}")
        print(f"Bugs found in test files WITH false positive reduction: {len(test_bugs_after)}")
        print(f"False positives eliminated: {len(test_bugs_before) - len(test_bugs_after)}")
        
        print("\nDemo completed successfully!")
        
    finally:
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Error cleaning up temporary directory: {e}")


if __name__ == "__main__":
    main()
