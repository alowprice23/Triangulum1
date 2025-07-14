import asyncio
import logging
import enum
from typing import Dict, Any, Optional

from .base_agent import BaseAgent
from .message import AgentMessage, MessageType

logger = logging.getLogger(__name__)

class TaskPriority(enum.IntEnum):
    """Priority levels for tasks in the Orchestrator's queue."""
    CRITICAL = 0    # Highest priority - security issues, blocking bugs
    HIGH = 1        # High priority - serious bugs, performance issues
    MEDIUM = 2      # Medium priority - non-blocking bugs, minor issues
    LOW = 3         # Low priority - enhancements, refactoring
    BACKGROUND = 4  # Lowest priority - non-essential tasks

class OrchestratorAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(agent_type="orchestrator", **kwargs)

    async def _handle_task_request(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        action = message.content.get("action")
        if action == "orchestrate_folder_healing":
            return await self._handle_folder_healing(message)
        else:
            return await self.send_error_response(message, f"Unknown action: {action}")

    async def _handle_query(self, message: AgentMessage):
        await self.send_error_response(message, "Queries not yet implemented")

    async def _handle_folder_healing(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        folder_path = message.content.get("folder_path")
        if not folder_path:
            return await self.send_error_response(message, "folder_path is required")

        # For now, just send a success message.
        # In the future, this will be where the workflow logic goes.
        return await self.send_response(
            message,
            MessageType.TASK_RESULT,
            {"status": "success"}
        )

    async def send_error_response(self, original_message: AgentMessage, error: str) -> Optional[Dict[str, Any]]:
        return await self.send_response(
            original_message,
            MessageType.ERROR,
            {"error": error}
        )
