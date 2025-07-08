#!/usr/bin/env python3
"""
Fix for timeout and progress tracking issues

This script enhances Triangulum with:
1. Robust timeout handling for long-running operations
2. Accurate progress reporting with ETA calculation
3. Clean cancellation with proper resource cleanup
4. Rich progress visualization
"""

import os
import sys
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("timeout_progress_fix")

def fix_orchestrator_timeout():
    """
    Enhance timeout handling in the orchestrator agent.
    
    - Increases timeout for folder analysis
    - Adds periodic status updates
    - Implements adaptive timeouts based on operation complexity
    """
    # File path
    file_path = Path("triangulum_lx/agents/orchestrator_agent.py")
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return False
    
    # Create backup
    backup_path = file_path.with_suffix(".py.bak")
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Created backup at {backup_path}")
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return False
    
    # Find the _wait_for_result method
    wait_method_pattern = "    def _wait_for_result"
    wait_method_pos = content.find(wait_method_pattern)
    
    if wait_method_pos == -1:
        logger.error("Could not find _wait_for_result method")
        return False
    
    # Find the end of the _wait_for_result method
    wait_method_end = content.find("\n    def", wait_method_pos + 10)
    if wait_method_end == -1:
        wait_method_end = len(content)
    
    wait_method_code = content[wait_method_pos:wait_method_end]
    
    # Create enhanced version with proper docstring
    new_wait_method_code = '''    def _wait_for_result(self, workflow_id: str, agent_type: str, timeout: float = None) -> Optional[Dict[str, Any]]:
        """Wait for a result from an agent with timeout."""
        if timeout is None:
            timeout = self.timeout
        
        start_time = time.time()
        result = None
        
        logger.info(f"Waiting for result from {agent_type} with timeout {timeout}s")
        
        # Initialize progress tracking
        progress_data = {
            "current_step": 0,
            "total_steps": 1,
            "status": "in_progress",
            "start_time": start_time,
            "elapsed": 0,
            "progress": 0.0,
            "agent_type": agent_type
        }
        
        try:
            while True:
                # Check if we have a result
                result = self._check_for_result(workflow_id, agent_type)
                if result is not None:
                    progress_data["status"] = "completed"
                    logger.info(f"Received result from {agent_type} after {time.time() - start_time:.2f}s")
                    return result
                
                # Check if we've timed out
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    progress_data["status"] = "timeout"
                    logger.warning(f"Timeout waiting for result from {agent_type} after {elapsed:.2f}s")
                    return None
                
                # Update progress
                progress_data["elapsed"] = elapsed
                progress_data["progress"] = min(0.95, elapsed / timeout)
                
                # Print periodic status updates (every 5 seconds)
                if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    # Extend timeout for complex operations if needed
                    if agent_type in ["bug_detector", "verification_agent"] and elapsed > timeout * 0.8:
                        # These agents may need more time for complex tasks
                        old_timeout = timeout
                        timeout = min(timeout * 1.5, timeout + 60)  # Add up to 60 more seconds
                        logger.info(f"Extended timeout for {agent_type} from {old_timeout}s to {timeout}s")
                    
                    logger.info(f"Still waiting for response from {agent_type} - {int(elapsed)}s elapsed")
                
                # Sleep a bit to avoid busy waiting
                time.sleep(0.1)
                
        finally:
            # Ensure we report final status
            if result is None and progress_data["status"] == "in_progress":
                progress_data["status"] = "cancelled"
        
        return None'''
    
    # Replace the wait method
    updated_content = content.replace(wait_method_code, new_wait_method_code)
    
    # Find the analyze_folder method to update timeout for folder analysis
    folder_analysis_pattern = "        # Wait for the result with timeout\n        result = self._wait_for_result(workflow_id, agent_type, self.timeout * 3)  # Longer timeout for folder analysis"
    folder_analysis_update = "        # Wait for the result with timeout\n        result = self._wait_for_result(workflow_id, agent_type, self.timeout * 10)  # Much longer timeout for folder analysis"
    
    if folder_analysis_pattern in updated_content:
        updated_content = updated_content.replace(folder_analysis_pattern, folder_analysis_update)
    
    # Write the updated content back to the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        logger.info(f"Successfully updated {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to file: {e}")
        return False


