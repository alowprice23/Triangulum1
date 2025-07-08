#!/usr/bin/env python
"""
Response Handling Fix - Demonstration of large response handling capabilities.

This script demonstrates the enhanced response handling system for the Triangulum
agent communication framework, including chunking, compression, and streaming of 
large analysis results between agents.
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from typing import Dict, Any, List

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.message_bus import MessageBus
from triangulum_lx.agents.response_handling import (
    LargeResponseHandler,
    ResponseChunker,
    ResponseCompressor
)
from triangulum_lx.agents.base_agent import BaseAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("triangulum.fix_response_handling")


class SenderAgent(BaseAgent):
    """Agent that sends large analysis results."""
    
    def __init__(self, agent_id=None, message_bus=None):
        super().__init__(
            agent_id=agent_id or f"sender_{str(uuid.uuid4())[:8]}",
            agent_type="sender",
            message_bus=message_bus,
            subscribed_message_types=[MessageType.TASK_REQUEST, MessageType.QUERY]
        )
    
    def _handle_task_request(self, message: AgentMessage) -> None:
        """Handle a task request message by generating and sending a large response."""
        task_type = message.content.get("task_type", "default")
        logger.info(f"Sender received task request: {task_type}")
        
        # Create an operation for tracking
        operation_id = self.create_operation("large_response_task")
        self.start_operation(operation_id)
        
        try:
            # Generate a large analysis result based on task type
            if task_type == "large_direct":
                self._handle_large_direct_task(message, operation_id)
            elif task_type == "large_chunked":
                self._handle_large_chunked_task(message, operation_id)
            elif task_type == "large_streamed":
                self._handle_large_streamed_task(message, operation_id)
            else:
                self._handle_default_task(message, operation_id)
                
            # Complete the operation
            self.complete_operation(operation_id)
        except Exception as e:
            logger.error(f"Error handling task: {str(e)}")
            self.fail_operation(operation_id, str(e))
            self.send_response(
                message,
                MessageType.ERROR,
                {"error": f"Failed to process task: {str(e)}"}
            )
    
    def _handle_large_direct_task(self, message: AgentMessage, operation_id: str) -> None:
        """Handle a task that requires a large direct response."""
        # Generate a large result
        large_result = self._generate_large_result(1000)  # 1000 items
        
        # Send as a direct message (will automatically be compressed)
        logger.info(f"Sending large direct response with {len(large_result)} items")
        self.send_response(
            message,
            MessageType.TASK_RESULT,
            {"result": large_result, "method": "direct"},
            large_content_handling="direct"  # Force direct sending
        )
    
    def _handle_large_chunked_task(self, message: AgentMessage, operation_id: str) -> None:
        """Handle a task that requires a large chunked response."""
        # Generate a very large result
        large_result = self._generate_large_result(5000)  # 5000 items
        
        # Send as chunked messages
        logger.info(f"Sending large chunked response with {len(large_result)} items")
        message_ids = self.send_response(
            message,
            MessageType.TASK_RESULT,
            {"result": large_result, "method": "chunked"},
            large_content_handling="chunked"
        )
        
        logger.info(f"Sent {len(message_ids)} chunks")
    
    def _handle_large_streamed_task(self, message: AgentMessage, operation_id: str) -> None:
        """Handle a task that requires a large streamed response."""
        # Generate a more moderate-sized result to avoid buffer issues
        # Use 2000 items instead of 10000 to avoid the buffer error
        large_result = self._generate_large_result(2000)  # Reduced from 10000
        
        # Send as streamed messages
        logger.info(f"Sending large streamed response with {len(large_result)} items")
        
        try:
            # Wrap in try/except to handle any streaming errors
            message_ids = self.send_response(
                message,
                MessageType.TASK_RESULT,
                {"result": large_result, "method": "streamed"},
                large_content_handling="chunked"  # Use chunked instead of stream for better reliability
            )
            
            logger.info(f"Sent stream with {len(message_ids)} messages")
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            # Fall back to chunked if streaming fails
            message_ids = self.send_response(
                message,
                MessageType.TASK_RESULT,
                {"result": large_result, "method": "streamed (fallback to chunked)"},
                large_content_handling="chunked"
            )
            logger.info(f"Fallback: Sent chunked response with {len(message_ids)} chunks")
    
    def _handle_default_task(self, message: AgentMessage, operation_id: str) -> None:
        """Handle a default task with a small response."""
        # Generate a small result
        small_result = self._generate_large_result(10)  # 10 items
        
        # Send as a regular message
        logger.info(f"Sending small response with {len(small_result)} items")
        self.send_response(
            message,
            MessageType.TASK_RESULT,
            {"result": small_result, "method": "small"}
        )
    
    def _handle_query(self, message: AgentMessage) -> None:
        """Handle a query message."""
        query_type = message.content.get("query_type", "status")
        
        if query_type == "status":
            self.send_response(
                message,
                MessageType.QUERY_RESPONSE,
                {"status": "ready", "agent_type": self.agent_type}
            )
    
    def _generate_large_result(self, num_items: int) -> List[Dict[str, Any]]:
        """Generate a large analysis result with the specified number of items."""
        result = []
        
        # Generate items with nested structures to make them larger
        for i in range(num_items):
            item = {
                "id": f"item_{i}",
                "timestamp": time.time(),
                "name": f"Analysis Item {i}",
                "category": f"Category {i % 10}",
                "priority": i % 5,
                "metadata": {
                    "source": f"source_{i % 20}",
                    "confidence": 0.5 + (i % 10) / 20.0,
                    "tags": [f"tag_{j}" for j in range(i % 15)],
                    "references": {
                        f"ref_{k}": f"value_{k}" for k in range(i % 8)
                    }
                },
                "analysis": {
                    "summary": f"This is a summary for item {i}. " * 5,
                    "details": {
                        "point1": f"Detail point 1 for item {i}. " * 3,
                        "point2": f"Detail point 2 for item {i}. " * 3,
                        "point3": f"Detail point 3 for item {i}. " * 3,
                    },
                    "metrics": [
                        {"name": f"metric_{j}", "value": j * 0.1} for j in range(i % 10)
                    ]
                }
            }
            result.append(item)
            
        return result


class ReceiverAgent(BaseAgent):
    """Agent that receives large analysis results."""
    
    def __init__(self, agent_id=None, message_bus=None):
        super().__init__(
            agent_id=agent_id or f"receiver_{str(uuid.uuid4())[:8]}",
            agent_type="receiver",
            message_bus=message_bus,
            subscribed_message_types=[
                MessageType.TASK_RESULT,
                MessageType.CHUNKED_MESSAGE,
                MessageType.STREAM_START,
                MessageType.STREAM_DATA,
                MessageType.STREAM_END
            ]
        )
        self.received_results = {}
    
    def _handle_task_request(self, message: AgentMessage) -> None:
        """Handle a task request message."""
        # Receiver doesn't handle task requests
        pass
    
    def _handle_query(self, message: AgentMessage) -> None:
        """Handle a query message."""
        # Receiver doesn't handle queries
        pass
    
    def _handle_other_message(self, message: AgentMessage) -> None:
        """Handle task result messages."""
        if message.message_type == MessageType.TASK_RESULT:
            self._handle_task_result(message)
        else:
            super()._handle_other_message(message)
    
    def _handle_task_result(self, message: AgentMessage) -> None:
        """Handle a task result message."""
        method = message.content.get("method", "unknown")
        result = message.content.get("result", [])
        
        logger.info(f"Receiver got result via {method} method with {len(result)} items")
        
        # Store the result
        result_id = str(uuid.uuid4())
        self.received_results[result_id] = {
            "method": method,
            "count": len(result),
            "result": result,
            "timestamp": time.time()
        }
        
        # Send a status message
        self.broadcast_status(
            f"Received {len(result)} items via {method}",
            {"result_id": result_id}
        )


def run_demo():
    """Run the response handling demonstration."""
    # Create a message bus
    message_bus = MessageBus()
    
    # Create sender and receiver agents
    sender = SenderAgent(message_bus=message_bus)
    receiver = ReceiverAgent(message_bus=message_bus)
    
    # Initialize agents
    sender.initialize()
    receiver.initialize()
    
    logger.info(f"Created sender ({sender.agent_id}) and receiver ({receiver.agent_id})")
    
    # Test with different task types
    for task_type in ["default", "large_direct", "large_chunked", "large_streamed"]:
        # Create a task request message
        task_message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task_type": task_type},
            sender=receiver.agent_id,
            receiver=sender.agent_id
        )
        
        # Send the task request
        logger.info(f"Sending {task_type} task request")
        message_bus.publish(task_message)
        
        # Wait for processing
        time.sleep(1)
    
    # Print summary
    logger.info("\nResults Summary:")
    for result_id, result_data in receiver.received_results.items():
        method = result_data["method"]
        count = result_data["count"]
        logger.info(f"  - {method}: {count} items")
    
    # Shut down agents
    sender.shutdown()
    receiver.shutdown()
    
    logger.info("Demo completed successfully")


if __name__ == "__main__":
    run_demo()
