"""
Unit tests for the agent message protocol.

This module contains tests for the AgentMessage class, MessageBus, and
ConversationMemory, verifying that the agent communication protocol
works as expected.
"""

import unittest
import json
import threading
import time
from unittest.mock import MagicMock

from triangulum_lx.agents.message import AgentMessage, MessageType, ConversationMemory
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus as MessageBus, SubscriptionInfo


class TestAgentMessage(unittest.TestCase):
    """Test case for the AgentMessage class."""
    
    def test_create_message(self):
        """Test creating a valid agent message."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="test_agent"
        )
        
        self.assertEqual(message.message_type, MessageType.TASK_REQUEST)
        self.assertEqual(message.content, {"task": "Analyze code"})
        self.assertEqual(message.sender, "test_agent")
        self.assertIsNone(message.receiver)
        self.assertIsNotNone(message.message_id)
        self.assertIsNotNone(message.timestamp)
        self.assertIsNotNone(message.conversation_id)
        
        # Conversation ID should default to message ID if not provided
        self.assertEqual(message.conversation_id, message.message_id)
        
        # Check schema version
        self.assertEqual(message.schema_version, "1.1")
        
        # Check new fields have default empty values
        self.assertEqual(message.problem_context, {})
        self.assertEqual(message.analysis_results, {})
        self.assertEqual(message.suggested_actions, [])
    
    def test_create_message_with_enhanced_fields(self):
        """Test creating a message with the enhanced fields."""
        problem_context = {
            "file_path": "src/example.py",
            "error_message": "TypeError: cannot concatenate 'str' and 'int' objects",
            "stack_trace": ["line 1", "line 2"]
        }
        
        analysis_results = {
            "error_type": "TypeError",
            "error_cause": "Type mismatch",
            "affected_code": "print('Result: ' + 42)"
        }
        
        suggested_actions = [
            {
                "action_type": "code_change",
                "file": "src/example.py",
                "line": 10,
                "original": "print('Result: ' + 42)",
                "replacement": "print('Result: ' + str(42))"
            }
        ]
        
        message = AgentMessage(
            message_type=MessageType.CODE_ANALYSIS,
            content={"analysis": "Code has a type error"},
            sender="analyzer_agent",
            problem_context=problem_context,
            analysis_results=analysis_results,
            suggested_actions=suggested_actions
        )
        
        # Verify the enhanced fields were set correctly
        self.assertEqual(message.problem_context, problem_context)
        self.assertEqual(message.analysis_results, analysis_results)
        self.assertEqual(message.suggested_actions, suggested_actions)
    
    def test_message_validation(self):
        """Test that messages are validated correctly."""
        # Invalid message type
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type="not_an_enum",
                content={"task": "Analyze code"},
                sender="test_agent"
            )
        
        # Invalid content
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content="not_a_dict",
                sender="test_agent"
            )
        
        # Missing sender
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"task": "Analyze code"},
                sender=""
            )
        
        # Invalid confidence
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"task": "Analyze code"},
                sender="test_agent",
                confidence=1.5
            )
        
        # Invalid schema version
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"task": "Analyze code"},
                sender="test_agent",
                schema_version=1.1  # Should be string
            )
        
        # Invalid problem_context
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"task": "Analyze code"},
                sender="test_agent",
                problem_context="not_a_dict"
            )
        
        # Invalid analysis_results
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"task": "Analyze code"},
                sender="test_agent",
                analysis_results="not_a_dict"
            )
        
        # Invalid suggested_actions
        with self.assertRaises(ValueError):
            AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"task": "Analyze code"},
                sender="test_agent",
                suggested_actions="not_a_list"
            )
    
    def test_serialization(self):
        """Test serializing and deserializing messages."""
        original = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="test_agent",
            receiver="another_agent",
            confidence=0.8,
            metadata={"priority": "high"},
            problem_context={"file_path": "example.py"},
            analysis_results={"error_type": "TypeError"},
            suggested_actions=[{"action_type": "code_change"}]
        )
        
        # Test to_dict and from_dict
        message_dict = original.to_dict()
        self.assertEqual(message_dict["message_type"], "task_request")
        self.assertEqual(message_dict["problem_context"], {"file_path": "example.py"})
        self.assertEqual(message_dict["analysis_results"], {"error_type": "TypeError"})
        self.assertEqual(message_dict["suggested_actions"], [{"action_type": "code_change"}])
        
        recreated = AgentMessage.from_dict(message_dict)
        self.assertEqual(recreated.message_type, original.message_type)
        self.assertEqual(recreated.content, original.content)
        self.assertEqual(recreated.sender, original.sender)
        self.assertEqual(recreated.receiver, original.receiver)
        self.assertEqual(recreated.message_id, original.message_id)
        self.assertEqual(recreated.conversation_id, original.conversation_id)
        self.assertEqual(recreated.confidence, original.confidence)
        self.assertEqual(recreated.metadata, original.metadata)
        self.assertEqual(recreated.problem_context, original.problem_context)
        self.assertEqual(recreated.analysis_results, original.analysis_results)
        self.assertEqual(recreated.suggested_actions, original.suggested_actions)
        
        # Test to_json and from_json
        json_str = original.to_json()
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict["message_type"], "task_request")
        self.assertEqual(json_dict["problem_context"], {"file_path": "example.py"})
        
        recreated_from_json = AgentMessage.from_json(json_str)
        self.assertEqual(recreated_from_json.message_type, original.message_type)
        self.assertEqual(recreated_from_json.content, original.content)
        self.assertEqual(recreated_from_json.problem_context, original.problem_context)
    
    def test_create_response(self):
        """Test creating a response message."""
        original = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="agent_a",
            receiver="agent_b",
            conversation_id="conv123",
            problem_context={"file_path": "example.py"}
        )
        
        response = original.create_response(
            message_type=MessageType.TASK_RESULT,
            content={"result": "Analysis complete"},
            confidence=0.9,
            metadata={"execution_time": 1.5},
            problem_context={"file_path": "example.py", "line_number": 42},
            analysis_results={"error_type": "TypeError"},
            suggested_actions=[{"action_type": "code_change"}]
        )
        
        self.assertEqual(response.message_type, MessageType.TASK_RESULT)
        self.assertEqual(response.content, {"result": "Analysis complete"})
        self.assertEqual(response.sender, "agent_b")
        self.assertEqual(response.receiver, "agent_a")
        self.assertEqual(response.conversation_id, "conv123")
        self.assertEqual(response.parent_id, original.message_id)
        self.assertEqual(response.confidence, 0.9)
        self.assertEqual(response.metadata, {"execution_time": 1.5})
        self.assertEqual(response.problem_context, {"file_path": "example.py", "line_number": 42})
        self.assertEqual(response.analysis_results, {"error_type": "TypeError"})
        self.assertEqual(response.suggested_actions, [{"action_type": "code_change"}])
    
    def test_backward_compatibility(self):
        """Test backward compatibility with old message formats."""
        # Create a dictionary representing an old format message (no schema_version)
        old_format = {
            "message_type": "task_request",
            "content": {"task": "Analyze code"},
            "sender": "test_agent",
            "message_id": "msg123",
            "timestamp": time.time(),
            "receiver": "another_agent",
            "conversation_id": "conv123",
            "confidence": 0.8,
            "metadata": {"priority": "high"}
        }
        
        # Convert to a message object
        message = AgentMessage.from_dict(old_format)
        
        # Verify the message was upgraded to the new schema
        self.assertEqual(message.schema_version, "1.1")
        self.assertEqual(message.problem_context, {})
        self.assertEqual(message.analysis_results, {})
        self.assertEqual(message.suggested_actions, [])
        
        # Core fields should be preserved
        self.assertEqual(message.message_type, MessageType.TASK_REQUEST)
        self.assertEqual(message.content, {"task": "Analyze code"})
        self.assertEqual(message.sender, "test_agent")
        self.assertEqual(message.message_id, "msg123")
        self.assertEqual(message.receiver, "another_agent")
        self.assertEqual(message.conversation_id, "conv123")
        self.assertEqual(message.confidence, 0.8)
        self.assertEqual(message.metadata, {"priority": "high"})


class TestConversationMemory(unittest.TestCase):
    """Test case for the ConversationMemory class."""
    
    def setUp(self):
        """Set up a conversation memory for testing."""
        self.conversation_id = "test_conversation"
        self.memory = ConversationMemory(conversation_id=self.conversation_id)
        
        # Add some messages
        self.message1 = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Task 1"},
            sender="agent_a",
            receiver="agent_b",
            conversation_id=self.conversation_id,
            message_id="msg1"
        )
        
        self.message2 = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            content={"result": "Result 1"},
            sender="agent_b",
            receiver="agent_a",
            conversation_id=self.conversation_id,
            message_id="msg2",
            parent_id="msg1"
        )
        
        self.message3 = AgentMessage(
            message_type=MessageType.QUERY,
            content={"query": "Query 1"},
            sender="agent_a",
            receiver="agent_c",
            conversation_id=self.conversation_id,
            message_id="msg3"
        )
        
        self.memory.add_message(self.message1)
        self.memory.add_message(self.message2)
        self.memory.add_message(self.message3)
    
    def test_add_message(self):
        """Test adding messages to the conversation."""
        self.assertEqual(len(self.memory.messages), 3)
        
        # Try to add a message with a different conversation ID
        message4 = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Task 2"},
            sender="agent_a",
            conversation_id="different_conversation",
            message_id="msg4"
        )
        
        with self.assertRaises(ValueError):
            self.memory.add_message(message4)
    
    def test_get_message_by_id(self):
        """Test retrieving a message by its ID."""
        message = self.memory.get_message_by_id("msg2")
        self.assertEqual(message, self.message2)
        
        # Test with a non-existent ID
        self.assertIsNone(self.memory.get_message_by_id("non_existent"))
    
    def test_get_messages_by_type(self):
        """Test retrieving messages by type."""
        task_requests = self.memory.get_messages_by_type(MessageType.TASK_REQUEST)
        self.assertEqual(len(task_requests), 1)
        self.assertEqual(task_requests[0], self.message1)
        
        # Test with a type that has no messages
        error_messages = self.memory.get_messages_by_type(MessageType.ERROR)
        self.assertEqual(len(error_messages), 0)
    
    def test_get_messages_by_sender(self):
        """Test retrieving messages by sender."""
        agent_a_messages = self.memory.get_messages_by_sender("agent_a")
        self.assertEqual(len(agent_a_messages), 2)
        self.assertIn(self.message1, agent_a_messages)
        self.assertIn(self.message3, agent_a_messages)
        
        # Test with a sender that has no messages
        unknown_messages = self.memory.get_messages_by_sender("unknown_agent")
        self.assertEqual(len(unknown_messages), 0)
    
    def test_get_message_chain(self):
        """Test retrieving a chain of messages."""
        chain = self.memory.get_message_chain("msg1")
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0], self.message1)
        self.assertEqual(chain[1], self.message2)
        
        # Test with a message that has no children
        chain = self.memory.get_message_chain("msg3")
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0], self.message3)
        
        # Test with a non-existent ID
        chain = self.memory.get_message_chain("non_existent")
        self.assertEqual(len(chain), 0)
    
    def test_serialization(self):
        """Test serializing and deserializing conversation memory."""
        memory_dict = self.memory.to_dict()
        self.assertEqual(memory_dict["conversation_id"], self.conversation_id)
        self.assertEqual(len(memory_dict["messages"]), 3)
        
        recreated = ConversationMemory.from_dict(memory_dict)
        self.assertEqual(recreated.conversation_id, self.memory.conversation_id)
        self.assertEqual(len(recreated.messages), len(self.memory.messages))
        
        # Verify message details were preserved
        message = recreated.get_message_by_id("msg1")
        self.assertEqual(message.message_type, MessageType.TASK_REQUEST)
        self.assertEqual(message.content, {"task": "Task 1"})


class TestMessageBus(unittest.TestCase):
    """Test case for the MessageBus class."""
    
    def setUp(self):
        """Set up a message bus for testing."""
        self.message_bus = MessageBus()
        
        # Create mock callbacks
        self.agent_a_callback = MagicMock()
        self.agent_b_callback = MagicMock()
        self.agent_c_callback = MagicMock()
        
        # Subscribe agents
        self.message_bus.subscribe(
            agent_id="agent_a",
            callback=self.agent_a_callback,
            message_types=[MessageType.TASK_REQUEST, MessageType.QUERY]
        )
        
        self.message_bus.subscribe(
            agent_id="agent_b",
            callback=self.agent_b_callback,
            message_types=[MessageType.TASK_REQUEST, MessageType.TASK_RESULT]
        )
        
        self.message_bus.subscribe(
            agent_id="agent_c",
            callback=self.agent_c_callback
        )
    
    def test_direct_message_delivery(self):
        """Test delivering a message to a specific agent."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="agent_a",
            receiver="agent_b"
        )
        
        self.message_bus.publish(message)
        
        # agent_b should receive the message
        self.agent_b_callback.assert_called_once()
        called_message = self.agent_b_callback.call_args[0][0]
        self.assertEqual(called_message.message_type, MessageType.TASK_REQUEST)
        self.assertEqual(called_message.content, {"task": "Analyze code"})
        
        # Other agents should not receive it
        self.agent_a_callback.assert_not_called()
        self.agent_c_callback.assert_not_called()
        
        # Verify the message was stored in conversation memory
        conversation = self.message_bus.get_conversation(message.conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual(len(conversation.messages), 1)
    
    def test_broadcast_message(self):
        """Test broadcasting a message to all interested agents."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="agent_c"
        )
        
        self.message_bus.publish(message)
        
        # agent_a and agent_b should receive the message (they're subscribed to TASK_REQUEST)
        self.agent_a_callback.assert_called_once()
        self.agent_b_callback.assert_called_once()
        
        # agent_c should not receive its own broadcast
        self.agent_c_callback.assert_not_called()
    
    def test_message_type_filtering(self):
        """Test that messages are filtered by type."""
        # Send a message type that agent_a is not subscribed to
        message = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            content={"result": "Analysis complete"},
            sender="agent_c",
            receiver="agent_a"
        )
        
        self.message_bus.publish(message)
        
        # agent_a should not receive the message (not subscribed to TASK_RESULT)
        self.agent_a_callback.assert_not_called()
        
        # But it should still be stored in conversation memory
        conversation = self.message_bus.get_conversation(message.conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual(len(conversation.messages), 1)
    
    def test_unsubscribe(self):
        """Test unsubscribing from the message bus."""
        # Unsubscribe agent_a from all message types
        self.message_bus.unsubscribe(agent_id="agent_a")
        
        # Unsubscribe agent_b from TASK_RESULT only
        self.message_bus.unsubscribe(
            agent_id="agent_b",
            message_types=[MessageType.TASK_RESULT]
        )
        
        # Send a TASK_REQUEST message
        message1 = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Analyze code"},
            sender="agent_c"
        )
        
        self.message_bus.publish(message1)
        
        # agent_a should not receive it (unsubscribed from all)
        self.agent_a_callback.assert_not_called()
        
        # agent_b should still receive it (still subscribed to TASK_REQUEST)
        self.agent_b_callback.assert_called_once()
        self.agent_b_callback.reset_mock()
        
        # Send a TASK_RESULT message
        message2 = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            content={"result": "Analysis complete"},
            sender="agent_c"
        )
        
        self.message_bus.publish(message2)
        
        # Neither agent_a nor agent_b should receive it
        self.agent_a_callback.assert_not_called()
        self.agent_b_callback.assert_not_called()
    
    def test_conversation_management(self):
        """Test conversation management functionality."""
        # Create and publish messages in a conversation
        message1 = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "Task 1"},
            sender="agent_a",
            receiver="agent_b",
            conversation_id="test_convo"
        )
        
        message2 = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            content={"result": "Result 1"},
            sender="agent_b",
            receiver="agent_a",
            conversation_id="test_convo",
            parent_id=message1.message_id
        )
        
        self.message_bus.publish(message1)
        self.message_bus.publish(message2)
        
        # Get the conversation
        conversation = self.message_bus.get_conversation("test_convo")
        self.assertIsNotNone(conversation)
        self.assertEqual(len(conversation.messages), 2)
        
        # Test get_message
        retrieved_message = self.message_bus.get_message(message1.message_id)
        self.assertIsNotNone(retrieved_message)
        self.assertEqual(retrieved_message.content, message1.content)
        
        # Test get_message_chain
        chain = self.message_bus.get_message_chain(message1.message_id)
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0].message_id, message1.message_id)
        self.assertEqual(chain[1].message_id, message2.message_id)
        
        # Test clear_conversation
        self.message_bus.clear_conversation("test_convo")
        self.assertIsNone(self.message_bus.get_conversation("test_convo"))
        
        # Test clear_conversations
        message3 = AgentMessage(
            message_type=MessageType.QUERY,
            content={"query": "Query 1"},
            sender="agent_a",
            conversation_id="another_convo"
        )
        
        self.message_bus.publish(message3)
        self.assertIsNotNone(self.message_bus.get_conversation("another_convo"))
        
        self.message_bus.clear_conversations()
        self.assertIsNone(self.message_bus.get_conversation("another_convo"))


if __name__ == "__main__":
    unittest.main()
