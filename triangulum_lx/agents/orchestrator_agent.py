"""
Orchestrator Agent

This agent coordinates the workflow between all specialized agents
in the Triangulum self-healing system. It manages the execution flow,
ensures proper communication, and handles error recovery.
"""

import logging
import os
import time
import traceback
import threading
import queue
import enum
from typing import Dict, List, Set, Tuple, Any, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime

from .base_agent import BaseAgent
from .message import AgentMessage, MessageType, ConfidenceLevel
from .message_bus import MessageBus
from ..core.exceptions import TriangulumError

logger = logging.getLogger(__name__)


# Define task priority levels
class TaskPriority(enum.IntEnum):
    """Priority levels for tasks in the Orchestrator's queue."""
    CRITICAL = 0    # Highest priority - security issues, blocking bugs
    HIGH = 1        # High priority - serious bugs, performance issues
    MEDIUM = 2      # Medium priority - non-blocking bugs, minor issues
    LOW = 3         # Low priority - enhancements, refactoring
    BACKGROUND = 4  # Lowest priority - non-essential tasks


@dataclass
class Task:
    """
    Represents a task in the Orchestrator's queue.
    
    Attributes:
        id: Unique identifier for the task
        type: Type of task (e.g., 'file_healing', 'folder_healing')
        priority: Priority level of the task
        content: Task content/parameters
        workflow_id: ID of the associated workflow
        created_at: When the task was created
        started_at: When the task execution started
        completed_at: When the task execution completed
        status: Current status of the task
        attempts: Number of attempts made to execute the task
        sender: Agent that sent the task request
        result: Result of the task execution
        required_capabilities: List of capabilities required to execute this task
        target_agent_type: Specific agent type to target (bypasses capability-based routing)
        assigned_agent: ID of the agent this task is assigned to
        retry_count: Number of times this task has been retried
        max_retries: Maximum number of retries allowed
        last_error: Last error message if task failed
        task_start_time: When the task started execution
        processing_stages: List of processing stages the task has gone through
    """
    id: str
    type: str
    priority: TaskPriority
    content: Dict[str, Any]
    workflow_id: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, in_progress, completed, failed, cancelled
    attempts: int = 0
    sender: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    required_capabilities: List[str] = None
    target_agent_type: Optional[str] = None
    assigned_agent: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    task_start_time: Optional[float] = None
    processing_stages: List[str] = None
    
    def __post_init__(self):
        """Initialize default values for collections."""
        if self.required_capabilities is None:
            self.required_capabilities = []
        if self.processing_stages is None:
            self.processing_stages = []
    
    def mark_started(self):
        """Mark the task as started."""
        self.started_at = datetime.now()
        self.status = "in_progress"
        self.attempts += 1
    
    def mark_completed(self, result: Dict[str, Any]):
        """Mark the task as completed."""
        self.completed_at = datetime.now()
        self.status = "completed"
        self.result = result
    
    def mark_failed(self, error: str):
        """Mark the task as failed."""
        self.completed_at = datetime.now()
        self.status = "failed"
        if self.result is None:
            self.result = {}
        self.result["error"] = error
    
    def can_retry(self, max_attempts: int) -> bool:
        """Check if the task can be retried."""
        return self.attempts < max_attempts and self.status != "completed"
    
    def time_in_queue(self) -> float:
        """Get the time spent in queue in seconds."""
        if self.started_at is None:
            return (datetime.now() - self.created_at).total_seconds()
        return (self.started_at - self.created_at).total_seconds()
    
    def execution_time(self) -> Optional[float]:
        """Get the execution time in seconds."""
        if self.started_at is None:
            return None
        if self.completed_at is None:
            return (datetime.now() - self.started_at).total_seconds()
        return (self.completed_at - self.started_at).total_seconds()
    
    def total_time(self) -> float:
        """Get the total time from creation to completion (or now) in seconds."""
        if self.completed_at is None:
            return (datetime.now() - self.created_at).total_seconds()
        return (self.completed_at - self.created_at).total_seconds()


class AgentRegistry:
    """
    Registry of available agents and their capabilities.
    
    This class keeps track of agent availability, capabilities, and health.
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self.agents = {}  # agent_id -> agent_info
        self.capabilities = {}  # capability -> [agent_ids]
        self.agent_health = {}  # agent_id -> health_status
        self.lock = threading.RLock()
    
    def register_agent(self, agent_id: str, agent_type: str, capabilities: List[str]):
        """
        Register an agent with the registry.
        
        Args:
            agent_id: ID of the agent
            agent_type: Type of the agent
            capabilities: List of capabilities the agent has
        """
        with self.lock:
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "capabilities": capabilities,
                "registered_at": datetime.now()
            }
            
            for capability in capabilities:
                if capability not in self.capabilities:
                    self.capabilities[capability] = []
                self.capabilities[capability].append(agent_id)
            
            self.agent_health[agent_id] = {
                "status": "available",
                "last_heartbeat": datetime.now(),
                "error_count": 0,
                "success_count": 0
            }
    
    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: ID of the agent to unregister
        """
        with self.lock:
            if agent_id in self.agents:
                agent_info = self.agents[agent_id]
                
                # Remove from capabilities
                for capability in agent_info["capabilities"]:
                    if capability in self.capabilities and agent_id in self.capabilities[capability]:
                        self.capabilities[capability].remove(agent_id)
                        if not self.capabilities[capability]:
                            del self.capabilities[capability]
                
                # Remove agent
                del self.agents[agent_id]
                
                # Remove health info
                if agent_id in self.agent_health:
                    del self.agent_health[agent_id]
    
    def get_agent_for_capability(self, capability: str, exclude_agents: Optional[List[str]] = None) -> Optional[str]:
        """
        Get an available agent with the specified capability.
        
        Args:
            capability: The capability needed
            exclude_agents: List of agent IDs to exclude from consideration
            
        Returns:
            ID of an available agent or None if none found
        """
        with self.lock:
            if capability not in self.capabilities:
                return None
            
            exclude_agents = exclude_agents or []
            
            # Filter out excluded agents and check health
            available_agents = [
                agent_id for agent_id in self.capabilities[capability]
                if agent_id not in exclude_agents and self.agent_health.get(agent_id, {}).get("status") == "available"
            ]
            
            if not available_agents:
                return None
            
            # For now, just return the first available agent
            # In a more advanced implementation, could consider load balancing, success rate, etc.
            return available_agents[0]
    
    def update_agent_health(self, agent_id: str, success: bool, error_message: Optional[str] = None):
        """
        Update the health status of an agent.
        
        Args:
            agent_id: ID of the agent
            success: Whether the agent operation was successful
            error_message: Error message if operation failed
        """
        with self.lock:
            if agent_id not in self.agent_health:
                return
            
            health = self.agent_health[agent_id]
            health["last_heartbeat"] = datetime.now()
            
            if success:
                health["success_count"] += 1
                # If agent was marked as unavailable, mark it as available again
                if health["status"] == "unavailable":
                    health["status"] = "available"
                    health["error_count"] = 0
            else:
                health["error_count"] += 1
                # If error count reaches threshold, mark agent as unavailable
                if health["error_count"] >= 3:  # Threshold for marking as unavailable
                    health["status"] = "unavailable"
                    logger.warning(f"Agent {agent_id} marked as unavailable due to repeated errors")
                    if error_message:
                        logger.warning(f"Last error from {agent_id}: {error_message}")
    
    def is_agent_available(self, agent_id: str) -> bool:
        """
        Check if an agent is available.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            True if the agent is available, False otherwise
        """
        with self.lock:
            if agent_id not in self.agent_health:
                return False
            
            return self.agent_health[agent_id]["status"] == "available"


