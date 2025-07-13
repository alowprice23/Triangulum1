"""
Agent Factory - Creates and manages specialized agents in the Triangulum system.

This module provides the AgentFactory class which handles the creation, 
registration, and management of specialized agents in the Triangulum system.
"""

import logging
import importlib
import time
import concurrent.futures
from typing import Dict, List, Any, Optional, Type, Set, Callable, Tuple

from triangulum_lx.agents.base_agent import BaseAgent
# from triangulum_lx.agents.message_bus import MessageBus # Old
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus # New
from triangulum_lx.core.exceptions import AgentInitError, ConfigurationError

logger = logging.getLogger(__name__)


class AgentStatus:
    """Status of an agent."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    READY = "ready"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class AgentFactory:
    """
    Factory for creating and managing specialized agents in the Triangulum system.
    
    The AgentFactory is responsible for creating instances of specialized agents,
    managing agent registration and discovery, and providing a unified interface
    for accessing different agent types.
    """
    
    def __init__(self,
                 message_bus: Optional[EnhancedMessageBus] = None,
                 config: Optional[Dict[str, Any]] = None,
                 metrics_collector: Optional[Any] = None, # Added
                 engine_monitor: Optional[Any] = None): # Added, as BaseAgent takes it
        """
        Initialize the agent factory.
        
        Args:
            message_bus: Enhanced message bus for agent communication
            config: Optional configuration dictionary for agents section
            metrics_collector: Optional MetricsCollector instance
            engine_monitor: Optional Engine monitor instance for OperationProgress
        """
        self.message_bus = message_bus
        self.config = config or {} # This is typically the 'agents' section of main config
        self.metrics_collector = metrics_collector
        self.engine_monitor = engine_monitor
        self._agent_registry: Dict[str, Type[BaseAgent]] = {}
        self._active_agents: Dict[str, BaseAgent] = {}
        self._agent_configs: Dict[str, Dict[str, Any]] = {}
        self._agent_status: Dict[str, str] = {}
        self._startup_errors: Dict[str, str] = {}
        self._agent_dependencies: Dict[str, Set[str]] = {}
    
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseAgent], dependencies: Optional[Set[str]] = None) -> None:
        """
        Register an agent type with the factory.
        
        Args:
            agent_type: Type identifier for the agent
            agent_class: Agent class to register
            dependencies: Set of agent types this agent depends on (optional)
        """
        if agent_type in self._agent_registry:
            logger.warning(f"Agent type '{agent_type}' already registered, overwriting")
        
        self._agent_registry[agent_type] = agent_class
        self._agent_status[agent_type] = AgentStatus.PENDING
        self._agent_dependencies[agent_type] = dependencies or set()
        
        logger.debug(f"Registered agent type: {agent_type}")
    
    def configure_agent(self, agent_type: str, config: Dict[str, Any]) -> None:
        """
        Configure an agent type.
        
        Args:
            agent_type: Agent type
            config: Configuration dictionary
        """
        # Validate configuration
        self._validate_agent_config(agent_type, config)
        
        # Store configuration
        self._agent_configs[agent_type] = config
        
        # Update configuration of active agent if exists
        if agent_type in self._active_agents:
            try:
                agent = self._active_agents[agent_type]
                agent.config.update(config)
                logger.info(f"Updated configuration for active agent: {agent_type}")
            except Exception as e:
                logger.error(f"Failed to update configuration for agent {agent_type}: {e}")
    
    def _validate_agent_config(self, agent_type: str, config: Dict[str, Any]) -> None:
        """
        Validate agent configuration.
        
        Args:
            agent_type: Agent type
            config: Configuration dictionary
            
        Raises:
            ConfigValidationError: If the configuration is invalid
        """
        errors = []
        
        # Check if agent type is registered
        if agent_type not in self._agent_registry:
            errors.append(f"Unknown agent type: {agent_type}")
            
        # Check for required configuration keys
        if agent_type in self._agent_registry:
            agent_class = self._agent_registry[agent_type]
            if hasattr(agent_class, 'REQUIRED_CONFIG_KEYS'):
                for key in agent_class.REQUIRED_CONFIG_KEYS:
                    if key not in config:
                        errors.append(f"Missing required configuration key '{key}' for agent {agent_type}")
        
        if errors:
            raise ConfigurationError(
                f"Invalid configuration for agent {agent_type}",
                invalid_sections=errors
            )
    
    def create_agent(
        self,
        agent_type: str,
        agent_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        retry: bool = True,
        timeout: Optional[float] = None
    ) -> Optional[BaseAgent]:
        """
        Create an agent of the specified type.
        
        Args:
            agent_type: Type of agent to create
            agent_id: Unique identifier for the agent (optional)
            config: Agent configuration (optional)
            retry: Whether to retry if agent creation fails
            timeout: Maximum time to wait for agent creation
            
        Returns:
            The created agent instance
            
        Raises:
            AgentInitError: If agent creation fails
        """
        if agent_type not in self._agent_registry:
            error_msg = f"Agent type '{agent_type}' not registered"
            logger.error(error_msg)
            raise AgentInitError(error_msg, agent_type)
        
        # Mark as initializing
        self._agent_status[agent_type] = AgentStatus.INITIALIZING
        logger.info(f"Creating agent of type {agent_type}")
        
        try:
            # Get agent config (provided or stored)
            agent_config = config or self._agent_configs.get(agent_type, {})
            
            # Get timeout
            if timeout is None:
                timeout = self.config.get("agent_timeout", 30)  # Default 30-second timeout
            
            start_time = time.time()
            max_retries = 3 if retry else 1
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        wait_time = min(2 ** attempt, 10)  # Exponential backoff with max of 10 seconds
                        logger.info(f"Retrying agent {agent_type} creation (attempt {attempt+1}/{max_retries})...")
                        time.sleep(wait_time)
                    
                    # Check timeout
                    if timeout and time.time() - start_time > timeout:
                        raise TimeoutError(f"Agent {agent_type} creation timed out after {timeout} seconds")
                    
                    # Create the agent instance
                    agent_class = self._agent_registry[agent_type]
                    agent = agent_class(
                        agent_id=agent_id,
                        # agent_type=agent_type, # agent_class should define its AGENT_TYPE
                        message_bus=self.message_bus,
                        config=agent_config,
                        metrics_collector=self.metrics_collector, # Pass metrics collector
                        engine_monitor=self.engine_monitor # Pass engine monitor
                    )
                    
                    # Initialize the agent
                    if not agent.initialize():
                        raise AgentInitError(f"Failed to initialize {agent_type} agent", agent_type)
                    
                    # Mark as ready
                    self._agent_status[agent_type] = AgentStatus.READY
                    logger.info(f"Created {agent_type} agent with ID: {agent.agent_id}")
                    
                    # Store in active agents
                    self._active_agents[agent.agent_id] = agent
                    
                    return agent
                    
                except Exception as e:
                    last_error = e
                    error_msg = f"Error creating {agent_type} agent (attempt {attempt+1}/{max_retries}): {e}"
                    logger.error(error_msg, exc_info=True)
            
            # If we get here, all retries failed
            self._agent_status[agent_type] = AgentStatus.FAILED
            error_msg = f"Failed to create {agent_type} agent after {max_retries} attempts"
            self._startup_errors[agent_type] = error_msg
            raise AgentInitError(error_msg, agent_type, details={"last_error": str(last_error)})
            
        except Exception as e:
            self._agent_status[agent_type] = AgentStatus.FAILED
            error_msg = f"Error creating {agent_type} agent: {e}"
            self._startup_errors[agent_type] = error_msg
            logger.error(error_msg, exc_info=True)
            raise AgentInitError(error_msg, agent_type, details={"exception": str(e)})
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an active agent by ID.
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            The agent instance, or None if not found
        """
        return self._active_agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[BaseAgent]:
        """
        Get all active agents of a specific type.
        
        Args:
            agent_type: Type of agents to retrieve
            
        Returns:
            List of agent instances of the specified type
        """
        return [
            agent for agent in self._active_agents.values()
            if agent.agent_type == agent_type
        ]
    
    def initialize_agent(
        self, 
        agent_type: str, 
        agent_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        check_dependencies: bool = True
    ) -> Optional[BaseAgent]:
        """
        Initialize an agent and its dependencies.
        
        Args:
            agent_type: Type of agent to initialize
            agent_id: Unique identifier for the agent (optional)
            config: Agent configuration (optional)
            timeout: Maximum time to wait for agent initialization
            check_dependencies: Whether to check and initialize dependencies first
            
        Returns:
            The initialized agent instance, or None if initialization failed
        """
        logger.info(f"Initializing agent: {agent_type}")
        
        # Skip if already initialized
        active_agents_of_type = self.get_agents_by_type(agent_type)
        if active_agents_of_type and self._agent_status.get(agent_type) == AgentStatus.READY:
            logger.info(f"Agent type {agent_type} already initialized")
            return active_agents_of_type[0]
        
        # Initialize dependencies first
        if check_dependencies and agent_type in self._agent_dependencies:
            for dependency in self._agent_dependencies[agent_type]:
                if self._agent_status.get(dependency) != AgentStatus.READY:
                    # Initialize the dependency
                    dependency_agent = self.initialize_agent(
                        dependency,
                        timeout=timeout,
                        check_dependencies=True
                    )
                    
                    if dependency_agent is None:
                        error_msg = f"Failed to initialize dependency {dependency} for agent {agent_type}"
                        logger.error(error_msg)
                        self._startup_errors[agent_type] = error_msg
                        self._agent_status[agent_type] = AgentStatus.FAILED
                        return None
        
        try:
            # Get agent config
            if config is None:
                config = self._agent_configs.get(agent_type, {})
            
            # Create the agent
            agent = self.create_agent(
                agent_type=agent_type,
                agent_id=agent_id,
                config=config,
                timeout=timeout
            )
            
            return agent
            
        except Exception as e:
            error_msg = f"Failed to initialize agent {agent_type}: {e}"
            logger.error(error_msg, exc_info=True)
            self._startup_errors[agent_type] = error_msg
            self._agent_status[agent_type] = AgentStatus.FAILED
            return None
    
    def initialize_agents(
        self, 
        agent_types: Optional[List[str]] = None,
        parallel: bool = True,
        timeout: Optional[float] = None
    ) -> Dict[str, bool]:
        """
        Initialize multiple agents.
        
        Args:
            agent_types: List of agent types to initialize (default: all configured agents)
            parallel: Whether to initialize independent agents in parallel
            timeout: Maximum time to wait for agent initialization
            
        Returns:
            Dictionary mapping agent types to initialization success status
        """
        # Determine which agents to initialize
        if agent_types is None:
            agent_types = list(self._agent_configs.keys())
        
        results = {}
        
        # Determine initialization order based on dependencies
        if parallel:
            # Find agents with no dependencies
            independent_agents = [
                agent_type for agent_type in agent_types
                if not any(dep in agent_types for dep in self._agent_dependencies.get(agent_type, set()))
            ]
            
            # Initialize independent agents in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(independent_agents))) as executor:
                # Start initialization tasks
                future_to_agent = {
                    executor.submit(self.initialize_agent, agent_type, timeout=timeout, check_dependencies=False): agent_type
                    for agent_type in independent_agents
                }
                
                # Process results as they become available
                for future in concurrent.futures.as_completed(future_to_agent):
                    agent_type = future_to_agent[future]
                    try:
                        agent = future.result()
                        results[agent_type] = agent is not None
                    except Exception as e:
                        logger.error(f"Error initializing agent {agent_type}: {e}")
                        self._startup_errors[agent_type] = str(e)
                        self._agent_status[agent_type] = AgentStatus.FAILED
                        results[agent_type] = False
            
            # Initialize remaining agents sequentially
            remaining_agents = [
                agent_type for agent_type in agent_types
                if agent_type not in independent_agents
            ]
            
            for agent_type in remaining_agents:
                agent = self.initialize_agent(agent_type, timeout=timeout)
                results[agent_type] = agent is not None
        else:
            # Initialize all agents sequentially with dependency checking
            for agent_type in agent_types:
                agent = self.initialize_agent(agent_type, timeout=timeout)
                results[agent_type] = agent is not None
        
        return results
    
    def shutdown_agent(self, agent_id: str) -> bool:
        """
        Shut down a specific agent.
        
        Args:
            agent_id: ID of the agent to shut down
            
        Returns:
            True if the agent was shut down successfully, False otherwise
        """
        agent = self._active_agents.get(agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found for shutdown")
            return False
        
        try:
            agent.shutdown()
            del self._active_agents[agent_id]
            logger.info(f"Agent {agent_id} shut down successfully")
            
            # Check if this was the last agent of its type
            agent_type = agent.agent_type
            if not self.get_agents_by_type(agent_type):
                self._agent_status[agent_type] = AgentStatus.SHUTDOWN
            
            return True
        except Exception as e:
            logger.error(f"Error shutting down agent {agent_id}: {e}")
            return False
    
    def shutdown_all_agents(self) -> None:
        """Shut down all active agents."""
        agent_ids = list(self._active_agents.keys())  # Create a copy to avoid modification during iteration
        
        # Shutdown in reverse dependency order
        # First create a mapping from agent_id to agent_type
        id_to_type = {agent_id: agent.agent_type for agent_id, agent in self._active_agents.items()}
        
        # Get dependency order
        dependency_order = self._get_dependency_order(list(set(id_to_type.values())))
        
        # Reverse the order for shutdown
        dependency_order.reverse()
        
        # Shutdown agents in reversed dependency order
        for agent_type in dependency_order:
            # Get all active agents of this type
            agent_ids_of_type = [
                agent_id for agent_id, agent_type2 in id_to_type.items()
                if agent_type2 == agent_type and agent_id in self._active_agents
            ]
            
            for agent_id in agent_ids_of_type:
                self.shutdown_agent(agent_id)
        
        # Shutdown any remaining agents
        for agent_id in list(self._active_agents.keys()):
            self.shutdown_agent(agent_id)
    
    def _get_dependency_order(self, agent_types: List[str]) -> List[str]:
        """
        Get a list of agent types ordered by dependencies.
        
        Args:
            agent_types: List of agent types to order
            
        Returns:
            List of agent types in initialization order
        """
        # Build a dependency graph
        graph = {
            agent_type: set(dep for dep in self._agent_dependencies.get(agent_type, set()) if dep in agent_types)
            for agent_type in agent_types
        }
        
        # Find a topological sort
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                # Circular dependency detected
                raise ValueError(f"Circular dependency detected involving {node}")
            
            if node in visited:
                return
            
            temp_visited.add(node)
            
            # Visit all dependencies
            for dependency in graph.get(node, set()):
                visit(dependency)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        # Visit all nodes
        for agent_type in agent_types:
            if agent_type not in visited:
                visit(agent_type)
        
        return result
    
    def load_agent_module(self, module_path: str) -> bool:
        """
        Dynamically load an agent module and register its agent types.
        
        Args:
            module_path: Path to the agent module
            
        Returns:
            True if the module was loaded successfully, False otherwise
        """
        try:
            module = importlib.import_module(module_path)
            
            # Look for agent classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseAgent) and attr != BaseAgent:
                    # Get the agent type from the class
                    agent_type = getattr(attr, "AGENT_TYPE", None)
                    if agent_type:
                        # Get dependencies if defined
                        dependencies = getattr(attr, "DEPENDENCIES", None)
                        self.register_agent_type(agent_type, attr, dependencies)
            
            logger.info(f"Loaded agent module: {module_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading agent module {module_path}: {e}")
            return False
    
    def discover_agents(self, package_path: str = "triangulum_lx.agents") -> int:
        """
        Discover and register agent types from a package.
        
        Args:
            package_path: Path to the package containing agent modules
            
        Returns:
            Number of agent types discovered
        """
        count = 0
        try:
            package = importlib.import_module(package_path)
            
            # Get all modules in the package
            for module_info in getattr(package, "__all__", []):
                module_path = f"{package_path}.{module_info}"
                if self.load_agent_module(module_path):
                    count += 1
                    
            logger.info(f"Discovered {count} agent modules in {package_path}")
            return count
            
        except Exception as e:
            logger.error(f"Error discovering agents in {package_path}: {e}")
            return count
    
    def get_agent_info(self, agent_type: str) -> Dict[str, Any]:
        """
        Get information about an agent type.
        
        Args:
            agent_type: Agent type
            
        Returns:
            Agent information dictionary
        """
        if agent_type not in self._agent_registry:
            return {"error": f"Unknown agent type: {agent_type}"}
        
        agent_class = self._agent_registry[agent_type]
        
        info = {
            "name": agent_type,
            "class": agent_class.__name__,
            "module": agent_class.__module__,
            "status": self._agent_status.get(agent_type, AgentStatus.PENDING),
            "has_config": agent_type in self._agent_configs,
            "dependencies": list(self._agent_dependencies.get(agent_type, set())),
            "active_instances": len(self.get_agents_by_type(agent_type))
        }
        
        # Add error info if available
        if agent_type in self._startup_errors:
            info["error"] = self._startup_errors[agent_type]
        
        return info
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of all active agents.
        
        Returns:
            Dictionary with health check results
        """
        results = {
            "agents": {},
            "overall_status": "healthy"
        }
        
        # Get unique agent types
        agent_types = set(agent.agent_type for agent in self._active_agents.values())
        
        # Check each agent type
        for agent_type in agent_types:
            agents = self.get_agents_by_type(agent_type)
            agent_health = {
                "status": self._agent_status.get(agent_type, AgentStatus.PENDING),
                "active_instances": len(agents),
                "instances": []
            }
            
            # Check individual agent instances
            for agent in agents:
                instance_health = {"agent_id": agent.agent_id}
                
                # Check if agent has a health_check method
                if hasattr(agent, "health_check") and callable(getattr(agent, "health_check")):
                    try:
                        instance_health.update(agent.health_check())
                    except Exception as e:
                        instance_health["error"] = str(e)
                        instance_health["healthy"] = False
                        agent_health["status"] = AgentStatus.FAILED
                        results["overall_status"] = "degraded"
                
                agent_health["instances"].append(instance_health)
            
            results["agents"][agent_type] = agent_health
        
        # Check if any agent type is not healthy
        if any(agent_info.get("status") != AgentStatus.READY for agent_info in results["agents"].values()):
            results["overall_status"] = "degraded"
        
        # Check if any agent type has no active instances
        if any(agent_info.get("active_instances", 0) == 0 for agent_info in results["agents"].values()):
            results["overall_status"] = "critical"
        
        return results
