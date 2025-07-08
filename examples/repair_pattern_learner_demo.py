#!/usr/bin/env python3
"""
Repair Pattern Learner Demo

This script demonstrates how the repair pattern learner works with the auto verifier
to learn from successful repairs and improve future fix suggestions.
"""

import os
import sys
import time
import logging
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.tooling.auto_verification import AutoVerifier
from triangulum_lx.learning.repair_pattern_learner import RepairPatternLearner, RepairPattern

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample code with different types of bugs
BUGGY_FILES = {
    "error_handling.py": """
import os
import json

def load_config(file_path):
    # Bug: No error handling for file operations
    with open(file_path, 'r') as f:
        return json.load(f)

def process_data(data_dict):
    # Bug: No error handling for key access
    value = data_dict['important_key']
    return value * 2

def main():
    config = load_config('config.json')
    result = process_data(config)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
""",

    "input_validation.py": """
import sys

def calculate_average(numbers):
    # Bug: No input validation
    total = sum(numbers)
    return total / len(numbers)

def process_user_input(input_str):
    # Bug: No input validation
    parts = input_str.split(',')
    numbers = [int(p) for p in parts]
    return calculate_average(numbers)

def main():
    if len(sys.argv) > 1:
        user_input = sys.argv[1]
    else:
        user_input = input("Enter numbers separated by commas: ")
    
    result = process_user_input(user_input)
    print(f"Average: {result}")

if __name__ == "__main__":
    main()
""",

    "performance_issue.py": """
def find_duplicates(items):
    # Bug: Inefficient algorithm for finding duplicates (O(n²) complexity)
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates

def process_large_dataset(filename):
    # Simulate loading data
    data = list(range(1000)) + list(range(500))
    
    # Find duplicates inefficiently
    return find_duplicates(data)

def main():
    result = process_large_dataset("large_dataset.txt")
    print(f"Found {len(result)} duplicates")

if __name__ == "__main__":
    main()
""",

    "security_issue.py": """
import os

def execute_command(user_input):
    # Bug: Command injection vulnerability
    os.system(f"echo {user_input}")

def save_to_file(filename, content):
    # Bug: Path traversal vulnerability
    with open(filename, 'w') as f:
        f.write(content)

def main():
    user_input = input("Enter your name: ")
    execute_command(user_input)
    
    filename = input("Enter filename to save: ")
    save_to_file(filename, f"Hello, {user_input}!")

if __name__ == "__main__":
    main()
"""
}

