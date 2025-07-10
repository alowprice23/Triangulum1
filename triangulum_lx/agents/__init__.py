"""Agent components of the Triangulum system."""

from .llm_config import LLM_CONFIG, get_agent_config, get_provider_config
from .roles import OBSERVER_PROMPT, ANALYST_PROMPT, VERIFIER_PROMPT
# from .meta_agent import MetaAgent # MetaAgent was removed, functionality merged elsewhere
from .response_cache import ResponseCache, get_response_cache

from .router import Router

__all__ = [
    'LLM_CONFIG',
    'get_agent_config',
    'get_provider_config',
    'OBSERVER_PROMPT',
    'ANALYST_PROMPT',
    'VERIFIER_PROMPT',
    # 'MetaAgent', # MetaAgent was removed
    'ResponseCache',
    'get_response_cache',
    'Router',
]
