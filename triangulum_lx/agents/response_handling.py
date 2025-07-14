"""
Response Handling Module for Triangulum

This module provides utilities for handling large responses, response chunking,
compression, validation, and asynchronous coordination in the Triangulum agent
communication framework.
"""

import gzip
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple, Callable, Union

from .message import AgentMessage, MessageType

logger = logging.getLogger("triangulum.response_handling")

class ResponseSerializer:
    """Serializes and deserializes response content."""
    
    @staticmethod
    def serialize(content: Any) -> str:
        """
        Serialize content to a string representation.
        
        Args:
            content: The content to serialize
            
        Returns:
            Serialized string
        """
        return json.dumps(content, default=str)
    
    @staticmethod
    def deserialize(serialized: str) -> Any:
        """
        Deserialize content from a string representation.
        
        Args:
            serialized: The serialized string
            
        Returns:
            Deserialized content
        """
        return json.loads(serialized)

# Constants for response handling
MAX_MESSAGE_SIZE = 500 * 1024  # 500KB max message size
DEFAULT_CHUNK_SIZE = 100 * 1024  # 100KB default chunk size
COMPRESSION_THRESHOLD = 50 * 1024  # 50KB compression threshold
DEFAULT_TIMEOUT = 30.0  # 30 seconds default timeout
MAX_RETRIES = 3  # Maximum number of retries for failed responses
STREAM_BUFFER_SIZE = 10  # Number of messages to buffer in a stream


class ResponseValidationError(Exception):
    """Exception raised when a response fails validation."""
    pass


class ResponseTimeoutError(Exception):
    """Exception raised when a response times out."""
    pass


class ResponseFormatError(Exception):
    """Exception raised when a response has an invalid format."""
    pass


