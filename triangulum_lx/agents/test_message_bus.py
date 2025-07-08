"""
Test Message Bus for Triangulum Agentic System Testing

This module provides a stub implementation of the EnhancedMessageBus
that includes additional methods needed for testing.
"""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Set, Callable, Union

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus

logger = logging.getLogger(__name__)


class TestEnhancedMessageBus(EnhancedMessageBus):
    """Test-specific implementation of EnhancedMessageBus with additional testing methods."""
    
    def __init__(self, thought_chain_manager=None):
        """Initialize the test message bus."""
        super().__init__(thought_chain_manager=thought_chain_manager)
        
        # Add test-specific tracking
        self._message_history = []
        self._thought_chains = []
        self._message_results = {}
    
    def publish(self, message):
        """Override publish to track message history."""
        # Add to history
        self._message_history.append(message)
        
        # Store message ID for results
        message_id = message.message_id
        self._message_results[message_id] = {
            "timestamp": time.time(),
            "processed": False,
            "results": None
        }
        
        # Simulate some basic processing
        if message.receiver and message.receiver in [agent.agent_id for agent in self._subscriptions]:
            # This is a direct message
            pass
        
        # Return the message ID
        return message_id
    
    def send_message(self, message):
        """Alias for publish method for testing compatibility."""
        return self.publish(message)
    
    def get_message_history(self) -> List[AgentMessage]:
        """Get the history of all messages processed by the bus."""
        return self._message_history
    
    def get_thought_chains(self) -> List[Any]:
        """Get all thought chains tracked by the bus."""
        return self._thought_chains
    
    def add_thought_chain(self, thought_chain):
        """Add a thought chain for testing."""
        self._thought_chains.append(thought_chain)
    
    def store_result(self, message_id, result):
        """Store a result for a message."""
        if message_id in self._message_results:
            self._message_results[message_id]["processed"] = True
            self._message_results[message_id]["results"] = result
    
    def get_results(self, message_id):
        """Get results for a message."""
        if message_id in self._message_results:
            return self._message_results[message_id].get("results")
        return None
    
    def clear_history(self):
        """Clear the message history."""
        self._message_history = []
        self._thought_chains = []
        self._message_results = {}
