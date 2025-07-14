import unittest
import asyncio
import os
import tempfile
import shutil
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus

class TempTest(unittest.TestCase):
    def test_empty_folder(self):
        async def run_test():
            message_bus = EnhancedMessageBus()

            response_received = asyncio.Future()

            def response_handler(message: AgentMessage):
                response_received.set_result(message.content)

            message_bus.subscribe(
                agent_id="test",
                callback=response_handler,
                message_types=[MessageType.TASK_RESULT]
            )

            orchestrator = OrchestratorAgent(message_bus=message_bus)
            message = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"action": "orchestrate_folder_healing", "folder_path": self.test_dir},
                sender="test"
            )
            await orchestrator.handle_message(message)

            response = await asyncio.wait_for(response_received, timeout=5.0)

            self.assertIsNotNone(response)
            self.assertEqual(response["status"], "success")

        self.test_dir = tempfile.mkdtemp()
        asyncio.run(run_test())
        shutil.rmtree(self.test_dir)

if __name__ == '__main__':
    unittest.main()
