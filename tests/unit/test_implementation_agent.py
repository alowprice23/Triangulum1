"""
Unit tests for the Implementation Agent.

These tests verify the advanced capabilities of the enhanced Implementation Agent,
including code analysis, patch generation, validation, backup/rollback, and metrics.
"""

import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from triangulum_lx.agents.implementation_agent import ImplementationAgent, ImplementationMetrics
from triangulum_lx.agents.message import AgentMessage, MessageType


class TestImplementationAgent(unittest.TestCase):
    """Test cases for the enhanced Implementation Agent."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Set up the implementation agent with test configuration
        self.agent = ImplementationAgent(
            agent_id="test_implementation_agent",
            config={
                "backup_dir": os.path.join(self.test_dir, "backups"),
                "validate_patches": True,
                "progressive_patching": True
            }
        )
        
        # Create test files
        self.null_pointer_file = os.path.join(self.test_dir, "null_pointer_test.py")
        with open(self.null_pointer_file, "w") as f:
            f.write("""
def process_data(data):
    # Null pointer bug: data might be None
    return data.get('key')

def main():
    result = process_data(None)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
""")
        
        self.resource_leak_file = os.path.join(self.test_dir, "resource_leak_test.py")
        with open(self.resource_leak_file, "w") as f:
            f.write("""
def read_file_content(filename):
    # Resource leak: file is not properly closed
    f = open(filename, 'r')
    content = f.read()
    return content

def main():
    content = read_file_content('example.txt')
    print(f"Content length: {len(content)}")

if __name__ == "__main__":
    main()
