"""Agent components of the Triangulum system."""

from .llm_config import LLM_CONFIG, get_agent_config, get_provider_config
from .roles import OBSERVER_PROMPT, ANALYST_PROMPT, VERIFIER_PROMPT
from .meta_agent import MetaAgent
from .response_cache import ResponseCache, get_response_cache

from .router import Router

__all__ = [
    'LLM_CONFIG',
    'get_agent_config',
    'get_provider_config',
    'OBSERVER_PROMPT',
    'ANALYST_PROMPT',
    'VERIFIER_PROMPT',
    'MetaAgent',
    'ResponseCache',
    'get_response_cache',
    'Router',
]
