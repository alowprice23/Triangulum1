#!/usr/bin/env python3
"""
Progress Tracker

This module provides a way for Triangulum agents to report progress to the
agentic dashboard, including status updates, thought processes, and inter-agent
communication.
"""

import os
import time
import threading
import logging
import datetime
import uuid
from typing import Dict, List, Any, Optional, Union, Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProgressTracker:
    """
    Tracks progress of Triangulum agents and reports to the agentic dashboard.
    
    This class provides a simple interface for agents to report their progress,
    thoughts, and messages, which can then be visualized in the dashboard.
    """
    
    def __init__(self, 
                dashboard=None,
                agent_id: str = None,
                enable_local_logging: bool = True,
                log_dir: str = "./triangulum_logs",
                connect_to_dashboard: bool = True):
        """
        Initialize the progress tracker.
        
        Args:
            dashboard: The agentic dashboard instance to report to (optional)
            agent_id: ID of the agent using this tracker
            enable_local_logging: Whether to log progress locally to files
            log_dir: Directory to store local logs
            connect_to_dashboard: Whether to attempt to connect to a running dashboard
        """
        self.dashboard = dashboard
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        self.enable_local_logging = enable_local_logging
        self.log_dir = log_dir
        self.connect_to_dashboard = connect_to_dashboard
        
        # Initialize tracking data
        self.percent_complete = 0.0
        self.status = "Initializing"
        self.current_activity = None
        self.tasks_completed = 0
        self.total_tasks = 0
        self.thought_count = 0
        self.start_time = datetime.datetime.now()
        self.last_update = time.time()
        
        # Create log directory if needed
        if enable_local_logging:
            os.makedirs(log_dir, exist_ok=True)
            os.makedirs(os.path.join(log_dir, "thoughts"), exist_ok=True)
            os.makedirs(os.path.join(log_dir, "messages"), exist_ok=True)
            os.makedirs(os.path.join(log_dir, "progress"), exist_ok=True)
        
        # Connect to dashboard if requested
        if connect_to_dashboard and dashboard is None:
            self._connect_to_dashboard()
        
        logger.info(f"Progress tracker initialized for agent {self.agent_id}")
    
    def _connect_to_dashboard(self):
        """Try to connect to a running dashboard instance."""
        try:
            # We'll look for a running dashboard in common locations
            # This is a simple implementation - in a real system we'd use a more robust discovery mechanism
            from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard
            
            # Check for dashboard in common directories
            dashboard_dirs = [
                "./triangulum_dashboard",
                "./agentic_dashboard",
                "./dashboard"
            ]
            
            for dir in dashboard_dirs:
                if os.path.exists(dir):
                    # Found a potential dashboard directory
                    logger.info(f"Found potential dashboard directory: {dir}")
                    # In a real implementation, we'd check for a running dashboard process
                    # and connect to it, but for now we'll just create a new instance
                    self.dashboard = AgenticDashboard(
                        output_dir=dir,
                        enable_server=False  # Don't start a new server, as one should already be running
                    )
                    logger.info(f"Connected to dashboard at {dir}")
                    return
            
            logger.warning("No running dashboard found. Progress will only be logged locally.")
        except ImportError:
            logger.warning("Could not import AgenticDashboard. Progress will only be logged locally.")
        except Exception as e:
            logger.warning(f"Error connecting to dashboard: {e}")
    
    def update_progress(self, 
                      percent_complete: float,
                      status: str = None,
                      current_activity: str = None,
                      tasks_completed: int = None,
                      total_tasks: int = None):
        """
        Update progress for the agent.
        
        Args:
            percent_complete: Percentage of completion (0-100)
            status: Current status (Active, Idle, Error, etc.)
            current_activity: Description of current activity
            tasks_completed: Number of tasks completed
            total_tasks: Total number of tasks
        """
        # Update local tracking data
        self.percent_complete = percent_complete
        
        if status is not None:
            self.status = status
        
        if current_activity is not None:
            self.current_activity = current_activity
        
        if tasks_completed is not None:
            self.tasks_completed = tasks_completed
        
        if total_tasks is not None:
            self.total_tasks = total_tasks
        
        # Log progress locally
        if self.enable_local_logging:
            self._log_progress()
        
        # Report to dashboard if available
        if self.dashboard is not None:
            try:
                self.dashboard.update_agent_progress(
                    agent_id=self.agent_id,
                    percent_complete=percent_complete,
                    status=self.status,
                    current_activity=self.current_activity,
                    tasks_completed=self.tasks_completed,
                    total_tasks=self.total_tasks,
                    thought_count=self.thought_count
                )
            except Exception as e:
                logger.warning(f"Error reporting progress to dashboard: {e}")
    
    def record_thought(self, 
                      content: str, 
                      thought_type: str = "analysis",
                      chain_id: str = None,
                      metadata: Optional[Dict] = None):
        """
        Record a thought from the agent.
        
        Args:
            content: The thought content
            thought_type: Type of thought (analysis, decision, etc.)
            chain_id: ID of the thought chain (optional)
            metadata: Additional metadata for the thought
        """
        # Generate chain ID if not provided
        if chain_id is None:
            chain_id = f"{self.agent_id}_chain_{uuid.uuid4().hex[:8]}"
        
        # Update thought count
        self.thought_count += 1
        
        # Log thought locally
        if self.enable_local_logging:
            self._log_thought(content, thought_type, chain_id, metadata)
        
        # Report to dashboard if available
        if self.dashboard is not None:
            try:
                self.dashboard.register_thought(
                    agent_id=self.agent_id,
                    chain_id=chain_id,
                    content=content,
                    thought_type=thought_type,
                    metadata=metadata
                )
            except Exception as e:
                logger.warning(f"Error reporting thought to dashboard: {e}")
    
    def send_message(self, 
                    target_agent: str, 
                    content: str, 
                    message_type: str = "request",
                    metadata: Optional[Dict] = None):
        """
        Send a message to another agent.
        
        Args:
            target_agent: ID of the target agent
            content: Message content
            message_type: Type of message (request, response, notification, etc.)
            metadata: Additional metadata for the message
        """
        # Log message locally
        if self.enable_local_logging:
            self._log_message(target_agent, content, message_type, metadata)
        
        # Report to dashboard if available
        if self.dashboard is not None:
            try:
                self.dashboard.register_message(
                    source_agent=self.agent_id,
                    target_agent=target_agent,
                    message_type=message_type,
                    content=content,
                    metadata=metadata
                )
            except Exception as e:
                logger.warning(f"Error reporting message to dashboard: {e}")
    
    def _log_progress(self):
        """Log progress information to a local file."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.log_dir, "progress", f"{self.agent_id}_progress.log")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] Progress: {self.percent_complete:.1f}%, Status: {self.status}, "
                       f"Activity: {self.current_activity}, "
                       f"Tasks: {self.tasks_completed}/{self.total_tasks}\n")
        except Exception as e:
            logger.warning(f"Error logging progress: {e}")
    
    def _log_thought(self, content, thought_type, chain_id, metadata):
        """Log a thought to a local file."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.log_dir, "thoughts", f"{self.agent_id}_thoughts.log")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {thought_type.upper()} (Chain: {chain_id}): {content}\n")
        except Exception as e:
            logger.warning(f"Error logging thought: {e}")
    
    def _log_message(self, target_agent, content, message_type, metadata):
        """Log a message to a local file."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.log_dir, "messages", f"{self.agent_id}_messages.log")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] TO {target_agent} ({message_type}): {content}\n")
        except Exception as e:
            logger.warning(f"Error logging message: {e}")
    
    def estimate_completion_time(self):
        """Estimate the time remaining based on current progress."""
        if self.percent_complete <= 0:
            return None
        
        elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
        if elapsed <= 0:
            return None
        
        progress_rate = self.percent_complete / elapsed  # % per second
        if progress_rate <= 0:
            return None
        
        remaining_percent = 100 - self.percent_complete
        remaining_seconds = remaining_percent / progress_rate
        
        completion_time = datetime.datetime.now() + datetime.timedelta(seconds=remaining_seconds)
        return completion_time
    
    def get_progress_summary(self):
        """Get a summary of current progress."""
        est_completion = self.estimate_completion_time()
        completion_str = "Unknown"
        if est_completion:
            completion_str = est_completion.strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "agent_id": self.agent_id,
            "percent_complete": self.percent_complete,
            "status": self.status,
            "current_activity": self.current_activity,
            "tasks_completed": self.tasks_completed,
            "total_tasks": self.total_tasks,
            "thought_count": self.thought_count,
            "start_time": self.start_time.isoformat(),
            "estimated_completion": completion_str
        }


# Demo usage when run directly
if __name__ == "__main__":
    # Create a progress tracker
    tracker = ProgressTracker(agent_id="demo_agent")
    
    # Simulate a task with progress updates
    print("Starting task simulation...")
    
    for i in range(10):
        # Update progress
        percent = (i + 1) * 10
        tracker.update_progress(
            percent_complete=percent,
            status="Active",
            current_activity=f"Processing step {i+1}",
            tasks_completed=i+1,
            total_tasks=10
        )
        
        # Record some thoughts
        tracker.record_thought(
            f"Analyzing data for step {i+1}",
            thought_type="analysis"
        )
        
        if i % 3 == 0:
            tracker.record_thought(
                f"Decision: proceed with algorithm A for step {i+1}",
                thought_type="decision"
            )
        
        # Send some messages
        if i % 2 == 0:
            tracker.send_message(
                target_agent="coordinator",
                content=f"Completed step {i+1}",
                message_type="notification"
            )
        
        if i % 4 == 0:
            tracker.send_message(
                target_agent="data_processor",
                content=f"Request data for step {i+2}",
                message_type="request"
            )
        
        # Simulate work
        time.sleep(0.5)
    
    # Final update
    tracker.update_progress(
        percent_complete=100.0,
        status="Completed",
        current_activity="Task finished successfully",
        tasks_completed=10,
        total_tasks=10
    )
    
    # Show summary
    summary = tracker.get_progress_summary()
    print("\nTask completed with summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
