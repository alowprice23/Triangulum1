"""
LLM Provider Abstraction Layer for Triangulum LX.

This package provides a standardized interface for interacting with various
Large Language Model providers, ensuring that the core system remains
agnostic to the specific backend being used.
"""

from .base import LLMProvider, LLMResponse
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .groq import GroqProvider
from .openrouter import OpenRouterProvider
# Avoid circular imports
# These are imported elsewhere directly from factory

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "OpenAIProvider",
    "AnthropicProvider",
    "GroqProvider",
    "OpenRouterProvider",
]
