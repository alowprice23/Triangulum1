#!/usr/bin/env python3
"""
Auto Verification Demo

This script demonstrates how the auto verification tool works to verify
implemented fixes and ensure they resolve issues without introducing regressions.
"""

import os
import sys
import time
import tempfile
import shutil
import logging
import argparse
from pathlib import Path
from typing import Optional

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.tooling.auto_verification import AutoVerifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define sample buggy code and fixed code
BUGGY_CODE = """#!/usr/bin/env python3
\"\"\"
Sample module with a bug for demonstration purposes.
\"\"\"

def process_data(data):
    \"\"\"Process input data and return results.\"\"\"
    result = []
    
    # Bug: No error handling for invalid input
    for item in data:
        value = item['value']  # This will fail if item is not a dict or has no 'value' key
        processed = value * 2
        result.append(processed)
    
    return result

def calculate_average(numbers):
    \"\"\"Calculate the average of a list of numbers.\"\"\"
    # Bug: No error handling for empty list
    return sum(numbers) / len(numbers)  # This will fail if numbers is empty

def main():
    \"\"\"Main function to demonstrate the buggy code.\"\"\"
    try:
        # Example 1: Will work fine
        data = [{'value': 5}, {'value': 10}, {'value': 15}]
        result1 = process_data(data)
        print(f"Result 1: {result1}")
        
        # Example 2: Will fail due to missing 'value' key
        data = [{'value': 5}, {'val': 10}, {'value': 15}]
        result2 = process_data(data)
        print(f"Result 2: {result2}")
        
        # Example 3: Will fail due to empty list
        numbers = []
        avg = calculate_average(numbers)
        print(f"Average: {avg}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
"""

FIXED_CODE = """#!/usr/bin/env python3
\"\"\"
Sample module with fixes applied for demonstration purposes.
\"\"\"

def process_data(data):
    \"\"\"Process input data and return results.\"\"\"
    result = []
    
    # Fixed: Added error handling for invalid input
    for item in data:
        try:
            value = item.get('value')
            if value is None:
                logger.warning(f"Skipping item without 'value' key: {item}")
                continue
            processed = value * 2
            result.append(processed)
        except (AttributeError, TypeError) as e:
            logger.error(f"Error processing item {item}: {e}")
            continue
    
    return result

def calculate_average(numbers):
    \"\"\"Calculate the average of a list of numbers.\"\"\"
    # Fixed: Added error handling for empty list
    if not numbers:
        logger.warning("Empty list provided to calculate_average")
        return 0  # Return default value for empty list
    
    return sum(numbers) / len(numbers)

def main():
    \"\"\"Main function to demonstrate the fixed code.\"\"\"
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Example 1: Will work fine
        data = [{'value': 5}, {'value': 10}, {'value': 15}]
        result1 = process_data(data)
        print(f"Result 1: {result1}")
        
        # Example 2: Will now skip the item with missing 'value' key
        data = [{'value': 5}, {'val': 10}, {'value': 15}]
        result2 = process_data(data)
        print(f"Result 2: {result2}")
        
        # Example 3: Will now return 0 for empty list
        numbers = []
        avg = calculate_average(numbers)
        print(f"Average: {avg}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
"""

