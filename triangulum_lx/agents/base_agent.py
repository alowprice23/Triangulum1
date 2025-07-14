"""
Base Agent - Abstract base class for all specialized agents in the Triangulum system.

This module defines the BaseAgent class which serves as the foundation for
all specialized agents in the Triangulum system, providing a common interface
for agent interaction and message handling.
"""

import abc
import logging
import uuid
import time
from typing import Dict, List, Any, Optional, Set, Callable, Tuple, Generator, Union

from triangulum_lx.agents.message import AgentMessage, MessageType, ConfidenceLevel
# from triangulum_lx.agents.message_bus import MessageBus # Old
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus # New
from triangulum_lx.core.monitor import OperationProgress
from triangulum_lx.agents.response_handling import (
    LargeResponseHandler,
    ResponseChunker,
    ResponseSerializer,
    ResponseCompressor
)

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    """
    Abstract base class for all specialized agents in the Triangulum system.

    BaseAgent provides a common interface for all specialized agents, including
    message handling, agent identification, and lifecycle management. Each specialized
    agent in the system should inherit from this class and implement its abstract methods.
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_type: str = "base",
        message_bus: Optional[EnhancedMessageBus] = None, # Changed MessageBus to EnhancedMessageBus
        subscribed_message_types: Optional[List[MessageType]] = None,
        config: Optional[Dict[str, Any]] = None,
        engine_monitor=None, # Monitor for OperationProgress
        metrics_collector=None # Added for metrics collection
    ):
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            agent_type: Type of the agent (e.g., "relationship_analyst", "bug_identifier")
            message_bus: Enhanced message bus for agent communication
            subscribed_message_types: Types of messages this agent subscribes to
            config: Agent configuration dictionary
            engine_monitor: Optional monitor for tracking operations
            metrics_collector: Optional MetricsCollector instance
        """
        self.agent_id = agent_id or f"{agent_type}_{str(uuid.uuid4())[:8]}"
        self.agent_type = agent_type
        self.message_bus = message_bus
        self.config = config or {}
        self._is_initialized = False
        self._subscribed_message_types = subscribed_message_types or []
        self._engine_monitor = engine_monitor
        self.metrics = metrics_collector # Store metrics collector
        self._active_operations = {}  # operation_id -> (start_time, timeout_seconds)
        self._operation_details = {}  # operation_id -> additional details
        
        # Initialize response handling
        self._response_handler = LargeResponseHandler()
        self._pending_large_responses = {}  # response_id -> list of chunks
        
        # Register with message bus if provided
        if self.message_bus:
            self._register_with_message_bus()
            
    def _register_with_message_bus(self) -> None:
        """Register the agent with the message bus."""
        if not self.message_bus:
            logger.warning(f"Agent {self.agent_id}: No message bus available for registration")
            return
            
        self.message_bus.subscribe(
            agent_id=self.agent_id,
            callback=self.handle_message,
            message_types=self._subscribed_message_types if self._subscribed_message_types else None
        )
        logger.debug(f"Agent {self.agent_id} registered with message bus")
        
    async def handle_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """
        Handle an incoming message.

        This method dispatches the message to the appropriate handler based on its type.

        Args:
            message: The message to handle
        """
        logger.debug(f"Agent {self.agent_id} handling message: {message.message_type} from {message.sender}")
        
        # Handle chunked messages specially
        if message.message_type == MessageType.CHUNKED_MESSAGE:
            return await self._handle_chunked_message(message)
        elif message.message_type == MessageType.STREAM_START:
            return await self._handle_stream_start(message)
        elif message.message_type == MessageType.STREAM_END:
            return await self._handle_stream_end(message)
        # Dispatch to specific handler based on message type
        elif message.message_type == MessageType.TASK_REQUEST:
            return await self._handle_task_request(message)
        elif message.message_type == MessageType.QUERY:
            return await self._handle_query(message)
        elif message.message_type == MessageType.ERROR:
            return await self._handle_error(message)
        elif message.message_type == MessageType.STATUS:
            return await self._handle_status(message)
        else:
            return await self._handle_other_message(message)
    
    async def send_message(
        self,
        message_type: MessageType,
        content: Dict[str, Any],
        receiver: Optional[str] = None,
        confidence: Optional[float] = None,
        parent_message_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        large_content_handling: str = "auto"  # "auto", "direct", "chunked", "stream"
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message via the message bus.

        Args:
            message_type: Type of message to send
            content: Message content
            receiver: Message recipient (optional)
            confidence: Confidence level (optional)
            parent_message_id: ID of the parent message (optional)
            conversation_id: ID of the conversation (optional)
            metadata: Additional message metadata (optional)
            large_content_handling: How to handle large content:
                "auto": Automatically determine the best method
                "direct": Send as a single message, regardless of size
                "chunked": Split into chunks if needed
                "stream": Stream the content as chunks

        Returns:
            The response content if the message was sent successfully, otherwise None.
        """
        if not self.message_bus:
            logger.warning(f"Agent {self.agent_id}: No message bus available, message not sent")
            return None
        
        # Determine if content is large
        serialized = ResponseSerializer.serialize(content)
        is_large = len(serialized) > 1024 * 1024  # Consider anything over 1MB to be large
        
        # Handle based on size and specified method
        if is_large and large_content_handling != "direct":
            # Determine method if auto
            if large_content_handling == "auto":
                large_content_handling = "chunked"  # Default to chunked for auto
            
            if large_content_handling == "chunked":
                # Prepare chunked response
                return await self._send_chunked_message(
                    message_type=message_type,
                    content=content,
                    receiver=receiver,
                    confidence=confidence,
                    parent_message_id=parent_message_id,
                    conversation_id=conversation_id,
                    metadata=metadata
                )
            elif large_content_handling == "stream":
                # Stream the response
                return await self._send_streamed_message(
                    message_type=message_type,
                    content=content,
                    receiver=receiver,
                    confidence=confidence,
                    parent_message_id=parent_message_id,
                    conversation_id=conversation_id,
                    metadata=metadata
                )
        
        # Default case: send as a single message
        message = AgentMessage(
            message_type=message_type,
            content=content,
            sender=self.agent_id,
            receiver=receiver,
            parent_id=parent_message_id,
            conversation_id=conversation_id,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        response = await self.message_bus.publish(message)
        return response
    
    async def send_response(
        self,
        original_message: AgentMessage,
        message_type: MessageType,
        content: Dict[str, Any],
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        large_content_handling: str = "auto"  # "auto", "direct", "chunked", "stream"
    ) -> Optional[Dict[str, Any]]:
        """
        Send a response to a specific message.

        Args:
            original_message: The message to respond to
            message_type: Type of response message
            content: Response content
            confidence: Confidence level (optional)
            metadata: Additional message metadata (optional)
            large_content_handling: How to handle large content:
                "auto": Automatically determine the best method
                "direct": Send as a single message, regardless of size
                "chunked": Split into chunks if needed
                "stream": Stream the content as chunks

        Returns:
            The response content if the message was sent successfully, otherwise None.
        """
        return await self.send_message(
            message_type=message_type,
            content=content,
            receiver=original_message.sender,
            confidence=confidence,
            parent_message_id=original_message.message_id,
            conversation_id=original_message.conversation_id,
            metadata=metadata,
            large_content_handling=large_content_handling
        )
    
    def broadcast_status(
        self,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Broadcast a status message to all agents.

        Args:
            status: Status message
            metadata: Additional message metadata (optional)

        Returns:
            The message ID if sent successfully, None otherwise
        """
        return self.send_message(
            message_type=MessageType.STATUS,
            content={"status": status, "agent_type": self.agent_type},
            metadata=metadata,
            large_content_handling="direct"  # Status messages should be direct
        )
    
    def initialize(self) -> bool:
        """
        Initialize the agent.

        Performs any setup needed before the agent can process messages.
        Subclasses should override this method to perform specific initialization.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self._is_initialized = True
        return True
    
    def shutdown(self) -> None:
        """
        Shut down the agent.

        Performs cleanup when the agent is no longer needed.
        Subclasses should override this method to perform specific cleanup.
        """
        # Cancel any active operations
        active_ops = list(self._active_operations.keys())
        for op_id in active_ops:
            self.cancel_operation(op_id, {"reason": "Agent shutdown"})
            
        # Unsubscribe from message bus
        if self.message_bus:
            self.message_bus.unsubscribe(self.agent_id)
    
    def _handle_chunked_message(self, message: AgentMessage) -> None:
        """
        Handle a chunked message.

        Args:
            message: The chunked message
        """
        logger.debug(f"Agent {self.agent_id} received chunked message: {message.chunk_id}")
        
        # Add the chunk to the response handler
        response_data = {
            "response_type": "chunk",
            "response_id": message.response_id,
            "chunk_id": message.chunk_id,
            "sequence": message.chunk_sequence,
            "total": message.total_chunks,
            "data": message.content.get("data", ""),
            "compressed": message.compressed,
            "metadata": message.metadata
        }
        
        is_complete, processed_data = self._response_handler.process_response(response_data)
        
        if is_complete and processed_data:
            # Handle the complete message based on the original message type
            # Use the metadata to determine the original message type
            original_type_str = message.metadata.get("original_type")
            try:
                original_type = MessageType(original_type_str) if original_type_str else MessageType.TASK_RESULT
            except ValueError:
                original_type = MessageType.TASK_RESULT
            
            # Create a new message with the processed data
            reconstructed = AgentMessage(
                message_type=original_type,
                content=processed_data,
                sender=message.sender,
                receiver=message.receiver,
                parent_id=message.parent_id,
                conversation_id=message.conversation_id,
                confidence=message.metadata.get("confidence"),
                metadata=message.metadata
            )
            
            # Handle the reconstructed message
            self.handle_message(reconstructed)
    
    def _handle_stream_start(self, message: AgentMessage) -> None:
        """
        Handle a stream start message.

        Args:
            message: The stream start message
        """
        logger.debug(f"Agent {self.agent_id} received stream start: {message.response_id}")
        
        # Store stream information
        if message.response_id:
            self._pending_large_responses[message.response_id] = {
                "total_chunks": message.content.get("total_chunks", 0),
                "received_chunks": 0,
                "metadata": message.metadata
            }
    
    def _handle_stream_end(self, message: AgentMessage) -> None:
        """
        Handle a stream end message.

        Args:
            message: The stream end message
        """
        logger.debug(f"Agent {self.agent_id} received stream end: {message.response_id}")
        
        # Clean up stream information
        if message.response_id and message.response_id in self._pending_large_responses:
            del self._pending_large_responses[message.response_id]
    
    def _send_chunked_message(
        self,
        message_type: MessageType,
        content: Dict[str, Any],
        receiver: Optional[str] = None,
        confidence: Optional[float] = None,
        parent_message_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Send a large message as multiple chunks.

        Args:
            message_type: Type of message to send
            content: Message content
            receiver: Message recipient (optional)
            confidence: Confidence level (optional)
            parent_message_id: ID of the parent message (optional)
            conversation_id: ID of the conversation (optional)
            metadata: Additional message metadata (optional)

        Returns:
            List of message IDs for the chunks sent
        """
        if not self.message_bus:
            logger.warning(f"Agent {self.agent_id}: No message bus available, chunked message not sent")
            return []
        
        # Store original message type in metadata
        meta = metadata or {}
        meta["original_type"] = message_type.value
        meta["confidence"] = confidence
        
        # Prepare the large response
        response_data = self._response_handler.prepare_large_response(
            content,
            chunk=False  # Get all chunks at once
        )
        
        if response_data.get("response_type") == "chunked":
            # We have a chunked response
            response_id = response_data.get("response_id")
            chunks = response_data.get("chunks", [])
            
            message_ids = []
            for i, chunk_data in enumerate(chunks):
                # Create a chunked message
                chunk_message = AgentMessage.create_chunked_message(
                    chunk_sequence=chunk_data.get("sequence"),
                    total_chunks=chunk_data.get("total"),
                    response_id=response_id,
                    content={"data": chunk_data.get("data")},
                    sender=self.agent_id,
                    receiver=receiver,
                    parent_id=parent_message_id,
                    conversation_id=conversation_id,
                    compressed=chunk_data.get("compressed", False),
                    metadata=meta
                )
                
                # Send the chunked message
                self.message_bus.publish(chunk_message)
                message_ids.append(chunk_message.message_id)
            
            return message_ids
        else:
            # Not chunked, just send directly
            logger.debug(f"Agent {self.agent_id}: Content was not large enough to chunk")
            message = AgentMessage(
                message_type=message_type,
                content=content,
                sender=self.agent_id,
                receiver=receiver,
                parent_id=parent_message_id,
                conversation_id=conversation_id,
                confidence=confidence,
                metadata=meta
            )
            
            self.message_bus.publish(message)
            return [message.message_id]
    
    def _send_streamed_message(
        self,
        message_type: MessageType,
        content: Dict[str, Any],
        receiver: Optional[str] = None,
        confidence: Optional[float] = None,
        parent_message_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Stream a large message as multiple chunks.

        Args:
            message_type: Type of message to send
            content: Message content
            receiver: Message recipient (optional)
            confidence: Confidence level (optional)
            parent_message_id: ID of the parent message (optional)
            conversation_id: ID of the conversation (optional)
            metadata: Additional message metadata (optional)

        Returns:
            List of message IDs for the messages sent
        """
        if not self.message_bus:
            logger.warning(f"Agent {self.agent_id}: No message bus available, streamed message not sent")
            return []
        
        # Store original message type in metadata
        meta = metadata or {}
        meta["original_type"] = message_type.value
        meta["confidence"] = confidence
        
        # Prepare the large response as a generator
        response_gen = self._response_handler.prepare_large_response(
            content,
            chunk=True  # Get a generator of chunks
        )
        
        # Create a unique response ID
        response_id = str(uuid.uuid4())
        
        # Send start message
        start_message = AgentMessage.create_stream_start_message(
            response_id=response_id,
            total_chunks=0,  # We don't know yet
            sender=self.agent_id,
            receiver=receiver,
            parent_id=parent_message_id,
            conversation_id=conversation_id,
            metadata=meta
        )
        
        self.message_bus.publish(start_message)
        message_ids = [start_message.message_id]
        
        # Send chunks
        chunk_count = 0
        try:
            for chunk_data in response_gen:
                chunk_message = AgentMessage.create_chunked_message(
                    chunk_sequence=chunk_data.get("sequence"),
                    total_chunks=chunk_data.get("total"),
                    response_id=response_id,
                    content={"data": chunk_data.get("data")},
                    sender=self.agent_id,
                    receiver=receiver,
                    parent_id=parent_message_id,
                    conversation_id=conversation_id,
                    compressed=chunk_data.get("compressed", False),
                    metadata=meta
                )
                
                self.message_bus.publish(chunk_message)
                message_ids.append(chunk_message.message_id)
                chunk_count += 1
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Error streaming message: {str(e)}")
        
        # Send end message
        end_message = AgentMessage.create_stream_end_message(
            response_id=response_id,
            chunks_sent=chunk_count,
            sender=self.agent_id,
            receiver=receiver,
            parent_id=parent_message_id,
            conversation_id=conversation_id,
            metadata=meta
        )
        
        self.message_bus.publish(end_message)
        message_ids.append(end_message.message_id)
        
        return message_ids
        
    @abc.abstractmethod
    async def _handle_task_request(self, message: AgentMessage) -> None:
        """
        Handle a task request message.

        Args:
            message: The task request message
        """
        pass
    
    @abc.abstractmethod
    async def _handle_query(self, message: AgentMessage) -> None:
        """
        Handle a query message.

        Args:
            message: The query message
        """
        pass
    
    async def _handle_error(self, message: AgentMessage) -> None:
        """
        Handle an error message.

        Args:
            message: The error message
        """
        error_text = message.content.get("error", "Unknown error")
        logger.warning(f"Agent {self.agent_id} received error: {error_text}")
    
    async def _handle_status(self, message: AgentMessage) -> None:
        """
        Handle a status message.

        Args:
            message: The status message
        """
        # Only log the status content, not the message handling itself
        # (which is already logged in the handle_message method)
        status = message.content.get("status", "Unknown status")
        sender_type = message.content.get("agent_type", "unknown")
        logger.debug(f"Agent {self.agent_id} received status from {sender_type} agent: {status}")
    
    async def _handle_other_message(self, message: AgentMessage) -> None:
        """
        Handle any other type of message.

        Args:
            message: The message to handle
        """
        logger.debug(f"Agent {self.agent_id} received unhandled message type: {message.message_type}")

    def send_message_to_user(self, message: str):
        """
        Send a message to the user.

        Args:
            message: The message to send to the user.
        """
        if self.message_bus:
            user_message = AgentMessage(
                message_type=MessageType.LOG,
                content={"message": message},
                sender=self.agent_id,
                receiver="user"
            )
            self.message_bus.publish(user_message)
        
    # Operation tracking methods
    
    def create_operation(
        self, 
        operation_type: str, 
        total_steps: int = 1,
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new operation for tracking.
        
        Args:
            operation_type: Type of operation (e.g., "file_analysis", "bug_detection")
            total_steps: Total number of steps in the operation
            timeout_seconds: Optional timeout in seconds
            details: Optional additional details about the operation
            
        Returns:
            The operation ID
        """
        # Generate a unique operation ID
        operation_id = f"{self.agent_type}_{str(uuid.uuid4())[:8]}"
        
        # Store operation details locally
        self._active_operations[operation_id] = (time.time(), timeout_seconds)
        self._operation_details[operation_id] = details or {}
        
        # If we have an engine monitor, register the operation there too
        if self._engine_monitor:
            # Create a cancel callback that will call our cancel_operation method
            def cancel_callback():
                self.handle_timeout(operation_id)
                
            # Create the operation in the monitor
            self._engine_monitor.create_operation(
                operation_type=operation_type,
                total_steps=total_steps,
                timeout_seconds=timeout_seconds,
                cancel_callback=cancel_callback
            )
            
        logger.debug(f"Agent {self.agent_id} created operation {operation_id} of type {operation_type}")
        return operation_id
    
    def start_operation(self, operation_id: str) -> None:
        """
        Mark an operation as started.
        
        Args:
            operation_id: ID of the operation to start
        """
        if operation_id in self._active_operations:
            # Update the start time
            self._active_operations[operation_id] = (time.time(), self._active_operations[operation_id][1])
            
            # Update in the monitor if available
            if self._engine_monitor:
                self._engine_monitor.start_operation(operation_id)
                
            logger.debug(f"Agent {self.agent_id} started operation {operation_id}")
        else:
            logger.warning(f"Agent {self.agent_id} tried to start unknown operation {operation_id}")
    
    def update_operation_progress(
        self, 
        operation_id: str, 
        current_step: int,
        total_steps: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update the progress of an operation.
        
        Args:
            operation_id: ID of the operation to update
            current_step: Current step number
            total_steps: Optional updated total number of steps
            details: Optional additional details about the progress
        """
        if operation_id in self._active_operations:
            # Update details locally
            if details:
                self._operation_details[operation_id].update(details)
                
            # Update in the monitor if available
            if self._engine_monitor:
                self._engine_monitor.update_operation(
                    operation_id=operation_id,
                    current_step=current_step,
                    total_steps=total_steps,
                    details=details
                )
                
            logger.debug(f"Agent {self.agent_id} updated operation {operation_id} to step {current_step}")
        else:
            logger.warning(f"Agent {self.agent_id} tried to update unknown operation {operation_id}")
    
    def complete_operation(
        self, 
        operation_id: str, 
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark an operation as completed.
        
        Args:
            operation_id: ID of the operation to complete
            details: Optional additional details about the completion
        """
        if operation_id in self._active_operations:
            # Remove from active operations
            del self._active_operations[operation_id]
            
            # Update details
            if details and operation_id in self._operation_details:
                self._operation_details[operation_id].update(details)
                
            # Update in the monitor if available
            if self._engine_monitor:
                self._engine_monitor.complete_operation(
                    operation_id=operation_id,
                    details=details
                )
                
            logger.debug(f"Agent {self.agent_id} completed operation {operation_id}")
        else:
            logger.warning(f"Agent {self.agent_id} tried to complete unknown operation {operation_id}")
    
    def fail_operation(
        self, 
        operation_id: str, 
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark an operation as failed.
        
        Args:
            operation_id: ID of the operation to fail
            error: Error message
            details: Optional additional details about the failure
        """
        if operation_id in self._active_operations:
            # Remove from active operations
            del self._active_operations[operation_id]
            
            # Update details
            if operation_id in self._operation_details:
                self._operation_details[operation_id]["error"] = error
                if details:
                    self._operation_details[operation_id].update(details)
                    
            # Update in the monitor if available
            if self._engine_monitor:
                self._engine_monitor.fail_operation(
                    operation_id=operation_id,
                    error=error,
                    details=details
                )
                
            logger.warning(f"Agent {self.agent_id} failed operation {operation_id}: {error}")
        else:
            logger.warning(f"Agent {self.agent_id} tried to fail unknown operation {operation_id}")
    
    def cancel_operation(
        self, 
        operation_id: str, 
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Cancel an operation.
        
        Args:
            operation_id: ID of the operation to cancel
            details: Optional additional details about the cancellation
        """
        if operation_id in self._active_operations:
            # Remove from active operations
            del self._active_operations[operation_id]
            
            # Update details
            if details and operation_id in self._operation_details:
                self._operation_details[operation_id].update(details)
                
            # Update in the monitor if available
            if self._engine_monitor:
                self._engine_monitor.cancel_operation(
                    operation_id=operation_id,
                    details=details
                )
                
            logger.info(f"Agent {self.agent_id} cancelled operation {operation_id}")
        else:
            logger.warning(f"Agent {self.agent_id} tried to cancel unknown operation {operation_id}")
    
    def get_operation_details(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details about an operation.
        
        Args:
            operation_id: ID of the operation to get details for
            
        Returns:
            The operation details, or None if not found
        """
        # First check local details
        local_details = self._operation_details.get(operation_id, {})
        
        # Then check monitor if available
        if self._engine_monitor:
            operation = self._engine_monitor.get_operation(operation_id)
            if operation:
                # Combine monitor details with local details
                monitor_details = operation.to_dict()
                return {**monitor_details, **local_details}
                
        return local_details if local_details else None
    
    def check_operation_timeouts(self) -> List[str]:
        """
        Check for timed-out operations and handle them.
        
        Returns:
            List of timed-out operation IDs
        """
        timed_out = []
        current_time = time.time()
        
        for op_id, (start_time, timeout) in list(self._active_operations.items()):
            if timeout is not None and (current_time - start_time) > timeout:
                self.handle_timeout(op_id)
                timed_out.append(op_id)
                
        return timed_out
    
    def handle_timeout(self, operation_id: str) -> None:
        """
        Handle a timed-out operation.
        
        Args:
            operation_id: ID of the timed-out operation
        """
        if operation_id in self._active_operations:
            logger.warning(f"Agent {self.agent_id} operation {operation_id} timed out")
            
            # Remove from active operations
            del self._active_operations[operation_id]
            
            # Add timeout information to details
            if operation_id in self._operation_details:
                self._operation_details[operation_id]["timed_out"] = True
                
            # Implement graceful cancellation of the operation
            # This method should be overridden by subclasses to provide specific handling
            self._handle_operation_timeout(operation_id)
            
            # Broadcast a status message about the timeout
            self.broadcast_status(
                status=f"Operation {operation_id} timed out",
                metadata={"operation_id": operation_id, "timed_out": True}
            )
    
    def _handle_operation_timeout(self, operation_id: str) -> None:
        """
        Handle a timed-out operation. Override this in subclasses for specific handling.
        
        Args:
            operation_id: ID of the timed-out operation
        """
        # Default implementation just logs the timeout
        logger.warning(f"Agent {self.agent_id} operation {operation_id} timed out with no specific handling")
