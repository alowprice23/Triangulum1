"""
Concrete implementation of the LLMProvider for Groq models.
"""

import os
import time
import json
from typing import List, Dict, Any, Optional, Union, Iterator

from groq import Groq
from .base import LLMProvider, LLMResponse

class GroqProvider(LLMProvider):
    """
    An LLMProvider for interacting with Groq's high-speed API.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "llama3-8b-8192"):
        super().__init__(api_key or os.getenv("GROQ_API_KEY"), model)
        if not self.api_key:
            raise ValueError("Groq API key not provided or found in environment variables.")
        self.client = Groq(api_key=self.api_key)

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
                    model=self.model, # Groq stream response doesn't include model
                    raw_response=chunk.model_dump()
                )

    def generate_with_tools(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: List[Any],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Union[LLMResponse, List[Any]]:
        # Groq's API is OpenAI-compatible, so the implementation is similar
        self._ensure_deterministic(temperature)

        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
            
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

        from .base import ToolCall
        standardized_tool_calls = []
        for tool_call in tool_calls:
            standardized_tool_calls.append(ToolCall(
                id=tool_call.id,
                function_name=tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments)
            ))
            
        return standardized_tool_calls
