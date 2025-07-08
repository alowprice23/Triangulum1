#!/usr/bin/env python3
"""
Provider Factory

Factory for creating and managing LLM provider instances.
Handles provider discovery, configuration, and instantiation.
"""

import logging
import traceback
from typing import Dict, List, Any, Optional, Type, Set, Callable
from pathlib import Path
import concurrent.futures
import time

from .base import BaseProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .groq import GroqProvider
from .openrouter import OpenRouterProvider
from .local import LocalProvider
from ..core.exceptions import ProviderInitError, ConfigurationError

logger = logging.getLogger(__name__)


class ProviderStatus:
    """Status of a provider."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    READY = "ready"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class ProviderFactory:
    """Factory for creating and managing LLM providers."""
    
    # Registry of available provider classes
    PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'groq': GroqProvider,
        'openrouter': OpenRouterProvider,
        'local': LocalProvider,
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the provider factory.
        
        Args:
            config: Optional configuration dictionary for all providers
        """
        self.active_providers: Dict[str, BaseProvider] = {}
        self.provider_configs: Dict[str, Dict[str, Any]] = {}
        self.provider_status: Dict[str, str] = {}
        self.startup_errors: Dict[str, str] = {}
        self.config = config or {}
        
        # Initialize status for all registered providers
        for provider_type in self.PROVIDER_REGISTRY:
            self.provider_status[provider_type] = ProviderStatus.PENDING
        
        logger.info("Provider Factory initialized")
    
    def register_provider(self, name: str, provider_class: Type[BaseProvider]) -> None:
        """
        Register a new provider class.
        
        Args:
            name: Provider name
            provider_class: Provider class
        """
        self.PROVIDER_REGISTRY[name] = provider_class
        self.provider_status[name] = ProviderStatus.PENDING
        logger.info(f"Registered provider: {name}")
    
    def create_provider(
        self, 
        provider_type: str, 
        config: Optional[Dict[str, Any]] = None,
        retry: bool = True,
        timeout: Optional[float] = None
    ) -> BaseProvider:
        """
        Create a provider instance.
        
        Args:
            provider_type: Type of provider to create
            config: Optional configuration dictionary
            retry: Whether to retry if provider creation fails
            timeout: Optional timeout for provider creation
            
        Returns:
            Provider instance
            
        Raises:
            ProviderInitError: If provider creation fails
        """
        if provider_type not in self.PROVIDER_REGISTRY:
            available = list(self.PROVIDER_REGISTRY.keys())
            raise ProviderInitError(
                f"Unsupported provider type: {provider_type}. Available: {available}",
                provider_type
            )
        
        # Mark provider as initializing
        self.provider_status[provider_type] = ProviderStatus.INITIALIZING
        
        provider_class = self.PROVIDER_REGISTRY[provider_type]
        
        # Use provided config or stored config
        provider_config = config or self.provider_configs.get(provider_type, {})
        
        # Set up default timeout if not provided
        if timeout is None:
            timeout = self.config.get("provider_timeout", 30)  # Default 30-second timeout
        
        start_time = time.time()
        max_retries = 3 if retry else 1
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff with max of 10 seconds
                    logger.info(f"Retrying provider {provider_type} creation (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                
                # Check timeout
                if timeout and time.time() - start_time > timeout:
                    raise TimeoutError(f"Provider {provider_type} creation timed out after {timeout} seconds")
                
                # Create the provider
                provider = provider_class(provider_config)
                
                # Verify provider is available
                if not provider.is_available():
                    raise ProviderInitError(
                        f"Provider {provider_type} is not available",
                        provider_type
                    )
                
                # Mark provider as ready
                self.provider_status[provider_type] = ProviderStatus.READY
                logger.info(f"Created provider: {provider_type}")
                return provider
                
            except Exception as e:
                last_error = e
                error_msg = f"Failed to create provider {provider_type}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.startup_errors[provider_type] = error_msg
                self.provider_status[provider_type] = ProviderStatus.FAILED
        
        # If we get here, all retries failed
        error_message = f"Failed to create provider {provider_type} after {max_retries} attempts"
        logger.error(error_message)
        
        raise ProviderInitError(
            error_message,
            provider_type,
            last_error
        )
    
    def get_or_create_provider(
        self, 
        provider_type: str, 
        config: Optional[Dict[str, Any]] = None,
        create_if_missing: bool = True
    ) -> BaseProvider:
        """
        Get existing provider or create new one.
        
        Args:
            provider_type: Type of provider
            config: Optional configuration dictionary
            create_if_missing: Whether to create the provider if it doesn't exist
            
        Returns:
            Provider instance
            
        Raises:
            ProviderInitError: If provider creation fails and create_if_missing is True
        """
        if provider_type in self.active_providers:
            provider = self.active_providers[provider_type]
            # Check if provider is still available
            try:
                if provider.is_available():
                    return provider
                else:
                    logger.warning(f"Provider {provider_type} no longer available, recreating")
                    self.shutdown_provider(provider_type)
            except Exception as e:
                logger.warning(f"Error checking provider {provider_type} availability: {e}")
                self.shutdown_provider(provider_type)
        
        if not create_if_missing:
            raise ProviderInitError(
                f"Provider {provider_type} not found and create_if_missing is False",
                provider_type
            )
        
        provider = self.create_provider(provider_type, config)
        self.active_providers[provider_type] = provider
        return provider
    
    def configure_provider(self, provider_type: str, config: Dict[str, Any]) -> None:
        """
        Configure a provider.
        
        Args:
            provider_type: Provider type
            config: Configuration dictionary
        """
        # Validate the config
        self._validate_provider_config(provider_type, config)
        
        # Store the config
        self.provider_configs[provider_type] = config
        
        # If provider is already active, update its configuration
        if provider_type in self.active_providers:
            try:
                self.active_providers[provider_type].configure(config)
                logger.info(f"Updated configuration for active provider: {provider_type}")
            except Exception as e:
                logger.warning(f"Failed to update configuration for {provider_type}: {e}")
    
    def _validate_provider_config(self, provider_type: str, config: Dict[str, Any]) -> None:
        """
        Validate provider configuration.
        
        Args:
            provider_type: Provider type
            config: Configuration dictionary
            
        Raises:
            ConfigValidationError: If the configuration is invalid
        """
        errors = []
        
        # Check if the provider type is registered
        if provider_type not in self.PROVIDER_REGISTRY:
            errors.append(f"Unknown provider type: {provider_type}")
            
        # Get the provider class
        provider_class = self.PROVIDER_REGISTRY.get(provider_type)
        if provider_class:
            # Check for required configuration keys
            if hasattr(provider_class, 'REQUIRED_CONFIG_KEYS'):
                for key in provider_class.REQUIRED_CONFIG_KEYS:
                    if key not in config:
                        errors.append(f"Missing required configuration key '{key}' for provider {provider_type}")
        
        if errors:
            raise ConfigurationError(
                f"Invalid configuration for provider {provider_type}",
                invalid_sections=errors
            )
    
    def list_available_providers(self) -> List[str]:
        """
        List all available provider types.
        
        Returns:
            List of provider type names
        """
        return list(self.PROVIDER_REGISTRY.keys())
    
    def list_active_providers(self) -> List[str]:
        """
        List all active provider instances.
        
        Returns:
            List of active provider names
        """
        return list(self.active_providers.keys())
    
    def get_provider_info(self, provider_type: str) -> Dict[str, Any]:
        """
        Get information about a provider.
        
        Args:
            provider_type: Provider type
            
        Returns:
            Provider information dictionary
        """
        if provider_type not in self.PROVIDER_REGISTRY:
            return {'error': f'Unknown provider type: {provider_type}'}
        
        provider_class = self.PROVIDER_REGISTRY[provider_type]
        
        info = {
            'name': provider_type,
            'class': provider_class.__name__,
            'module': provider_class.__module__,
            'is_active': provider_type in self.active_providers,
            'has_config': provider_type in self.provider_configs,
            'status': self.provider_status.get(provider_type, ProviderStatus.PENDING)
        }
        
        # Add provider-specific info if available
        if hasattr(provider_class, 'get_provider_info'):
            try:
                provider_info = provider_class.get_provider_info()
                info.update(provider_info)
            except Exception as e:
                info['info_error'] = str(e)
        
        # Add error info if available
        if provider_type in self.startup_errors:
            info['error'] = self.startup_errors[provider_type]
        
        return info
    
    def discover_providers(self, parallel: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Discover available providers and their capabilities.
        
        Args:
            parallel: Whether to discover providers in parallel
            
        Returns:
            Dictionary of provider information
        """
        discovered = {}
        
        # Get the list of provider types
        provider_types = self.list_available_providers()
        
        if parallel:
            # Discover providers in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(provider_types))) as executor:
                # Start discovery tasks
                future_to_provider = {
                    executor.submit(self._discover_provider, provider_type): provider_type
                    for provider_type in provider_types
                }
                
                # Process results as they become available
                for future in concurrent.futures.as_completed(future_to_provider):
                    provider_type = future_to_provider[future]
                    try:
                        info = future.result()
                        discovered[provider_type] = info
                    except Exception as e:
                        discovered[provider_type] = {
                            'error': str(e),
                            'available': False,
                            'status': ProviderStatus.FAILED
                        }
        else:
            # Discover providers sequentially
            for provider_type in provider_types:
                try:
                    info = self._discover_provider(provider_type)
                    discovered[provider_type] = info
                except Exception as e:
                    discovered[provider_type] = {
                        'error': str(e),
                        'available': False,
                        'status': ProviderStatus.FAILED
                    }
        
        logger.info(f"Discovered {len(discovered)} providers")
        return discovered
    
    def _discover_provider(self, provider_type: str) -> Dict[str, Any]:
        """
        Discover information about a specific provider.
        
        Args:
            provider_type: Provider type to discover
            
        Returns:
            Provider information dictionary
        """
        info = self.get_provider_info(provider_type)
        
        # Check if provider is available (has required dependencies, API keys, etc.)
        if provider_type in self.active_providers:
            provider = self.active_providers[provider_type]
            info['available'] = provider.is_available()
        else:
            # Try to create a temporary instance to check availability
            try:
                temp_provider = self.create_provider(provider_type, retry=False)
                info['available'] = temp_provider.is_available()
                # Don't keep the temporary provider
                del temp_provider
            except Exception:
                info['available'] = False
                info['status'] = ProviderStatus.FAILED
        
        return info
    
    def initialize_providers(
        self, 
        provider_types: Optional[List[str]] = None,
        parallel: bool = True,
        timeout: Optional[float] = None
    ) -> Dict[str, bool]:
        """
        Initialize a list of providers.
        
        Args:
            provider_types: List of provider types to initialize (default: all configured providers)
            parallel: Whether to initialize providers in parallel
            timeout: Optional timeout per provider initialization
            
        Returns:
            Dictionary mapping provider types to initialization success status
        """
        # Determine which providers to initialize
        if provider_types is None:
            provider_types = list(self.provider_configs.keys())
        
        results = {}
        
        if parallel:
            # Initialize providers in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(provider_types))) as executor:
                # Start initialization tasks
                future_to_provider = {
                    executor.submit(self._initialize_provider, provider_type, timeout): provider_type
                    for provider_type in provider_types
                }
                
                # Process results as they become available
                for future in concurrent.futures.as_completed(future_to_provider):
                    provider_type = future_to_provider[future]
                    try:
                        success = future.result()
                        results[provider_type] = success
                    except Exception as e:
                        logger.error(f"Error initializing provider {provider_type}: {e}")
                        self.startup_errors[provider_type] = str(e)
                        self.provider_status[provider_type] = ProviderStatus.FAILED
                        results[provider_type] = False
        else:
            # Initialize providers sequentially
            for provider_type in provider_types:
                try:
                    success = self._initialize_provider(provider_type, timeout)
                    results[provider_type] = success
                except Exception as e:
                    logger.error(f"Error initializing provider {provider_type}: {e}")
                    self.startup_errors[provider_type] = str(e)
                    self.provider_status[provider_type] = ProviderStatus.FAILED
                    results[provider_type] = False
        
        return results
    
    def _initialize_provider(self, provider_type: str, timeout: Optional[float] = None) -> bool:
        """
        Initialize a specific provider.
        
        Args:
            provider_type: Provider type to initialize
            timeout: Optional timeout for provider initialization
            
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info(f"Initializing provider: {provider_type}")
        
        try:
            # Skip if already initialized
            if provider_type in self.active_providers:
                if self.provider_status[provider_type] == ProviderStatus.READY:
                    logger.info(f"Provider {provider_type} already initialized")
                    return True
                
                # If provider is in failed state, shut it down first
                if self.provider_status[provider_type] == ProviderStatus.FAILED:
                    self.shutdown_provider(provider_type)
            
            # Get the configuration
            config = self.provider_configs.get(provider_type, {})
            
            # Create the provider
            provider = self.create_provider(provider_type, config, timeout=timeout)
            
            # Store the provider
            self.active_providers[provider_type] = provider
            self.provider_status[provider_type] = ProviderStatus.READY
            
            return True
        except Exception as e:
            error_msg = f"Failed to initialize provider {provider_type}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.startup_errors[provider_type] = error_msg
            self.provider_status[provider_type] = ProviderStatus.FAILED
            return False
    
    def shutdown_provider(self, provider_type: str) -> bool:
        """
        Shutdown a specific provider.
        
        Args:
            provider_type: Provider type to shutdown
            
        Returns:
            True if shutdown successful, False otherwise
        """
        if provider_type not in self.active_providers:
            return False
        
        try:
            provider = self.active_providers[provider_type]
            if hasattr(provider, 'shutdown'):
                provider.shutdown()
            
            del self.active_providers[provider_type]
            self.provider_status[provider_type] = ProviderStatus.SHUTDOWN
            logger.info(f"Shutdown provider: {provider_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error shutting down provider {provider_type}: {e}")
            return False
    
    def shutdown_all_providers(self) -> Dict[str, bool]:
        """
        Shutdown all active providers.
        
        Returns:
            Dictionary mapping provider types to shutdown success status
        """
        provider_types = list(self.active_providers.keys())
        results = {}
        
        for provider_type in provider_types:
            results[provider_type] = self.shutdown_provider(provider_type)
        
        logger.info("All providers shutdown")
        return results
    
    def get_best_provider(
        self, 
        criteria: Optional[Dict[str, Any]] = None,
        provider_types: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Get the best available provider based on criteria.
        
        Args:
            criteria: Optional criteria for selection (e.g., {'speed': 'fast', 'cost': 'low'})
            provider_types: Optional list of provider types to consider (default: all registered providers)
            
        Returns:
            Best provider name or None if none available
        """
        # Determine which providers to consider
        if provider_types is None:
            provider_types = self.list_available_providers()
        
        available_providers = []
        
        # Check which providers are available
        for provider_type in provider_types:
            # First check if provider is already active
            if provider_type in self.active_providers:
                try:
                    provider = self.active_providers[provider_type]
                    if provider.is_available():
                        available_providers.append(provider_type)
                except Exception:
                    continue
            else:
                # Try to create a temporary provider to check availability
                try:
                    is_available = False
                    
                    # Skip providers with no configuration
                    if provider_type not in self.provider_configs:
                        continue
                    
                    temp_provider = self.create_provider(provider_type, retry=False)
                    is_available = temp_provider.is_available()
                    
                    # Don't keep the temporary provider
                    del temp_provider
                    
                    if is_available:
                        available_providers.append(provider_type)
                except Exception:
                    continue
        
        if not available_providers:
            return None
        
        # Simple selection logic (can be enhanced with more sophisticated criteria)
        if criteria:
            # Prefer providers based on criteria
            if criteria.get('speed') == 'fast' and 'groq' in available_providers:
                return 'groq'
            elif criteria.get('cost') == 'low' and 'local' in available_providers:
                return 'local'
            elif criteria.get('quality') == 'high' and 'openai' in available_providers:
                return 'openai'
        
        # Default preference order
        preference_order = ['openai', 'anthropic', 'groq', 'openrouter', 'local']
        
        for preferred in preference_order:
            if preferred in available_providers:
                return preferred
        
        # Return first available if no preferences match
        return available_providers[0] if available_providers else None
    
    def load_config_file(self, config_path: str) -> bool:
        """
        Load provider configurations from a file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            True if the config was loaded successfully, False otherwise
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_path}")
            return False
        
        try:
            import json
            with open(config_file, 'r') as f:
                configs = json.load(f)
            
            success = True
            for provider_type, config in configs.items():
                if provider_type in self.PROVIDER_REGISTRY:
                    try:
                        self.configure_provider(provider_type, config)
                        logger.info(f"Loaded config for provider: {provider_type}")
                    except Exception as e:
                        logger.error(f"Error configuring provider {provider_type}: {e}")
                        success = False
                else:
                    logger.warning(f"Unknown provider in config: {provider_type}")
                    
            return success
            
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            return False
    
    def save_config_file(self, config_path: str) -> bool:
        """
        Save current provider configurations to a file.
        
        Args:
            config_path: Path to save configuration file
            
        Returns:
            True if the config was saved successfully, False otherwise
        """
        try:
            import json
            with open(config_path, 'w') as f:
                json.dump(self.provider_configs, f, indent=2)
            
            logger.info(f"Saved provider configs to: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config file {config_path}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of all active providers.
        
        Returns:
            Dictionary with health check results
        """
        results = {
            'providers': {},
            'overall_status': 'healthy'
        }
        
        # Check each active provider
        for provider_type, provider in self.active_providers.items():
            provider_health = {
                'status': self.provider_status.get(provider_type, ProviderStatus.PENDING)
            }
            
            try:
                # Check if provider is available
                is_available = provider.is_available()
                provider_health['available'] = is_available
                
                # Check provider-specific health if method exists
                if hasattr(provider, 'health_check'):
                    health_data = provider.health_check()
                    provider_health.update(health_data)
                
                if not is_available:
                    provider_health['status'] = ProviderStatus.FAILED
                    results['overall_status'] = 'degraded'
            except Exception as e:
                provider_health['available'] = False
                provider_health['status'] = ProviderStatus.FAILED
                provider_health['error'] = str(e)
                results['overall_status'] = 'degraded'
            
            results['providers'][provider_type] = provider_health
        
        # Check if any provider is available
        if not any(provider.get('available', False) for provider in results['providers'].values()):
            results['overall_status'] = 'critical'
        
        return results


# Global factory instance
_factory_instance: Optional[ProviderFactory] = None

def get_factory(config: Optional[Dict[str, Any]] = None) -> ProviderFactory:
    """
    Get the global provider factory instance.
    
    Args:
        config: Optional configuration to apply to the factory
        
    Returns:
        Global ProviderFactory instance
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ProviderFactory(config)
    elif config:
        # Update the factory's configuration
        _factory_instance.config.update(config)
    return _factory_instance

def reset_factory() -> None:
    """Reset the global provider factory instance."""
    global _factory_instance
    if _factory_instance:
        _factory_instance.shutdown_all_providers()
    _factory_instance = None

def create_provider(provider_type: str, config: Optional[Dict[str, Any]] = None) -> BaseProvider:
    """
    Convenience function to create a provider.
    
    Args:
        provider_type: Type of provider to create
        config: Optional configuration dictionary
        
    Returns:
        Provider instance
    """
    factory = get_factory()
    return factory.create_provider(provider_type, config)

def get_best_provider(criteria: Optional[Dict[str, Any]] = None) -> Optional[BaseProvider]:
    """
    Convenience function to get the best available provider.
    
    Args:
        criteria: Optional criteria for selection
        
    Returns:
        Best provider instance or None
    """
    factory = get_factory()
    provider_type = factory.get_best_provider(criteria)
    
    if provider_type:
        return factory.get_or_create_provider(provider_type)
    
    return None

def get_provider(provider_type: str, config: Optional[Dict[str, Any]] = None) -> BaseProvider:
    """
    Convenience function to get or create a provider.
    
    Args:
        provider_type: Type of provider to get
        config: Optional configuration dictionary
        
    Returns:
        Provider instance
    """
    factory = get_factory()
    return factory.get_or_create_provider(provider_type, config)
