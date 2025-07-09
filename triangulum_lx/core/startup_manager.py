"""
System Startup Manager

This module provides the SystemStartupManager class for managing system startup,
including initialization, dependency resolution, recovery, and health monitoring.
It implements recovery strategies for handling startup failures.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Set, Tuple, Union # Removed unused Set, Tuple, Union for now
from pathlib import Path

# Adjusted imports for new location
from .engine import TriangulumEngine, ComponentStatus
from .exceptions import TriangulumException, StartupError
from ..monitoring.startup_dashboard import StartupDashboard

logger = logging.getLogger(__name__)


class SystemStartupManager:
    """
    Manager for system startup and recovery.
    
    This class provides functionality for starting the system, recovering from
    startup failures, and monitoring system health.
    """
    
    def __init__(self, config_file: str):
        """
        Initialize the system startup manager.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = self._load_config(config_file)
        self.engine = None
        self.dashboard = StartupDashboard()
        self.recovery_attempts = {
            "general": 0
        }
        self.max_recovery_attempts = 3
        self._initialized = False
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            Dictionary with configuration
        """
        if not os.path.exists(config_file):
            logger.error(f"Configuration file not found: {config_file}")
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            # Ensure required sections exist
            for section in ["providers", "agents", "startup", "logging"]:
                if section not in config:
                    config[section] = {}
            
            # Set default values if not present
            if "parallel" not in config["startup"]:
                config["startup"]["parallel"] = False
            
            if "retry_count" not in config["startup"]:
                config["startup"]["retry_count"] = 1
            
            if "timeout" not in config["startup"]:
                config["startup"]["timeout"] = 10
            
            if "auto_recover" not in config["startup"]:
                config["startup"]["auto_recover"] = True
            
            logger.info(f"Configuration loaded from {config_file}")
            return config
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise ValueError(f"Error parsing configuration file: {e}")
        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
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
        
        # Create engine
        self.engine = TriangulumEngine(self.config)
        
        # Initialize engine
        result = self._initialize_with_recovery()
        
        # Check result
        if result:
            logger.info("System started successfully")
            self._initialized = True
        else:
            logger.error("System failed to start")
            self._initialized = False
        
        # Stop monitoring
        self.dashboard.stop_monitoring()
        
        return result
    
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
            if "strategy1" not in self.recovery_attempts or self.recovery_attempts["strategy1"] != "failed":
                result = self._recovery_strategy_1()
                if result:
                    self.recovery_attempts["strategy1"] = "succeeded"
                    return True
                else:
                    self.recovery_attempts["strategy1"] = "failed"
            
            if "strategy2" not in self.recovery_attempts or self.recovery_attempts["strategy2"] != "failed":
                result = self._recovery_strategy_2()
                if result:
                    self.recovery_attempts["strategy2"] = "succeeded"
                    return True
                else:
                    self.recovery_attempts["strategy2"] = "failed"
            
            if "strategy3" not in self.recovery_attempts or self.recovery_attempts["strategy3"] != "failed":
                result = self._recovery_strategy_3()
                if result:
                    self.recovery_attempts["strategy3"] = "succeeded"
                    return True
                else:
                    self.recovery_attempts["strategy3"] = "failed"
            
            # If all strategies failed, give up
            logger.error("All recovery strategies failed")
            break
        
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
        else:
            logger.info("Recovery strategy 3 failed: Minimal configuration")
        
        return result
    
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
        
        # Save minimal configuration to a file
        minimal_config_file = "minimal_config.json"
        self._save_config(minimal_config_file, minimal_config)
        
        return minimal_config
    
    def shutdown_system(self) -> bool:
        """
        Shut down the system gracefully.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        logger.info("Shutting down system...")
        
        if not self._initialized:
            logger.warning("System not initialized, nothing to shut down")
            return True
        
        if not self.engine:
            logger.warning("No engine instance, nothing to shut down")
            return True
        
        try:
            result = self.engine.shutdown()
            
            if result:
                logger.info("System shut down successfully")
            else:
                logger.error("System failed to shut down")
            
            self._initialized = False
            return result
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            self._initialized = False
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the system.
        
        Returns:
            Dictionary with system status information
        """
        status = {
            "initialized": self._initialized,
            "recovery_attempts": self.recovery_attempts
        }
        
        if self.engine:
            engine_status = self.engine.get_status()
            status.update(engine_status)
        
        return status
    
    def print_status(self) -> None:
        """Print the current status of the system."""
        status = self.get_status()
        
        print("\n===== System Status =====")
        print(f"Initialized: {status['initialized']}")
        
        if "recovery_attempts" in status:
            print("\nRecovery Attempts:")
            for key, value in status["recovery_attempts"].items():
                print(f"  - {key}: {value}")
        
        if "component_status" in status:
            print("\nComponent Status:")
            for component, component_status in status["component_status"].items():
                print(f"  - {component}: {component_status}")
        
        print("========================\n")

# Main entry point for direct execution (optional)
# def main() -> int:
#     """
#     Main entry point for system startup.
    
#     Returns:
#         Exit code
#     """
#     import argparse
#     import sys
    
#     # Parse command line arguments
#     parser = argparse.ArgumentParser(description="Start the system")
#     parser.add_argument("--config", "-c", default="config/triangulum_config.json",
#                        help="Path to configuration file")
#     parser.add_argument("--log-level", "-l", default="INFO",
#                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
#                        help="Logging level")
    
#     args = parser.parse_args()
    
#     # Configure logging
#     logging.basicConfig(
#         level=getattr(logging, args.log_level),
#         format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
#     )
    
#     # Create startup manager
#     manager = SystemStartupManager(args.config)
    
#     try:
#         # Start system
#         result = manager.start_system()

#         if not result:
#             logger.error("System failed to start")
#             return 1

#         # Wait for keyboard interrupt
#         logger.info("System started successfully, press Ctrl+C to shut down")
#         while True:
#             try:
#                 time.sleep(1)
#             except KeyboardInterrupt:
#                 break

#         # Shutdown system
#         manager.shutdown_system()
#         return 0

#     except Exception as e:
#         logger.error(f"Error during startup: {e}")

#         # Try to shut down the system
#         try:
#             manager.shutdown_system()
#         except:
#             pass

#         return 1

# if __name__ == "__main__":
#     import sys
#     sys.exit(main())
