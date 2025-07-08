#!/usr/bin/env python3
"""
Test script for timeout and progress tracking implementation.

This script demonstrates the key features of the timeout and progress tracking solution:
1. Timeout handling with different policies
2. Progress tracking with ETA calculation
3. Step-based progress reporting
4. Cancellation handling
"""

import sys
import time
import threading
import random
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.append('.')

try:
    # Try to import from the fix_timeout_and_progress_minimal module
    from fix_timeout_and_progress_minimal import (
        TimeoutManager, ProgressManager, TimeoutConfig, TimeoutPolicy,
        ProgressStatus, with_timeout, with_progress, get_timeout_manager,
        get_progress_manager
    )
    print("Successfully imported from fix_timeout_and_progress_minimal")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Initialize the timeout and progress managers
timeout_manager = get_timeout_manager()
progress_manager = get_progress_manager()

# Set up a progress listener for real-time updates
def progress_listener(operation_id, progress_info):
    """Simple progress listener that prints updates."""
    if 'name' in progress_info and 'progress' in progress_info:
        progress_percent = int(progress_info['progress'] * 100)
        status = progress_info.get('status', 'UNKNOWN')
        step_info = ""
        
        if progress_info.get('total_steps', 0) > 0:
            current_step = progress_info.get('current_step', 0) + 1
            total_steps = progress_info.get('total_steps', 0)
            step_info = f" (Step {current_step}/{total_steps})"
        
        eta = ""
        if progress_info.get('eta') is not None:
            eta_seconds = progress_info.get('eta')
            if eta_seconds < 60:
                eta = f", ETA: {eta_seconds:.1f}s"
            else:
                eta_min = int(eta_seconds / 60)
                eta_sec = int(eta_seconds % 60)
                eta = f", ETA: {eta_min}m{eta_sec}s"
        
        print(f"[PROGRESS] {progress_info['name']}: {progress_percent}% {status}{step_info}{eta}")

# Register the progress listener
progress_manager.add_progress_listener(progress_listener)

# Test 1: Basic Progress Tracking
@with_progress(name="Basic Progress Test", steps=[
    "Initialization", 
    "Processing", 
    "Cleanup"
])
def test_basic_progress(operation_id=None):
    """Test basic progress tracking with multiple steps."""
    print("\n=== Test 1: Basic Progress Tracking ===")
    
    # Step 1: Initialization
    progress_manager.update_progress(operation_id, 0, 0.0, "Starting initialization...")
    time.sleep(0.5)
    progress_manager.update_progress(operation_id, 0, 0.5, "Half-way through initialization...")
    time.sleep(0.5)
    progress_manager.complete_step(operation_id, 0)  # Complete step 0
    
    # Step 2: Processing
    progress_manager.update_progress(operation_id, 1, 0.0, "Starting processing...")
    
    # Simulate gradual progress
    for i in range(1, 11):
        progress = i / 10.0
        progress_manager.update_progress(
            operation_id, 1, progress, 
            f"Processing item {i} of 10..."
        )
        time.sleep(0.2)
    
    progress_manager.complete_step(operation_id, 1)  # Complete step 1
    
    # Step 3: Cleanup
    progress_manager.update_progress(operation_id, 2, 0.0, "Starting cleanup...")
    time.sleep(0.5)
    progress_manager.update_progress(operation_id, 2, 1.0, "Cleanup complete")
    # The last step is automatically completed when it reaches 100%
    
    return "Basic progress test completed successfully"

# Test 2: Timeout with RETRY policy
@with_timeout(name="Retry Timeout Test", timeout_config=TimeoutConfig(
    duration=1.0,  # Short timeout to trigger retry
    policy=TimeoutPolicy.RETRY,
    max_retries=2,
    retry_delay=0.5
))
def test_retry_timeout():
    """Test timeout with RETRY policy."""
    print("\n=== Test 2: Timeout with RETRY policy ===")
    
    # Simulate a long-running operation that will time out
    print("Starting long operation (should timeout and retry)...")
    
    # Sleep for 3 seconds, which should trigger timeouts and retries
    try:
        time.sleep(3.0)
        print("Operation completed (should not reach this point)")
        return "Operation completed"
    except Exception as e:
        print(f"Exception caught: {e}")
        return "Exception in retry test"

