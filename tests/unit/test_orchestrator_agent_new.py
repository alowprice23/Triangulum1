import unittest
import asyncio
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus

class TestOrchestratorAgentNew(unittest.TestCase):
    def test_handle_message(self):
        async def run_test():
            message_bus = EnhancedMessageBus()
            orchestrator = OrchestratorAgent(message_bus=message_bus)
            message = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"action": "test"},
                sender="test"
            )
            await orchestrator.handle_message(message)
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
