"""
Message Bus - Central message passing infrastructure for agent communication.

This module implements the MessageBus class which serves as the central hub for
routing messages between agents in the Triangulum system.
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Union, Callable, Set
from dataclasses import dataclass, field

from triangulum_lx.agents.message import AgentMessage, ConversationMemory, MessageType

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionInfo:
    """Information about a message subscription."""
    
    agent_id: str
    message_types: Set[MessageType]
    callback: Callable[[AgentMessage], None]


class MessageBus:
    """
    Central message routing system for agent communication.
    
    The MessageBus manages the routing of messages between agents, maintains
    conversation history, and provides a centralized communication infrastructure
    for the multi-agent system.
    """
    
    def __init__(self):
        """Initialize the message bus."""
        self._subscriptions: List[SubscriptionInfo] = []
        self._conversations: Dict[str, ConversationMemory] = {}
        self._lock = threading.RLock()
    
    def subscribe(self, 
                  agent_id: str, 
                  callback: Callable[[AgentMessage], None],
                  message_types: Optional[List[MessageType]] = None) -> None:
        """
        Subscribe an agent to receive messages.
        
        Args:
            agent_id: ID of the subscribing agent
            callback: Function to call when a message is received
            message_types: Types of messages to subscribe to (None for all)
        """
        with self._lock:
            message_types_set = set(message_types) if message_types else set(MessageType)
            
            # Check if subscription already exists
            for sub in self._subscriptions:
                if sub.agent_id == agent_id:
                    # Update existing subscription
                    sub.message_types.update(message_types_set)
                    sub.callback = callback
                    logger.debug(f"Updated subscription for agent {agent_id}")
                    return
            
            # Add new subscription
            self._subscriptions.append(
                SubscriptionInfo(
                    agent_id=agent_id,
                    message_types=message_types_set,
                    callback=callback
                )
            )
            logger.debug(f"Added subscription for agent {agent_id}")
    
    def unsubscribe(self, agent_id: str, message_types: Optional[List[MessageType]] = None) -> None:
        """
        Unsubscribe an agent from receiving messages.
        
        Args:
            agent_id: ID of the agent to unsubscribe
            message_types: Types of messages to unsubscribe from (None for all)
        """
        with self._lock:
            if message_types is None:
                # Remove all subscriptions for this agent
                self._subscriptions = [s for s in self._subscriptions if s.agent_id != agent_id]
                logger.debug(f"Removed all subscriptions for agent {agent_id}")
            else:
                # Remove specific message types
                message_types_set = set(message_types)
                for sub in self._subscriptions:
                    if sub.agent_id == agent_id:
                        sub.message_types -= message_types_set
                        if not sub.message_types:
                            # Remove subscription if no message types left
                            self._subscriptions.remove(sub)
                            logger.debug(f"Removed empty subscription for agent {agent_id}")
    
    def publish(self, message: AgentMessage) -> None:
        """
        Publish a message to all subscribed agents.
        
        Args:
            message: Message to publish
        """
        # Store message in conversation memory
        self._store_message(message)
        
        # Route message to receivers
        if message.receiver:
            # Direct message to specific receiver
            self._route_to_agent(message, message.receiver)
        else:
            # Broadcast to all interested subscribers
            self._broadcast_message(message)
        
        logger.debug(f"Published message {message.message_id} from {message.sender}")
    
    def _route_to_agent(self, message: AgentMessage, agent_id: str) -> bool:
        """
        Route a message to a specific agent.
        
        Args:
            message: Message to route
            agent_id: ID of the agent to route to
            
        Returns:
            bool: True if the message was routed successfully, False otherwise
        """
        with self._lock:
            for sub in self._subscriptions:
                if sub.agent_id == agent_id and message.message_type in sub.message_types:
                    try:
                        sub.callback(message)
                        return True
                    except Exception as e:
                        logger.error(f"Error delivering message to agent {agent_id}: {e}")
                        return False
        
        logger.warning(f"No subscription found for agent {agent_id}, message type {message.message_type}")
        return False
    
    def _broadcast_message(self, message: AgentMessage) -> None:
        """
        Broadcast a message to all interested subscribers.
        
        Args:
            message: Message to broadcast
        """
        with self._lock:
            for sub in self._subscriptions:
                if message.message_type in sub.message_types and sub.agent_id != message.sender:
                    try:
                        sub.callback(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting message to agent {sub.agent_id}: {e}")
    
    def _store_message(self, message: AgentMessage) -> None:
        """
        Store a message in conversation memory.
        
        Args:
            message: Message to store
        """
        with self._lock:
            conversation_id = message.conversation_id
            
            if conversation_id not in self._conversations:
                # Create new conversation memory
                self._conversations[conversation_id] = ConversationMemory(conversation_id=conversation_id)
            
            # Add message to conversation
            self._conversations[conversation_id].add_message(message)
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationMemory]:
        """
        Get the conversation memory for a specific conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            ConversationMemory or None: The conversation memory if found
        """
        with self._lock:
            return self._conversations.get(conversation_id)
    
    def get_message(self, message_id: str) -> Optional[AgentMessage]:
        """
        Get a message by its ID.
        
        Args:
            message_id: ID of the message
            
        Returns:
            AgentMessage or None: The message if found
        """
        with self._lock:
            for conversation in self._conversations.values():
                message = conversation.get_message_by_id(message_id)
                if message:
                    return message
            return None
    
    def get_message_chain(self, message_id: str, include_parents: bool = True, include_children: bool = True) -> List[AgentMessage]:
        """
        Get a chain of messages related to the specified message, including parents and/or children.
        
        This method builds a comprehensive message chain that can include both the ancestry
        (parent messages that led to this message) and descendants (replies to this message).
        
        Args:
            message_id: ID of the central message to build the chain around
            include_parents: Whether to include parent messages in the chain
            include_children: Whether to include child messages in the chain
            
        Returns:
            List[AgentMessage]: Chain of messages in chronological order
        """
        with self._lock:
            # First, find which conversation this message belongs to
            message = self.get_message(message_id)
            if not message:
                logger.warning(f"Cannot find message with ID {message_id}")
                return []
            
            conversation = self.get_conversation(message.conversation_id)
            if not conversation:
                logger.warning(f"Cannot find conversation with ID {message.conversation_id}")
                return []
            
            # Get the complete message chain
            return conversation.get_message_chain(
                message_id, 
                include_parents=include_parents,
                include_children=include_children
            )
    
    def clear_conversations(self) -> None:
        """Clear all stored conversations."""
        with self._lock:
            self._conversations.clear()
            logger.debug("Cleared all conversations")
    
    def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear a specific conversation.
        
        Args:
            conversation_id: ID of the conversation to clear
        """
        with self._lock:
            if conversation_id in self._conversations:
                del self._conversations[conversation_id]
                logger.debug(f"Cleared conversation {conversation_id}")
    
    def cleanup_old_conversations(self, max_conversations: int = 100, max_age_seconds: Optional[float] = None) -> int:
        """
        Clean up old conversations to prevent memory leaks.
        
        This method removes the oldest conversations when the total number exceeds
        the specified maximum, or removes conversations older than the specified age.
        
        Args:
            max_conversations: Maximum number of conversations to keep
            max_age_seconds: Maximum age of conversations to keep (in seconds)
            
        Returns:
            int: Number of conversations removed
        """
        with self._lock:
            removed_count = 0
            
            # If we have more than the maximum number of conversations, remove the oldest ones
            if max_conversations is not None and len(self._conversations) > max_conversations:
                # Sort conversations by timestamp of the latest message
                sorted_conversations = sorted(
                    self._conversations.items(),
                    key=lambda x: max(msg.timestamp for msg in x[1].messages) if x[1].messages else 0
                )
                
                # Remove the oldest conversations
                for conv_id, _ in sorted_conversations[:-max_conversations]:
                    del self._conversations[conv_id]
                    removed_count += 1
                    logger.debug(f"Removed old conversation {conv_id} during cleanup")
            
            # If a maximum age is specified, remove conversations older than that
            if max_age_seconds is not None:
                current_time = time.time()
                old_conversations = []
                
                for conv_id, conv in self._conversations.items():
                    if not conv.messages:
                        old_conversations.append(conv_id)
                        continue
                    
                    # Find the timestamp of the most recent message
                    latest_timestamp = max(msg.timestamp for msg in conv.messages)
                    if current_time - latest_timestamp > max_age_seconds:
                        old_conversations.append(conv_id)
                
                for conv_id in old_conversations:
                    del self._conversations[conv_id]
                    removed_count += 1
                    logger.debug(f"Removed expired conversation {conv_id} during cleanup")
            
            return removed_count
    
    def register_handler(self, 
                         handler_id: str, 
                         message_type: MessageType, 
                         callback: Callable[[AgentMessage], None]) -> None:
        """
        Register a handler for a specific message type.
        
        This is a compatibility method specifically designed for the OrchestratorAgent
        and other components that expect a register_handler interface. It provides a
        direct mapping to the more flexible subscribe method but with a simplified
        interface focused on a single message type.
        
        Args:
            handler_id: ID of the handler (agent) that will receive messages
            message_type: Specific type of message this handler wants to receive
            callback: Function to call when a matching message is received;
                     will be passed the AgentMessage object
                     
        Note:
            This method internally translates to a call to subscribe() with a single
            message type. For registering multiple message types at once, use the
            subscribe() method directly with a list of message types.
        """
        logger.info(f"Registering handler '{handler_id}' for message type '{message_type}'")
        
        # Map to subscribe with a single message type
        self.subscribe(
            agent_id=handler_id,
            callback=callback,
            message_types=[message_type]
        )
        
        logger.debug(f"Handler registration complete: {handler_id} → {message_type}")
