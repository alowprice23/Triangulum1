import os
import copy
from typing import Dict, Any, List, Optional, Union

# Global LLM configuration dictionary, initialized as None.
# This will be populated by load_llm_config().
LLM_CONFIG: Optional[Dict[str, Any]] = None

def load_llm_config(main_config_llm_section: Dict[str, Any]) -> Dict[str, Any]:
    """
    Loads LLM configuration from the provided main config section,
    integrating environment variables for overrides and sensitive data.
    """
    global LLM_CONFIG
    
    # Deep copy the llm section from the main config to avoid modifying the original
    cfg = copy.deepcopy(main_config_llm_section)

    # Override default provider with environment variable if set
    cfg["default_provider"] = os.getenv("TRI_DEFAULT_PROVIDER", cfg.get("default_provider", "openai"))

    # Process providers: inject API keys and base URLs from environment variables
    processed_providers: Dict[str, Any] = {}
    for provider_name, provider_details in cfg.get("providers", {}).items():
        pd = copy.deepcopy(provider_details)

        # API Key from environment variable
        api_key_env_var = pd.pop("api_key_env_var", None)
        if api_key_env_var:
            pd["api_key"] = os.getenv(api_key_env_var)

        # Base URL from environment variable, with a fallback to default from config
        base_url_env_var = pd.pop("base_url_env_var", None)
        base_url_default = pd.pop("base_url_default", None)
        if base_url_env_var:
            pd["base_url"] = os.getenv(base_url_env_var, base_url_default)
        elif base_url_default: # If no env var specified, but default exists
             pd["base_url"] = base_url_default

        # For providers like ollama and lmstudio that don't use api_keys explicitly in requests
        if provider_name in ["ollama", "lmstudio"] and "api_key" not in pd:
            pd["api_key"] = None

        processed_providers[provider_name] = pd
    cfg["providers"] = processed_providers

    # Process agent model mapping: override with environment variables
    # The structure in JSON is agent_model_mapping_defaults
    agent_mapping_defaults = cfg.pop("agent_model_mapping_defaults", {})
    processed_agent_mapping: Dict[str, Any] = {}
    for agent_name, defaults in agent_mapping_defaults.items():
        provider_env_var = defaults.get("provider_env_var")
        model_env_var = defaults.get("model_env_var")

        agent_provider = os.getenv(provider_env_var, defaults.get("default_provider", cfg["default_provider"]))
        agent_model = os.getenv(model_env_var, defaults.get("default_model")) # Can be None

        processed_agent_mapping[agent_name] = {
            "provider": agent_provider,
            "model": agent_model # If None, provider's default model will be used later
        }
    cfg["agent_model_mapping"] = processed_agent_mapping

    # Ensure other sections are present, even if empty, to avoid KeyErrors later
    for section in ["generation_params", "resilience", "routing_rules"]:
        if section not in cfg:
            cfg[section] = {}

    LLM_CONFIG = cfg
    return LLM_CONFIG

def get_llm_config() -> Dict[str, Any]:
    """
    Returns the global LLM_CONFIG.
    Raises a RuntimeError if load_llm_config has not been called.
    """
    if LLM_CONFIG is None:
        raise RuntimeError(
            "LLM_CONFIG not initialized. Call load_llm_config() first."
        )
    return LLM_CONFIG

def get_provider_config(provider_name: str) -> Optional[Dict[str, Any]]:
    """Returns the configuration for a specific provider."""
    config = get_llm_config()
    return config.get("providers", {}).get(provider_name)

def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """
    Returns the model configuration for a specific agent role.
    Falls back to the default provider if a specific mapping is not found
    or if the specified provider/model is not fully configured.
    """
    config = get_llm_config()
    mapping = config.get("agent_model_mapping", {})
    agent_specific_config = mapping.get(agent_name)

    if not agent_specific_config or not agent_specific_config.get("provider"):
        # Fallback to default provider if agent-specific provider is missing
        return {
            "provider": config["default_provider"],
            "model": None, # Will use the provider's default model
        }
    
    # If model is specified as None for the agent, it means use that provider's default model.
    # The actual resolution of provider's default model happens in the factory or request manager.
    return {
        "provider": agent_specific_config["provider"],
        "model": agent_specific_config.get("model"), # This can be None
    }

# Example of how this might be initialized at startup:
# import json
# def initialize_system_config():
#     with open("config/triangulum_config.json", "r") as f:
#         main_config = json.load(f)
#     load_llm_config(main_config.get("llm", {}))
#
# if __name__ == "__main__":
#     # This is just for demonstration if you run this file directly
#     # In actual application, initialize_system_config() would be called by the engine.
#     mock_main_config_llm_section = {
#         "default_provider": "openai",
#         "providers": {
#             "openai": {"api_key_env_var": "OPENAI_API_KEY", "default_model": "gpt-4o-mini"},
#             "anthropic": {"api_key_env_var": "ANTHROPIC_API_KEY", "default_model": "claude-3-haiku"},
#             "ollama": {"base_url_env_var": "OLLAMA_BASE_URL", "base_url_default": "http://localhost:11434", "default_model": "llama3"}
#         },
#         "agent_model_mapping_defaults": {
#             "Observer": {"provider_env_var": "TRI_OBSERVER_PROVIDER", "model_env_var": "TRI_OBSERVER_MODEL", "default_provider": "openai"},
#             "Analyst": {"provider_env_var": "TRI_ANALYST_PROVIDER", "model_env_var": "TRI_ANALYST_MODEL", "default_provider": "anthropic", "default_model": "claude-3-opus"}
#         },
#         "generation_params": {"temperature": 0.1},
#         "resilience": {"request_retries": 2}
#     }
#     # Simulate environment variables
#     os.environ["OPENAI_API_KEY"] = "sk-env-openai-key"
#     # os.environ["TRI_ANALYST_PROVIDER"] = "ollama"
#     # os.environ["TRI_ANALYST_MODEL"] = "codellama"
#
#     loaded_config = load_llm_config(mock_main_config_llm_section)
#     print("Loaded LLM Config:", json.dumps(loaded_config, indent=2))
#     print("\nObserver Config:", get_agent_config("Observer"))
#     print("Analyst Config:", get_agent_config("Analyst"))
#     print("UnknownAgent Config:", get_agent_config("UnknownAgent")) # Test fallback
#     print("\nOpenAI Provider Config:", get_provider_config("openai"))
#     print("Ollama Provider Config:", get_provider_config("ollama"))
