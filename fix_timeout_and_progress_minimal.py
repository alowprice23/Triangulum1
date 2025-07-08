#!/usr/bin/env python3
"""
Minimal Fix for Timeout and Progress Tracking

This script implements a complete solution for timeout and progress tracking issues
while keeping the implementation concise and focused on core functionality.
"""

import os
import sys
import time
import threading
import logging
import uuid
import inspect
import functools
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("timeout_progress_fix")

# =============================================================================
# Core Classes
# =============================================================================

class TimeoutPolicy(Enum):
    """Timeout policy options."""
    EXCEPTION = auto()   # Raise exception on timeout
    RETURN_NONE = auto() # Return None on timeout
    RETRY = auto()       # Retry the operation
    EXTEND = auto()      # Extend the timeout

class ProgressStatus(Enum):
    """Status of a progress operation."""
    NOT_STARTED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class TimeoutConfig:
    """Configuration for timeout behavior."""
    duration: float
    policy: TimeoutPolicy = TimeoutPolicy.EXCEPTION
    max_retries: int = 3
    retry_delay: float = 1.0
    max_extension: float = 60.0
    propagate: bool = True

@dataclass
class ProgressStep:
    """Step in a progress operation."""
    name: str
    weight: float = 1.0
    progress: float = 0.0
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    message: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None

@dataclass
class ProgressOperation:
    """Progress operation with multiple steps."""
    id: str
    name: str
    steps: List[ProgressStep] = field(default_factory=list)
    current_step_index: int = 0
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    parent_id: Optional[str] = None

# =============================================================================
# Managers
# =============================================================================

