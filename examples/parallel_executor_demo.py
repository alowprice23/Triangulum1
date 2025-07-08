"""
Parallel Executor Demo

This demo showcases the capabilities of the enhanced Parallel Executor for
efficiently executing multiple tasks concurrently with advanced features:

1. Dynamic scaling of concurrent execution
2. Resource-aware scheduling
3. Priority-based execution queuing
4. Work stealing for load balancing
5. Timeout and cancellation support
6. Progress tracking and reporting
7. Failure isolation and recovery
"""

import os
import sys
import time
import asyncio
import logging
import random
from pathlib import Path
from typing import Dict, List, Any

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.core.parallel_executor import (
    ParallelExecutor, TaskContext, ExecutionMode, ResourceRequirements
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define some example tasks
def cpu_intensive_task(iterations: int, complexity: int = 1000000) -> Dict[str, Any]:
    """
    A CPU-intensive task that performs mathematical calculations.
    
    Args:
        iterations: Number of calculation iterations
        complexity: Complexity factor for calculations
        
    Returns:
        Dictionary with task results
    """
    start_time = time.time()
    result = 0
    
    for i in range(iterations):
        # Perform some CPU-intensive calculations
        for j in range(complexity):
            result += (i * j) % (j + 1 or 1)
            if j % 10000 == 0:
                # Simulate progress reporting
                progress = (i * complexity + j) / (iterations * complexity)
                logger.debug(f"CPU task progress: {progress:.2%}")
    
    end_time = time.time()
    return {
        "task_type": "cpu_intensive",
        "iterations": iterations,
        "complexity": complexity,
        "result": result,
        "execution_time": end_time - start_time
    }

def io_intensive_task(file_count: int, size_kb: int = 100) -> Dict[str, Any]:
    """
    An IO-intensive task that performs file operations.
    
    Args:
        file_count: Number of files to create and read
        size_kb: Size of each file in KB
        
    Returns:
        Dictionary with task results
    """
    start_time = time.time()
    temp_dir = Path("temp_io_task")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Create and write to files
        files = []
        for i in range(file_count):
            file_path = temp_dir / f"file_{i}.dat"
            with open(file_path, "wb") as f:
                f.write(os.urandom(size_kb * 1024))
            files.append(file_path)
            
            # Simulate progress reporting
            progress = (i + 1) / file_count
            logger.debug(f"IO task progress (writing): {progress:.2%}")
        
        # Read files
        total_bytes = 0
        for i, file_path in enumerate(files):
            with open(file_path, "rb") as f:
                data = f.read()
                total_bytes += len(data)
            
            # Simulate progress reporting
            progress = (i + 1) / file_count
            logger.debug(f"IO task progress (reading): {progress:.2%}")
        
        end_time = time.time()
        return {
            "task_type": "io_intensive",
            "file_count": file_count,
            "size_kb": size_kb,
            "total_bytes": total_bytes,
            "execution_time": end_time - start_time
        }
    finally:
        # Clean up
        for file_path in temp_dir.glob("*.dat"):
            file_path.unlink(missing_ok=True)
        temp_dir.rmdir()

def memory_intensive_task(size_mb: int) -> Dict[str, Any]:
    """
    A memory-intensive task that allocates and manipulates large arrays.
    
    Args:
        size_mb: Size of memory to allocate in MB
        
    Returns:
        Dictionary with task results
    """
    start_time = time.time()
    
    # Allocate a large array
    array_size = size_mb * 1024 * 1024 // 8  # 8 bytes per element
    large_array = [random.random() for _ in range(array_size)]
    
    # Perform some operations on the array
    sum_value = sum(large_array[:1000000])
    min_value = min(large_array[:1000000])
    max_value = max(large_array[:1000000])
    
    end_time = time.time()
    return {
        "task_type": "memory_intensive",
        "size_mb": size_mb,
        "array_size": array_size,
        "sum_sample": sum_value,
        "min_sample": min_value,
        "max_sample": max_value,
        "execution_time": end_time - start_time
    }

def failing_task() -> None:
    """A task that always fails with an exception."""
    time.sleep(1)  # Simulate some work
    raise ValueError("This task is designed to fail")

def timeout_task(sleep_time: int) -> Dict[str, Any]:
    """
    A task that sleeps for a specified time.
    
    Args:
        sleep_time: Time to sleep in seconds
        
    Returns:
        Dictionary with task results
    """
    time.sleep(sleep_time)
    return {
        "task_type": "timeout",
        "sleep_time": sleep_time
    }

def progress_reporting_task(steps: int, step_time: float = 0.5) -> Dict[str, Any]:
    """
    A task that reports progress as it executes.
    
    Args:
        steps: Number of steps to execute
        step_time: Time to sleep between steps
        
    Returns:
        Dictionary with task results
    """
    results = []
    for i in range(steps):
        # Simulate work
        time.sleep(step_time)
        
        # Record result
        results.append(i * i)
        
        # Report progress (this would be captured by the progress callback)
        progress = (i + 1) / steps
        logger.debug(f"Progress task: {progress:.2%} complete")
    
    return {
        "task_type": "progress_reporting",
        "steps": steps,
        "step_time": step_time,
        "results": results
    }

async def run_demo() -> None:
    """Run the parallel executor demo."""
    logger.info("Starting Parallel Executor Demo")
    
    # Create a parallel executor with various configurations
    executor = ParallelExecutor(
        max_workers=8,
        min_workers=2,
        execution_mode=ExecutionMode.HYBRID,
        adaptive_scaling=True,
        stall_threshold=30.0,
        max_retries=2,
        work_stealing=True
    )
    
    # Define task progress callback
    def progress_callback(progress: float, message: str) -> None:
        logger.info(f"Progress update: {progress:.2%} - {message}")
    
    # Add various tasks with different priorities and resource requirements
    tasks = []
    
    # CPU-intensive tasks
    for i in range(3):
        task_id = executor.add_task(
            function=cpu_intensive_task,
            args=(10, 100000),
            priority=i,  # Lower number = higher priority
            resource_requirements={"cpu": 1.0, "memory": 100.0},
            progress_callback=progress_callback
        )
        tasks.append(("cpu", task_id))
    
    # IO-intensive tasks
    for i in range(2):
        task_id = executor.add_task(
            function=io_intensive_task,
            args=(5, 100),
            priority=i + 3,
            resource_requirements={"cpu": 0.5, "memory": 50.0, "io": 100.0},
            progress_callback=progress_callback
        )
        tasks.append(("io", task_id))
    
    # Memory-intensive tasks
    for i in range(2):
        task_id = executor.add_task(
            function=memory_intensive_task,
            args=(100,),  # 100 MB
            priority=i + 5,
            resource_requirements={"cpu": 0.5, "memory": 200.0},
            progress_callback=progress_callback
        )
        tasks.append(("memory", task_id))
    
    # Task with timeout
    task_id = executor.add_task(
        function=timeout_task,
        args=(10,),  # 10 seconds
        timeout=5,  # 5 second timeout
        priority=7,
        progress_callback=progress_callback
    )
    tasks.append(("timeout", task_id))
    
    # Failing task
    task_id = executor.add_task(
        function=failing_task,
        priority=8,
        progress_callback=progress_callback
    )
    tasks.append(("failing", task_id))
    
    # Progress reporting task
    task_id = executor.add_task(
        function=progress_reporting_task,
        args=(10, 0.5),  # 10 steps, 0.5 seconds per step
        priority=9,
        progress_callback=progress_callback
    )
    tasks.append(("progress", task_id))
    
    # Task with dependencies
    task_id_1 = executor.add_task(
        function=progress_reporting_task,
        args=(5, 0.2),
        priority=10,
        progress_callback=progress_callback
    )
    tasks.append(("dependency_1", task_id_1))
    
    task_id_2 = executor.add_task(
        function=progress_reporting_task,
        args=(5, 0.2),
        priority=11,
        dependencies=[task_id_1],  # This task depends on task_id_1
        progress_callback=progress_callback
    )
    tasks.append(("dependency_2", task_id_2))
    
    # Run the executor until all tasks are complete
    logger.info("Running executor until all tasks complete...")
    results = await executor.run_until_complete()
    
    # Print results
    logger.info("Execution completed with the following results:")
    logger.info(f"Total tasks: {results['total_tasks']}")
    logger.info(f"Completed tasks: {results['completed_tasks']}")
    logger.info(f"Failed tasks: {results['failed_tasks']}")
    logger.info(f"Cancelled tasks: {results['cancelled_tasks']}")
    logger.info(f"Success rate: {results['success_rate_tasks']:.2%}")
    logger.info(f"Total execution time: {results['elapsed_time']:.2f} seconds")
    logger.info(f"Average task time: {results['average_task_time']:.2f} seconds")
    
    # Print task results
    logger.info("\nTask results:")
    for task_type, task_id in tasks:
        status = executor.get_task_status(task_id)
        logger.info(f"Task {task_id} ({task_type}): {status.name if status else 'UNKNOWN'}")
        
        if status and status.name == "COMPLETED":
            result = executor.get_task_result(task_id)
            if isinstance(result, dict) and "execution_time" in result:
                logger.info(f"  Execution time: {result['execution_time']:.2f} seconds")
        elif status and status.name == "FAILED":
            exception = executor.get_task_exception(task_id)
            logger.info(f"  Failed with exception: {exception}")
    
    # Print executor metrics
    logger.info("\nExecutor metrics:")
    metrics = executor.get_all_metrics()
    logger.info(f"Worker utilization: {metrics['executor']['worker_utilization']:.2%}")
    logger.info(f"CPU utilization: {metrics['executor']['resource_utilization']['cpu']:.2%}")
    logger.info(f"Memory utilization: {metrics['executor']['resource_utilization']['memory']:.2%}")
    logger.info(f"IO utilization: {metrics['executor']['resource_utilization']['io']:.2%}")
    
    # Shutdown the executor
    executor.shutdown()
    logger.info("Parallel Executor Demo completed")

def main():
    """Main entry point for the demo."""
    asyncio.run(run_demo())

if __name__ == "__main__":
    main()
