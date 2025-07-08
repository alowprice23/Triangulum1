"""
Demonstration of the CodeFixer's ability to automatically fix code issues.
"""

import os
import sys
import logging
from pathlib import Path
import shutil

# Set up the Python path to include the Triangulum package
sys.path.insert(0, str(Path(__file__).parent.parent))

from triangulum_lx.verification.code_fixer import CodeFixer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to demonstrate the CodeFixer."""
    # Print header
    print("=" * 80)
    print("TRIANGULUM CODE FIXER DEMONSTRATION")
    print("=" * 80)
    
    # Initialize the CodeFixer
    code_fixer = CodeFixer()
    
    # Path to our example file with issues
    example_file = os.path.join('example_files', 'code_with_issues.py')
    fixed_file = os.path.join('example_files', 'code_fixed.py')
    
    # Create a copy of the original file to preserve it
    shutil.copy(example_file, fixed_file)
    
    print(f"\nOriginal file: {example_file}")
    with open(example_file, 'r') as f:
        original_code = f.read()
    
    print("\nOriginal code:")
    print("-" * 40)
    print(original_code)
    print("-" * 40)
    
    # Create verification results for different issue types
    verification_results = [
        {
            "bug_type": "hardcoded_credentials",
            "overall_success": False,
            "issues": ["Hardcoded credentials detected in the code"]
        },
        {
            "bug_type": "resource_leak",
            "overall_success": False,
            "issues": ["Resource leak detected in read_file_with_leak function"]
        },
        {
            "bug_type": "sql_injection", 
            "overall_success": False,
            "issues": ["SQL injection vulnerability detected in get_user function"]
        },
        {
            "bug_type": "exception_swallowing",
            "overall_success": False,
            "issues": ["Exception swallowing detected in divide function"]
        },
        {
            "bug_type": "null_pointer",
            "overall_success": False,
            "issues": ["Null pointer dereference detected in process_data function"]
        }
    ]
    
    # Fix each issue one by one
    for i, verification_result in enumerate(verification_results):
        print(f"\nFIX #{i+1}: {verification_result['bug_type'].upper()}")
        print(f"Issue: {verification_result['issues'][0]}")
        
        # Fix the code
        result = code_fixer.fix_code(fixed_file, verification_result)
        
        # Print results
        if result["success"]:
            print(f"✅ Fixed successfully! Applied {len(result['fixes_applied'])} fixes:")
            for fix in result["fixes_applied"]:
                print(f"  - {fix}")
            
            print("\nDiff:")
            print(result["diff"])
        else:
            print("❌ No fixes applied")
    
    # Show the final fixed code
    print("\nFinal fixed code:")
    print("-" * 40)
    with open(fixed_file, 'r') as f:
        fixed_code = f.read()
    print(fixed_code)
    print("-" * 40)
    
    print("\nAll issues have been fixed! 🎉")
    print("=" * 80)

if __name__ == "__main__":
    main()
