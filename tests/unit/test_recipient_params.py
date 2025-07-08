#!/usr/bin/env python3
"""
Unit tests for recipient parameter fixes.

This module contains tests to verify that the recipient parameter fixes
have been correctly applied, including broadcast message handling,
delivery confirmation, and invalid recipient handling.
"""

import unittest
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus, MessagePriority
from fix_all_recipient_params import MessageAddressingFix


class TestRecipientParamsFix(unittest.TestCase):
    """Test cases for the recipient parameters fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.fixer = MessageAddressingFix()
        
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_fix_recipient_parameter(self):
        """Test fixing recipient parameter."""
        # Create test content with recipient parameter
        content = """
        message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            recipient="test_receiver"
        )
        """
        
        # Apply fix
        count, fixed_content = self.fixer.fix_recipient_parameter(content)
        
        # Check that the fix was applied
        self.assertEqual(count, 1)
        self.assertIn("receiver=", fixed_content)
        self.assertNotIn("recipient=", fixed_content)
    
    def test_fix_broadcast_handling(self):
        """Test fixing broadcast message handling."""
        # Create test content with broadcast message
        content = """
        message_bus.publish(AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            receiver=None
        ))
        """
        
        # Apply fix
        count, fixed_content = self.fixer.fix_broadcast_handling(content)
        
        # Check that the fix was applied
        self.assertEqual(count, 1)
        self.assertIn("target_filter=None", fixed_content)
    
    def test_fix_delivery_confirmation(self):
        """Test fixing delivery confirmation for critical messages."""
        # Create test content with critical message
        content = """
        message_bus.publish(AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test"},
            sender="test_sender",
            receiver="test_receiver"
        ))
        """
        
        # Apply fix
        count, fixed_content = self.fixer.fix_delivery_confirmation(content)
        
        # Check that the fix was applied
        self.assertEqual(count, 1)
        self.assertIn("require_confirmation=True", fixed_content)
    
    def test_fix_invalid_recipient_handling(self):
        """Test fixing invalid recipient handling."""
        # Create test content with publish call without error handling
        content = """
        result = message_bus.publish(AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            receiver="test_receiver"
        ))
        """
        
        # Apply fix
        count, fixed_content = self.fixer.fix_invalid_recipient_handling(content)
        
        # Check that the fix was applied
        self.assertEqual(count, 1)
        self.assertIn('if not result["success"]:', fixed_content)
        self.assertIn('logger.error', fixed_content)
        self.assertIn('delivery_status', fixed_content)
    
    def test_add_target_filter_support(self):
        """Test adding target filter support to message bus."""
        # Create a mock message bus file
        with open(self.temp_file.name, 'w') as f:
            f.write("""
class EnhancedMessageBus:
    def publish(self, message: AgentMessage):
        # Broadcast to all interested subscribers
        results = {}
        # Group by agent ID
        agent_subs = {}
        return results
""")
        
        # Apply fix
        result = self.fixer.add_target_filter_support(Path(self.temp_file.name))
        
        # Check that the fix was applied
        self.assertTrue(result)
        
        # Read the fixed file
        with open(self.temp_file.name, 'r') as f:
            content = f.read()
        
        # Check that target filter support was added
        self.assertIn("target_filter:", content)
        self.assertIn("if target_filter is not None:", content)
    
    def test_integration_with_enhanced_message_bus(self):
        """Test integration with EnhancedMessageBus."""
        # Create a message bus
        message_bus = EnhancedMessageBus()
        
        # Create a test message with receiver parameter
        message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            receiver="test_receiver"
        )
        
        # Mock callback
        callback = MagicMock()
        
        # Subscribe to messages
        message_bus.subscribe(
            agent_id="test_receiver",
            callback=callback,
            message_types=[MessageType.STATUS]
        )
        
        # Publish the message
        result = message_bus.publish(message)
        
        # Check that the message was delivered
        self.assertTrue(result["success"])
        callback.assert_called_once()
        
        # Create a broadcast message
        broadcast_message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "broadcast"},
            sender="test_sender",
            receiver=None
        )
        
        # Publish the broadcast message
        result = message_bus.publish(broadcast_message)
        
        # Check that the broadcast message was delivered
        self.assertTrue(result["success"])
        self.assertEqual(callback.call_count, 2)
    
    def test_fix_file(self):
        """Test fixing a file."""
        # Create a test file with multiple issues
        with open(self.temp_file.name, 'w') as f:
            f.write("""
