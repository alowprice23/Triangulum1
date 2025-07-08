"""
Enhanced o3 Provider Implementation

This module implements a specialized OpenAI provider optimized for o3 model interactions,
with advanced features like:
- API Abstraction Layer: Robust handling of rate limits, token optimization, and errors
- Context Management: Sophisticated context management to optimize token usage 
- Model Configuration Profiles: Optimal configurations for different agent roles
"""

import os
import time
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, Iterator, Tuple
from dataclasses import dataclass
from enum import Enum
import backoff

from openai import OpenAI, APIError, RateLimitError
from .openai import OpenAIProvider
from .base import LLMProvider, LLMResponse, Tool, ToolCall

# Configure logging
logger = logging.getLogger(__name__)

class AgentRole(Enum):
    """Defines different agent roles for model configuration."""
    ANALYST = "analyst"          # For analyzing code and relationships
    DETECTIVE = "detective"      # For finding bugs and issues
    STRATEGIST = "strategist"    # For planning repairs
    IMPLEMENTER = "implementer"  # For generating code fixes
    VERIFIER = "verifier"        # For testing and verifying changes
    DEFAULT = "default"          # Default configuration


@dataclass
class ModelConfig:
    """Configuration profile for a specific model and agent role."""
    temperature: float
    top_p: float
    max_tokens: int
    frequency_penalty: float
    presence_penalty: float
    system_prompt_template: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_completion_tokens": self.max_tokens,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty
        }


