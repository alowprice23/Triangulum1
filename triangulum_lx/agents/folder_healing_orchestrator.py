"""
This module defines the FolderHealingOrchestrator class.
"""

from typing import Dict, Any, Optional

from triangulum_lx.agents.base_agent import BaseAgent
from triangulum_lx.agents.message import AgentMessage, MessageType


class FolderHealingOrchestrator(BaseAgent):
    """
    The FolderHealingOrchestrator is responsible for managing the workflow for healing a folder.
    """

    def __init__(self, **kwargs):
        super().__init__(agent_type="folder_healing_orchestrator", **kwargs)

    async def _handle_task_request(self, message: AgentMessage) -> None:
        """
        Handles a task request message.
        """
        action = message.content.get("action")
        if action == "heal_folder":
            folder_path = message.content.get("folder_path")
            await self.send_message(
                message_type=MessageType.TASK_REQUEST,
                content={"action": "detect_bugs_in_folder", "folder_path": folder_path},
                receiver="bug_detector",
                parent_message_id=message.message_id,
                conversation_id=message.conversation_id,
            )

    async def _handle_task_result(self, message: AgentMessage) -> None:
        """
        Handles a task result message.
        """
        sender = message.sender
        content = message.content

        if sender == "bug_detector":
            await self.send_message(
                message_type=MessageType.TASK_REQUEST,
                content={"action": "generate_strategy", "bug_report": content},
                receiver="strategy",
                parent_message_id=message.message_id,
                conversation_id=message.conversation_id,
            )
        elif sender == "strategy":
            await self.send_message(
                message_type=MessageType.TASK_REQUEST,
                content={"action": "implement_strategy", "strategy": content},
                receiver="implementation",
                parent_message_id=message.message_id,
                conversation_id=message.conversation_id,
            )
        elif sender == "implementation":
            await self.send_message(
                message_type=MessageType.TASK_REQUEST,
                content={"action": "verify_implementation", "implementation": content},
                receiver="verification",
                parent_message_id=message.message_id,
                conversation_id=message.conversation_id,
            )
        elif sender == "verification":
            if content.get("overall_success"):
                await self.send_message_to_user("Folder healing complete.")
            else:
                await self.send_message(
                    message_type=MessageType.TASK_REQUEST,
                    content={"action": "generate_strategy", "bug_report": content},
                    receiver="strategy",
                    parent_message_id=message.message_id,
                    conversation_id=message.conversation_id,
                )

    async def _handle_query(self, message: AgentMessage) -> None:
        """
        Handles a query message.
        """
        pass
