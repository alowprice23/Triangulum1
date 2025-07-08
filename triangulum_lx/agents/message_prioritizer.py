#!/usr/bin/env python3
"""
Message Prioritizer

This module provides advanced message prioritization for the Triangulum agentic system,
allowing agents to prioritize messages based on urgency, relevance, and other factors.
"""

import logging
import datetime
import json
import os
import time
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
import heapq
import threading
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriorityLevel(Enum):
    """Priority levels for messages."""
    CRITICAL = 0  # Highest priority, urgent messages requiring immediate attention
    HIGH = 1      # Important messages that should be processed soon
    MEDIUM = 2    # Regular messages with standard priority
    LOW = 3       # Non-urgent messages that can wait
    BACKGROUND = 4  # Lowest priority, processed only when no other messages are waiting

class MessagePrioritizer:
    """
    Provides advanced message prioritization for agent communication,
    ensuring that important messages are processed first.
    """
    
    def __init__(self, 
                agent_id: str,
                max_queue_size: int = 1000,
                priority_threshold: PriorityLevel = PriorityLevel.MEDIUM,
                enable_adaptive_prioritization: bool = True,
                priority_rules: Optional[Dict[str, Callable]] = None):
        """
        Initialize the message prioritizer.
        
        Args:
            agent_id: ID of the agent that owns this prioritizer
            max_queue_size: Maximum number of messages to keep in the queue
            priority_threshold: Minimum priority level to process messages (lower value = higher priority)
            enable_adaptive_prioritization: Whether to adapt priorities based on message patterns
            priority_rules: Custom rules for prioritizing messages, keyed by message type
        """
        self.agent_id = agent_id
        self.max_queue_size = max_queue_size
        self.priority_threshold = priority_threshold
        self.enable_adaptive_prioritization = enable_adaptive_prioritization
        self.priority_rules = priority_rules or {}
        
        # Initialize message queue as a priority queue
        self.message_queue = []  # Will be used as a heap queue
        self.queue_lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Message statistics for adaptive prioritization
        self.message_stats = {
            "message_types": {},  # message_type -> count
            "source_agents": {},  # source_agent -> count
            "response_times": {},  # message_type -> avg response time (ms)
            "success_rates": {},  # message_type -> success rate (0-1)
            "total_messages": 0,
            "total_processed": 0,
            "total_successful": 0
        }
        
        # Conflict resolution tracking
        self.conflict_history = {}  # (source, target, message_type) -> resolution history
        
        logger.info(f"Message Prioritizer initialized for agent {agent_id}")
    
    def enqueue_message(self, 
                       message: Dict,
                       source_agent: str,
                       message_type: str,
                       content: Optional[str] = None,
                       urgency: Optional[float] = None,
                       context_relevance: Optional[float] = None,
                       expiration_time: Optional[datetime.datetime] = None,
                       dependencies: Optional[List[str]] = None,
                       metadata: Optional[Dict] = None) -> str:
        """
        Add a message to the priority queue.
        
        Args:
            message: The complete message to enqueue
            source_agent: ID of the agent that sent the message
            message_type: Type of message (command, query, response, etc.)
            content: Optional message content
            urgency: Message urgency (0-1, higher is more urgent)
            context_relevance: Relevance to current context (0-1, higher is more relevant)
            expiration_time: When the message becomes irrelevant
            dependencies: List of message IDs that this message depends on
            metadata: Additional metadata for the message
        
        Returns:
            message_id: ID of the enqueued message
        """
        # Generate message ID based on timestamp and source
        message_id = f"{int(time.time())}_{source_agent}_{self.agent_id}"
        timestamp = datetime.datetime.now().isoformat()
        
        # Calculate initial priority based on message type and urgency
        priority = self._calculate_priority(
            message_type=message_type, 
            source_agent=source_agent,
            urgency=urgency,
            context_relevance=context_relevance,
            expiration_time=expiration_time,
            dependencies=dependencies,
            metadata=metadata
        )
        
        # Prepare message with priority information
        prioritized_message = {
            "message_id": message_id,
            "original_message": message,
            "source_agent": source_agent,
            "target_agent": self.agent_id,
            "message_type": message_type,
            "content": content,
            "timestamp": timestamp,
            "priority": priority,
            "priority_level": self._priority_to_level(priority),
            "urgency": urgency,
            "context_relevance": context_relevance,
            "expiration_time": expiration_time.isoformat() if expiration_time else None,
            "dependencies": dependencies or [],
            "metadata": metadata or {},
            "processed": False,
            "processing_attempts": 0,
            "response_time_ms": None,
            "success": None
        }
        
        # Update message statistics
        self._update_stats(source_agent, message_type)
        
        # Check if the message has dependencies
        if dependencies and not self._are_dependencies_met(dependencies):
            # Store message as pending on dependencies
            prioritized_message["status"] = "pending_dependencies"
            logger.debug(f"Message {message_id} is pending on dependencies: {dependencies}")
        else:
            prioritized_message["status"] = "ready"
        
        # Check for message expiration
        if expiration_time and datetime.datetime.now() > expiration_time:
            logger.debug(f"Message {message_id} has already expired")
            return message_id
        
        # Add message to priority queue
        with self.queue_lock:
            # Add to priority queue as (priority, timestamp, message_id, message)
            # Using timestamp as secondary sort to ensure FIFO for same priority
            timestamp_seconds = time.time()
            heapq.heappush(
                self.message_queue, 
                (priority, timestamp_seconds, message_id, prioritized_message)
            )
            
            # Limit queue size by removing lowest priority messages if needed
            if len(self.message_queue) > self.max_queue_size:
                self._trim_queue()
        
        logger.debug(f"Enqueued message {message_id} with priority {priority}")
        return message_id
    
    def dequeue_message(self) -> Optional[Dict]:
        """
        Get the highest priority message from the queue.
        
        Returns:
            message: The highest priority message, or None if queue is empty
        """
        with self.queue_lock:
            if not self.message_queue:
                return None
            
            # Pop highest priority message (lowest priority value)
            _, _, message_id, message = heapq.heappop(self.message_queue)
            
            # Check if message has expired
            if message.get("expiration_time"):
                try:
                    expiration = datetime.datetime.fromisoformat(message["expiration_time"])
                    if datetime.datetime.now() > expiration:
                        logger.debug(f"Skipped expired message {message_id}")
                        return self.dequeue_message()  # Recursively get next message
                except (ValueError, TypeError):
                    # Invalid expiration time, continue processing
                    pass
            
            # Mark message as being processed
            message["processing_attempts"] += 1
            message["processing_start_time"] = datetime.datetime.now().isoformat()
            
            return message
    
    def complete_message_processing(self, message_id: str, success: bool = True, response_time_ms: Optional[float] = None):
        """
        Mark a message as processed and update statistics.
        
        Args:
            message_id: ID of the processed message
            success: Whether processing was successful
            response_time_ms: Time taken to process the message in milliseconds
        """
        # Find the message in the processed list
        # In a real implementation, this might use a database lookup
        
        # Update statistics
        self.message_stats["total_processed"] += 1
        if success:
            self.message_stats["total_successful"] += 1
        
        # If response time provided, update average response time for this message type
        # This would be implemented in a real system
        
        logger.debug(f"Completed processing message {message_id}, success={success}")
    
    def get_queue_status(self) -> Dict:
        """
        Get the current status of the message queue.
        
        Returns:
            status: Dictionary with queue statistics
        """
        with self.queue_lock:
            queue_length = len(self.message_queue)
            
            # Count messages by priority level
            priority_counts = {}
            for level in PriorityLevel:
                priority_counts[level.name] = 0
            
            for _, _, _, message in self.message_queue:
                level = message.get("priority_level", PriorityLevel.MEDIUM.name)
                priority_counts[level] = priority_counts.get(level, 0) + 1
            
            return {
                "queue_length": queue_length,
                "priority_counts": priority_counts,
                "total_messages_received": self.message_stats["total_messages"],
                "total_messages_processed": self.message_stats["total_processed"],
                "success_rate": (self.message_stats["total_successful"] / self.message_stats["total_processed"]) 
                                if self.message_stats["total_processed"] > 0 else 0
            }
    
    def resolve_conflict(self, 
                        message1: Dict, 
                        message2: Dict, 
                        resolution_strategy: str = "priority") -> Dict:
        """
        Resolve a conflict between two messages.
        
        Args:
            message1: First conflicting message
            message2: Second conflicting message
            resolution_strategy: Strategy to use for resolution (priority, time, source, etc.)
        
        Returns:
            message: The message that should be processed first
        """
        if resolution_strategy == "priority":
            # Choose message with higher priority (lower value)
            return message1 if message1["priority"] < message2["priority"] else message2
        
        elif resolution_strategy == "time":
            # Choose older message
            time1 = datetime.datetime.fromisoformat(message1["timestamp"])
            time2 = datetime.datetime.fromisoformat(message2["timestamp"])
            return message1 if time1 < time2 else message2
        
        elif resolution_strategy == "source":
            # Implement source agent priority logic
            # This would depend on the system's agent hierarchy
            return message1  # Placeholder
        
        else:
            # Default to priority-based resolution
            return message1 if message1["priority"] < message2["priority"] else message2
    
    def update_priority(self, message_id: str, new_priority: float) -> bool:
        """
        Update the priority of a message in the queue.
        
        Args:
            message_id: ID of the message to update
            new_priority: New priority value
        
        Returns:
            success: Whether the update was successful
        """
        with self.queue_lock:
            # Find the message in the queue
            for i, (_, _, mid, message) in enumerate(self.message_queue):
                if mid == message_id:
                    # Remove from queue
                    self.message_queue[i] = self.message_queue[-1]
                    self.message_queue.pop()
                    heapq.heapify(self.message_queue)
                    
                    # Update priority
                    message["priority"] = new_priority
                    message["priority_level"] = self._priority_to_level(new_priority)
                    
                    # Re-add to queue
                    timestamp_seconds = time.time()
                    heapq.heappush(
                        self.message_queue, 
                        (new_priority, timestamp_seconds, message_id, message)
                    )
                    
                    logger.debug(f"Updated priority of message {message_id} to {new_priority}")
                    return True
        
        logger.debug(f"Message {message_id} not found in queue for priority update")
        return False
    
    def _calculate_priority(self, 
                          message_type: str, 
                          source_agent: str,
                          urgency: Optional[float] = None,
                          context_relevance: Optional[float] = None,
                          expiration_time: Optional[datetime.datetime] = None,
                          dependencies: Optional[List[str]] = None,
                          metadata: Optional[Dict] = None) -> float:
        """
        Calculate message priority based on various factors.
        
        Returns:
            priority: Priority value (lower value = higher priority)
        """
        # Start with a base priority value (1-5, with 1 being highest priority)
        base_priority = 3.0  # Medium priority by default
        
        # Adjust based on message type
        type_priorities = {
            "command": 1.0,      # Commands get high priority
            "query": 2.0,        # Queries get medium-high priority
            "response": 1.5,     # Responses get high priority
            "notification": 3.0, # Notifications get medium priority
            "update": 2.5,       # Updates get medium-high priority
            "heartbeat": 5.0     # Heartbeats get lowest priority
        }
        
        base_priority = type_priorities.get(message_type.lower(), base_priority)
        
        # Adjust based on source agent (could implement agent hierarchies here)
        
        # Adjust based on urgency if provided
        if urgency is not None:
            urgency_factor = max(0.0, min(1.0, urgency))  # Clamp to 0-1
            base_priority -= urgency_factor * 2  # Higher urgency lowers priority value
        
        # Adjust based on context relevance if provided
        if context_relevance is not None:
            relevance_factor = max(0.0, min(1.0, context_relevance))  # Clamp to 0-1
            base_priority -= relevance_factor * 1.5  # Higher relevance lowers priority value
        
        # Adjust based on expiration time if provided
        if expiration_time:
            now = datetime.datetime.now()
            time_until_expiry = (expiration_time - now).total_seconds()
            if time_until_expiry < 60:  # Less than a minute until expiry
                base_priority -= 1.0  # Increase priority for soon-to-expire messages
            elif time_until_expiry < 300:  # Less than 5 minutes
                base_priority -= 0.5
        
        # Adjust based on dependencies if provided
        if dependencies and len(dependencies) > 0:
            base_priority += 0.2 * len(dependencies)  # Lower priority for messages with many dependencies
        
        # Apply custom priority rules if defined for this message type
        if message_type in self.priority_rules:
            rule_func = self.priority_rules[message_type]
            base_priority = rule_func(base_priority, source_agent, metadata)
        
        # Adaptive prioritization based on history (if enabled)
        if self.enable_adaptive_prioritization:
            # Example: If a message type has high success rate, slightly lower its priority
            # This would be more sophisticated in a real implementation
            success_rate = self.message_stats["success_rates"].get(message_type, 0.5)
            if success_rate > 0.9:  # Very reliable message type
                base_priority += 0.1  # Slightly lower priority
            elif success_rate < 0.3:  # Problematic message type
                base_priority -= 0.2  # Slightly higher priority
        
        # Ensure priority stays within reasonable bounds
        base_priority = max(0.5, min(5.0, base_priority))
        
        return base_priority
    
    def _priority_to_level(self, priority: float) -> str:
        """Convert numeric priority to PriorityLevel enum name."""
        if priority < 1.0:
            return PriorityLevel.CRITICAL.name
        elif priority < 2.0:
            return PriorityLevel.HIGH.name
        elif priority < 3.0:
            return PriorityLevel.MEDIUM.name
        elif priority < 4.0:
            return PriorityLevel.LOW.name
        else:
            return PriorityLevel.BACKGROUND.name
    
    def _update_stats(self, source_agent: str, message_type: str):
        """Update message statistics for adaptive prioritization."""
        self.message_stats["total_messages"] += 1
        
        # Update message type count
        if message_type not in self.message_stats["message_types"]:
            self.message_stats["message_types"][message_type] = 0
        self.message_stats["message_types"][message_type] += 1
        
        # Update source agent count
        if source_agent not in self.message_stats["source_agents"]:
            self.message_stats["source_agents"][source_agent] = 0
        self.message_stats["source_agents"][source_agent] += 1
    
    def _trim_queue(self):
        """Trim the queue to the maximum size by removing lowest priority messages."""
        if len(self.message_queue) <= self.max_queue_size:
            return
        
        # Sort by priority (ascending) to find lowest priority messages
        self.message_queue.sort()
        
        # Remove excess messages (from the end, which are lowest priority)
        excess = len(self.message_queue) - self.max_queue_size
        if excess > 0:
            self.message_queue = self.message_queue[:-excess]
            
            # Reheapify the queue
            heapq.heapify(self.message_queue)
            
            logger.debug(f"Trimmed {excess} low-priority messages from queue")
    
    def _are_dependencies_met(self, dependencies: List[str]) -> bool:
        """
        Check if all dependencies for a message have been processed.
        
        In a real implementation, this would check against a database of processed messages.
        This is a simplified version that always returns True.
        """
        # Placeholder implementation
        return True


