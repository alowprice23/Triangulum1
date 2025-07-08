"""
Agent Communication Demo - Demonstrates the Triangulum agent communication framework.

This script shows how the Triangulum agent communication protocol works,
with multiple agents communicating through the message bus.
"""

import logging
import time
import sys
import os
import json
from typing import Dict, Any, List, Optional

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.message import AgentMessage, MessageType, ConfidenceLevel
from triangulum_lx.agents.message_bus import MessageBus
from triangulum_lx.core.engine import TriangulumEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("agent_communication_demo")


class SimpleAgent:
    """
    A simple agent that can send and receive messages through the message bus.
    """
    
    def __init__(self, agent_id: str, role: str, message_bus: MessageBus):
        """
        Initialize the agent.
        
        Args:
            agent_id: Unique identifier for the agent
            role: Role of the agent (e.g., "analyzer", "planner", "executor")
            message_bus: Message bus for communication
        """
        self.agent_id = agent_id
        self.role = role
        self.message_bus = message_bus
        self.received_messages = []
        
        # Subscribe to the message bus
        self.message_bus.subscribe(
            agent_id=self.agent_id,
            callback=self.handle_message,
            message_types=None  # Subscribe to all message types
        )
        
        logger.info(f"Agent {self.agent_id} ({self.role}) initialized")
    
    def handle_message(self, message: AgentMessage):
        """
        Handle incoming messages.
        
        Args:
            message: Message to handle
        """
        logger.info(f"Agent {self.agent_id} received message: {message.message_type.value} from {message.sender}")
        self.received_messages.append(message)
        
        # Process message based on type
        if message.message_type == MessageType.TASK_REQUEST:
            self._process_task_request(message)
        elif message.message_type == MessageType.QUERY:
            self._process_query(message)
    
    def _process_task_request(self, message: AgentMessage):
        """
        Process a task request message.
        
        Args:
            message: Task request message
        """
        task = message.content.get("task", "")
        task_id = message.content.get("task_id", 0)
        
        # Simulate processing time
        time.sleep(0.5)
        
        # Generate a response based on the agent's role
        if self.role == "analyzer":
            result = f"Analysis of '{task}': This task involves code understanding."
            confidence = ConfidenceLevel.HIGH.value
        elif self.role == "planner":
            result = f"Plan for '{task}': 1. Analyze code, 2. Generate solution, 3. Implement fix"
            confidence = ConfidenceLevel.MEDIUM.value
        elif self.role == "executor":
            result = f"Executed '{task}' successfully"
            confidence = ConfidenceLevel.HIGH.value
        else:
            result = f"Processed '{task}' with default handling"
            confidence = ConfidenceLevel.MEDIUM.value
        
        # Send a response
        response = message.create_response(
            message_type=MessageType.TASK_RESULT,
            content={
                "task_id": task_id,
                "result": result
            },
            confidence=confidence
        )
        
        self.message_bus.publish(response)
    
    def _process_query(self, message: AgentMessage):
        """
        Process a query message.
        
        Args:
            message: Query message
        """
        query = message.content.get("query", "")
        
        # Simulate processing time
        time.sleep(0.2)
        
        # Generate a response based on the agent's role
        if self.role == "analyzer":
            answer = f"Analysis result for '{query}': Found 3 related functions."
        elif self.role == "planner":
            answer = f"Planning information for '{query}': Recommend approach B."
        elif self.role == "executor":
            answer = f"Execution information for '{query}': Ready to implement."
        else:
            answer = f"Default information for '{query}': No specific data available."
        
        # Send a response
        response = message.create_response(
            message_type=MessageType.QUERY_RESPONSE,
            content={
                "query": query,
                "answer": answer
            },
            confidence=ConfidenceLevel.HIGH.value
        )
        
        self.message_bus.publish(response)
    
    def send_task(self, receiver: str, task: str, task_id: int = 1):
        """
        Send a task request to another agent.
        
        Args:
            receiver: Agent to send the task to
            task: Task description
            task_id: ID of the task
        """
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "task": task,
                "task_id": task_id
            },
            sender=self.agent_id,
            receiver=receiver
        )
        
        logger.info(f"Agent {self.agent_id} sending task '{task}' to {receiver}")
        self.message_bus.publish(message)
    
    def send_query(self, receiver: str, query: str):
        """
        Send a query to another agent.
        
        Args:
            receiver: Agent to send the query to
            query: Query text
        """
        message = AgentMessage(
            message_type=MessageType.QUERY,
            content={
                "query": query
            },
            sender=self.agent_id,
            receiver=receiver
        )
        
        logger.info(f"Agent {self.agent_id} sending query '{query}' to {receiver}")
        self.message_bus.publish(message)
    
    def broadcast_status(self, status: str):
        """
        Broadcast a status message to all agents.
        
        Args:
            status: Status message
        """
        message = AgentMessage(
            message_type=MessageType.STATUS,
            content={
                "status": status,
                "agent_role": self.role
            },
            sender=self.agent_id
        )
        
        logger.info(f"Agent {self.agent_id} broadcasting status: {status}")
        self.message_bus.publish(message)


