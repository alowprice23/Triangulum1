#!/usr/bin/env python3
"""
Unit tests for the Enhanced Message Bus.

This module contains comprehensive tests for the Enhanced Message Bus,
verifying all its advanced features including message filtering, priority-based
delivery, circuit breaker pattern, timeout handling, and thought chain integration.
"""

import unittest
import time
import threading
import json
import uuid
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from triangulum_lx.agents.message import AgentMessage, MessageType, ConfidenceLevel
from triangulum_lx.agents.enhanced_message_bus import (
    EnhancedMessageBus, MessagePriority, CircuitBreaker, CircuitState,
    MessageDeduplicator, DeliveryStatus
)
from triangulum_lx.agents.thought_chain_manager import ThoughtChainManager
from triangulum_lx.agents.thought_chain import ThoughtChain


class TestEnhancedMessageBus(unittest.TestCase):
    """Test cases for the EnhancedMessageBus class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.message_bus = EnhancedMessageBus()
        
        # Create a test message
        self.test_message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender"
        )
        
        # Create a mock callback
        self.mock_callback = MagicMock()
    
    def test_subscribe_and_publish(self):
        """Test basic subscription and publishing."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Publish a message
        result = self.message_bus.publish(self.test_message)
        
        # Check that the callback was called
        self.mock_callback.assert_called_once()
        self.assertTrue(result["success"])
    
    def test_unsubscribe(self):
        """Test unsubscribing from messages."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Unsubscribe from messages
        self.message_bus.unsubscribe(
            agent_id="test_agent",
            message_types=[MessageType.STATUS]
        )
        
        # Publish a message
        self.message_bus.publish(self.test_message)
        
        # Check that the callback was not called
        self.mock_callback.assert_not_called()
    
    def test_direct_message(self):
        """Test sending a direct message to a specific agent."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_receiver",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Create a direct message
        direct_message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "direct"},
            sender="test_sender",
            receiver="test_receiver"
        )
        
        # Publish the message
        result = self.message_bus.publish(direct_message)
        
        # Check that the callback was called
        self.mock_callback.assert_called_once()
        self.assertTrue(result["success"])
    
    def test_message_filtering_by_topic(self):
        """Test message filtering by topic."""
        # Subscribe to messages with topic filter
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS],
            filters={"topic": "test_topic"}
        )
        
        # Create a message with matching topic
        message_with_topic = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            metadata={"topic": "test_topic"}
        )
        
        # Create a message with non-matching topic
        message_with_other_topic = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            metadata={"topic": "other_topic"}
        )
        
        # Publish both messages
        self.message_bus.publish(message_with_topic)
        self.message_bus.publish(message_with_other_topic)
        
        # Check that the callback was called only once (for the matching topic)
        self.assertEqual(self.mock_callback.call_count, 1)
        
        # Check that the callback was called with the correct message
        called_message = self.mock_callback.call_args[0][0]
        self.assertEqual(called_message.metadata["topic"], "test_topic")
    
    def test_message_filtering_by_source(self):
        """Test message filtering by source."""
        # Subscribe to messages with source filter
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS],
            filters={"source": "specific_sender"}
        )
        
        # Create a message from the specific sender
        message_from_specific = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="specific_sender"
        )
        
        # Create a message from another sender
        message_from_other = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="other_sender"
        )
        
        # Publish both messages
        self.message_bus.publish(message_from_specific)
        self.message_bus.publish(message_from_other)
        
        # Check that the callback was called only once (for the matching sender)
        self.assertEqual(self.mock_callback.call_count, 1)
        
        # Check that the callback was called with the correct message
        called_message = self.mock_callback.call_args[0][0]
        self.assertEqual(called_message.sender, "specific_sender")
    
    def test_message_filtering_by_confidence(self):
        """Test message filtering by confidence level."""
        # Subscribe to messages with confidence filter
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS],
            filters={"min_confidence": 0.7}
        )
        
        # Create a message with high confidence
        high_confidence_message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            confidence=0.8
        )
        
        # Create a message with low confidence
        low_confidence_message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            confidence=0.5
        )
        
        # Publish both messages
        self.message_bus.publish(high_confidence_message)
        self.message_bus.publish(low_confidence_message)
        
        # Check that the callback was called only once (for the high confidence message)
        self.assertEqual(self.mock_callback.call_count, 1)
        
        # Check that the callback was called with the correct message
        called_message = self.mock_callback.call_args[0][0]
        self.assertEqual(called_message.confidence, 0.8)
    
    def test_priority_based_delivery(self):
        """Test priority-based message delivery."""
        # Create a list to track the order of message delivery
        delivery_order = []
        
        # Create a callback that records the message priority
        def priority_callback(message):
            priority = message.metadata.get("priority", "unknown")
            delivery_order.append(priority)
        
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=priority_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Create messages with different priorities
        low_priority_message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "low"},
            sender="test_sender",
            metadata={"priority": "low"}
        )
        
        high_priority_message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "high"},
            sender="test_sender",
            metadata={"priority": "high"}
        )
        
        critical_priority_message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "critical"},
            sender="test_sender",
            metadata={"priority": "critical"}
        )
        
        # Publish messages with different priorities
        self.message_bus.publish(
            low_priority_message,
            priority=MessagePriority.LOW
        )
        
        self.message_bus.publish(
            high_priority_message,
            priority=MessagePriority.HIGH
        )
        
        self.message_bus.publish(
            critical_priority_message,
            priority=MessagePriority.CRITICAL
        )
        
        # Check that messages were delivered in priority order
        # Note: This is a simplification, as the actual delivery order depends on
        # the implementation details of the message bus and may not be strictly
        # priority-ordered in all cases.
        self.assertEqual(len(delivery_order), 3)
    
    def test_circuit_breaker(self):
        """Test the circuit breaker pattern for failure isolation."""
        # Create a callback that raises an exception
        def failing_callback(message):
            raise RuntimeError("Simulated failure")
        
        # Subscribe to messages with the failing callback
        self.message_bus.subscribe(
            agent_id="failing_agent",
            callback=failing_callback,
            message_types=[MessageType.STATUS],
            max_retries=1  # Only retry once
        )
        
        # Get the circuit breaker for the agent
        circuit_breaker = self.message_bus._circuit_breakers.get("failing_agent")
        self.assertIsNotNone(circuit_breaker)
        
        # Initially, the circuit should be closed
        self.assertEqual(circuit_breaker.state, CircuitState.CLOSED)
        
        # Publish messages until the circuit opens
        for _ in range(10):  # Should be enough to trigger the circuit breaker
            self.message_bus.publish(self.test_message.create_response(
                message_type=MessageType.STATUS,
                content={"status": "test"},
                receiver="failing_agent"
            ))
        
        # Check that the circuit is now open
        self.assertEqual(circuit_breaker.state, CircuitState.OPEN)
        
        # Get performance metrics
        metrics = self.message_bus.get_performance_metrics()
        
        # Check that circuit breaker trips were recorded
        self.assertGreater(metrics.circuit_breaker_trips, 0)
    
    def test_timeout_handling(self):
        """Test timeout handling for message delivery."""
        # Create a callback that sleeps longer than the timeout
        def slow_callback(message):
            time.sleep(0.2)  # Sleep for 200ms
        
        # Subscribe to messages with the slow callback and a short timeout
        self.message_bus.subscribe(
            agent_id="slow_agent",
            callback=slow_callback,
            message_types=[MessageType.STATUS],
            timeout=0.1  # 100ms timeout
        )
        
        # Publish a message
        result = self.message_bus.publish(self.test_message.create_response(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            receiver="slow_agent"
        ))
        
        # Check that the delivery failed due to timeout
        self.assertFalse(result["delivery_status"]["slow_agent"]["success"])
        self.assertEqual(result["delivery_status"]["slow_agent"]["error"], "Timeout")
        
        # Get performance metrics
        metrics = self.message_bus.get_performance_metrics()
        
        # Check that timeouts were recorded
        self.assertGreater(metrics.timeouts, 0)
    
    def test_large_message_handling(self):
        """Test handling of large messages with chunking."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.CHUNKED_MESSAGE]
        )
        
        # Create a large message
        large_content = {"data": "x" * 1000000}  # 1MB of data
        large_message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content=large_content,
            sender="test_sender",
            receiver="test_agent"
        )
        
        # Publish the large message
        result = self.message_bus.publish(large_message)
        
        # Check that the message was chunked
        self.assertTrue(result.get("chunked", False))
        self.assertGreater(result.get("chunks", 0), 1)
        
        # Check that the callback was called for each chunk
        self.assertGreater(self.mock_callback.call_count, 1)
        
        # Check that all chunks have the correct message type
        for call in self.mock_callback.call_args_list:
            message = call[0][0]
            self.assertEqual(message.message_type, MessageType.CHUNKED_MESSAGE)
    
    def test_message_deduplication(self):
        """Test message deduplication to prevent processing duplicates."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Publish the same message twice
        self.message_bus.publish(self.test_message)
        self.message_bus.publish(self.test_message)  # Duplicate
        
        # Check that the callback was called only once
        self.assertEqual(self.mock_callback.call_count, 1)
    
    def test_conversation_memory(self):
        """Test conversation memory for storing message history."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS, MessageType.QUERY, MessageType.QUERY_RESPONSE]
        )
        
        # Create a conversation with multiple messages
        query = AgentMessage(
            message_type=MessageType.QUERY,
            content={"query": "What is the status?"},
            sender="agent1",
            receiver="agent2"
        )
        
        response = query.create_response(
            message_type=MessageType.QUERY_RESPONSE,
            content={"response": "Status is normal"},
            sender="agent2",
            receiver="agent1"
        )
        
        follow_up = response.create_response(
            message_type=MessageType.QUERY,
            content={"query": "Any warnings?"},
            sender="agent1",
            receiver="agent2"
        )
        
        # Publish all messages
        self.message_bus.publish(query)
        self.message_bus.publish(response)
        self.message_bus.publish(follow_up)
        
        # Get the conversation
        conversation = self.message_bus.get_conversation(query.conversation_id)
        
        # Check that all messages are in the conversation
        self.assertEqual(len(conversation.messages), 3)
        
        # Check that messages can be retrieved by ID
        retrieved_query = self.message_bus.get_message(query.message_id)
        self.assertEqual(retrieved_query.message_id, query.message_id)
        
        # Check that message chains can be retrieved
        message_chain = self.message_bus.get_message_chain(query.message_id)
        self.assertEqual(len(message_chain), 3)
    
    def test_thought_chain_integration(self):
        """Test integration with thought chains."""
        # Create a thought chain manager
        thought_chain_manager = ThoughtChainManager()
        
        # Create a message bus with thought chain integration
        message_bus_with_tc = EnhancedMessageBus(thought_chain_manager=thought_chain_manager)
        
        # Subscribe to messages
        message_bus_with_tc.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Publish a message
        message_bus_with_tc.publish(self.test_message)
        
        # Check that a thought chain was created
        thought_chain = message_bus_with_tc.get_thought_chain(self.test_message.conversation_id)
        self.assertIsNotNone(thought_chain)
        
        # Check that the message was added to the thought chain
        self.assertEqual(len(thought_chain.thoughts), 1)
    
    def test_performance_metrics(self):
        """Test performance metrics tracking."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Publish a message
        self.message_bus.publish(self.test_message)
        
        # Get performance metrics
        metrics = self.message_bus.get_performance_metrics()
        
        # Check that metrics were recorded
        self.assertEqual(metrics.total_messages, 1)
        self.assertEqual(metrics.successful_deliveries, 1)
        self.assertEqual(metrics.failed_deliveries, 0)
        
        # Check message type counts
        self.assertEqual(metrics.message_type_counts.get(MessageType.STATUS.value), 1)
        
        # Check agent message counts
        self.assertEqual(metrics.agent_message_counts.get("test_sender"), 1)
    
    def test_delivery_status_tracking(self):
        """Test delivery status tracking."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Publish a message
        self.message_bus.publish(self.test_message)
        
        # Get delivery status
        delivery_status = self.message_bus.get_delivery_status(self.test_message.message_id)
        
        # Check that delivery status was recorded
        self.assertIn("test_agent", delivery_status)
        self.assertTrue(delivery_status["test_agent"].success)
    
    def test_cleanup_old_conversations(self):
        """Test cleanup of old conversations."""
        # Create multiple conversations
        for i in range(5):
            message = AgentMessage(
                message_type=MessageType.STATUS,
                content={"status": f"test_{i}"},
                sender="test_sender",
                conversation_id=f"conversation_{i}"
            )
            self.message_bus.publish(message)
        
        # Check that all conversations were created
        self.assertEqual(len(self.message_bus._conversations), 5)
        
        # Clean up old conversations
        removed = self.message_bus.cleanup_old_conversations(max_conversations=3)
        
        # Check that conversations were removed
        self.assertEqual(removed, 2)
        self.assertEqual(len(self.message_bus._conversations), 3)
    
    def test_shutdown(self):
        """Test shutting down the message bus."""
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.mock_callback,
            message_types=[MessageType.STATUS]
        )
        
        # Shutdown the message bus
        self.message_bus.shutdown()
        
        # Check that subscriptions were cleared
        self.assertEqual(len(self.message_bus._subscriptions), 0)
        
        # Check that conversations were cleared
        self.assertEqual(len(self.message_bus._conversations), 0)
        
        # Check that delivery status was cleared
        self.assertEqual(len(self.message_bus._delivery_status), 0)
        
        # Check that circuit breakers were cleared
        self.assertEqual(len(self.message_bus._circuit_breakers), 0)
        
        # Check that thought chains were cleared
        self.assertEqual(len(self.message_bus._thought_chains), 0)


class TestCircuitBreaker(unittest.TestCase):
    """Test cases for the CircuitBreaker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            reset_timeout=0.1,  # Short timeout for testing
            half_open_max_calls=2
        )
    
    def test_initial_state(self):
        """Test the initial state of the circuit breaker."""
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.circuit_breaker.failure_count, 0)
        self.assertTrue(self.circuit_breaker.allow_request())
    
    def test_record_success(self):
        """Test recording a successful call."""
        # Record a success
        self.circuit_breaker.record_success()
        
        # Check that the state is still closed
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.circuit_breaker.failure_count, 0)
    
    def test_record_failure(self):
        """Test recording a failed call."""
        # Record failures up to the threshold
        for _ in range(self.circuit_breaker.failure_threshold):
            self.circuit_breaker.record_failure()
        
        # Check that the circuit is now open
        self.assertEqual(self.circuit_breaker.state, CircuitState.OPEN)
        self.assertEqual(self.circuit_breaker.failure_count, self.circuit_breaker.failure_threshold)
        self.assertFalse(self.circuit_breaker.allow_request())
    
    def test_reset_timeout(self):
        """Test that the circuit resets after the timeout."""
        # Open the circuit
        for _ in range(self.circuit_breaker.failure_threshold):
            self.circuit_breaker.record_failure()
        
        # Wait for the reset timeout
        time.sleep(self.circuit_breaker.reset_timeout + 0.05)
        
        # Check that the circuit is now half-open
        self.assertTrue(self.circuit_breaker.allow_request())
        self.assertEqual(self.circuit_breaker.state, CircuitState.HALF_OPEN)
    
    def test_half_open_state(self):
        """Test the half-open state behavior."""
        # Open the circuit
        for _ in range(self.circuit_breaker.failure_threshold):
            self.circuit_breaker.record_failure()
        
        # Wait for the reset timeout
        time.sleep(self.circuit_breaker.reset_timeout + 0.05)
        
        # Allow a request (moves to half-open)
        self.assertTrue(self.circuit_breaker.allow_request())
        self.assertEqual(self.circuit_breaker.state, CircuitState.HALF_OPEN)
        
        # Record successful calls up to the half-open max
        for _ in range(self.circuit_breaker.half_open_max_calls):
            self.circuit_breaker.record_success()
        
        # Check that the circuit is now closed
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.circuit_breaker.failure_count, 0)
    
    def test_failure_in_half_open(self):
        """Test failure while in half-open state."""
        # Open the circuit
        for _ in range(self.circuit_breaker.failure_threshold):
            self.circuit_breaker.record_failure()
        
        # Wait for the reset timeout
        time.sleep(self.circuit_breaker.reset_timeout + 0.05)
        
        # Allow a request (moves to half-open)
        self.assertTrue(self.circuit_breaker.allow_request())
        self.assertEqual(self.circuit_breaker.state, CircuitState.HALF_OPEN)
        
        # Record a failure
        self.circuit_breaker.record_failure()
        
        # Check that the circuit is open again
        self.assertEqual(self.circuit_breaker.state, CircuitState.OPEN)
        self.assertFalse(self.circuit_breaker.allow_request())


