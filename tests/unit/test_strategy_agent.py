"""
Unit tests for the StrategyAgent.

These tests ensure that the StrategyAgent correctly formulates repair strategies
for different types of bugs and evaluates strategies against constraints.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import json

from triangulum_lx.agents.strategy_agent import StrategyAgent
from triangulum_lx.agents.message import AgentMessage, MessageType


class TestStrategyAgent(unittest.TestCase):
    """Test cases for the StrategyAgent."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create the agent with a mock message bus
        self.message_bus = MagicMock()
        self.agent = StrategyAgent(
            agent_id="test_strategy_agent",
            agent_type="strategy_formulation",
            message_bus=self.message_bus
        )
    
    def test_determine_bug_type(self):
        """Test determining the bug type from a bug report."""
        # Test with pattern_id
        bug_report = {"pattern_id": "null_pointer", "description": "Test bug"}
        self.assertEqual(self.agent._determine_bug_type(bug_report), "null_pointer")
        
        # Test with error_type
        bug_report = {"error_type": "NullPointerException", "description": "Test bug"}
        self.assertEqual(self.agent._determine_bug_type(bug_report), "null_pointer")
        
        # Test with description
        bug_report = {"description": "Resource leak detected"}
        self.assertEqual(self.agent._determine_bug_type(bug_report), "resource_leak")
        
        # Test with generic
        bug_report = {"description": "Unknown bug"}
        self.assertEqual(self.agent._determine_bug_type(bug_report), "generic")
    
    def test_formulate_strategy_null_pointer(self):
        """Test formulating a strategy for a null pointer bug."""
        bug_report = {
            "pattern_id": "null_pointer",
            "file": "test.py",
            "line": 10,
            "code": "result = data.get_value()",
            "description": "Potential null/None reference",
            "severity": "high"
        }
        
        code_context = {
            "language": "python",
            "file_content": "def process(data):\n    result = data.get_value()\n    return result"
        }
        
        strategy = self.agent.formulate_strategy(bug_report, code_context)
        
        # Verify the strategy
        self.assertEqual(strategy["bug_type"], "null_pointer")
        self.assertEqual(strategy["bug_location"], "test.py")
        self.assertEqual(strategy["bug_line"], 10)
        self.assertEqual(len(strategy["repair_steps"]), 4)  # 4 steps in the template
        self.assertGreater(len(strategy["code_examples"]), 0)
    
    def test_formulate_strategy_resource_leak(self):
        """Test formulating a strategy for a resource leak bug."""
        bug_report = {
            "pattern_id": "resource_leak",
            "file": "test.py",
            "line": 5,
            "code": "f = open('data.txt', 'r')",
            "description": "Resource opened but not properly closed",
            "severity": "medium"
        }
        
        code_context = {
            "language": "python",
            "file_content": "def read_file():\n    f = open('data.txt', 'r')\n    data = f.read()\n    return data"
        }
        
        strategy = self.agent.formulate_strategy(bug_report, code_context)
        
        # Verify the strategy
        self.assertEqual(strategy["bug_type"], "resource_leak")
        self.assertEqual(strategy["bug_location"], "test.py")
        self.assertEqual(strategy["bug_line"], 5)
        self.assertEqual(len(strategy["repair_steps"]), 4)  # 4 steps in the template
        self.assertGreater(len(strategy["code_examples"]), 0)
    
    def test_evaluate_strategy_acceptable(self):
        """Test evaluating an acceptable strategy."""
        strategy = {
            "repair_steps": [{"description": "Step 1"}, {"description": "Step 2"}],
            "affected_files": ["file1.py", "file2.py"]
        }
        
        constraints = {
            "max_complexity": 5,
            "max_changes": 10,
            "max_files": 3,
            "restricted_areas": []
        }
        
        evaluation = self.agent.evaluate_strategy(strategy, constraints)
        
        # Verify the evaluation
        self.assertTrue(evaluation["acceptable"])
        self.assertGreaterEqual(evaluation["score"], 60)
        self.assertEqual(len(evaluation["issues"]), 0)
    
    def test_evaluate_strategy_unacceptable(self):
        """Test evaluating an unacceptable strategy."""
        strategy = {
            "repair_steps": [{"description": "Step 1"}, {"description": "Step 2"}],
            "affected_files": ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
        }
        
        constraints = {
            "max_complexity": 2,
            "max_changes": 1,
            "max_files": 1,
            "restricted_areas": []
        }
        
        evaluation = self.agent.evaluate_strategy(strategy, constraints)
        
        # Verify the evaluation
        self.assertFalse(evaluation["acceptable"])
        self.assertLess(evaluation["score"], 60)
        self.assertGreater(len(evaluation["issues"]), 0)
    
    def test_extract_variables(self):
        """Test extracting variables from code."""
        # Test with assignment
        code = "result = data.get_value()"
        variables = self.agent._extract_variables(code)
        self.assertIn("result", variables)
        
        # Test with function parameters
        code = "def process(data, options=None):\n    result = data.get_value()\n    return result"
        variables = self.agent._extract_variables(code)
        self.assertIn("data", variables)
        self.assertIn("options", variables)
        
        # Test with type annotations
        code = "def process(data: Dict, options: Optional[List] = None):\n    result = data.get_value()\n    return result"
        variables = self.agent._extract_variables(code)
        self.assertIn("data", variables)
        self.assertIn("options", variables)
    
    def test_handle_task_request_formulate_strategy(self):
        """Test handling a task request to formulate a strategy."""
        bug_report = {
            "pattern_id": "null_pointer",
            "file": "test.py",
            "line": 10,
            "code": "result = data.get_value()",
            "description": "Potential null/None reference",
            "severity": "high"
        }
        
        code_context = {
            "language": "python",
            "file_content": "def process(data):\n    result = data.get_value()\n    return result"
        }
        
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "formulate_strategy",
                "bug_report": bug_report,
                "code_context": code_context
            },
            sender="test_sender"
        )
        
        # Handle the message
        self.agent._handle_task_request(message)
        
        # Verify that send_response was called with the correct arguments
        self.agent.message_bus.publish.assert_called_once()
        response_msg = self.agent.message_bus.publish.call_args[0][0]
        self.assertEqual(response_msg.message_type, MessageType.TASK_RESULT)
        self.assertEqual(response_msg.content["status"], "success")
        self.assertIn("strategy", response_msg.content)
    
    def test_handle_query_get_strategy_templates(self):
        """Test handling a query for strategy templates."""
        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={
                "query_type": "get_strategy_templates",
                "bug_type": "null_pointer"
            },
            sender="test_sender"
        )
        
        # Handle the message
        self.agent._handle_query(message)
        
        # Verify that send_response was called with the correct arguments
        self.agent.message_bus.publish.assert_called_once()
        response_msg = self.agent.message_bus.publish.call_args[0][0]
        self.assertEqual(response_msg.message_type, MessageType.QUERY_RESPONSE)
        self.assertEqual(response_msg.content["status"], "success")
        self.assertIn("templates", response_msg.content)
        self.assertEqual(response_msg.content["template_count"], 1)
    
    def test_handle_error_messages(self):
        """Test handling error cases."""
        # Test with invalid action
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "invalid_action"
            },
            sender="test_sender"
        )
        
        # Handle the message
        self.agent._handle_task_request(message)
        
        # Verify that send_response was called with an error message
        self.agent.message_bus.publish.assert_called_once()
        response_msg = self.agent.message_bus.publish.call_args[0][0]
        self.assertEqual(response_msg.message_type, MessageType.ERROR)
        self.assertEqual(response_msg.content["status"], "error")
        self.assertIn("Unknown action", response_msg.content["error"])
    
    def test_handle_other_message(self):
        """Test handling other types of messages."""
        # Create a test strategy
        self.agent.successful_strategies = {
            "test_strategy": {
                "verified": False,
                "bug_type": "null_pointer"
            }
        }
        
        # Create a verification result message
        message = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            content={
                "verification_result": True,
                "strategy_id": "test_strategy",
                "success": True
            },
            sender="verification_agent"
        )
        
        # Handle the message
        self.agent._handle_other_message(message)
        
        # Verify that the strategy was updated
        self.assertTrue(self.agent.successful_strategies["test_strategy"]["verified"])


if __name__ == "__main__":
    unittest.main()
