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
from triangulum_lx.core.fs_state import FileSystemStateCache # Added import


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
        
        # Initialize the PatcherAgent with a mock FileSystemStateCache
        self.mock_fs_cache = MagicMock(spec=FileSystemStateCache)
        self.agent = PatcherAgent(fs_cache=self.mock_fs_cache)
        
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
    
    @patch('triangulum_lx.tooling.repair.Path')
    @patch('triangulum_lx.tooling.repair.atomic_write')
    @patch('triangulum_lx.tooling.repair.PatchBundle') # Keep this for git-style patch part
    def test_apply(self, MockPatchBundle, mock_atomic_write, mock_path_constructor):
        """Test the _apply method."""
        
        # --- Test with a git-style patch ---
        mock_original_content = b"original content for backup"
        mock_path_instance_for_read = MagicMock()
        mock_path_instance_for_read.read_bytes.return_value = mock_original_content

        # When Path(self.bug_file) is called for reading original content for backup
        mock_path_constructor.side_effect = lambda x: mock_path_instance_for_read if x == self.bug_file else MagicMock()

        git_patch_data = {
            'bug_id': 'TEST-001',
            'file_path': self.bug_file,
            'patch_diff': '--- file.py\n+++ file.py\n@@ -1,1 +1,1 @@\n-old\n+new', # Git-style
            'impact_level': 'low',
            'related_files': []
        }
        
        mock_bundle_instance = MockPatchBundle.return_value
        self.agent._apply(git_patch_data)
            
        # Check backup creation: Path(self.bug_file).read_bytes() and atomic_write for backup
        mock_path_constructor.assert_any_call(self.bug_file) # Called for read_bytes
        mock_path_instance_for_read.read_bytes.assert_called_once()
        expected_backup_path = f"{self.bug_file}.bak"
        mock_atomic_write.assert_any_call(expected_backup_path, mock_original_content)
            
        # Check PatchBundle usage
        MockPatchBundle.assert_called_once_with(
            git_patch_data['bug_id'],
            git_patch_data['patch_diff'],
            fs_cache=self.agent.fs_cache # Check if fs_cache is passed
        )
        mock_bundle_instance.apply.assert_called_once()

        # Check that fs_cache.invalidate was called for the main file after PatchBundle.apply()
        self.agent.fs_cache.invalidate.assert_any_call(self.bug_file)
            
        self.assertTrue(hasattr(self.agent, 'applied_patches'))
        self.assertEqual(self.agent.applied_patches['primary']['file_path'], self.bug_file)

        # Reset mocks for the next part of the test
        mock_atomic_write.reset_mock()
        mock_path_constructor.reset_mock()
        mock_path_instance_for_read.reset_mock()
        # Ensure fs_cache mock is fresh or re-mocked if necessary for PatcherAgent instance
        self.agent.fs_cache.invalidate.reset_mock()


        # --- Test with direct content replacement ---
        # Path(self.bug_file).read_bytes() will be called again for backup
        mock_path_constructor.side_effect = lambda x: mock_path_instance_for_read if x == self.bug_file else MagicMock()

        direct_patch_data = {
            'bug_id': 'TEST-002',
            'file_path': self.bug_file,
            'patch_diff': 'def add(a, b): return a + b', # Not a git diff
            'impact_level': 'low',
            'related_files': []
        }
        
        self.agent._apply(direct_patch_data)
        
        # Check backup creation again
        mock_path_instance_for_read.read_bytes.assert_called_once() # Called once in this section
        mock_atomic_write.assert_any_call(expected_backup_path, mock_original_content)

        # Check direct atomic_write for the patch content
        mock_atomic_write.assert_any_call(self.bug_file, direct_patch_data['patch_diff'].encode('utf-8'))

        # Check that fs_cache.invalidate was called for the main file
        self.agent.fs_cache.invalidate.assert_any_call(self.bug_file)
    
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
    
    @patch('triangulum_lx.tooling.repair.Path')
    @patch('triangulum_lx.tooling.repair.atomic_write')
    @patch('triangulum_lx.tooling.repair.atomic_delete')
    def test_rollback(self, mock_atomic_delete, mock_atomic_write, mock_path_constructor):
        """Test the _rollback method."""
        backup_file_path = f"{self.bug_file}.bak"
        backup_content = b"Backup content from rollback"

        # Mock fs_cache.exists and fs_cache.invalidate for the backup file
        self.agent.fs_cache.exists = MagicMock(return_value=True)
        self.agent.fs_cache.invalidate = MagicMock() # Mock invalidate method

        # Mock Path(backup_file_path).read_bytes()
        mock_backup_path_instance = MagicMock()
        mock_backup_path_instance.read_bytes.return_value = backup_content

        # Configure mock_path_constructor to return the correct mock for the backup path
        def path_side_effect(p):
            if str(p) == backup_file_path:
                return mock_backup_path_instance
            return MagicMock() # Default mock for other Path calls
        mock_path_constructor.side_effect = path_side_effect

        # Set up applied patches tracking (as PatcherAgent expects)
        self.agent.applied_patches = {
            'primary': {
                'file_path': self.bug_file,
                'backup_path': backup_file_path  # Store the full path
            },
            'related': []
        }
        
        patch_data = { # This is passed to _rollback, but its content isn't directly used by _rollback itself
            'bug_id': 'TEST-001',
            'file_path': self.bug_file
        }
            
        self.agent._rollback(patch_data)
            
        # Check that it checked for backup, read it, wrote to original, and deleted backup
        self.agent.fs_cache.exists.assert_called_with(backup_file_path)
        mock_path_constructor.assert_any_call(backup_file_path) # Check Path() was called for backup
        mock_backup_path_instance.read_bytes.assert_called_once()
        mock_atomic_write.assert_called_once_with(self.bug_file, backup_content)
        mock_atomic_delete.assert_called_once_with(backup_file_path)

        # Verify cache invalidations
        self.agent.fs_cache.invalidate.assert_any_call(self.bug_file)
        self.agent.fs_cache.invalidate.assert_any_call(backup_file_path)
    
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
