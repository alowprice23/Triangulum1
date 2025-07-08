#!/usr/bin/env python3
"""
Enhanced Message Bus Demo

This demo showcases the advanced features of the Enhanced Message Bus:
1. Message filtering by topic, priority, and source
2. Reliable broadcast capabilities with delivery confirmation
3. Integration with thought chains for context preservation
4. Error handling for malformed messages
5. Performance metrics tracking
6. Circuit breaker pattern for failure isolation
7. Timeout handling for long-running operations
8. Large message handling with chunking and compression
"""

import os
import sys
import time
import logging
import threading
import random
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.agents.message import AgentMessage, MessageType, ConfidenceLevel
from triangulum_lx.agents.enhanced_message_bus import (
    EnhancedMessageBus, MessagePriority, CircuitBreaker, CircuitState
)
from triangulum_lx.agents.thought_chain_manager import ThoughtChainManager
from triangulum_lx.agents.thought_chain import ThoughtChain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("enhanced_message_bus_demo")


class DemoAgent:
    """
    Demo agent for testing the enhanced message bus.
    
    This agent can send and receive messages, and can be configured to
    simulate various behaviors like slow processing, errors, etc.
    """
    
    def __init__(self, 
                 agent_id: str, 
                 message_bus: EnhancedMessageBus,
                 error_rate: float = 0.0,
                 slow_rate: float = 0.0,
                 slow_duration: float = 2.0):
        """
        Initialize the demo agent.
        
        Args:
            agent_id: ID of the agent
            message_bus: Message bus to use
            error_rate: Probability of simulating an error (0.0-1.0)
            slow_rate: Probability of simulating slow processing (0.0-1.0)
            slow_duration: Duration of slow processing in seconds
        """
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.error_rate = error_rate
        self.slow_rate = slow_rate
        self.slow_duration = slow_duration
        self.received_messages = []
        self.lock = threading.RLock()
        
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id=self.agent_id,
            callback=self.handle_message,
            message_types=None,  # Subscribe to all message types
            priority=MessagePriority.NORMAL
        )
        
        logger.info(f"Agent {agent_id} initialized")
    
    def handle_message(self, message: AgentMessage) -> None:
        """
        Handle a received message.
        
        Args:
            message: Message to handle
        """
        # Simulate errors
        if random.random() < self.error_rate:
            logger.warning(f"Agent {self.agent_id} simulating error for message {message.message_id}")
            raise RuntimeError(f"Simulated error in agent {self.agent_id}")
        
        # Simulate slow processing
        if random.random() < self.slow_rate:
            logger.info(f"Agent {self.agent_id} simulating slow processing for message {message.message_id}")
            time.sleep(self.slow_duration)
        
        # Store the message
        with self.lock:
            self.received_messages.append(message)
        
        logger.info(f"Agent {self.agent_id} received message {message.message_id} of type {message.message_type}")
        
        # Automatically respond to task requests
        if message.message_type == MessageType.TASK_REQUEST:
            self.send_response(message)
    
    def send_message(self, 
                    message_type: MessageType, 
                    content: Dict[str, Any],
                    receiver: Optional[str] = None,
                    priority: MessagePriority = MessagePriority.NORMAL) -> str:
        """
        Send a message.
        
        Args:
            message_type: Type of message to send
            content: Content of the message
            receiver: Receiver of the message (None for broadcast)
            priority: Priority of the message
            
        Returns:
            str: ID of the sent message
        """
        # Create the message
        message = AgentMessage(
            message_type=message_type,
            content=content,
            sender=self.agent_id,
            receiver=receiver
        )
        
        # Publish the message
        result = self.message_bus.publish(
            message=message,
            priority=priority
        )
        
        logger.info(f"Agent {self.agent_id} sent message {message.message_id} of type {message_type}")
        
        return message.message_id
    
    def send_response(self, request: AgentMessage) -> str:
        """
        Send a response to a request.
        
        Args:
            request: Request message to respond to
            
        Returns:
            str: ID of the response message
        """
        # Create a response message
        response = request.create_response(
            message_type=MessageType.TASK_RESULT,
            content={
                "result": f"Task completed by {self.agent_id}",
                "timestamp": time.time()
            },
            confidence=0.95
        )
        
        # Publish the response
        result = self.message_bus.publish(response)
        
        logger.info(f"Agent {self.agent_id} sent response {response.message_id} to request {request.message_id}")
        
        return response.message_id
    
    def get_received_messages(self) -> List[AgentMessage]:
        """
        Get all received messages.
        
        Returns:
            List[AgentMessage]: List of received messages
        """
        with self.lock:
            return self.received_messages.copy()