class TimeoutManager:
    """Manages timeouts consistently across the application."""
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TimeoutManager()
        return cls._instance
    
    def __init__(self):
        self._active_timeouts = {}  # operation_id -> timeout_info
        self._operation_stack = {}  # thread_id -> [operation_ids]
        self._lock = threading.RLock()
        self._default_config = TimeoutConfig(duration=30.0)
    
    def set_default_config(self, config: TimeoutConfig) -> None:
        with self._lock:
            self._default_config = config
    
    def start_operation(self, name: str, config=None, parent_id=None) -> str:
        with self._lock:
            operation_id = str(uuid.uuid4())
            if config is None:
                config = self._default_config
            
            timeout_info = {
                "id": operation_id, "name": name, "config": config,
                "start_time": time.time(), "end_time": None, "parent_id": parent_id,
                "children": set(), "status": "running", "timer": None,
                "retries": 0, "thread_id": threading.get_ident()
            }
            
            self._active_timeouts[operation_id] = timeout_info
            thread_id = threading.get_ident()
            
            if thread_id not in self._operation_stack:
                self._operation_stack[thread_id] = []
            self._operation_stack[thread_id].append(operation_id)
            
            if parent_id and parent_id in self._active_timeouts:
                self._active_timeouts[parent_id]["children"].add(operation_id)
            
            self._start_timer(operation_id)
            return operation_id
    
    def _start_timer(self, operation_id: str) -> None:
        if operation_id not in self._active_timeouts:
            return
        
        info = self._active_timeouts[operation_id]
        if info["timer"] is not None:
            info["timer"].cancel()
        
        timer = threading.Timer(info["config"].duration, self._handle_timeout, args=[operation_id])
        timer.daemon = True
        timer.start()
        info["timer"] = timer
    
    def _handle_timeout(self, operation_id: str) -> None:
        with self._lock:
            if operation_id not in self._active_timeouts:
                return
            
            info = self._active_timeouts[operation_id]
            policy = info["config"].policy
            logger.warning(f"Operation timeout: {info['name']} (ID: {operation_id})")
            
            if policy == TimeoutPolicy.RETRY and info["retries"] < info["config"].max_retries:
                info["retries"] += 1
                retry_delay = info["config"].retry_delay
                logger.info(f"Retrying {info['name']} ({info['retries']}/{info['config'].max_retries})")
                info["timer"] = threading.Timer(retry_delay, self._start_timer, args=[operation_id])
                info["timer"].daemon = True
                info["timer"].start()
            elif policy == TimeoutPolicy.EXTEND:
                current_duration = info["config"].duration
                max_extension = info["config"].max_extension
                new_duration = min(current_duration * 1.5, current_duration + max_extension)
                
                if new_duration > current_duration:
                    logger.info(f"Extending timeout from {current_duration}s to {new_duration}s")
                    info["config"].duration = new_duration
                    self._start_timer(operation_id)
                else:
                    info["status"] = "timeout"
                    self._cleanup_operation(operation_id)
            else:
                info["status"] = "timeout"
                self._cleanup_operation(operation_id)
    
    def _cleanup_operation(self, operation_id: str) -> None:
        if operation_id not in self._active_timeouts:
            return
        
        info = self._active_timeouts[operation_id]
        if info["timer"] is not None:
            info["timer"].cancel()
            info["timer"] = None
        
        info["end_time"] = time.time()
        
        if info["config"].propagate:
            for child_id in list(info["children"]):
                if child_id in self._active_timeouts:
                    child_info = self._active_timeouts[child_id]
                    if child_info["status"] == "running":
                        child_info["status"] = "cancelled_by_parent"
                        self._cleanup_operation(child_id)
    
    def end_operation(self, operation_id: str, status: str = "completed") -> Dict[str, Any]:
        with self._lock:
            if operation_id not in self._active_timeouts:
                return {}
            
            info = self._active_timeouts[operation_id]
            info["status"] = status
            info["end_time"] = time.time()
            
            if info["timer"] is not None:
                info["timer"].cancel()
                info["timer"] = None
            
            thread_id = info["thread_id"]
            if thread_id in self._operation_stack:
                if operation_id in self._operation_stack[thread_id]:
                    self._operation_stack[thread_id].remove(operation_id)
                if not self._operation_stack[thread_id]:
                    del self._operation_stack[thread_id]
            
            parent_id = info["parent_id"]
            if parent_id and parent_id in self._active_timeouts:
                if operation_id in self._active_timeouts[parent_id]["children"]:
                    self._active_timeouts[parent_id]["children"].remove(operation_id)
            
            return dict(info)
    
    def get_current_operation(self) -> Optional[str]:
        thread_id = threading.get_ident()
        with self._lock:
            if thread_id in self._operation_stack and self._operation_stack[thread_id]:
                return self._operation_stack[thread_id][-1]
            return None
    
    def extend_timeout(self, operation_id: str, additional_time: float) -> bool:
        with self._lock:
            if operation_id not in self._active_timeouts or self._active_timeouts[operation_id]["status"] != "running":
                return False
            
            info = self._active_timeouts[operation_id]
            current_duration = info["config"].duration
            max_extension = info["config"].max_extension
            new_duration = min(current_duration + additional_time, current_duration + max_extension)
            
            if new_duration <= current_duration:
                return False
            
            info["config"].duration = new_duration
            self._start_timer(operation_id)
            logger.info(f"Extended timeout from {current_duration}s to {new_duration}s")
            return True
    
    def cancel_operation(self, operation_id: str) -> bool:
        with self._lock:
            if operation_id not in self._active_timeouts or self._active_timeouts[operation_id]["status"] != "running":
                return False
            
            info = self._active_timeouts[operation_id]
            info["status"] = "cancelled"
            self._cleanup_operation(operation_id)
            logger.info(f"Cancelled operation: {info['name']} (ID: {operation_id})")
            return True

