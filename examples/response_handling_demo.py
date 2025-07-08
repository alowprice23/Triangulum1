#!/usr/bin/env python3
"""
Response Handling Demo

This demo showcases the advanced response handling capabilities of Triangulum,
including chunking, compression, and asynchronous coordination for large messages.
It demonstrates how to effectively handle large data transfers between agents.
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
import random
from typing import Dict, Any, List, Optional

# Add parent directory to path to allow running the demo from this directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Direct imports instead of using BaseAgent
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.response_handling import (
    LargeResponseHandler, 
    ResponseChunker,
    ResponseCompressor,
    ResponseValidator,
    ResponseSerializer,
    AsyncResponseCoordinator,
    ResponseValidationError,
    ResponseTimeoutError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("triangulum.demo.response_handling")


class SimpleMessageBus:
    """Simple message bus implementation for the demo."""
    
    def __init__(self):
        self.subscribers = {}  # agent_id -> callback
        self.messages = []  # List of all messages for inspection
    
    def subscribe(self, agent_id, callback):
        """Subscribe an agent to messages."""
        self.subscribers[agent_id] = callback
    
    def unsubscribe(self, agent_id):
        """Unsubscribe an agent."""
        if agent_id in self.subscribers:
            del self.subscribers[agent_id]
    
    def publish(self, message):
        """Publish a message to subscribers."""
        self.messages.append(message)
        
        # Deliver to specific receiver if specified
        if message.receiver and message.receiver in self.subscribers:
            self.subscribers[message.receiver](message)
        
        return message.message_id

class AnalysisAgent:
    """Agent that generates and sends large analysis results."""
    
    def __init__(self, agent_id=None, message_bus=None):
        self.agent_id = agent_id or f"analysis_agent_{str(uuid.uuid4())[:8]}"
        self.agent_type = "analysis"
        self.message_bus = message_bus
        
        # Initialize response handler
        self.response_handler = LargeResponseHandler(message_bus)
        
        # Setup operations tracking
        self.operations = {}  # operation_id -> status
    
    def initialize(self):
        """Initialize the agent."""
        # Set message bus for response handler
        self.response_handler.set_message_bus(self.message_bus)
        
        # Subscribe to messages
        if self.message_bus:
            self.message_bus.subscribe(self.agent_id, self.handle_message)
        
        return True
    
    def handle_message(self, message: AgentMessage) -> None:
        """Handle an incoming message."""
        logger.debug(f"Agent {self.agent_id} handling message: {message.message_type} from {message.sender}")
        
        # Dispatch based on message type
        if message.message_type == MessageType.TASK_REQUEST:
            self.handle_task_request(message)
        elif message.message_type == MessageType.QUERY:
            self.handle_query(message)
    
    def handle_task_request(self, message: AgentMessage) -> None:
        """Handle a task request message."""
        task_type = message.content.get("task_type", "default")
        data_size = message.content.get("data_size", "medium")
        logger.info(f"Analysis agent received task request: {task_type} (size: {data_size})")
        
        # Create an operation for tracking
        operation_id = str(uuid.uuid4())
        self.operations[operation_id] = {
            "status": "running",
            "start_time": time.time(),
            "type": f"analysis_{task_type}"
        }
        
        try:
            # Generate analysis results based on requested size
            if data_size == "small":
                result = self._generate_analysis_result(10)  # Small result
            elif data_size == "medium":
                result = self._generate_analysis_result(100)  # Medium result
            elif data_size == "large":
                result = self._generate_analysis_result(1000)  # Large result
            elif data_size == "very_large":
                result = self._generate_analysis_result(5000)  # Very large result
            else:
                result = self._generate_analysis_result(50)  # Default size
            
            # Determine response handling method based on size
            if data_size == "small":
                # Small response, send directly
                logger.info(f"Sending small response with {len(result)} items")
                response_msg = self.create_response_message(message, result, task_type)
                message_id = self.response_handler.process_outgoing_message(
                    response_msg, large_content_handling="direct"
                )
                logger.info(f"Sent response with ID: {message_id}")
                
            elif data_size == "medium":
                # Medium response, use compression
                logger.info(f"Sending medium response with {len(result)} items")
                response_msg = self.create_response_message(message, result, task_type)
                message_id = self.response_handler.process_outgoing_message(
                    response_msg, large_content_handling="direct"
                )
                logger.info(f"Sent compressed response with ID: {message_id}")
                
            elif data_size == "large" or data_size == "very_large":
                # Large response, use chunking
                logger.info(f"Sending large response with {len(result)} items")
                response_msg = self.create_response_message(message, result, task_type)
                message_ids = self.response_handler.process_outgoing_message(
                    response_msg, large_content_handling="chunked"
                )
                logger.info(f"Sent chunked response with {len(message_ids)} chunks")
                
            # Complete the operation
            self.operations[operation_id]["status"] = "completed"
            self.operations[operation_id]["end_time"] = time.time()
            
        except Exception as e:
            logger.error(f"Error processing task: {str(e)}")
            # Mark operation as failed
            self.operations[operation_id]["status"] = "failed"
            self.operations[operation_id]["error"] = str(e)
            self.operations[operation_id]["end_time"] = time.time()
            
            # Send error response
            self.send_message(
                MessageType.ERROR,
                {"error": f"Failed to process analysis task: {str(e)}"},
                receiver=message.sender,
                parent_message_id=message.message_id
            )
    
    def send_message(self, message_type, content, receiver=None, parent_message_id=None):
        """Send a message via the message bus."""
        if not self.message_bus:
            logger.warning(f"Agent {self.agent_id}: No message bus available, message not sent")
            return None
        
        message = AgentMessage(
            message_id=f"{self.agent_id}_{str(uuid.uuid4())}",
            message_type=message_type,
            content=content,
            sender=self.agent_id,
            receiver=receiver,
            parent_id=parent_message_id,
            timestamp=time.time()
        )
        
        return self.message_bus.publish(message)
    
    def create_response_message(self, request_msg, result, task_type):
        """Create a response message with analysis results."""
        return AgentMessage(
            message_id=f"response_{uuid.uuid4()}",
            message_type=MessageType.TASK_RESULT,
            content={
                "result": result,
                "task_type": task_type,
                "timestamp": time.time(),
                "agent_id": self.agent_id,
                "request_id": request_msg.message_id
            },
            sender=self.agent_id,
            receiver=request_msg.sender,
            timestamp=time.time()
        )
    
    def _generate_analysis_result(self, num_items: int) -> List[Dict[str, Any]]:
        """Generate a synthetic analysis result with the specified number of items."""
        result = []
        
        # Generate items with realistic analysis data
        for i in range(num_items):
            # Create a complex nested structure that resembles real analysis data
            item = {
                "id": f"finding_{i}",
                "timestamp": time.time(),
                "name": f"Analysis Finding {i}",
                "category": random.choice(["security", "performance", "code_quality", "architecture"]),
                "severity": random.randint(1, 5),
                "confidence": round(random.uniform(0.5, 1.0), 2),
                "location": {
                    "file": f"src/module_{i % 20}/file_{i % 50}.py",
                    "line_start": random.randint(1, 500),
                    "line_end": random.randint(1, 500) + random.randint(1, 20),
                    "context": "def example_function():\n    # Some code here\n    pass"
                },
                "details": {
                    "description": f"This is a detailed description of finding {i}. " * 3,
                    "impact": f"The impact of this finding is significant because... " * 2,
                    "remediation": f"To fix this issue, you should consider the following steps: " * 2,
                    "references": [
                        f"https://example.com/ref/{j}" for j in range(random.randint(1, 3))
                    ]
                },
                "metadata": {
                    "detector": f"detector_{i % 10}",
                    "execution_time": random.uniform(0.01, 2.0),
                    "tags": [f"tag_{j}" for j in range(random.randint(1, 5))],
                    "related_findings": [f"finding_{i-j}" for j in range(1, min(4, i+1))],
                    "history": [
                        {
                            "date": time.time() - j*86400,
                            "status": random.choice(["new", "investigating", "fixed", "wontfix"]),
                            "comment": f"Status update {j}"
                        } for j in range(random.randint(1, 3))
                    ]
                }
            }
            
            result.append(item)
            
        return result


class ConsumerAgent:
    """Agent that consumes large analysis results."""
    
    def __init__(self, agent_id=None, message_bus=None):
        self.agent_id = agent_id or f"consumer_agent_{str(uuid.uuid4())[:8]}"
        self.agent_type = "consumer"
        self.message_bus = message_bus
        
        # Initialize response handler
        self.response_handler = LargeResponseHandler(message_bus)
        
        # Storage for received results
        self.received_results = {}
        self.pending_requests = {}
    
    def initialize(self):
        """Initialize the agent."""
        # Set message bus for response handler
        self.response_handler.set_message_bus(self.message_bus)
        
        # Subscribe to messages
        if self.message_bus:
            self.message_bus.subscribe(self.agent_id, self.handle_message)
        
        return True
    
    def handle_message(self, message: AgentMessage):
        """Handle an incoming message."""
        # Process based on message type
        if message.message_type == MessageType.TASK_RESULT:
            # Check if it's a compressed message
            processed = self.response_handler.process_incoming_message(message)
            self._process_task_result(processed)
            
        elif message.message_type == MessageType.CHUNKED_MESSAGE:
            logger.debug(f"Received chunked message: {message.message_id}")
            reassembled = self.response_handler.process_incoming_message(message)
            
            if reassembled:
                logger.info(f"Reassembled chunked message: {reassembled.message_id}")
                # Process the reassembled message as a regular task result
                self._process_task_result(reassembled)
                
        elif message.message_type == MessageType.ERROR:
            # Handle error messages
            self._handle_error(message)
    
    def _handle_error(self, message: AgentMessage):
        """Handle error messages."""
        request_id = message.parent_id
        error = message.content.get("error", "Unknown error")
        
        if request_id and request_id in self.pending_requests:
            logger.error(f"Error for request {request_id}: {error}")
            self.pending_requests[request_id]["status"] = "error"
            self.pending_requests[request_id]["error"] = error
            
            # Notify async coordinator
            self.response_handler.handle_async_response(
                request_id, None, error
            )
        else:
            logger.error(f"Received error message: {error}")
    
    def request_analysis(self, task_type: str, data_size: str, 
                         analysis_agent_id: str) -> str:
        """
        Request an analysis from an analysis agent.
        
        Args:
            task_type: Type of analysis task
            data_size: Size of requested data ("small", "medium", "large", "very_large")
            analysis_agent_id: ID of the analysis agent
            
        Returns:
            Request ID
        """
        request_id = f"request_{uuid.uuid4()}"
        
        # Create request message
        request_msg = AgentMessage(
            message_id=request_id,
            message_type=MessageType.TASK_REQUEST,
            content={
                "task_type": task_type,
                "data_size": data_size,
                "timestamp": time.time()
            },
            sender=self.agent_id,
            receiver=analysis_agent_id,
            timestamp=time.time()
        )
        
        # Register for async response
        self.response_handler.register_async_response(
            request_id, 
            timeout=30.0,  # 30 second timeout
            callback=self._handle_async_response
        )
        
        # Store pending request
        self.pending_requests[request_id] = {
            "task_type": task_type,
            "data_size": data_size,
            "timestamp": time.time(),
            "status": "pending"
        }
        
        # Send request
        logger.info(f"Requesting {data_size} analysis of type {task_type}")
        self.message_bus.publish(request_msg)
        
        return request_id
    
    def send_message(self, message_type, content, receiver=None, parent_message_id=None):
        """Send a message via the message bus."""
        if not self.message_bus:
            logger.warning(f"Agent {self.agent_id}: No message bus available, message not sent")
            return None
        
        message = AgentMessage(
            message_id=f"{self.agent_id}_{str(uuid.uuid4())}",
            message_type=message_type,
            content=content,
            sender=self.agent_id,
            receiver=receiver,
            parent_id=parent_message_id,
            timestamp=time.time()
        )
        
        return self.message_bus.publish(message)
    
    def _process_task_result(self, message: AgentMessage) -> None:
        """Process a task result message."""
        result = message.content.get("result", [])
        task_type = message.content.get("task_type", "unknown")
        request_id = message.content.get("request_id", "unknown")
        
        # Store the result
        result_id = str(uuid.uuid4())
        self.received_results[result_id] = {
            "task_type": task_type,
            "count": len(result),
            "result": result,
            "timestamp": time.time()
        }
        
        logger.info(f"Received {task_type} result with {len(result)} items")
        
        # Update pending request if applicable
        if request_id in self.pending_requests:
            self.pending_requests[request_id]["status"] = "completed"
            self.pending_requests[request_id]["result_id"] = result_id
            
            # Notify async coordinator
            self.response_handler.handle_async_response(
                request_id, result, None
            )
    
    def _handle_async_response(self, request_id, response, error):
        """Handle asynchronous response callback."""
        if error:
            logger.error(f"Async response error for {request_id}: {error}")
        else:
            count = len(response) if response else 0
            logger.info(f"Async response received for {request_id}: {count} items")
    
    def wait_for_result(self, request_id: str, timeout: float = 30.0) -> Optional[Dict]:
        """
        Wait for a result to be received.
        
        Args:
            request_id: The request ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Result data or None if timed out
        """
        success, response, error = self.response_handler.wait_for_async_response(
            request_id, timeout
        )
        
        if success:
            return response
        else:
            logger.error(f"Wait failed: {error}")
            return None
    
    def print_result_summary(self, result_id: str = None) -> None:
        """
        Print a summary of received results.
        
        Args:
            result_id: Specific result ID to print, or None for all
        """
        if result_id and result_id in self.received_results:
            result = self.received_results[result_id]
            print(f"\nResult {result_id}:")
            print(f"  Type: {result['task_type']}")
            print(f"  Items: {result['count']}")
            print(f"  Timestamp: {time.ctime(result['timestamp'])}")
            
            # Print a sample of items
            if result['result']:
                print("\nSample items:")
                for i, item in enumerate(result['result'][:3]):  # First 3 items
                    print(f"  Item {i}: {item['name']} (Severity: {item['severity']})")
                    print(f"    Category: {item['category']}")
                    print(f"    Location: {item['location']['file']}:{item['location']['line_start']}")
                    print(f"    Description: {item['details']['description'][:100]}...")
        
        else:
            print("\nAll Results:")
            for rid, result in self.received_results.items():
                print(f"  {rid}: {result['task_type']} - {result['count']} items")


def run_demo():
    """Run the response handling demonstration."""
    # Create a message bus
    message_bus = SimpleMessageBus()
    
    # Create agents
    analysis_agent = AnalysisAgent(message_bus=message_bus)
    consumer_agent = ConsumerAgent(message_bus=message_bus)
    
    # Initialize agents
    analysis_agent.initialize()
    consumer_agent.initialize()
    
    logger.info(f"Created analysis agent ({analysis_agent.agent_id}) and consumer agent ({consumer_agent.agent_id})")
    
    # Test with different data sizes
    data_sizes = ["small", "medium", "large", "very_large"]
    request_ids = []
    
    for size in data_sizes:
        # Request analysis
        request_id = consumer_agent.request_analysis(
            "code_analysis", size, analysis_agent.agent_id
        )
        request_ids.append(request_id)
        
        # Wait between requests
        time.sleep(1)
    
    # Wait for all results
    logger.info("Waiting for all results...")
    for request_id in request_ids:
        result = consumer_agent.wait_for_result(request_id)
        if result:
            logger.info(f"Result received for {request_id}: {len(result)} items")
        else:
            logger.warning(f"No result received for {request_id}")
    
    # Print result summaries
    print("\n============= RESULTS SUMMARY =============")
    consumer_agent.print_result_summary()
    
    # Clean up
    logger.info("Cleaning up...")
    if message_bus:
        message_bus.unsubscribe(analysis_agent.agent_id)
        message_bus.unsubscribe(consumer_agent.agent_id)
    
    logger.info("Demo completed successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Response Handling Demo")
    args = parser.parse_args()
    
    run_demo()
