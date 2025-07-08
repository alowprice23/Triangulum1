"""
Unit tests for the PatcherAgent class.

Tests the functionality of the PatcherAgent, including bug analysis,
patch generation, application, verification, and rollback.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import shutil
from pathlib import Path

from triangulum_lx.tooling.repair import PatcherAgent
from triangulum_lx.tooling.test_runner import TestResult


class TestPatcherAgent(unittest.TestCase):
    """Test cases for the PatcherAgent class."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
        # Create a simple Python file with a bug
        self.bug_file = os.path.join(self.test_dir, 'buggy_file.py')
        with open(self.bug_file, 'w') as f:
            f.write("""
def add(a, b):
    # Bug: This function has a bug
    return a - b  # Should be a + b
            """)
        
        # Create a test file for the buggy file
        self.test_file = os.path.join(self.test_dir, 'test_buggy_file.py')
        with open(self.test_file, 'w') as f:
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
        
        # Initialize the PatcherAgent
        self.agent = PatcherAgent()
        
        # Mock the relationship analyzer and provider
        self.agent.relationship_analyzer = MagicMock()
        self.agent.relationship_provider = MagicMock()
        
        # Set up the relationship provider to return test data
        self.agent.relationship_provider.get_context_for_repair.return_value = {
            'functions': ['add'],
            'complexity': {'functions': 1, 'classes': 0},
            'impact': {'risk_level': 'low'}
        }
        self.agent.relationship_provider.get_impact_analysis.return_value = {
            'risk_level': 'low',
            'direct_dependents': [],
            'indirect_dependents': []
        }
        self.agent.relationship_provider.get_related_files.return_value = []
        
        # Mock the test runner
        self.agent.test_runner = MagicMock()
        
        # Task for testing
        self.task = {
            'bug_id': 'TEST-001',
            'file_path': self.bug_file,
            'bug_description': 'Addition function subtracts instead of adding'
        }
    
    def tearDown(self):
        """Clean up after the test."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_analyze(self):
        """Test the _analyze method."""
        # Mock the open function to return file content
        with patch('builtins.open', mock_open(read_data="def add(a, b): return a - b")):
            context = self.agent._analyze(self.task)
            
            # Check that the analysis includes expected data
            self.assertEqual(context['file_path'], self.bug_file)
            self.assertEqual(context['bug_id'], 'TEST-001')
            self.assertEqual(context['bug_description'], 'Addition function subtracts instead of adding')
            
            # Check that it called the relationship provider
            self.agent.relationship_provider.get_context_for_repair.assert_called_once_with(self.bug_file)
            self.agent.relationship_provider.get_impact_analysis.assert_called_once_with(self.bug_file)
    
    def test_generate_patch(self):
        """Test the _generate_patch method."""
        context = {
            'file_path': self.bug_file,
            'bug_id': 'TEST-001',
            'file_content': "def add(a, b): return a - b",
            'impact_analysis': {'risk_level': 'low'},
            'related_files': []
        }
        
        patch = self.agent._generate_patch(self.task, context)
        
        # Check that patch contains expected data
        self.assertEqual(patch['bug_id'], 'TEST-001')
        self.assertEqual(patch['file_path'], self.bug_file)
        self.assertIn('patch_diff', patch)
        self.assertEqual(patch['impact_level'], 'low')
        self.assertEqual(patch['related_files'], [])
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_apply(self, mock_file, mock_exists):
        """Test the _apply method."""
        # Mock that the backup path exists
        mock_exists.return_value = True
        
        # Test with a git-style patch (starts with '---')
        git_patch_data = {
            'bug_id': 'TEST-001',
            'file_path': self.bug_file,
            'patch_diff': '--- file.py\n+++ file.py\n@@ -1,1 +1,1 @@\n-old\n+new',
            'impact_level': 'low',
            'related_files': []
        }
        
        # Mock the PatchBundle for git-style patches
        with patch('triangulum_lx.tooling.repair.PatchBundle') as MockPatchBundle:
            mock_bundle = MagicMock()
            MockPatchBundle.return_value = mock_bundle
            
            self.agent._apply(git_patch_data)
            
            # Check that it created a backup
            mock_file.assert_called()
            
            # Check that it applied the patch with PatchBundle
            MockPatchBundle.assert_called_once_with('TEST-001', git_patch_data['patch_diff'])
            mock_bundle.apply.assert_called_once()
            
            # Check that it tracked the applied patch
            self.assertTrue(hasattr(self.agent, 'applied_patches'))
            self.assertEqual(self.agent.applied_patches['primary']['file_path'], self.bug_file)
        
        # Reset mocks
        mock_file.reset_mock()
        
        # Test with direct content replacement (no git-style patch)
        direct_patch_data = {
            'bug_id': 'TEST-001',
            'file_path': self.bug_file,
            'patch_diff': 'def add(a, b): return a + b',
            'impact_level': 'low',
            'related_files': []
        }
        
        # Apply direct content patch
        self.agent._apply(direct_patch_data)
        
        # Check that it created a backup and wrote the content directly
        mock_file.assert_called()
        write_call_args = mock_file().write.call_args_list
        self.assertTrue(len(write_call_args) > 0, "No write calls were made")
        self.assertEqual(write_call_args[-1][0][0], direct_patch_data['patch_diff'])
    
    def test_verify_success(self):
        """Test the _verify method with successful tests."""
        # Set up the test runner to find tests and return success
        self.agent.test_runner.find_related_tests.return_value = [self.test_file]
        self.agent.test_runner.validate_patch.return_value = TestResult(True, "Tests passed")
        
        result = self.agent._verify(self.task)
        
        # Check that it called the test runner
        self.agent.test_runner.find_related_tests.assert_called_once_with(self.bug_file)
        self.agent.test_runner.validate_patch.assert_called_once()
        
        # Check that the result indicates success
        self.assertTrue(result.success)
    
    def test_verify_failure(self):
        """Test the _verify method with failing tests."""
        # Set up the test runner to find tests and return failure
        self.agent.test_runner.find_related_tests.return_value = [self.test_file]
        self.agent.test_runner.validate_patch.return_value = TestResult(False, "Tests failed")
        
        result = self.agent._verify(self.task)
        
        # Check that it called the test runner
        self.agent.test_runner.find_related_tests.assert_called_once_with(self.bug_file)
        self.agent.test_runner.validate_patch.assert_called_once()
        
        # Check that the result indicates failure
        self.assertFalse(result.success)
    
    @patch('os.path.exists')
    @patch('os.remove')
    def test_rollback(self, mock_remove, mock_exists):
        """Test the _rollback method."""
        # Mock that the backup path exists
        mock_exists.return_value = True
        
        # Set up applied patches tracking
        self.agent.applied_patches = {
            'primary': {
                'file_path': self.bug_file,
                'backup_path': f"{self.bug_file}.bak"
            },
            'related': []
        }
        
        # Open will be mocked to simulate reading and writing files
        with patch('builtins.open', mock_open(read_data="Backup content")):
            patch_data = {
                'bug_id': 'TEST-001',
                'file_path': self.bug_file,
                'patch_diff': 'Test patch'
            }
            
            self.agent._rollback(patch_data)
            
            # Check that it restored from backup
            mock_exists.assert_called_with(f"{self.bug_file}.bak")
            mock_remove.assert_called_with(f"{self.bug_file}.bak")
    
    def test_execute_repair_success(self):
        """Test the execute_repair method with successful repair."""
        # Mock internal methods
        self.agent._analyze = MagicMock(return_value={'mock': 'context'})
        self.agent._generate_patch = MagicMock(return_value={'bug_id': 'TEST-001', 'file_path': self.bug_file})
        self.agent._apply = MagicMock()
        self.agent._verify = MagicMock(return_value=TestResult(True, "Tests passed"))
        self.agent._rollback = MagicMock()
        
        result = self.agent.execute_repair(self.task)
        
        # Check that it called all methods in sequence
        self.agent._analyze.assert_called_once_with(self.task)
        self.agent._generate_patch.assert_called_once()
        self.agent._apply.assert_called_once()
        self.agent._verify.assert_called_once_with(self.task)
        
        # Rollback should not be called on success
        self.agent._rollback.assert_not_called()
        
        # Check the result
        self.assertEqual(result, "SUCCESS")
    
    def test_execute_repair_failure(self):
        """Test the execute_repair method with failed verification."""
        # Mock internal methods
        self.agent._analyze = MagicMock(return_value={'mock': 'context'})
        self.agent._generate_patch = MagicMock(return_value={'bug_id': 'TEST-001', 'file_path': self.bug_file})
        self.agent._apply = MagicMock()
        self.agent._verify = MagicMock(return_value=TestResult(False, "Tests failed"))
        self.agent._rollback = MagicMock()
        
        result = self.agent.execute_repair(self.task)
        
        # Check that it called all methods in sequence
        self.agent._analyze.assert_called_once_with(self.task)
        self.agent._generate_patch.assert_called_once()
        self.agent._apply.assert_called_once()
        self.agent._verify.assert_called_once_with(self.task)
        
        # Rollback should be called on failure
        self.agent._rollback.assert_called_once()
        
        # Check the result
        self.assertTrue(result.startswith("FAILURE"))
    
    def test_integration(self):
        """Integration test with actual file operations."""
        # Create a corrected version of the buggy file
        fixed_content = """