class ResponseChunker:
    """Handles chunking of large responses into multiple messages."""
    
    def __init__(self, max_chunk_size: int = DEFAULT_CHUNK_SIZE):
        """Initialize the chunker with maximum chunk size."""
        self.max_chunk_size = max_chunk_size
    
    def chunk_message(self, message: AgentMessage) -> List[AgentMessage]:
        """
        Split a large message into multiple chunks.
        
        Args:
            message: The original message to chunk
            
        Returns:
            List of chunked messages
        """
        # Serialize the content to estimate size
        content_json = json.dumps(message.content)
        content_size = len(content_json.encode('utf-8'))
        
        # If under threshold, return original message
        if content_size <= self.max_chunk_size:
            return [message]
        
        # Generate a chunk ID for this set of chunks
        chunk_id = str(uuid.uuid4())
        
        # Split the content into chunks
        chunks = []
        remaining = message.content
        chunk_number = 0
        total_chunks = None  # Will be calculated later
        
        # Create chunks of manageable size
        chunk_data_list = []
        if isinstance(message.content, dict) and 'data' in message.content and isinstance(message.content['data'], list):
            data_list = message.content['data']
            items_per_chunk = 1
            while True:
                chunk_size = len(json.dumps(data_list[:items_per_chunk]).encode('utf-8'))
                if chunk_size > self.max_chunk_size and items_per_chunk > 1:
                    items_per_chunk -=1
                    break
                if chunk_size > self.max_chunk_size:
                    # A single item is too large, so we can't chunk it further.
                    # It will be sent as a single chunk and hopefully compressed.
                    break
                if chunk_size <= self.max_chunk_size:
                    items_per_chunk += 1
                if items_per_chunk > len(data_list):
                    items_per_chunk = len(data_list)
                    break

            for i in range(0, len(data_list), items_per_chunk):
                chunk_data_list.append({'data': data_list[i:i + items_per_chunk]})
        else:
            chunk_data_list.append(message.content)

        for i, chunk_data in enumerate(chunk_data_list):
            # Create the chunk message
            chunk_message = AgentMessage(
                message_id=f"{message.message_id}_chunk_{i}",
                message_type=MessageType.CHUNKED_MESSAGE,
                content={
                    "chunk_id": chunk_id,
                    "chunk_number": i,
                    "original_message_id": message.message_id,
                    "original_message_type": message.message_type.value,
                    "chunk_data": chunk_data
                },
                sender=message.sender,
                receiver=message.receiver,
                timestamp=message.timestamp
            )
            chunks.append(chunk_message)
        
        # Update total_chunks in all chunks
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk.content["total_chunks"] = total_chunks
        
        logger.info(f"Split message {message.message_id} into {total_chunks} chunks")
        return chunks
    
    def reassemble_chunks(self, chunks: List[AgentMessage]) -> Optional[AgentMessage]:
        """
        Reassemble chunks into the original message.
        
        Args:
            chunks: List of chunked messages
            
        Returns:
            Reassembled original message or None if incomplete
        """
        if not chunks:
            return None
        
        # Get chunk information from the first chunk
        first_chunk = chunks[0]
        chunk_id = first_chunk.content.get("chunk_id")
        total_chunks = first_chunk.content.get("total_chunks")
        original_message_id = first_chunk.content.get("original_message_id")
        original_message_type = first_chunk.content.get("original_message_type")
        
        # Validate chunk information
        if not all([chunk_id, total_chunks, original_message_id, original_message_type]):
            logger.error("Invalid chunk information")
            return None
        
        # Check if we have all chunks
        if len(chunks) != total_chunks:
            logger.info(f"Incomplete chunks: {len(chunks)}/{total_chunks}")
            return None
        
        # Sort chunks by chunk number
        chunks.sort(key=lambda c: c.content.get("chunk_number", 0))
        
        # Validate chunk sequence
        for i, chunk in enumerate(chunks):
            if chunk.content.get("chunk_number") != i:
                logger.error(f"Invalid chunk sequence: expected {i}, got {chunk.content.get('chunk_number')}")
                return None
            if chunk.content.get("chunk_id") != chunk_id:
                logger.error(f"Inconsistent chunk_id: {chunk.content.get('chunk_id')} != {chunk_id}")
                return None
        
        # Merge chunk data
        merged_content = {}
        for chunk in chunks:
            chunk_data = chunk.content.get("chunk_data", {})
            for key, value in chunk_data.items():
                if key in merged_content and isinstance(merged_content[key], list) and isinstance(value, list):
                    # Append lists
                    merged_content[key].extend(value)
                elif key not in merged_content:
                    # Add new key
                    merged_content[key] = value
        
        # Create the reassembled message
        message_type = MessageType(original_message_type)
        reassembled = AgentMessage(
            message_id=original_message_id,
            message_type=message_type,
            content=merged_content,
            sender=first_chunk.sender,
            receiver=first_chunk.receiver,
            timestamp=first_chunk.timestamp
        )
        
        logger.info(f"Reassembled {total_chunks} chunks into message {original_message_id}")
        return reassembled


