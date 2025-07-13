"""
Agent Message Protocol - Defines the standardized message format for agent communication.

This module implements the message structure and validation for inter-agent communication
in the Triangulum system, enabling standardized information exchange between specialized agents.
It includes support for chunking large messages, streaming, and compression to handle
large analysis results efficiently.
"""

import uuid
import json
import time
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, field, asdict


class MessageType(Enum):
    """Enum defining the types of messages that can be exchanged between agents."""
    
    # Command messages
    TASK_REQUEST = "task_request"       # Request an agent to perform a task
    QUERY = "query"                     # Request information from an agent
    
    # Response messages
    TASK_RESULT = "task_result"         # Response to a task request
    QUERY_RESPONSE = "query_response"   # Response to a query
    
    # Analysis messages
    PROBLEM_ANALYSIS = "problem_analysis"  # Analysis of a problem
    CODE_ANALYSIS = "code_analysis"        # Analysis of code
    RELATIONSHIP_ANALYSIS = "relationship_analysis"  # Analysis of code relationships
    
    # Action messages
    REPAIR_SUGGESTION = "repair_suggestion"  # Suggested repair action
    VERIFICATION_RESULT = "verification_result"  # Result of verification
    
    # System messages
    ERROR = "error"                     # Error message
    STATUS = "status"                   # Status update
    STATUS_UPDATE = "status_update"     # Detailed status update message
    LOG = "log"                         # Log message
    
    # Large response handling
    CHUNKED_MESSAGE = "chunked_message"  # Message that is part of a larger chunked response
    CHUNK_RESPONSE = "chunk_response"    # Response to a chunked message
    STREAM_START = "stream_start"        # Start of a streamed response
    STREAM_DATA = "stream_data"          # Data in a streamed response
    STREAM_END = "stream_end"            # End of a streamed response


class ConfidenceLevel(Enum):
    """Enum defining confidence levels for agent responses."""
    
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 1.0


# Constants for chunking and large responses
DEFAULT_MAX_MESSAGE_SIZE = 5 * 1024 * 1024  # 5MB maximum message size
MAX_CHUNK_SIZE = 1 * 1024 * 1024  # 1MB maximum chunk size


