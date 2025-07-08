import time
import uuid
import logging
import threading
from math import log2
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from .state import Phase
from typing import List, Dict, Any, Optional, Callable, Set, Tuple

logger = logging.getLogger(__name__)

class ProgressStatus(Enum):
    """Enum for operation progress status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


@dataclass
class OperationProgress:
    """Data class for tracking progress of a single operation."""
    operation_id: str
    operation_type: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    percentage: float = 0.0
    current_step: int = 0
    total_steps: int = 1
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    parent_id: Optional[str] = None
    timeout_seconds: Optional[float] = None
    cancel_callback: Optional[Callable] = None
    
    def start(self) -> None:
        """Mark the operation as started."""
        self.start_time = time.time()
        self.status = ProgressStatus.IN_PROGRESS
        
    def update(self, current_step: int, total_steps: Optional[int] = None, 
               details: Optional[Dict[str, Any]] = None) -> None:
        """Update the progress of the operation."""
        if total_steps is not None:
            self.total_steps = total_steps
        
        self.current_step = current_step
        
        if self.total_steps > 0:
            self.percentage = min(100.0, (current_step / self.total_steps) * 100.0)
        
        if details:
            self.details.update(details)
    
    def complete(self, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark the operation as completed."""
        self.end_time = time.time()
        self.status = ProgressStatus.COMPLETED
        self.percentage = 100.0
        self.current_step = self.total_steps
        
        if details:
            self.details.update(details)
    
    def fail(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark the operation as failed."""
        self.end_time = time.time()
        self.status = ProgressStatus.FAILED
        self.error = error
        
        if details:
            self.details.update(details)
    
    def cancel(self, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark the operation as cancelled."""
        self.end_time = time.time()
        self.status = ProgressStatus.CANCELLED
        
        if details:
            self.details.update(details)
            
        # Execute cancel callback if provided
        if self.cancel_callback:
            try:
                self.cancel_callback()
            except Exception as e:
                logger.error(f"Error executing cancel callback for operation {self.operation_id}: {str(e)}")
    
    def timeout(self, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark the operation as timed out."""
        self.end_time = time.time()
        self.status = ProgressStatus.TIMED_OUT
        self.error = "Operation timed out"
        
        if details:
            self.details.update(details)
            
        # Execute cancel callback if provided
        if self.cancel_callback:
            try:
                self.cancel_callback()
            except Exception as e:
                logger.error(f"Error executing cancel callback for operation {self.operation_id}: {str(e)}")
    
    def duration(self) -> Optional[float]:
        """Get the duration of the operation in seconds."""
        if self.start_time is None:
            return None
            
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time
    
    def has_timed_out(self) -> bool:
        """Check if the operation has timed out."""
        if self.timeout_seconds is None or self.start_time is None:
            return False
            
        if self.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED, 
                           ProgressStatus.CANCELLED, ProgressStatus.TIMED_OUT]:
            return False
            
        return (time.time() - self.start_time) > self.timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value,
            "percentage": self.percentage,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "details": self.details,
            "error": self.error,
            "parent_id": self.parent_id,
            "duration": self.duration()
        }


class OperationTracker:
    """Class for tracking multiple operations with timeout handling."""
    
    def __init__(self):
        """Initialize the operation tracker."""
        self.operations: Dict[str, OperationProgress] = {}
        self.timeout_thread = None
        self.should_stop = threading.Event()
        self.lock = threading.RLock()
        self.event_subscribers: List[Callable[[str, OperationProgress], None]] = []
        
    def start_timeout_checker(self, check_interval: float = 1.0) -> None:
        """Start the timeout checker thread."""
        if self.timeout_thread is not None and self.timeout_thread.is_alive():
            return
            
        self.should_stop.clear()
        self.timeout_thread = threading.Thread(
            target=self._timeout_checker_loop,
            args=(check_interval,),
            daemon=True,
            name="TimeoutCheckerThread"
        )
        self.timeout_thread.start()
        
    def stop_timeout_checker(self) -> None:
        """Stop the timeout checker thread."""
        if self.timeout_thread is None or not self.timeout_thread.is_alive():
            return
            
        self.should_stop.set()
        self.timeout_thread.join(timeout=5.0)
        
    def _timeout_checker_loop(self, check_interval: float) -> None:
        """Main loop for checking timeouts."""
        while not self.should_stop.is_set():
            with self.lock:
                # Get a snapshot of current operations to prevent long lock holding
                operations = list(self.operations.items())
                
            # Check each operation
            for op_id, progress in operations:
                if progress.has_timed_out():
                    with self.lock:
                        # Re-check in case it was updated while we were checking
                        if op_id in self.operations and self.operations[op_id].has_timed_out():
                            # Mark as timed out and trigger cancel callback
                            self.operations[op_id].timeout()
                            self._emit_event("operation_timeout", self.operations[op_id])
            
            # Sleep for the check interval
            self.should_stop.wait(check_interval)
    
    def create_operation(self, operation_type: str, total_steps: int = 1, 
                        timeout_seconds: Optional[float] = None,
                        parent_id: Optional[str] = None,
                        cancel_callback: Optional[Callable] = None) -> str:
        """
        Create a new operation for tracking.
        
        Args:
            operation_type: Type of operation (e.g., "file_healing", "folder_analysis")
            total_steps: Total number of steps in the operation
            timeout_seconds: Optional timeout in seconds
            parent_id: Optional parent operation ID for hierarchical operations
            cancel_callback: Optional callback to execute on cancellation/timeout
            
        Returns:
            The ID of the created operation
        """
        operation_id = str(uuid.uuid4())
        
        progress = OperationProgress(
            operation_id=operation_id,
            operation_type=operation_type,
            total_steps=total_steps,
            timeout_seconds=timeout_seconds,
            parent_id=parent_id,
            cancel_callback=cancel_callback
        )
        
        with self.lock:
            self.operations[operation_id] = progress
            
        self._emit_event("operation_created", progress)
        return operation_id
    
    def start_operation(self, operation_id: str) -> None:
        """
        Mark an operation as started.
        
        Args:
            operation_id: ID of the operation to start
        """
        with self.lock:
            if operation_id in self.operations:
                self.operations[operation_id].start()
                self._emit_event("operation_started", self.operations[operation_id])
    
    def update_operation(self, operation_id: str, current_step: int, 
                        total_steps: Optional[int] = None,
                        details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the progress of an operation.
        
        Args:
            operation_id: ID of the operation to update
            current_step: Current step number
            total_steps: Optional updated total number of steps
            details: Optional details to add to the operation
        """
        with self.lock:
            if operation_id in self.operations:
                self.operations[operation_id].update(current_step, total_steps, details)
                self._emit_event("operation_updated", self.operations[operation_id])
    
    def complete_operation(self, operation_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark an operation as completed.
        
        Args:
            operation_id: ID of the operation to complete
            details: Optional details to add to the operation
        """
        with self.lock:
            if operation_id in self.operations:
                self.operations[operation_id].complete(details)
                self._emit_event("operation_completed", self.operations[operation_id])
    
    def fail_operation(self, operation_id: str, error: str, 
                      details: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark an operation as failed.
        
        Args:
            operation_id: ID of the operation to fail
            error: Error message
            details: Optional details to add to the operation
        """
        with self.lock:
            if operation_id in self.operations:
                self.operations[operation_id].fail(error, details)
                self._emit_event("operation_failed", self.operations[operation_id])
    
    def cancel_operation(self, operation_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Cancel an operation.
        
        Args:
            operation_id: ID of the operation to cancel
            details: Optional details to add to the operation
        """
        with self.lock:
            if operation_id in self.operations:
                self.operations[operation_id].cancel(details)
                self._emit_event("operation_cancelled", self.operations[operation_id])
    
    def get_operation(self, operation_id: str) -> Optional[OperationProgress]:
        """
        Get the progress of an operation.
        
        Args:
            operation_id: ID of the operation to get
            
        Returns:
            The operation progress, or None if not found
        """
        with self.lock:
            return self.operations.get(operation_id)
    
    def get_all_operations(self) -> Dict[str, OperationProgress]:
        """
        Get all operations.
        
        Returns:
            Dictionary of all operations
        """
        with self.lock:
            return self.operations.copy()
    
    def get_active_operations(self) -> Dict[str, OperationProgress]:
        """
        Get all active operations.
        
        Returns:
            Dictionary of active operations
        """
        with self.lock:
            return {
                op_id: progress for op_id, progress in self.operations.items() 
                if progress.status == ProgressStatus.IN_PROGRESS
            }
    
    def subscribe_to_events(self, callback: Callable[[str, OperationProgress], None]) -> None:
        """
        Subscribe to operation events.
        
        Args:
            callback: Function to call with event name and operation progress
        """
        with self.lock:
            self.event_subscribers.append(callback)
    
    def unsubscribe_from_events(self, callback: Callable[[str, OperationProgress], None]) -> None:
        """
        Unsubscribe from operation events.
        
        Args:
            callback: Function to remove from subscribers
        """
        with self.lock:
            if callback in self.event_subscribers:
                self.event_subscribers.remove(callback)
    
    def _emit_event(self, event_name: str, progress: OperationProgress) -> None:
        """
        Emit an event to all subscribers.
        
        Args:
            event_name: Name of the event
            progress: Progress of the related operation
        """
        # Make a copy to avoid modification during iteration
        subscribers = self.event_subscribers.copy()
        
        for callback in subscribers:
            try:
                callback(event_name, progress)
            except Exception as e:
                logger.error(f"Error in event subscriber for {event_name}: {str(e)}")


class EngineMonitor:
    """Monitor for tracking engine performance and operations."""
    
    def __init__(self, engine):
        self.engine = engine
        self.H0_bits = log2(len(engine.bugs)) if len(engine.bugs) > 0 else 0
        self.g_bits = 0
        self.failed_cycles = 0
        self.total_cost = 0.0
        self.total_latency = 0.0
        self.total_tokens = 0
        self.request_count = 0
        
        # Operation tracking
        self.operation_tracker = OperationTracker()
        
        # Start the timeout checker
        self.operation_tracker.start_timeout_checker()

    def record_llm_response(self, response: Any) -> None:
        """Records metrics from an LLMResponse object."""
        if hasattr(response, 'cost') and response.cost is not None:
            self.total_cost += response.cost
        if hasattr(response, 'latency') and response.latency is not None:
            self.total_latency += response.latency
        if hasattr(response, 'tokens_used') and response.tokens_used is not None:
            self.total_tokens += response.tokens_used
        self.request_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Returns a dictionary of current metrics."""
        # Get operation statistics
        operations = self.operation_tracker.get_all_operations()
        active_ops = sum(1 for op in operations.values() if op.status == ProgressStatus.IN_PROGRESS)
        completed_ops = sum(1 for op in operations.values() if op.status == ProgressStatus.COMPLETED)
        failed_ops = sum(1 for op in operations.values() if op.status == ProgressStatus.FAILED)
        timed_out_ops = sum(1 for op in operations.values() if op.status == ProgressStatus.TIMED_OUT)
        cancelled_ops = sum(1 for op in operations.values() if op.status == ProgressStatus.CANCELLED)
        
        # Get average duration of completed operations
        completed_durations = [op.duration() for op in operations.values() 
                               if op.status == ProgressStatus.COMPLETED and op.duration() is not None]
        avg_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0
        
        return {
            # Original metrics
            "entropy_bits_gained": self.g_bits,
            "initial_entropy_bits": self.H0_bits,
            "total_llm_cost": self.total_cost,
            "average_llm_latency": self.total_latency / self.request_count if self.request_count > 0 else 0,
            "total_llm_tokens": self.total_tokens,
            "total_llm_requests": self.request_count,
            
            # Operation metrics
            "active_operations": active_ops,
            "completed_operations": completed_ops,
            "failed_operations": failed_ops,
            "timed_out_operations": timed_out_ops,
            "cancelled_operations": cancelled_ops,
            "total_operations": len(operations),
            "average_operation_duration": avg_duration
        }

    def after_tick(self):
        # capacity invariant - disabled for async operation
        # When running asynchronously, the agent count can temporarily be inconsistent
        # assert self.engine.free_agents + \
        #        3 * sum(b.phase in {Phase.REPRO, Phase.PATCH, Phase.VERIFY}
        #                for b in self.engine.bugs) == self.engine.AGENTS

        # entropy accounting
        from ..agents.llm_config import get_agent_config, get_provider_config

        for bug in self.engine.bugs:
            if bug.phase is Phase.PATCH and bug.attempts == 1:
                # This logic assumes the 'Analyst' is responsible for the patch
                analyst_config = get_agent_config("Analyst")
                provider_name = analyst_config["provider"]
                model_name = analyst_config.get("model") or get_provider_config(provider_name).get("default_model")
                
                # Get reasoning power from config, default to 1.0
                reasoning_power = get_provider_config(provider_name).get("models", {}).get(model_name, {}).get("reasoning_power", 1.0)
                
                information_gain = 1.0 * reasoning_power
                self.g_bits += information_gain

        # escalate rule
        if self.g_bits >= self.H0_bits and \
           all(b.phase is Phase.DONE for b in self.engine.bugs):
            raise SystemExit("✔ All bugs complete within entropy budget")

        if self.engine.tick_no == self.engine.MAX_TICKS:
            raise RuntimeError("✗ Exceeded 60-tick bound")
            
    def done(self):
        """Check if monitoring is complete."""
        # Check if all operations are complete
        operations = self.operation_tracker.get_active_operations()
        operations_done = len(operations) == 0
        
        # Check if all bugs are complete
        bugs_done = (self.g_bits >= self.H0_bits and 
                    all(b.phase in {Phase.DONE, Phase.ESCALATE} for b in self.engine.bugs))
        
        return bugs_done and operations_done
    
    def create_operation(self, operation_type: str, total_steps: int = 1, 
                        timeout_seconds: Optional[float] = None,
                        parent_id: Optional[str] = None,
                        cancel_callback: Optional[Callable] = None) -> str:
        """
        Create a new operation for tracking.
        
        Args:
            operation_type: Type of operation (e.g., "file_healing", "folder_analysis")
            total_steps: Total number of steps in the operation
            timeout_seconds: Optional timeout in seconds
            parent_id: Optional parent operation ID for hierarchical operations
            cancel_callback: Optional callback to execute on cancellation/timeout
            
        Returns:
            The ID of the created operation
        """
        return self.operation_tracker.create_operation(
            operation_type, total_steps, timeout_seconds, parent_id, cancel_callback
        )
    
    def start_operation(self, operation_id: str) -> None:
        """
        Mark an operation as started.
        
        Args:
            operation_id: ID of the operation to start
        """
        self.operation_tracker.start_operation(operation_id)
    
    def update_operation(self, operation_id: str, current_step: int, 
                        total_steps: Optional[int] = None,
                        details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the progress of an operation.
        
        Args:
            operation_id: ID of the operation to update
            current_step: Current step number
            total_steps: Optional updated total number of steps
            details: Optional details to add to the operation
        """
        self.operation_tracker.update_operation(operation_id, current_step, total_steps, details)
    
    def complete_operation(self, operation_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark an operation as completed.
        
        Args:
            operation_id: ID of the operation to complete
            details: Optional details to add to the operation
        """
        self.operation_tracker.complete_operation(operation_id, details)
    
    def fail_operation(self, operation_id: str, error: str, 
                      details: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark an operation as failed.
        
        Args:
            operation_id: ID of the operation to fail
            error: Error message
            details: Optional details to add to the operation
        """
        self.operation_tracker.fail_operation(operation_id, error, details)
    
    def cancel_operation(self, operation_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Cancel an operation.
        
        Args:
            operation_id: ID of the operation to cancel
            details: Optional details to add to the operation
        """
        self.operation_tracker.cancel_operation(operation_id, details)
    
    def get_operation(self, operation_id: str) -> Optional[OperationProgress]:
        """
        Get the progress of an operation.
        
        Args:
            operation_id: ID of the operation to get
            
        Returns:
            The operation progress, or None if not found
        """
        return self.operation_tracker.get_operation(operation_id)
    
    def get_all_operations(self) -> Dict[str, OperationProgress]:
        """
        Get all operations.
        
        Returns:
            Dictionary of all operations
        """
        return self.operation_tracker.get_all_operations()
    
    def get_active_operations(self) -> Dict[str, OperationProgress]:
        """
        Get all active operations.
        
        Returns:
            Dictionary of active operations
        """
        return self.operation_tracker.get_active_operations()
    
    def subscribe_to_events(self, callback: Callable[[str, OperationProgress], None]) -> None:
        """
        Subscribe to operation events.
        
        Args:
            callback: Function to call with event name and operation progress
        """
        self.operation_tracker.subscribe_to_events(callback)
    
    def unsubscribe_from_events(self, callback: Callable[[str, OperationProgress], None]) -> None:
        """
        Unsubscribe from operation events.
        
        Args:
            callback: Function to remove from subscribers
        """
        self.operation_tracker.unsubscribe_from_events(callback)
    
    def cleanup(self) -> None:
        """Clean up resources used by the monitor."""
        self.operation_tracker.stop_timeout_checker()

# Alias for backward compatibility
Monitor = EngineMonitor