def add(a, b):
    # Bug fixed: This function now correctly adds
    return a + b  # Corrected
        """
        
        # Mock _generate_patch to return a patch that would fix the file
        def mock_generate_patch(task, context):
            return {
                'bug_id': task['bug_id'],
                'file_path': task['file_path'],
                'patch_diff': fixed_content,
                'impact_level': 'low',
                'related_files': []
            }
        
        # Mock TestRunner.validate_patch to check if the file was actually fixed
        def mock_validate_patch(file_path, test_paths):
            # Read the current content of the file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check if the bug is fixed (looks for "return a + b")
            if "return a + b" in content:
                return TestResult(True, "Tests passed")
            else:
                return TestResult(False, "Tests failed")
        
        # Apply our mocks
        self.agent._generate_patch = MagicMock(side_effect=mock_generate_patch)
        self.agent.test_runner.find_related_tests.return_value = [self.test_file]
        self.agent.test_runner.validate_patch.side_effect = mock_validate_patch
        
        # Run the repair
        result = self.agent.execute_repair(self.task)
        
        # Check the result
        self.assertEqual(result, "SUCCESS")
        
        # Verify the file was actually changed
        with open(self.bug_file, 'r') as f:
            content = f.read()
        
        self.assertIn("return a + b", content)


if __name__ == '__main__':
    unittest.main()
