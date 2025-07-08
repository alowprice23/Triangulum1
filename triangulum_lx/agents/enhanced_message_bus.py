"""
Enhanced Message Bus - Advanced message routing and handling for agent communication.

This module extends the basic MessageBus with advanced features including:
- Message filtering by topic, priority, and source
- Reliable broadcast capabilities with delivery confirmation
- Integration with thought chains for context preservation
- Error handling for malformed messages
- Performance metrics tracking
- Circuit breaker pattern for failure isolation
- Timeout handling for long-running operations
"""

import logging
import threading
import time
import queue
import uuid
import json
import zlib
import base64
import traceback
from typing import Dict, List, Any, Optional, Union, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError

from triangulum_lx.agents.message import (
    AgentMessage, ConversationMemory, MessageType, ConfidenceLevel,
    DEFAULT_MAX_MESSAGE_SIZE, MAX_CHUNK_SIZE
)
from triangulum_lx.agents.thought_chain_manager import ThoughtChainManager
from triangulum_lx.agents.thought_chain import ThoughtChain

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Priority levels for message delivery."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class CircuitState(Enum):
    """State of a circuit breaker."""
    CLOSED = auto()    # Normal operation, messages flow through
    OPEN = auto()      # Failure detected, messages blocked
    HALF_OPEN = auto() # Testing if system has recovered