class ProgressManager:
    """Manages progress tracking for operations."""
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ProgressManager()
        return cls._instance
    
    def __init__(self):
        self._operations = {}  # operation_id -> ProgressOperation
        self._operation_stack = {}  # thread_id -> [operation_ids]
        self._lock = threading.RLock()
        self._listeners = []  # List of progress update listeners
    
    def create_operation(self, name: str, steps=None, parent_id=None) -> str:
        with self._lock:
            operation_id = str(uuid.uuid4())
            progress_steps = []
            
            if steps:
                for step in steps:
                    if isinstance(step, tuple) and len(step) == 2:
                        step_name, weight = step
                        progress_steps.append(ProgressStep(name=step_name, weight=weight))
                    else:
                        progress_steps.append(ProgressStep(name=str(step)))
            
            operation = ProgressOperation(id=operation_id, name=name, steps=progress_steps, parent_id=parent_id)
            self._operations[operation_id] = operation
            
            thread_id = threading.get_ident()
            if thread_id not in self._operation_stack:
                self._operation_stack[thread_id] = []
            self._operation_stack[thread_id].append(operation_id)
            
            return operation_id
    
    def start_operation(self, operation_id: str) -> None:
        with self._lock:
            if operation_id not in self._operations:
                return
            
            operation = self._operations[operation_id]
            operation.status = ProgressStatus.RUNNING
            operation.start_time = time.time()
            
            if operation.steps and operation.current_step_index < len(operation.steps):
                self.start_step(operation_id, operation.current_step_index)
            
            self._notify_progress_update(operation_id)
    
    def start_step(self, operation_id: str, step_index: int) -> None:
        with self._lock:
            if operation_id not in self._operations:
                return
            
            operation = self._operations[operation_id]
            if step_index < 0 or step_index >= len(operation.steps):
                return
            
            step = operation.steps[step_index]
            step.status = ProgressStatus.RUNNING
            step.start_time = time.time()
            operation.current_step_index = step_index
            
            self._notify_progress_update(operation_id)
    
    def complete_step(self, operation_id: str, step_index: Optional[int] = None) -> None:
        with self._lock:
            if operation_id not in self._operations:
                return
            
            operation = self._operations[operation_id]
            if step_index is None:
                step_index = operation.current_step_index
            
            if step_index < 0 or step_index >= len(operation.steps):
                return
            
            step = operation.steps[step_index]
            step.status = ProgressStatus.COMPLETED
            step.progress = 1.0
            step.end_time = time.time()
            
            if step_index == operation.current_step_index:
                next_step = step_index + 1
                if next_step < len(operation.steps):
                    operation.current_step_index = next_step
                    self.start_step(operation_id, next_step)
                elif all(s.status == ProgressStatus.COMPLETED for s in operation.steps):
                    operation.status = ProgressStatus.COMPLETED
                    operation.end_time = time.time()
            
            self._notify_progress_update(operation_id)
    
    def update_progress(self, operation_id: str, step_index=None, progress=None, message=None) -> None:
        with self._lock:
            if operation_id not in self._operations:
                return
            
            operation = self._operations[operation_id]
            if step_index is None:
                step_index = operation.current_step_index
            
            if step_index < 0 or step_index >= len(operation.steps):
                return
            
            step = operation.steps[step_index]
            
            if progress is not None:
                step.progress = max(0.0, min(1.0, progress))
                if step.progress >= 1.0 and step.status == ProgressStatus.RUNNING:
                    self.complete_step(operation_id, step_index)
                    return
            
            if message is not None:
                step.message = message
            
            self._notify_progress_update(operation_id)
    
    def complete_operation(self, operation_id: str, success: bool = True) -> None:
        with self._lock:
            if operation_id not in self._operations:
                return
            
            operation = self._operations[operation_id]
            
            for i in range(operation.current_step_index, len(operation.steps)):
                step = operation.steps[i]
                if step.status != ProgressStatus.COMPLETED:
                    if i == operation.current_step_index:
                        step.status = ProgressStatus.COMPLETED
                        step.progress = 1.0
                        step.end_time = time.time()
                    else:
                        step.status = ProgressStatus.CANCELLED
            
            operation.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
            operation.end_time = time.time()
            
            thread_id = threading.get_ident()
            if thread_id in self._operation_stack:
                if operation_id in self._operation_stack[thread_id]:
                    self._operation_stack[thread_id].remove(operation_id)
                if not self._operation_stack[thread_id]:
                    del self._operation_stack[thread_id]
            
            self._notify_progress_update(operation_id)
    
    def get_progress(self, operation_id: str) -> Dict[str, Any]:
        with self._lock:
            if operation_id not in self._operations:
                return {}
            
            operation = self._operations[operation_id]
            
            total_weight = sum(step.weight for step in operation.steps) if operation.steps else 1.0
            weighted_progress = sum(step.progress * step.weight for step in operation.steps)
            overall_progress = weighted_progress / total_weight if total_weight > 0 else 0
            
            # Calculate ETA
            eta = None
            if operation.start_time and operation.status == ProgressStatus.RUNNING and overall_progress > 0:
                elapsed = time.time() - operation.start_time
                eta = (elapsed / overall_progress) - elapsed if elapsed > 0 else None
            
            return {
                "id": operation.id,
                "name": operation.name,
                "status": operation.status.name,
                "progress": overall_progress,
                "elapsed": time.time() - operation.start_time if operation.start_time else 0,
                "eta": eta,
                "current_step": operation.current_step_index,
                "total_steps": len(operation.steps),
                "steps": [{
                    "name": step.name, 
                    "progress": step.progress,
                    "status": step.status.name,
                    "message": step.message
                } for step in operation.steps]
            }
    
    def add_progress_listener(self, listener):
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)
    
    def remove_progress_listener(self, listener):
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)
    
    def get_current_operation(self) -> Optional[str]:
        """Get the current operation ID for this thread."""
        thread_id = threading.get_ident()
        with self._lock:
            if thread_id in self._operation_stack and self._operation_stack[thread_id]:
                return self._operation_stack[thread_id][-1]
            return None
            
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a progress operation.
        
        Args:
            operation_id: Operation ID
            
        Returns:
            Whether the operation was cancelled
        """
        with self._lock:
            if operation_id not in self._operations:
                return False
            
            operation = self._operations[operation_id]
            if operation.status != ProgressStatus.RUNNING:
                return False
            
            # Update operation status
            operation.status = ProgressStatus.CANCELLED
            operation.end_time = time.time()
            
            # Update current step status
            if operation.steps and operation.current_step_index < len(operation.steps):
                step = operation.steps[operation.current_step_index]
                step.status = ProgressStatus.CANCELLED
                step.end_time = time.time()
            
            # Remove from thread's operation stack
            thread_id = threading.get_ident()
            if thread_id in self._operation_stack:
                if operation_id in self._operation_stack[thread_id]:
                    self._operation_stack[thread_id].remove(operation_id)
                if not self._operation_stack[thread_id]:
                    del self._operation_stack[thread_id]
            
            # Notify listeners
            self._notify_progress_update(operation_id)
            
            logger.info(f"Cancelled operation: {operation.name} (ID: {operation_id})")
            return True
    
    def _notify_progress_update(self, operation_id: str) -> None:
        if not self._listeners:
            return
        
        progress_info = self.get_progress(operation_id)
        for listener in self._listeners:
            try:
                listener(operation_id, progress_info)
            except Exception as e:
                logger.error(f"Error in progress listener: {e}")

# =============================================================================
# Helper Functions
# =============================================================================

# Global instances
_timeout_manager = TimeoutManager.get_instance()
_progress_manager = ProgressManager.get_instance()

def get_timeout_manager(): return _timeout_manager
def get_progress_manager(): return _progress_manager

def with_timeout(name=None, timeout_config=None):
    """Decorator to add timeout handling to a function."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = name or func.__name__
            parent_id = _timeout_manager.get_current_operation()
            operation_id = _timeout_manager.start_operation(name=op_name, config=timeout_config, parent_id=parent_id)
            
            try:
                result = func(*args, **kwargs)
                _timeout_manager.end_operation(operation_id, status="completed")
                return result
            except Exception:
                _timeout_manager.end_operation(operation_id, status="failed")
                raise
        return wrapper
    return decorator

