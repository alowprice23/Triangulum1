"""
Enhanced Message Bus with Thought Chain Integration Demo

This example demonstrates how the Enhanced Message Bus integrates with
Thought Chain persistence to provide a record of agent communication.
"""

import os
import time
import uuid
import shutil
import logging
from typing import Dict, Any

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a temporary directory for thought chain storage
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "demo_thought_chains")
os.makedirs(STORAGE_DIR, exist_ok=True)


def agent_message_handler(message: AgentMessage) -> None:
    """Handler function for receiving messages."""
    logger.info(f"Agent received message: {message.message_id} from {message.sender}")
    logger.info(f"Message content: {message.content}")


def create_sample_message(sender: str, receiver: str = None, conversation_id: str = None,
                         reply_to: str = None, content: Dict[str, Any] = None) -> AgentMessage:
    """Create a sample message for demonstration purposes."""
    if content is None:
        content = {"task": "Sample task", "data": str(uuid.uuid4())}
        
    return AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content=content,
        sender=sender,
        receiver=receiver,
        conversation_id=conversation_id,
        reply_to=reply_to
    )


def main():
    """Run the Enhanced Message Bus with Thought Chain demo."""
    try:
        # Initialize the Enhanced Message Bus with thought chain persistence
        logger.info("Initializing Enhanced Message Bus with thought chain persistence...")
        message_bus = EnhancedMessageBus(
            delivery_guarantee=True,
            retry_interval=1.0,
            enable_thought_chain_persistence=True,
            thought_chain_storage_dir=STORAGE_DIR
        )

        # Create agent subscriptions
        logger.info("Creating agent subscriptions...")
        message_bus.subscribe(
            agent_id="agent1",
            callback=agent_message_handler,
            message_types=[MessageType.TASK_REQUEST, MessageType.TASK_RESPONSE]
        )
        
        message_bus.subscribe(
            agent_id="agent2",
            callback=agent_message_handler,
            message_types=[MessageType.TASK_REQUEST, MessageType.TASK_RESPONSE]
        )

        # Create a conversation ID to track the conversation
        conversation_id = str(uuid.uuid4())
        logger.info(f"Created conversation ID: {conversation_id}")

        # Send initial message in the conversation
        initial_message = create_sample_message(
            sender="agent1",
            receiver="agent2",
            conversation_id=conversation_id,
            content={"task": "Initial request", "data": "Please analyze this information"}
        )
        
        logger.info(f"Sending initial message: {initial_message.message_id}")
        message_bus.publish(initial_message)
        
        # Wait for delivery
        time.sleep(1)
        
        # Send a response message that replies to the initial message
        response_message = create_sample_message(
            sender="agent2",
            receiver="agent1",
            conversation_id=conversation_id,
            reply_to=initial_message.message_id,
            content={"task": "Response", "data": "Analysis complete", "result": "Positive"}
        )
        
        logger.info(f"Sending response message: {response_message.message_id}")
        message_bus.publish(response_message)
        
        # Wait for delivery
        time.sleep(1)
        
        # Send a follow-up message
        followup_message = create_sample_message(
            sender="agent1",
            receiver="agent2",
            conversation_id=conversation_id,
            reply_to=response_message.message_id,
            content={"task": "Follow-up", "data": "Additional information requested"}
        )
        
        logger.info(f"Sending follow-up message: {followup_message.message_id}")
        message_bus.publish(followup_message)
        
        # Wait for delivery
        time.sleep(1)

        # Retrieve the thought chain
        logger.info(f"Retrieving thought chain for conversation: {conversation_id}")
        thought_chain = message_bus.get_thought_chain(conversation_id)
        
        if thought_chain:
            logger.info(f"Retrieved thought chain: {thought_chain.chain_id}")
            logger.info(f"Chain name: {thought_chain.name}")
            logger.info(f"Chain description: {thought_chain.description}")
            logger.info(f"Number of nodes: {len(thought_chain)}")
            
            # Display the chain structure
            logger.info("Thought chain structure:")
            for i, node in enumerate(thought_chain):
                logger.info(f"Node {i+1}: {node.node_id} (Type: {node.thought_type})")
                logger.info(f"  Author: {node.author_agent_id}")
                logger.info(f"  Content: {node.content}")
                logger.info(f"  Metadata: {node.metadata}")
                logger.info(f"  Timestamp: {node.timestamp}")
                
                # Display child relationships
                children = thought_chain.get_children(node.node_id)
                if children:
                    logger.info(f"  Children: {[child.node_id for child in children]}")
                else:
                    logger.info("  Children: None")
                    
                logger.info("---")
            
            # List all available chains
            logger.info("All available thought chains:")
            chains = message_bus.list_thought_chains()
            for chain_meta in chains:
                logger.info(f"  {chain_meta.get('chain_id')}: {chain_meta.get('name')}")
        else:
            logger.error(f"No thought chain found for conversation: {conversation_id}")

        # Shutdown the message bus
        logger.info("Shutting down Enhanced Message Bus...")
        message_bus.shutdown()
        
    except Exception as e:
        logger.exception(f"Error in demo: {e}")
    finally:
        # Clean up storage directory
        if os.path.exists(STORAGE_DIR):
            logger.info(f"Cleaning up storage directory: {STORAGE_DIR}")
            shutil.rmtree(STORAGE_DIR)


if __name__ == "__main__":
    main()
