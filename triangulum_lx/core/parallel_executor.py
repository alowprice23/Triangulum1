"""
Parallel execution system for Triangulum.

Enables efficient parallel execution of tasks with dynamic scaling, resource-aware
scheduling, priority-based execution, work stealing, and robust failure isolation.
"""

import time
import asyncio
import logging
import os
import psutil
import threading
import uuid
import json
from enum import Enum, auto
from collections import deque, defaultdict
from typing import Dict, List, Optional, Any, Deque, Set, Tuple, Callable, Union, TypeVar
from pathlib import Path
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future, CancelledError

from . import get_triangulum_engine
from .monitor import EngineMonitor

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar('T')
TaskID = str
Priority = int
ResourceRequirements = Dict[str, float]
TaskResult = Any
TaskFunction = Callable[..., Any]
ProgressCallback = Callable[[float, str], None]


class TaskStatus(Enum):
    """Status of a task in the execution system."""
    PENDING = auto()    # Task is in the queue, not yet started
    RUNNING = auto()    # Task is currently running
    COMPLETED = auto()  # Task completed successfully
    FAILED = auto()     # Task failed with an exception
    CANCELLED = auto()  # Task was cancelled before completion
    TIMEOUT = auto()    # Task timed out
    STALLED = auto()    # Task is running but appears to be stalled


class ExecutionMode(Enum):
    """Execution mode for the parallel executor."""
    THREAD = auto()     # Execute tasks in threads
    PROCESS = auto()    # Execute tasks in separate processes
    HYBRID = auto()     # Use a mix of threads and processes based on task requirements