def demo_basic_messaging():
    """Demonstrate basic messaging capabilities."""
    print("\n=== Basic Messaging Demo ===")
    
    # Create message bus
    message_bus = EnhancedMessageBus()
    
    # Create agents
    agent1 = DemoAgent("agent1", message_bus)
    agent2 = DemoAgent("agent2", message_bus)
    agent3 = DemoAgent("agent3", message_bus)
    
    # Send a direct message
    print("\nSending direct message from agent1 to agent2...")
    agent1.send_message(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "process_data", "data": [1, 2, 3]},
        receiver="agent2"
    )
    
    # Wait for processing
    time.sleep(0.5)
    
    # Send a broadcast message
    print("\nSending broadcast message from agent3...")
    agent3.send_message(
        message_type=MessageType.STATUS,
        content={"status": "ready", "timestamp": time.time()}
    )
    
    # Wait for processing
    time.sleep(0.5)
    
    # Check received messages
    print("\nReceived messages:")
    for agent in [agent1, agent2, agent3]:
        messages = agent.get_received_messages()
        print(f"  Agent {agent.agent_id}: {len(messages)} messages")
        for msg in messages:
            print(f"    - {msg.message_type.value} from {msg.sender}")
    
    # Get performance metrics
    metrics = message_bus.get_performance_metrics()
    print("\nPerformance Metrics:")
    print(f"  Total messages: {metrics.total_messages}")
    print(f"  Successful deliveries: {metrics.successful_deliveries}")
    print(f"  Failed deliveries: {metrics.failed_deliveries}")
    print(f"  Average delivery time: {metrics.average_delivery_time:.6f} seconds")


def demo_message_filtering():
    """Demonstrate message filtering capabilities."""
    print("\n=== Message Filtering Demo ===")
    
    # Create message bus
    message_bus = EnhancedMessageBus()
    
    # Create agents with filters
    agent1 = DemoAgent("agent1", message_bus)
    
    # Subscribe agent2 with topic filter
    agent2 = DemoAgent("agent2", message_bus)
    message_bus.subscribe(
        agent_id="agent2",
        callback=agent2.handle_message,
        message_types=None,
        filters={"topic": "security"}
    )
    
    # Subscribe agent3 with source filter
    agent3 = DemoAgent("agent3", message_bus)
    message_bus.subscribe(
        agent_id="agent3",
        callback=agent3.handle_message,
        message_types=None,
        filters={"source": "agent1"}
    )
    
    # Send messages with different topics
    print("\nSending messages with different topics...")
    
    # Message with security topic (should reach agent1 and agent2)
    agent1.send_message(
        message_type=MessageType.STATUS,
        content={"status": "alert", "level": "high"},
        receiver=None,  # Broadcast
        priority=MessagePriority.HIGH
    )
    
    # Add topic to metadata
    message = AgentMessage(
        message_type=MessageType.STATUS,
        content={"status": "alert", "level": "high"},
        sender="agent1",
        receiver=None,  # Broadcast
        metadata={"topic": "security"}
    )
    message_bus.publish(message)
    
    # Message with performance topic (should reach agent1 and agent3)
    message = AgentMessage(
        message_type=MessageType.STATUS,
        content={"status": "normal", "metrics": {"cpu": 0.5, "memory": 0.3}},
        sender="agent1",
        receiver=None,  # Broadcast
        metadata={"topic": "performance"}
    )
    message_bus.publish(message)
    
    # Wait for processing
    time.sleep(0.5)
    
    # Check received messages
    print("\nReceived messages:")
    for agent in [agent1, agent2, agent3]:
        messages = agent.get_received_messages()
        print(f"  Agent {agent.agent_id}: {len(messages)} messages")
        for msg in messages:
            topic = msg.metadata.get("topic", "none")
            print(f"    - {msg.message_type.value} from {msg.sender} (topic: {topic})")


