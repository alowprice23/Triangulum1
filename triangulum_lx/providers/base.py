#!/usr/bin/env python3
"""
Base Provider

Abstract base class for all LLM providers in the Triangulum system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Tool:
    """Represents a tool that can be used by agents."""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Optional[callable] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class ToolCall:
    """Represents a call to a tool."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None
    
    def __post_init__(self):
        if self.arguments is None:
            self.arguments = {}
        if self.call_id is None:
            import uuid
            self.call_id = str(uuid.uuid4())

class LLMProvider(ABC):
    """Abstract base class for LLM providers (alias for BaseProvider)."""
    pass

class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the provider with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured.
        
        Returns:
            True if provider is available, False otherwise
        """
        pass
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a response using the provider.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        pass
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Update provider configuration.
        
        Args:
            config: New configuration dictionary
        """
        self.config.update(config)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about this provider.
        
        Returns:
            Provider information dictionary
        """
        return {
            'name': self.name,
            'available': self.is_available(),
            'config_keys': list(self.config.keys())
        }
    
    def shutdown(self) -> None:
        """Shutdown the provider and clean up resources."""
        pass