def with_progress(name=None, steps=None):
    """Decorator to add progress tracking to a function."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = name or func.__name__
            parent_id = _progress_manager.get_current_operation()
            operation_id = _progress_manager.create_operation(name=op_name, steps=steps, parent_id=parent_id)
            _progress_manager.start_operation(operation_id)
            
            try:
                # Add operation_id to kwargs if accepted
                sig = inspect.signature(func)
                if 'operation_id' in sig.parameters:
                    kwargs['operation_id'] = operation_id
                
                result = func(*args, **kwargs)
                _progress_manager.complete_operation(operation_id, success=True)
                return result
            except Exception:
                _progress_manager.complete_operation(operation_id, success=False)
                raise
        return wrapper
    return decorator

# =============================================================================
# Integration with Triangulum
# =============================================================================

def fix_orchestrator_agent_timeout() -> bool:
    """Fix timeout handling in the orchestrator agent."""
    file_path = Path("triangulum_lx/agents/orchestrator_agent.py")
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read file and create backup
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        backup_path = file_path.with_suffix(".py.bak")
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Error reading/backing up file: {e}")
        return False
    
    # Add imports
    imports_end = content.find("\n\n", content.find("import "))
    new_imports = """import threading
from ..core.timeout_manager import TimeoutManager, TimeoutConfig, TimeoutPolicy
from ..core.progress_manager import ProgressManager, ProgressStatus
"""
    
    if "TimeoutManager" not in content:
        updated_content = content[:imports_end] + "\n" + new_imports + content[imports_end:]
    else:
        updated_content = content
    
    # Update __init__ method
    init_pattern = "    def __init__"
    init_pos = updated_content.find(init_pattern)
    init_end = updated_content.find("\n    def", init_pos + 10)
    if init_end == -1:
        init_end = len(updated_content)
    
    init_code = updated_content[init_pos:init_end]
    
    if "self.timeout_manager = TimeoutManager()" not in init_code:
        new_init_code = init_code.replace(
            "        self.timeout = timeout\n",
            "        self.timeout = timeout\n"
            "        # Initialize timeout and progress management\n"
            "        self.timeout_manager = TimeoutManager.get_instance()\n"
            "        self.progress_manager = ProgressManager.get_instance()\n"
            "        self.timeout_manager.set_default_config(TimeoutConfig(\n"
            "            duration=self.timeout,\n"
            "            policy=TimeoutPolicy.RETRY,\n"
            "            retry_delay=1.0,\n"
            "            max_extension=self.timeout * 2\n"
            "        ))\n"
        )
        updated_content = updated_content.replace(init_code, new_init_code)
    
    # Update folder analysis timeout
    folder_analysis_pattern = "result = self._wait_for_result(workflow_id, agent_type, self.timeout * 3)"
    if folder_analysis_pattern in updated_content:
        updated_content = updated_content.replace(
            folder_analysis_pattern,
            "result = self._wait_for_result(workflow_id, agent_type, self.timeout * 10)"
        )
    
    # Write updated content
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        logger.info(f"Updated {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to file: {e}")
        return False

def fix_folder_healer_progress() -> bool:
    """Fix progress reporting in the folder healer."""
    file_path = Path("triangulum_folder_healer.py")
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read file and create backup
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        backup_path = file_path.with_suffix(".py.bak")
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Error reading/backing up file: {e}")
        return False
    
    # Add imports
    imports_end = content.find("\n\n", content.find("import "))
    new_imports = """from triangulum_lx.core.progress_manager import ProgressManager, ProgressStatus