@dataclass
class TaskContext:
    """
    Context for a single task being processed.
    
    This class maintains the state and resources for processing a single task,
    including its own engine instance and coordinator if applicable.
    """
    
    id: TaskID
    priority: Priority
    function: TaskFunction
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    resource_requirements: ResourceRequirements = field(default_factory=dict)
    timeout: Optional[float] = None
    dependencies: Set[TaskID] = field(default_factory=set)
    dependents: Set[TaskID] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    exception: Optional[Exception] = None
    progress_callback: Optional[ProgressCallback] = None
    
    # Execution tracking
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    last_progress_time: Optional[float] = None
    progress: float = 0.0
    progress_message: str = ""
    
    # For bug-specific contexts
    engine: Any = None
    monitor: Any = None
    coordinator: Any = None
    
    def __post_init__(self):
        """Initialize derived fields after instance creation."""
        if self.id is None:
            self.id = str(uuid.uuid4())
        
        # Initialize tracking metrics
        self.metrics = {
            "ticks_processed": 0,
            "verification_attempts": 0,
            "memory_usage": 0,
            "cpu_usage": 0,
            "io_operations": 0,
            "stall_count": 0,
            "retry_count": 0,
        }
    
    def initialize_bug_context(self, bug_id: str, engine_factory: Callable):
        """
        Initialize this context as a bug processing context.
        
        Args:
            bug_id: Unique identifier for the bug
            engine_factory: Factory function to create a TriangulumEngine instance
        """
        self.id = bug_id
        self.engine = engine_factory()
        self.monitor = EngineMonitor(self.engine)
        self.engine.monitor = self.monitor
        self.coordinator = AutoGenCoordinator(self.engine)
        self.last_progress_time = time.time()
        self.start_time = time.time()
    
    async def process_tick(self) -> bool:
        """
        Process one tick for this bug.
        
        Returns:
            bool: True if processing should continue, False if done
        """
        if self.engine.monitor.done():
            return False
            
        # Process tick
        self.engine.tick()
        self.metrics["ticks_processed"] += 1
        
        # Track verification attempts
        for bug in self.engine.bugs:
            if bug.phase.name == "VERIFY" and bug.timer == 3:
                self.metrics["verification_attempts"] += 1
        
        # Let coordinator process the tick
        await self.coordinator.step()
        
        # Update progress
        self.last_progress_time = time.time()
        self.progress = self.engine.monitor.get_progress()
        
        # Update resource usage metrics
        self._update_resource_metrics()
        
        # Call progress callback if provided
        if self.progress_callback:
            self.progress_callback(self.progress, f"Processing bug {self.id}")
        
        return not self.engine.monitor.done()
    
    def _update_resource_metrics(self):
        """Update resource usage metrics for this task."""
        try:
            process = psutil.Process(os.getpid())
            self.metrics["memory_usage"] = process.memory_info().rss / (1024 * 1024)  # MB
            self.metrics["cpu_usage"] = process.cpu_percent(interval=0.1)
            self.metrics["io_operations"] = sum(process.io_counters())
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            pass
    
    def is_stalled(self, stall_threshold_seconds: float = 60.0) -> bool:
        """
        Check if this task appears to be stalled.
        
        Args:
            stall_threshold_seconds: Threshold in seconds to consider a task stalled
            
        Returns:
            bool: True if the task appears to be stalled
        """
        if self.status != TaskStatus.RUNNING or self.last_progress_time is None:
            return False
        
        time_since_progress = time.time() - self.last_progress_time
        return time_since_progress > stall_threshold_seconds
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics for this task context."""
        metrics = {
            "task_id": self.id,
            "status": self.status.name,
            "priority": self.priority,
            "progress": self.progress,
            "wall_time": (time.time() - self.start_time) if self.start_time else 0,
            "execution_time": (self.end_time - self.start_time) if self.end_time and self.start_time else None,
        }
        
        # Add bug-specific metrics if this is a bug context
        if self.engine and self.monitor:
            metrics.update({
                "ticks": self.metrics["ticks_processed"],
                "verifications": self.metrics["verification_attempts"],
                "entropy": getattr(self.engine.monitor, "g_bits", 0)
            })
        
        # Add resource usage metrics
        metrics.update({k: v for k, v in self.metrics.items() if k not in ["ticks_processed", "verification_attempts"]})
        
        return metrics


class ResourceManager:
    """
    Manages system resources for the parallel executor.
    
    This class tracks available system resources and allocates them to tasks
    based on their requirements and priorities.
    """
    
    def __init__(self, 
                 cpu_limit: Optional[float] = None, 
                 memory_limit: Optional[float] = None,
                 io_limit: Optional[float] = None):
        """
        Initialize the resource manager.
        
        Args:
            cpu_limit: Maximum CPU usage as a percentage (0-100 * num_cores)
            memory_limit: Maximum memory usage in MB
            io_limit: Maximum IO operations per second
        """
        self.cpu_limit = cpu_limit or psutil.cpu_count() * 75  # 75% of all cores by default
        self.memory_limit = memory_limit or psutil.virtual_memory().total / (1024 * 1024) * 0.75  # 75% of total memory
        self.io_limit = io_limit or 1000  # Default IO limit
        
        # Track allocated resources
        self.allocated_cpu = 0
        self.allocated_memory = 0
        self.allocated_io = 0
        
        # Track resource usage by task
        self.task_resources: Dict[TaskID, ResourceRequirements] = {}
        
        # Resource usage history for adaptive scaling
        self.usage_history: Deque[Dict[str, float]] = deque(maxlen=100)
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
    def can_allocate(self, requirements: ResourceRequirements) -> bool:
        """
        Check if the required resources can be allocated.
        
        Args:
            requirements: Resource requirements dictionary
            
        Returns:
            bool: True if resources can be allocated
        """
        with self.lock:
            cpu_req = requirements.get("cpu", 0)
            memory_req = requirements.get("memory", 0)
            io_req = requirements.get("io", 0)
            
            return (self.allocated_cpu + cpu_req <= self.cpu_limit and
                    self.allocated_memory + memory_req <= self.memory_limit and
                    self.allocated_io + io_req <= self.io_limit)
    
    def allocate(self, task_id: TaskID, requirements: ResourceRequirements) -> bool:
        """
        Allocate resources for a task.
        
        Args:
            task_id: ID of the task
            requirements: Resource requirements dictionary
            
        Returns:
            bool: True if resources were successfully allocated
        """
        with self.lock:
            if not self.can_allocate(requirements):
                return False
            
            cpu_req = requirements.get("cpu", 0)
            memory_req = requirements.get("memory", 0)
            io_req = requirements.get("io", 0)
            
            self.allocated_cpu += cpu_req
            self.allocated_memory += memory_req
            self.allocated_io += io_req
            
            self.task_resources[task_id] = requirements
            return True
    
    def release(self, task_id: TaskID) -> None:
        """
        Release resources allocated to a task.
        
        Args:
            task_id: ID of the task
        """
        with self.lock:
            if task_id not in self.task_resources:
                return
            
            requirements = self.task_resources[task_id]
            
            self.allocated_cpu -= requirements.get("cpu", 0)
            self.allocated_memory -= requirements.get("memory", 0)
            self.allocated_io -= requirements.get("io", 0)
            
            del self.task_resources[task_id]
    
    def get_available_resources(self) -> ResourceRequirements:
        """
        Get the currently available resources.
        
        Returns:
            ResourceRequirements: Available resources
        """
        with self.lock:
            return {
                "cpu": max(0, self.cpu_limit - self.allocated_cpu),
                "memory": max(0, self.memory_limit - self.allocated_memory),
                "io": max(0, self.io_limit - self.allocated_io)
            }
    
    def update_limits(self, 
                      cpu_limit: Optional[float] = None, 
                      memory_limit: Optional[float] = None,
                      io_limit: Optional[float] = None) -> None:
        """
        Update resource limits.
        
        Args:
            cpu_limit: New CPU limit
            memory_limit: New memory limit
            io_limit: New IO limit
        """
        with self.lock:
            if cpu_limit is not None:
                self.cpu_limit = cpu_limit
            
            if memory_limit is not None:
                self.memory_limit = memory_limit
            
            if io_limit is not None:
                self.io_limit = io_limit
    
    def update_usage_history(self) -> None:
        """Update resource usage history for adaptive scaling."""
        with self.lock:
            usage = {
                "cpu": self.allocated_cpu / max(1, self.cpu_limit),
                "memory": self.allocated_memory / max(1, self.memory_limit),
                "io": self.allocated_io / max(1, self.io_limit),
                "timestamp": time.time()
            }
            self.usage_history.append(usage)
    
    def get_usage_metrics(self) -> Dict[str, Any]:
        """
        Get current resource usage metrics.
        
        Returns:
            Dict with resource usage metrics
        """
        with self.lock:
            return {
                "cpu": {
                    "limit": self.cpu_limit,
                    "allocated": self.allocated_cpu,
                    "available": max(0, self.cpu_limit - self.allocated_cpu),
                    "utilization": self.allocated_cpu / max(1, self.cpu_limit)
                },
                "memory": {
                    "limit": self.memory_limit,
                    "allocated": self.allocated_memory,
                    "available": max(0, self.memory_limit - self.allocated_memory),
                    "utilization": self.allocated_memory / max(1, self.memory_limit)
                },
                "io": {
                    "limit": self.io_limit,
                    "allocated": self.allocated_io,
                    "available": max(0, self.io_limit - self.allocated_io),
                    "utilization": self.allocated_io / max(1, self.io_limit)
                },
                "task_count": len(self.task_resources)
            }


class WorkStealingQueue:
    """
    Work stealing queue for load balancing.
    
    This class implements a work stealing queue that allows tasks to be
    redistributed between worker threads for better load balancing.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the work stealing queue.
        
        Args:
            max_size: Maximum queue size
        """
        self.local_queues: Dict[int, Deque[TaskContext]] = {}
        self.global_queue: Deque[TaskContext] = deque(maxlen=max_size)
        self.lock = threading.RLock()
        self.max_size = max_size
    
    def register_worker(self, worker_id: int) -> None:
        """
        Register a worker thread.
        
        Args:
            worker_id: ID of the worker thread
        """
        with self.lock:
            if worker_id not in self.local_queues:
                self.local_queues[worker_id] = deque(maxlen=self.max_size)
    
    def push_local(self, worker_id: int, task: TaskContext) -> bool:
        """
        Push a task to a worker's local queue.
        
        Args:
            worker_id: ID of the worker thread
            task: Task to push
            
        Returns:
            bool: True if the task was pushed successfully
        """
        with self.lock:
            if worker_id not in self.local_queues:
                self.register_worker(worker_id)
            
            if len(self.local_queues[worker_id]) >= self.max_size:
                return False
            
            self.local_queues[worker_id].append(task)
            return True
    
    def push_global(self, task: TaskContext) -> bool:
        """
        Push a task to the global queue.
        
        Args:
            task: Task to push
            
        Returns:
            bool: True if the task was pushed successfully
        """
        with self.lock:
            if len(self.global_queue) >= self.max_size:
                return False
            
            self.global_queue.append(task)
            return True
    
    def pop_local(self, worker_id: int) -> Optional[TaskContext]:
        """
        Pop a task from a worker's local queue.
        
        Args:
            worker_id: ID of the worker thread
            
        Returns:
            TaskContext or None if the queue is empty
        """
        with self.lock:
            if worker_id not in self.local_queues or not self.local_queues[worker_id]:
                return None
            
            return self.local_queues[worker_id].popleft()
    
    def pop_global(self) -> Optional[TaskContext]:
        """
        Pop a task from the global queue.
        
        Returns:
            TaskContext or None if the queue is empty
        """
        with self.lock:
            if not self.global_queue:
                return None
            
            return self.global_queue.popleft()
    
    def steal(self, worker_id: int) -> Optional[TaskContext]:
        """
        Steal a task from another worker's queue.
        
        Args:
            worker_id: ID of the worker thread
            
        Returns:
            TaskContext or None if no task could be stolen
        """
        with self.lock:
            # Try to steal from the global queue first
            if self.global_queue:
                return self.global_queue.popleft()
            
            # Try to steal from other workers
            for other_id, queue in self.local_queues.items():
                if other_id != worker_id and queue:
                    # Steal from the end of the queue (most recently added tasks)
                    return queue.pop()
            
            return None
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """
        Get the sizes of all queues.
        
        Returns:
            Dict with queue sizes
        """
        with self.lock:
            sizes = {"global": len(self.global_queue)}
            for worker_id, queue in self.local_queues.items():
                sizes[f"worker_{worker_id}"] = len(queue)
            return sizes


class ParallelExecutor:
    """
    Executes multiple tasks in parallel with advanced features.
    
    This class manages the concurrent execution of tasks with support for:
    - Dynamic scaling of concurrent execution
    - Resource-aware scheduling
    - Priority-based execution queuing
    - Work stealing for load balancing
    - Timeout and cancellation support
    - Progress tracking and reporting
    - Failure isolation and recovery
    """
    
    def __init__(self, 
                 max_workers: Optional[int] = None,
                 min_workers: int = 2,
                 execution_mode: ExecutionMode = ExecutionMode.THREAD,
                 resource_limits: Optional[Dict[str, float]] = None,
                 adaptive_scaling: bool = True,
                 stall_threshold: float = 60.0,
                 max_retries: int = 3,
                 work_stealing: bool = True):
        """
        Initialize the parallel executor.
        
        Args:
            max_workers: Maximum number of worker threads/processes
            min_workers: Minimum number of worker threads/processes
            execution_mode: Mode of execution (THREAD, PROCESS, or HYBRID)
            resource_limits: Resource limits dictionary
            adaptive_scaling: Whether to adaptively scale workers based on load
            stall_threshold: Threshold in seconds to consider a task stalled
            max_retries: Maximum number of retries for failed tasks
            work_stealing: Whether to enable work stealing for load balancing
        """
        # Worker configuration
        self.max_workers = max_workers or min(32, os.cpu_count() * 2)
        self.min_workers = min_workers
        self.execution_mode = execution_mode
        self.adaptive_scaling = adaptive_scaling
        self.stall_threshold = stall_threshold
        self.max_retries = max_retries
        self.work_stealing = work_stealing
        
        # Initialize resource manager
        self.resource_manager = ResourceManager(
            cpu_limit=resource_limits.get("cpu") if resource_limits else None,
            memory_limit=resource_limits.get("memory") if resource_limits else None,
            io_limit=resource_limits.get("io") if resource_limits else None
        )
        
        # Task queues and tracking
        self.task_queue = asyncio.PriorityQueue()
        self.active_tasks: Dict[TaskID, TaskContext] = {}
        self.completed_tasks: Dict[TaskID, TaskContext] = {}
        self.failed_tasks: Dict[TaskID, TaskContext] = {}
        self.cancelled_tasks: Dict[TaskID, TaskContext] = {}
        
        # For bug-specific processing
        self.bug_queue = asyncio.PriorityQueue()
        self.active_bugs: Dict[str, TaskContext] = {}
        self.completed_bugs: List[str] = []
        self.failed_bugs: List[str] = []
        
        # Dependency tracking
        self.dependency_graph: Dict[TaskID, Set[TaskID]] = {}
        self.reverse_dependency_graph: Dict[TaskID, Set[TaskID]] = {}
        
        # Work stealing queue for load balancing
        self.work_stealing_queue = WorkStealingQueue() if work_stealing else None
        
        # Executor pools
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=max(1, self.max_workers // 2))
        
        # Future tracking
        self.futures: Dict[TaskID, Future] = {}
        
        # Control flags
        self.shutdown_event = asyncio.Event()
        self.paused = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Not paused initially
        
        # Metrics and monitoring
        self.start_time = time.time()
        self.metrics = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "bugs_submitted": 0,
            "bugs_completed": 0,
            "bugs_failed": 0,
            "total_execution_time": 0,
            "average_task_time": 0,
            "average_wait_time": 0,
            "worker_utilization": 0,
            "resource_utilization": {
                "cpu": 0,
                "memory": 0,
                "io": 0
            }
        }
        
        # Monitoring and logging
        self.last_metrics_update = time.time()
        self.metrics_update_interval = 5.0  # seconds
        
        # Initialize worker scaling
        self.current_workers = min_workers
        self.target_workers = min_workers
        self.worker_adjustment_interval = 10.0  # seconds
        self.last_worker_adjustment = time.time()
        
        logger.info(f"Parallel Executor initialized with {self.min_workers}-{self.max_workers} workers "
                   f"in {self.execution_mode.name} mode")
    
    def add_task(self, 
                function: TaskFunction, 
                args: Tuple = (), 
                kwargs: Dict[str, Any] = None,
                task_id: Optional[TaskID] = None,
                priority: Priority = 0,
                resource_requirements: Optional[ResourceRequirements] = None,
                timeout: Optional[float] = None,
                dependencies: Optional[List[TaskID]] = None,
                progress_callback: Optional[ProgressCallback] = None) -> TaskID:
        """
        Add a task to the execution queue.
        
        Args:
            function: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            task_id: Optional task ID, will be generated if not provided
            priority: Priority of the task (lower values = higher priority)
            resource_requirements: Resource requirements for the task
            timeout: Timeout in seconds for the task
            dependencies: List of task IDs that must complete before this task
            progress_callback: Callback function for progress updates
            
        Returns:
            Task ID
        """
        # Generate task ID if not provided
        task_id = task_id or str(uuid.uuid4())
        
        # Initialize kwargs if None
        kwargs = kwargs or {}
        
        # Create task context
        task = TaskContext(
            id=task_id,
            priority=priority,
            function=function,
            args=args,
            kwargs=kwargs,
            resource_requirements=resource_requirements or {},
            timeout=timeout,
            dependencies=set(dependencies or []),
            progress_callback=progress_callback
        )
        
        # Update dependency tracking
        self.dependency_graph[task_id] = set(dependencies or [])
        for dep_id in task.dependencies:
            if dep_id not in self.reverse_dependency_graph:
                self.reverse_dependency_graph[dep_id] = set()
            self.reverse_dependency_graph[dep_id].add(task_id)
            task.dependents.add(dep_id)
        
        # Add to queue
        self.task_queue.put_nowait((priority, task_id, task))
        
        # Update metrics
        self.metrics["tasks_submitted"] += 1
        
        logger.debug(f"Added task {task_id} with priority {priority}")
        
        return task_id
    
    def add_bug(self, bug: Any, priority: int = 0) -> str:
        """
        Add a bug to the processing queue.
        
        Args:
            bug: Bug object to add
            priority: Priority of the bug (lower values = higher priority)
            
        Returns:
            Bug ID
        """
        bug_id = getattr(bug, "id", str(uuid.uuid4()))
        
        # Add to queue
        self.bug_queue.put_nowait((priority, bug_id, bug))
        
        # Update metrics
        self.metrics["bugs_submitted"] += 1
        
        logger.debug(f"Added bug {bug_id} with priority {priority}")
        
        return bug_id
    
    async def _spawn_bug(self) -> None:
        """Spawn a new bug context from the priority queue."""
        if self.bug_queue.empty():
            return
            
        priority, bug_id, bug = await self.bug_queue.get()
        
        # Check if we have resources available
        resource_requirements = {"cpu": 1.0, "memory": 500.0, "io": 10.0}  # Default requirements
        if not self.resource_manager.can_allocate(resource_requirements):
            # Put back in queue with same priority
            self.bug_queue.put_nowait((priority, bug_id, bug))
            return
        
        # Create bug context
        TriangulumEngine = get_triangulum_engine()
        
        # Create task context for the bug
        task = TaskContext(
            id=bug_id,
            priority=priority,
            function=lambda: None,  # Placeholder
            resource_requirements=resource_requirements
        )
        
        # Initialize as bug context
        task.initialize_bug_context(bug_id, lambda: TriangulumEngine())
        
        # Allocate resources
        self.resource_manager.allocate(bug_id, resource_requirements)
        
        # Add to active bugs
        self.active_bugs[bug_id] = task
        
        logger.info(f"Spawned bug context for bug {bug_id}")
    
    async def _process_bug_context(self, bug_id: str, ctx: TaskContext) -> None:
        """
        Process a bug context.
        
        Args:
            bug_id: Bug ID
            ctx: Task context for the bug
        """
        try:
            # Wait for pause if paused
            await self.pause_event.wait()
            
            # Process tick with timeout
            continue_processing = await asyncio.wait_for(
                ctx.process_tick(), 
                timeout=ctx.engine.config.get("tick_timeout", 60)
            )
            
            if not continue_processing:
                # Bug processing is complete
                if all(b.phase.name == "DONE" for b in ctx.engine.bugs):
                    self.completed_bugs.append(bug_id)
                    logger.info(f"Bug {bug_id} completed successfully")
                else:
                    self.failed_bugs.append(bug_id)
                    logger.warning(f"Bug {bug_id} failed to complete")
                
                # Release resources
                self.resource_manager.release(bug_id)
                
                # Remove from active bugs
                del self.active_bugs[bug_id]
        
        except asyncio.TimeoutError:
            logger.error(f"Timeout processing bug {bug_id}")
            self.failed_bugs.append(bug_id)
            self.resource_manager.release(bug_id)
            del self.active_bugs[bug_id]
        
        except Exception as e:
            logger.error(f"Error processing bug {bug_id}: {str(e)}")
            self.failed_bugs.append(bug_id)
            self.resource_manager.release(bug_id)
            del self.active_bugs[bug_id]
    
    async def _execute_task(self, task: TaskContext) -> None:
        """
        Execute a task.
        
        Args:
            task: Task context
        """
        # Mark as running
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        task.last_progress_time = time.time()
        
        try:
            # Wait for pause if paused
            await self.pause_event.wait()
            
            # Choose executor based on execution mode and task requirements
            if self.execution_mode == ExecutionMode.PROCESS or (
                self.execution_mode == ExecutionMode.HYBRID and 
                task.resource_requirements.get("cpu", 0) > 1.0
            ):
                # Use process executor for CPU-intensive tasks
                future = self.process_executor.submit(task.function, *task.args, **task.kwargs)
            else:
                # Use thread executor for most tasks
                future = self.thread_executor.submit(task.function, *task.args, **task.kwargs)
            
            # Store future
            self.futures[task.id] = future
            
            # Wait for completion with timeout
            if task.timeout:
                result = await asyncio.wait_for(
                    asyncio.wrap_future(future), 
                    timeout=task.timeout
                )
            else:
                result = await asyncio.wrap_future(future)
            
            # Task completed successfully
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.end_time = time.time()
            task.progress = 1.0
            
            # Update metrics
            self.metrics["tasks_completed"] += 1
            self.metrics["total_execution_time"] += (task.end_time - task.start_time)
            self.metrics["average_task_time"] = (
                self.metrics["total_execution_time"] / self.metrics["tasks_completed"]
            )
            
            # Move to completed tasks
            self.completed_tasks[task.id] = task
            
            # Release resources
            self.resource_manager.release(task.id)
            
            # Remove from active tasks
            del self.active_tasks[task.id]
            
            # Update dependents
            self._update_dependents(task.id)
            
            logger.debug(f"Task {task.id} completed successfully")
        
        except asyncio.TimeoutError:
            # Task timed out
            task.status = TaskStatus.TIMEOUT
            task.end_time = time.time()
            task.exception = TimeoutError(f"Task timed out after {task.timeout} seconds")
            
            # Cancel future
            if task.id in self.futures:
                self.futures[task.id].cancel()
                del self.futures[task.id]
            
            # Update metrics
            self.metrics["tasks_failed"] += 1
            
            # Move to failed tasks
            self.failed_tasks[task.id] = task
            
            # Release resources
            self.resource_manager.release(task.id)
            
            # Remove from active tasks
            del self.active_tasks[task.id]
            
            logger.warning(f"Task {task.id} timed out after {task.timeout} seconds")
        
        except CancelledError:
            # Task was cancelled
            task.status = TaskStatus.CANCELLED
            task.end_time = time.time()
            
            # Update metrics
            self.metrics["tasks_cancelled"] += 1
            
            # Move to cancelled tasks
            self.cancelled_tasks[task.id] = task
            
            # Release resources
            self.resource_manager.release(task.id)
            
            # Remove from active tasks
            del self.active_tasks[task.id]
            
            logger.info(f"Task {task.id} was cancelled")
        
        except Exception as e:
            # Task failed with exception
            task.status = TaskStatus.FAILED
            task.end_time = time.time()
            task.exception = e
            
            # Update metrics
            self.metrics["tasks_failed"] += 1
            
            # Move to failed tasks
            self.failed_tasks[task.id] = task
            
            # Release resources
            self.resource_manager.release(task.id)
            
            # Remove from active tasks
            del self.active_tasks[task.id]
            
            logger.error(f"Task {task.id} failed with exception: {str(e)}")
    
    def _update_dependents(self, task_id: TaskID) -> None:
        """
        Update dependents of a completed task.
        
        Args:
            task_id: ID of the completed task
        """
        if task_id not in self.reverse_dependency_graph:
            return
        
        for dependent_id in self.reverse_dependency_graph[task_id]:
            if dependent_id in self.dependency_graph:
                self.dependency_graph[dependent_id].remove(task_id)
    
    async def _spawn_task(self) -> None:
        """Spawn a new task from the priority queue."""
        if self.task_queue.empty():
            return
        
        # Get next task
        priority, task_id, task = await self.task_queue.get()
        
        # Check if dependencies are satisfied
        if task.dependencies and any(
            dep_id not in self.completed_tasks for dep_id in task.dependencies
        ):
            # Put back in queue with same priority
            self.task_queue.put_nowait((priority, task_id, task))
            return
        
        # Check if we have resources available
        if not self.resource_manager.can_allocate(task.resource_requirements):
            # Put back in queue with same priority
            self.task_queue.put_nowait((priority, task_id, task))
            return
        
        # Allocate resources
        self.resource_manager.allocate(task.id, task.resource_requirements)
        
        # Add to active tasks
        self.active_tasks[task.id] = task
        
        # Execute task
        asyncio.create_task(self._execute_task(task))
        
        logger.debug(f"Spawned task {task.id}")
    
    async def step(self) -> Dict[str, Any]:
        """
        Process one step of parallel execution.
        
        This advances all active tasks and bugs by one step and manages
        the task lifecycle.
        
        Returns:
            Dict with step results
        """
        # Wait for pause if paused
        await self.pause_event.wait()
        
        # Update resource usage history
        self.resource_manager.update_usage_history()
        
        # Adjust worker count if needed
        await self._adjust_worker_count()
        
        # Spawn new tasks up to capacity
        available_slots = self.current_workers - len(self.active_tasks) - len(self.active_bugs)
        for _ in range(max(0, available_slots)):
            if not self.task_queue.empty():
                await self._spawn_task()
            elif not self.bug_queue.empty():
                await self._spawn_bug()
            else:
                break
        
        # Process active bugs
        bug_tasks = [
            self._process_bug_context(bug_id, ctx) 
            for bug_id, ctx in list(self.active_bugs.items())
        ]
        
        if bug_tasks:
            await asyncio.gather(*bug_tasks)
        
        # Check for stalled tasks
        await self._check_stalled_tasks()
        
        # Update metrics
        if time.time() - self.last_metrics_update > self.metrics_update_interval:
            self._update_metrics()
            self.last_metrics_update = time.time()
        
        # Return step results
        return {
            "active_tasks": len(self.active_tasks),
            "active_bugs": len(self.active_bugs),
            "pending_tasks": self.task_queue.qsize(),
            "pending_bugs": self.bug_queue.qsize(),
            "completed_tasks": len(self.completed_tasks),
            "completed_bugs": len(self.completed_bugs),
            "failed_tasks": len(self.failed_tasks),
            "failed_bugs": len(self.failed_bugs),
            "cancelled_tasks": len(self.cancelled_tasks),
            "current_workers": self.current_workers,
            "resource_usage": self.resource_manager.get_usage_metrics()
        }
    
    async def _check_stalled_tasks(self) -> None:
        """Check for and handle stalled tasks."""
        for task_id, task in list(self.active_tasks.items()):
            if task.is_stalled(self.stall_threshold):
                logger.warning(f"Task {task_id} appears to be stalled")
                
                # Increment stall count
                task.metrics["stall_count"] += 1
                
                # If stalled too many times, cancel it
                if task.metrics["stall_count"] > self.max_retries:
                    logger.error(f"Task {task_id} stalled {task.metrics['stall_count']} times, cancelling")
                    self.cancel_task(task_id)
    
    async def _adjust_worker_count(self) -> None:
        """Adjust worker count based on load."""
        if not self.adaptive_scaling:
            return
        
        # Only adjust periodically
        if time.time() - self.last_worker_adjustment < self.worker_adjustment_interval:
            return
        
        # Calculate load
        total_tasks = len(self.active_tasks) + len(self.active_bugs)
        queue_size = self.task_queue.qsize() + self.bug_queue.qsize()
        
        # Get resource utilization
        resource_usage = self.resource_manager.get_usage_metrics()
        cpu_utilization = resource_usage["cpu"]["utilization"]
        memory_utilization = resource_usage["memory"]["utilization"]
        
        # Calculate target workers
        if queue_size > total_tasks and cpu_utilization < 0.8 and memory_utilization < 0.8:
            # Increase workers if we have queued tasks and resources available
            self.target_workers = min(self.max_workers, self.current_workers + 1)
        elif total_tasks < self.current_workers // 2 and self.current_workers > self.min_workers:
            # Decrease workers if we have excess capacity
            self.target_workers = max(self.min_workers, self.current_workers - 1)
        
        # Adjust current workers towards target
        if self.current_workers < self.target_workers:
            self.current_workers += 1
            logger.info(f"Increased worker count to {self.current_workers}")
        elif self.current_workers > self.target_workers:
            self.current_workers -= 1
            logger.info(f"Decreased worker count to {self.current_workers}")
        
        self.last_worker_adjustment = time.time()
    
    def _update_metrics(self) -> None:
        """Update executor metrics."""
        # Calculate worker utilization
        total_capacity = self.current_workers
        used_capacity = len(self.active_tasks) + len(self.active_bugs)
        self.metrics["worker_utilization"] = used_capacity / max(1, total_capacity)
        
        # Update resource utilization
        resource_usage = self.resource_manager.get_usage_metrics()
        self.metrics["resource_utilization"] = {
            "cpu": resource_usage["cpu"]["utilization"],
            "memory": resource_usage["memory"]["utilization"],
            "io": resource_usage["io"]["utilization"]
        }
    
    def cancel_task(self, task_id: TaskID) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            bool: True if the task was cancelled
        """
        # Check if task is active
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            
            # Cancel future if it exists
            if task_id in self.futures:
                self.futures[task_id].cancel()
                del self.futures[task_id]
            
            # Update task status
            task.status = TaskStatus.CANCELLED
            task.end_time = time.time()
            
            # Update metrics
            self.metrics["tasks_cancelled"] += 1
            
            # Move to cancelled tasks
            self.cancelled_tasks[task_id] = task
            
            # Release resources
            self.resource_manager.release(task_id)
            
            # Remove from active tasks
            del self.active_tasks[task_id]
            
            logger.info(f"Task {task_id} cancelled")
            return True
        
        return False
    
    def pause(self) -> None:
        """Pause execution."""
        if not self.paused:
            self.paused = True
            self.pause_event.clear()
            logger.info("Parallel executor paused")
    
    def resume(self) -> None:
        """Resume execution."""
        if self.paused:
            self.paused = False
            self.pause_event.set()
            logger.info("Parallel executor resumed")
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the executor.
        
        Args:
            wait: Whether to wait for active tasks to complete
        """
        logger.info("Shutting down parallel executor")
        
        # Set shutdown event
        self.shutdown_event.set()
        
        if wait:
            # Wait for active tasks to complete
            self.thread_executor.shutdown(wait=True)
            self.process_executor.shutdown(wait=True)
        else:
            # Cancel all active tasks
            for task_id in list(self.active_tasks.keys()):
                self.cancel_task(task_id)
            
            # Shutdown executors without waiting
            self.thread_executor.shutdown(wait=False)
            self.process_executor.shutdown(wait=False)
        
        logger.info("Parallel executor shutdown complete")
    
    async def run_until_complete(self) -> Dict[str, Any]:
        """
        Run the executor until all tasks are processed.
        
        Returns:
            Dict with execution results
        """
        start_time = time.time()
        step_count = 0
        
        logger.info("Starting parallel execution")
        
        while (
            (self.active_tasks or self.active_bugs or 
             not self.task_queue.empty() or not self.bug_queue.empty()) and 
            not self.shutdown_event.is_set()
        ):
            await self.step()
            step_count += 1
            
            # Optional: Add a small delay to prevent CPU hogging
            await asyncio.sleep(0.01)
        
        end_time = time.time()
        
        # Return final results
        results = {
            "total_tasks": self.metrics["tasks_submitted"],
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "cancelled_tasks": len(self.cancelled_tasks),
            "total_bugs": self.metrics["bugs_submitted"],
            "completed_bugs": len(self.completed_bugs),
            "failed_bugs": len(self.failed_bugs),
            "success_rate_tasks": (
                len(self.completed_tasks) / max(1, self.metrics["tasks_submitted"])
            ),
            "success_rate_bugs": (
                len(self.completed_bugs) / max(1, self.metrics["bugs_submitted"])
            ),
            "total_steps": step_count,
            "elapsed_time": end_time - start_time,
            "average_task_time": self.metrics["average_task_time"],
            "resource_utilization": self.metrics["resource_utilization"]
        }
        
        logger.info(f"Parallel execution completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Processed {self.metrics['tasks_submitted']} tasks and {self.metrics['bugs_submitted']} bugs")
        logger.info(f"Success rate: {results['success_rate_tasks']:.2%} for tasks, {results['success_rate_bugs']:.2%} for bugs")
        
        return results
    
    def get_task_status(self, task_id: TaskID) -> Optional[TaskStatus]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            TaskStatus or None if the task doesn't exist
        """
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].status
        elif task_id in self.completed_tasks:
            return self.completed_tasks[task_id].status
        elif task_id in self.failed_tasks:
            return self.failed_tasks[task_id].status
        elif task_id in self.cancelled_tasks:
            return self.cancelled_tasks[task_id].status
        
        return None
    
    def get_task_result(self, task_id: TaskID) -> Optional[Any]:
        """
        Get the result of a completed task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task result or None if the task doesn't exist or isn't completed
        """
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id].result
        
        return None
    
    def get_task_exception(self, task_id: TaskID) -> Optional[Exception]:
        """
        Get the exception of a failed task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Exception or None if the task doesn't exist or didn't fail
        """
        if task_id in self.failed_tasks:
            return self.failed_tasks[task_id].exception
        
        return None
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics for the executor.
        
        Returns:
            Dict with all metrics
        """
        # Update metrics first
        self._update_metrics()
        
        # Get resource usage
        resource_usage = self.resource_manager.get_usage_metrics()
        
        # Combine all metrics
        return {
            "executor": self.metrics,
            "resources": resource_usage,
            "active_tasks": {
                task_id: task.get_metrics() for task_id, task in self.active_tasks.items()
            },
            "active_bugs": {
                bug_id: task.get_metrics() for bug_id, task in self.active_bugs.items()
            },
            "queue_sizes": {
                "tasks": self.task_queue.qsize(),
                "bugs": self.bug_queue.qsize()
            },
            "worker_count": self.current_workers,
            "uptime": time.time() - self.start_time
        }
    
    def get_bug_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for all active bug contexts.
        
        Returns:
            Dict with bug metrics
        """
        return {
            "active": {bug_id: ctx.get_metrics() for bug_id, ctx in self.active_bugs.items()},
            "backlog_size": self.bug_queue.qsize(),
            "completed": len(self.completed_bugs),
            "failed": len(self.failed_bugs)
        }