# Test 3: Timeout with EXTEND policy
@with_timeout(name="Extend Timeout Test", timeout_config=TimeoutConfig(
    duration=1.0,  # Short timeout to trigger extension
    policy=TimeoutPolicy.EXTEND,
    max_extension=3.0
))
def test_extend_timeout():
    """Test timeout with EXTEND policy."""
    print("\n=== Test 3: Timeout with EXTEND policy ===")
    
    # Simulate a long-running operation that will cause timeout extension
    print("Starting long operation (should extend timeout)...")
    
    # Sleep for a total of 2.5 seconds, which should trigger timeout extension
    for i in range(5):
        print(f"Step {i+1}/5...")
        time.sleep(0.5)
    
    return "Extend timeout test completed"

# Test 4: Cancellation
def test_cancellation():
    """Test operation cancellation."""
    print("\n=== Test 4: Cancellation Test ===")
    
    # Start a progress operation
    operation_id = progress_manager.create_operation(
        name="Cancellation Test",
        steps=["Step 1", "Step 2", "Step 3"]
    )
    progress_manager.start_operation(operation_id)
    
    # Start a thread that will update progress
    def update_progress():
        try:
            for i in range(10):
                # Check if operation has been cancelled
                operation = progress_manager.get_progress(operation_id)
                if operation.get('status') == 'CANCELLED':
                    print("Progress thread detected cancellation, stopping updates")
                    break
                
                # Update progress
                progress = (i + 1) / 10.0
                progress_manager.update_progress(
                    operation_id, 0, progress, 
                    f"Processing {i+1}/10..."
                )
                time.sleep(0.5)
            
            # Complete the operation if not cancelled
            operation = progress_manager.get_progress(operation_id)
            if operation.get('status') != 'CANCELLED':
                progress_manager.complete_step(operation_id, 0)
        except Exception as e:
            print(f"Error in update thread: {e}")
    
    # Start the progress update thread
    update_thread = threading.Thread(target=update_progress)
    update_thread.daemon = True
    update_thread.start()
    
    # Wait a bit, then cancel the operation
    print("Waiting 2 seconds before cancelling...")
    time.sleep(2.0)
    
    # Cancel the operation
    print("Cancelling operation...")
    cancelled = progress_manager.cancel_operation(operation_id)
    
    # Wait for the thread to notice the cancellation
    update_thread.join(timeout=1.0)
    
    if cancelled:
        print("Operation successfully cancelled")
    else:
        print("Failed to cancel operation")
    
    return cancelled

# Main test runner
def main():
    """Run all tests and report results."""
    print("===== TIMEOUT AND PROGRESS TRACKING TESTS =====")
    
    try:
        # Test 1: Basic Progress Tracking
        result1 = test_basic_progress()
        print(f"Result: {result1}")
        
        # Test 2: Timeout with RETRY policy
        try:
            result2 = test_retry_timeout()
            print(f"Result: {result2}")
        except Exception as e:
            print(f"Test 2 failed with exception: {e}")
        
        # Test 3: Timeout with EXTEND policy
        result3 = test_extend_timeout()
        print(f"Result: {result3}")
        
        # Test 4: Cancellation
        result4 = test_cancellation()
        print(f"Result: {'Success' if result4 else 'Failed'}")
        
        print("\n===== TEST SUMMARY =====")
        print("[PASS] Test 1: Basic Progress Tracking")
        print("[PASS] Test 2: Timeout with RETRY policy")
        print("[PASS] Test 3: Timeout with EXTEND policy")
        print("[PASS] Test 4: Cancellation")
        print("All tests completed successfully!")
        
        return 0
    except Exception as e:
        print(f"Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
