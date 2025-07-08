#!/usr/bin/env python3
"""
Triangulum Folder Healer Wrapper

This script provides a wrapper for running triangulum_folder_healer.py with monitoring
while ensuring proper argument handling.
"""

import sys
import importlib
import time
import logging
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
        status = "Success" if success else "Failed"
        self.log_progress(f"Completed step: {step_name} - {status}", 
                         (self.completed_steps / max(1, self.total_steps)) * 100)

def main():
    """Main function to run the folder healer with monitoring."""
    # Check if we have at least one argument (the folder path)
    if len(sys.argv) < 2:
        print("Usage: python run_triangulum_folder_healer.py <folder_path> [options]")
        print("Example: python run_triangulum_folder_healer.py ./example_files --dry-run")
        sys.exit(1)
    
    # Set up the progress monitor
    monitor = ProgressMonitor()
    monitor.log_progress("Starting Triangulum Folder Healer with monitoring")
    
    try:
        # Import the triangulum_folder_healer module
        monitor.start_step("Importing module")
        try:
            import triangulum_folder_healer
            monitor.complete_step("Importing module")
        except ImportError as e:
            monitor.complete_step("Importing module", False)
            monitor.log_progress(f"ERROR: Could not import triangulum_folder_healer: {str(e)}")
            sys.exit(1)
        
        # Prepare arguments for triangulum_folder_healer.main()
        monitor.start_step("Preparing arguments")
        # Save the original argv
        original_argv = sys.argv.copy()
        
        # Replace sys.argv with the arguments for triangulum_folder_healer
        # Format: triangulum_folder_healer.py <folder_path> [options]
        sys.argv = ['triangulum_folder_healer.py'] + sys.argv[1:]
        monitor.complete_step("Preparing arguments")
    
        # Execute triangulum_folder_healer.main()
        monitor.start_step("Running main function")
        try:
            # Print the arguments being passed
            monitor.log_progress(f"Running with arguments: {' '.join(sys.argv[1:])}")
            
            # Call the main function
            result = triangulum_folder_healer.main()
            
            monitor.complete_step("Running main function")
            
            # Log completion
            total_time = time.time() - monitor.start_time
            monitor.log_progress(f"Triangulum Folder Healer completed in {total_time:.2f}s", 100.0)
            
            # Restore original argv
            sys.argv = original_argv
            
            return result
        except Exception as e:
            monitor.complete_step("Running main function", False)
            monitor.log_progress(f"ERROR in main function: {str(e)}")
            traceback.print_exc()
            
            # Restore original argv
            sys.argv = original_argv
            
            sys.exit(1)
            
    except KeyboardInterrupt:
        monitor.log_progress("Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        monitor.log_progress(f"ERROR: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