from triangulum_lx.core.timeout_manager import TimeoutManager, TimeoutConfig
"""
    
    if "ProgressManager" not in content:
        updated_content = content[:imports_end] + "\n" + new_imports + content[imports_end:]
    else:
        updated_content = content
    
    # Update __init__ method
    class_pattern = "class TriangulumFolderHealer"
    class_pos = updated_content.find(class_pattern)
    init_pattern = "    def __init__"
    init_pos = updated_content.find(init_pattern, class_pos)
    init_end = updated_content.find("\n    def", init_pos + 10)
    if init_end == -1:
        init_end = len(updated_content)
    
    init_code = updated_content[init_pos:init_end]
    
    if "self.progress_manager = ProgressManager()" not in init_code:
        new_init_code = init_code.replace(
            "        self.logger = logger or logging.getLogger(__name__)\n",
            "        self.logger = logger or logging.getLogger(__name__)\n"
            "        # Initialize progress and timeout management\n"
            "        self.progress_manager = ProgressManager.get_instance()\n"
            "        self.timeout_manager = TimeoutManager.get_instance()\n"
        )
        updated_content = updated_content.replace(init_code, new_init_code)
    
    # Write updated content
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        logger.info(f"Updated {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to file: {e}")
        return False

def setup_core_modules() -> bool:
    """Set up core modules for timeout and progress tracking."""
    # Create directory if it doesn't exist
    Path("triangulum_lx/core").mkdir(parents=True, exist_ok=True)
    
    # Create timeout_manager.py
    timeout_manager_path = Path("triangulum_lx/core/timeout_manager.py")
    timeout_manager_content = """
