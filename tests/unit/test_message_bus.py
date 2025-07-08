"""
Unit tests for the MessageBus class.

Tests the functionality of the MessageBus, including message routing,
subscription management, conversation tracking, and handler registration.
"""

import unittest
from unittest.mock import Mock, patch
import logging
import time

from triangulum_lx.agents.message_bus import MessageBus
from triangulum_lx.agents.message import AgentMessage, MessageType

# Suppress log messages during tests
logging.basicConfig(level=logging.CRITICAL)


class TestMessageBus(unittest.TestCase):
    """Test cases for the MessageBus class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.message_bus = MessageBus()
        self.callback_mock = Mock()
    
    def test_subscribe(self):
        """Test subscribing an agent to the message bus."""
        # Subscribe an agent
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.callback_mock,
            message_types=[MessageType.TASK_REQUEST]
        )
        
        # Publish a message of the subscribed type
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"test": "content"},
            sender="sender_agent"
        )
        self.message_bus.publish(message)
        
        # Check that the callback was called
        self.callback_mock.assert_called_once_with(message)
    
    def test_unsubscribe(self):
        """Test unsubscribing an agent from the message bus."""
        # Subscribe an agent
        self.message_bus.subscribe(
            agent_id="test_agent",
            callback=self.callback_mock,
            message_types=[MessageType.TASK_REQUEST]
        )
        
        # Unsubscribe the agent
        self.message_bus.unsubscribe(
            agent_id="test_agent",
            message_types=[MessageType.TASK_REQUEST]
        )
        
        # Publish a message of the unsubscribed type
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"test": "content"},
            sender="sender_agent"
        )
        self.message_bus.publish(message)
        
        # Check that the callback was not called
        self.callback_mock.assert_not_called()
    
    def test_register_handler(self):
        """Test registering a handler for a specific message type."""
        # Register a handler
        self.message_bus.register_handler(
            handler_id="test_handler",
            message_type=MessageType.TASK_REQUEST,
            callback=self.callback_mock
        )
        
        # Publish a message of the registered type
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"test": "content"},
            sender="sender_agent"
        )
        self.message_bus.publish(message)
        
        # Check that the callback was called
        self.callback_mock.assert_called_once_with(message)
    
    def test_register_handler_different_message_type(self):
        """Test handler doesn't receive messages of different types."""
        # Register a handler for one message type
        self.message_bus.register_handler(
            handler_id="test_handler",
            message_type=MessageType.TASK_REQUEST,
            callback=self.callback_mock
        )
        
        # Publish a message of a different type
        message = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            content={"test": "content"},
            sender="sender_agent"
        )
        self.message_bus.publish(message)
        
        # Check that the callback was not called
        self.callback_mock.assert_not_called()
    
    def test_register_handler_direct_message(self):
        """Test handler receives directed messages."""
        # Register a handler
        self.message_bus.register_handler(
            handler_id="test_handler",
            message_type=MessageType.TASK_REQUEST,
            callback=self.callback_mock
        )
        
        # Publish a direct message to the handler
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"test": "content"},
            sender="sender_agent",
            receiver="test_handler"
        )
        self.message_bus.publish(message)
        
        # Check that the callback was called
        self.callback_mock.assert_called_once_with(message)
    
    def test_register_handler_maps_to_subscribe(self):
        """Test register_handler correctly maps to subscribe method."""
        # Mock the subscribe method
        with patch.object(self.message_bus, 'subscribe') as mock_subscribe:
            # Call register_handler
            self.message_bus.register_handler(
                handler_id="test_handler",
                message_type=MessageType.TASK_REQUEST,
                callback=self.callback_mock
            )
            
            # Check that subscribe was called with correct arguments
            mock_subscribe.assert_called_once_with(
                agent_id="test_handler",
                callback=self.callback_mock,
                message_types=[MessageType.TASK_REQUEST]
            )
    
    def test_conversation_tracking(self):
        """Test conversation tracking functionality."""
        # Create a conversation with two messages
        message1 = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"test": "request"},
            sender="agent1",
            receiver="agent2",
            conversation_id="conv123"
        )
        
        message2 = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            content={"test": "result"},
            sender="agent2",
            receiver="agent1",
            conversation_id="conv123",
            parent_id=message1.message_id
        )
        
        # Publish the messages
        self.message_bus.publish(message1)
        self.message_bus.publish(message2)
        
        # Get the conversation
        conversation = self.message_bus.get_conversation("conv123")
        
        # Check that the conversation contains both messages
        self.assertIsNotNone(conversation)
        self.assertEqual(len(conversation.messages), 2)
        
        # Test message chain retrieval with both parents and children
        chain = self.message_bus.get_message_chain(message1.message_id)
        
        # Chain should have both messages (message1 + its child message2)
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0].message_id, message1.message_id)
        self.assertEqual(chain[1].message_id, message2.message_id)
        
        # Test message chain from child with parents only
        chain_with_parents = self.message_bus.get_message_chain(
            message_id=message2.message_id,
            include_parents=True,
            include_children=False
        )
        
        # Chain should have both messages (parent message1 + message2)
        self.assertEqual(len(chain_with_parents), 2)
        self.assertEqual(chain_with_parents[0].message_id, message1.message_id)
        self.assertEqual(chain_with_parents[1].message_id, message2.message_id)


    def test_cleanup_old_conversations(self):
        """Test cleanup of old conversations."""
        # Create several conversations
        for i in range(5):
            message = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"test": f"message{i}"},
                sender="agent1",
                receiver="agent2",
                conversation_id=f"conv{i}"
            )
            self.message_bus.publish(message)
        
        # Check that we have 5 conversations
        self.assertEqual(len(self.message_bus._conversations), 5)
        
        # Clean up conversations, keeping only 2
        removed = self.message_bus.cleanup_old_conversations(max_conversations=2)
        
        # Check that we removed 3 conversations
        self.assertEqual(removed, 3)
        self.assertEqual(len(self.message_bus._conversations), 2)
    
    def test_cleanup_old_conversations_by_age(self):
        """Test cleanup of old conversations by age."""
        # Create a conversation with an old timestamp
        old_message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"test": "old"},
            sender="agent1",
            receiver="agent2",
            conversation_id="old_conv",
            timestamp=time.time() - 1000  # 1000 seconds old
        )
        self.message_bus.publish(old_message)
        
        # Create a conversation with a recent timestamp
        new_message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"test": "new"},
            sender="agent1",
            receiver="agent2",
            conversation_id="new_conv"
        )
        self.message_bus.publish(new_message)
        
        # Check that we have 2 conversations
        self.assertEqual(len(self.message_bus._conversations), 2)
        
        # Clean up conversations older than 500 seconds
        removed = self.message_bus.cleanup_old_conversations(max_age_seconds=500)
        
        # Check that we removed 1 conversation
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.message_bus._conversations), 1)
        self.assertIn("new_conv", self.message_bus._conversations)
        self.assertNotIn("old_conv", self.message_bus._conversations)


if __name__ == "__main__":
    unittest.main()