class ResponseCompressor:
    """Handles compression and decompression of large responses."""
    
    def __init__(self, compression_threshold: int = COMPRESSION_THRESHOLD):
        """Initialize with compression threshold."""
        self.compression_threshold = compression_threshold
    
    def compress_message(self, message: AgentMessage) -> AgentMessage:
        """
        Compress message content if it exceeds the threshold.
        
        Args:
            message: The message to compress
            
        Returns:
            Message with compressed content if applicable
        """
        # Serialize the content to estimate size
        content_json = json.dumps(message.content)
        content_size = len(content_json.encode('utf-8'))
        
        # If under threshold, return original message
        if content_size <= self.compression_threshold:
            return message
        
        # Compress the content
        compressed_content = gzip.compress(content_json.encode('utf-8'))
        compressed_size = len(compressed_content)
        
        # Create compression metadata
        compression_info = {
            "compressed": True,
            "original_size": content_size,
            "compressed_size": compressed_size,
            "compression_ratio": content_size / compressed_size if compressed_size > 0 else 0
        }
        
        # Create a new message with compressed content
        compressed_message = AgentMessage(
            message_id=message.message_id,
            message_type=message.message_type,
            content={
                "_compression": compression_info,
                "_compressed_data": compressed_content.hex()  # Convert binary to hex string for JSON compatibility
            },
            sender=message.sender,
            receiver=message.receiver,
            timestamp=message.timestamp
        )
        
        logger.info(f"Compressed message {message.message_id}: {compression_info['compression_ratio']:.2f}x ratio")
        return compressed_message
    
    def decompress_message(self, message: AgentMessage) -> AgentMessage:
        """
        Decompress message content if it is compressed.
        
        Args:
            message: The potentially compressed message
            
        Returns:
            Message with decompressed content if applicable
        """
        # Check if the message is compressed
        compression_info = message.content.get("_compression", {})
        compressed_data_hex = message.content.get("_compressed_data")
        
        if not compression_info.get("compressed") or not compressed_data_hex:
            return message  # Not compressed
        
        try:
            # Convert hex string back to binary and decompress
            compressed_data = bytes.fromhex(compressed_data_hex)
            decompressed_json = gzip.decompress(compressed_data).decode('utf-8')
            decompressed_content = json.loads(decompressed_json)
            
            # Create a new message with decompressed content
            decompressed_message = AgentMessage(
                message_id=message.message_id,
                message_type=message.message_type,
                content=decompressed_content,
                sender=message.sender,
                receiver=message.receiver,
                timestamp=message.timestamp
            )
            
            logger.info(f"Decompressed message {message.message_id}")
            return decompressed_message
            
        except Exception as e:
            logger.error(f"Error decompressing message {message.message_id}: {str(e)}")
            # Return original message if decompression fails
            return message