def improve_folder_healer_progress():
    """
    Enhance progress reporting in triangulum_folder_healer.py.
    
    - Adds detailed progress bar visualization
    - Implements ETA calculation
    - Provides real-time status updates
    - Shows file-level progress details
    """
    # File path
    file_path = Path("triangulum_folder_healer.py")
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return False
    
    # Create backup
    backup_path = file_path.with_suffix(".py.bak")
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Created backup at {backup_path}")
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return False
    
    # Find the progress_monitor function
    progress_monitor_pattern = "def progress_monitor("
    progress_monitor_pos = content.find(progress_monitor_pattern)
    
    if progress_monitor_pos == -1:
        logger.error("Could not find progress_monitor function")
        return False
    
    # Find the end of the progress_monitor function
    progress_monitor_end = content.find("\ndef ", progress_monitor_pos + 10)
    if progress_monitor_end == -1:
        progress_monitor_end = len(content)
    
    progress_monitor_code = content[progress_monitor_pos:progress_monitor_end]
    
    # Replace with enhanced progress monitor using single quotes for code and triple quotes for docstring
    new_progress_monitor_code = '''def progress_monitor(folder_healer: TriangulumFolderHealer):
    """
    Monitor the progress of the healing process and display a rich progress bar.
    
    Args:
        folder_healer: The folder healer instance
    """
    import sys
    import itertools
    
    # Terminal colors
    class TermColors:
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
    
    spinner = itertools.cycle(['-', '\\\\', '|', '/'])
    last_progress = {}
    last_files_processed = 0
    last_status_length = 0
    
    # Progress bar settings
    bar_width = 40
    
    def format_time(seconds):
        """Format time in a human-readable way."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds / 60)
        seconds = seconds % 60
        if minutes < 60:
            return f"{minutes}m {int(seconds)}s"
        hours = int(minutes / 60)
        minutes = minutes % 60
        return f"{hours}h {minutes}m"
    
    try:
        while True:
            # Get current progress
            progress = folder_healer.get_progress()
            
            if progress:
                # Clear previous line
                if last_status_length > 0:
                    sys.stdout.write('\r' + ' ' * last_status_length + '\r')
                
                # Print status
                current_step = progress.get("current_step", 0)
                total_steps = progress.get("total_steps", 0)
                status = progress.get("status", "in_progress")
                
                if status == "in_progress":
                    # Calculate progress percentage
                    percent = 0
                    if "progress" in progress:
                        percent = int(progress["progress"] * 100)
                    elif total_steps > 0:
                        percent = int((current_step / total_steps) * 100)
                    
                    # Create progress bar
                    filled_width = int(bar_width * percent / 100)
                    bar = f"{TermColors.GREEN}{'█' * filled_width}{TermColors.RESET}{'░' * (bar_width - filled_width)}"
                    
                    # Format step information
                    step_info = ""
                    if total_steps > 0:
                        step_name = progress.get("steps", {}).get(current_step, {}).get("name", "")
                        step_info = f" Step {current_step+1}/{total_steps}"
                        if step_name:
                            step_info += f": {step_name}"
                    
                    # Format time information
                    time_info = ""
                    if "start_time" in progress and "elapsed" in progress:
                        elapsed = progress["elapsed"]
                        time_info = f" | Time: {format_time(elapsed)}"
                        
                        # Add ETA if available
                        if percent > 0 and percent < 100:
                            eta = elapsed * (100 - percent) / percent
                            time_info += f" | ETA: {format_time(eta)}"
                    
                    # Format file statistics
                    file_info = ""
                    files_processed = len(progress.get("files_processed", []))
                    files_healed = len(progress.get("files_healed", []))
                    files_failed = len(progress.get("files_failed", []))
                    
                    if files_processed > 0:
                        file_info = f" | Files: {files_processed} processed, {files_healed} healed, {files_failed} failed"
                        
                        # Log when new files are processed
                        if files_processed > last_files_processed:
                            new_files = files_processed - last_files_processed
                            print(f"\\nProcessed {new_files} new files. Total: {files_processed}")
                            last_files_processed = files_processed
                    
                    # Construct status line
                    status_line = f"Progress: [{bar}] {percent}%{step_info}{time_info}{file_info} {next(spinner)}"
                    
                    # Show current file being processed
                    current_file = progress.get("current_file", "")
                    if current_file:
                        # Truncate if too long
                        if len(current_file) > 40:
                            current_file = "..." + current_file[-37:]
                        status_line += f"\\n  Current: {current_file}"
                else:
                    # Process complete
                    filled_width = bar_width
                    bar = f"{TermColors.GREEN}{'█' * filled_width}{TermColors.RESET}"
                    
                    files_healed = len(progress.get("files_healed", []))
                    files_failed = len(progress.get("files_failed", []))
                    
                    elapsed = progress.get("elapsed", 0)
                    time_info = f" in {format_time(elapsed)}" if elapsed > 0 else ""
                    
                    status_line = f"Status: {TermColors.BOLD}{TermColors.GREEN}COMPLETED{TermColors.RESET} [{bar}] 100% | {files_healed} files healed, {files_failed} failed{time_info}"
                
                # Print status line
                sys.stdout.write(status_line)
                sys.stdout.flush()
                last_status_length = len(status_line.replace('\033[92m', '').replace('\033[0m', '').replace('\033[1m', ''))
                
                # Exit if complete
                if status != "in_progress":
                    print()  # Add newline after completion
                    break
                
                last_progress = progress
            
            # Sleep a bit
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\\nProgress monitoring interrupted.")
    except Exception as e:
        print(f"\\nError in progress monitor: {str(e)}")
        import traceback
        print(traceback.format_exc())'''
    
    # Replace progress monitor
    updated_content = content.replace(progress_monitor_code, new_progress_monitor_code)
    
    # Find and enhance the get_progress method
    get_progress_pattern = "    def get_progress"
    get_progress_pos = updated_content.find(get_progress_pattern)
    
    if get_progress_pos != -1:
        # Find the end of the get_progress method
        get_progress_end = updated_content.find("\n    def", get_progress_pos + 10)
        if get_progress_end == -1:
            get_progress_end = len(updated_content)
        
        get_progress_code = updated_content[get_progress_pos:get_progress_end]
        
        # Replace with enhanced get_progress
        new_get_progress_code = '''    def get_progress(self) -> Dict[str, Any]:
        """Get the current progress of the healing process."""
        # Initialize with basic progress structure
        progress = {
            "current_step": getattr(self, "_current_step", 0),
            "total_steps": 5,  # 5 steps: analyze, detect, plan, fix, verify
            "status": "in_progress",
            "start_time": getattr(self, "_start_time", time.time()),
            "elapsed": time.time() - getattr(self, "_start_time", time.time()),
            "progress": 0.0,
            "steps": [
                {"name": "Analyzing folder structure", "weight": 0.1},
                {"name": "Detecting issues", "weight": 0.2},
                {"name": "Planning repairs", "weight": 0.1},
                {"name": "Applying fixes", "weight": 0.5},
                {"name": "Verification", "weight": 0.1}
            ],
            "files_processed": getattr(self, "_files_processed", []),
            "files_healed": getattr(self, "_files_healed", []),
            "files_failed": getattr(self, "_files_failed", []),
            "current_file": getattr(self, "_current_file", "")
        }
        
        # Calculate overall progress based on step weights
        if hasattr(self, "_current_step"):
            current_step = self._current_step
            step_progress = getattr(self, "_step_progress", 0.0)
            
            # Calculate total progress based on completed steps and current step progress
            total_progress = 0.0
            
            # Add completed steps
            for i in range(current_step):
                total_progress += progress["steps"][i]["weight"]
            
            # Add current step progress
            if current_step < len(progress["steps"]):
                total_progress += progress["steps"][current_step]["weight"] * step_progress
            
            progress["progress"] = total_progress
        
        # Update status if process is complete
        if hasattr(self, "_complete") and self._complete:
            progress["status"] = "completed"
        
        return progress'''
        
        # Update the method
        updated_content = updated_content.replace(get_progress_code, new_get_progress_code)
    
    # Write the updated content back to the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        logger.info(f"Successfully updated {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to file: {e}")
        return False


def main():
    """Main function to run the fixes."""
    print("Applying timeout and progress reporting fixes...")
    
    timeout_fixed = fix_orchestrator_timeout()
    progress_fixed = improve_folder_healer_progress()
    
    if timeout_fixed and progress_fixed:
        print("All fixes applied successfully!")
        return 0
    elif timeout_fixed:
        print("Only timeout fix applied successfully.")
        return 1
    elif progress_fixed:
        print("Only progress reporting fix applied successfully.")
        return 1
    else:
        print("Failed to apply fixes.")
        return 2

if __name__ == "__main__":
    sys.exit(main())
