import os
from typing import Dict, Any, List, Optional

# Default configuration that can be overridden by environment variables
# or a dedicated configuration file.

DEFAULT_PROVIDER = "openai"

LLM_CONFIG: Dict[str, Any] = {
    "default_provider": os.getenv("TRI_DEFAULT_PROVIDER", DEFAULT_PROVIDER),
    
    "providers": {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "default_model": "o3",
            "models": {
                "o3": { "reasoning_power": 1.5 },
                "gpt-4o-mini": { "reasoning_power": 1.0 },
                "gpt-4o": { "reasoning_power": 1.2 }
            }
        },
        "anthropic": {
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "default_model": "claude-3-haiku-20240307",
            "models": {
                "claude-3-haiku-20240307": { "reasoning_power": 0.9 },
                "claude-3-opus-20240229": { "reasoning_power": 1.3 }
            }
        },
        "groq": {
            "api_key": os.getenv("GROQ_API_KEY"),
            "default_model": "llama3-8b-8192",
            "models": {
                "llama3-8b-8192": { "reasoning_power": 0.8 }
            }
        },
        "openrouter": {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "default_model": "openai/gpt-4o-mini",
            "models": {
                "openai/gpt-4o-mini": { "reasoning_power": 1.0 }
            }
        },
        "ollama": {
            "api_key": None,  # Ollama doesn't use API keys
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "default_model": "llama3",
            "models": {
                "llama3": { "reasoning_power": 0.8 },
                "codellama": { "reasoning_power": 0.9 },
                "mistral": { "reasoning_power": 0.7 }
            }
        },
        "lmstudio": {
            "api_key": None,  # LM Studio doesn't use API keys
            "base_url": os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234"),
            "default_model": "local-model",
            "models": {
                "local-model": { "reasoning_power": 0.8 }
            }
        },
    },

    "agent_model_mapping": {
        "Observer": {
            "provider": os.getenv("TRI_OBSERVER_PROVIDER", DEFAULT_PROVIDER),
            "model": os.getenv("TRI_OBSERVER_MODEL"), # Falls back to provider default if None
        },
        "Analyst": {
            "provider": os.getenv("TRI_ANALYST_PROVIDER", DEFAULT_PROVIDER),
            "model": os.getenv("TRI_ANALYST_MODEL"),
        },
        "Verifier": {
            "provider": os.getenv("TRI_VERIFIER_PROVIDER", DEFAULT_PROVIDER),
            "model": os.getenv("TRI_VERIFIER_MODEL"),
        },
    },
    
    "generation_params": {
        "temperature": 0.0,
        "max_tokens": 2048,
    },

    "resilience": {
        "fallback_providers": ["openai", "anthropic"], # Order matters
        "request_retries": 3,
        "retry_delay_seconds": 1,
    },

    "routing_rules": {
        "agent_overrides": {
            "Analyst": { "provider": "openai", "model": "gpt-4o" }
        },
        "task_rules": [
            {
                "keywords": ["summarize", "compress", "explain"],
                "provider": "groq",
                "model": "llama3-8b-8192"
            },
            {
                "keywords": ["generate_code", "patch", "fix", "implement"],
                "provider": "anthropic",
                "model": "claude-3-opus-20240229"
            }
        ],
        "hybrid_strategies": [
            {
                "condition": "local_available",
                "keywords": ["simple", "quick", "draft"],
                "local_provider": "ollama",
                "local_model": "llama3",
                "fallback_provider": "groq",
                "fallback_model": "llama3-8b-8192"
            }
        ]
    }
}

def get_provider_config(provider_name: str) -> Optional[Dict[str, Any]]:
    """Returns the configuration for a specific provider."""
    return LLM_CONFIG.get("providers", {}).get(provider_name)

def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """
    Returns the model configuration for a specific agent role.
    Falls back to the default provider if a specific mapping is not found.
    """
    mapping = LLM_CONFIG.get("agent_model_mapping", {})
    agent_specific_config = mapping.get(agent_name)

    if not agent_specific_config:
        return {
            "provider": LLM_CONFIG["default_provider"],
            "model": None, # Will use the provider's default
        }
    
    return agent_specific_config