@dataclass
class AgentMessage:
    """
    Standard message format for agent communication.
    
    This class defines the structure of messages exchanged between agents,
    ensuring a consistent format and facilitating proper routing and handling.
    """
    
    # Required fields
    message_type: MessageType
    content: Dict[str, Any]
    sender: str
    
    # Optional fields with defaults
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    receiver: Optional[str] = None
    parent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Schema version for backward compatibility
    schema_version: str = "1.1"
    
    # Large response handling fields
    is_chunked: bool = False
    chunk_id: Optional[str] = None
    total_chunks: Optional[int] = None
    chunk_sequence: Optional[int] = None
    response_id: Optional[str] = None
    compressed: bool = False
    
    # Enhanced fields for agent communication framework
    problem_context: Dict[str, Any] = field(default_factory=dict)
    """
    Context information about the problem being addressed.
    
    This field provides additional context about the problem that is being
    discussed in the conversation, such as file paths, error messages,
    stack traces, or any other relevant information that helps agents
    understand the problem domain.
    """
    
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    """
    Results of analysis performed by agents.
    
    This field contains structured data representing the results of
    analysis performed by agents, such as bug detection results,
    relationship analysis, or other findings that contribute to
    solving the problem.
    """
    
    suggested_actions: List[Dict[str, Any]] = field(default_factory=list)
    """
    Actions suggested by agents.
    
    This field contains a list of suggested actions that agents propose
    to address the problem, such as code changes, tests to run, or
    other actions that could resolve the issue. Each action is a
    dictionary with details about the suggestion.
    """
    
    def __post_init__(self):
        """Validate the message after initialization."""
        self.validate()
        
        # If no conversation_id is provided, use message_id as the start of a conversation
        if not self.conversation_id:
            self.conversation_id = self.message_id
    
    def validate(self) -> bool:
        """
        Validate the message structure and content.
        
        Returns:
            bool: True if the message is valid, raises ValueError otherwise
        """
        if not isinstance(self.message_type, MessageType):
            raise ValueError(f"message_type must be a MessageType enum, got {type(self.message_type)}")
        try:
            # Import here to avoid circular imports
            from triangulum_lx.agents.message_schema import validate_message
            
            # Convert to dict for validation
            message_dict = self.to_dict()
            
            # Validate against schema
            is_valid, errors = validate_message(message_dict)
            
            if not is_valid:
                error_msg = "; ".join(errors)
                raise ValueError(f"Message validation failed: {error_msg}")
            
            return True
        except ImportError:
            # Fall back to basic validation if schema module is not available
            # Check required fields
            
            if not isinstance(self.content, dict):
                raise ValueError(f"content must be a dictionary, got {type(self.content)}")
            
            if not self.sender:
                raise ValueError("sender is required")
            
            # Validate confidence if provided
            if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
                raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
            
            # Validate schema version
            if not isinstance(self.schema_version, str):
                raise ValueError(f"schema_version must be a string, got {type(self.schema_version)}")
            
            # Validate enhanced fields
            if not isinstance(self.problem_context, dict):
                raise ValueError(f"problem_context must be a dictionary, got {type(self.problem_context)}")
            
            if not isinstance(self.analysis_results, dict):
                raise ValueError(f"analysis_results must be a dictionary, got {type(self.analysis_results)}")
            
            if not isinstance(self.suggested_actions, list):
                raise ValueError(f"suggested_actions must be a list, got {type(self.suggested_actions)}")
            
            return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the message
        """
        result = asdict(self)
        
        # Convert Enum to string for JSON serialization
        result["message_type"] = self.message_type.value
        
        return result
    
    def to_json(self) -> str:
        """
        Convert the message to a JSON string.
        
        Returns:
            str: JSON representation of the message
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """
        Create a message from a dictionary representation.
        
        Args:
            data: Dictionary representation of the message
            
        Returns:
            AgentMessage: Instantiated message object
        """
        try:
            # Import here to avoid circular imports
            from triangulum_lx.agents.message_schema import convert_field_type, get_default_values
            
            # Apply default values for missing fields
            defaults = get_default_values()
            for field, default in defaults.items():
                if field not in data:
                    data[field] = default
            
            # Convert field types according to schema
            for field, value in list(data.items()):
                data[field] = convert_field_type(field, value)
        except ImportError:
            # Fall back to basic conversion if schema module is not available
            # Convert string to Enum for message_type
            if isinstance(data.get("message_type"), str):
                data["message_type"] = MessageType(data["message_type"])
            
            # Handle backward compatibility for schema versions
            schema_version = data.get("schema_version", "1.0")
            
            # If this is an old format message (pre-1.1), ensure the new fields are initialized
            if schema_version == "1.0":
                # Add the new fields with default values
                data["schema_version"] = "1.1"  # Upgrade to current schema
                data["problem_context"] = data.get("problem_context", {})
                data["analysis_results"] = data.get("analysis_results", {})
                data["suggested_actions"] = data.get("suggested_actions", [])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMessage':
        """
        Create a message from a JSON string.
        
        Args:
            json_str: JSON representation of the message
            
        Returns:
            AgentMessage: Instantiated message object
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def create_response(self, 
                         message_type: MessageType, 
                         content: Dict[str, Any],
                         confidence: Optional[float] = None,
                         metadata: Optional[Dict[str, Any]] = None,
                         problem_context: Optional[Dict[str, Any]] = None,
                         analysis_results: Optional[Dict[str, Any]] = None,
                         suggested_actions: Optional[List[Dict[str, Any]]] = None,
                         is_chunked: bool = False,
                         chunk_id: Optional[str] = None,
                         total_chunks: Optional[int] = None,
                         chunk_sequence: Optional[int] = None,
                         response_id: Optional[str] = None,
                         compressed: bool = False) -> 'AgentMessage':
        """
        Create a response message to this message.
        
        Args:
            message_type: Type of the response message
            content: Content of the response
            confidence: Confidence level of the response
            metadata: Additional metadata for the response
            problem_context: Context information about the problem (optional)
            analysis_results: Results of analysis performed (optional)
            suggested_actions: List of suggested actions (optional)
            
        Returns:
            AgentMessage: Response message
        """
        return AgentMessage(
            message_type=message_type,
            content=content,
            sender=self.receiver,
            receiver=self.sender,
            parent_id=self.message_id,
            conversation_id=self.conversation_id,
            confidence=confidence,
            metadata=metadata or {},
            problem_context=problem_context or self.problem_context,
            analysis_results=analysis_results or self.analysis_results,
            suggested_actions=suggested_actions or self.suggested_actions,
            is_chunked=is_chunked,
            chunk_id=chunk_id,
            total_chunks=total_chunks,
            chunk_sequence=chunk_sequence,
            response_id=response_id,
            compressed=compressed
        )
        
    @classmethod
    def create_chunked_message(
        cls,
        chunk_sequence: int,
        total_chunks: int,
        response_id: str,
        content: Dict[str, Any],
        sender: str,
        receiver: Optional[str] = None,
        parent_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        compressed: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'AgentMessage':
        """
        Create a chunked message for large response data.
        
        Args:
            chunk_sequence: Position of this chunk in the sequence
            total_chunks: Total number of chunks in the complete response
            response_id: Identifier for the complete response this chunk belongs to
            content: Content of this chunk
            sender: Sender of the message
            receiver: Receiver of the message
            parent_id: ID of the parent message
            conversation_id: ID of the conversation
            compressed: Whether the data is compressed
            metadata: Additional metadata
            
        Returns:
            AgentMessage: A chunked message
        """
        chunk_id = f"{response_id}_{chunk_sequence}"
        
        return cls(
            message_type=MessageType.CHUNKED_MESSAGE,
            content=content,
            sender=sender,
            receiver=receiver,
            parent_id=parent_id,
            conversation_id=conversation_id,
            metadata=metadata or {},
            is_chunked=True,
            chunk_id=chunk_id,
            total_chunks=total_chunks,
            chunk_sequence=chunk_sequence,
            response_id=response_id,
            compressed=compressed
        )
    
    @classmethod
    def create_stream_start_message(
        cls,
        response_id: str,
        total_chunks: int,
        sender: str,
        receiver: Optional[str] = None,
        parent_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'AgentMessage':
        """
        Create a message indicating the start of a streamed response.
        
        Args:
            response_id: Identifier for the complete response
            total_chunks: Expected total number of chunks
            sender: Sender of the message
            receiver: Receiver of the message
            parent_id: ID of the parent message
            conversation_id: ID of the conversation
            metadata: Additional metadata
            
        Returns:
            AgentMessage: A stream start message
        """
        return cls(
            message_type=MessageType.STREAM_START,
            content={
                "response_id": response_id,
                "total_chunks": total_chunks,
                "timestamp": time.time()
            },
            sender=sender,
            receiver=receiver,
            parent_id=parent_id,
            conversation_id=conversation_id,
            metadata=metadata or {},
            is_chunked=False,
            response_id=response_id,
            total_chunks=total_chunks
        )
    
    @classmethod
    def create_stream_end_message(
        cls,
        response_id: str,
        chunks_sent: int,
        sender: str,
        receiver: Optional[str] = None,
        parent_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'AgentMessage':
        """
        Create a message indicating the end of a streamed response.
        
        Args:
            response_id: Identifier for the complete response
            chunks_sent: Number of chunks sent
            sender: Sender of the message
            receiver: Receiver of the message
            parent_id: ID of the parent message
            conversation_id: ID of the conversation
            metadata: Additional metadata
            
        Returns:
            AgentMessage: A stream end message
        """
        return cls(
            message_type=MessageType.STREAM_END,
            content={
                "response_id": response_id,
                "chunks_sent": chunks_sent,
                "timestamp": time.time()
            },
            sender=sender,
            receiver=receiver,
            parent_id=parent_id,
            conversation_id=conversation_id,
            metadata=metadata or {},
            is_chunked=False,
            response_id=response_id
        )


@dataclass
class ConversationMemory:
    """
    Stores the history of messages in a conversation.
    
    This class maintains the history of messages exchanged in a conversation,
    allowing agents to reference previous messages and maintain context.
    """
    
    conversation_id: str
    messages: List[AgentMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: AgentMessage) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            message: Message to add
        """
        if message.conversation_id != self.conversation_id:
            raise ValueError(
                f"Message conversation_id ({message.conversation_id}) does not match "
                f"conversation_id ({self.conversation_id})"
            )
        
        self.messages.append(message)
    
    def get_message_by_id(self, message_id: str) -> Optional[AgentMessage]:
        """
        Get a message by its ID.
        
        Args:
            message_id: ID of the message to retrieve
            
        Returns:
            AgentMessage or None: The message if found, None otherwise
        """
        for message in self.messages:
            if message.message_id == message_id:
                return message
        return None
    
    def get_messages_by_type(self, message_type: MessageType) -> List[AgentMessage]:
        """
        Get all messages of a specific type.
        
        Args:
            message_type: Type of messages to retrieve
            
        Returns:
            List[AgentMessage]: List of messages of the specified type
        """
        return [m for m in self.messages if m.message_type == message_type]
    
    def get_messages_by_sender(self, sender: str) -> List[AgentMessage]:
        """
        Get all messages from a specific sender.
        
        Args:
            sender: Sender of messages to retrieve
            
        Returns:
            List[AgentMessage]: List of messages from the specified sender
        """
        return [m for m in self.messages if m.sender == sender]
    
    def get_message_chain(
        self, 
        message_id: str,
        include_parents: bool = True,
        include_children: bool = True
    ) -> List[AgentMessage]:
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
        # Find the starting message
        start_message = self.get_message_by_id(message_id)
        if not start_message:
            return []
        
        # Build the chain
        chain = [start_message]
        
        # Add parent messages if requested
        if include_parents:
            # Build the parent chain recursively
            parent_chain = []
            current_message = start_message
            
            while current_message.parent_id:
                parent = self.get_message_by_id(current_message.parent_id)
                if not parent:
                    # Parent message not found in this conversation
                    break
                
                parent_chain.insert(0, parent)  # Insert at beginning to maintain chronological order
                current_message = parent
            
            # Add parent chain before start message
            chain = parent_chain + chain
        
        # Add child messages if requested
        if include_children:
            current_id = message_id
            
            # Add all direct child messages
            while True:
                # Find messages that have this message as parent
                children = [m for m in self.messages if m.parent_id == current_id]
                if not children:
                    break
                    
                # Add the first child and continue the chain
                chain.append(children[0])
                current_id = children[0].message_id
        
        return chain
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the conversation memory to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the conversation memory
        """
        return {
            "conversation_id": self.conversation_id,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMemory':
        """
        Create a conversation memory from a dictionary.
        
        Args:
            data: Dictionary representation of the conversation memory
            
        Returns:
            ConversationMemory: Instantiated conversation memory
        """
        messages = [AgentMessage.from_dict(m) for m in data.get("messages", [])]
        
        return cls(
            conversation_id=data["conversation_id"],
            messages=messages,
            metadata=data.get("metadata", {})
        )