class ResponseValidator:
    """Validates response format and content."""
    
    def __init__(self, schema_validators: Dict[str, Callable] = None):
        """
        Initialize with optional schema validators.
        
        Args:
            schema_validators: Dict mapping message types to validator functions
        """
        self.schema_validators = schema_validators or {}
    
    def validate_response(self, message: AgentMessage) -> Tuple[bool, Optional[str]]:
        """
        Validate a response message.
        
        Args:
            message: The message to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic validation
        if not message.message_id:
            return False, "Missing message ID"
        
        if not message.message_type:
            return False, "Missing message type"
        
        if not message.sender:
            return False, "Missing sender"
        
        if not message.receiver:
            return False, "Missing receiver"
        
        if message.timestamp is None:
            return False, "Missing timestamp"
        
        # Content validation
        if message.content is None:
            return False, "Missing content"
        
        # Schema validation if available
        validator = self.schema_validators.get(message.message_type.value)
        if validator:
            try:
                validator(message.content)
            except Exception as e:
                return False, f"Schema validation failed: {str(e)}"
        
        return True, None
    
    def normalize_response(self, message: AgentMessage) -> AgentMessage:
        """
        Normalize a response message to ensure consistent format.
        
        Args:
            message: The message to normalize
            
        Returns:
            Normalized message
        """
        # Create a copy to avoid modifying the original
        normalized = AgentMessage(
            message_id=message.message_id,
            message_type=message.message_type,
            content=message.content.copy() if message.content else {},
            sender=message.sender,
            receiver=message.receiver,
            timestamp=message.timestamp
        )
        
        # Ensure content is a dictionary
        if normalized.content is None:
            normalized.content = {}
        
        # Add metadata if missing
        if "metadata" not in normalized.content:
            normalized.content["metadata"] = {}
        
        # Add normalized timestamp
        normalized.content["metadata"]["normalized_timestamp"] = time.time()
        
        return normalized


class AsyncResponseCoordinator:
    """Coordinates asynchronous responses across agents."""
    
    def __init__(self, default_timeout: float = DEFAULT_TIMEOUT):
        """Initialize with default timeout."""
        self.pending_responses = {}  # request_id -> response_info
        self.response_callbacks = {}  # request_id -> callback_function
        self.default_timeout = default_timeout
    
    def register_request(self, request_id: str, timeout: Optional[float] = None, 
                        callback: Optional[Callable] = None) -> None:
        """
        Register a request for async response tracking.
        
        Args:
            request_id: The unique request ID
            timeout: Optional timeout in seconds
            callback: Optional callback function to invoke on response
        """
        self.pending_responses[request_id] = {
            "request_id": request_id,
            "status": "pending",
            "request_time": time.time(),
            "timeout": timeout or self.default_timeout,
            "response": None,
            "error": None
        }
        
        if callback:
            self.response_callbacks[request_id] = callback
    
    def handle_response(self, request_id: str, response: Any, 
                       error: Optional[str] = None) -> bool:
        """
        Handle a response for a registered request.
        
        Args:
            request_id: The request ID
            response: The response data
            error: Optional error message
            
        Returns:
            True if the response was handled, False otherwise
        """
        if request_id not in self.pending_responses:
            logger.warning(f"Received response for unknown request ID: {request_id}")
            return False
        
        # Update response info
        self.pending_responses[request_id].update({
            "status": "completed" if error is None else "error",
            "response_time": time.time(),
            "response": response,
            "error": error
        })
        
        # Call callback if registered
        if request_id in self.response_callbacks:
            try:
                self.response_callbacks[request_id](
                    request_id, 
                    response, 
                    error
                )
            except Exception as e:
                logger.error(f"Error in response callback for {request_id}: {str(e)}")
            
            # Remove callback after execution
            del self.response_callbacks[request_id]
        
        return True
    
    def check_timeouts(self) -> List[str]:
        """
        Check for timed-out requests.
        
        Returns:
            List of timed-out request IDs
        """
        timed_out = []
        current_time = time.time()
        
        for request_id, info in self.pending_responses.items():
            if info["status"] == "pending":
                elapsed = current_time - info["request_time"]
                if elapsed > info["timeout"]:
                    # Mark as timed out
                    info["status"] = "timeout"
                    info["error"] = f"Request timed out after {elapsed:.2f} seconds"
                    timed_out.append(request_id)
                    
                    # Call callback with timeout error
                    if request_id in self.response_callbacks:
                        try:
                            self.response_callbacks[request_id](
                                request_id, 
                                None, 
                                info["error"]
                            )
                        except Exception as e:
                            logger.error(f"Error in timeout callback for {request_id}: {str(e)}")
                        
                        # Remove callback after execution
                        del self.response_callbacks[request_id]
        
        return timed_out
    
    def wait_for_response(self, request_id: str, timeout: Optional[float] = None) -> Tuple[bool, Any, Optional[str]]:
        """
        Wait for a response to a specific request.
        
        Args:
            request_id: The request ID
            timeout: Optional timeout override
            
        Returns:
            Tuple of (success, response, error)
        """
        if request_id not in self.pending_responses:
            return False, None, "Unknown request ID"
        
        info = self.pending_responses[request_id]
        wait_timeout = timeout or info["timeout"]
        end_time = info["request_time"] + wait_timeout
        
        # Wait for response or timeout
        while time.time() < end_time:
            if info["status"] != "pending":
                break
            time.sleep(0.1)
        
        # Check result
        if info["status"] == "completed":
            return True, info["response"], None
        elif info["status"] == "error":
            return False, None, info["error"]
        elif info["status"] == "timeout":
            return False, None, f"Request timed out after {wait_timeout:.2f} seconds"
        else:
            # Manually check for timeout
            self.check_timeouts()
            info = self.pending_responses[request_id]
            
            if info["status"] == "timeout":
                return False, None, info["error"]
            else:
                return False, None, "Unknown error"
    
    def clean_up(self, max_age: float = 3600.0) -> int:
        """
        Clean up old completed or failed requests.
        
        Args:
            max_age: Maximum age in seconds for keeping completed/failed requests
            
        Returns:
            Number of removed entries
        """
        to_remove = []
        current_time = time.time()
        
        for request_id, info in self.pending_responses.items():
            if info["status"] in ["completed", "error", "timeout"]:
                if "response_time" in info and current_time - info["response_time"] > max_age:
                    to_remove.append(request_id)
        
        # Remove old entries
        for request_id in to_remove:
            del self.pending_responses[request_id]
        
        return len(to_remove)


class LargeResponseHandler:
    """
    Handles large responses with chunking, compression and streaming.
    
    This class orchestrates the entire large response handling process,
    using the various specialized components to process responses efficiently.
    """
    
    def __init__(self, message_bus=None):
        """
        Initialize with dependencies.
        
        Args:
            message_bus: Optional message bus reference
        """
        self.message_bus = message_bus
        self.chunker = ResponseChunker()
        self.compressor = ResponseCompressor()
        self.validator = ResponseValidator()
        self.async_coordinator = AsyncResponseCoordinator()
        
        # Chunk storage for reassembly
        self.chunk_storage = {}  # chunk_id -> list of chunks
        
        # Stream handling
        self.active_streams = {}  # stream_id -> stream_info
    
    def set_message_bus(self, message_bus) -> None:
        """Set the message bus reference."""
        self.message_bus = message_bus
    
    def process_outgoing_message(self, message: AgentMessage, 
                                large_content_handling: str = "auto") -> Union[List[str], str]:
        """
        Process an outgoing message, handling large content as needed.
        
        Args:
            message: The message to process
            large_content_handling: How to handle large content 
                                   ("auto", "direct", "chunked", "stream")
                                   
        Returns:
            List of message IDs or single message ID
        """
        # Validate message
        is_valid, error = self.validator.validate_response(message)
        if not is_valid:
            raise ResponseValidationError(f"Invalid message: {error}")
        
        # Normalize message
        message = self.validator.normalize_response(message)
        
        # Handle based on specified method
        if large_content_handling == "direct":
            # Compress if necessary but send as single message
            processed_message = self.compressor.compress_message(message)
            
            # Check if message size is still too large
            content_json = json.dumps(processed_message.content)
            content_size = len(content_json.encode('utf-8'))
            
            if content_size > MAX_MESSAGE_SIZE:
                logger.warning(
                    f"Message {message.message_id} exceeds maximum size "
                    f"({content_size} > {MAX_MESSAGE_SIZE}) even after compression. "
                    f"Falling back to chunking."
                )
                return self._handle_chunked(message)
            else:
                # Send directly
                if self.message_bus:
                    self.message_bus.publish(processed_message)
                return processed_message.message_id
                
        elif large_content_handling == "chunked":
            return self._handle_chunked(message)
            
        elif large_content_handling == "stream":
            return self._handle_streamed(message)
            
        else:  # "auto"
            # Determine best method based on content size
            content_json = json.dumps(message.content)
            content_size = len(content_json.encode('utf-8'))
            
            if content_size <= self.chunker.max_chunk_size:
                # Small enough to send directly
                if self.message_bus:
                    self.message_bus.publish(message)
                return [message.message_id]

            # Compress if size is between chunk size and max message size
            elif content_size <= MAX_MESSAGE_SIZE:
                compressed_message = self.compressor.compress_message(message)
                if self.message_bus:
                    self.message_bus.publish(compressed_message)
                return [compressed_message.message_id]

            else:
                # Too large, use chunking
                return self._handle_chunked(message)
    
    def _handle_chunked(self, message: AgentMessage) -> List[str]:
        """
        Handle a message using chunking.
        
        Args:
            message: The message to chunk
            
        Returns:
            List of chunk message IDs
        """
        # Split into chunks
        chunks = self.chunker.chunk_message(message)
        
        # If only one chunk, and it's the original message, send it directly
        if len(chunks) == 1 and chunks[0] is message:
            if self.message_bus:
                self.message_bus.publish(message)
            return [message.message_id]

        # Compress each chunk if necessary
        compressed_chunks = [self.compressor.compress_message(chunk) for chunk in chunks]
        
        # Send chunks
        if self.message_bus:
            for chunk in compressed_chunks:
                self.message_bus.publish(chunk)
        
        # Return the chunk message IDs
        return [chunk.message_id for chunk in compressed_chunks]
    
    def _handle_streamed(self, message: AgentMessage) -> List[str]:
        """
        Handle a message using streaming.
        
        Args:
            message: The message to stream
            
        Returns:
            List of stream message IDs
        """
        # For now, streaming is implemented as chunking
        # In a full implementation, this would use a more efficient streaming protocol
        return self._handle_chunked(message)
    
    def process_incoming_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Process an incoming message, handling decompression and reassembly.
        
        Args:
            message: The incoming message
            
        Returns:
            Processed message or None if no complete message is available
        """
        # Check for compression
        if "_compression" in message.content:
            message = self.compressor.decompress_message(message)
        
        # Handle chunked messages
        if message.message_type == MessageType.CHUNKED_MESSAGE:
            return self._process_chunk(message)
        
        # Regular message
        return message
    
    def _process_chunk(self, chunk: AgentMessage) -> Optional[AgentMessage]:
        """
        Process a chunk message and attempt reassembly.
        
        Args:
            chunk: The chunk message
            
        Returns:
            Reassembled message if complete, None otherwise
        """
        chunk_id = chunk.content.get("chunk_id")
        if not chunk_id:
            logger.error("Received chunk without chunk_id")
            return None
        
        # Store the chunk
        if chunk_id not in self.chunk_storage:
            self.chunk_storage[chunk_id] = []
        
        self.chunk_storage[chunk_id].append(chunk)
        
        # Check if we have all chunks
        total_chunks = chunk.content.get("total_chunks")
        if total_chunks and len(self.chunk_storage[chunk_id]) >= total_chunks:
            # Attempt reassembly
            reassembled = self.chunker.reassemble_chunks(self.chunk_storage[chunk_id])
            
            # Clean up chunks if reassembly succeeded
            if reassembled:
                del self.chunk_storage[chunk_id]
                return reassembled
        
        return None
    
    def register_async_response(self, request_id: str, timeout: Optional[float] = None,
                              callback: Optional[Callable] = None) -> None:
        """
        Register for an asynchronous response.
        
        Args:
            request_id: The request ID to track
            timeout: Optional timeout in seconds
            callback: Optional callback function
        """
        self.async_coordinator.register_request(request_id, timeout, callback)
    
    def handle_async_response(self, request_id: str, response: Any, error: Optional[str] = None) -> bool:
        """
        Handle an asynchronous response.
        
        Args:
            request_id: The request ID
            response: The response data
            error: Optional error message
            
        Returns:
            True if the response was handled, False otherwise
        """
        return self.async_coordinator.handle_response(request_id, response, error)
    
    def wait_for_async_response(self, request_id: str, timeout: Optional[float] = None) -> Tuple[bool, Any, Optional[str]]:
        """
        Wait for an asynchronous response.
        
        Args:
            request_id: The request ID
            timeout: Optional timeout override
            
        Returns:
            Tuple of (success, response, error)
        """
        return self.async_coordinator.wait_for_response(request_id, timeout)
    
    def check_timeouts(self) -> List[str]:
        """
        Check for timed-out requests.
        
        Returns:
            List of timed-out request IDs
        """
        return self.async_coordinator.check_timeouts()
    
    def clean_up(self) -> None:
        """Clean up expired data."""
        # Clean up old requests
        self.async_coordinator.clean_up()
        
        # Clean up old chunks (incomplete for over 5 minutes)
        current_time = time.time()
        chunk_ids_to_remove = []
        
        for chunk_id, chunks in self.chunk_storage.items():
            oldest_chunk_time = min(chunk.timestamp for chunk in chunks)
            if current_time - oldest_chunk_time > 300:  # 5 minutes
                chunk_ids_to_remove.append(chunk_id)
        
        for chunk_id in chunk_ids_to_remove:
            del self.chunk_storage[chunk_id]