def run_demo():
    """Run the agent communication demo."""
    logger.info("Starting Agent Communication Demo")
    
    # Initialize the engine (which creates the message bus)
    engine = TriangulumEngine()
    message_bus = engine.message_bus
    
    # Create agents with different roles
    analyzer = SimpleAgent("analyzer_1", "analyzer", message_bus)
    planner = SimpleAgent("planner_1", "planner", message_bus)
    executor = SimpleAgent("executor_1", "executor", message_bus)
    
    # Have each agent broadcast their status
    analyzer.broadcast_status("Ready for code analysis")
    planner.broadcast_status("Ready for planning")
    executor.broadcast_status("Ready for execution")
    
    # Wait a moment for messages to be processed
    time.sleep(1)
    
    # Demonstrate direct task assignments
    analyzer.send_task("planner_1", "Create a plan for fixing bug #123")
    time.sleep(1)
    
    planner.send_task("executor_1", "Implement fix for bug #123 according to plan")
    time.sleep(1)
    
    # Demonstrate queries
    executor.send_query("analyzer_1", "What files are affected by bug #123?")
    time.sleep(1)
    
    # Demonstrate a multi-agent chain interaction
    logger.info("\n=== Starting Multi-Agent Interaction Chain ===")
    
    # Step 1: Analyzer identifies a bug
    analyzer.broadcast_status("Found potential bug in authentication module")
    time.sleep(0.5)
    
    # Step 2: Planner queries analyzer for details
    planner.send_query("analyzer_1", "What are the details of the authentication bug?")
    time.sleep(0.5)
    
    # Step 3: Planner creates a plan and sends to executor
    planner.send_task("executor_1", "Fix authentication bug: Update token validation")
    time.sleep(0.5)
    
    # Step 4: Executor asks for clarification
    executor.send_query("planner_1", "Which token validation method should be updated?")
    time.sleep(0.5)
    
    # Step 5: Executor reports completion
    executor.broadcast_status("Authentication bug fix implemented")
    time.sleep(0.5)
    
    # Print conversation summary
    logger.info("\n=== Conversation Summary ===")
    
    # Get all conversations - wrap in try/except in case there are errors accessing the conversations
    try:
        for conversation_id, conversation in message_bus._conversations.items():
            logger.info(f"Conversation {conversation_id}: {len(conversation.messages)} messages")
            
            # Print a few sample messages from each conversation
            for i, message in enumerate(conversation.messages[:3]):
                logger.info(f"  Message {i+1}: {message.message_type.value} from {message.sender} to {message.receiver or 'broadcast'}")
            
            if len(conversation.messages) > 3:
                logger.info(f"  ... and {len(conversation.messages) - 3} more messages")
    except Exception as e:
        logger.error(f"Error printing conversation summary: {e}")
    
    # Shutdown the engine
    try:
        engine.shutdown()
        logger.info("Agent Communication Demo completed")
    except Exception as e:
        logger.error(f"Error during engine shutdown: {e}")
        logger.info("Agent Communication Demo completed with errors")


if __name__ == "__main__":
    run_demo()
