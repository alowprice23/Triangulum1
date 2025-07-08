#!/usr/bin/env python3
"""
Fix System Startup

This script implements fixes for system startup issues, including:
1. Component initialization order
2. Dependency resolution during startup
3. Configuration validation
4. Startup error handling and reporting
5. Recovery from failed initialization

It enhances the SystemStartupManager to provide more robust startup capabilities.
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("triangulum.fix_system_startup")

# Import Triangulum components
from triangulum_lx.core.engine import TriangulumEngine, ComponentStatus
from triangulum_lx.core.exceptions import TriangulumException, StartupError, ProviderInitError
from triangulum_lx.monitoring.startup_dashboard import StartupDashboard


class EnhancedSystemStartupManager:
    """
    Enhanced manager for system startup and recovery.
    
    This class extends the SystemStartupManager with improved dependency resolution,
    component initialization, and error handling capabilities.
    """
    
    def __init__(self, config_file: str):
        """
        Initialize the enhanced system startup manager.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = self._load_and_validate_config(config_file)
        self.engine = None
        self.dashboard = StartupDashboard()
        self.recovery_attempts = {
            "general": 0,
            "components": {}
        }
        self.max_recovery_attempts = self.config["startup"].get("max_recovery_attempts", 3)
        self._initialized = False
        self._component_dependencies = self._build_dependency_graph()
        self._startup_sequence = self._compute_startup_sequence()
        self._health_check_interval = self.config["startup"].get("health_check_interval", 15)
        self._health_check_timer = None
        self._diagnostics_history = []
    
    def _load_and_validate_config(self, config_file: str) -> Dict[str, Any]:
        """
        Load and validate configuration from file.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            Dictionary with validated configuration
            
        Raises:
            FileNotFoundError: If configuration file not found
            ValueError: If configuration is invalid
        """
        if not os.path.exists(config_file):
            logger.error(f"Configuration file not found: {config_file}")
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            # Validate required sections
            required_sections = ["providers", "agents", "startup", "logging"]
            missing_sections = [section for section in required_sections if section not in config]
            
            if missing_sections:
                logger.warning(f"Missing configuration sections: {missing_sections}")
                for section in missing_sections:
                    config[section] = {}
            
            # Set default values for startup section
            startup_defaults = {
                "parallel": False,
                "retry_count": 1,
                "timeout": 30,
                "auto_recover": True,
                "health_check_interval": 15,
                "max_recovery_attempts": 3,
                "dependency_validation": True,
                "progressive_startup": True
            }
            
            for key, default_value in startup_defaults.items():
                if key not in config["startup"]:
                    config["startup"][key] = default_value
            
            # Validate provider configuration
            if "providers" in config:
                if "default_provider" not in config["providers"]:
                    logger.warning("No default provider specified, using 'local'")
                    config["providers"]["default_provider"] = "local"
                
                # Ensure local provider exists
                if "local" not in config["providers"]:
                    logger.warning("Local provider not configured, adding default configuration")
                    config["providers"]["local"] = {
                        "enabled": True,
                        "models": ["echo"]
                    }
            
            # Validate agent configuration
            if "agents" in config:
                for agent_name, agent_config in config["agents"].items():
                    if "enabled" not in agent_config:
                        logger.warning(f"Agent {agent_name} missing 'enabled' flag, defaulting to False")
                        config["agents"][agent_name]["enabled"] = False
            
            logger.info(f"Configuration loaded and validated from {config_file}")
            return config
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise ValueError(f"Error parsing configuration file: {e}")
        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Build a dependency graph for system components.
        
        Returns:
            Dictionary mapping component names to sets of dependency names
        """
        # Define core component dependencies
        dependencies = {
            # Core engine components
            "config_manager": set(),
            "provider_factory": {"config_manager"},
            "message_bus": {"config_manager"},
            "agent_factory": {"provider_factory", "message_bus"},
            
            # Agent dependencies
            "meta_agent": {"agent_factory"},
            "relationship_analyst": {"agent_factory", "message_bus"},
            "bug_detector": {"agent_factory", "message_bus", "relationship_analyst"},
            "strategy": {"agent_factory", "message_bus", "bug_detector"},
            "implementation": {"agent_factory", "message_bus", "strategy"},
            "verification": {"agent_factory", "message_bus", "implementation"},
            "priority_analyzer": {"agent_factory", "message_bus", "bug_detector"},
            "orchestrator": {"agent_factory", "message_bus", "meta_agent", "relationship_analyst", 
                            "bug_detector", "strategy", "implementation", "verification", "priority_analyzer"}
        }
        
        # Add provider dependencies
        for provider_name in self.config.get("providers", {}):
            if provider_name != "default_provider":
                dependencies[f"{provider_name}_provider"] = {"provider_factory"}
        
        return dependencies
    
    def _compute_startup_sequence(self) -> List[str]:
        """
        Compute an optimal startup sequence based on dependencies.
        
        Returns:
            List of component names in startup order
        """
        # Create a copy of the dependency graph
        graph = {component: deps.copy() for component, deps in self._component_dependencies.items()}
        
        # Track visited and result
        visited = set()
        result = []
        
        # Define topological sort function
        def visit(node):
            if node in visited:
                return
            
            # Process dependencies first
            for dependency in sorted(graph.get(node, set())):
                visit(dependency)
            
            visited.add(node)
            result.append(node)
        
        # Visit all nodes
        for component in sorted(graph.keys()):
            visit(component)
        
        # Filter out disabled components
        enabled_components = []
        for component in result:
            # Core components are always enabled
            if component in {"config_manager", "provider_factory", "message_bus", "agent_factory"}:
                enabled_components.append(component)
                continue
            
            # Check if agent is enabled
            if component in self.config.get("agents", {}):
                if self.config["agents"][component].get("enabled", False):
                    enabled_components.append(component)
                    continue
            
            # Check if provider is enabled
            if component.endswith("_provider"):
                provider_name = component[:-9]  # Remove "_provider" suffix
                if provider_name in self.config.get("providers", {}) and provider_name != "default_provider":
                    if self.config["providers"][provider_name].get("enabled", False):
                        enabled_components.append(component)
                        continue
        
        logger.info(f"Computed startup sequence: {enabled_components}")
        return enabled_components
    
    def _validate_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Validate that all dependencies are satisfied.
        
        Returns:
            Tuple of (is_valid, list of missing dependencies)
        """
        missing_dependencies = []
        
        # Check each enabled component
        for component in self._startup_sequence:
            for dependency in self._component_dependencies.get(component, set()):
                if dependency not in self._startup_sequence:
                    missing_dependencies.append((component, dependency))
        
        is_valid = len(missing_dependencies) == 0
        
        if not is_valid:
            logger.warning(f"Dependency validation failed: {missing_dependencies}")
        
        return is_valid, missing_dependencies
    
    def start_system(self) -> bool:
        """
        Start the system with the loaded configuration.
        
        Returns:
            True if the system started successfully, False otherwise
        """
        logger.info("Starting system...")
        
        # Create dashboard
        self.dashboard = StartupDashboard()
        
        # Start monitoring
        self.dashboard.start_monitoring(update_interval=1.0)
        
        # Validate dependencies if enabled
        if self.config["startup"].get("dependency_validation", True):
            is_valid, missing_dependencies = self._validate_dependencies()
            if not is_valid:
                logger.warning("Dependency validation failed, attempting to fix configuration...")
                self._fix_dependencies(missing_dependencies)
        
        # Create engine
        self.engine = TriangulumEngine(self.config)
        
        # Initialize engine
        if self.config["startup"].get("progressive_startup", True):
            result = self._progressive_initialization()
        else:
            result = self._initialize_with_recovery()
        
        # Check result
        if result:
            logger.info("System started successfully")
            self._initialized = True
            
            # Start health check timer if interval > 0
            if self._health_check_interval > 0:
                self._start_health_check_timer()
        else:
            logger.error("System failed to start")
            self._initialized = False
        
        # Stop monitoring
        self.dashboard.stop_monitoring()
        
        return result
    
    def _progressive_initialization(self) -> bool:
        """
        Initialize components progressively in dependency order.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info("Using progressive initialization...")
        
        # Track initialization status
        initialized_components = set()
        failed_components = set()
        
        # Initialize components in order
        for component in self._startup_sequence:
            logger.info(f"Initializing component: {component}")
            
            # Check if dependencies are initialized
            dependencies = self._component_dependencies.get(component, set())
            missing_deps = [dep for dep in dependencies if dep not in initialized_components]
            
            if missing_deps:
                logger.error(f"Cannot initialize {component}, missing dependencies: {missing_deps}")
                failed_components.add(component)
                continue
            
            # Initialize component
            try:
                if hasattr(self.engine, f"_init_{component}"):
                    init_method = getattr(self.engine, f"_init_{component}")
                    success = init_method()
                    
                    if success:
                        logger.info(f"Component {component} initialized successfully")
                        initialized_components.add(component)
                    else:
                        logger.error(f"Component {component} initialization failed")
                        failed_components.add(component)
                else:
                    logger.warning(f"No initialization method found for {component}")
                    # Assume success if no method exists
                    initialized_components.add(component)
            except Exception as e:
                logger.error(f"Error initializing {component}: {str(e)}")
                failed_components.add(component)
                
                # Try recovery for this component
                if self.config["startup"].get("auto_recover", True):
                    if self._recover_component(component):
                        logger.info(f"Component {component} recovered successfully")
                        initialized_components.add(component)
                        failed_components.remove(component)
        
        # Check if all required components are initialized
        required_components = {"config_manager", "provider_factory", "message_bus", "agent_factory"}
        missing_required = [comp for comp in required_components if comp not in initialized_components]
        
        if missing_required:
            logger.error(f"Missing required components: {missing_required}")
            return False
        
        # Update engine status
        if hasattr(self.engine, "_component_status"):
            for component in initialized_components:
                self.engine._component_status[component] = ComponentStatus.READY
            
            for component in failed_components:
                self.engine._component_status[component] = ComponentStatus.FAILED
        
        # Return success if all components initialized or only optional components failed
        return len(failed_components) == 0 or all(comp not in required_components for comp in failed_components)
    
    def _initialize_with_recovery(self) -> bool:
        """
        Initialize the engine with recovery mechanisms.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # First attempt: standard initialization
        parallel = self.config["startup"].get("parallel", False)
        retry_count = self.config["startup"].get("retry_count", 1)
        
        logger.info(f"Initializing engine (parallel={parallel}, retry_count={retry_count})...")
        result = self.engine.initialize(parallel=parallel, retry_count=retry_count)
        
        # If successful, return immediately
        if result:
            return True
        
        # If auto-recovery is disabled, return the result
        if not self.config["startup"].get("auto_recover", True):
            logger.info("Auto-recovery disabled, not attempting recovery")
            return result
        
        # Try recovery strategies
        max_attempts = self.max_recovery_attempts
        while self.recovery_attempts["general"] < max_attempts:
            self.recovery_attempts["general"] += 1
            logger.info(f"Initialization failed, trying recovery (attempt {self.recovery_attempts['general']}/{max_attempts})...")
            
            # Try different recovery strategies based on attempt number
            if self._try_recovery_strategies():
                return True
            
            # If all strategies failed, give up
            logger.error("All recovery strategies failed")
            break
        
        return False
    
    def _try_recovery_strategies(self) -> bool:
        """
        Try all recovery strategies in sequence.
        
        Returns:
            True if any strategy succeeded, False otherwise
        """
        # Strategy 1: Sequential initialization
        if "strategy1" not in self.recovery_attempts or self.recovery_attempts["strategy1"] != "failed":
            result = self._recovery_strategy_1()
            if result:
                self.recovery_attempts["strategy1"] = "succeeded"
                return True
            else:
                self.recovery_attempts["strategy1"] = "failed"
        
        # Strategy 2: Disable problematic components
        if "strategy2" not in self.recovery_attempts or self.recovery_attempts["strategy2"] != "failed":
            result = self._recovery_strategy_2()
            if result:
                self.recovery_attempts["strategy2"] = "succeeded"
                return True
            else:
                self.recovery_attempts["strategy2"] = "failed"
        
        # Strategy 3: Minimal configuration
        if "strategy3" not in self.recovery_attempts or self.recovery_attempts["strategy3"] != "failed":
            result = self._recovery_strategy_3()
            if result:
                self.recovery_attempts["strategy3"] = "succeeded"
                return True
            else:
                self.recovery_attempts["strategy3"] = "failed"
        
        # Strategy 4: Progressive initialization
        if "strategy4" not in self.recovery_attempts or self.recovery_attempts["strategy4"] != "failed":
            result = self._recovery_strategy_4()
            if result:
                self.recovery_attempts["strategy4"] = "succeeded"
                return True
            else:
                self.recovery_attempts["strategy4"] = "failed"
        
        return False
    
    def _recovery_strategy_1(self) -> bool:
        """
        Recovery strategy 1: Try sequential initialization instead of parallel.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        logger.info("Recovery strategy 1: Trying sequential initialization...")
        
        # If already using sequential initialization, skip this strategy
        if not self.config["startup"].get("parallel", False):
            logger.info("Already using sequential initialization, skipping strategy 1")
            return False
        
        # Try sequential initialization
        retry_count = self.config["startup"].get("retry_count", 1)
        result = self.engine.initialize(parallel=False, retry_count=retry_count)
        
        if result:
            logger.info("Recovery strategy 1 succeeded: Sequential initialization")
            # Update configuration
            self.config["startup"]["parallel"] = False
            self._save_config(self.config_file, self.config)
        else:
            logger.info("Recovery strategy 1 failed: Sequential initialization")
        
        return result
    
    def _recovery_strategy_2(self) -> bool:
        """
        Recovery strategy 2: Disable problematic components and retry.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        logger.info("Recovery strategy 2: Disabling problematic components...")
        
        # Identify failed components
        failed_components = []
        if hasattr(self.engine, '_component_status'):
            failed_components = [
                component for component, status in self.engine._component_status.items()
                if status == ComponentStatus.FAILED
            ]
        
        if not failed_components:
            logger.info("No failed components identified, skipping strategy 2")
            return False
        
        # Create a new configuration with disabled components
        new_config = self._disable_components(failed_components)
        
        # Create a new engine with the modified configuration
        self.engine = TriangulumEngine(new_config)
        
        # Initialize with the new configuration
        retry_count = new_config["startup"].get("retry_count", 1)
        parallel = new_config["startup"].get("parallel", False)
        result = self.engine.initialize(parallel=parallel, retry_count=retry_count)
        
        if result:
            logger.info(f"Recovery strategy 2 succeeded: Disabled components {failed_components}")
            self.recovery_attempts["disabled_components"] = failed_components
            # Update configuration
            self.config = new_config
            self._save_config(self.config_file, self.config)
        else:
            logger.info(f"Recovery strategy 2 failed: Disabled components {failed_components}")
        
        return result
    
    def _recovery_strategy_3(self) -> bool:
        """
        Recovery strategy 3: Use minimal configuration for critical operations.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        logger.info("Recovery strategy 3: Using minimal configuration...")
        
        # Create a minimal configuration
        minimal_config = self._create_minimal_config()
        
        # Create a new engine with the minimal configuration
        self.engine = TriangulumEngine(minimal_config)
        
        # Initialize with the minimal configuration
        result = self.engine.initialize(parallel=False, retry_count=1)
        
        if result:
            logger.info("Recovery strategy 3 succeeded: Minimal configuration")
            # Update configuration
            self.config = minimal_config
            self._save_config(self.config_file, self.config)
        else:
            logger.info("Recovery strategy 3 failed: Minimal configuration")
        
        return result
    
    def _recovery_strategy_4(self) -> bool:
        """
        Recovery strategy 4: Use progressive initialization.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        logger.info("Recovery strategy 4: Using progressive initialization...")
        
        # Enable progressive startup in configuration
        self.config["startup"]["progressive_startup"] = True
        
        # Recompute startup sequence
        self._startup_sequence = self._compute_startup_sequence()
        
        # Try progressive initialization
        result = self._progressive_initialization()
        
        if result:
            logger.info("Recovery strategy 4 succeeded: Progressive initialization")
            # Update configuration
            self._save_config(self.config_file, self.config)
        else:
            logger.info("Recovery strategy 4 failed: Progressive initialization")
        
        return result
    
    def _recover_component(self, component: str) -> bool:
        """
        Attempt to recover a specific component.
        
        Args:
            component: Name of the component to recover
            
        Returns:
            True if recovery was successful, False otherwise
        """
        # Initialize recovery attempts for this component if not already present
        if component not in self.recovery_attempts["components"]:
            self.recovery_attempts["components"][component] = 0
        
        # Check if max attempts reached
        max_attempts = self.config["startup"].get("retry_count", 1)
        if self.recovery_attempts["components"][component] >= max_attempts:
            logger.warning(f"Max recovery attempts reached for component {component}")
            return False
        
        # Increment attempt counter
        self.recovery_attempts["components"][component] += 1
        
        logger.info(f"Attempting to recover component {component} (attempt {self.recovery_attempts['components'][component]}/{max_attempts})...")
        
        try:
            # Try to initialize the component
            if hasattr(self.engine, f"_init_{component}"):
                init_method = getattr(self.engine, f"_init_{component}")
                success = init_method()
                
                if success:
                    logger.info(f"Component {component} recovered successfully")
                    return True
                else:
                    logger.error(f"Component {component} recovery failed")
                    return False
            else:
                logger.warning(f"No initialization method found for {component}")
                return False
        except Exception as e:
            logger.error(f"Error recovering component {component}: {str(e)}")
            return False
    
    def _fix_dependencies(self, missing_dependencies: List[Tuple[str, str]]) -> None:
        """
        Fix missing dependencies in the configuration.
        
        Args:
            missing_dependencies: List of (component, dependency) tuples
        """
        # Group by dependency
        dependency_map = {}
        for component, dependency in missing_dependencies:
            if dependency not in dependency_map:
                dependency_map[dependency] = []
            dependency_map[dependency].append(component)
        
        # Fix each missing dependency
        for dependency, components in dependency_map.items():
            logger.info(f"Fixing missing dependency {dependency} for components {components}")
            
            # Enable the dependency
            if dependency in self.config.get("agents", {}):
                logger.info(f"Enabling agent {dependency}")
                self.config["agents"][dependency]["enabled"] = True
            
            # For provider dependencies
            if dependency.endswith("_provider") and dependency[:-9] in self.config.get("providers", {}):
                provider_name = dependency[:-9]
                logger.info(f"Enabling provider {provider_name}")
                self.config["providers"][provider_name]["enabled"] = True
        
        # Save updated configuration
        self._save_config(self.config_file, self.config)
        
        # Recompute startup sequence
        self._startup_sequence = self._compute_startup_sequence()
    
    def _disable_components(self, components: List[str]) -> Dict[str, Any]:
        """
        Create a new configuration with specified components disabled.
        
        Args:
            components: List of component names to disable
            
        Returns:
            Modified configuration dictionary
        """
        # Create a copy of the configuration
        new_config = self.config.copy()
        
        # Disable components in the "agents" section
        for component in components:
            if component in new_config.get("agents", {}):
                new_config["agents"][component]["enabled"] = False
                logger.info(f"Disabled agent: {component}")
            
            # For provider components
            if component.endswith("_provider") and component[:-9] in new_config.get("providers", {}):
                provider_name = component[:-9]
                new_config["providers"][provider_name]["enabled"] = False
                logger.info(f"Disabled provider: {provider_name}")
        
        # Save updated configuration to a recovery file
        recovery_config_file = "recovery_config.json"
        self._save_config(recovery_config_file, new_config)
        
        return new_config
    
    def _create_minimal_config(self) -> Dict[str, Any]:
        """
        Create a minimal configuration for critical operations.
        
        Returns:
            Minimal configuration dictionary
        """
        # Start with a copy of the original configuration
        minimal_config = self.config.copy()
        
        # Modify providers section
        if "providers" in minimal_config:
            # Enable only the local provider
            for provider_name in minimal_config["providers"]:
                if provider_name != "local" and provider_name != "default_provider":
                    minimal_config["providers"][provider_name]["enabled"] = False
            
            # Ensure local provider is enabled
            if "local" in minimal_config["providers"]:
                minimal_config["providers"]["local"]["enabled"] = True
                minimal_config["providers"]["default_provider"] = "local"
        
        # Modify agents section
        if "agents" in minimal_config:
            # Enable only essential agents
            essential_agents = {"meta", "bug_detector"}
            for agent_name in minimal_config["agents"]:
                if agent_name not in essential_agents:
                    minimal_config["agents"][agent_name]["enabled"] = False
                else:
                    minimal_config["agents"][agent_name]["enabled"] = True
        
        # Modify startup section
        minimal_config["startup"]["parallel"] = False
        minimal_config["startup"]["retry_count"] = 1
        minimal_config["startup"]["auto_recover"] = False
        minimal_config["startup"]["progressive_startup"] = True
        
        # Save minimal configuration to a file
        minimal_config_file = "minimal_config.json"
        self._save_config(minimal_config_file, minimal_config)
        
        return minimal_config
    
    def _save_config(self, config_file: str, config: Dict[str, Any]) -> None:
        """
        Save configuration to file.
        
        Args:
            config_file: Path to save the configuration file
            config: Configuration dictionary to save
        """
        try:
            # Create parent directory if it doesn't exist
            directory = os.path.dirname(config_file)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(config_file, "w") as f:
                json.dump(config, f, indent=4)
            
            logger.info(f"Configuration saved to {config_file}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def _start_health_check_timer(self) -> None:
        """Start the health check timer."""
        import threading
        
        def health_check():
            while self._initialized:
                try:
                    # Run diagnostics
                    diagnostics = self._run_diagnostics()
                    
                    # Store diagnostics history
                    self._diagnostics_history.append({
                        "timestamp": time.time(),
                        "diagnostics": diagnostics
                    })
                    
                    # Keep only the last 10 diagnostics
                    if len(self._diagnostics_history) > 10:
                        self._diagnostics_history.pop(0)
                    
                    # Check for issues
                    if not diagnostics.get("overall_health", False):
                        logger.warning("Health check detected issues")
                        self._handle_health_issues(diagnostics)
                    
                except Exception as e:
                    logger.error(f"Error in health check: {str(e)}")
                
                # Sleep for the interval
                time.sleep(self._health_check_interval)
        
        # Start health check thread
        self._health_check_timer = threading.Thread(target=health_check, daemon=True)
        self._health_check_timer.start()
        logger.info(f"Health check timer started with interval {self._health_check_interval}s")
    
    def _handle_health_issues(self, diagnostics: Dict[str, Any]) -> None:
        """
        Handle health issues detected by diagnostics.
        
        Args:
            diagnostics: Diagnostics dictionary
        """
        # Check for provider issues
        if "providers" in diagnostics and isinstance(diagnostics["providers"], dict) and "error" in diagnostics["providers"]:
            logger.warning(f"Provider issue detected: {diagnostics['providers']['error']}")
            self._handle_provider_issues(diagnostics["providers"])
        
        # Check for agent issues
        if "agents" in diagnostics and isinstance(diagnostics["agents"], dict) and "error" in diagnostics["agents"]:
            logger.warning(f"Agent issue detected: {diagnostics['agents']['error']}")
            self._handle_agent_issues(diagnostics["agents"])
        
        # Check for component issues
        if "components" in diagnostics and isinstance(diagnostics["components"], dict):
            for component, status in diagnostics["components"].items():
                if status == ComponentStatus.FAILED:
                    logger.warning(f"Component issue detected: {component} is in FAILED state")
                    self._recover_component(component)
    
    def _handle_provider_issues(self, provider_diagnostics: Dict[str, Any]) -> None:
        """
        Handle provider issues.
        
        Args:
            provider_diagnostics: Provider diagnostics dictionary
        """
        # Check if any providers are in error state
        if "providers" in provider_diagnostics and isinstance(provider_diagnostics["providers"], dict):
            for provider_name, status in provider_diagnostics["providers"].items():
                if status == "error":
                    logger.warning(f"Provider {provider_name} is in error state, attempting recovery")
                    self._recover_component(f"{provider_name}_provider")
    
    def _handle_agent_issues(self, agent_diagnostics: Dict[str, Any]) -> None:
        """
        Handle agent issues.
        
        Args:
            agent_diagnostics: Agent diagnostics dictionary
        """
        # Check if any agents are in error state
        if "agents" in agent_diagnostics and isinstance(agent_diagnostics["agents"], dict):
            for agent_name, status in agent_diagnostics["agents"].items():
                if status == "error":
                    logger.warning(f"Agent {agent_name} is in error state, attempting recovery")
                    self._recover_component(agent_name)
    
    def _check_provider_health(self) -> Dict[str, Any]:
        """
        Check the health of all providers.
        
        Returns:
            Dictionary with provider health information
        """
        if not self.engine:
            return {"overall_health": False, "error": "No engine instance"}
        
        try:
            # Get provider factory
            provider_factory = None
            if hasattr(self.engine, "_provider_factory"):
                provider_factory = self.engine._provider_factory
            
            if not provider_factory:
                return {"overall_health": False, "error": "No provider factory available"}
            
            # Check each provider
            providers_status = {}
            all_healthy = True
            
            for provider_name in self.config.get("providers", {}):
                if provider_name == "default_provider":
                    continue
                
                if not self.config["providers"][provider_name].get("enabled", False):
                    providers_status[provider_name] = "disabled"
                    continue
                
                # Check if provider exists
                provider = None
                try:
                    if hasattr(provider_factory, "get_provider"):
                        provider = provider_factory.get_provider(provider_name)
                    elif hasattr(provider_factory, "get_or_create_provider"):
                        provider = provider_factory.get_or_create_provider(provider_name)
                except Exception as e:
                    providers_status[provider_name] = "error"
                    all_healthy = False
                    continue
                
                if not provider:
                    providers_status[provider_name] = "not_found"
                    all_healthy = False
                    continue
                
                # Check provider health
                try:
                    if hasattr(provider, "check_health"):
                        health = provider.check_health()
                        providers_status[provider_name] = "healthy" if health else "unhealthy"
                        if not health:
                            all_healthy = False
                    else:
                        # Assume healthy if no health check method
                        providers_status[provider_name] = "assumed_healthy"
                except Exception as e:
                    providers_status[provider_name] = "error"
                    all_healthy = False
            
            return {
                "overall_health": all_healthy,
                "providers": providers_status
            }
            
        except Exception as e:
            logger.error(f"Error checking provider health: {str(e)}")
            return {
                "overall_health": False,
                "error": f"Error checking provider health: {str(e)}"
            }
    
    def _check_agent_health(self) -> Dict[str, Any]:
        """
        Check the health of all agents.
        
        Returns:
            Dictionary with agent health information
        """
        if not self.engine:
            return {"overall_health": False, "error": "No engine instance"}
        
        try:
            # Get agent factory
            agent_factory = None
            if hasattr(self.engine, "_agent_factory"):
                agent_factory = self.engine._agent_factory
            
            if not agent_factory:
                return {"overall_health": False, "error": "No agent factory available"}
            
            # Check each agent
            agents_status = {}
            all_healthy = True
            
            for agent_name in self.config.get("agents", {}):
                if not self.config["agents"][agent_name].get("enabled", False):
                    agents_status[agent_name] = "disabled"
                    continue
                
                # Check if agent exists
                agent = None
                try:
                    if hasattr(agent_factory, "get_agent"):
                        agent = agent_factory.get_agent(agent_name)
                    elif hasattr(agent_factory, "get_or_create_agent"):
                        agent = agent_factory.get_or_create_agent(agent_name)
                except Exception as e:
                    agents_status[agent_name] = "error"
                    all_healthy = False
                    continue
                
                if not agent:
                    agents_status[agent_name] = "not_found"
                    all_healthy = False
                    continue
                
                # Check agent health
                try:
                    if hasattr(agent, "check_health"):
                        health = agent.check_health()
                        agents_status[agent_name] = "healthy" if health else "unhealthy"
                        if not health:
                            all_healthy = False
                    else:
                        # Assume healthy if no health check method
                        agents_status[agent_name] = "assumed_healthy"
                except Exception as e:
                    agents_status[agent_name] = "error"
                    all_healthy = False
            
            return {
                "overall_health": all_healthy,
                "agents": agents_status
            }
            
        except Exception as e:
            logger.error(f"Error checking agent health: {str(e)}")
            return {
                "overall_health": False,
                "error": f"Error checking agent health: {str(e)}"
            }
    
    def _run_diagnostics(self) -> Dict[str, Any]:
        """
        Run system diagnostics.
        
        Returns:
            Dictionary with diagnostics results
        """
        if not self.engine:
            return {"overall_health": False, "error": "No engine instance"}
        
        try:
            # Get component status
            component_status = {}
            if hasattr(self.engine, "_component_status"):
                component_status = self.engine._component_status
            
            # Check provider health
            provider_health = self._check_provider_health()
            
            # Check agent health
            agent_health = self._check_agent_health()
            
            # Determine overall health
            overall_health = (
                provider_health.get("overall_health", False) and
                agent_health.get("overall_health", False) and
                all(status == ComponentStatus.READY for component, status in component_status.items())
            )
            
            # Create diagnostics result
            diagnostics = {
                "overall_health": overall_health,
                "components": component_status,
                "providers": provider_health,
                "agents": agent_health,
                "timestamp": time.time()
            }
            
            return diagnostics
            
        except Exception as e:
            logger.error(f"Error running diagnostics: {str(e)}")
            return {
                "overall_health": False,
                "error": f"Error running diagnostics: {str(e)}"
            }


def shutdown_system(manager):
    """
    Shutdown the system gracefully.
    
    Args:
        manager: SystemStartupManager instance
    """
    if manager:
        logger.info("Shutting down system...")
        manager.shutdown_system()


def main():
    """
    Main entry point for the system startup fix.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Fix system startup issues")
    parser.add_argument("--config", "-c", default="config/triangulum_config.json",
                       help="Path to configuration file")
    parser.add_argument("--log-level", "-l", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Logging level")
    parser.add_argument("--run-tests", "-t", action="store_true",
                       help="Run system startup tests after fixing")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Run in interactive mode")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    try:
        # Create enhanced startup manager
        logger.info(f"Creating enhanced startup manager with config: {args.config}")
        manager = EnhancedSystemStartupManager(args.config)
        
        # Start system
        logger.info("Starting system with enhanced startup manager...")
        result = manager.start_system()
        
        if not result:
            logger.error("System failed to start with enhanced startup manager")
            return 1
        
        logger.info("System started successfully with enhanced startup manager")
        
        # Run tests if requested
        if args.run_tests:
            logger.info("Running system startup tests...")
            from run_system_startup_tests import run_tests
            test_result = run_tests(verbose=True)
            
            if test_result != 0:
                logger.error("System startup tests failed")
                shutdown_system(manager)
                return 1
            
            logger.info("System startup tests passed")
        
        # Interactive mode
        if args.interactive:
            logger.info("Running in interactive mode, press Ctrl+C to exit")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
        
        # Shutdown system
        shutdown_system(manager)
        return 0
        
    except Exception as e:
        logger.error(f"Error during system startup: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
