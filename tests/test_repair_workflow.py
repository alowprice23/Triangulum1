"""
Simple demonstration of the PatcherAgent's repair workflow.
"""

import os
import tempfile
import shutil
from pathlib import Path

from triangulum_lx.tooling.repair import PatcherAgent
from triangulum_lx.tooling.test_runner import TestResult

def setup_test_files():
    """Create test files in a temporary directory."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary test directory: {temp_dir}")
    
    # Create a simple Python file with a bug
    bug_file = os.path.join(temp_dir, 'buggy_file.py')
    with open(bug_file, 'w') as f:
        f.write("""
def add(a, b):
    # Bug: This function has a bug
    return a - b  # Should be a + b
        """)
    
    # Create a test file for the buggy file
    test_file = os.path.join(temp_dir, 'test_buggy_file.py')
    with open(test_file, 'w') as f:
        f.write("""
import unittest
from buggy_file import add

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)
        self.assertEqual(add(0, 0), 0)

if __name__ == '__main__':
    unittest.main()
        """)
    
    return temp_dir, bug_file, test_file

def cleanup(temp_dir):
    """Clean up the temporary directory."""
    try:
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning up: {e}")

def main():
    """Run the repair workflow demonstration."""
    # Set up the test environment
    temp_dir, bug_file, test_file = setup_test_files()
    
    try:
        # Initialize the PatcherAgent
        agent = PatcherAgent()
        print("Initialized PatcherAgent")
        
        # Set up mock dependencies
        # In a real scenario, these would be properly initialized
        agent.relationship_analyzer = type('MockAnalyzer', (), {
            'analyze_directory': lambda self, directory: None,
            'save_relationships': lambda self, path: None,
            'relationships': {}
        })()
        
        agent.relationship_provider = type('MockProvider', (), {
            'relationships': {'files': []},
            'get_context_for_repair': lambda self, file_path: {'complexity': 'low'},
            'get_impact_analysis': lambda self, file_path: {'risk_level': 'low'},
            'suggest_refactoring': lambda self, file_path: [],
            'get_related_files': lambda self, file_path, max_depth: [],
            'load_relationships': lambda self, relationships: None
        })()
        
        # Mock the test runner to simulate test validation
        agent.test_runner = type('MockTestRunner', (), {
            'find_related_tests': lambda self, file_path: [test_file],
            'validate_patch': lambda self, file_path, test_paths: TestResult(True, "Tests passed"),
            'run_specific_test': lambda self, test_path: TestResult(True, "Test passed")
        })()
        
        # Create a repair task
        task = {
            'bug_id': 'TEST-001',
            'file_path': bug_file,
            'bug_description': 'Addition function subtracts instead of adding'
        }
        
        # Create a fix for the bug
        fixed_content = """
def add(a, b):
    # Bug fixed: This function now correctly adds
    return a + b  # Corrected
        """
        
        # Override _generate_patch to return our fixed content
        original_generate_patch = agent._generate_patch
        agent._generate_patch = lambda t, c: {
            'bug_id': t['bug_id'],
            'file_path': t['file_path'],
            'patch_diff': fixed_content,
            'impact_level': 'low',
            'related_files': []
        }
        
        # Also override _apply to directly write the file rather than using PatchBundle
        # since PatchBundle relies on git which we don't have in this test environment
        original_apply = agent._apply
        def mock_apply(patch):
            file_path = patch['file_path']
            # Create backup
            backup_path = f"{file_path}.bak"
            with open(file_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                    
            # Apply patch by directly writing the new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(patch['patch_diff'])
                
            # Track applied patches
            agent.applied_patches = {
                'primary': {
                    'file_path': file_path,
                    'backup_path': backup_path
                },
                'related': []
            }
            
            print(f"Mock applied patch to {file_path}")
            
        agent._apply = mock_apply
        
        # Execute the repair
        print(f"Executing repair for file: {bug_file}")
        result = agent.execute_repair(task)
        print(f"Repair result: {result}")
        
        # Verify the file was actually changed
        with open(bug_file, 'r') as f:
            content = f.read()
        
        if "return a + b" in content:
            print("SUCCESS: Bug was fixed correctly!")
        else:
            print("FAILURE: Bug was not fixed.")
            print(f"Current file content: {content}")
        
    finally:
        # Clean up
        cleanup(temp_dir)

if __name__ == "__main__":
    main()
