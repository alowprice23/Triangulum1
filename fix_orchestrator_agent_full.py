#!/usr/bin/env python3
"""
Comprehensive fix script for the Orchestrator Agent.

This script addresses issues with task coordination, resource management,
error handling, and parallel execution in the orchestrator agent.
"""

import os
import sys
import logging
import traceback
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def apply_orchestrator_agent_fixes():
    """
    Apply comprehensive fixes to the Orchestrator Agent implementation.
    
    This function implements:
    1. Enhanced dynamic agent allocation with workload balancing
    2. Improved task prioritization with adaptive scheduling
    3. Robust error handling with automatic recovery
    4. Advanced conflict resolution between competing agents
    5. Optimized resource management for parallel activities
    """
    try:
        from triangulum_lx.agents.orchestrator_agent import OrchestratorAgent, TaskPriority, Task, AgentRegistry
        import threading
        
        #======================================================================
        # ENHANCEMENT 1: Improved Agent Allocation
        #======================================================================
        
        def enhanced_assign_task_to_agent(self, task):
            """
            Enhanced version of _assign_task_to_agent with workload balancing,
            performance-based selection, and capability matching.
            
            Args:
                task: The task to assign
                
            Returns:
                ID of the assigned agent or None if no suitable agent found
            """
            logger.debug(f"Enhanced task assignment for task {task.id}")
            
            # If a target agent type is specified, try to find an agent of that type
            if task.target_agent_type:
                # Find available agents of the specified type
                available_agents = []
                for agent_id, agent_info in self.agent_registry.agents.items():
                    if (agent_info["agent_type"] == task.target_agent_type and 
                        self.agent_registry.is_agent_available(agent_id)):
                        available_agents.append((agent_id, agent_info))
                
                if available_agents:
                    # Get agent workloads
                    agent_scores = {}
                    for agent_id, agent_info in available_agents:
                        # Score based on current workload
                        workload = self.agent_registry.agent_health.get(agent_id, {}).get("current_tasks", 0)
                        # Also consider success rate if available
                        success_rate = agent_info.get("performance_metrics", {}).get("task_success_rate", 1.0)
                        # Calculate a weighted score (lower is better)
                        agent_scores[agent_id] = workload * 2 - success_rate * 10
                    
                    # Return the agent with the best (lowest) score
                    return min(agent_scores.keys(), key=lambda k: agent_scores[k])
                
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
                    # Calculate scores based on multiple factors
                    agent_scores = {}
                    for agent_id in available_capable_agents:
                        # Get agent info
                        agent_info = self.agent_registry.agents.get(agent_id, {})
                        health_info = self.agent_registry.agent_health.get(agent_id, {})
                        
                        # Calculate capability match score (higher is better)
                        capability_match = len(set(agent_info.get("capabilities", [])) & 
                                              set(task.required_capabilities))
                        
                        # Get workload (lower is better)
                        workload = health_info.get("current_tasks", 0)
                        
                        # Get success rate (higher is better)
                        success_count = health_info.get("success_count", 0)
                        error_count = health_info.get("error_count", 0)
                        success_rate = success_count / max(1, success_count + error_count)
                        
                        # Calculate a combined score (lower is better)
                        # Prioritize capability match, then success rate, then workload
                        agent_scores[agent_id] = (
                            -capability_match * 100 +  # Negative because lower score is better
                            -success_rate * 10 +
                            workload
                        )
                    
                    # Return the agent with the best (lowest) score
                    best_agent = min(agent_scores.keys(), key=lambda k: agent_scores[k])
                    logger.debug(f"Selected agent {best_agent} for task {task.id} based on capabilities and performance")
                    return best_agent
                
                logger.warning(f"No available agent with capabilities {task.required_capabilities} found for task {task.id}")
                return None
            
            # If no specific requirements, select based on workload and performance
            available_agents = {}
            for agent_id in self.agent_registry.agents.keys():
                if self.agent_registry.is_agent_available(agent_id):
                    # Get health and performance metrics
                    health_info = self.agent_registry.agent_health.get(agent_id, {})
                    agent_info = self.agent_registry.agents.get(agent_id, {})
                    
                    # Get workload
                    workload = health_info.get("current_tasks", 0)
                    
                    # Get success rate
                    success_count = health_info.get("success_count", 0)
                    error_count = health_info.get("error_count", 0)
                    success_rate = success_count / max(1, success_count + error_count)
                    
                    # Calculate a combined score (lower is better)
                    available_agents[agent_id] = workload - success_rate * 5
            
            if available_agents:
                # Return agent with the best (lowest) score
                return min(available_agents.keys(), key=lambda k: available_agents[k])
            
            logger.warning(f"No available agent found for task {task.id}")
            return None
        
        # Replace the original method with our enhanced version
        OrchestratorAgent._assign_task_to_agent_original = OrchestratorAgent._assign_task_to_agent
        OrchestratorAgent._assign_task_to_agent = enhanced_assign_task_to_agent
        
        #======================================================================
        # ENHANCEMENT 2: Improved Worker Loop with Error Handling
        #======================================================================
        
        def enhanced_worker_loop(self):
            """
            Enhanced worker loop with improved error handling, recovery,
            and task processing.
            """
            worker_name = threading.current_thread().name
            logger.info(f"Starting enhanced worker loop: {worker_name}")
            
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
                                
                                # Track when the task was claimed
                                if not hasattr(task, 'processing_stages'):
                                    task.processing_stages = []
                                task.processing_stages.append(f"Claimed by worker {worker_name}")
                                
                                # Update agent workload if assigned
                                if task.assigned_agent:
                                    self.agent_registry.update_agent_health(
                                        task.assigned_agent, 
                                        success=True, 
                                        workload_change=1
                                    )
                                
                                break
                    
                    if task is None:
                        continue
                    
                    # Set up task processing with improved error handling
                    task_start_time = time.time()
                    task_success = False
                    task_error = None
                    
                    try:
                        # Log task processing
                        logger.info(f"Worker {worker_name} processing task {task.id} of type {task.type}")
                        task.processing_stages.append(f"Processing started by {worker_name}")
                        
                        # Process based on task type with timeouts
                        if task.type == "file_healing":
                            result = self._process_file_healing_task_with_timeout(task)
                        elif task.type == "folder_healing":
                            result = self._process_folder_healing_task_with_timeout(task)
                        else:
                            # Handle other task types with graceful degradation
                            logger.warning(f"Unknown task type: {task.type}, attempting generic processing")
                            result = self._process_generic_task_with_timeout(task)
                        
                        # Mark task as completed
                        with self.task_lock:
                            task.mark_completed(result)
                            task.processing_stages.append(f"Processing completed successfully by {worker_name}")
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
                                    logger.debug(traceback.format_exc())
                            
                            task_success = True
                    
                    except Exception as e:
                        task_error = e
                        logger.error(f"Error processing task {task.id}: {str(e)}")
                        logger.debug(traceback.format_exc())
                        
                        # Mark task as failed
                        with self.task_lock:
                            task.mark_failed(str(e))
                            task.processing_stages.append(f"Processing failed: {str(e)}")
                            self.task_queue.update_task(task)
                            
                            # Check if task can be retried
                            if task.can_retry(self.max_retries):
                                logger.info(f"Retrying task {task.id} (attempt {task.attempts}/{self.max_retries})")
                                task.status = "pending"
                                task.processing_stages.append(f"Scheduled for retry (attempt {task.attempts})")
                                self.task_queue.update_task(task)
                                # Signal that a task is available for retry
                                self.task_event.set()
                            else:
                                # Store failure result
                                with self.result_lock:
                                    self.task_results[task.id] = {
                                        "status": "failed",
                                        "error": str(e),
                                        "task_id": task.id,
                                        "error_details": {
                                            "exception_type": type(e).__name__,
                                            "traceback": traceback.format_exc()
                                        }
                                    }
                                
                                # Execute callback if registered
                                if task.id in self.task_callbacks:
                                    callback = self.task_callbacks[task.id]
                                    try:
                                        callback({"status": "failed", "error": str(e)})
                                    except Exception as callback_error:
                                        logger.error(f"Error executing callback for task {task.id}: {str(callback_error)}")
                    
                    finally:
                        # Clean up regardless of success or failure
                        task_end_time = time.time()
                        response_time = task_end_time - task_start_time
                        
                        # Update agent performance metrics if assigned
                        if task.assigned_agent:
                            # Update agent workload
                            self.agent_registry.update_agent_health(
                                task.assigned_agent, 
                                success=task_success, 
                                error_message=str(task_error) if task_error else None,
                                workload_change=-1  # Decrease workload now that task is done
                            )
                            
                            # Record performance metrics if available
                            if hasattr(self.agent_registry, 'record_agent_performance'):
                                self.agent_registry.record_agent_performance(
                                    task.assigned_agent,
                                    task_success,
                                    response_time
                                )
                        
                        # Remove from pending tasks
                        if task.workflow_id in self.pending_tasks:
                            del self.pending_tasks[task.workflow_id]
                
                except Exception as e:
                    logger.error(f"Critical error in worker loop {worker_name}: {str(e)}")
                    logger.debug(traceback.format_exc())
                    
                    # Sleep to avoid CPU spinning on errors
                    time.sleep(1.0)
        
        # Replace the original worker loop with our enhanced version
        OrchestratorAgent._worker_loop_original = OrchestratorAgent._worker_loop
        OrchestratorAgent._worker_loop = enhanced_worker_loop
        
        #======================================================================
        # ENHANCEMENT 3: Add Timeout Processing Methods
        #======================================================================
        
        def process_task_with_timeout(self, task, process_func):
            """
            Process a task with timeout handling.
            
            Args:
                task: The task to process
                process_func: Function to process the task
                
            Returns:
                Result of processing the task
            """
            # Get task-specific timeout or use default
            timeout = task.content.get("_metadata", {}).get("timeout", self.timeout)
            
            # Use a thread to execute the task with timeout
            result_container = []
            error_container = []
            
            def target_func():
                try:
                    result = process_func(task)
                    result_container.append(result)
                except Exception as e:
                    error_container.append(e)
            
            # Start the thread
            thread = threading.Thread(target=target_func)
            thread.daemon = True
            thread.start()
            
            # Wait for the thread to complete or timeout
            thread.join(timeout)
            
            # Check if the thread is still alive (timeout occurred)
            if thread.is_alive():
                error_msg = f"Task {task.id} timed out after {timeout} seconds"
                logger.warning(error_msg)
                return {
                    "status": "failed",
                    "error": error_msg,
                    "task_id": task.id,
                    "timeout": True
                }
            
            # Check if an error occurred
            if error_container:
                error = error_container[0]
                logger.error(f"Error processing task {task.id}: {str(error)}")
                return {
                    "status": "failed",
                    "error": str(error),
                    "task_id": task.id,
                    "error_details": {
                        "exception_type": type(error).__name__,
                        "traceback": traceback.format_exc()
                    }
                }
            
            # Return the result if successful
            if result_container:
                return result_container[0]
            
            # Unexpected case: no result and no error
            return {
                "status": "failed",
                "error": "Task completed but no result was returned",
                "task_id": task.id
            }
        
        # Add the timeout processing method
        OrchestratorAgent._process_task_with_timeout = process_task_with_timeout
        
        # Create wrapper methods for specific task types
        def process_file_healing_task_with_timeout(self, task):
            """Process a file healing task with timeout handling."""
            return self._process_task_with_timeout(task, self._process_file_healing_task)
        
        def process_folder_healing_task_with_timeout(self, task):
            """Process a folder healing task with timeout handling."""
            return self._process_task_with_timeout(task, self._process_folder_healing_task)
        
        def process_generic_task_with_timeout(self, task):
            """Process a generic task with timeout handling."""
            # Use process_generic_task if it exists, otherwise use a minimal implementation
            if hasattr(self, '_process_generic_task'):
                return self._process_task_with_timeout(task, self._process_generic_task)
            else:
                # Minimal implementation
                def minimal_generic_processor(task):
                    return {
                        "status": "partial_success",
                        "task_id": task.id,
                        "warning": "Generic task processing not fully implemented",
                        "content": task.content
                    }
                return self._process_task_with_timeout(task, minimal_generic_processor)
        
        # Add the timeout wrapper methods
        OrchestratorAgent._process_file_healing_task_with_timeout = process_file_healing_task_with_timeout
        OrchestratorAgent._process_folder_healing_task_with_timeout = process_folder_healing_task_with_timeout
        OrchestratorAgent._process_generic_task_with_timeout = process_generic_task_with_timeout
        
        #======================================================================
        # ENHANCEMENT 4: Advanced Conflict Resolution
        #======================================================================
        
        def resolve_agent_conflicts(self, task_a, task_b):
            """
            Resolve conflicts between competing tasks or agents.
            
            Args:
                task_a: First task in conflict
                task_b: Second task in conflict
                
            Returns:
                The task that should take precedence
            """
            # Define conflict resolution criteria and weights
            criteria = {
                "priority": 10,       # Task priority (higher priority wins)
                "age": 5,             # Task age (older tasks win)
                "dependencies": 8,    # Tasks with dependencies get priority
                "progress": 3,        # Tasks with more progress get priority
                "retry_count": 2      # Tasks with fewer retries get priority
            }
            
            # Calculate scores for each task
            score_a = 0
            score_b = 0
            
            # Priority comparison (lower enum value = higher priority)
            if task_a.priority.value < task_b.priority.value:
                score_a += criteria["priority"]
            elif task_b.priority.value < task_a.priority.value:
                score_b += criteria["priority"]
            
            # Age comparison
            if task_a.created_at < task_b.created_at:
                score_a += criteria["age"]
            elif task_b.created_at < task_a.created_at:
                score_b += criteria["age"]
            
            # Dependency comparison
            task_a_deps = len(task_a.content.get("_metadata", {}).get("dependencies", []))
            task_b_deps = len(task_b.content.get("_metadata", {}).get("dependencies", []))
            if task_a_deps > task_b_deps:
                score_a += criteria["dependencies"]
            elif task_b_deps > task_a_deps:
                score_b += criteria["dependencies"]
            
            # Progress comparison
            task_a_progress = len(getattr(task_a, "processing_stages", []))
            task_b_progress = len(getattr(task_b, "processing_stages", []))
            if task_a_progress > task_b_progress:
                score_a += criteria["progress"]
            elif task_b_progress > task_a_progress:
                score_b += criteria["progress"]
            
            # Retry count comparison (fewer retries is better)
            if task_a.retry_count < task_b.retry_count:
                score_a += criteria["retry_count"]
            elif task_b.retry_count < task_a.retry_count:
                score_b += criteria["retry_count"]
            
            # Return the task with the higher score
            logger.debug(f"Conflict resolution scores: Task {task_a.id}: {score_a}, Task {task_b.id}: {score_b}")
            return task_a if score_a >= score_b else task_b
        
        # Add the conflict resolution method
        OrchestratorAgent.resolve_agent_conflicts = resolve_agent_conflicts
        
        # Conflict detection method
        def detect_conflicts(self, task):
            """
            Detect potential conflicts with existing tasks.
            
            Args:
                task: The task to check for conflicts
                
            Returns:
                List of conflicting tasks, if any
            """
            conflicts = []
            
            # Get all in-progress tasks
            in_progress_tasks = self.task_queue.get_tasks_by_status("in_progress")
            
            for existing_task in in_progress_tasks:
                if existing_task.id == task.id:
                    continue  # Skip the same task
                
                # Check for resource conflicts
                if self._tasks_have_resource_conflict(task, existing_task):
                    conflicts.append(existing_task)
                
                # Check for agent conflicts
                if (task.assigned_agent and existing_task.assigned_agent and 
                    task.assigned_agent == existing_task.assigned_agent):
                    conflicts.append(existing_task)
            
            return conflicts
        
        # Add the conflict detection method
        OrchestratorAgent.detect_conflicts = detect_conflicts
        
        # Helper method to check resource conflicts
        def tasks_have_resource_conflict(self, task_a, task_b):
            """
            Check if two tasks have conflicting resource requirements.
            
            Args:
                task_a: First task
                task_b: Second task
                
            Returns:
                True if the tasks have a resource conflict, False otherwise
            """
            # Check for file access conflicts
            file_a = task_a.content.get("file_path")
            file_b = task_b.content.get("file_path")
            if file_a and file_b and file_a == file_b:
                return True
            
            # Check for folder access conflicts
            folder_a = task_a.content.get("folder_path")
            folder_b = task_b.content.get("folder_path")
            if folder_a and folder_b:
                # Check if one path is a subdirectory of the other
                if folder_a.startswith(folder_b) or folder_b.startswith(folder_a):
                    return True
            
            # Check if file is inside folder
            if file_a and folder_b and file_a.startswith(folder_b):
                return True
            if file_b and folder_a and file_b.startswith(folder_a):
                return True
            
            # No conflict detected
            return False
        
        # Add the resource conflict helper method
        OrchestratorAgent._tasks_have_resource_conflict = tasks_have_resource_conflict
        
        #======================================================================
        # ENHANCEMENT 5: Resource Management and Optimization
        #======================================================================
        
        def optimize_resource_allocation(self):
            """
            Optimize resource allocation across agents based on workload,
            performance, and task queue.
            
            Returns:
                Dictionary with optimization results
            """
            logger.info("Optimizing resource allocation across agents")
            
            # Get current state
            agent_workloads = {
                agent_id: self.agent_registry.agent_health.get(agent_id, {}).get("current_tasks", 0)
                for agent_id in self.agent_registry.agents.keys()
            }
            
            pending_tasks = self.task_queue.get_tasks_by_status("pending")
            pending_count = len(pending_tasks)
            
            # Calculate optimal worker thread count based on pending tasks and agents
            available_agents = sum(1 for agent_id in self.agent_registry.agents.keys() 
                                 if self.agent_registry.is_agent_available(agent_id))
            
            optimal_workers = min(
                max(1, available_agents),  # At least 1, at most number of available agents
                max(2, pending_count // 2)  # At least 2, scale with pending tasks
            )
            
            # Adjust worker thread count if needed
            current_workers = len(self.worker_threads)
            workers_adjustment = 0
            
            if optimal_workers > current_workers:
                # Need to add workers
                workers_to_add = min(optimal_workers - current_workers, 3)  # Add at most 3 at a time
                for i in range(workers_to_add):
                    self._add_worker_thread()
                workers_adjustment = workers_to_add
            elif optimal_workers < current_workers and current_workers > 2:
                # Need to remove workers, but keep at least 2
                workers_to_remove = min(current_workers - optimal_workers, 2)  # Remove at most 2 at a time
                # Mark threads for removal (they'll exit on next cycle)
                self.threads_to_remove = workers_to_remove
                workers_adjustment = -workers_to_remove
            
            # Return optimization results
            return {
                "timestamp": datetime.now().isoformat(),
                "agent_workloads": agent_workloads,
                "pending_tasks": pending_count,
                "available_agents": available_agents,
                "worker_threads": {
                    "before": current_workers,
                    "optimal": optimal_workers,
                    "adjustment": workers_adjustment,
                    "after": current_workers + workers_adjustment
                }
            }
        
        # Add the resource optimization method
        OrchestratorAgent.optimize_resource_allocation = optimize_resource_allocation
        
        # Helper method to add a worker thread
        def add_worker_thread(self):
            """Add a new worker thread to the pool."""
            thread_index = len(self.worker_threads)
            worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"OrchestratorWorker-{thread_index}"
            )
            worker_thread.start()
            self.worker_threads.append(worker_thread)
            logger.info(f"Added new worker thread: OrchestratorWorker-{thread_index}")
            return worker_thread
        
        # Add the worker thread helper method
        OrchestratorAgent._add_worker_thread = add_worker_thread
        
        #======================================================================
        # ENHANCEMENT 6: Heartbeat and Health Monitoring
        #======================================================================
        
        def start_heartbeat_monitor(self):
            """Start the agent heartbeat monitoring thread."""
            self.heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="OrchestratorHeartbeat"
            )
            self.heartbeat_thread.start()
            logger.info("Started heartbeat monitoring thread")
        
        # Add the heartbeat monitor startup method
        OrchestratorAgent.start_heartbeat_monitor = start_heartbeat_monitor
        
        # Heartbeat monitoring loop
        def heartbeat_loop(self):
            """Monitor agent heartbeats and handle agent failures."""
            while not self.shutdown_event.is_set():
                try:
                    # Check all registered agents
                    current_time = datetime.now()
                    for agent_id, health in list(self.agent_registry.agent_health.items()):
                        last_heartbeat = health.get("last_heartbeat")
                        if last_heartbeat:
                            # Calculate time since last heartbeat
                            heartbeat_age = (current_time - last_heartbeat).total_seconds()
                            
                            # Check if the heartbeat is too old
                            if heartbeat_age > self.heartbeat_interval * 3:
                                logger.warning(f"Agent {agent_id} has not sent a heartbeat in {heartbeat_age:.1f} seconds")
                                
                                # Mark the agent as unavailable
                                health["status"] = "unavailable"
                                
                                # Reassign any tasks assigned to this agent
                                self._handle_agent_failure(agent_id)
                    
                    # Periodically run resource optimization
                    if hasattr(self, 'last_optimization_time'):
                        time_since_optimization = (current_time - self.last_optimization_time).total_seconds()