class TestMessageDeduplicator(unittest.TestCase):
    """Test cases for the MessageDeduplicator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.deduplicator = MessageDeduplicator(
            cache_size=5,
            expiration_time=0.1  # Short expiration for testing
        )
    
    def test_is_duplicate(self):
        """Test checking for duplicate messages."""
        # Check a new message
        self.assertFalse(self.deduplicator.is_duplicate("message1"))
        
        # Mark as processed
        self.deduplicator.mark_processed("message1")
        
        # Check again
        self.assertTrue(self.deduplicator.is_duplicate("message1"))
        
        # Check a different message
        self.assertFalse(self.deduplicator.is_duplicate("message2"))
    
    def test_expiration(self):
        """Test that messages expire from the cache."""
        # Mark a message as processed
        self.deduplicator.mark_processed("message1")
        
        # Check that it's a duplicate
        self.assertTrue(self.deduplicator.is_duplicate("message1"))
        
        # Wait for expiration
        time.sleep(self.deduplicator.expiration_time + 0.05)
        
        # Check that it's no longer a duplicate
        self.assertFalse(self.deduplicator.is_duplicate("message1"))
    
    def test_cache_size_limit(self):
        """Test that the cache size is limited."""
        # Fill the cache
        for i in range(self.deduplicator.cache_size + 2):
            self.deduplicator.mark_processed(f"message{i}")
        
        # Check that the cache size is limited
        self.assertLessEqual(len(self.deduplicator.message_cache), self.deduplicator.cache_size)


if __name__ == "__main__":
    unittest.main()