def setup_demo_project(base_dir: str):
    """
    Set up a demo project with buggy code for verification.
    
    Args:
        base_dir: The base directory for the demo project
    
    Returns:
        Dictionary with project information
    """
    logger.info(f"Setting up demo project in {base_dir}")
    
    # Create project structure
    os.makedirs(os.path.join(base_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "tests"), exist_ok=True)
    
    # Write buggy module
    with open(os.path.join(base_dir, "src", "sample_module.py"), 'w', encoding='utf-8') as f:
        f.write(BUGGY_CODE)
    
    # Write simple test
    test_code = """#!/usr/bin/env python3
\"\"\"
Tests for sample_module.py
\"\"\"

import unittest
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.sample_module import process_data, calculate_average

# Disable logging during tests
logging.disable(logging.CRITICAL)

class TestSampleModule(unittest.TestCase):
    \"\"\"Test cases for sample_module.py\"\"\"
    
    def test_process_data_valid(self):
        \"\"\"Test process_data with valid input\"\"\"
        data = [{'value': 5}, {'value': 10}, {'value': 15}]
        result = process_data(data)
        self.assertEqual(result, [10, 20, 30])
    
    def test_calculate_average(self):
        \"\"\"Test calculate_average with valid input\"\"\"
        numbers = [5, 10, 15]
        result = calculate_average(numbers)
        self.assertEqual(result, 10)

if __name__ == '__main__':
    unittest.main()
"""
    
    with open(os.path.join(base_dir, "tests", "test_sample_module.py"), 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    # Create a simple run script
    run_script = """#!/usr/bin/env python3
\"\"\"
Run script for sample_module.py
\"\"\"

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.sample_module import main

if __name__ == '__main__':
    main()
"""
    
    with open(os.path.join(base_dir, "run.py"), 'w', encoding='utf-8') as f:
        f.write(run_script)
    
    # Make run script executable
    try:
        os.chmod(os.path.join(base_dir, "run.py"), 0o755)
    except Exception as e:
        logger.warning(f"Could not make run.py executable: {e}")
    
    return {
        "project_root": base_dir,
        "module_path": os.path.join("src", "sample_module.py"),
        "fixes": [
            {
                "file": os.path.join("src", "sample_module.py"),
                "line": 13,
                "severity": "high",
                "description": "Added error handling for missing 'value' key"
            },
            {
                "file": os.path.join("src", "sample_module.py"),
                "line": 26,
                "severity": "medium",
                "description": "Added error handling for empty list in calculate_average"
            }
        ]
    }

def apply_fixes(project_info: dict):
    """
    Apply fixes to the demo project.
    
    Args:
        project_info: Dictionary with project information
    
    Returns:
        Path to the fixed module
    """
    logger.info("Applying fixes to the project")
    
    module_path = os.path.join(project_info["project_root"], project_info["module_path"])
    
    # Write fixed code
    with open(module_path, 'w', encoding='utf-8') as f:
        f.write(FIXED_CODE)
    
    logger.info(f"Fixes applied to {module_path}")
    return module_path

def run_demo(output_dir: Optional[str] = None, keep_files: bool = False):
    """
    Run the auto verification demo.
    
    Args:
        output_dir: Directory to store demo outputs
        keep_files: Whether to keep temporary files after demo
    """
    # Create temporary directory if no output directory specified
    if output_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="auto_verification_demo_")
        output_dir = temp_dir
        logger.info(f"Created temporary directory: {temp_dir}")
    else:
        os.makedirs(output_dir, exist_ok=True)
        temp_dir = None
    
    try:
        # Set up demo project
        project_info = setup_demo_project(output_dir)
        project_root = project_info["project_root"]
        
        # Initialize auto verifier
        verifier = AutoVerifier(
            project_root=project_root,
            verification_dir=os.path.join(project_root, ".verification"),
            test_command="python -m unittest discover tests",
            enable_regression_testing=True,
            enable_performance_testing=True
        )
        
        # Create baseline
        logger.info("Creating baseline for the project")
        baseline = verifier.create_baseline()
        logger.info(f"Baseline created with {len(baseline['files'])} files")
        
        # Run tests on buggy code (expected to fail)
        logger.info("Running tests on buggy code (expected to fail)")
        try:
            test_results = verifier._run_tests()
            logger.info(f"Test results: {'SUCCESS' if test_results['success'] else 'FAILURE'}")
        except Exception as e:
            logger.error(f"Error running tests on buggy code: {e}")
        
        # Apply fixes
        logger.info("Applying fixes to the code")
        apply_fixes(project_info)
        
        # Verify fixes
        logger.info("Verifying fixes")
        verification_results = []
        for fix_info in project_info["fixes"]:
            logger.info(f"Verifying fix: {fix_info['description']}")
            result = verifier.verify_fix(fix_info)
            verification_results.append(result)
            logger.info(f"Verification result: {'SUCCESS' if result['verified'] else 'FAILURE'}")
            
            # Generate regression test
            if result['verified']:
                logger.info(f"Generating regression test for fix: {fix_info['description']}")
                test_path = verifier.generate_regression_test(fix_info)
                logger.info(f"Regression test generated: {test_path}")
        
        # Run regression tests
        logger.info("Running all regression tests")
        regression_results = verifier.run_regression_tests()
        logger.info(f"Regression test results: {regression_results['passed']}/{regression_results['tests_run']} passed")
        
        # Export verification report
        report_path = verifier.export_verification_report()
        logger.info(f"Verification report exported to {report_path}")
        
        # Print summary
        print("\n" + "="*80)
        print("AUTO VERIFICATION DEMO SUMMARY")
        print("="*80)
        
        print(f"\nProject Root: {project_root}")
        print(f"Verification Directory: {os.path.join(project_root, '.verification')}")
        
        print("\nFixes Applied:")
        for i, fix in enumerate(project_info["fixes"], 1):
            result = verification_results[i-1]
            status = "✓ VERIFIED" if result["verified"] else "✗ FAILED"
            print(f"  {i}. {fix['description']} ({fix['file']} line {fix['line']}) - {status}")
        
        print("\nRegression Tests:")
        print(f"  Tests Run: {regression_results['tests_run']}")
        print(f"  Tests Passed: {regression_results['passed']}")
        print(f"  Tests Failed: {regression_results['failed']}")
        
        print(f"\nVerification Report: {report_path}")
        print("\nDemo completed successfully!")
        
    except Exception as e:
        logger.exception(f"Error running demo: {e}")
    
    finally:
        # Cleanup if needed
        if temp_dir and not keep_files:
            logger.info(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto Verification Demo")
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Directory to store demo outputs"
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep temporary files after demo"
    )
    
    args = parser.parse_args()
    
    run_demo(output_dir=args.output_dir, keep_files=args.keep_files)