def demo_priority_based_delivery():
    """Demonstrate priority-based message delivery."""
    print("\n=== Priority-Based Delivery Demo ===")
    
    # Create message bus
    message_bus = EnhancedMessageBus()
    
    # Create agents
    agent1 = DemoAgent("agent1", message_bus)
    agent2 = DemoAgent("agent2", message_bus)
    
    # Send messages with different priorities
    print("\nSending messages with different priorities...")
    
    # Low priority message
    agent1.send_message(
        message_type=MessageType.STATUS,
        content={"status": "info", "message": "System running normally"},
        receiver="agent2",
        priority=MessagePriority.LOW
    )
    
    # Normal priority message
    agent1.send_message(
        message_type=MessageType.STATUS,
        content={"status": "warning", "message": "Disk space low"},
        receiver="agent2",
        priority=MessagePriority.NORMAL
    )
    
    # High priority message
    agent1.send_message(
        message_type=MessageType.STATUS,
        content={"status": "error", "message": "Network connection lost"},
        receiver="agent2",
        priority=MessagePriority.HIGH
    )
    
    # Critical priority message
    agent1.send_message(
        message_type=MessageType.STATUS,
        content={"status": "critical", "message": "System failure imminent"},
        receiver="agent2",
        priority=MessagePriority.CRITICAL
    )
    
    # Wait for processing
    time.sleep(0.5)
    
    # Check received messages (should be in order of priority)
    print("\nReceived messages (should be in order of priority):")
    messages = agent2.get_received_messages()
    for i, msg in enumerate(messages):
        priority = "unknown"
        if "status" in msg.content:
            priority = msg.content["status"]
        print(f"  {i+1}. {priority}: {msg.content.get('message', '')}")


def demo_error_handling():
    """Demonstrate error handling capabilities."""
    print("\n=== Error Handling Demo ===")
    
    # Create message bus
    message_bus = EnhancedMessageBus()
    
    # Create agents with error simulation
    agent1 = DemoAgent("agent1", message_bus)
    agent2 = DemoAgent("agent2", message_bus, error_rate=0.5)  # 50% chance of error
    
    # Send multiple messages to demonstrate retry and circuit breaker
    print("\nSending messages to agent with simulated errors...")
    for i in range(10):
        agent1.send_message(
            message_type=MessageType.TASK_REQUEST,
            content={"task": f"task_{i}", "data": f"data_{i}"},
            receiver="agent2"
        )
        time.sleep(0.1)
    
    # Wait for processing
    time.sleep(1.0)
    
    # Get performance metrics
    metrics = message_bus.get_performance_metrics()
    print("\nPerformance Metrics after error simulation:")
    print(f"  Total messages: {metrics.total_messages}")
    print(f"  Successful deliveries: {metrics.successful_deliveries}")
    print(f"  Failed deliveries: {metrics.failed_deliveries}")
    print(f"  Retried deliveries: {metrics.retried_deliveries}")
    print(f"  Circuit breaker trips: {metrics.circuit_breaker_trips}")
    
    # Check circuit breaker state
    circuit_breaker = message_bus._circuit_breakers.get("agent2")
    if circuit_breaker:
        print(f"\nCircuit breaker state for agent2: {circuit_breaker.state.name}")
        print(f"Failure count: {circuit_breaker.failure_count}")
    
    # Wait for circuit breaker reset timeout
    if circuit_breaker and circuit_breaker.state == CircuitState.OPEN:
        reset_time = circuit_breaker.reset_timeout - (time.time() - circuit_breaker.last_failure_time)
        if reset_time > 0:
            print(f"\nWaiting {reset_time:.1f} seconds for circuit breaker reset timeout...")
            time.sleep(reset_time + 0.1)
        
        # Send another message to test half-open state
        print("\nSending message to test half-open state...")
        agent1.send_message(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test_half_open", "data": "test_data"},
            receiver="agent2"
        )
        
        time.sleep(0.5)
        
        print(f"Circuit breaker state after test: {circuit_breaker.state.name}")


def demo_timeout_handling():
    """Demonstrate timeout handling capabilities."""
    print("\n=== Timeout Handling Demo ===")
    
    # Create message bus
    message_bus = EnhancedMessageBus()
    
    # Create agents with slow processing
    agent1 = DemoAgent("agent1", message_bus)
    agent2 = DemoAgent("agent2", message_bus, slow_rate=1.0, slow_duration=2.0)  # Always slow
    
    # Subscribe with timeout
    message_bus.subscribe(
        agent_id="agent2",
        callback=agent2.handle_message,
        timeout=1.0  # 1 second timeout
    )
    
    # Send a message
    print("\nSending message to agent with slow processing...")
    agent1.send_message(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "slow_task", "data": "test_data"},
        receiver="agent2"
    )
    
    # Wait for processing
    time.sleep(3.0)
    
    # Get performance metrics
    metrics = message_bus.get_performance_metrics()
    print("\nPerformance Metrics after timeout:")
    print(f"  Total messages: {metrics.total_messages}")
    print(f"  Successful deliveries: {metrics.successful_deliveries}")
    print(f"  Failed deliveries: {metrics.failed_deliveries}")
    print(f"  Timeouts: {metrics.timeouts}")


