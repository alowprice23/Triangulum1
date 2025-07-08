"""
Agentic System Monitor - Enhanced monitoring for agentic system with progress tracking.

This module provides improved monitoring capabilities specifically designed for 
the agentic system, including:
- Detailed progress tracking for LLM operations
- Agent activity visualization
- Thought chain integration
- Real-time progress updates
"""

import logging
import os
import sys
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Callable, Set
from enum import Enum, auto

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    """Progress event for tracking agent activities."""
    
    agent_name: str
    activity: str
    percent_complete: float
    timestamp: float = field(default_factory=time.time)
    estimated_completion: Optional[float] = None
    thought_chain_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def eta_str(self) -> str:
        """Get a human-readable ETA string."""
        if self.estimated_completion is None:
            return "Unknown"
        
        seconds_remaining = max(0, self.estimated_completion - time.time())
        
        if seconds_remaining < 60:
            return f"{seconds_remaining:.0f} seconds"
        elif seconds_remaining < 3600:
            return f"{seconds_remaining / 60:.1f} minutes"
        else:
            return f"{seconds_remaining / 3600:.1f} hours"


class AgentActivityState(Enum):
    """States that an agent can be in."""
    IDLE = auto()
    BUSY = auto()
    ERROR = auto()
    WAITING = auto()


