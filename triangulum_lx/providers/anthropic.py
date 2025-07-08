"""
Concrete implementation of the LLMProvider for Anthropic models.
"""

import os
import time
from typing import List, Dict, Any, Optional, Union, Iterator

from anthropic import Anthropic
from .base import LLMProvider, LLMResponse

class AnthropicProvider(LLMProvider):
    """
    An LLMProvider for interacting with Anthropic's API.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307"):
        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"), model)
        if not self.api_key:
            raise ValueError("Anthropic API key not provided or found in environment variables.")
        self.client = Anthropic(api_key=self.api_key)

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
            messages = self._normalize_messages(prompt)

        api_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs,
        }

        if stream:
            return self._generate_stream(api_params)
        else:
            return self._generate_non_stream(api_params)

    def _generate_non_stream(self, api_params: Dict[str, Any]) -> LLMResponse:
        start_time = time.time()
        response = self.client.messages.create(**api_params)
        latency = time.time() - start_time
        
        content = response.content[0].text if response.content else ""
        tokens_used = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else None
        
        return LLMResponse(
            content=content,
            model=response.model,
            latency=latency,
            tokens_used=tokens_used,
            raw_response=response.model_dump()
        )

    def _generate_stream(self, api_params: Dict[str, Any]) -> Iterator[LLMResponse]:
        with self.client.messages.stream(**api_params) as stream:
            for text in stream.text_stream:
                yield LLMResponse(content=text, model=self.model)

    def generate_with_tools(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: List[Any],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Union[LLMResponse, List[Any]]:
        self._ensure_deterministic(temperature)

        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = self._normalize_messages(prompt)
            
        anthropic_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in tools
        ]

        response = self.client.messages.create(
            model=self.model,
            messages=messages,
            tools=anthropic_tools,
            temperature=temperature,
            **kwargs,
        )

        if response.stop_reason == "tool_use":
            from .base import ToolCall
            tool_calls = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        function_name=block.name,
                        arguments=block.input
                    ))
            return tool_calls
        else:
            return LLMResponse(
                content=response.content[0].text if response.content else "",
                model=response.model,
                raw_response=response.model_dump()
            )

    def _normalize_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Normalizes messages to the format expected by Anthropic's API,
        which requires alternating user and assistant roles.
        """
        normalized = []
        if not messages:
            return []

        # Ensure the first message is from a user
        if messages[0]['role'] != 'user':
            # This is a simplification; a more robust solution might prepend a dummy user message
            # or raise an error. For Triangulum's use case, we assume a user prompt starts.
            pass

        last_role = None
        for msg in messages:
            # If the role is the same as the last one, it's not supported by Anthropic.
            # This is a simple handling strategy.
            if msg['role'] == last_role:
                # Merge with the previous message content
                if normalized:
                    normalized[-1]['content'] += f"\\n\\n{msg['content']}"
                    continue
            
            normalized.append(msg)
            last_role = msg['role']
            
        return normalized