class O3Provider(OpenAIProvider):
    """
    Enhanced OpenAI Provider specifically optimized for o3 model interactions.
    Includes advanced API abstraction, context management, and role-based configurations.
    """

    # Model configuration profiles for different agent roles
    MODEL_CONFIGS = {
        AgentRole.ANALYST: ModelConfig(
            temperature=0.2,
            top_p=0.9,
            max_tokens=4096,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            system_prompt_template="You are an expert code analyst helping to understand complex code relationships. {additional_context}"
        ),
        AgentRole.DETECTIVE: ModelConfig(
            temperature=0.3,
            top_p=0.9,
            max_tokens=4096,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            system_prompt_template="You are a bug detective specialized in finding issues in code. {additional_context}"
        ),
        AgentRole.STRATEGIST: ModelConfig(
            temperature=0.7,
            top_p=0.95,
            max_tokens=4096,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            system_prompt_template="You are a strategic planner for code repairs and improvements. {additional_context}"
        ),
        AgentRole.IMPLEMENTER: ModelConfig(
            temperature=0.2,
            top_p=0.9,
            max_tokens=8192,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            system_prompt_template="You are an expert software engineer implementing precise code fixes. {additional_context}"
        ),
        AgentRole.VERIFIER: ModelConfig(
            temperature=0.1,
            top_p=0.9,
            max_tokens=4096,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            system_prompt_template="You are a verification specialist ensuring code quality and correctness. {additional_context}"
        ),
        AgentRole.DEFAULT: ModelConfig(
            temperature=0.5,
            top_p=0.9,
            max_tokens=4096,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            system_prompt_template="You are an AI assistant helping with a software development task. {additional_context}"
        )
    }

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "o3",
        role: Union[AgentRole, str] = AgentRole.DEFAULT,
        additional_context: str = "",
        max_retries: int = 5,
        timeout: float = 120.0,
        token_limit_buffer: int = 1000
    ):
        """
        Initialize the O3Provider with enhanced configuration.
        
        Args:
            api_key: OpenAI API key (optional, will check environment if None)
            model: Model name (defaults to "o3")
            role: Agent role for configuration profile (analyst, detective, etc.)
            additional_context: Additional context to add to system prompts
            max_retries: Maximum number of retries on rate limit or transient errors
            timeout: API request timeout in seconds
            token_limit_buffer: Safety buffer for token limit calculations
        """
        # Initialize the parent OpenAIProvider
        super().__init__(api_key=api_key, model=model)
        
        # Enhanced configuration
        self.role = role if isinstance(role, AgentRole) else AgentRole(role) if role in [r.value for r in AgentRole] else AgentRole.DEFAULT
        self.additional_context = additional_context
        self.max_retries = max_retries
        self.timeout = timeout
        self.token_limit_buffer = token_limit_buffer
        
        # Rate limiting and usage tracking
        self.request_timestamps = []
        self.tokens_used_last_minute = 0
        self.last_minute_reset = time.time()
        
        # Context management
        self.context_store = {}
        
        # Statistics
        self.stats = {
            "requests": 0,
            "retries": 0,
            "tokens_used": 0,
            "errors": 0
        }

    def get_model_config(self, role: Optional[AgentRole] = None) -> ModelConfig:
        """
        Get the model configuration for the specified role.
        
        Args:
            role: Agent role to get configuration for (uses instance role if None)
            
        Returns:
            ModelConfig for the specified role
        """
        role = role or self.role
        return self.MODEL_CONFIGS.get(role, self.MODEL_CONFIGS[AgentRole.DEFAULT])

    def prepare_system_prompt(self, role: Optional[AgentRole] = None, custom_context: Optional[str] = None) -> str:
        """
        Prepare a system prompt based on the agent role.
        
        Args:
            role: Agent role to prepare prompt for
            custom_context: Custom context to add to the prompt template
            
        Returns:
            Formatted system prompt
        """
        role = role or self.role
        config = self.get_model_config(role)
        context = custom_context or self.additional_context
        return config.system_prompt_template.format(additional_context=context)

    def optimize_messages(self, messages: List[Dict[str, str]], max_tokens: int) -> List[Dict[str, str]]:
        """
        Optimize messages to fit within token limits while preserving critical information.
        
        Args:
            messages: Original message list
            max_tokens: Maximum tokens allowed
            
        Returns:
            Optimized message list
        """
        # Ensure we have a system message at the beginning
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.prepare_system_prompt()}] + messages
            
        # Simple token estimation (can be replaced with a more accurate tokenizer)
        estimated_tokens = sum(len(msg.get("content", "")) // 4 for msg in messages)
        
        # If we're under the limit with buffer, return as is
        token_limit = max_tokens - self.token_limit_buffer
        if estimated_tokens <= token_limit:
            return messages
            
        # Otherwise, we need to optimize
        # Keep system message, most recent user message, and most recent assistant message
        if len(messages) <= 3:
            return messages
            
        # Start with essential messages
        optimized = [messages[0]]  # System message
        
        # Find most recent user and assistant messages
        recent_user = None
        recent_assistant = None
        for msg in reversed(messages[1:]):
            if msg["role"] == "user" and recent_user is None:
                recent_user = msg
            elif msg["role"] == "assistant" and recent_assistant is None:
                recent_assistant = msg
                
            if recent_user is not None and recent_assistant is not None:
                break
                
        # Add summary of older messages
        if len(messages) > 3:
            # Create a summary message
            summary = {
                "role": "system",
                "content": f"The conversation history has been summarized to save tokens. There were {len(messages) - 3} previous messages."
            }
            optimized.append(summary)
            
        # Add the most recent messages
        if recent_assistant:
            optimized.append(recent_assistant)
        if recent_user:
            optimized.append(recent_user)
            
        return optimized

    @backoff.on_exception(
        backoff.expo,
        (RateLimitError, APIError),
        max_tries=5,
        giveup=lambda e: not isinstance(e, (RateLimitError, APIError)) or "exceeded your current quota" in str(e)
    )
    def _api_request_with_backoff(self, api_params: Dict[str, Any]) -> Any:
        """
        Make an API request with exponential backoff for rate limits and transient errors.
        
        Args:
            api_params: Parameters for the API request
            
        Returns:
            API response
        """
        self.stats["requests"] += 1
        try:
            # Track request for rate limiting
            current_time = time.time()
            self.request_timestamps = [ts for ts in self.request_timestamps if current_time - ts < 60]
            self.request_timestamps.append(current_time)
            
            # Check if we should throttle (over 50 requests per minute)
            if len(self.request_timestamps) > 50:
                sleep_time = 60 - (current_time - self.request_timestamps[0])
                if sleep_time > 0:
                    logger.info(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            
            # Make the actual request
            return self.client.chat.completions.create(**api_params)
            
        except (RateLimitError, APIError) as e:
            self.stats["retries"] += 1
            logger.warning(f"API error ({type(e).__name__}): {str(e)}. Retrying...")
            raise
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Unexpected error: {str(e)}")
            raise

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        model_name: Optional[str] = None,
        role: Optional[Union[AgentRole, str]] = None,
        **kwargs: Any
    ) -> Union[LLMResponse, Iterator[LLMResponse]]:
        """
        Generate a response using the o3 model with enhanced features.
        
        Args:
            prompt: String prompt or list of message dictionaries
            temperature: Override temperature from role config
            max_tokens: Override max tokens from role config
            stream: Whether to stream the response
            model_name: Override model name
            role: Override role for this request
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            LLMResponse or Iterator[LLMResponse] if streaming
        """
        # Resolve role if provided as string
        if isinstance(role, str):
            role = AgentRole(role) if role in [r.value for r in AgentRole] else AgentRole.DEFAULT
        
        # Get configuration for the specified role
        config = self.get_model_config(role or self.role)
        
        # Convert string prompt to messages if needed
        if isinstance(prompt, str):
            messages = [
                {"role": "system", "content": self.prepare_system_prompt(role or self.role)},
                {"role": "user", "content": prompt}
            ]
        else:
            messages = prompt
            
        # Optimize messages to fit within token limits
        max_tokens_value = max_tokens or config.max_tokens
        messages = self.optimize_messages(messages, max_tokens_value)
        
        # Prepare API parameters
        api_params = {
            "model": model_name or self.model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }
        
        # Add configuration based on model and role
        if api_params["model"] == "o3":
            # O3 model only accepts default temperature (1.0)
            api_params["max_completion_tokens"] = max_tokens or config.max_tokens
            # Note: o3 model doesn't support temperature other than default (1.0)
            # Only add other parameters if they're supported
            if hasattr(self, "o3_supports_params") and self.o3_supports_params:
                api_params["top_p"] = config.top_p
                api_params["frequency_penalty"] = config.frequency_penalty
                api_params["presence_penalty"] = config.presence_penalty
        else:
            # For non-o3 models, use simpler parameters
            api_params["max_tokens"] = max_tokens or config.max_tokens
            api_params["temperature"] = temperature if temperature is not None else config.temperature
            
        # Generate response with automatic retries and backoff
        if stream:
            return self._generate_stream_enhanced(api_params)
        else:
            return self._generate_non_stream_enhanced(api_params)

    def _generate_non_stream_enhanced(self, api_params: Dict[str, Any]) -> LLMResponse:
        """
        Enhanced non-streaming generation with error handling and statistics.
        
        Args:
            api_params: API parameters
            
        Returns:
            LLMResponse with the generated content
        """
        start_time = time.time()
        try:
            response = self._api_request_with_backoff(api_params)
            latency = time.time() - start_time
            
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None
            
            # Update statistics
            if tokens_used:
                self.stats["tokens_used"] += tokens_used
            
            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                metadata={"latency": latency, "raw_response": response.model_dump()}
            )
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Error generating response: {str(e)}")
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=api_params.get("model", self.model),
                finish_reason="error",
                metadata={"error": str(e), "latency": latency}
            )

    def _generate_stream_enhanced(self, api_params: Dict[str, Any]) -> Iterator[LLMResponse]:
        """
        Enhanced streaming generation with error handling.
        
        Args:
            api_params: API parameters
            
        Yields:
            LLMResponse chunks as they are received
        """
        try:
            stream = self._api_request_with_backoff(api_params)
            for chunk in stream:
                content_delta = chunk.choices[0].delta.content or ""
                if content_delta:
                    yield LLMResponse(
                        content=content_delta,
                        model=chunk.model,
                        metadata={"raw_response": chunk.model_dump()}
                    )
        except Exception as e:
            logger.error(f"Error in stream generation: {str(e)}")
            yield LLMResponse(
                content=f"Error: {str(e)}",
                model=api_params.get("model", self.model),
                finish_reason="error",
                metadata={"error": str(e)}
            )

    def generate_with_tools_enhanced(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: List[Tool],
        temperature: Optional[float] = None,
        role: Optional[Union[AgentRole, str]] = None,
        **kwargs: Any
    ) -> Union[LLMResponse, List[ToolCall]]:
        """
        Enhanced version of generate_with_tools with role-based configuration.
        
        Args:
            prompt: String prompt or list of message dictionaries
            tools: List of Tool objects
            temperature: Override temperature from role config
            role: Override role for this request
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            LLMResponse or List[ToolCall] if tools were called
        """
        # Resolve role if provided as string
        if isinstance(role, str):
            role = AgentRole(role) if role in [r.value for r in AgentRole] else AgentRole.DEFAULT
        
        # Get configuration for the specified role
        config = self.get_model_config(role or self.role)
        
        # Convert string prompt to messages if needed
        if isinstance(prompt, str):
            messages = [
                {"role": "system", "content": self.prepare_system_prompt(role or self.role)},
                {"role": "user", "content": prompt}
            ]
        else:
            messages = prompt
            
        # Optimize messages to fit within token limits
        messages = self.optimize_messages(messages, config.max_tokens)
        
        # Convert our Tool objects to the format OpenAI expects
        openai_tools = [
            {"type": "function", "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }} for tool in tools
        ]

        api_params = {
            "model": self.model,
            "messages": messages,
            "tools": openai_tools,
            "tool_choice": "auto",
            "max_completion_tokens": config.max_tokens,
            # Note: o3 model doesn't support temperature customization
            **kwargs,
        }

        try:
            response = self._api_request_with_backoff(api_params)
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if not tool_calls:
                return LLMResponse(
                    content=response_message.content or "",
                    model=response.model,
                    tokens_used=response.usage.total_tokens if response.usage else None,
                    metadata={"raw_response": response.model_dump()}
                )

            # Convert OpenAI tool calls back to our standardized format
            standardized_tool_calls = []
            for tool_call in tool_calls:
                standardized_tool_calls.append(ToolCall(
                    tool_name=tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                    call_id=tool_call.id
                ))
                
            return standardized_tool_calls
            
        except Exception as e:
            logger.error(f"Error in tool generation: {str(e)}")
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                finish_reason="error",
                metadata={"error": str(e)}
            )

    def save_context(self, key: str, context: Dict[str, Any]) -> None:
        """
        Save context for later use.
        
        Args:
            key: Unique identifier for this context
            context: Context data to save
        """
        self.context_store[key] = context

    def get_context(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve saved context.
        
        Args:
            key: Unique identifier for the context
            
        Returns:
            Saved context data or None if not found
        """
        return self.context_store.get(key)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get provider usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return self.stats.copy()

    def is_available(self) -> bool:
        """
        Check if the provider is available and properly configured.
        
        Returns:
            True if available, False otherwise
        """
        try:
            # Test the API key with a simple request
            self.client.models.list(limit=1)
            return True
        except Exception as e:
            logger.warning(f"Provider not available: {str(e)}")
            return False
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a response using the provider (compatibility with BaseProvider).
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        response = self.generate(messages, **kwargs)
        return response.content