# Fixed versions of the buggy files
FIXED_FILES = {
    "error_handling.py": """
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(file_path):
    # Fixed: Added error handling for file operations
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in config file: {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def process_data(data_dict):
    # Fixed: Added error handling for key access
    try:
        value = data_dict.get('important_key')
        if value is None:
            logger.warning("Missing 'important_key' in data")
            return 0
        return value * 2
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return 0

def main():
    config = load_config('config.json')
    result = process_data(config)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
""",

    "input_validation.py": """
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_average(numbers):
    # Fixed: Added input validation
    if not numbers:
        logger.warning("Empty list provided to calculate_average")
        return 0
    
    return sum(numbers) / len(numbers)

def process_user_input(input_str):
    # Fixed: Added input validation
    if not input_str or not input_str.strip():
        logger.warning("Empty input string")
        return 0
    
    try:
        parts = input_str.split(',')
        numbers = []
        
        for part in parts:
            try:
                num = int(part.strip())
                numbers.append(num)
            except ValueError:
                logger.warning(f"Skipping invalid number: {part}")
        
        if not numbers:
            logger.warning("No valid numbers found in input")
            return 0
        
        return calculate_average(numbers)
    except Exception as e:
        logger.error(f"Error processing input: {e}")
        return 0

def main():
    if len(sys.argv) > 1:
        user_input = sys.argv[1]
    else:
        user_input = input("Enter numbers separated by commas: ")
    
    result = process_user_input(user_input)
    print(f"Average: {result}")

if __name__ == "__main__":
    main()
""",

    "performance_issue.py": """
def find_duplicates(items):
    # Fixed: Optimized algorithm for finding duplicates (O(n) complexity)
    seen = set()
    duplicates = set()
    
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    
    return list(duplicates)

def process_large_dataset(filename):
    # Simulate loading data
    data = list(range(1000)) + list(range(500))
    
    # Find duplicates efficiently
    return find_duplicates(data)

def main():
    result = process_large_dataset("large_dataset.txt")
    print(f"Found {len(result)} duplicates")

if __name__ == "__main__":
    main()
""",

    "security_issue.py": """
import os
import subprocess
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_command(user_input):
    # Fixed: Prevent command injection
    # Validate input to contain only alphanumeric characters
    if not re.match(r'^[a-zA-Z0-9 ]*$', user_input):
        logger.warning(f"Invalid input containing special characters: {user_input}")
        return "Invalid input"
    
    # Use subprocess with shell=False for security
    try:
        result = subprocess.run(["echo", user_input], 
                               shell=False, 
                               check=True, 
                               capture_output=True, 
                               text=True)
        return result.stdout
    except subprocess.SubprocessError as e:
        logger.error(f"Command execution error: {e}")
        return "Error executing command"

def save_to_file(filename, content):
    # Fixed: Prevent path traversal
    try:
        # Normalize and validate path is within current directory
        file_path = Path(filename)
        if file_path.is_absolute() or '..' in file_path.parts:
            logger.warning(f"Attempted path traversal: {filename}")
            return False
        
        # Ensure we're writing to a safe location
        safe_path = Path.cwd() / file_path.name
        
        with open(safe_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Error saving to file: {e}")
        return False

def main():
    user_input = input("Enter your name: ")
    result = execute_command(user_input)
    print(result)
    
    filename = input("Enter filename to save: ")
    success = save_to_file(filename, f"Hello, {user_input}!")
    if success:
        print(f"Saved to {filename}")
    else:
        print("Failed to save file")

if __name__ == "__main__":
    main()
"""
}

# Fix information dictionaries
FIX_INFO = {
    "error_handling.py": [
        {
            "file": "error_handling.py",
            "line": 8,
            "severity": "high",
            "description": "Added error handling for file operations"
        },
        {
            "file": "error_handling.py",
            "line": 19,
            "severity": "medium",
            "description": "Added error handling for missing dictionary key"
        }
    ],
    "input_validation.py": [
        {
            "file": "input_validation.py",
            "line": 8,
            "severity": "medium",
            "description": "Added input validation for empty list"
        },
        {
            "file": "input_validation.py",
            "line": 16,
            "severity": "high",
            "description": "Added input validation for user input"
        }
    ],
    "performance_issue.py": [
        {
            "file": "performance_issue.py",
            "line": 2,
            "severity": "medium",
            "description": "Optimized algorithm for finding duplicates"
        }
    ],
    "security_issue.py": [
        {
            "file": "security_issue.py",
            "line": 11,
            "severity": "critical",
            "description": "Fixed command injection vulnerability"
        },
        {
            "file": "security_issue.py",
            "line": 25,
            "severity": "critical",
            "description": "Fixed path traversal vulnerability"
        }
    ]
}

