"""
Startup Dashboard

This module provides the StartupDashboard class for visualizing and monitoring
the system startup process, including component initialization, dependencies,
and health status.
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional, Set, Callable, Tuple, Union
from enum import Enum

from triangulum_lx.core.engine import ComponentStatus

logger = logging.getLogger(__name__)


class StartupPhase(str, Enum):
    """Enum representing phases of system startup."""
    CONFIGURATION = "configuration"
    CORE_COMPONENTS = "core_components"
    PROVIDERS = "providers"
    AGENTS = "agents"
    INTEGRATIONS = "integrations"
    HEALTH_CHECKS = "health_checks"
    READY = "ready"
    FAILED = "failed"


class StartupDashboard:
    """
    Dashboard for monitoring and visualizing system startup.
    
    This class provides real-time monitoring of system startup, component
    initialization, dependency resolution, and health status.
    """
    
    def __init__(self):
        """Initialize the startup dashboard."""
        self.start_time = time.time()
        self.current_phase = StartupPhase.CONFIGURATION
        self.component_status = {}
        self.component_timing = {}
        self.component_dependencies = {}
        self.startup_errors = {}
        self.recovered_components = set()
        self.startup_warnings = []
        self.startup_complete = False
        self.startup_success = False
        self.startup_duration = None
        self._update_thread = None
        self._update_interval = 0.5  # Update interval in seconds
        self._running = False
        self._lock = threading.Lock()
    
    def start_monitoring(self, engine=None, update_interval: float = 0.5) -> None:
        """
        Start monitoring system startup.
        
        Args:
            engine: Optional engine instance to monitor
            update_interval: Update interval in seconds
        """
        self.start_time = time.time()
        self._update_interval = update_interval
        self._running = True
        
        # Start update thread
        self._update_thread = threading.Thread(
            target=self._update_loop,
            args=(engine,),
            daemon=True
        )
        self._update_thread.start()
        logger.info("Startup monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring system startup."""
        self._running = False
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=2.0)
            logger.info("Startup monitoring stopped")
    
    def _update_loop(self, engine=None) -> None:
        """
        Update loop for monitoring system startup.
        
        Args:
            engine: Optional engine instance to monitor
        """
        while self._running:
            if engine:
                self._update_from_engine(engine)
            
            # Sleep until next update
            time.sleep(self._update_interval)
    
    def _update_from_engine(self, engine) -> None:
        """
        Update dashboard with information from engine.
        
        Args:
            engine: Engine instance to monitor
        """
        with self._lock:
            # Update component status
            if hasattr(engine, '_component_status'):
                self.component_status = {
                    component: status.value
                    for component, status in engine._component_status.items()
                }
            
            # Update component dependencies
            if hasattr(engine, '_dependencies'):
                self.component_dependencies = engine._dependencies
            
            # Update startup errors
            if hasattr(engine, '_startup_errors'):
                self.startup_errors = {
                    f"error_{i}": error
                    for i, error in enumerate(engine._startup_errors)
                }
            
            # Update startup phase based on component status
            self._update_startup_phase()
            
            # Check if startup is complete
            self._check_startup_complete()
    
    def _update_startup_phase(self) -> None:
        """Update the current startup phase based on component status."""
        # Check if any component is in FAILED state
        if any(status == "failed" for status in self.component_status.values()):
            self.current_phase = StartupPhase.FAILED
            return
        
        # Define phase mapping
        core_components = {'metrics', 'message_bus'}
        provider_components = {'provider_factory'}
        agent_factory_components = {'agent_factory'}
        agent_components = {
            'meta_agent', 'router', 'relationship_analyst', 'bug_detector',
            'strategy_agent', 'implementation_agent', 'verification_agent',
            'priority_analyzer', 'orchestrator'
        }
        
        # Follow a strict phase progression
        if self.current_phase == StartupPhase.CONFIGURATION:
            # Only advance if core components are ready
            if all(self.component_status.get(component) == "ready" for component in core_components
                   if component in self.component_status):
                self.current_phase = StartupPhase.CORE_COMPONENTS
        
        elif self.current_phase == StartupPhase.CORE_COMPONENTS:
            # Advance to providers phase
            self.current_phase = StartupPhase.PROVIDERS
        
        elif self.current_phase == StartupPhase.PROVIDERS:
            # Check if providers are ready
            if all(self.component_status.get(component) == "ready" for component in provider_components
                   if component in self.component_status):
                self.current_phase = StartupPhase.AGENTS
        
        elif self.current_phase == StartupPhase.AGENTS:
            # Check if agent factory and all agents are ready
            all_agent_factory_ready = all(
                self.component_status.get(component) == "ready" 
                for component in agent_factory_components
                if component in self.component_status
            )
            
            all_agents_ready = all(
                self.component_status.get(component) == "ready" 
                for component in agent_components
                if component in self.component_status
            )
            
            # Only advance if all agents are ready
            if all_agent_factory_ready and all_agents_ready:
                self.current_phase = StartupPhase.HEALTH_CHECKS
        
        elif self.current_phase == StartupPhase.HEALTH_CHECKS:
            # This phase is transitioned to READY by _check_startup_complete when startup is successful
            pass
    
    def _check_startup_complete(self) -> None:
        """Check if system startup is complete."""
        # Check if all components are in READY or FAILED state
        all_components_ready_or_failed = all(
            status in ("ready", "failed")
            for status in self.component_status.values()
        )
        
        if all_components_ready_or_failed and not self.startup_complete:
            self.startup_complete = True
            self.startup_duration = time.time() - self.start_time
            self.startup_success = all(
                status == "ready" for status in self.component_status.values()
            )
            
            if self.startup_success:
                self.current_phase = StartupPhase.READY
                logger.info(f"System startup completed successfully in {self.startup_duration:.2f} seconds")
            else:
                self.current_phase = StartupPhase.FAILED
                logger.error(f"System startup failed after {self.startup_duration:.2f} seconds")
    
    def record_component_start(self, component: str) -> None:
        """
        Record the start of component initialization.
        
        Args:
            component: Name of the component
        """
        with self._lock:
            self.component_timing[component] = {
                "start_time": time.time(),
                "end_time": None,
                "duration": None
            }
    
    def record_component_complete(self, component: str, success: bool) -> None:
        """
        Record the completion of component initialization.
        
        Args:
            component: Name of the component
            success: Whether initialization was successful
        """
        with self._lock:
            if component in self.component_timing:
                self.component_timing[component]["end_time"] = time.time()
                self.component_timing[component]["duration"] = (
                    self.component_timing[component]["end_time"] -
                    self.component_timing[component]["start_time"]
                )
                self.component_timing[component]["success"] = success
    
    def record_component_recovery(self, component: str, success: bool) -> None:
        """
        Record a component recovery attempt.
        
        Args:
            component: Name of the component
            success: Whether recovery was successful
        """
        with self._lock:
            if success:
                self.recovered_components.add(component)
                logger.info(f"Component recovery successful: {component}")
            else:
                logger.warning(f"Component recovery failed: {component}")
    
    def record_startup_warning(self, warning: str) -> None:
        """
        Record a startup warning.
        
        Args:
            warning: Warning message
        """
        with self._lock:
            self.startup_warnings.append(warning)
            logger.warning(f"Startup warning: {warning}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of system startup.
        
        Returns:
            Dictionary with startup status information
        """
        with self._lock:
            elapsed_time = time.time() - self.start_time
            
            status = {
                "phase": self.current_phase,
                "elapsed_time": elapsed_time,
                "complete": self.startup_complete,
                "success": self.startup_success,
                "component_status": self.component_status,
                "startup_errors": self.startup_errors,
                "startup_warnings": self.startup_warnings,
                "recovered_components": list(self.recovered_components)
            }
            
            if self.startup_complete:
                status["startup_duration"] = self.startup_duration
            
            return status
    
    def get_component_timing(self) -> Dict[str, Dict[str, Any]]:
        """
        Get timing information for component initialization.
        
        Returns:
            Dictionary with component timing information
        """
        with self._lock:
            return self.component_timing
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Get the component dependency graph.
        
        Returns:
            Dictionary mapping components to their dependencies
        """
        with self._lock:
            return self.component_dependencies
    
    def print_status_summary(self) -> None:
        """Print a summary of the startup status."""
        status = self.get_status()
        
        print("\n===== Startup Status Summary =====")
        print(f"Phase: {status['phase']}")
        print(f"Elapsed Time: {status['elapsed_time']:.2f} seconds")
        
        if status['complete']:
            print(f"Startup Complete: {'Success' if status['success'] else 'Failed'}")
            print(f"Startup Duration: {status['startup_duration']:.2f} seconds")
        else:
            print("Startup Status: In Progress")
        
        print("\nComponent Status:")
        for component, component_status in status['component_status'].items():
            print(f"  - {component}: {component_status}")
        
        if status['startup_errors']:
            print("\nStartup Errors:")
            for error_id, error in status['startup_errors'].items():
                print(f"  - {error}")
        
        if status['startup_warnings']:
            print("\nStartup Warnings:")
            for warning in status['startup_warnings']:
                print(f"  - {warning}")
        
        if status['recovered_components']:
            print("\nRecovered Components:")
            for component in status['recovered_components']:
                print(f"  - {component}")
        
        print("===================================\n")


def create_dashboard() -> StartupDashboard:
    """
    Create and configure a startup dashboard.
    
    Returns:
        Configured StartupDashboard instance
    """
    return StartupDashboard()