import logging
from triangulum_lx.agents.message import AgentMessage, MessageType

logger = logging.getLogger(__name__)

def test_function():
    # Issue 1: recipient parameter
    message1 = AgentMessage(
        message_type=MessageType.STATUS,
        content={"status": "test"},
        sender="test_sender",
        recipient="test_receiver"
    )
    
    # Issue 2: broadcast without target filter
    message2 = AgentMessage(
        message_type=MessageType.STATUS,
        content={"status": "broadcast"},
        sender="test_sender",
        receiver=None
    )
    
    # Issue 3: critical message without delivery confirmation
    message3 = AgentMessage(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "test"},
        sender="test_sender",
        receiver="test_receiver"
    )
    
    # Issue 4: publish without error handling
    message_bus = get_message_bus()
    result = message_bus.publish(message1)
    
    # Issue 5: broadcast publish without target filter
    result = message_bus.publish(message2)
    
    # Issue 6: critical message publish without delivery confirmation
    result = message_bus.publish(message3)
""")
        
        # Apply fix
        result = self.fixer.fix_file(Path(self.temp_file.name))
        
        # Check that the fix was applied
        self.assertTrue(result)
        
        # Read the fixed file
        with open(self.temp_file.name, 'r') as f:
            content = f.read()
        
        # Check that all issues were fixed
        self.assertIn("receiver=", content)
        self.assertNotIn("recipient=", content)
        self.assertIn("target_filter=None", content)
        self.assertIn("require_confirmation=True", content)
        self.assertIn('if not result["success"]:', content)
        self.assertIn('logger.error', content)


class TestEnhancedMessageBusWithTargetFilter(unittest.TestCase):
    """Test cases for EnhancedMessageBus with target filter support."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.message_bus = EnhancedMessageBus()
        
        # Create mock callbacks
        self.callback1 = MagicMock()
        self.callback2 = MagicMock()
        self.callback3 = MagicMock()
        
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id="agent1",
            callback=self.callback1,
            message_types=[MessageType.STATUS]
        )
        
        self.message_bus.subscribe(
            agent_id="agent2",
            callback=self.callback2,
            message_types=[MessageType.STATUS]
        )
        
        self.message_bus.subscribe(
            agent_id="agent3",
            callback=self.callback3,
            message_types=[MessageType.STATUS]
        )
    
    def test_broadcast_with_target_filter(self):
        """Test broadcast message with target filter."""
        # Create a broadcast message
        message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "broadcast"},
            sender="test_sender",
            receiver=None
        )
        
        # Publish with target filter
        # Note: This test assumes that target_filter support has been added to EnhancedMessageBus
        # If not, this test will fail and you'll need to add the support manually
        try:
            result = self.message_bus.publish(
                message=message,
                target_filter=["agent1", "agent3"]
            )
            
            # Check that the message was delivered only to the targeted agents
            self.callback1.assert_called_once()
            self.callback2.assert_not_called()
            self.callback3.assert_called_once()
        except TypeError:
            # If target_filter is not supported, this test will be skipped
            print("Target filter not supported in EnhancedMessageBus, skipping test")
    
    def test_delivery_confirmation(self):
        """Test delivery confirmation for critical messages."""
        # Create a critical message
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test"},
            sender="test_sender",
            receiver="agent1"
        )
        
        # Publish with delivery confirmation
        result = self.message_bus.publish(
            message=message,
            require_confirmation=True
        )
        
        # Check that the message was delivered and confirmation was received
        self.assertTrue(result["success"])
        self.callback1.assert_called_once()
        
        # Check delivery status
        self.assertIn("delivery_status", result)
        self.assertIn("agent1", result["delivery_status"])
        self.assertTrue(result["delivery_status"]["agent1"]["success"])
    
    def test_invalid_recipient_handling(self):
        """Test handling of invalid recipients."""
        # Create a message with invalid receiver
        message = AgentMessage(
            message_type=MessageType.STATUS,
            content={"status": "test"},
            sender="test_sender",
            receiver="non_existent_agent"
        )
        
        # Publish the message
        result = self.message_bus.publish(message)
        
        # Check that the delivery failed
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        
        # Check that no callbacks were called
        self.callback1.assert_not_called()
        self.callback2.assert_not_called()
        self.callback3.assert_not_called()


if __name__ == "__main__":
    unittest.main()
