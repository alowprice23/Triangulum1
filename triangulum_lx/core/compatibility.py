"""
Backwards Compatibility Layer for Triangulum LX.

This module provides migration utilities and compatibility layers to ensure
that older configurations, APIs, and data formats continue to work as the
system evolves.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class Migration:
    """Represents a single migration step."""
    from_version: str
    to_version: str
    description: str
    migrate_func: Callable[[Dict[str, Any]], Dict[str, Any]]

class VersionManager:
    """Manages version information and compatibility checks."""
    
    CURRENT_VERSION = "2.0.0"
    SUPPORTED_VERSIONS = ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]
    
    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Pad shorter version with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        return 0
    
    @staticmethod
    def is_compatible(version: str) -> bool:
        """Check if a version is compatible with the current system."""
        return version in VersionManager.SUPPORTED_VERSIONS

class ConfigurationMigrator:
    """Handles migration of configuration files between versions."""
    
    def __init__(self):
        self.migrations: List[Migration] = []
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all available migrations."""
        
        # Migration from v1.0.0 to v1.1.0: Add provider abstraction
        self.migrations.append(Migration(
            from_version="1.0.0",
            to_version="1.1.0",
            description="Add provider abstraction layer",
            migrate_func=self._migrate_1_0_to_1_1
        ))
        
        # Migration from v1.1.0 to v1.2.0: Add routing rules
        self.migrations.append(Migration(
            from_version="1.1.0",
            to_version="1.2.0",
            description="Add routing rules and hybrid strategies",
            migrate_func=self._migrate_1_1_to_1_2
        ))
        
        # Migration from v1.2.0 to v2.0.0: Major restructuring
        self.migrations.append(Migration(
            from_version="1.2.0",
            to_version="2.0.0",
            description="Major restructuring with local providers",
            migrate_func=self._migrate_1_2_to_2_0
        ))
    
    def _migrate_1_0_to_1_1(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v1.0.0 to v1.1.0 format."""
        new_config = config.copy()
        
        # Old format had a simple "openai_api_key" field
        if "openai_api_key" in config:
            new_config["providers"] = {
                "openai": {
                    "api_key": config["openai_api_key"],
                    "default_model": config.get("model", "gpt-4o-mini")
                }
            }
            new_config.pop("openai_api_key", None)
            new_config.pop("model", None)
        
        new_config["version"] = "1.1.0"
        return new_config
    
    def _migrate_1_1_to_1_2(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v1.1.0 to v1.2.0 format."""
        new_config = config.copy()
        
        # Add routing rules if they don't exist
        if "routing_rules" not in config:
            new_config["routing_rules"] = {
                "agent_overrides": {},
                "task_rules": [],
                "hybrid_strategies": []
            }
        
        # Add reasoning power to existing models
        if "providers" in config:
            for provider_name, provider_config in config["providers"].items():
                if "models" not in provider_config:
                    model_name = provider_config.get("default_model", "unknown")
                    provider_config["models"] = {
                        model_name: {"reasoning_power": 1.0}
                    }
        
        new_config["version"] = "1.2.0"
        return new_config
    
    def _migrate_1_2_to_2_0(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v1.2.0 to v2.0.0 format."""
        new_config = config.copy()
        
        # Add local providers
        if "providers" in config:
            providers = new_config["providers"]
            
            # Add Ollama provider if not present
            if "ollama" not in providers:
                providers["ollama"] = {
                    "api_key": None,
                    "base_url": "http://localhost:11434",
                    "default_model": "llama3",
                    "models": {
                        "llama3": {"reasoning_power": 0.8}
                    }
                }
            
            # Add LM Studio provider if not present
            if "lmstudio" not in providers:
                providers["lmstudio"] = {
                    "api_key": None,
                    "base_url": "http://localhost:1234",
                    "default_model": "local-model",
                    "models": {
                        "local-model": {"reasoning_power": 0.8}
                    }
                }
        
        # Add resilience configuration
        if "resilience" not in config:
            new_config["resilience"] = {
                "fallback_providers": ["openai", "anthropic"],
                "request_retries": 3,
                "retry_delay_seconds": 1
            }
        
        new_config["version"] = "2.0.0"
        return new_config
    
    def migrate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a configuration to the latest version."""
        current_version = config.get("version", "1.0.0")
        
        if current_version == VersionManager.CURRENT_VERSION:
            return config
        
        # Find migration path
        migrated_config = config.copy()
        
        while migrated_config.get("version", "1.0.0") != VersionManager.CURRENT_VERSION:
            current_ver = migrated_config.get("version", "1.0.0")
            
            # Find next migration
            next_migration = None
            for migration in self.migrations:
                if migration.from_version == current_ver:
                    next_migration = migration
                    break
            
            if not next_migration:
                logger.warning(f"No migration path found from version {current_ver}")
                break
            
            logger.info(f"Migrating config from {next_migration.from_version} to {next_migration.to_version}: {next_migration.description}")
            migrated_config = next_migration.migrate_func(migrated_config)
        
        return migrated_config

class APICompatibilityLayer:
    """Provides backwards compatibility for API interfaces."""
    
    @staticmethod
    def legacy_provider_interface(provider_name: str, **kwargs) -> Any:
        """Provides compatibility for the old provider interface."""
        from ..providers.factory import get_provider
        from ..agents.llm_config import get_provider_config
        
        # Handle legacy parameter names
        legacy_mapping = {
            "api_key": "api_key",
            "model_name": "model",
            "temperature": "temperature",
            "max_length": "max_tokens"  # Old parameter name
        }
        
        mapped_kwargs = {}
        for old_key, new_key in legacy_mapping.items():
            if old_key in kwargs:
                mapped_kwargs[new_key] = kwargs[old_key]
        
        # Get provider with legacy parameters
        provider_config = get_provider_config(provider_name)
        return get_provider(provider_name, {**provider_config, **mapped_kwargs})
    
    @staticmethod
    def legacy_response_format(response: Any) -> Dict[str, Any]:
        """Convert new response format to legacy format."""
        if hasattr(response, 'content'):
            return {
                "text": response.content,
                "model": getattr(response, 'model', 'unknown'),
                "usage": {
                    "total_tokens": getattr(response, 'tokens_used', 0),
                    "cost": getattr(response, 'cost', 0.0)
                }
            }
        return {"text": str(response), "model": "unknown", "usage": {}}

class DataFormatMigrator:
    """Handles migration of data files and cache formats."""
    
    @staticmethod
    def migrate_cache_format(cache_file: Path) -> bool:
        """Migrate old cache format to new format."""
        try:
            if not cache_file.exists():
                return True
            
            # Read old format
            with open(cache_file, 'r') as f:
                old_data = json.load(f)
            
            # Check if migration is needed
            if "version" in old_data and old_data["version"] == "2.0.0":
                return True  # Already new format
            
            # Migrate to new format
            new_data = {
                "version": "2.0.0",
                "cache_entries": {},
                "metadata": {
                    "created_at": old_data.get("created_at"),
                    "last_updated": old_data.get("last_updated")
                }
            }
            
            # Migrate cache entries
            if "entries" in old_data:
                for key, value in old_data["entries"].items():
                    # Old format: key was just prompt hash
                    # New format: key includes agent and model info
                    if isinstance(value, str):
                        new_data["cache_entries"][key] = {
                            "content": value,
                            "model": "unknown",
                            "timestamp": old_data.get("last_updated")
                        }
                    else:
                        new_data["cache_entries"][key] = value
            
            # Write new format
            backup_file = cache_file.with_suffix('.bak')
            cache_file.rename(backup_file)
            
            with open(cache_file, 'w') as f:
                json.dump(new_data, f, indent=2)
            
            logger.info(f"Migrated cache file {cache_file} (backup saved as {backup_file})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate cache file {cache_file}: {e}")
            return False

def ensure_backwards_compatibility(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Main function to ensure backwards compatibility for the entire system.
    
    This function should be called during system initialization to handle
    any necessary migrations.
    """
    logger.info("Checking backwards compatibility...")
    
    migrator = ConfigurationMigrator()
    
    # Migrate configuration if needed
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            original_version = config.get("version", "1.0.0")
            migrated_config = migrator.migrate_config(config)
            
            if migrated_config.get("version") != original_version:
                # Backup original
                backup_path = config_path.with_suffix('.bak')
                config_path.rename(backup_path)
                
                # Save migrated version
                with open(config_path, 'w') as f:
                    json.dump(migrated_config, f, indent=2)
                
                logger.info(f"Configuration migrated from {original_version} to {migrated_config.get('version')}")
                logger.info(f"Original backed up to {backup_path}")
            
            return migrated_config
            
        except Exception as e:
            logger.error(f"Failed to migrate configuration: {e}")
            return {}
    
    logger.info("Backwards compatibility check complete.")
    return {}

# Decorator for marking deprecated functions
def deprecated(reason: str = "This function is deprecated"):
    """Decorator to mark functions as deprecated."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.warning(f"DEPRECATED: {func.__name__} - {reason}")
            return func(*args, **kwargs)
        wrapper.__doc__ = f"DEPRECATED: {reason}\n\n{func.__doc__}"
        return wrapper
    return decorator
