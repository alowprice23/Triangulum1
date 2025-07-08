#!/usr/bin/env python3
"""
Triangulum Monitoring Runner

This script integrates with Triangulum to provide non-invasive progress tracking and logging.
It lets Triangulum operate normally while monitoring and logging its activities.
"""

import os
import sys
import time
import logging
import importlib.util
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("triangulum_monitoring.log"),
        logging.StreamHandler()
    ]
)

class ProgressMonitor:
    """Monitor progress of Triangulum operations"""
    
    def __init__(self):
        self.start_time = time.time()
        self.total_steps = 0
        self.completed_steps = 0
        self.current_step = None
        logging.info("Progress Monitor initialized")
        
    def log_progress(self, message, percent=None):
        """Log a progress message with optional percentage"""
        elapsed = time.time() - self.start_time
        progress_msg = f"[{elapsed:.1f}s] {message}"
        
        if percent is not None:
            progress_msg += f" ({percent:.1f}%)"
            
        logging.info(progress_msg)
        print(progress_msg)
    
    def start_step(self, step_name):
        """Start a new step in the process"""
        self.total_steps += 1
        self.current_step = step_name
        self.log_progress(f"Starting step: {step_name}", 
                         (self.completed_steps / max(1, self.total_steps)) * 100)
    
    def complete_step(self, step_name, success=True):
        """Mark a step as completed"""
        self.completed_steps += 1
        status = "? Success" if success else "? Failed"
        self.log_progress(f"Completed step: {step_name} - {status}", 
                         (self.completed_steps / max(1, self.total_steps)) * 100)

def run_triangulum(module_name, function_name="main", *args, **kwargs):
    """
    Run a Triangulum module function with progress monitoring
    
    Args:
        module_name: Name of the Triangulum module to run
        function_name: Name of the function to call in the module
        *args, **kwargs: Arguments to pass to the function
    """
    monitor = ProgressMonitor()
    monitor.log_progress(f"Starting Triangulum: {module_name}.{function_name}")
    
    try:
        # Import the Triangulum module
        monitor.start_step("Importing module")
        try:
            # Try to import as module path
            module = importlib.import_module(module_name)
        except ImportError:
            # Try to load from file path
            if os.path.exists(module_name):
                spec = importlib.util.spec_from_file_location("triangulum_module", module_name)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                raise ImportError(f"Could not import {module_name}")
                
        monitor.complete_step("Importing module")
        
        # Get the function to call
        monitor.start_step(f"Locating function: {function_name}")
        if not hasattr(module, function_name):
            monitor.complete_step(f"Locating function: {function_name}", False)
            monitor.log_progress(f"ERROR: Function {function_name} not found in {module_name}")
            return False
            
        function = getattr(module, function_name)
        monitor.complete_step(f"Locating function: {function_name}")
        
        # Run the function
        monitor.start_step(f"Running: {function_name}")
        try:
            result = function(*args, **kwargs)
            monitor.complete_step(f"Running: {function_name}")
            
            # Log completion
            total_time = time.time() - monitor.start_time
            percent_complete = 100.0
            monitor.log_progress(f"Triangulum execution completed successfully in {total_time:.2f}s", percent_complete)
            
            return result
        except Exception as e:
            monitor.complete_step(f"Running: {function_name}", False)
            monitor.log_progress(f"ERROR in {function_name}: {str(e)}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        monitor.log_progress(f"ERROR: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python run_triangulum_with_monitoring.py <module_name> [function_name=main]")
        print("Example: python run_triangulum_with_monitoring.py triangulum_folder_healer main")
        sys.exit(1)
        
    # Get module name
    module_name = sys.argv[1]
    
    # Get function name (default to main)
    function_name = "main"
    if len(sys.argv) >= 3:
        function_name = sys.argv[2]
        
    # Run Triangulum with monitoring
    result = run_triangulum(module_name, function_name)
    
    # Exit with appropriate code
    sys.exit(0 if result else 1)

