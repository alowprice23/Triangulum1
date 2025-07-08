"""
Concrete implementation of the LLMProvider for OpenAI models.
"""

import os
import time
import json
import asyncio
from typing import List, Dict, Any, Optional, Union, Iterator

from openai import OpenAI
from .base import LLMProvider, LLMResponse

class OpenAIProvider(LLMProvider):
    """
    An LLMProvider for interacting with OpenAI's API.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "o3"):
        super().__init__()  # Adjusted to not pass any arguments
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError("OpenAI API key not provided or found in environment variables.")
        self.client = OpenAI(api_key=self.api_key)

    def _ensure_deterministic(self, temperature: float) -> None:
        """Ensure deterministic behavior for low temperatures."""
        # This is a placeholder - in practice you might want to log warnings
        # or adjust parameters for deterministic behavior
        pass

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = 2048,
        stream: bool = False,
        model_name: Optional[str] = None,
        **kwargs: Any
    ) -> Union[LLMResponse, Iterator[LLMResponse]]:
        self._ensure_deterministic(temperature)

        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        api_params = {
            "model": model_name or self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs,
        }

        if api_params["model"] == "o3":
            api_params["max_completion_tokens"] = max_tokens
            api_params["temperature"] = 1.0
        else:
            api_params["max_tokens"] = max_tokens

        if stream:
            return self._generate_stream(api_params)
        else:
            return self._generate_non_stream(api_params)

    def _generate_non_stream(self, api_params: Dict[str, Any]) -> LLMResponse:
        start_time = time.time()
        response = self.client.chat.completions.create(**api_params)
        latency = time.time() - start_time
        
        content = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else None
        
        return LLMResponse(
            content=content,
            model=response.model,
            latency=latency,
            tokens_used=tokens_used,
            raw_response=response.model_dump()
        )

    def _generate_stream(self, api_params: Dict[str, Any]) -> Iterator[LLMResponse]:
        stream = self.client.chat.completions.create(**api_params)
        for chunk in stream:
            content_delta = chunk.choices[0].delta.content or ""
            if content_delta:
                yield LLMResponse(
                    content=content_delta,
                    model=chunk.model,
                    raw_response=chunk.model_dump()
                )

    def generate_with_tools(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: List[Any], # Using Any to avoid circular import with base.Tool
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Union[LLMResponse, List[Any]]:
        self._ensure_deterministic(temperature)

        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
            
        # Convert our Tool objects to the format OpenAI expects
        openai_tools = [
            {"type": "function", "function": tool.dict()} for tool in tools
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
            temperature=temperature,
            **kwargs,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if not tool_calls:
            return LLMResponse(
                content=response_message.content or "",
                model=response.model,
                raw_response=response.model_dump()
            )

        # Convert OpenAI tool calls back to our standardized format
        from .base import ToolCall # Local import to avoid circular dependency
        standardized_tool_calls = []
        for tool_call in tool_calls:
            standardized_tool_calls.append(ToolCall(
                id=tool_call.id,
                function_name=tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments)
            ))
            
        return standardized_tool_calls

    async def generate_async(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = 2048,
        model_name: Optional[str] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Async version of generate method."""
        # For now, we'll run the sync method in a thread pool
        # In a real implementation, you'd use the async OpenAI client
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.generate(prompt, temperature, max_tokens, False, model_name, **kwargs)
        )
