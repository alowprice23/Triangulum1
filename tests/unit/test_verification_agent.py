import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import tempfile
import shutil
import sys
from pathlib import Path

from triangulum_lx.agents.verification_agent import VerificationAgent
from triangulum_lx.agents.message import AgentMessage, MessageType

class TestVerificationAgent(unittest.TestCase):
    """Test cases for the VerificationAgent."""

    def setUp(self):
        """Set up the test environment."""
        self.message_bus = MagicMock()
        self.agent = VerificationAgent(
            agent_id="test_verification_agent",
            message_bus=self.message_bus,
            config={}
        )

    def test_determine_language(self):
        """Test determining language from file extension."""
        self.assertEqual(self.agent._determine_language("file.py"), "python")
        self.assertEqual(self.agent._determine_language("file.java"), "java")
        self.assertEqual(self.agent._determine_language("file.js"), "javascript")
        self.assertEqual(self.agent._determine_language("file.unknown"), "unknown")

    def test_calculate_confidence(self):
        """Test calculating confidence level."""
        checks_pass = {
            "syntax": {"success": True},
            "tests": {"success": True},
        }
        self.assertEqual(self.agent._calculate_confidence(checks_pass, "any"), 1.0)

        checks_fail = {
            "syntax": {"success": True},
            "tests": {"success": False},
        }
        self.assertEqual(self.agent._calculate_confidence(checks_fail, "any"), 0.5)

    def test_sandbox_creation_and_patching(self):
        """Test creating a sandbox and applying patches."""
        implementation = {
            "changes": [{
                "file_path": "new_dir/test_file.py",
                "new_content": "print('hello')"
            }]
        }
        with self.agent._create_verification_sandbox(implementation) as sandbox_path:
            sandbox_path_obj = Path(sandbox_path)
            self.assertTrue(sandbox_path_obj.exists())
            
            patch_result = self.agent._apply_patches_in_sandbox(implementation, sandbox_path)
            self.assertTrue(patch_result["success"])
            
            patched_file = sandbox_path_obj / "new_dir/test_file.py"
            self.assertTrue(patched_file.exists())
            with open(patched_file, "r") as f:
                content = f.read()
            self.assertEqual(content, "print('hello')")

    def test_verify_syntax(self):
        """Test the syntax verification method."""
        with tempfile.TemporaryDirectory() as sandbox_dir:
            # Valid syntax
            implementation_valid = { "changes": [{ "file_path": "valid.py", "new_content": "x = 1" }] }
            valid_file = Path(sandbox_dir) / "valid.py"
            with open(valid_file, "w") as f:
                f.write("x = 1")
            result_valid = self.agent._verify_syntax(implementation_valid, sandbox_dir, "any")
            self.assertTrue(result_valid["success"])

            # Invalid syntax
            implementation_invalid = { "changes": [{ "file_path": "invalid.py", "new_content": "x = 1 +" }] }
            invalid_file = Path(sandbox_dir) / "invalid.py"
            with open(invalid_file, "w") as f:
                f.write("x = 1 +")
            result_invalid = self.agent._verify_syntax(implementation_invalid, sandbox_dir, "any")
            self.assertFalse(result_invalid["success"])
            self.assertEqual(len(result_invalid["issues"]), 1)

    @patch('subprocess.run')
    def test_verify_tests(self, mock_subprocess_run):
        """Test the test verification method."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_subprocess_run.return_value = mock_process

        with tempfile.TemporaryDirectory() as sandbox_dir:
            result = self.agent._verify_tests({}, sandbox_dir, "any")
            self.assertTrue(result["success"])
            mock_subprocess_run.assert_called_once()

        mock_process.returncode = 1
        mock_process.stdout = "Test failed"
        mock_process.stderr = "Error details"
        with tempfile.TemporaryDirectory() as sandbox_dir:
            result = self.agent._verify_tests({}, sandbox_dir, "any")
            self.assertFalse(result["success"])
            self.assertEqual(len(result["issues"]), 1)

    @patch('subprocess.run')
    def test_verify_standards(self, mock_subprocess_run):
        """Test the standards verification method."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_subprocess_run.return_value = mock_process

        with tempfile.TemporaryDirectory() as sandbox_dir:
            implementation = { "changes": [{ "file_path": "code.py", "new_content": "x=1" }] }
            (Path(sandbox_dir) / "code.py").write_text("x=1")
            result = self.agent._verify_standards(implementation, sandbox_dir, "any")
            self.assertTrue(result["success"])
            mock_subprocess_run.assert_called_once()

    def test_handle_task_request(self):
        """Test handling a task request for verification."""
        implementation = {"strategy_id": "test_strat", "changes": []}
        message = AgentMessage(
            sender="test_sender",
            message_type=MessageType.TASK_REQUEST,
            content={"task": {"type": "verify_implementation", "implementation": implementation}}
        )
        
        with patch.object(self.agent, 'verify_implementation') as mock_verify:
            mock_verify.return_value = {"overall_success": True, "confidence": 1.0}
            response = self.agent._handle_task_request(message)
            mock_verify.assert_called_once_with(implementation, None, None)
            self.assertIsInstance(response, AgentMessage)
            self.assertEqual(response.message_type, MessageType.TASK_RESULT)
            self.assertTrue(response.content["success"])

    def test_handle_query(self):
        """Test handling a query for verification results."""
        self.agent.verification_results["test_id"] = {"status": "complete"}
        message = AgentMessage(
            sender="test_sender",
            message_type=MessageType.QUERY,
            content={"query": {"type": "get_verification_result", "implementation_id": "test_id"}}
        )
        response = self.agent._handle_query(message)
        self.assertIsInstance(response, AgentMessage)
        self.assertEqual(response.message_type, MessageType.QUERY_RESPONSE)
        self.assertEqual(response.content["result"], {"status": "complete"})

if __name__ == "__main__":
    unittest.main()
