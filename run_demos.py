"""
Demo Runner Script for Triangulum

This script helps locate and run the various demo files in the Triangulum project.
It provides a simple interface to list available demos and run them.
"""

import os
import sys
import subprocess
from pathlib import Path

def find_demo_files():
    """Find all demo files in the project."""
    demos = []
    
    # Look in examples directory
    examples_dir = Path("examples")
    if examples_dir.exists() and examples_dir.is_dir():
        for file in examples_dir.glob("*_demo.py"):
            demos.append(str(file))
    
    # Look in root directory
    for file in Path(".").glob("*_demo.py"):
        demos.append(str(file))
    
    return sorted(demos)

def list_demos():
    """List all available demos."""
    demos = find_demo_files()
    
    if not demos:
        print("No demo files found.")
        return
    
    print(f"Found {len(demos)} demo files:")
    for i, demo in enumerate(demos, 1):
        print(f"{i}. {demo}")

def run_demo(demo_path):
    """Run a specific demo."""
    if not os.path.exists(demo_path):
        print(f"Error: Demo file '{demo_path}' not found.")
        return False
    
    print(f"Running demo: {demo_path}")
    try:
        subprocess.run([sys.executable, demo_path], check=True)
        print(f"Demo completed: {demo_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running demo: {e}")
        return False

def main():
    """Main function."""
    print("Triangulum Demo Runner")
    print("=====================")
    
    # Check for specific demos mentioned in command line
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            list_demos()
            return
        
        # Try to run the specified demo
        demo_path = sys.argv[1]
        run_demo(demo_path)
        return
    
    # Interactive mode
    demos = find_demo_files()
    
    if not demos:
        print("No demo files found in examples/ directory or root directory.")
        print("Checking if files exist directly...")
        
        # Check if specific demo files exist
        specific_demos = [
            "examples/dependency_graph_demo.py",
            "examples/parallel_executor_demo.py",
            "examples/priority_analyzer_demo.py",
            "examples/verification_agent_demo.py",
            "examples/incremental_analyzer_demo.py"
        ]
        
        found_specific = []
        for demo in specific_demos:
            if os.path.exists(demo):
                found_specific.append(demo)
        
        if found_specific:
            print(f"Found {len(found_specific)} specific demo files:")
            for i, demo in enumerate(found_specific, 1):
                print(f"{i}. {demo}")
            
            demos = found_specific
        else:
            print("No specific demo files found either.")
            
            # List all Python files in examples directory
            examples_dir = Path("examples")
            if examples_dir.exists() and examples_dir.is_dir():
                print("\nAll Python files in examples directory:")
                for file in examples_dir.glob("*.py"):
                    print(f"  {file}")
            return
    else:
        print(f"Found {len(demos)} demo files:")
        for i, demo in enumerate(demos, 1):
            print(f"{i}. {demo}")
    
    try:
        choice = input("\nEnter the number of the demo to run (or 'q' to quit): ")
        if choice.lower() == 'q':
            return
        
        choice = int(choice)
        if 1 <= choice <= len(demos):
            run_demo(demos[choice - 1])
        else:
            print(f"Invalid choice. Please enter a number between 1 and {len(demos)}.")
    except ValueError:
        print("Invalid input. Please enter a number.")

if __name__ == "__main__":
    main()
