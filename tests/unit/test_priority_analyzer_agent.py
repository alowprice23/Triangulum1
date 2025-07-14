import unittest
import asyncio
from unittest.mock import MagicMock, patch
from triangulum_lx.agents.priority_analyzer_agent import PriorityAnalyzerAgent
from triangulum_lx.agents.message import AgentMessage, MessageType

class TestPriorityAnalyzerAgent(unittest.TestCase):
    def setUp(self):
        self.message_bus = MagicMock()
        self.agent = PriorityAnalyzerAgent(message_bus=self.message_bus)

    def test_initialization(self):
        self.assertEqual(self.agent.agent_type, "priority_analyzer")
        self.assertIn(MessageType.TASK_REQUEST, self.agent._subscribed_message_types)

    def test_analyze_priorities(self):
        bugs_by_file = {
            "file1.py": [{"severity": "high"}, {"severity": "low"}],
            "file2.py": [{"severity": "critical"}],
        }
        relationships = {
            "file1.py": {"dependencies": ["file2.py"], "dependents": []},
            "file2.py": {"dependencies": [], "dependents": ["file1.py"]},
        }
        
        priorities = self.agent.analyze_priorities("dummy_path", bugs_by_file, relationships)
        
        self.assertIn("file1.py", priorities)
        self.assertIn("file2.py", priorities)
        self.assertLess(priorities["file1.py"]["priority"], priorities["file2.py"]["priority"])

    async def test_handle_priority_analysis_request(self):
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            sender="test_agent",
            content={
                "action": "analyze_priorities",
                "folder_path": "/path/to/folder",
                "bugs_by_file": {"file1.py": []},
                "relationships": {},
            },
        )
        await self.agent.handle_message(message)
        self.message_bus.publish.assert_called_once()
        response = self.message_bus.publish.call_args[0][0]
        self.assertEqual(response.message_type, MessageType.TASK_RESULT)
        self.assertEqual(response.content["status"], "success")
        self.assertIn("file_priorities", response.content)

if __name__ == "__main__":
    unittest.main()
