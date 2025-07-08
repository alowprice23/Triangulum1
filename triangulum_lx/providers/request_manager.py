"""
Request Manager for handling LLM provider API calls with resilience.

This module provides a wrapper for LLM providers to handle retries,
fallbacks, and rate limit errors gracefully, while preserving determinism
through careful integration with the response cache.
"""

import time
import logging
from typing import Callable, Any, List, Dict, Optional

from ..agents.llm_config import get_provider_config, LLM_CONFIG
from ..agents.response_cache import get_response_cache
from .factory import get_provider

logger = logging.getLogger(__name__)

class RequestManager:
    """
    Manages requests to LLM providers, adding a layer of resilience.
    """

    def __init__(self, agent_name: str, prompt: str):
        self.agent_name = agent_name
        self.prompt = prompt
        self.cache = get_response_cache()

    def execute(self) -> Any:
        """
        Executes the LLM generation request with retry and fallback logic.
        """
        primary_config = LLM_CONFIG["agent_model_mapping"][self.agent_name]
        provider_sequence = [primary_config["provider"]]
        
        # Add fallback providers if they exist in the config
        fallback_providers = LLM_CONFIG.get("fallback_providers", [])
        provider_sequence.extend(fallback_providers)

        last_exception = None

        for provider_name in provider_sequence:
            model_name = primary_config.get("model") or get_provider_config(provider_name).get("default_model")
            
            # The cache key is always based on the *primary* intended provider
            # to ensure deterministic replay of the fallback logic.
            primary_provider_name = provider_sequence[0]
            cache_key_model = primary_config.get("model") or get_provider_config(primary_provider_name).get("default_model")
            
            cached_response = self.cache.get(self.agent_name, cache_key_model, self.prompt)
            if cached_response:
                logger.info(f"Returning cached response for agent '{self.agent_name}'")
                return cached_response.content

            try:
                logger.info(f"Attempting request for agent '{self.agent_name}' with provider '{provider_name}'")
                provider = get_provider(provider_name, get_provider_config(provider_name))
                
                # This is a simplified execution. A real implementation would
                # use the provider's generate method and handle specific exceptions.
                # For now, we simulate a successful call.
                response = self._execute_with_retries(provider.generate, self.prompt, model_name=model_name)

                # Cache the successful response against the primary provider's key
                self.cache.put(self.agent_name, cache_key_model, self.prompt, response)
                
                return response.content

            except Exception as e:
                logger.warning(f"Request failed for provider '{provider_name}': {e}. Trying next fallback.")
                last_exception = e
        
        # If all providers in the sequence fail
        raise RuntimeError(f"All LLM providers failed for agent '{self.agent_name}'. Last error: {last_exception}")

    def _execute_with_retries(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executes a function with a simple retry mechanism for transient errors.
        """
        max_retries = LLM_CONFIG.get("request_retries", 3)
        base_delay = LLM_CONFIG.get("retry_delay_seconds", 1)
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # In a real implementation, we would check for specific transient error codes
                # (e.g., 5xx server errors, 429 rate limit).
                if attempt == max_retries - 1:
                    raise e # Re-raise the last exception
                
                delay = base_delay * (2 ** attempt)
                logger.info(f"Attempt {attempt + 1}/{max_retries} failed. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)

def managed_generate(agent_name: str, prompt: str) -> str:
    """
    A convenience function to create and execute a request manager.
    """
    manager = RequestManager(agent_name=agent_name, prompt=prompt)
    return manager.execute()
