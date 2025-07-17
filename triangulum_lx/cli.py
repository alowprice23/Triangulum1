"""
This module defines the command-line interface for the Triangulum system.
"""

import click

from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus
from triangulum_lx.agents.folder_healing_orchestrator import FolderHealingOrchestrator
from triangulum_lx.agents.bug_detector_agent import BugDetectorAgent
from triangulum_lx.agents.strategy_agent import StrategyAgent
from triangulum_lx.agents.implementation_agent import ImplementationAgent
from triangulum_lx.agents.verification_agent import VerificationAgent
from triangulum_lx.agents.message import AgentMessage, MessageType


@click.group()
def cli():
    """
    A command-line interface for the Triangulum system.
    """
    pass


@cli.command(name="heal-folder")
@click.argument("folder_path")
def heal_folder(folder_path: str):
    """
    Heals a folder by detecting and fixing bugs.
    """
    message_bus = EnhancedMessageBus()

    orchestrator = FolderHealingOrchestrator(
        agent_id="folder_healing_orchestrator",
        message_bus=message_bus,
    )

    bug_detector = BugDetectorAgent(
        agent_id="bug_detector",
        message_bus=message_bus,
    )

    strategy_agent = StrategyAgent(
        agent_id="strategy",
        message_bus=message_bus,
    )

    implementation_agent = ImplementationAgent(
        agent_id="implementation",
        message_bus=message_bus,
    )

    verification_agent = VerificationAgent(
        agent_id="verification",
        message_bus=message_bus,
    )

    # Start the workflow by sending a message to the orchestrator.
    start_message = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={"action": "heal_folder", "folder_path": folder_path},
        sender="user",
        receiver="folder_healing_orchestrator",
    )
    message_bus.publish(start_message)

    # Wait for all messages to be processed.
    message_bus.wait_for_completion()


if __name__ == "__main__":
    cli()