# Example usage
if __name__ == "__main__":
    # Create a message prioritizer for an agent
    prioritizer = MessagePrioritizer(agent_id="orchestrator")
    
    # Enqueue some messages
    prioritizer.enqueue_message(
        message={"command": "analyze_code", "params": {"file": "main.py"}},
        source_agent="user",
        message_type="command",
        content="Analyze the code in main.py",
        urgency=0.8
    )
    
    prioritizer.enqueue_message(
        message={"query": "system_status", "params": {}},
        source_agent="monitoring_agent",
        message_type="query",
        content="What is the current system status?",
        urgency=0.5
    )
    
    prioritizer.enqueue_message(
        message={"notification": "new_file", "params": {"file": "test.py"}},
        source_agent="file_system_agent",
        message_type="notification",
        content="New file detected: test.py",
        urgency=0.2
    )
    
    # Process messages in priority order
    while True:
        message = prioritizer.dequeue_message()
        if message is None:
            break
        
        print(f"Processing: {message['message_type']} from {message['source_agent']} with priority {message['priority']}")
        
        # Simulate processing
        time.sleep(0.1)
        
        # Mark as completed
        prioritizer.complete_message_processing(message['message_id'], success=True, response_time_ms=100)
    
    # Get queue status
    status = prioritizer.get_queue_status()
    print(f"Queue status: {status}")