class TaskQueue:
    """
    Priority queue for orchestration tasks.
    
    This class manages the queue of tasks to be executed by the orchestrator,
    with priority-based scheduling.
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize the task queue.
        
        Args:
            max_size: Maximum size of the queue
        """
        self.tasks = {}  # task_id -> Task
        self.queues = {
            TaskPriority.CRITICAL: queue.PriorityQueue(max_size),
            TaskPriority.HIGH: queue.PriorityQueue(max_size),
            TaskPriority.MEDIUM: queue.PriorityQueue(max_size),
            TaskPriority.LOW: queue.PriorityQueue(max_size),
            TaskPriority.BACKGROUND: queue.PriorityQueue(max_size)
        }
        self.lock = threading.RLock()
    
    def add_task(self, task: Task):
        """
        Add a task to the queue.
        
        Args:
            task: The task to add
        """
        with self.lock:
            self.tasks[task.id] = task
            # Use creation time as secondary priority (older tasks first)
            priority_tuple = (task.priority, task.created_at.timestamp())
            self.queues[task.priority].put((priority_tuple, task.id))
    
    def get_next_task(self) -> Optional[Task]:
        """
        Get the next task from the queue based on priority.
        
        Returns:
            The next task or None if queue is empty
        """
        with self.lock:
            # Try to get a task from each queue in priority order
            for priority in TaskPriority:
                if not self.queues[priority].empty():
                    _, task_id = self.queues[priority].get()
                    if task_id in self.tasks:
                        return self.tasks[task_id]
            
            return None
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a specific task by ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            The task or None if not found
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a task from the queue.
        
        Args:
            task_id: ID of the task
            
        Returns:
            True if the task was removed, False otherwise
        """
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
            return False
    
    def update_task(self, task: Task):
        """
        Update a task in the queue.
        
        Args:
            task: The updated task
        """
        with self.lock:
            if task.id in self.tasks:
                self.tasks[task.id] = task
    
    def get_tasks_by_status(self, status: str) -> List[Task]:
        """
        Get all tasks with the specified status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of tasks with the specified status
        """
        with self.lock:
            return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_workflow(self, workflow_id: str) -> List[Task]:
        """
        Get all tasks for a specific workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            List of tasks for the workflow
        """
        with self.lock:
            return [task for task in self.tasks.values() if task.workflow_id == workflow_id]
    
    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks in the queue.
        
        Returns:
            List of all tasks
        """
        with self.lock:
            return list(self.tasks.values())
    
    def size(self) -> int:
        """
        Get the current size of the queue.
        
        Returns:
            Number of tasks in the queue
        """
        with self.lock:
            return len(self.tasks)