@dataclass
class DeliveryStatus:
    """Status of a message delivery attempt."""
    success: bool
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class EnhancedSubscriptionInfo:
    """Enhanced information about a message subscription."""
    agent_id: str
    message_types: Set[MessageType]
    callback: Callable[[AgentMessage], None]
    priority: MessagePriority = MessagePriority.NORMAL
    filters: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None
    max_retries: int = 3
    circuit_breaker: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for the message bus."""
    total_messages: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    retried_deliveries: int = 0
    average_delivery_time: float = 0.0
    max_delivery_time: float = 0.0
    message_type_counts: Dict[str, int] = field(default_factory=dict)
    agent_message_counts: Dict[str, int] = field(default_factory=dict)
    circuit_breaker_trips: int = 0
    timeouts: int = 0
    
    def update_delivery_time(self, delivery_time: float) -> None:
        """Update the average and max delivery time."""
        if self.total_messages == 0:
            self.average_delivery_time = delivery_time
        else:
            self.average_delivery_time = (
                (self.average_delivery_time * self.total_messages + delivery_time) / 
                (self.total_messages + 1)
            )
        
        self.max_delivery_time = max(self.max_delivery_time, delivery_time)
    
    def increment_message_type(self, message_type: MessageType) -> None:
        """Increment the count for a message type."""
        type_name = message_type.value
        self.message_type_counts[type_name] = self.message_type_counts.get(type_name, 0) + 1
    
    def increment_agent_count(self, agent_id: str) -> None:
        """Increment the count for an agent."""
        self.agent_message_counts[agent_id] = self.agent_message_counts.get(agent_id, 0) + 1


class CircuitBreaker:
    """
    Circuit breaker for failure isolation.
    
    This class implements the circuit breaker pattern to prevent cascading failures
    by stopping message delivery to agents that are consistently failing.
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 reset_timeout: float = 60.0,
                 half_open_max_calls: int = 3):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening the circuit
            reset_timeout: Time in seconds before attempting to reset the circuit
            half_open_max_calls: Maximum number of calls to allow in half-open state
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0
        self.lock = threading.RLock()
    
    def record_success(self) -> None:
        """Record a successful call."""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls >= self.half_open_max_calls:
                    # Reset the circuit after successful test calls
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.half_open_calls = 0
                    logger.info("Circuit breaker reset to CLOSED state after successful test calls")
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed call."""
        with self.lock:
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens the circuit again
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker opened again after failure in HALF_OPEN state")
            elif self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    # Too many failures, open the circuit
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker opened after {self.failure_count} consecutive failures")
    
    def allow_request(self) -> bool:
        """
        Check if a request should be allowed.
        
        Returns:
            bool: True if the request should be allowed, False otherwise
        """
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check if enough time has passed to try again
                if time.time() - self.last_failure_time > self.reset_timeout:
                    # Move to half-open state to test if system has recovered
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker moved to HALF_OPEN state to test recovery")
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                return self.half_open_calls < self.half_open_max_calls
            
            return False


class MessageDeduplicator:
    """
    Message deduplicator to prevent processing duplicate messages.
    
    This class maintains a cache of recently processed message IDs to
    prevent the same message from being processed multiple times.
    """
    
    def __init__(self, cache_size: int = 1000, expiration_time: float = 300.0):
        """
        Initialize the message deduplicator.
        
        Args:
            cache_size: Maximum number of message IDs to cache
            expiration_time: Time in seconds before a message ID expires from the cache
        """
        self.cache_size = cache_size
        self.expiration_time = expiration_time
        self.message_cache: Dict[str, float] = {}
        self.lock = threading.RLock()
    
    def is_duplicate(self, message_id: str) -> bool:
        """
        Check if a message is a duplicate.
        
        Args:
            message_id: ID of the message to check
            
        Returns:
            bool: True if the message is a duplicate, False otherwise
        """
        with self.lock:
            # Clean expired entries
            self._clean_expired()
            
            # Check if message ID is in cache
            return message_id in self.message_cache
    
    def mark_processed(self, message_id: str) -> None:
        """
        Mark a message as processed.
        
        Args:
            message_id: ID of the message to mark
        """
        with self.lock:
            # Clean expired entries if cache is full
            if len(self.message_cache) >= self.cache_size:
                self._clean_expired()
                
                # If still full, remove oldest entry
                if len(self.message_cache) >= self.cache_size:
                    oldest_id = min(self.message_cache, key=self.message_cache.get)
                    del self.message_cache[oldest_id]
            
            # Add message ID to cache
            self.message_cache[message_id] = time.time()
    
    def _clean_expired(self) -> None:
        """Clean expired entries from the cache."""
        current_time = time.time()
        expired_ids = [
            msg_id for msg_id, timestamp in self.message_cache.items()
            if current_time - timestamp > self.expiration_time
        ]
        
        for msg_id in expired_ids:
            del self.message_cache[msg_id]


class EnhancedMessageBus:
    """
    Enhanced message routing system for agent communication.
    
    This class extends the basic MessageBus with advanced features including
    message filtering, reliable broadcast, thought chain integration, error
    handling, and performance metrics tracking.
    """
    
    def __init__(self, thought_chain_manager: Optional[ThoughtChainManager] = None):
        """
        Initialize the enhanced message bus.
        
        Args:
            thought_chain_manager: ThoughtChainManager for thought chain integration
        """
        self._subscriptions: List[EnhancedSubscriptionInfo] = []
        self._conversations: Dict[str, ConversationMemory] = {}
        self._delivery_status: Dict[str, Dict[str, DeliveryStatus]] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._message_deduplicator = MessageDeduplicator()
        self._performance_metrics = PerformanceMetrics()
        self._thought_chain_manager = thought_chain_manager
        self._thought_chains: Dict[str, ThoughtChain] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._futures: Dict[str, Future] = {}
    
    def subscribe(self, 
                  agent_id: str, 
                  callback: Callable[[AgentMessage], None],
                  message_types: Optional[List[MessageType]] = None,
                  priority: MessagePriority = MessagePriority.NORMAL,
                  filters: Optional[Dict[str, Any]] = None,
                  timeout: Optional[float] = None,
                  max_retries: int = 3) -> None:
        """
        Subscribe an agent to receive messages.
        
        Args:
            agent_id: ID of the subscribing agent
            callback: Function to call when a message is received
            message_types: Types of messages to subscribe to (None for all)
            priority: Priority level for message delivery
            filters: Filters to apply to messages (e.g., by topic, source)
            timeout: Timeout in seconds for message delivery
            max_retries: Maximum number of delivery retries
        """
        with self._lock:
            message_types_set = set(message_types) if message_types else set(MessageType)
            
            # Check if subscription already exists
            for sub in self._subscriptions:
                if sub.agent_id == agent_id:
                    # Update existing subscription
                    sub.message_types.update(message_types_set)
                    sub.callback = callback
                    sub.priority = priority
                    if filters:
                        sub.filters.update(filters)
                    sub.timeout = timeout
                    sub.max_retries = max_retries
                    logger.debug(f"Updated subscription for agent {agent_id}")
                    return
            
            # Create circuit breaker for this agent if it doesn't exist
            if agent_id not in self._circuit_breakers:
                self._circuit_breakers[agent_id] = CircuitBreaker()
            
            # Add new subscription
            self._subscriptions.append(
                EnhancedSubscriptionInfo(
                    agent_id=agent_id,
                    message_types=message_types_set,
                    callback=callback,
                    priority=priority,
                    filters=filters or {},
                    timeout=timeout,
                    max_retries=max_retries,
                    circuit_breaker={"agent_id": agent_id}
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
    
    def publish(self, 
                message: AgentMessage, 
                priority: Optional[MessagePriority] = None,
                timeout: Optional[float] = None,
                require_confirmation: bool = False) -> Dict[str, Any]:
        """
        Publish a message to all subscribed agents.
        
        Args:
            message: Message to publish
            priority: Priority level for this message (overrides subscription priority)
            timeout: Timeout in seconds for message delivery (overrides subscription timeout)
            require_confirmation: Whether to require delivery confirmation
            
        Returns:
            Dict[str, Any]: Delivery status information
        """
        # Check for duplicate message
        if self._message_deduplicator.is_duplicate(message.message_id):
            logger.warning(f"Duplicate message detected: {message.message_id}")
            return {"success": False, "error": "Duplicate message", "message_id": message.message_id}
        
        # Mark message as processed to prevent duplicates
        self._message_deduplicator.mark_processed(message.message_id)
        
        # Update performance metrics
        self._performance_metrics.total_messages += 1
        self._performance_metrics.increment_message_type(message.message_type)
        self._performance_metrics.increment_agent_count(message.sender)
        
        # Store message in conversation memory
        self._store_message(message)
        
        # Integrate with thought chains if available
        self._integrate_with_thought_chains(message)
        
        # Handle large messages
        if self._is_large_message(message):
            logger.debug(f"Large message detected: {message.message_id}, size: {len(message.to_json())}")
            chunked_messages = self._chunk_message(message)
            
            # Publish each chunk
            for chunk in chunked_messages:
                self._publish_single_message(
                    chunk, 
                    priority or MessagePriority.NORMAL,
                    timeout,
                    require_confirmation
                )
            
            return {
                "success": True, 
                "chunked": True, 
                "chunks": len(chunked_messages),
                "message_id": message.message_id
            }
        
        # Publish the message
        return self._publish_single_message(
            message, 
            priority or MessagePriority.NORMAL,
            timeout,
            require_confirmation
        )
    
    def _publish_single_message(self,
                               message: AgentMessage,
                               priority: MessagePriority,
                               timeout: Optional[float],
                               require_confirmation: bool) -> Dict[str, Any]:
        """
        Publish a single message to all subscribed agents.
        
        Args:
            message: Message to publish
            priority: Priority level for this message
            timeout: Timeout in seconds for message delivery
            require_confirmation: Whether to require delivery confirmation
            
        Returns:
            Dict[str, Any]: Delivery status information
        """
        # Route message to receivers
        if message.receiver:
            # Direct message to specific receiver
            result = self._route_to_agent(
                message, 
                message.receiver, 
                priority,
                timeout,
                require_confirmation
            )
            
            return {
                "success": result["success"],
                "message_id": message.message_id,
                "receiver": message.receiver,
                "delivery_status": result
            }
        else:
            # Broadcast to all interested subscribers
            results = self._broadcast_message(
                message, 
                priority,
                timeout,
                require_confirmation
            )
            
            # Check if any deliveries were successful
            any_success = any(r["success"] for r in results.values())
            
            return {
                "success": any_success,
                "message_id": message.message_id,
                "delivery_status": results
            }
    
    def _route_to_agent(self, 
                       message: AgentMessage, 
                       agent_id: str,
                       priority: MessagePriority,
                       timeout: Optional[float],
                       require_confirmation: bool) -> Dict[str, Any]:
        """
        Route a message to a specific agent.
        
        Args:
            message: Message to route
            agent_id: ID of the agent to route to
            priority: Priority level for this message
            timeout: Timeout in seconds for message delivery
            require_confirmation: Whether to require delivery confirmation
            
        Returns:
            Dict[str, Any]: Delivery status information
        """
        with self._lock:
            # Find matching subscription
            matching_subs = []
            for sub in self._subscriptions:
                if sub.agent_id == agent_id and message.message_type in sub.message_types:
                    # Check if message passes filters
                    if self._passes_filters(message, sub.filters):
                        matching_subs.append(sub)
            
            if not matching_subs:
                logger.warning(f"No subscription found for agent {agent_id}, message type {message.message_type}")
                return {"success": False, "error": "No matching subscription"}
            
            # Sort by priority (highest first)
            matching_subs.sort(key=lambda s: s.priority.value, reverse=True)
            
            # Use the highest priority subscription
            sub = matching_subs[0]
            
            # Check circuit breaker
            circuit_breaker = self._circuit_breakers.get(agent_id)
            if circuit_breaker and not circuit_breaker.allow_request():
                logger.warning(f"Circuit breaker open for agent {agent_id}, message delivery blocked")
                self._performance_metrics.circuit_breaker_trips += 1
                return {"success": False, "error": "Circuit breaker open"}
            
            # Use the specified timeout or the subscription timeout
            effective_timeout = timeout or sub.timeout
            
            # Deliver the message
            delivery_status = self._deliver_message(
                message, 
                sub, 
                effective_timeout,
                require_confirmation
            )
            
            # Update delivery status
            self._update_delivery_status(message.message_id, agent_id, delivery_status)
            
            # Update circuit breaker
            if delivery_status["success"]:
                if circuit_breaker:
                    circuit_breaker.record_success()
            else:
                if circuit_breaker:
                    circuit_breaker.record_failure()
            
            return delivery_status
    
    def _broadcast_message(self, 
                          message: AgentMessage,
                          priority: MessagePriority,
                          timeout: Optional[float],
                          require_confirmation: bool) -> Dict[str, Dict[str, Any]]:
        """
        Broadcast a message to all interested subscribers.
        
        Args:
            message: Message to broadcast
            priority: Priority level for this message
            timeout: Timeout in seconds for message delivery
            require_confirmation: Whether to require delivery confirmation
            
        Returns:
            Dict[str, Dict[str, Any]]: Delivery status information for each receiver
        """
        with self._lock:
            # Find all matching subscriptions
            matching_subs = []
            for sub in self._subscriptions:
                if (message.message_type in sub.message_types and 
                    sub.agent_id != message.sender and
                    self._passes_filters(message, sub.filters)):
                    matching_subs.append(sub)
            
            # Sort by priority (highest first)
            matching_subs.sort(key=lambda s: s.priority.value, reverse=True)
            
            # Group by agent ID to avoid duplicate deliveries
            agent_subs = {}
            for sub in matching_subs:
                if sub.agent_id not in agent_subs:
                    agent_subs[sub.agent_id] = sub
            
            # Deliver to each agent
            results = {}
            for agent_id, sub in agent_subs.items():
                # Check circuit breaker
                circuit_breaker = self._circuit_breakers.get(agent_id)
                if circuit_breaker and not circuit_breaker.allow_request():
                    logger.warning(f"Circuit breaker open for agent {agent_id}, message delivery blocked")
                    self._performance_metrics.circuit_breaker_trips += 1
                    results[agent_id] = {"success": False, "error": "Circuit breaker open"}
                    continue
                
                # Use the specified timeout or the subscription timeout
                effective_timeout = timeout or sub.timeout
                
                # Deliver the message
                delivery_status = self._deliver_message(
                    message, 
                    sub, 
                    effective_timeout,
                    require_confirmation
                )
                
                # Update delivery status
                self._update_delivery_status(message.message_id, agent_id, delivery_status)
                
                # Update circuit breaker
                if delivery_status["success"]:
                    if circuit_breaker:
                        circuit_breaker.record_success()
                else:
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                
                results[agent_id] = delivery_status
            
            return results
    
    def _deliver_message(self, 
                        message: AgentMessage, 
                        subscription: EnhancedSubscriptionInfo,
                        timeout: Optional[float],
                        require_confirmation: bool) -> Dict[str, Any]:
        """
        Deliver a message to a subscriber.
        
        Args:
            message: Message to deliver
            subscription: Subscription information
            timeout: Timeout in seconds for message delivery
            require_confirmation: Whether to require delivery confirmation
            
        Returns:
            Dict[str, Any]: Delivery status information
        """
        agent_id = subscription.agent_id
        callback = subscription.callback
        max_retries = subscription.max_retries
        
        # Initialize delivery status
        delivery_status = {
            "success": False,
            "agent_id": agent_id,
            "message_id": message.message_id,
            "timestamp": time.time(),
            "retry_count": 0
        }
        
        # Attempt delivery with retries
        for retry in range(max_retries + 1):
            if retry > 0:
                delivery_status["retry_count"] = retry
                logger.debug(f"Retrying delivery to {agent_id}, attempt {retry}/{max_retries}")
                self._performance_metrics.retried_deliveries += 1
            
            try:
                start_time = time.time()
                
                if timeout:
                    # Use a future for timeout handling
                    future = self._executor.submit(callback, message)
                    
                    try:
                        # Wait for the callback to complete with timeout
                        future.result(timeout=timeout)
                        delivery_time = time.time() - start_time
                        
                        # Update performance metrics
                        self._performance_metrics.update_delivery_time(delivery_time)
                        self._performance_metrics.successful_deliveries += 1
                        
                        # Mark as successful
                        delivery_status["success"] = True
                        delivery_status["delivery_time"] = delivery_time
                        
                        # Exit retry loop on success
                        break
                    
                    except TimeoutError:
                        # Timeout occurred
                        logger.warning(f"Timeout delivering message to {agent_id}")
                        self._performance_metrics.timeouts += 1
                        delivery_status["error"] = "Timeout"
                        
                        # Cancel the future if possible
                        future.cancel()
                    
                    except Exception as e:
                        # Callback raised an exception
                        logger.error(f"Error delivering message to {agent_id}: {e}")
                        delivery_status["error"] = str(e)
                        self._performance_metrics.failed_deliveries += 1
                
                else:
                    # No timeout, call directly
                    callback(message)
                    delivery_time = time.time() - start_time
                    
                    # Update performance metrics
                    self._performance_metrics.update_delivery_time(delivery_time)
                    self._performance_metrics.successful_deliveries += 1
                    
                    # Mark as successful
                    delivery_status["success"] = True
                    delivery_status["delivery_time"] = delivery_time
                    
                    # Exit retry loop on success
                    break
            
            except Exception as e:
                # Callback raised an exception
                logger.error(f"Error delivering message to {agent_id}: {e}")
                delivery_status["error"] = str(e)
                self._performance_metrics.failed_deliveries += 1
        
        # If delivery failed after all retries
        if not delivery_status["success"]:
            logger.warning(f"Failed to deliver message to {agent_id} after {max_retries} retries")
        
        return delivery_status
    
    def _update_delivery_status(self, message_id: str, agent_id: str, status: Dict[str, Any]) -> None:
        """
        Update the delivery status for a message.
        
        Args:
            message_id: ID of the message
            agent_id: ID of the agent
            status: Delivery status information
        """
        with self._lock:
            if message_id not in self._delivery_status:
                self._delivery_status[message_id] = {}
            
            self._delivery_status[message_id][agent_id] = DeliveryStatus(
                success=status["success"],
                timestamp=status.get("timestamp", time.time()),
                error=status.get("error"),
                retry_count=status.get("retry_count", 0)
            )
    
    def _passes_filters(self, message: AgentMessage, filters: Dict[str, Any]) -> bool:
        """
        Check if a message passes the specified filters.
        
        Args:
            message: Message to check
            filters: Filters to apply
            
        Returns:
            bool: True if the message passes all filters, False otherwise
        """
        # Check topic filter
        if "topic" in filters and "topic" in message.metadata:
            if message.metadata["topic"] != filters["topic"]:
                return False
        
        # Check source filter
        if "source" in filters and message.sender != filters["source"]:
            return False
        
        # Check confidence filter
        if "min_confidence" in filters and message.confidence is not None:
            if message.confidence < filters["min_confidence"]:
                return False
        
        # Check content filter (simple key existence check)
        if "content_keys" in filters:
            required_keys = filters["content_keys"]
            if not all(key in message.content for key in required_keys):
                return False
        
        # All filters passed
        return True
    
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
    
    def _integrate_with_thought_chains(self, message: AgentMessage) -> None:
        """
        Integrate a message with thought chains.
        
        This method adds the message to the appropriate thought chain if available,
        or creates a new thought chain if needed.
        
        Args:
            message: Message to integrate
        """
        if not self._thought_chain_manager:
            return
        
        conversation_id = message.conversation_id
        
        # Check if we have a thought chain for this conversation
        if conversation_id not in self._thought_chains:
            # Create a new thought chain
            chain = self._thought_chain_manager.create_chain(
                name=f"Conversation {conversation_id}",
                metadata={"conversation_id": conversation_id}
            )
            self._thought_chains[conversation_id] = chain
        
        # Get the thought chain
        chain = self._thought_chains[conversation_id]
        
        # Add the message to the thought chain
        chain.add_thought(
            content=message.to_dict(),
            thought_type="message",
            metadata={
                "message_id": message.message_id,
                "message_type": message.message_type.value,
                "sender": message.sender,
                "receiver": message.receiver,
                "timestamp": message.timestamp
            }
        )
    
    def _is_large_message(self, message: AgentMessage) -> bool:
        """
        Check if a message is too large for a single delivery.
        
        Args:
            message: Message to check
            
        Returns:
            bool: True if the message is too large, False otherwise
        """
        # Convert to JSON to get actual size
        message_json = message.to_json()
        return len(message_json) > DEFAULT_MAX_MESSAGE_SIZE
    
    def _chunk_message(self, message: AgentMessage) -> List[AgentMessage]:
        """
        Split a large message into chunks.
        
        Args:
            message: Message to split
            
        Returns:
            List[AgentMessage]: List of chunked messages
        """
        # Convert to JSON
        message_json = message.to_json()
        
        # Compress the content if it's very large
        compressed = False
        if len(message_json) > 10 * 1024 * 1024:  # 10MB
            compressed = True
            message_json = zlib.compress(message_json.encode('utf-8'))
            message_json = base64.b64encode(message_json).decode('utf-8')
        
        # Calculate number of chunks needed
        chunk_size = MAX_CHUNK_SIZE
        total_size = len(message_json)
        total_chunks = (total_size + chunk_size - 1) // chunk_size  # Ceiling division
        
        # Generate a response ID for this chunked message
        response_id = str(uuid.uuid4())
        
        # Split the content into chunks
        chunks = []
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, total_size)
            chunk_content = message_json[start:end]
            
            # Create a chunked message
            chunk = AgentMessage.create_chunked_message(
                chunk_sequence=i,
                total_chunks=total_chunks,
                response_id=response_id,
                content={
                    "chunk_data": chunk_content,
                    "original_type": message.message_type.value,
                    "chunk_info": {
                        "index": i,
                        "total": total_chunks,
                        "size": end - start,
                        "compressed": compressed
                    }
                },
                sender=message.sender,
                receiver=message.receiver,
                parent_id=message.parent_id,
                conversation_id=message.conversation_id,
                compressed=compressed,
                metadata=message.metadata.copy()
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def reassemble_chunked_message(self, chunks: List[AgentMessage]) -> Optional[AgentMessage]:
        """
        Reassemble a message from chunks.
        
        Args:
            chunks: List of chunked messages
            
        Returns:
            AgentMessage or None: Reassembled message or None if incomplete
        """
        if not chunks:
            return None
        
        # Sort chunks by sequence number
        chunks.sort(key=lambda c: c.chunk_sequence)
        
        # Check if we have all chunks
        if len(chunks) != chunks[0].total_chunks:
            logger.warning(f"Incomplete chunked message: {len(chunks)}/{chunks[0].total_chunks} chunks")
            return None
        
        # Reassemble the content
        content = ""
        for chunk in chunks:
            content += chunk.content.get("chunk_data", "")
        
        # Decompress if necessary
        compressed = chunks[0].compressed
        if compressed:
            try:
                content = base64.b64decode(content)
                content = zlib.decompress(content).decode('utf-8')
            except Exception as e:
                logger.error(f"Error decompressing chunked message: {e}")
                return None
        
        # Parse the JSON content
        try:
            message_data = json.loads(content)
            
            # Create a new message from the data
            return AgentMessage.from_dict(message_data)
        except Exception as e:
            logger.error(f"Error parsing reassembled message: {e}")
            return None
    
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
    
    def get_delivery_status(self, message_id: str) -> Dict[str, DeliveryStatus]:
        """
        Get the delivery status for a message.
        
        Args:
            message_id: ID of the message
            
        Returns:
            Dict[str, DeliveryStatus]: Delivery status for each receiver
        """
        with self._lock:
            return self._delivery_status.get(message_id, {}).copy()
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """
        Get performance metrics for the message bus.
        
        Returns:
            PerformanceMetrics: Copy of the current performance metrics
        """
        with self._lock:
            # Return a copy to avoid modification
            return PerformanceMetrics(
                total_messages=self._performance_metrics.total_messages,
                successful_deliveries=self._performance_metrics.successful_deliveries,
                failed_deliveries=self._performance_metrics.failed_deliveries,
                retried_deliveries=self._performance_metrics.retried_deliveries,
                average_delivery_time=self._performance_metrics.average_delivery_time,
                max_delivery_time=self._performance_metrics.max_delivery_time,
                message_type_counts=self._performance_metrics.message_type_counts.copy(),
                agent_message_counts=self._performance_metrics.agent_message_counts.copy(),
                circuit_breaker_trips=self._performance_metrics.circuit_breaker_trips,
                timeouts=self._performance_metrics.timeouts
            )
    
    def reset_performance_metrics(self) -> None:
        """Reset performance metrics."""
        with self._lock:
            self._performance_metrics = PerformanceMetrics()
    
    def get_thought_chain(self, conversation_id: str) -> Optional[ThoughtChain]:
        """
        Get the thought chain for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            ThoughtChain or None: The thought chain if found
        """
        with self._lock:
            return self._thought_chains.get(conversation_id)
    
    def register_handler(self, 
                         handler_id: str, 
                         message_type: MessageType, 
                         callback: Callable[[AgentMessage], None]) -> None:
        """
        Register a handler for a specific message type.
        
        This is a compatibility method for the OrchestratorAgent.
        It maps to the subscribe method with a specific message type.
        
        Args:
            handler_id: ID of the handler (agent)
            message_type: Type of message to handle
            callback: Function to call when a message is received
        """
        # Simply map to subscribe with a single message type
        self.subscribe(
            agent_id=handler_id,
            callback=callback,
            message_types=[message_type]
        )
        logger.debug(f"Registered handler {handler_id} for message type {message_type}")
    
    def shutdown(self) -> None:
        """Shutdown the message bus and release resources."""
        with self._lock:
            # Shutdown the executor
            self._executor.shutdown(wait=True)
            
            # Clear all subscriptions
            self._subscriptions.clear()
            
            # Clear all conversations
            self._conversations.clear()
            
            # Clear all delivery status
            self._delivery_status.clear()
            
            # Clear all circuit breakers
            self._circuit_breakers.clear()
            
            # Clear all thought chains
            self._thought_chains.clear()
            
            logger.info("Message bus shutdown complete")