class AgenticSystemMonitor:
    """
    Enhanced monitoring system designed for agentic operations with progress tracking.
    
    This class provides detailed visibility into the internal processing of agents,
    including progress tracking, activity monitoring, and thought chain visualization.
    It replaces the original SystemMonitor class with one specifically designed
    for the agentic system.
    """
    
    def __init__(self, 
                 update_interval: float = 0.5,
                 enable_detailed_progress: bool = True,
                 enable_agent_activity_tracking: bool = True,
                 enable_thought_chain_visualization: bool = False):
        """
        Initialize the agentic system monitor.
        
        Args:
            update_interval: Interval in seconds to update progress information
            enable_detailed_progress: Whether to track detailed progress
            enable_agent_activity_tracking: Whether to track agent activities
            enable_thought_chain_visualization: Whether to visualize thought chains
        """
        self.update_interval = update_interval
        self.enable_detailed_progress = enable_detailed_progress
        self.enable_agent_activity_tracking = enable_agent_activity_tracking
        self.enable_thought_chain_visualization = enable_thought_chain_visualization
        
        # Progress tracking
        self.progress_callbacks: List[Callable[[ProgressEvent], None]] = []
        self.current_progress: Dict[str, ProgressEvent] = {}
        self.progress_history: List[ProgressEvent] = []
        
        # Agent activity tracking
        self.agent_states: Dict[str, AgentActivityState] = {}
        self.agent_activities: Dict[str, str] = {}
        self.agent_start_times: Dict[str, float] = {}
        
        # Thought chain tracking
        self.active_thought_chains: Dict[str, Any] = {}
        
        # Internal state
        self.last_update_time = time.time()
        self.update_thread = None
        self.is_running = False
        self.lock = threading.RLock()
        
        logger.info("AgenticSystemMonitor initialized with update_interval=%.2fs", update_interval)
    
    def start(self) -> None:
        """Start the monitor with automatic updates."""
        with self.lock:
            if self.is_running:
                return
            
            self.is_running = True
            
            def update_loop():
                while self.is_running:
                    try:
                        self.update()
                        time.sleep(self.update_interval)
                    except Exception as e:
                        logger.error(f"Error in monitor update loop: {e}")
                        time.sleep(self.update_interval)
            
            self.update_thread = threading.Thread(target=update_loop, daemon=True)
            self.update_thread.start()
            
            logger.info("Started automatic progress updates with interval %.2fs", self.update_interval)
    
    def stop(self) -> None:
        """Stop the automatic updates."""
        with self.lock:
            self.is_running = False
            if self.update_thread:
                self.update_thread.join(timeout=1.0)
                self.update_thread = None
                
            logger.info("Stopped automatic progress updates")
    
    def update(self) -> None:
        """
        Update the monitor state and notify callbacks of progress events.
        
        This should be called periodically to ensure progress information is up-to-date.
        """
        with self.lock:
            current_time = time.time()
            self.last_update_time = current_time
            
            # Update progress events
            for agent_name, event in self.current_progress.items():
                # Notify callbacks
                for callback in self.progress_callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")
    
    def register_progress_callback(self, callback: Callable[[ProgressEvent], None]) -> None:
        """
        Register a callback to be notified of progress events.
        
        Args:
            callback: Function to call with progress events
        """
        with self.lock:
            if callback not in self.progress_callbacks:
                self.progress_callbacks.append(callback)
                logger.debug("Registered progress callback")
    
    def unregister_progress_callback(self, callback: Callable[[ProgressEvent], None]) -> None:
        """
        Unregister a progress callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        with self.lock:
            if callback in self.progress_callbacks:
                self.progress_callbacks.remove(callback)
                logger.debug("Unregistered progress callback")
    
    def update_progress(self, 
                       agent_name: str, 
                       activity: str, 
                       percent_complete: float,
                       estimated_completion: Optional[float] = None,
                       thought_chain_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the progress for an agent.
        
        Args:
            agent_name: Name of the agent
            activity: Current activity description
            percent_complete: Percentage of completion (0-100)
            estimated_completion: Estimated completion time (timestamp)
            thought_chain_id: ID of the associated thought chain
            details: Additional details about the progress
        """
        with self.lock:
            # Create a progress event
            event = ProgressEvent(
                agent_name=agent_name,
                activity=activity,
                percent_complete=percent_complete,
                timestamp=time.time(),
                estimated_completion=estimated_completion,
                thought_chain_id=thought_chain_id,
                details=details or {}
            )
            
            # Store the event
            self.current_progress[agent_name] = event
            self.progress_history.append(event)
            
            # Update agent state
            self.agent_states[agent_name] = AgentActivityState.BUSY
            self.agent_activities[agent_name] = activity
            
            # Notify callbacks immediately if they exist
            for callback in self.progress_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
            
            logger.debug(f"Progress updated: {agent_name} - {activity} - {percent_complete}%")
    
    def set_agent_state(self, agent_name: str, state: AgentActivityState, activity: Optional[str] = None) -> None:
        """
        Set the state of an agent.
        
        Args:
            agent_name: Name of the agent
            state: New state for the agent
            activity: Current activity description (optional)
        """
        with self.lock:
            self.agent_states[agent_name] = state
            
            if activity:
                self.agent_activities[agent_name] = activity
            
            if state == AgentActivityState.BUSY:
                self.agent_start_times[agent_name] = time.time()
            
            logger.debug(f"Agent state updated: {agent_name} - {state.name}")
    
    def get_agent_state(self, agent_name: str) -> AgentActivityState:
        """
        Get the current state of an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Current state of the agent
        """
        with self.lock:
            return self.agent_states.get(agent_name, AgentActivityState.IDLE)
    
    def register_thought_chain(self, thought_chain_id: str, thought_chain: Any) -> None:
        """
        Register a thought chain for visualization.
        
        Args:
            thought_chain_id: ID of the thought chain
            thought_chain: Thought chain object
        """
        with self.lock:
            self.active_thought_chains[thought_chain_id] = thought_chain
            logger.debug(f"Registered thought chain: {thought_chain_id}")
    
    def unregister_thought_chain(self, thought_chain_id: str) -> None:
        """
        Unregister a thought chain.
        
        Args:
            thought_chain_id: ID of the thought chain to unregister
        """
        with self.lock:
            if thought_chain_id in self.active_thought_chains:
                del self.active_thought_chains[thought_chain_id]
                logger.debug(f"Unregistered thought chain: {thought_chain_id}")
    
    def get_active_thought_chains(self) -> Dict[str, Any]:
        """
        Get all active thought chains.
        
        Returns:
            Dictionary mapping thought chain IDs to thought chain objects
        """
        with self.lock:
            return self.active_thought_chains.copy()
    
    def get_progress_history(self) -> List[ProgressEvent]:
        """
        Get the history of progress events.
        
        Returns:
            List of progress events in chronological order
        """
        with self.lock:
            return self.progress_history.copy()
    
    def get_current_activities(self) -> Dict[str, str]:
        """
        Get the current activities of all agents.
        
        Returns:
            Dictionary mapping agent names to their current activities
        """
        with self.lock:
            return self.agent_activities.copy()
    
    def get_agent_progress(self, agent_name: str) -> Optional[ProgressEvent]:
        """
        Get the current progress for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Current progress event for the agent, or None if not found
        """
        with self.lock:
            return self.current_progress.get(agent_name)
    
    def clear_history(self) -> None:
        """Clear the progress history."""
        with self.lock:
            self.progress_history = []
            logger.debug("Cleared progress history")
    
    def generate_progress_report(self) -> Dict[str, Any]:
        """
        Generate a report of current progress for all agents.
        
        Returns:
            Dictionary containing progress information
        """
        with self.lock:
            report = {
                'timestamp': time.time(),
                'agent_states': {agent: state.name for agent, state in self.agent_states.items()},
                'agent_activities': self.agent_activities.copy(),
                'current_progress': {agent: {
                    'activity': event.activity,
                    'percent_complete': event.percent_complete,
                    'eta': event.eta_str
                } for agent, event in self.current_progress.items()},
                'active_thought_chains': list(self.active_thought_chains.keys())
            }
            
            return report


# For backwards compatibility
SystemMonitor = AgenticSystemMonitor
