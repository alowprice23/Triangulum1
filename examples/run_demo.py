"""
This script demonstrates the multi-agent communication framework.
"""

import asyncio

from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus
from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.message import AgentMessage, MessageType


async def main():
    """
    The main function for the demo.
    """
    message_bus = EnhancedMessageBus()

    orchestrator = OrchestratorAgent(
        agent_id="orchestrator",
        message_bus=message_bus,
    )

    relationship_analyst = RelationshipAnalystAgent(
        agent_id="relationship_analyst",
        message_bus=message_bus,
    )

    # Start the workflow by sending a message to the orchestrator.
    start_message = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={"action": "start"},
        sender="user",
        receiver="orchestrator",
    )
    await message_bus.publish(start_message)

    # Wait for all messages to be processed.
    message_bus.wait_for_completion()


if __name__ == "__main__":
    asyncio.run(main())
