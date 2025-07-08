#!/usr/bin/env python3
"""
Triangulum Folder Debugger Demo

This script demonstrates how to use the Triangulum Folder Debugger to analyze and debug
a small project with several interconnected files.
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path

# Make sure triangulum_folder_debugger.py is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_folder_debugger import FolderDebugger

# Create a temporary directory for our demo files
demo_dir = tempfile.mkdtemp(prefix="triangulum_demo_")
print(f"Created demo directory: {demo_dir}")

# Define some sample files with bugs
files = {
    "main.py": """#!/usr/bin/env python3
\"\"\"
Main entry point for the demo application.
\"\"\"

import utils
import data_processor

def main():
    \"\"\"Main entry point.\"\"\"
    data = utils.load_data("sample.json")
    processed_data = data_processor.process_data(data)
    utils.save_results(processed_data)
    
    # Bug: Missing return statement
    # Should return processed_data

if __name__ == "__main__":
    main()
""",
    
    "utils.py": """#!/usr/bin/env python3
\"\"\"
Utility functions for the demo application.
\"\"\"

import json
import os

def load_data(filename):
    \"\"\"Load data from a JSON file.\"\"\"
    # Bug: Missing error handling for file not found
    with open(filename, 'r') as f:
        return json.load(f)

def save_results(data, filename="results.json"):
    \"\"\"Save results to a JSON file.\"\"\"
    # Bug: Doesn't create directory if it doesn't exist
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
""",
    
    "data_processor.py": """#!/usr/bin/env python3
\"\"\"
Data processing functions.
\"\"\"

def process_data(data):
    \"\"\"Process the input data.\"\"\"
    result = {}
    
    # Bug: Doesn't check if data is None
    for key, value in data.items():
        # Bug: Doesn't handle non-numeric values
        result[key] = value * 2
        
    return result

def validate_data(data):
    \"\"\"Validate the input data.\"\"\"
    # Bug: Function is defined but never used
    if not isinstance(data, dict):
        return False
    
    return all(isinstance(v, (int, float)) for v in data.values())
""",
    
    "test_utils.py": """#!/usr/bin/env python3
\"\"\"
Tests for utility functions.
\"\"\"

import unittest
import utils

class TestUtils(unittest.TestCase):
    
    def test_load_data(self):
        \"\"\"Test load_data function.\"\"\"
        # Bug: Test doesn't properly mock file operations
        data = utils.load_data("sample.json")
        self.assertIsNotNone(data)

if __name__ == "__main__":
    unittest.main()
"""
}

# Create the files in the demo directory
for filename, content in files.items():
    file_path = os.path.join(demo_dir, filename)
    with open(file_path, 'w') as f:
        f.write(content)
    print(f"Created {filename}")

# Create a dummy JSON file for testing
with open(os.path.join(demo_dir, "sample.json"), 'w') as f:
    f.write('{"a": 1, "b": 2, "c": "string"}')
print("Created sample.json")

print("\n=== Running Triangulum Folder Debugger ===\n")

# Set up the output directory
output_dir = os.path.join(demo_dir, "debug_output")
os.makedirs(output_dir, exist_ok=True)

try:
    # Initialize the folder debugger with analyze-only mode for this demo
    debugger = FolderDebugger(
        project_path=demo_dir,
        output_dir=output_dir,
        max_pass=1  # Use a lower pass level for faster demo
    )
    
    # Analyze the project
    debugger.analyze_project()
    
    # Get and display prioritized files
    prioritized_files = debugger.prioritize_files(['.py'])
    
    print("\nPrioritized Files:")
    for i, (file_path, priority) in enumerate(prioritized_files[:10], 1):
        print(f"{i:2d}. {os.path.basename(file_path)} (Priority: {priority:.4f})")
    
    # Generate a project health report
    debugger._generate_project_health_report(prioritized_files)
    print(f"\nProject health report saved to: {os.path.join(output_dir, 'project_health_report.md')}")
    
    # Ask user if they want to continue with debugging
    response = input("\nWould you like to debug the top 2 files? (y/n): ")
    
    if response.lower() in ('y', 'yes'):
        # Debug the top 2 files
        debug_summary = debugger.debug_project(max_files=2, extension_filter=['.py'])
        
        # Print summary
        print("\n=== Debug Summary ===")
        print(f"Files analyzed: {len(debugger.analyzer.id_to_file)}")
        print(f"Files debugged: {debug_summary['files_debugged']}")
        print(f"Bugs fixed: {debug_summary['bugs_fixed']}")
        success_rate = debug_summary['bugs_fixed'] / max(1, debug_summary['files_debugged'])
        print(f"Success rate: {success_rate:.2f}")
        
        print(f"\nFinal report saved to: {os.path.join(output_dir, 'project_debug_report.md')}")
    else:
        print("\nSkipping debugging phase. Demo complete.")

except Exception as e:
    print(f"Error during demo: {e}")

print(f"\nDemo files are located at: {demo_dir}")
print("You can examine these files and the debug output to understand how Triangulum Folder Debugger works.")
print("Once you're finished, you can delete the demo directory.")

# Optionally, uncomment to automatically clean up the demo directory
# shutil.rmtree(demo_dir)