def setup_project(base_dir: str):
    """
    Set up a demo project with buggy code.
    
    Args:
        base_dir: The base directory for the demo project
    
    Returns:
        Dictionary with project information
    """
    logger.info(f"Setting up demo project in {base_dir}")
    
    # Create project structure
    os.makedirs(base_dir, exist_ok=True)
    
    # Write buggy files
    for filename, content in BUGGY_FILES.items():
        file_path = os.path.join(base_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
    
    # Create a dummy config file for testing
    config_path = os.path.join(base_dir, "config.json")
    with open(config_path, 'w') as f:
        f.write('{"important_key": 21}')
    
    logger.info(f"Created demo project with {len(BUGGY_FILES)} buggy files")
    
    return {
        "project_root": base_dir,
        "files": list(BUGGY_FILES.keys()),
        "fixes": [fix for fixes in FIX_INFO.values() for fix in fixes]
    }

def apply_fix(project_root: str, file_name: str):
    """
    Apply a fix to a buggy file.
    
    Args:
        project_root: Path to the project root
        file_name: Name of the file to fix
    
    Returns:
        True if the fix was applied, False otherwise
    """
    if file_name not in FIXED_FILES:
        logger.error(f"No fix available for {file_name}")
        return False
    
    # Apply the fix
    file_path = os.path.join(project_root, file_name)
    with open(file_path, 'w') as f:
        f.write(FIXED_FILES[file_name])
    
    logger.info(f"Applied fix to {file_name}")
    return True

def run_demo():
    """Run the repair pattern learner demo."""
    # Create a temporary directory for the demo
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up paths
        project_root = os.path.join(temp_dir, "buggy_project")
        patterns_dir = os.path.join(temp_dir, "repair_patterns")
        verification_dir = os.path.join(temp_dir, "verification")
        
        # Set up project with buggy code
        project_info = setup_project(project_root)
        
        # Initialize auto verifier and pattern learner
        verifier = AutoVerifier(
            project_root=project_root,
            verification_dir=verification_dir,
            enable_regression_testing=True
        )
        
        learner = RepairPatternLearner(
            patterns_dir=patterns_dir,
            verification_dir=verification_dir,
            enable_auto_learning=True,
            min_examples_for_pattern=1  # Lower threshold for demo purposes
        )
        
        # Create baseline
        logger.info("Creating baseline state before fixes")
        verifier.create_baseline()
        
        # Step 1: Apply error handling fixes and learn patterns
        logger.info("\n--- STEP 1: Error Handling Fixes ---")
        error_file = "error_handling.py"
        apply_fix(project_root, error_file)
        
        # Verify the fixes
        verification_results = []
        for fix_info in FIX_INFO[error_file]:
            result = verifier.verify_fix(fix_info)
            verification_results.append(result)
            
            logger.info(f"Fix verification for {fix_info['description']}: {'SUCCESS' if result['verified'] else 'FAILURE'}")
        
        # Create synthetic verification results for learning
        combined_results = {
            "fix_results": verification_results
        }
        
        # Learn patterns from the verification results
        new_patterns = learner.learn_from_verification(combined_results)
        logger.info(f"Learned {len(new_patterns)} new patterns from error handling fixes")
        
        for pattern in new_patterns:
            logger.info(f"  - {pattern.name}: {pattern.description}")
        
        # Step 2: Apply input validation fixes and learn patterns
        logger.info("\n--- STEP 2: Input Validation Fixes ---")
        input_file = "input_validation.py"
        apply_fix(project_root, input_file)
        
        # Verify the fixes
        verification_results = []
        for fix_info in FIX_INFO[input_file]:
            result = verifier.verify_fix(fix_info)
            verification_results.append(result)
            
            logger.info(f"Fix verification for {fix_info['description']}: {'SUCCESS' if result['verified'] else 'FAILURE'}")
        
        # Create synthetic verification results for learning
        combined_results = {
            "fix_results": verification_results
        }
        
        # Learn patterns from the verification results
        new_patterns = learner.learn_from_verification(combined_results)
        logger.info(f"Learned {len(new_patterns)} new patterns from input validation fixes")
        
        for pattern in new_patterns:
            logger.info(f"  - {pattern.name}: {pattern.description}")
        
        # Step 3: Test pattern matching and fix suggestions
        logger.info("\n--- STEP 3: Pattern Matching and Fix Suggestions ---")
        
        # Create a new buggy file with similar issues
        new_buggy_file = """
def process_config(config_path):
    # This function needs error handling
    with open(config_path, 'r') as f:
        config = f.read().strip().split('\\n')
    
    settings = {}
    for line in config:
        key, value = line.split('=')
        settings[key] = value
    
    return settings

def validate_user_data(user_data):
    # This function needs input validation
    username = user_data['username']
    email = user_data['email']
    
    # Process user data
    return username, email
"""
        
        new_file_path = os.path.join(project_root, "new_module.py")
        with open(new_file_path, 'w') as f:
            f.write(new_buggy_file)
        
        # Test fix suggestions for error handling
        error_fix_info = {
            "file": "new_module.py",
            "line": 3,
            "severity": "high",
            "description": "Need to add error handling for file operations"
        }
        
        # Get code context around the fix location
        with open(new_file_path, 'r') as f:
            context = f.read()
        
        # Get fix suggestion for error handling
        error_suggestion = learner.suggest_fix(error_fix_info, context)
        
        if error_suggestion:
            logger.info(f"Suggested fix for error handling:")
            logger.info(f"  Pattern: {error_suggestion['pattern_name']}")
            logger.info(f"  Confidence: {error_suggestion['confidence']:.2f}")
            logger.info(f"  Suggestion:")
            for line in error_suggestion['suggestion'].split('\n'):
                logger.info(f"    {line}")
        else:
            logger.info("No suggestion found for error handling")
        
        # Test fix suggestions for input validation
        validation_fix_info = {
            "file": "new_module.py",
            "line": 13,
            "severity": "medium",
            "description": "Need to add input validation for user data"
        }
        
        # Get fix suggestion for input validation
        validation_suggestion = learner.suggest_fix(validation_fix_info, context)
        
        if validation_suggestion:
            logger.info(f"Suggested fix for input validation:")
            logger.info(f"  Pattern: {validation_suggestion['pattern_name']}")
            logger.info(f"  Confidence: {validation_suggestion['confidence']:.2f}")
            logger.info(f"  Suggestion:")
            for line in validation_suggestion['suggestion'].split('\n'):
                logger.info(f"    {line}")
        else:
            logger.info("No suggestion found for input validation")
        
        # Step 4: Apply performance and security fixes
        logger.info("\n--- STEP 4: Performance and Security Fixes ---")
        
        # Apply and verify performance fix
        apply_fix(project_root, "performance_issue.py")
        for fix_info in FIX_INFO["performance_issue.py"]:
            result = verifier.verify_fix(fix_info)
            logger.info(f"Fix verification for {fix_info['description']}: {'SUCCESS' if result['verified'] else 'FAILURE'}")
        
        # Apply and verify security fixes
        apply_fix(project_root, "security_issue.py")
        for fix_info in FIX_INFO["security_issue.py"]:
            result = verifier.verify_fix(fix_info)
            logger.info(f"Fix verification for {fix_info['description']}: {'SUCCESS' if result['verified'] else 'FAILURE'}")
        
        # Learn from all fixes
        all_fixes = [fix for fixes in FIX_INFO.values() for fix in fixes]
        all_success = [True] * len(all_fixes)  # All fixes are successful
        
        new_patterns = learner.learn_from_fixes(all_fixes, all_success)
        
        # Step 5: Generate verification report
        logger.info("\n--- STEP 5: Generate Verification Report ---")
        report_path = verifier.export_verification_report()
        logger.info(f"Verification report exported to {report_path}")
        
        # Print summary of learned patterns
        logger.info("\n--- SUMMARY: Learned Repair Patterns ---")
        for pattern_id, pattern in learner.patterns.items():
            logger.info(f"Pattern: {pattern.name}")
            logger.info(f"  ID: {pattern.pattern_id}")
            logger.info(f"  Description: {pattern.description}")
            logger.info(f"  Language: {pattern.language}")
            logger.info(f"  Tags: {', '.join(pattern.tags)}")
            logger.info(f"  Examples: {len(pattern.examples)}")
            logger.info(f"  Success Rate: {pattern.success_rate:.2f}")
            logger.info("")
        
        logger.info("Repair Pattern Learner Demo completed successfully!")

if __name__ == "__main__":
    run_demo()