class OrchestratorAgent(BaseAgent):
    """
    Agent responsible for orchestrating the entire self-healing workflow.
    
    The Orchestrator Agent coordinates between all specialized agents:
    - Bug Detector Agent
    - Relationship Analyst Agent
    - Strategy Agent
    - Implementation Agent
    - Verification Agent
    
    It manages the workflow, handles errors, and ensures proper communication
    between agents. It also provides task distribution, priority-based scheduling,
    and error recovery.
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_type: str = "orchestrator",
        message_bus: Optional[MessageBus] = None,
        subscribed_message_types: Optional[List[MessageType]] = None,
        config: Optional[Dict[str, Any]] = None,
        engine_monitor=None
    ):
        """
        Initialize the Orchestrator Agent.
        
        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            agent_type: Type of the agent
            message_bus: Message bus for agent communication
            subscribed_message_types: Types of messages this agent subscribes to
            config: Agent configuration dictionary
        """
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            message_bus=message_bus,
            subscribed_message_types=subscribed_message_types or [
                MessageType.TASK_REQUEST,
                MessageType.TASK_RESULT,
                MessageType.ERROR,
                MessageType.STATUS,
                MessageType.QUERY,
                MessageType.QUERY_RESPONSE,
                MessageType.LOG
            ],
            config=config,
            engine_monitor=engine_monitor
        )
        
        # Default configurations
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout = self.config.get("timeout", 60)  # seconds
        self.parallel_execution = self.config.get("parallel_execution", False)
        self.max_queue_size = self.config.get("max_queue_size", 100)
        self.worker_count = self.config.get("worker_count", 2)
        self.task_check_interval = self.config.get("task_check_interval", 0.5)
        self.heartbeat_interval = self.config.get("heartbeat_interval", 30)
        
        # Progress tracking configurations
        self.progress_update_interval = self.config.get("progress_update_interval", 5.0)  # seconds
        self.default_task_timeout = self.config.get("default_task_timeout", 300.0)  # 5 minutes default
        self.enable_progress_events = self.config.get("enable_progress_events", True)
        self.timeout_grace_period = self.config.get("timeout_grace_period", 10.0)  # seconds
        
        # Task queue and agent registry
        self.task_queue = TaskQueue(max_size=self.max_queue_size)
        self.agent_registry = AgentRegistry()
        
        # Store for pending tasks and results
        self.pending_tasks = {}
        self.task_results = {}
        self.error_counts = {}
        
        # Task distribution and worker thread control
        self.task_distribution_thread = None
        self.worker_threads = []
        self.task_event = threading.Event()
        self.shutdown_event = threading.Event()
        
        # Locks for thread safety
        self.task_lock = threading.RLock()
        self.result_lock = threading.RLock()
        
        # Timeout and progress tracking
        self.progress_thread = None
        self.operation_to_task_map = {}  # Map operation IDs to task IDs for cross-referencing
        self.task_progress_events = {}  # Store task progress milestones for event emission
        
        # Task responses and callback registry
        self.task_responses = {}  # task_id -> response
        self.task_callbacks = {}  # task_id -> callback
        
        # Workflow sequences
        self.file_workflow = [
            "bug_detector",
            "relationship_analyst",
            "strategy",
            "implementation",
            "verification"
        ]
        
        self.folder_workflow = [
            "bug_detector",
            "relationship_analyst",
            "priority_analyzer",
            "strategy",
            "implementation",
            "verification",
            "integration_tester"
        ]
        
        # Start task distribution, worker, and progress tracking threads
        self._start_threads()
    
    def _start_threads(self):
        """Start the task distribution, worker, and progress tracking threads."""
        # Start task distribution thread
        self.task_distribution_thread = threading.Thread(
            target=self._task_distribution_loop,
            daemon=True,
            name="OrchestratorTaskDistribution"
        )
        self.task_distribution_thread.start()
        
        # Start worker threads
        for i in range(self.worker_count):
            worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"OrchestratorWorker-{i}"
            )
            worker_thread.start()
            self.worker_threads.append(worker_thread)
            
        # Start progress tracking thread
        self.progress_thread = threading.Thread(
            target=self._progress_tracking_loop,
            daemon=True,
            name="OrchestratorProgressTracking"
        )
        self.progress_thread.start()
        
        logger.info(f"Started task distribution, {self.worker_count} worker threads, and progress tracking")
        
    def _progress_tracking_loop(self):
        """Monitor task progress and handle timeouts."""
        while not self.shutdown_event.is_set():
            try:
                # Get active tasks
                tasks = self.task_queue.get_tasks_by_status("in_progress")
                current_time = time.time()
                
                for task in tasks:
                    # Check for timeout
                    if task.task_start_time and self.timeout > 0:
                        elapsed = current_time - task.task_start_time
                        
                        # Calculate percentage based on elapsed time vs timeout
                        # Cap at 99% until explicitly completed
                        estimated_percentage = min(99.0, (elapsed / self.timeout) * 100.0)
                        
                        # Update operation progress in the engine monitor if available
                        operation_id = task.content.get("_metadata", {}).get("operation_id")
                        if operation_id and self._engine_monitor:
                            # Calculate appropriate step based on workflow stage
                            current_step = task.current_step if hasattr(task, 'current_step') else 1
                            total_steps = task.total_steps if hasattr(task, 'total_steps') else 5
                            
                            # Update the operation progress
                            self._engine_monitor.update_operation(
                                operation_id=operation_id,
                                current_step=current_step,
                                total_steps=total_steps,
                                details={
                                    "estimated_percentage": estimated_percentage,
                                    "elapsed_time": elapsed,
                                    "task_id": task.id,
                                    "status": task.status
                                }
                            )
                            
                            # Emit progress event if enabled
                            if self.enable_progress_events:
                                # Check for milestone events (25%, 50%, 75%)
                                for milestone in [25, 50, 75]:
                                    milestone_key = f"{task.id}_milestone_{milestone}"
                                    if estimated_percentage >= milestone and milestone_key not in self.task_progress_events:
                                        self.task_progress_events[milestone_key] = True
                                        logger.info(f"Task {task.id} reached {milestone}% progress milestone")
                                        
                                        # Broadcast status for monitoring
                                        self.broadcast_status(
                                            status=f"Task {task.id} reached {milestone}% completion",
                                            metadata={
                                                "task_id": task.id,
                                                "progress": milestone,
                                                "event_type": "progress_milestone"
                                            }
                                        )
                            
                            # Check for timeout
                            if elapsed > self.timeout + self.timeout_grace_period:
                                logger.warning(f"Task {task.id} timed out after {elapsed:.1f} seconds (timeout: {self.timeout}s)")
                                
                                # Gracefully cancel the operation
                                with self.task_lock:
                                    # Mark the task as failed due to timeout
                                    task.mark_failed(f"Operation timed out after {elapsed:.1f} seconds")
                                    task.processing_stages.append("Timed out")
                                    self.task_queue.update_task(task)
                                    
                                    # Cancel the operation in the engine monitor
                                    self._engine_monitor.timeout_operation(
                                        operation_id=operation_id,
                                        details={
                                            "task_id": task.id,
                                            "elapsed_time": elapsed,
                                            "timeout": self.timeout
                                        }
                                    )
                                    
                                    # Emit timeout event
                                    self.broadcast_status(
                                        status=f"Task {task.id} timed out after {elapsed:.1f} seconds",
                                        metadata={
                                            "task_id": task.id,
                                            "elapsed_time": elapsed,
                                            "timeout": self.timeout,
                                            "event_type": "timeout"
                                        }
                                    )
                                    
                                    # Remove from pending tasks if present
                                    if task.workflow_id in self.pending_tasks:
                                        del self.pending_tasks[task.workflow_id]
                
                # Sleep for the progress update interval
                time.sleep(self.progress_update_interval)
                
            except Exception as e:
                logger.error(f"Error in progress tracking loop: {str(e)}")
                logger.debug(traceback.format_exc())
                time.sleep(self.progress_update_interval)  # Sleep to avoid spinning on errors
    
    def _task_distribution_loop(self):
        """Main loop for distributing tasks to worker threads."""
        while not self.shutdown_event.is_set():
            try:
                # Get next task from queue based on priority
                task = self.task_queue.get_next_task()
                
                if task is not None and task.status == "pending":
                    # Check if task can be assigned to an agent
                    assigned_agent_id = self._assign_task_to_agent(task)
                    
                    if assigned_agent_id:
                        # Mark task as in progress and assign to agent
                        with self.task_lock:
                            task.mark_started()
                            task.assigned_agent = assigned_agent_id
                            task.task_start_time = time.time()
                            task.processing_stages.append(f"Assigned to agent {assigned_agent_id}")
                            self.task_queue.update_task(task)
                            
                            # Store metadata about assigned agent
                            if not task.content.get("_metadata"):
                                task.content["_metadata"] = {}
                            task.content["_metadata"]["assigned_agent"] = assigned_agent_id
                            task.content["_metadata"]["assigned_at"] = datetime.now().isoformat()
                        
                        # Signal workers that a task is available
                        self.task_event.set()
                        logger.info(f"Task {task.id} assigned to agent {assigned_agent_id}")
                    else:
                        # No agent available for this task, put it back in the queue
                        # with a delay to avoid busy waiting on unavailable agents
                        logger.warning(f"No agent available for task {task.id} with required capabilities: {task.required_capabilities}")
                        task.retry_count += 1
                        task.last_error = "No agent available with required capabilities"
                        
                        # If we've tried too many times, mark as failed
                        if task.retry_count >= task.max_retries:
                            with self.task_lock:
                                task.mark_failed("Failed to find available agent after maximum retries")
                                self.task_queue.update_task(task)
                            logger.error(f"Task {task.id} failed after {task.retry_count} attempts to find an agent")
                        else:
                            # Record this attempt in processing stages
                            task.processing_stages.append(f"No agent available (attempt {task.retry_count})")
                            self.task_queue.update_task(task)
                            # Sleep a bit longer than normal to allow agents to become available
                            time.sleep(self.task_check_interval * 2)
                
                # Sleep a bit to avoid busy waiting
                time.sleep(self.task_check_interval)
            
            except Exception as e:
                logger.error(f"Error in task distribution loop: {str(e)}")
                logger.debug(traceback.format_exc())
    
    def _assign_task_to_agent(self, task: Task) -> Optional[str]:
        """
        Assign a task to an appropriate agent based on capabilities or target agent type.
        
        Args:
            task: The task to assign
            
        Returns:
            ID of the assigned agent or None if no suitable agent found
        """
        # If a target agent type is specified, try to find an agent of that type
        if task.target_agent_type:
            # Find an agent of the specified type
            for agent_id, agent_info in self.agent_registry.agents.items():
                if agent_info["agent_type"] == task.target_agent_type and self.agent_registry.is_agent_available(agent_id):
                    return agent_id
            
            # No agent of the specified type found
            logger.warning(f"No available agent of type {task.target_agent_type} found for task {task.id}")
            return None
        
        # If required capabilities are specified, find an agent with those capabilities
        if task.required_capabilities:
            # Find an agent with all required capabilities
            capable_agents = set()
            
            # For the first capability, get all agents
            if not task.required_capabilities:
                # If no capabilities required, any agent will do
                for agent_id in self.agent_registry.agents.keys():
                    if self.agent_registry.is_agent_available(agent_id):
                        return agent_id
                return None
            
            # Start with agents having the first capability
            first_capability = task.required_capabilities[0]
            agents_with_capability = self.agent_registry.capabilities.get(first_capability, [])
            capable_agents = set(agents_with_capability)
            
            # Intersect with agents having other capabilities
            for capability in task.required_capabilities[1:]:
                agents_with_capability = set(self.agent_registry.capabilities.get(capability, []))
                capable_agents &= agents_with_capability
            
            # Filter for available agents
            available_capable_agents = [
                agent_id for agent_id in capable_agents 
                if self.agent_registry.is_agent_available(agent_id)
            ]
            
            if available_capable_agents:
                # For now, just pick the first one
                # In a more advanced implementation, could do load balancing
                return available_capable_agents[0]
            
            # No agent with all required capabilities found
            logger.warning(f"No available agent with capabilities {task.required_capabilities} found for task {task.id}")
            return None
        
        # If no specific requirements, just find any available agent
        for agent_id in self.agent_registry.agents.keys():
            if self.agent_registry.is_agent_available(agent_id):
                return agent_id
        
        # No available agent found
        logger.warning(f"No available agent found for task {task.id}")
        return None
    
    def _worker_loop(self):
        """Worker loop for processing tasks."""
        while not self.shutdown_event.is_set():
            try:
                # Wait for task to be available
                self.task_event.wait(self.task_check_interval)
                self.task_event.clear()
                
                # Look for in_progress tasks
                in_progress_tasks = self.task_queue.get_tasks_by_status("in_progress")
                
                if not in_progress_tasks:
                    continue
                
                # Try to claim a task using task_lock to avoid race conditions
                task = None
                with self.task_lock:
                    for t in in_progress_tasks:
                        # Check if task is being processed by another worker
                        if t.workflow_id not in self.pending_tasks:
                            task = t
                            self.pending_tasks[t.workflow_id] = True
                            break
                
                if task is None:
                    continue
                
                # Process the task
                try:
                    logger.info(f"Processing task {task.id} of type {task.type}")
                    
                    if task.type == "file_healing":
                        result = self._process_file_healing_task(task)
                    elif task.type == "folder_healing":
                        result = self._process_folder_healing_task(task)
                    else:
                        result = {"status": "failed", "error": f"Unknown task type: {task.type}"}
                    
                    # Mark task as completed
                    with self.task_lock:
                        task.mark_completed(result)
                        self.task_queue.update_task(task)
                        
                        # Store result
                        with self.result_lock:
                            self.task_results[task.id] = result
                        
                        # Execute callback if registered
                        if task.id in self.task_callbacks:
                            callback = self.task_callbacks[task.id]
                            try:
                                callback(result)
                            except Exception as e:
                                logger.error(f"Error executing callback for task {task.id}: {str(e)}")
                        
                        # Remove from pending tasks
                        if task.workflow_id in self.pending_tasks:
                            del self.pending_tasks[task.workflow_id]
                
                except Exception as e:
                    logger.error(f"Error processing task {task.id}: {str(e)}")
                    logger.debug(traceback.format_exc())
                    
                    # Mark task as failed
                    with self.task_lock:
                        task.mark_failed(str(e))
                        self.task_queue.update_task(task)
                        
                        # Check if task can be retried
                        if task.can_retry(self.max_retries):
                            logger.info(f"Retrying task {task.id} (attempt {task.attempts}/{self.max_retries})")
                            task.status = "pending"
                            self.task_queue.update_task(task)
                        else:
                            # Store failure result
                            with self.result_lock:
                                self.task_results[task.id] = {
                                    "status": "failed",
                                    "error": str(e),
                                    "task_id": task.id
                                }
                            
                            # Execute callback if registered
                            if task.id in self.task_callbacks:
                                callback = self.task_callbacks[task.id]
                                try:
                                    callback({"status": "failed", "error": str(e)})
                                except Exception as e:
                                    logger.error(f"Error executing callback for task {task.id}: {str(e)}")
                        
                        # Remove from pending tasks
                        if task.workflow_id in self.pending_tasks:
                            del self.pending_tasks[task.workflow_id]
            
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
                logger.debug(traceback.format_exc())
    
    def shutdown(self):
        """Shutdown the agent and its threads."""
        logger.info("Shutting down OrchestratorAgent")
        self.shutdown_event.set()
        
        # Wait for worker threads to terminate
        for thread in self.worker_threads:
            thread.join(timeout=5.0)
        
        # Wait for task distribution thread to terminate
        if self.task_distribution_thread:
            self.task_distribution_thread.join(timeout=5.0)
            
        # Wait for progress tracking thread to terminate
        if self.progress_thread:
            self.progress_thread.join(timeout=5.0)
        
        # Cancel any active operations in the engine monitor
        if self._engine_monitor:
            active_tasks = self.task_queue.get_tasks_by_status("in_progress")
            for task in active_tasks:
                operation_id = task.content.get("_metadata", {}).get("operation_id")
                if operation_id:
                    try:
                        self._engine_monitor.cancel_operation(
                            operation_id=operation_id,
                            details={"reason": "Agent shutdown"}
                        )
                    except Exception as e:
                        logger.error(f"Error cancelling operation {operation_id}: {str(e)}")
        
        logger.info("OrchestratorAgent shutdown complete")
    
    def enqueue_task(
        self,
        task_type: str,
        content: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        sender: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        required_capabilities: Optional[List[str]] = None,
        target_agent_type: Optional[str] = None,
        timeout_seconds: Optional[float] = None
    ) -> str:
        """
        Enqueue a task for execution.
        
        Args:
            task_type: Type of task (e.g., 'file_healing', 'folder_healing')
            content: Task content/parameters
            priority: Priority level of the task
            sender: ID of the agent that sent the task request
            callback: Optional callback function to execute when task completes
            required_capabilities: List of capabilities required to execute this task
            target_agent_type: Specific agent type to target (bypasses capability-based routing)
            
        Returns:
            ID of the enqueued task
        """
        # Generate workflow ID and task ID
        workflow_id = f"{task_type}_{self._generate_id()}"
        task_id = f"task_{self._generate_id()}"
        
        # Use custom timeout if provided, otherwise use default task timeout
        timeout_seconds = timeout_seconds or self.default_task_timeout
        
        # Create task
        task = Task(
            id=task_id,
            type=task_type,
            priority=priority,
            content=content,
            workflow_id=workflow_id,
            created_at=datetime.now(),
            sender=sender,
            required_capabilities=required_capabilities or [],
            target_agent_type=target_agent_type,
            max_retries=self.max_retries
        )
        
        # Store metadata about task in content for reference
        if not task.content.get("_metadata"):
            task.content["_metadata"] = {}
        
        task.content["_metadata"]["task_id"] = task_id
        task.content["_metadata"]["workflow_id"] = workflow_id
        task.content["_metadata"]["created_at"] = task.created_at.isoformat()
        task.content["_metadata"]["priority"] = str(priority)
        
        # Add task to queue
        self.task_queue.add_task(task)
        
        # Register callback if provided
        if callback:
            self.task_callbacks[task_id] = callback
            
        # Create operation tracking if engine monitor is available
        if self._engine_monitor:
            operation_id = self._engine_monitor.create_operation(
                operation_type=task_type,
                total_steps=5,  # Typical workflow has 5 steps
                timeout_seconds=timeout_seconds,
                cancel_callback=lambda: self.cancel_task(task_id)
            )
            self._engine_monitor.start_operation(operation_id)
            
            # Store operation ID in task metadata
            if not task.content.get("_metadata"):
                task.content["_metadata"] = {}
            task.content["_metadata"]["operation_id"] = operation_id
            
            # Map operation ID to task ID for lookup
            self.operation_to_task_map[operation_id] = task_id
            
            # Update task in queue with metadata
            self.task_queue.update_task(task)
        
        logger.info(f"Enqueued {task_type} task with ID {task_id} and priority {priority}")
        
        # Signal that a new task is available
        self.task_event.set()
        
        return task_id
    
    def _process_file_healing_task(self, task: Task) -> Dict[str, Any]:
        """
        Process a file healing task.
        
        Args:
            task: The task to process
            
        Returns:
            Result of the file healing process
        """
        content = task.content
        file_path = content.get("file_path")
        options = content.get("options", {})
        
        if not file_path:
            raise ValueError("file_path is required for file_healing tasks")
        
        return self.orchestrate_file_healing(file_path, options)
    
    def _process_folder_healing_task(self, task: Task) -> Dict[str, Any]:
        """
        Process a folder healing task.
        
        Args:
            task: The task to process
            
        Returns:
            Result of the folder healing process
        """
        content = task.content
        folder_path = content.get("folder_path")
        options = content.get("options", {})
        
        if not folder_path:
            raise ValueError("folder_path is required for folder_healing tasks")
        
        return self.orchestrate_folder_healing(folder_path, options)
    
    def orchestrate_file_healing(
        self,
        file_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate the self-healing process for a single file.
        
        Args:
            file_path: Path to the file to heal
            options: Optional configuration for the healing process
            
        Returns:
            Results of the healing process
        """
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        logger.info(f"Orchestrating self-healing for file: {file_path}")
        
        options = options or {}
        
        # Create a workflow ID for this healing process
        workflow_id = f"file_heal_{self._generate_id()}"
        
        # Initialize workflow state
        workflow_state = {
            "id": workflow_id,
            "type": "file_healing",
            "target": file_path,
            "options": options,
            "start_time": time.time(),
            "end_time": None,
            "current_step": 0,
            "total_steps": len(self.file_workflow),
            "steps_completed": [],
            "steps_failed": [],
            "results": {},
            "status": "in_progress"
        }
        
        self.pending_tasks[workflow_id] = workflow_state
        
        try:
            # Execute each step in the workflow
            for step_index, agent_type in enumerate(self.file_workflow):
                workflow_state["current_step"] = step_index + 1
                
                # Execute the current step
                step_result = self._execute_workflow_step(
                    workflow_id, agent_type, workflow_state)
                
                # Store the result
                workflow_state["results"][agent_type] = step_result
                
                if step_result.get("status") == "success":
                    workflow_state["steps_completed"].append(agent_type)
                else:
                    workflow_state["steps_failed"].append(agent_type)
                    logger.warning(f"Step {agent_type} failed for {file_path}")
                    
                    # If a critical step fails, abort the workflow
                    if self._is_critical_step(agent_type):
                        logger.error(f"Critical step {agent_type} failed, aborting workflow")
                        workflow_state["status"] = "failed"
                        break
            
            # If all steps completed successfully, mark the workflow as complete
            if len(workflow_state["steps_completed"]) == len(self.file_workflow):
                workflow_state["status"] = "completed"
                
                # Mark any associated operation as complete
                if workflow_id in workflow_state.get("_metadata", {}).get("operation_id"):
                    operation_id = workflow_state["_metadata"]["operation_id"]
                    if self._engine_monitor and operation_id:
                        self._engine_monitor.complete_operation(
                            operation_id=operation_id,
                            details={
                                "workflow_id": workflow_id,
                                "status": "completed",
                                "steps_completed": workflow_state["steps_completed"]
                            }
                        )
            elif workflow_state["status"] != "failed":
                workflow_state["status"] = "partial_success"
                
            # Calculate metrics
            workflow_state["metrics"] = self._calculate_metrics(workflow_state)
            
        except Exception as e:
            logger.error(f"Error orchestrating file healing: {str(e)}")
            logger.debug(traceback.format_exc())
            workflow_state["status"] = "failed"
            workflow_state["error"] = str(e)
            
        except Exception as e:
            logger.error(f"Error orchestrating file healing: {str(e)}")
            logger.debug(traceback.format_exc())
            workflow_state["status"] = "failed"
            workflow_state["error"] = str(e)
        
        # Finalize workflow
        workflow_state["end_time"] = time.time()
        
        # Remove from pending tasks
        if workflow_id in self.pending_tasks:
            del self.pending_tasks[workflow_id]
        
        # Store in task results
        self.task_results[workflow_id] = workflow_state
        
        return workflow_state
    
    def orchestrate_folder_healing(
        self,
        folder_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate the self-healing process for an entire folder/repository.
        
        Args:
            folder_path: Path to the folder to heal
            options: Optional configuration for the healing process
            
        Returns:
            Results of the healing process
        """
        if not os.path.isdir(folder_path):
            raise ValueError(f"Folder not found: {folder_path}")
        
        logger.info(f"Orchestrating self-healing for folder: {folder_path}")
        
        options = options or {}
        
        # Create a workflow ID for this healing process
        workflow_id = f"folder_heal_{self._generate_id()}"
        
        # Initialize workflow state
        workflow_state = {
            "id": workflow_id,
            "type": "folder_healing",
            "target": folder_path,
            "options": options,
            "start_time": time.time(),
            "end_time": None,
            "current_step": 0,
            "total_steps": len(self.folder_workflow),
            "steps_completed": [],
            "steps_failed": [],
            "results": {},
            "status": "in_progress",
            "files_processed": [],
            "files_healed": [],
            "files_failed": [],
            "bugs_detected": 0,
            "bugs_fixed": 0
        }
        
        self.pending_tasks[workflow_id] = workflow_state
        
        try:
            # Execute large-scale analysis steps
            for step_index, agent_type in enumerate(self.folder_workflow[:3]):
                workflow_state["current_step"] = step_index + 1
                
                # Execute analysis step
                step_result = self._execute_folder_analysis_step(
                    workflow_id, agent_type, folder_path, workflow_state)
                
                # Store the result
                workflow_state["results"][agent_type] = step_result
                
                if step_result.get("status") == "success":
                    workflow_state["steps_completed"].append(agent_type)
                else:
                    workflow_state["steps_failed"].append(agent_type)
                    logger.warning(f"Step {agent_type} failed for {folder_path}")
                    
                    # If a critical analysis step fails, abort the workflow
                    if self._is_critical_step(agent_type):
                        logger.error(f"Critical step {agent_type} failed, aborting workflow")
                        workflow_state["status"] = "failed"
                        return workflow_state
            
            # Get the prioritized list of files to process
            prioritized_files = self._get_prioritized_files(workflow_state)
            total_files = len(prioritized_files)
            
            logger.info(f"Processing {total_files} files in prioritized order")
            
            # Process each file in order
            for file_index, file_info in enumerate(prioritized_files):
                file_path = file_info["file_path"]
                logger.info(f"Processing file {file_index + 1}/{total_files}: {file_path}")
                
                # Try to heal this file
                file_result = self._heal_single_file_in_folder(
                    workflow_id, file_path, file_info, workflow_state)
                
                workflow_state["files_processed"].append(file_path)
                
                if file_result.get("status") == "success":
                    workflow_state["files_healed"].append(file_path)
                    workflow_state["bugs_fixed"] += file_result.get("bugs_fixed", 0)
                else:
                    workflow_state["files_failed"].append(file_path)
            
            # Run integration tests
            integration_result = self._run_integration_tests(workflow_id, folder_path, workflow_state)
            workflow_state["results"]["integration_tester"] = integration_result
            
            if integration_result.get("status") == "success":
                workflow_state["steps_completed"].append("integration_tester")
            else:
                workflow_state["steps_failed"].append("integration_tester")
            
            # Set the overall status based on results
            if len(workflow_state["files_failed"]) == 0 and len(workflow_state["files_healed"]) > 0:
                workflow_state["status"] = "completed"
            elif len(workflow_state["files_healed"]) > 0:
                workflow_state["status"] = "partial_success"
            else:
                workflow_state["status"] = "failed"
            
            # Calculate metrics
            workflow_state["metrics"] = self._calculate_folder_metrics(workflow_state)
            
        except Exception as e:
            logger.error(f"Error orchestrating folder healing: {str(e)}")
            logger.debug(traceback.format_exc())
            workflow_state["status"] = "failed"
            workflow_state["error"] = str(e)
        
        # Finalize workflow
        workflow_state["end_time"] = time.time()
        
        # Remove from pending tasks
        if workflow_id in self.pending_tasks:
            del self.pending_tasks[workflow_id]
        
        # Store in task results
        self.task_results[workflow_id] = workflow_state
        
        return workflow_state
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            The task status or None if not found
        """
        # Check pending tasks first
        if task_id in self.pending_tasks:
            return self.pending_tasks[task_id]
        
        # Then check completed tasks
        if task_id in self.task_results:
            return self.task_results[task_id]
        
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: The ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        # First, check the task queue for the task
        task = self.task_queue.get_task(task_id)
        if task:
            with self.task_lock:
                # Mark the task as cancelled
                task.status = "cancelled"
                task.completed_at = datetime.now()
                task.processing_stages.append("Cancelled by user request")
                self.task_queue.update_task(task)
                
                # Cancel any associated operation
                operation_id = task.content.get("_metadata", {}).get("operation_id")
                if operation_id and self._engine_monitor:
                    self._engine_monitor.cancel_operation(
                        operation_id=operation_id,
                        details={
                            "reason": "Cancelled by user request",
                            "task_id": task_id
                        }
                    )
                
                # If the task is part of a workflow, cancel it as well
                if task.workflow_id in self.pending_tasks:
                    self.pending_tasks[task.workflow_id]["status"] = "cancelled"
                    self.pending_tasks[task.workflow_id]["end_time"] = time.time()
                    
                    # Move to completed tasks
                    self.task_results[task.workflow_id] = self.pending_tasks[task.workflow_id]
                    del self.pending_tasks[task.workflow_id]
                
                logger.info(f"Task {task_id} cancelled")
                return True
                
        # Otherwise, check the traditional pending tasks dict
        elif task_id in self.pending_tasks:
            task = self.pending_tasks[task_id]
            task["status"] = "cancelled"
            task["end_time"] = time.time()
            
            # Move to completed tasks
            self.task_results[task_id] = task
            del self.pending_tasks[task_id]
            
            logger.info(f"Task {task_id} cancelled")
            return True
        
        logger.warning(f"Task {task_id} not found or already completed")
        return False
    
    def _execute_workflow_step(
        self,
        workflow_id: str,
        agent_type: str,
        workflow_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single step in the workflow.
        
        Args:
            workflow_id: The ID of the workflow
            agent_type: The type of agent to execute
            workflow_state: The current state of the workflow
            
        Returns:
            Result of the step execution
        """
        logger.info(f"Executing workflow step: {agent_type}")
        
        # Update operation progress if we have an engine monitor
        operation_id = workflow_state.get("_metadata", {}).get("operation_id")
        if operation_id and self._engine_monitor:
            # Calculate steps based on workflow stage
            step_index = self.file_workflow.index(agent_type) if agent_type in self.file_workflow else workflow_state.get("current_step", 0)
            total_steps = len(self.file_workflow)
            
            # Update operation progress
            self._engine_monitor.update_operation(
                operation_id=operation_id,
                current_step=step_index + 1,
                total_steps=total_steps,
                details={
                    "current_agent": agent_type,
                    "workflow_id": workflow_id,
                    "step_description": f"Executing {agent_type} step"
                }
            )
        
        # Get the target file path
        file_path = workflow_state["target"]
        
        # Prepare the message based on the agent type
        if agent_type == "bug_detector":
            message = self._prepare_bug_detector_message(workflow_id, file_path)
        elif agent_type == "relationship_analyst":
            message = self._prepare_relationship_analyst_message(workflow_id, file_path)
        elif agent_type == "strategy":
            message = self._prepare_strategy_message(workflow_id, file_path, workflow_state)
        elif agent_type == "implementation":
            message = self._prepare_implementation_message(workflow_id, file_path, workflow_state)
        elif agent_type == "verification":
            message = self._prepare_verification_message(workflow_id, file_path, workflow_state)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Send the message and wait for response
        self.message_bus.publish(message)
        
        # Wait for the result with timeout
        result = self._wait_for_result(workflow_id, agent_type, self.timeout)
        
        if result:
            logger.info(f"Step {agent_type} completed successfully")
            return result
        else:
            logger.warning(f"Step {agent_type} timed out or failed")
            return {"status": "failed", "error": "Timeout or no response"}
    
    def _execute_folder_analysis_step(
        self,
        workflow_id: str,
        agent_type: str,
        folder_path: str,
        workflow_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a folder analysis step in the workflow.
        
        Args:
            workflow_id: The ID of the workflow
            agent_type: The type of agent to execute
            folder_path: Path to the folder being analyzed
            workflow_state: The current state of the workflow
            
        Returns:
            Result of the step execution
        """
        logger.info(f"Executing folder analysis step: {agent_type}")
        
        # Prepare the message based on the agent type
        if agent_type == "bug_detector":
            message = self._prepare_folder_bug_detection_message(workflow_id, folder_path)
        elif agent_type == "relationship_analyst":
            message = self._prepare_folder_relationship_analysis_message(workflow_id, folder_path)
        elif agent_type == "priority_analyzer":
            message = self._prepare_priority_analysis_message(workflow_id, folder_path, workflow_state)
        else:
            raise ValueError(f"Unknown analysis agent type: {agent_type}")
        
        # Send the message and wait for response
        self.message_bus.publish(message)
        
        # Wait for the result with timeout
        result = self._wait_for_result(workflow_id, agent_type, self.timeout * 10)  # Much longer timeout for folder analysis
        
        if result:
            logger.info(f"Folder analysis step {agent_type} completed successfully")
            return result
        else:
            logger.warning(f"Folder analysis step {agent_type} timed out or failed")
            logger.warning(f"Step {agent_type} failed for {folder_path}")
            
            # Create a fallback response if needed to continue workflow
            if agent_type == "bug_detector":
                # Return empty bug results to allow workflow to continue
                logger.info(f"Creating fallback response for bug_detector to continue workflow")
                return {
                    "status": "partial_success",
                    "bugs_by_file": {},
                    "total_bugs": 0,
                    "files_analyzed": 0,
                    "files_with_bugs": 0,
                    "error": "Timeout or no response from bug detector"
                }
            # For other agent types, just fail that step but in a way that allows continue
            else:
                logger.warning(f"No fallback for {agent_type}, returning failure status")
                return {"status": "failed", "error": "Timeout or no response"}
        return {"status": "failed", "error": "Timeout or no response"}
    
    def _heal_single_file_in_folder(
        self,
        workflow_id: str,
        file_path: str,
        file_info: Dict[str, Any],
        workflow_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Heal a single file as part of folder healing.
        
        Args:
            workflow_id: The ID of the workflow
            file_path: Path to the file to heal
            file_info: Information about the file (bugs, priority, etc.)
            workflow_state: The current state of the workflow
            
        Returns:
            Result of healing the file
        """
        logger.info(f"Healing file within folder: {file_path}")
        
        # Get bug information for this file
        bugs = file_info.get("bugs", [])
        if not bugs:
            logger.info(f"No bugs to fix in {file_path}")
            return {"status": "success", "bugs_fixed": 0}
        
        # Get relationship information
        relationships = workflow_state["results"].get("relationship_analyst", {}).get("relationships", {})
        file_relationships = {k: v for k, v in relationships.items() if k == file_path or v.get("file_path") == file_path}
        
        # Process each bug in the file
        bugs_fixed = 0
        
        for bug in bugs:
            # Prepare strategy
            strategy_message = self._prepare_file_strategy_message(
                workflow_id, file_path, bug, file_relationships)
            
            self.message_bus.publish(strategy_message)
            strategy_result = self._wait_for_result(workflow_id, "strategy", self.timeout)
            
            if not strategy_result or strategy_result.get("status") != "success":
                logger.warning(f"Failed to formulate strategy for bug in {file_path}")
                continue
            
            strategy = strategy_result.get("strategy", {})
            
            # Implement the fix
            implement_message = self._prepare_file_implementation_message(
                workflow_id, file_path, strategy)
            
            self.message_bus.publish(implement_message)
            implement_result = self._wait_for_result(workflow_id, "implementation", self.timeout)
            
            if not implement_result or implement_result.get("status") != "success":
                logger.warning(f"Failed to implement fix for bug in {file_path}")
                continue
            
            implementation = implement_result.get("implementation", {})
            
            # Apply the fix (not in dry run mode for folder healing)
            apply_message = self._prepare_apply_implementation_message(
                workflow_id, implementation, False)  # Not dry run
            
            self.message_bus.publish(apply_message)
            apply_result = self._wait_for_result(workflow_id, "apply_implementation", self.timeout)
            
            if not apply_result or apply_result.get("status") != "success":
                logger.warning(f"Failed to apply fix for bug in {file_path}")
                continue
            
            # Verify the fix
            verify_message = self._prepare_file_verification_message(
                workflow_id, implementation, strategy, bug)
            
            self.message_bus.publish(verify_message)
            verify_result = self._wait_for_result(workflow_id, "verification", self.timeout)
            
            if not verify_result or verify_result.get("success") != True:
                logger.warning(f"Fix verification failed for bug in {file_path}")
                continue
            
            # Bug fixed successfully
            bugs_fixed += 1
        
        return {
            "status": "success" if bugs_fixed > 0 else "failed",
            "bugs_fixed": bugs_fixed,
            "total_bugs": len(bugs)
        }
    
    def _run_integration_tests(
        self,
        workflow_id: str,
        folder_path: str,
        workflow_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run integration tests after folder healing.
        
        Args:
            workflow_id: The ID of the workflow
            folder_path: Path to the folder
            workflow_state: The current state of the workflow
            
        Returns:
            Result of running integration tests
        """
        logger.info(f"Running integration tests for folder: {folder_path}")
        
        # Look for test files in the folder
        test_files = self._find_test_files(folder_path)
        
        if not test_files:
            logger.info("No test files found, skipping integration tests")
            return {"status": "skipped", "reason": "No test files found"}
        
        # Run the tests
        test_results = []
        
        for test_file in test_files:
            result = self._run_test(test_file, folder_path)
            test_results.append({
                "file": test_file,
                "success": result.get("success", False),
                "output": result.get("output", ""),
                "error": result.get("error", "")
            })
        
        # Check if all tests passed
        all_passed = all(result["success"] for result in test_results)
        
        return {
            "status": "success" if all_passed else "failed",
            "test_results": test_results,
            "tests_passed": sum(1 for result in test_results if result["success"]),
            "tests_failed": sum(1 for result in test_results if not result["success"]),
            "total_tests": len(test_results)
        }
    
    def _find_test_files(self, folder_path: str) -> List[str]:
        """
        Find test files in a folder.
        
        Args:
            folder_path: Path to the folder
            
        Returns:
            List of test file paths
        """
        test_files = []
        
        # Check for a tests directory
        tests_dir = os.path.join(folder_path, "tests")
        if os.path.isdir(tests_dir):
            for root, _, files in os.walk(tests_dir):
                for file in files:
                    if file.startswith("test_") and file.endswith(".py"):
                        test_files.append(os.path.join(root, file))
        
        # Look for test files in the main directory
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    test_path = os.path.join(root, file)
                    if test_path not in test_files:
                        test_files.append(test_path)
        
        return test_files
    
    def _run_test(self, test_file: str, working_dir: str) -> Dict[str, Any]:
        """
        Run a test file.
        
        Args:
            test_file: Path to the test file
            working_dir: Working directory for the test
            
        Returns:
            Result of running the test
        """
        import subprocess
        import sys
        
        try:
            # Change to the working directory
            cwd = os.getcwd()
            os.chdir(working_dir)
            
            # Run the test
            process = subprocess.run(
                [sys.executable, "-m", "unittest", test_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                text=True
            )
            
            # Change back to the original directory
            os.chdir(cwd)
            
            # Check the result
            success = process.returncode == 0
            
            return {
                "success": success,
                "output": process.stdout,
                "error": process.stderr,
                "returncode": process.returncode
            }
            
        except subprocess.TimeoutExpired:
            # Change back to the original directory
            os.chdir(cwd)
            return {
                "success": False,
                "output": "",
                "error": f"Test timed out after {self.timeout} seconds",
                "returncode": -1
            }
            
        except Exception as e:
            # Change back to the original directory
            os.chdir(cwd)
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1
            }
    
    def _get_prioritized_files(self, workflow_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get a prioritized list of files to process.
        
        Args:
            workflow_state: The current state of the workflow
            
        Returns:
            Prioritized list of files
        """
        # Get bug detection results
        bug_detection_result = workflow_state["results"].get("bug_detector", {})
        bugs_by_file = bug_detection_result.get("bugs_by_file", {})
        
        # Get priority analysis results
        priority_result = workflow_state["results"].get("priority_analyzer", {})
        file_priorities = priority_result.get("file_priorities", {})
        
        # Combine bug information with priorities
        prioritized_files = []
        
        for file_path, bugs in bugs_by_file.items():
            priority = file_priorities.get(file_path, {}).get("priority", 0)
            
            prioritized_files.append({
                "file_path": file_path,
                "bugs": bugs,
                "priority": priority,
                "bug_count": len(bugs)
            })
        
        # Sort by priority (higher first) and then bug count (higher first)
        prioritized_files.sort(key=lambda x: (-x["priority"], -x["bug_count"]))
        
        return prioritized_files
    
    def _prepare_bug_detector_message(
        self,
        workflow_id: str,
        file_path: str
    ) -> AgentMessage:
        """
        Prepare a message for the Bug Detector Agent.
        
        Args:
            workflow_id: The ID of the workflow
            file_path: Path to the file to analyze
            
        Returns:
            Message for the Bug Detector Agent
        """
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "detect_bugs_in_file",
                "file_path": file_path,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="bug_detector"
        )
    
    def _prepare_relationship_analyst_message(
        self,
        workflow_id: str,
        file_path: str
    ) -> AgentMessage:
        """
        Prepare a message for the Relationship Analyst Agent.
        
        Args:
            workflow_id: The ID of the workflow
            file_path: Path to the file to analyze
            
        Returns:
            Message for the Relationship Analyst Agent
        """
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "analyze_file_relationships",
                "file_path": file_path,
                "max_depth": 2,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="relationship_analyst"
        )
    
    def _prepare_strategy_message(
        self,
        workflow_id: str,
        file_path: str,
        workflow_state: Dict[str, Any]
    ) -> AgentMessage:
        """
        Prepare a message for the Strategy Agent.
        
        Args:
            workflow_id: The ID of the workflow
            file_path: Path to the file to analyze
            workflow_state: The current state of the workflow
            
        Returns:
            Message for the Strategy Agent
        """
        # Get bug information
        bug_detection_result = workflow_state["results"].get("bug_detector", {})
        bugs = bug_detection_result.get("bugs", [])
        
        if not bugs:
            raise ValueError("No bugs found to formulate strategy")
        
        # Get relationship information
        relationship_result = workflow_state["results"].get("relationship_analyst", {})
        relationships = relationship_result.get("relationships", {})
        
        # Use the first bug for demonstration
        bug = bugs[0]
        
        # Prepare code context
        with open(file_path, 'r') as f:
            code_content = f.read()
        
        code_context = {
            "language": os.path.splitext(file_path)[1][1:],  # Get extension without dot
            "file_content": code_content,
            "file_path": file_path
        }
        
        # Prepare relationship context
        relationship_context = {
            "file_relationships": relationships
        }
        
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "formulate_strategy",
                "bug_report": bug,
                "code_context": code_context,
                "relationship_context": relationship_context,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="strategy_agent"
        )
    
    def _prepare_implementation_message(
        self,
        workflow_id: str,
        file_path: str,
        workflow_state: Dict[str, Any]
    ) -> AgentMessage:
        """
        Prepare a message for the Implementation Agent.
        
        Args:
            workflow_id: The ID of the workflow
            file_path: Path to the file to analyze
            workflow_state: The current state of the workflow
            
        Returns:
            Message for the Implementation Agent
        """
        # Get strategy information
        strategy_result = workflow_state["results"].get("strategy_agent", {})
        strategy = strategy_result.get("strategy", {})
        
        if not strategy:
            raise ValueError("No strategy found to implement")
        
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "implement_strategy",
                "strategy": strategy,
                "additional_context": {},
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="implementation_agent"
        )
    
    def _prepare_verification_message(
        self,
        workflow_id: str,
        file_path: str,
        workflow_state: Dict[str, Any]
    ) -> AgentMessage:
        """
        Prepare a message for the Verification Agent.
        
        Args:
            workflow_id: The ID of the workflow
            file_path: Path to the file to analyze
            workflow_state: The current state of the workflow
            
        Returns:
            Message for the Verification Agent
        """
        # Get implementation information
        implementation_result = workflow_state["results"].get("implementation_agent", {})
        implementation = implementation_result.get("implementation", {})
        
        if not implementation:
            raise ValueError("No implementation found to verify")
        
        # Get strategy information
        strategy_result = workflow_state["results"].get("strategy_agent", {})
        strategy = strategy_result.get("strategy", {})
        
        # Get bug information
        bug_detection_result = workflow_state["results"].get("bug_detector", {})
        bugs = bug_detection_result.get("bugs", [])
        
        if not bugs:
            raise ValueError("No bugs found to verify fix for")
        
        # Use the first bug for demonstration
        bug = bugs[0]
        
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "verify_implementation",
                "implementation": implementation,
                "strategy": strategy,
                "bug_report": bug,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="verification_agent"
        )
    
    def _prepare_folder_bug_detection_message(
        self,
        workflow_id: str,
        folder_path: str
    ) -> AgentMessage:
        """
        Prepare a message for folder-level bug detection.
        
        Args:
            workflow_id: The ID of the workflow
            folder_path: Path to the folder to analyze
            
        Returns:
            Message for the Bug Detector Agent
        """
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "detect_bugs_in_folder",
                "folder_path": folder_path,
                "recursive": True,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="bug_detector"
        )
    
    def _prepare_folder_relationship_analysis_message(
        self,
        workflow_id: str,
        folder_path: str
    ) -> AgentMessage:
        """
        Prepare a message for folder-level relationship analysis.
        
        Args:
            workflow_id: The ID of the workflow
            folder_path: Path to the folder to analyze
            
        Returns:
            Message for the Relationship Analyst Agent
        """
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "analyze_folder_relationships",
                "folder_path": folder_path,
                "max_depth": 3,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="relationship_analyst"
        )
    
    def _prepare_priority_analysis_message(
        self,
        workflow_id: str,
        folder_path: str,
        workflow_state: Dict[str, Any]
    ) -> AgentMessage:
        """
        Prepare a message for priority analysis.
        
        Args:
            workflow_id: The ID of the workflow
            folder_path: Path to the folder to analyze
            workflow_state: The current state of the workflow
            
        Returns:
            Message for the Priority Analyzer Agent
        """
        # Get bug detection results
        bug_detection_result = workflow_state["results"].get("bug_detector", {})
        bugs_by_file = bug_detection_result.get("bugs_by_file", {})
        
        # Get relationship analysis results
        relationship_result = workflow_state["results"].get("relationship_analyst", {})
        relationships = relationship_result.get("relationships", {})
        
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "analyze_priorities",
                "folder_path": folder_path,
                "bugs_by_file": bugs_by_file,
                "relationships": relationships,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="priority_analyzer"
        )
    
    def _prepare_file_strategy_message(
        self,
        workflow_id: str,
        file_path: str,
        bug: Dict[str, Any],
        file_relationships: Dict[str, Any]
    ) -> AgentMessage:
        """
        Prepare a message for strategy formulation for a single bug.
        
        Args:
            workflow_id: The ID of the workflow
            file_path: Path to the file containing the bug
            bug: The bug to formulate a strategy for
            file_relationships: Relationships for this file
            
        Returns:
            Message for the Strategy Agent
        """
        # Prepare code context
        with open(file_path, 'r') as f:
            code_content = f.read()
        
        code_context = {
            "language": os.path.splitext(file_path)[1][1:],  # Get extension without dot
            "file_content": code_content,
            "file_path": file_path
        }
        
        # Prepare relationship context
        relationship_context = {
            "file_relationships": file_relationships
        }
        
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "formulate_strategy",
                "bug_report": bug,
                "code_context": code_context,
                "relationship_context": relationship_context,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="strategy_agent"
        )
    
    def _prepare_file_implementation_message(
        self,
        workflow_id: str,
        file_path: str,
        strategy: Dict[str, Any]
    ) -> AgentMessage:
        """
        Prepare a message for implementation of a strategy.
        
        Args:
            workflow_id: The ID of the workflow
            file_path: Path to the file to modify
            strategy: The strategy to implement
            
        Returns:
            Message for the Implementation Agent
        """
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "implement_strategy",
                "strategy": strategy,
                "additional_context": {
                    "file_path": file_path
                },
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="implementation_agent"
        )
    
    def _prepare_apply_implementation_message(
        self,
        workflow_id: str,
        implementation: Dict[str, Any],
        dry_run: bool
    ) -> AgentMessage:
        """
        Prepare a message to apply an implementation.
        
        Args:
            workflow_id: The ID of the workflow
            implementation: The implementation to apply
            dry_run: Whether to perform a dry run
            
        Returns:
            Message for the Implementation Agent
        """
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "apply_implementation",
                "implementation": implementation,
                "dry_run": dry_run,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="implementation_agent"
        )
    
    def _prepare_file_verification_message(
        self,
        workflow_id: str,
        implementation: Dict[str, Any],
        strategy: Dict[str, Any],
        bug: Dict[str, Any]
    ) -> AgentMessage:
        """
        Prepare a message for verification of an implementation.
        
        Args:
            workflow_id: The ID of the workflow
            implementation: The implementation to verify
            strategy: The strategy that was implemented
            bug: The bug that was fixed
            
        Returns:
            Message for the Verification Agent
        """
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={
                "action": "verify_implementation",
                "implementation": implementation,
                "strategy": strategy,
                "bug_report": bug,
                "workflow_id": workflow_id
            },
            sender=self.agent_id,
            receiver="verification_agent"
        )
    
    def _wait_for_result(
        self,
        workflow_id: str,
        agent_type: str,
        timeout: float
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for a result from an agent.
        
        Args:
            workflow_id: The ID of the workflow
            agent_type: The type of agent to wait for
            timeout: Timeout in seconds
            
        Returns:
            The result or None if timed out
        """
        # Wait for the result with timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if the result is available
            if workflow_id in self.task_results:
                result = self.task_results[workflow_id].get("results", {}).get(agent_type)
                if result:
                    return result
            
            # Sleep a bit to avoid busy waiting
            time.sleep(0.1)
        
        # Timeout
        return None
    
    def _is_critical_step(self, agent_type: str) -> bool:
        """
        Check if a step is critical for the workflow.
        
        Args:
            agent_type: The type of agent
            
        Returns:
            True if the step is critical, False otherwise
        """
        # Bug detection and strategy formulation are critical
        return agent_type in ["bug_detector", "strategy"]
    
    def _calculate_metrics(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate metrics for a file healing workflow.
        
        Args:
            workflow_state: The workflow state
            
        Returns:
            Metrics for the workflow
        """
        # Get bug detection results
        bug_detection_result = workflow_state["results"].get("bug_detector", {})
        bugs = bug_detection_result.get("bugs", [])
        
        # Get verification results
        verification_result = workflow_state["results"].get("verification", {})
        
        # Calculate metrics
        metrics = {
            "bugs_detected": len(bugs),
            "bugs_fixed": 1 if verification_result and verification_result.get("status") == "success" else 0,
            "duration": workflow_state["end_time"] - workflow_state["start_time"] if workflow_state.get("end_time") else 0,
            "success_rate": 1.0 if workflow_state["status"] == "completed" else (
                0.5 if workflow_state["status"] == "partial_success" else 0.0
            )
        }
        
        return metrics
    
    def _calculate_folder_metrics(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate metrics for a folder healing workflow.
        
        Args:
            workflow_state: The workflow state
            
        Returns:
            Metrics for the workflow
        """
        # Calculate metrics
        metrics = {
            "bugs_detected": workflow_state["bugs_detected"],
            "bugs_fixed": workflow_state["bugs_fixed"],
            "files_processed": len(workflow_state["files_processed"]),
            "files_healed": len(workflow_state["files_healed"]),
            "files_failed": len(workflow_state["files_failed"]),
            "duration": workflow_state["end_time"] - workflow_state["start_time"] if workflow_state.get("end_time") else 0,
            "success_rate": len(workflow_state["files_healed"]) / len(workflow_state["files_processed"]) if workflow_state["files_processed"] else 0
        }
        
        return metrics
    
    def _generate_id(self) -> str:
        """
        Generate a unique ID.
        
        Returns:
            A unique ID
        """
        import uuid
        return str(uuid.uuid4())
    
    def _handle_task_request(self, message: AgentMessage) -> None:
        """
        Handle a task request message.
        
        Args:
            message: The task request message
        """
        content = message.content
        action = content.get("action", "")
        
        if action == "orchestrate_file_healing":
            file_path = content.get("file_path")
            options = content.get("options", {})
            
            if not file_path:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": "file_path is required"
                    }
                )
                return
            
            try:
                result = self.orchestrate_file_healing(file_path, options)
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.TASK_RESULT,
                    content={
                        "status": "success",
                        "result": result
                    }
                )
            except Exception as e:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
        
        elif action == "orchestrate_folder_healing":
            folder_path = content.get("folder_path")
            options = content.get("options", {})
            
            if not folder_path:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": "folder_path is required"
                    }
                )
                return
            
            try:
                result = self.orchestrate_folder_healing(folder_path, options)
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.TASK_RESULT,
                    content={
                        "status": "success",
                        "result": result
                    }
                )
            except Exception as e:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
        
        elif action == "get_task_status":
            task_id = content.get("task_id")
            
            if not task_id:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": "task_id is required"
                    }
                )
                return
            
            try:
                result = self.get_task_status(task_id)
                
                if result:
                    self.send_response(
                        original_message=message,
                        message_type=MessageType.TASK_RESULT,
                        content={
                            "status": "success",
                            "result": result
                        }
                    )
                else:
                    self.send_response(
                        original_message=message,
                        message_type=MessageType.ERROR,
                        content={
                            "status": "error",
                            "error": f"Task {task_id} not found"
                        }
                    )
            except Exception as e:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
        
        elif action == "cancel_task":
            task_id = content.get("task_id")
            
            if not task_id:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": "task_id is required"
                    }
                )
                return
            
            try:
                result = self.cancel_task(task_id)
                
                self.send_response(
                    original_message=message,
                    message_type=MessageType.TASK_RESULT,
                    content={
                        "status": "success",
                        "result": result
                    }
                )
            except Exception as e:
                self.send_response(
                    original_message=message,
                    message_type=MessageType.ERROR,
                    content={
                        "status": "error",
                        "error": str(e)
                    }
                )
        
        else:
            self.send_response(
                original_message=message,
                message_type=MessageType.ERROR,
                content={
                    "status": "error",
                    "error": f"Unknown action: {action}"
                }
            )
    
    def handle_message(self, message: AgentMessage) -> None:
        """
        Handle an incoming message.
        
        Args:
            message: The incoming message
        """
        try:
            # Handle task requests
            if message.message_type == MessageType.TASK_REQUEST:
                self._handle_task_request(message)
            
            # Handle task results from other agents
            elif message.message_type == MessageType.TASK_RESULT:
                # Store the result
                if message.content.get("workflow_id") in self.pending_tasks:
                    workflow_id = message.content["workflow_id"]
                    agent_type = message.sender
                    
                    # Store the result
                    self.pending_tasks[workflow_id]["results"][agent_type] = message.content
            
            # Handle error messages from other agents
            elif message.message_type == MessageType.ERROR:
                # Increment error count
                if message.content.get("workflow_id") in self.pending_tasks:
                    workflow_id = message.content["workflow_id"]
                    agent_type = message.sender
                    
                    # Increment error count
                    if agent_type not in self.error_counts:
                        self.error_counts[agent_type] = 0
                    
                    self.error_counts[agent_type] += 1
                    
                    # Log the error
                    logger.error(f"Error from {agent_type}: {message.content.get('error', 'Unknown error')}")
            
            # Handle other message types using the base class
            else:
                super().handle_message(message)
        
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            logger.debug(traceback.format_exc())

    def _handle_query(self, message: AgentMessage) -> None:
        """
        Handle a query message.
        
        Args:
            message: The query message
        """
        # Extract message content
        content = message.content
        query_type = content.get("query_type", "")
        
        # Create a response message
        response_content = {
            "status": "success",
            "query_id": content.get("query_id", ""),
            "query_type": query_type,
            "result": {}
        }
        
        # Handle different query types
        if query_type == "task_status":
            task_id = content.get("task_id")
            if task_id:
                task_status = self.get_task_status(task_id)
                response_content["result"] = task_status or {"status": "not_found"}
            else:
                response_content["status"] = "error"
                response_content["error"] = "task_id is required"
        
        elif query_type == "agent_status":
            response_content["result"] = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": "active",
                "pending_tasks": len(self.pending_tasks),
                "completed_tasks": len(self.task_results)
            }
        
        else:
            # Unknown query type
            response_content["status"] = "error"
            response_content["error"] = f"Unknown query type: {query_type}"
        
        # Send the response
        self.send_response(
            original_message=message,
            message_type=MessageType.QUERY_RESPONSE,
            content=response_content
        )