def demo_large_message_handling():
    """Demonstrate large message handling capabilities."""
    print("\n=== Large Message Handling Demo ===")
    
    # Create message bus
    message_bus = EnhancedMessageBus()
    
    # Create agents
    agent1 = DemoAgent("agent1", message_bus)
    agent2 = DemoAgent("agent2", message_bus)
    
    # Create a large message
    print("\nCreating and sending a large message...")
    large_content = {
        "task": "process_large_data",
        "data": {
            "text": "x" * 1000000,  # 1MB of text
            "numbers": list(range(10000))
        }
    }
    
    # Send the large message
    message = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content=large_content,
        sender="agent1",
        receiver="agent2"
    )
    
    # Publish the message
    result = message_bus.publish(message)
    
    # Wait for processing
    time.sleep(1.0)
    
    # Check if the message was chunked
    print(f"Message was chunked: {result.get('chunked', False)}")
    if result.get('chunked', False):
        print(f"Number of chunks: {result.get('chunks', 0)}")
    
    # Check received messages
    messages = agent2.get_received_messages()
    chunked_messages = [m for m in messages if m.is_chunked]
    print(f"\nReceived {len(chunked_messages)} chunked messages")
    
    # Try to reassemble the message
    if chunked_messages:
        reassembled = message_bus.reassemble_chunked_message(chunked_messages)
        if reassembled:
            print("Successfully reassembled the chunked message")
            print(f"Reassembled message type: {reassembled.message_type}")
            print(f"Reassembled message size: {len(json.dumps(reassembled.content))} bytes")
        else:
            print("Failed to reassemble the chunked message")


def demo_thought_chain_integration():
    """Demonstrate thought chain integration."""
    print("\n=== Thought Chain Integration Demo ===")
    
    # Create thought chain manager
    thought_chain_manager = ThoughtChainManager()
    
    # Create message bus with thought chain integration
    message_bus = EnhancedMessageBus(thought_chain_manager=thought_chain_manager)
    
    # Create agents
    agent1 = DemoAgent("agent1", message_bus)
    agent2 = DemoAgent("agent2", message_bus)
    
    # Create a conversation with multiple messages
    print("\nCreating a conversation with multiple messages...")
    
    # First message
    message_id1 = agent1.send_message(
        message_type=MessageType.QUERY,
        content={"query": "What is the status of the system?"},
        receiver="agent2"
    )
    
    time.sleep(0.2)
    
    # Get the message to create a response
    message1 = message_bus.get_message(message_id1)
    
    # Response to first message
    response1 = message1.create_response(
        message_type=MessageType.QUERY_RESPONSE,
        content={"response": "The system is running normally."}
    )
    message_bus.publish(response1)
    
    time.sleep(0.2)
    
    # Follow-up message
    message2 = response1.create_response(
        message_type=MessageType.QUERY,
        content={"query": "Are there any warnings or errors?"}
    )
    message_bus.publish(message2)
    
    time.sleep(0.2)
    
    # Response to follow-up
    response2 = message2.create_response(
        message_type=MessageType.QUERY_RESPONSE,
        content={"response": "No warnings or errors at this time."}
    )
    message_bus.publish(response2)
    
    # Wait for processing
    time.sleep(0.5)
    
    # Get the conversation
    conversation = message_bus.get_conversation(message1.conversation_id)
    print(f"\nConversation {conversation.conversation_id} has {len(conversation.messages)} messages")
    
    # Get the thought chain
    thought_chain = message_bus.get_thought_chain(message1.conversation_id)
    if thought_chain:
        print(f"Thought chain {thought_chain.id} has {len(thought_chain.thoughts)} thoughts")
        
        # Print the thought chain
        print("\nThought Chain:")
        for i, thought in enumerate(thought_chain.thoughts):
            thought_data = json.loads(thought.content)
            if "message_type" in thought_data:
                msg_type = thought_data["message_type"]
                content_preview = str(thought_data.get("content", {}))[:50]
                print(f"  {i+1}. {msg_type}: {content_preview}...")
    else:
        print("No thought chain found for the conversation")
    
    # Get the message chain
    message_chain = message_bus.get_message_chain(message_id1)
    print(f"\nMessage chain for {message_id1} has {len(message_chain)} messages")
    
    # Print the message chain
    print("\nMessage Chain:")
    for i, msg in enumerate(message_chain):
        print(f"  {i+1}. {msg.message_type.value}: {msg.content}")


def main():
    """Main function to run the demo."""
    print("Enhanced Message Bus Demo")
    print("========================\n")
    
    # Run the demos
    demo_basic_messaging()
    demo_message_filtering()
    demo_priority_based_delivery()
    demo_error_handling()
    demo_timeout_handling()
    demo_large_message_handling()
    demo_thought_chain_integration()
    
    print("\nDemo completed successfully!")


if __name__ == "__main__":
    main()