""")
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)
    
    def test_metrics_collection(self):
        """Test the metrics collection functionality."""
        metrics = ImplementationMetrics()
        
        # Record implementations
        metrics.start_implementation()
        metrics.end_implementation(
            success=True,
            files_changed=2,
            patch_size=512,
            language="python",
            bug_type="null_pointer"
        )
        
        metrics.start_implementation()
        metrics.end_implementation(
            success=False,
            files_changed=1,
            patch_size=256,
            language="python",
            bug_type="resource_leak"
        )
        
        # Record validation and rollback
        metrics.record_validation(True)
        metrics.record_rollback()
        
        # Get summary
        summary = metrics.get_summary()
        
        # Verify metrics
        self.assertEqual(summary["total_implementations"], 2)
        # Check success rate instead of specific count values
        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["rollback_rate"], 0.5)
        self.assertEqual(summary["language_distribution"]["python"], 2)
        self.assertEqual(summary["bug_type_distribution"]["null_pointer"], 1)
        self.assertEqual(summary["bug_type_distribution"]["resource_leak"], 1)
    
    def test_implement_null_pointer_strategy(self):
        """Test implementation of a null pointer bug fix strategy."""
        # Create a strategy for null pointer bug
        strategy = {
            "id": "strategy_null_pointer",
            "name": "Fix null pointer bug",
            "description": "Add null check before accessing object properties",
            "bug_type": "null_pointer",
            "bug_location": self.null_pointer_file,
            "bug_line": 4,  # Line with data.get('key')
            "bug_code": "return data.get('key')",
            "confidence": 0.9,
            "affected_files": [self.null_pointer_file]
        }
        
        # Generate implementation
        implementation = self.agent.implement_strategy(strategy)
        
        # Verify implementation details
        self.assertIsNotNone(implementation)
        self.assertEqual(implementation["bug_type"], "null_pointer")
        self.assertEqual(implementation["bug_location"], self.null_pointer_file)
        self.assertGreater(len(implementation.get("patches", [])), 0)
        self.assertGreaterEqual(implementation.get("confidence_level", 0), 0.1)
        
        # Verify patch contains a null check
        patch = implementation.get("patches", [])[0]
        changes = patch.get("changes", [])
        self.assertGreater(len(changes), 0)
        
        change_content = changes[0].get("content", "")
        self.assertIn("None", change_content)  # Should have None check
    
    def test_implement_resource_leak_strategy(self):
        """Test implementation of a resource leak bug fix strategy."""
        # Create a strategy for resource leak bug
        strategy = {
            "id": "strategy_resource_leak",
            "name": "Fix resource leak bug",
            "description": "Use context manager to ensure file is closed",
            "bug_type": "resource_leak",
            "bug_location": self.resource_leak_file,
            "bug_line": 4,  # Line with f = open(filename, 'r')
            "bug_code": "f = open(filename, 'r')",
            "confidence": 0.9,
            "affected_files": [self.resource_leak_file]
        }
        
        # Generate implementation
        implementation = self.agent.implement_strategy(strategy)
        
        # Verify implementation details
        self.assertIsNotNone(implementation)
        self.assertEqual(implementation["bug_type"], "resource_leak")
        self.assertEqual(implementation["bug_location"], self.resource_leak_file)
        self.assertGreater(len(implementation.get("patches", [])), 0)
        self.assertGreaterEqual(implementation.get("confidence_level", 0), 0.1)
        
        # Verify patch contains a context manager (with statement)
        patch = implementation.get("patches", [])[0]
        changes = patch.get("changes", [])
        self.assertGreater(len(changes), 0)
        
        change_content = changes[0].get("content", "")
        self.assertIn("with", change_content)  # Should use with statement
    
    def test_apply_implementation(self):
        """Test applying an implementation to files."""
        # Create a strategy for null pointer bug
        strategy = {
            "id": "strategy_null_pointer",
            "name": "Fix null pointer bug",
            "description": "Add null check before accessing object properties",
            "bug_type": "null_pointer",
            "bug_location": self.null_pointer_file,
            "bug_line": 4,  # Line with data.get('key')
            "bug_code": "return data.get('key')",
            "confidence": 0.9,
            "affected_files": [self.null_pointer_file]
        }
        
        # Generate implementation
        implementation = self.agent.implement_strategy(strategy)
        
        # Apply implementation
        application_result = self.agent.apply_implementation(
            implementation=implementation,
            dry_run=False,
            progressive=True,
            validate_after_each_file=True
        )
        
        # Verify application result
        self.assertIsNotNone(application_result)
        self.assertEqual(application_result.get("status"), "success")
        self.assertEqual(len(application_result.get("files_modified", [])), 1)
        self.assertEqual(len(application_result.get("files_failed", [])), 0)
        
        # Verify file was actually modified
        with open(self.null_pointer_file, 'r') as f:
            modified_content = f.read()
            self.assertIn("None", modified_content)  # Should have None check
    
    def test_rollback_implementation(self):
        """Test rolling back an implementation."""
        # Create a strategy for null pointer bug
        strategy = {
            "id": "strategy_null_pointer",
            "name": "Fix null pointer bug",
            "description": "Add null check before accessing object properties",
            "bug_type": "null_pointer",
            "bug_location": self.null_pointer_file,
            "bug_line": 4,  # Line with data.get('key')
            "bug_code": "return data.get('key')",
            "confidence": 0.9,
            "affected_files": [self.null_pointer_file]
        }
        
        # Save original content
        with open(self.null_pointer_file, 'r') as f:
            original_content = f.read()
        
        # Generate and apply implementation
        implementation = self.agent.implement_strategy(strategy)
        application_result = self.agent.apply_implementation(implementation)
        
        # Verify file was modified
        with open(self.null_pointer_file, 'r') as f:
            modified_content = f.read()
            self.assertNotEqual(original_content, modified_content)
        
        # Rollback implementation
        rollback_result = self.agent.rollback_implementation(
            implementation_id=implementation.get("implementation_id")
        )
        
        # Verify rollback result
        self.assertIsNotNone(rollback_result)
        self.assertEqual(rollback_result.get("status"), "success")
        self.assertEqual(len(rollback_result.get("files_restored", [])), 1)
        
        # Verify file was restored to original content
        with open(self.null_pointer_file, 'r') as f:
            restored_content = f.read()
            self.assertEqual(original_content, restored_content)
    
    @patch('triangulum_lx.agents.implementation_agent.ImplementationAgent._validate_file_syntax')
    def test_validation_failure_handling(self, mock_validate_syntax):
        """Test handling of validation failures."""
        # Mock validation to fail
        mock_validate_syntax.return_value = {
            "success": False,
            "file": self.null_pointer_file,
            "errors": ["Syntax error: invalid syntax"]
        }
        
        # Create a strategy for null pointer bug
        strategy = {
            "id": "strategy_null_pointer",
            "name": "Fix null pointer bug",
            "description": "Add null check before accessing object properties",
            "bug_type": "null_pointer",
            "bug_location": self.null_pointer_file,
            "bug_line": 4,  # Line with data.get('key')
            "bug_code": "return data.get('key')",
            "confidence": 0.9,
            "affected_files": [self.null_pointer_file]
        }
        
        # Save original content
        with open(self.null_pointer_file, 'r') as f:
            original_content = f.read()
        
        # Generate implementation
        implementation = self.agent.implement_strategy(strategy)
        
        # Apply implementation - should rollback due to validation failure
        application_result = self.agent.apply_implementation(
            implementation=implementation,
            validate_after_each_file=True
        )
        
        # Verify application result shows failure
        self.assertIsNotNone(application_result)
        self.assertIn(application_result.get("status"), ["failed", "partial_success"])
        self.assertEqual(len(application_result.get("files_failed", [])), 1)
        
        # Verify file was rolled back (not modified)
        with open(self.null_pointer_file, 'r') as f:
            final_content = f.read()
            self.assertEqual(original_content, final_content)
    
    def test_runtime_environment_detection(self):
        """Test runtime environment detection."""
        runtime_info = self.agent._detect_runtime_environment()
        
        # Verify runtime info contains expected keys
        self.assertIn("os", runtime_info)
        self.assertIn("python_version", runtime_info)
        self.assertIn("platform", runtime_info)
        self.assertIn("detected_languages", runtime_info)
    
    def test_message_handling(self):
        """Test message handling in the agent."""
        # Create a strategy
        strategy = {
            "id": "strategy_test",
            "name": "Test strategy",
            "bug_type": "null_pointer",
            "bug_location": self.null_pointer_file,
            "bug_line": 4
        }
        
        # Mock implementation method to avoid actual implementation
        self.agent.implement_strategy = MagicMock(return_value={
            "implementation_id": "test_impl_id",
            "patches": [{"file_path": self.null_pointer_file, "changes": []}]
        })
        
        # Create a task request message
        message = AgentMessage(
            sender="test_sender",
            receiver=self.agent.agent_id,
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "implement_strategy",
                "strategy": strategy
            }
        )
        
        # Mock send_response method
        self.agent.send_response = MagicMock()
        
        # Handle the message
        self.agent._handle_task_request(message)
        
        # Verify implement_strategy was called with the strategy
        self.agent.implement_strategy.assert_called_once_with(
            strategy=strategy,
            additional_context=None
        )
        
        # Verify send_response was called with TASK_RESULT
        self.agent.send_response.assert_called_once()
        call_args = self.agent.send_response.call_args[1]
        self.assertEqual(call_args["message_type"], MessageType.TASK_RESULT)
        self.assertEqual(call_args["content"]["status"], "success")


if __name__ == "__main__":
    unittest.main()
