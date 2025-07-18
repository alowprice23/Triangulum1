
import os
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("triangulum_progress.log"),
        logging.StreamHandler()
    ]
)

class TriangulumMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.tasks = {}
        self.current_task = None
        self.total_tasks = 0
        self.completed_tasks = 0
        logging.info("Triangulum Monitor initialized")
        
    def start_task(self, task_name):
        """Start tracking a new task"""
        self.current_task = task_name
        self.tasks[task_name] = {
            "start_time": time.time(),
            "status": "running",
            "progress": 0
        }
        self.total_tasks += 1
        logging.info(f"Task started: {task_name}")
        
    def update_progress(self, task_name, progress_percentage):
        """Update the progress of a task"""
        if task_name in self.tasks:
            self.tasks[task_name]["progress"] = progress_percentage
            logging.info(f"Task progress: {task_name} - {progress_percentage}%")
            self.log_overall_progress()
        
    def complete_task(self, task_name, success=True):
        """Mark a task as completed"""
        if task_name in self.tasks:
            self.tasks[task_name]["status"] = "completed" if success else "failed"
            self.tasks[task_name]["end_time"] = time.time()
            self.tasks[task_name]["progress"] = 100 if success else self.tasks[task_name]["progress"]
            self.completed_tasks += 1
            
            duration = self.tasks[task_name]["end_time"] - self.tasks[task_name]["start_time"]
            result = "successfully" if success else "with errors"
            logging.info(f"Task completed {result}: {task_name} (Duration: {duration:.2f}s)")
            self.log_overall_progress()
    
    def log_overall_progress(self):
        """Log the overall progress of all tasks"""
        if self.total_tasks == 0:
            overall_progress = 0
        else:
            progress_sum = sum(task["progress"] for task in self.tasks.values())
            overall_progress = progress_sum / self.total_tasks
            
        elapsed_time = time.time() - self.start_time
        logging.info(f"Overall progress: {overall_progress:.2f}% ({self.completed_tasks}/{self.total_tasks} tasks) - Elapsed time: {elapsed_time:.2f}s")
    
    def add_log_entry(self, message, level="info"):
        """Add a custom log entry"""
        if level.lower() == "error":
            logging.error(message)
        elif level.lower() == "warning":
            logging.warning(message)
        else:
            logging.info(message)

# Example usage
if __name__ == "__main__":
    # This is just an example of how to use the monitor
    # In reality, this will be imported and used by Triangulum
    monitor = TriangulumMonitor()
    
    # Example task flow
    monitor.start_task("Analyzing file structure")
    monitor.update_progress("Analyzing file structure", 50)
    time.sleep(1)  # Simulate work being done
    monitor.update_progress("Analyzing file structure", 100)
    monitor.complete_task("Analyzing file structure")
    
    monitor.start_task("Fixing code issues")
    monitor.update_progress("Fixing code issues", 30)
    time.sleep(1)  # Simulate work being done
    monitor.add_log_entry("Found potential bug in file.py", "warning")
    monitor.update_progress("Fixing code issues", 75)
    time.sleep(1)  # Simulate work being done
    monitor.update_progress("Fixing code issues", 100)
    monitor.complete_task("Fixing code issues")
    
    monitor.log_overall_progress()
    logging.info("Triangulum monitoring completed")

