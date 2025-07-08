"""
Local model providers for Triangulum LX.

This module provides support for locally-hosted LLM models via Ollama
and LM Studio, allowing hybrid strategies that combine local and cloud models.
"""

import json
import time
import requests
from typing import List, Dict, Any, Optional, Union, Iterator

from .base import LLMProvider, LLMResponse, Tool, ToolCall, BaseProvider

class OllamaProvider(LLMProvider):
    """
    An LLMProvider for interacting with locally-hosted Ollama models.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        # Ollama doesn't use API keys, so we pass None
        super().__init__(api_key=None, model=model)
        self.base_url = base_url.rstrip('/')

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = 2048,
        stream: bool = False,
        **kwargs: Any
    ) -> Union[LLMResponse, Iterator[LLMResponse]]:
        self._ensure_deterministic(temperature)

        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or -1,
            }
        }

        if stream:
            return self._generate_stream(payload)
        else:
            return self._generate_non_stream(payload)

    def _generate_non_stream(self, payload: Dict[str, Any]) -> LLMResponse:
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        latency = time.time() - start_time
        result = response.json()
        
        content = result.get("message", {}).get("content", "")
        
        return LLMResponse(
            content=content,
            model=self.model,
            latency=latency,
            tokens_used=result.get("eval_count"),  # Ollama provides token counts
            cost=0.0,  # Local models are free
            raw_response=result
        )

    def _generate_stream(self, payload: Dict[str, Any]) -> Iterator[LLMResponse]:
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    if chunk.get("message", {}).get("content"):
                        yield LLMResponse(
                            content=chunk["message"]["content"],
                            model=self.model,
                            cost=0.0,
                            raw_response=chunk
                        )
                except json.JSONDecodeError:
                    continue

    def generate_with_tools(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: List[Tool],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Union[LLMResponse, List[ToolCall]]:
        # Ollama models typically don't support function calling natively
        # For now, we'll return a regular text response
        # In a more sophisticated implementation, we could use prompt engineering
        # to simulate tool calling behavior
        
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}" for tool in tools
        ])
        
        enhanced_prompt = f"{prompt}\n\nAvailable tools:\n{tool_descriptions}"
        
        return self.generate(enhanced_prompt, temperature=temperature, **kwargs)


class LMStudioProvider(LLMProvider):
    """
    An LLMProvider for interacting with LM Studio's local API server.
    """

    def __init__(self, base_url: str = "http://localhost:1234", model: str = "local-model"):
        super().__init__(api_key=None, model=model)
        self.base_url = base_url.rstrip('/')

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = 2048,
        stream: bool = False,
        **kwargs: Any
    ) -> Union[LLMResponse, Iterator[LLMResponse]]:
        self._ensure_deterministic(temperature)

        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if stream:
            return self._generate_stream(payload)
        else:
            return self._generate_non_stream(payload)

    def _generate_non_stream(self, payload: Dict[str, Any]) -> LLMResponse:
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        latency = time.time() - start_time
        result = response.json()
        
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        tokens_used = result.get("usage", {}).get("total_tokens")
        
        return LLMResponse(
            content=content,
            model=self.model,
            latency=latency,
            tokens_used=tokens_used,
            cost=0.0,  # Local models are free
            raw_response=result
        )

    def _generate_stream(self, payload: Dict[str, Any]) -> Iterator[LLMResponse]:
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line and line.startswith(b"data: "):
                try:
                    data = line[6:]  # Remove "data: " prefix
                    if data.strip() == b"[DONE]":
                        break
                    chunk = json.loads(data.decode('utf-8'))
                    content_delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content_delta:
                        yield LLMResponse(
                            content=content_delta,
                            model=self.model,
                            cost=0.0,
                            raw_response=chunk
                        )
                except json.JSONDecodeError:
                    continue

    def generate_with_tools(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: List[Tool],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Union[LLMResponse, List[ToolCall]]:
        # LM Studio follows OpenAI API format, so we can try to use tools if supported
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
            
        # Convert tools to OpenAI format
        openai_tools = [
            {"type": "function", "function": tool.dict()} for tool in tools
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": openai_tools,
            "tool_choice": "auto",
            "temperature": temperature,
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            
            response_message = result.get("choices", [{}])[0].get("message", {})
            tool_calls = response_message.get("tool_calls")

            if not tool_calls:
                return LLMResponse(
                    content=response_message.get("content", ""),
                    model=self.model,
                    cost=0.0,
                    raw_response=result
                )

            # Convert to standardized format
            standardized_tool_calls = []
            for tool_call in tool_calls:
                standardized_tool_calls.append(ToolCall(
                    id=tool_call.get("id", ""),
                    function_name=tool_call.get("function", {}).get("name", ""),
                    arguments=json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                ))
                
            return standardized_tool_calls
            
        except (requests.RequestException, KeyError):
            # Fallback to regular generation if tools aren't supported
            return self.generate(prompt, temperature=temperature, **kwargs)


class LocalProvider(BaseProvider):
    """Local LLM provider for testing and offline development."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the local provider.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.name = "local"
        self.model = self.config.get("model", "local-test-model")
    
    def is_available(self) -> bool:
        """Check if the local provider is available.
        
        Returns:
            Always True for local provider
        """
        return True
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a response using the local provider.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        # Simple local response for testing
        if not messages:
            return "No messages provided."
        
        last_message = messages[-1].get("content", "")
        
        # Generate a simple response based on the input
        if "error" in last_message.lower():
            return "I understand there's an error. Let me help you debug this issue."
        elif "fix" in last_message.lower():
            return "I'll work on implementing a fix for this issue."
        elif "test" in last_message.lower():
            return "Running tests to verify the implementation."
        else:
            return f"Processing your request: {last_message[:100]}..."
    
    def generate_llm_response(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Generate an LLMResponse object.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse object
        """
        content = self.generate_response(messages, **kwargs)
        
        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=len(content.split()),
            finish_reason="stop",
            metadata={"provider": "local", "test_mode": True}
        )
    
    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = 2048,
        stream: bool = False,
        model_name: Optional[str] = None,
        **kwargs: Any
    ) -> Union[LLMResponse, Iterator[LLMResponse]]:
        """Generate a response using the local provider.
        
        Args:
            prompt: Input prompt (string or list of message dictionaries)
            temperature: Temperature for generation (ignored in local provider)
            max_tokens: Maximum tokens to generate (ignored in local provider)
            stream: Whether to stream the response
            model_name: Model name override (ignored in local provider)
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse object or iterator of LLMResponse objects if streaming
        """
        # Convert prompt to messages format
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
        
        # Generate response using existing method
        response = self.generate_llm_response(messages, **kwargs)
        
        # Handle streaming
        if stream:
            # For local provider, we'll just yield the complete response
            # In a real implementation, this could be chunked
            yield response
        else:
            return response
    
    def generate_with_tools(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: List[Tool],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Union[LLMResponse, List[ToolCall]]:
        """Generate a response with tool support.
        
        Args:
            prompt: Input prompt
            tools: List of available tools
            temperature: Temperature for generation
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse or list of ToolCall objects
        """
        # For local provider, we'll simulate tool usage with a simple response
        tool_names = [tool.name for tool in tools] if tools else []
        
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
        
        # Add tool information to the response
        content = self.generate_response(messages, **kwargs)
        if tool_names:
            content += f"\n\nAvailable tools: {', '.join(tool_names)}"
        
        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=len(content.split()),
            finish_reason="stop",
            metadata={"provider": "local", "test_mode": True, "tools_available": tool_names}
        )