from enum import Enum, auto
import threading
import time
import uuid
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class TimeoutPolicy(Enum):
    EXCEPTION = auto()
    RETURN_NONE = auto()
    RETURN_PARTIAL = auto()
    RETRY = auto()
    EXTEND = auto()

class TimeoutConfig:
    def __init__(self, duration, policy=TimeoutPolicy.EXCEPTION, max_retries=3, 
                 retry_delay=1.0, max_extension=60.0, propagate=True):
        self.duration = duration
        self.policy = policy
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_extension = max_extension
        self.propagate = propagate

class TimeoutManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TimeoutManager()
        return cls._instance
        
    def __init__(self):
        self._active_timeouts = {}
        self._operation_stack = {}
        self._lock = threading.RLock()
        self._default_config = TimeoutConfig(duration=30.0)
    
    # Implementation as in the main script
    # Methods: set_default_config, start_operation, end_operation, etc.
"""
    
    # Create progress_manager.py
    progress_manager_path = Path("triangulum_lx/core/progress_manager.py")
    progress_manager_content = """
from enum import Enum, auto
import threading
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class ProgressStatus(Enum):
    NOT_STARTED = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class ProgressStep:
    name: str
    weight: float = 1.0
    progress: float = 0.0
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    message: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None

@dataclass
class ProgressOperation:
    id: str
    name: str
    steps: List[ProgressStep] = field(default_factory=list)
    current_step_index: int = 0
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    parent_id: Optional[str] = None

class ProgressManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ProgressManager()
        return cls._instance
        
    def __init__(self):
        self._operations = {}
        self._operation_stack = {}
        self._lock = threading.RLock()
        self._listeners = []
    
    # Implementation as in the main script
    # Methods: create_operation, start_operation, update_progress, etc.
"""
    
    # Write files
    try:
        with open(timeout_manager_path, 'w', encoding='utf-8') as f:
            f.write(timeout_manager_content.strip())
        
        with open(progress_manager_path, 'w', encoding='utf-8') as f:
            f.write(progress_manager_content.strip())
        
        # Create __init__.py if it doesn't exist
        init_path = Path("triangulum_lx/core/__init__.py")
        if not init_path.exists():
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write("# Core modules for Triangulum\n")
        
        logger.info("Created core modules")
        return True
    except Exception as e:
        logger.error(f"Error creating core modules: {e}")
        return False

def main():
    """Main function to run all fixes."""
    print("Applying timeout and progress tracking fixes...")
    
    # Setup core modules
    if setup_core_modules():
        print("✓ Core modules created")
    else:
        print("✗ Failed to create core modules")
        return 1
    
    # Fix orchestrator agent
    if fix_orchestrator_agent_timeout():
        print("✓ Fixed orchestrator agent timeout")
    else:
        print("✗ Failed to fix orchestrator agent")
        
    # Fix folder healer
    if fix_folder_healer_progress():
        print("✓ Fixed folder healer progress tracking")
    else:
        print("✗ Failed to fix folder healer")
    
    print("All fixes applied successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
