#!/usr/bin/env python3
"""
Simple Bug Detector Demo

A simplified demonstration of the enhanced Bug Detector agent capabilities
without complex dependencies.
"""

import os
import sys
import time
import tempfile
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("simple_bug_detector_demo")

# Add the Triangulum package to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import only what we need from Triangulum
from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent


def create_test_files(temp_dir):
    """Create test files with deliberate bugs for demonstration."""
    print(f"Creating test files with deliberate bugs in {temp_dir}...")
    
    # Create a file with SQL injection
    sql_file = os.path.join(temp_dir, "sql_injection_example.py")
    with open(sql_file, "w") as f:
        f.write("""
# Example with SQL injection vulnerability
def get_user(user_id):
    # This is vulnerable to SQL injection
    query = "SELECT * FROM users WHERE id = " + user_id
    return execute_query(query)

def execute_query(query):
    # This is a mock function
    print(f"Executing query: {query}")
    return []
""")
    
    # Create a file with null reference
    null_file = os.path.join(temp_dir, "null_pointer_example.py")
    with open(null_file, "w") as f:
        f.write("""
# Example with null reference vulnerability
def get_user_data(user):
    # This will cause a null reference if user.profile is None
    return user.profile.data

class User:
    def __init__(self):
        self.profile = None
""")
    
    # Create a file with resource leak
    resource_file = os.path.join(temp_dir, "resource_leak_example.py")
    with open(resource_file, "w") as f:
        f.write("""
# Example with resource leak
def read_file(filename):
    # File is never closed
    f = open(filename, 'r')
    content = f.read()
    return content
""")
    
    # Create a test file with intentional issues
    test_file = os.path.join(temp_dir, "test_examples.py")
    with open(test_file, "w") as f:
        f.write("""
# Test file with intentional issues that should be ignored
import unittest

def test_null_pointer():
    # This is intentional for testing
    user = get_mock_user()
    try:
        # This should raise an error, but it's for testing
        data = user.profile.data
    except AttributeError:
        pass  # Expected to fail
    
def get_mock_user():
    class User:
        def __init__(self):
            self.profile = None
    return User()
""")
    
    return [sql_file, null_file, resource_file, test_file]


def main():
    """Main function to run the demo."""
    print("Simple Bug Detector Demo")
    print("=======================")
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Create test files
        files = create_test_files(temp_dir)
        
        # Create bug detector with default settings
        print("\nInitializing Bug Detector...")
        bug_detector = BugDetectorAgent(
            agent_id="bug_detector_demo",
            enable_context_aware_detection=True,
            enable_multi_pass_verification=True,
            false_positive_threshold=0.8
        )
        
        # Analyze each file individually
        print("\n1. Individual File Analysis")
        print("----------------------------")
        for file_path in files:
            file_name = os.path.basename(file_path)
            print(f"\nAnalyzing: {file_name}")
            
            # First without verification (to show false positives)
            bugs_without_verification = bug_detector.detect_bugs_in_file(
                file_path=file_path,
                verify_bugs=False
            )
            
            # Then with verification
            bugs_with_verification = bug_detector.detect_bugs_in_file(
                file_path=file_path,
                verify_bugs=True
            )
            
            # Show results
            print(f"  Without false positive reduction: {len(bugs_without_verification)} bugs found")
            print(f"  With false positive reduction: {len(bugs_with_verification)} bugs found")
            
            # Show details of verified bugs
            if bugs_with_verification:
                print("\n  Verified bugs:")
                for i, bug in enumerate(bugs_with_verification, 1):
                    print(f"    {i}. {bug.get('bug_type', 'unknown')} at line {bug.get('line_number', bug.get('line', 0))}")
                    print(f"       Severity: {bug.get('severity', 'unknown')}")
                    print(f"       Description: {bug.get('description', '')}")
        
        # Analyze the folder
        print("\n2. Folder-Level Analysis")
        print("--------------------------")
        start_time = time.time()
        folder_result = bug_detector.detect_bugs_in_folder(
            folder_path=temp_dir,
            recursive=True
        )
        elapsed_time = time.time() - start_time
        
        print(f"Analysis completed in {elapsed_time:.2f} seconds")
        print(f"Files analyzed: {folder_result['files_analyzed']}")
        print(f"Files with bugs: {folder_result['files_with_bugs']}")
        print(f"Total bugs found: {folder_result['total_bugs']}")
        
        # Demonstrate false positive reduction
        print("\n3. False Positive Reduction")
        print("----------------------------")
        # Only analyze the test file
        test_file = next(f for f in files if "test_" in f)
        print(f"Analyzing: {os.path.basename(test_file)}")
        
        # Without verification
        bugs_before = bug_detector.detect_bugs_in_file(
            file_path=test_file,
            verify_bugs=False
        )
        
        # With verification
        bugs_after = bug_detector.detect_bugs_in_file(
            file_path=test_file,
            verify_bugs=True
        )
        
        print(f"Without false positive reduction: {len(bugs_before)} bugs")
        print(f"With false positive reduction: {len(bugs_after)} bugs")
        print(f"False positives eliminated: {len(bugs_before) - len(bugs_after)}")
        
        print("\nDemo completed successfully!")
    
    finally:
        # Clean up
        try:
            import shutil
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Error cleaning up: {e}")


if __name__ == "__main__":
    main()
