#!/usr/bin/env python3
"""
Agent System Demo - Demonstrates the Triangulum agent system in action.

This example shows how to use the Triangulum agent system components,
including BaseAgent, AgentFactory, and RelationshipAnalystAgent.
"""

import os
import logging
import json
import time
from typing import Dict, Any

from triangulum_lx.agents.message_bus import MessageBus
from triangulum_lx.agents.agent_factory import AgentFactory
from triangulum_lx.agents.message import MessageType
from triangulum_lx.agents.relationship_analyst_agent import RelationshipAnalystAgent
from triangulum_lx.agents.base_agent import BaseAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleAgent(BaseAgent):
    """Simple example agent that responds to task requests."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def _handle_task_request(self, message):
        """Handle a task request message."""
        task = message.content.get("task", "")
        logger.info(f"SimpleAgent {self.agent_id} handling task: {task}")
        
        # Process the task
        result = f"Completed task: {task}"
        
        # Send a response
        self.send_response(
            original_message=message,
            message_type=MessageType.TASK_RESULT,
            content={"result": result}
        )
    
    def _handle_query(self, message):
        """Handle a query message."""
        query = message.content.get("query", "")
        logger.info(f"SimpleAgent {self.agent_id} handling query: {query}")
        
        # Process the query
        answer = f"Answer to: {query}"
        
        # Send a response
        self.send_response(
            original_message=message,
            message_type=MessageType.QUERY_RESPONSE,
            content={"answer": answer}
        )


def setup_agent_system():
    """Set up the agent system with message bus and factory."""
    # Create a message bus
    message_bus = MessageBus()
    
    # Create an agent factory
    factory = AgentFactory(message_bus=message_bus)
    
    # Register agent types
    factory.register_agent_type("simple", SimpleAgent)
    factory.register_agent_type("relationship_analyst", RelationshipAnalystAgent)
    
    return message_bus, factory


def run_simple_agent_demo(factory):
    """Run a simple agent demo with task requests and queries."""
    # Create a few agents
    coordinator = factory.create_agent(
        agent_type="simple",
        agent_id="coordinator",
        config={"role": "coordinator"}
    )
    
    worker1 = factory.create_agent(
        agent_type="simple",
        agent_id="worker1",
        config={"role": "worker"}
    )
    
    worker2 = factory.create_agent(
        agent_type="simple",
        agent_id="worker2",
        config={"role": "worker"}
    )
    
    # Send task requests
    coordinator.send_message(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "Process data file"},
        receiver=worker1.agent_id
    )
    
    coordinator.send_message(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "Generate report"},
        receiver=worker2.agent_id
    )
    
    # Send queries
    worker1.send_message(
        message_type=MessageType.QUERY,
        content={"query": "What is the status of the system?"},
        receiver=coordinator.agent_id
    )
    
    # Give time for message processing
    time.sleep(0.1)
    
    # Show active agents
    logger.info(f"Active agents: {list(factory._active_agents.keys())}")
    
    # Shut down agents
    factory.shutdown_all_agents()
    logger.info("All agents shut down")


def run_relationship_analysis_demo(factory, target_dir):
    """Run a demo of the relationship analyst agent."""
    # Create a relationship analyst agent
    relationships_path = "demo_relationships.json"
    analyst = factory.create_agent(
        agent_type="relationship_analyst",
        agent_id="relationship_analyst",
        config={"relationships_path": relationships_path}
    )
    
    # Create a coordinator agent to interact with the analyst
    coordinator = factory.create_agent(
        agent_type="simple",
        agent_id="coordinator"
    )
    
    # Step 1: Analyze the directory
    logger.info(f"Analyzing directory: {target_dir}")
    coordinator.send_message(
        message_type=MessageType.TASK_REQUEST,
        content={
            "task": "analyze directory",
            "directory": target_dir,
            "task_id": 1
        },
        receiver=analyst.agent_id
    )
    
    # Give time for analysis to complete
    time.sleep(0.5)
    
    # Step 2: Query information about a specific file
    target_file = os.path.join(target_dir, "triangulum_lx/agents/base_agent.py")
    if os.path.exists(target_file):
        logger.info(f"Getting relationships for file: {target_file}")
        coordinator.send_message(
            message_type=MessageType.TASK_REQUEST,
            content={
                "task": "get relationships for file",
                "file": target_file,
                "task_id": 2
            },
            receiver=analyst.agent_id
        )
        
        # Give time for task to complete
        time.sleep(0.2)
        
        # Step 3: Ask what files would be affected by changes
        logger.info(f"Querying affected files for: {target_file}")
        coordinator.send_message(
            message_type=MessageType.QUERY,
            content={
                "query": "What files are affected by changes to this file?",
                "file": target_file
            },
            receiver=analyst.agent_id
        )
        
        # Give time for query to complete
        time.sleep(0.2)
        
        # Step 4: Get relationship between two files
        file2 = os.path.join(target_dir, "triangulum_lx/agents/relationship_analyst_agent.py")
        if os.path.exists(file2):
            logger.info(f"Querying relationship between files")
            coordinator.send_message(
                message_type=MessageType.QUERY,
                content={
                    "query": "What's the relationship between these files?",
                    "files": [target_file, file2]
                },
                receiver=analyst.agent_id
            )
            
            # Give time for query to complete
            time.sleep(0.2)
    
    # Shut down agents
    factory.shutdown_all_agents()
    logger.info("All agents shut down")
    
    # Check if relationships were saved
    if os.path.exists(relationships_path):
        logger.info(f"Relationships saved to: {relationships_path}")
        # Display some statistics
        with open(relationships_path, 'r') as f:
            relationships = json.load(f)
            file_count = len(relationships)
            
            # Count total relationships
            import_count = sum(len(info.get("imports", [])) for info in relationships.values())
            imported_by_count = sum(len(info.get("imported_by", [])) for info in relationships.values())
            
            logger.info(f"Analysis stats: {file_count} files, {import_count} imports, {imported_by_count} imported_by relationships")


def main():
    """Main function to run the demo."""
    message_bus, factory = setup_agent_system()
    
    logger.info("=== Running Simple Agent Demo ===")
    run_simple_agent_demo(factory)
    
    logger.info("\n=== Running Relationship Analysis Demo ===")
    # Use the current directory as the target for analysis
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_relationship_analysis_demo(factory, current_dir)


if __name__ == "__main__":
    main()
