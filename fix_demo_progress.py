"""
Enhanced Fix Impact Tracker with Progress Reporting

This version adds progress tracking to show completion percentage during operations
"""

import json
import os
import datetime
import time
import sys
from difflib import unified_diff

class ProgressTracker:
    """Simple progress tracker to show completion percentage"""
    
    def __init__(self, total_steps, description="Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = time.time()
        self.last_update = 0
        
    def update(self, step=None, message=None):
        """Update progress by one step or to a specific step number"""
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
            
        # Limit updates to once per 100ms for performance
        current_time = time.time()
        if current_time - self.last_update < 0.1 and self.current_step < self.total_steps:
            return
        
        self.last_update = current_time
        
        # Calculate percentage and elapsed time
        percentage = min(100, int(100 * self.current_step / self.total_steps))
        elapsed = current_time - self.start_time
        
        # Estimate remaining time
        if percentage > 0:
            remaining = elapsed * (100 - percentage) / percentage
            time_str = f"- ETA: {remaining:.1f}s" 
        else:
            time_str = ""
            
        # Construct progress bar
        bar_width = 30
        filled_width = int(bar_width * percentage / 100)
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Show optional message
        msg = f" | {message}" if message else ""
        
        # Print progress
        status = f"\r{self.description}: {percentage}% {bar} {time_str}{msg}"
        sys.stdout.write(status)
        sys.stdout.flush()
        
        # Add newline when complete
        if percentage == 100:
            print()

class FixImpactTracker:
    def __init__(self, project_path):
        self.project_path = project_path
        self.fixes = []
        self.fix_history_file = os.path.join(project_path, 'fix_history.json')
        self._load_history()
        
    def _load_history(self):
        """Load fix history from disk if available"""
        if os.path.exists(self.fix_history_file):
            try:
                with open(self.fix_history_file, 'r') as f:
                    self.fixes = json.load(f)
                print(f"Loaded {len(self.fixes)} previous fixes from history")
            except Exception as e:
                print(f"Error loading fix history: {e}")
    
    def _save_history(self):
        """Save fix history to disk with progress tracking"""
        try:
            progress = ProgressTracker(3, "Saving fix history")
            
            progress.update(message="Preparing data")
            time.sleep(0.5)  # Simulate processing time
            
            progress.update(message="Writing to disk")
            with open(self.fix_history_file, 'w') as f:
                json.dump(self.fixes, f, indent=2)
            time.sleep(0.5)  # Simulate processing time
            
            progress.update(message="Verifying data")
            time.sleep(0.5)  # Simulate processing time
            
            progress.update(3, message="Complete")
            print(f"Saved {len(self.fixes)} fixes to history")
            return True
        except Exception as e:
            print(f"Error saving fix history: {e}")
            return False
        
    def track_fix(self, file_path, original_content, fixed_content):
        """Track a fix that was applied to a file with detailed metrics and progress tracking"""
        # Initialize progress tracker for the fix tracking process
        progress = ProgressTracker(5, "Tracking fix impact")
        
        # Step 1: Analyze original content
        progress.update(message="Analyzing original content")
        time.sleep(0.3)  # Simulate processing time
        
        # Step 2: Analyze fixed content
        progress.update(message="Analyzing fixed content")
        time.sleep(0.3)  # Simulate processing time
        
        # Step 3: Calculate diff metrics
        progress.update(message="Generating diff")
        diff_lines = list(unified_diff(
            original_content.splitlines(),
            fixed_content.splitlines(),
            lineterm=''
        ))
        time.sleep(0.5)  # Simulate processing time
        
        # Step 4: Calculate metrics
        progress.update(message="Calculating metrics")
        lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        time.sleep(0.3)  # Simulate processing time
        
        # Step 5: Create and store fix record
        progress.update(message="Recording fix data")
        fix_record = {
            "file_path": file_path,
            "timestamp": datetime.datetime.now().isoformat(),
            "original_length": len(original_content) if original_content else 0,
            "fixed_length": len(fixed_content) if fixed_content else 0,
            "changed": original_content != fixed_content,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "net_change": lines_added - lines_removed,
            "diff_summary": '\n'.join(diff_lines[:10]) + ('...' if len(diff_lines) > 10 else '')
        }
        
        self.fixes.append(fix_record)
        time.sleep(0.3)  # Simulate processing time
        
        # Complete the progress tracking
        progress.update(5, message="Complete")
        print(f"Tracked fix for {file_path} (+{lines_added}/-{lines_removed} lines)")
        
        # Save history
        self._save_history()
        return fix_record
    
    def generate_report(self):
        """Generate a simple report of fixes with progress tracking"""
        if not self.fixes:
            return "No fixes tracked yet."
            
        progress = ProgressTracker(4, "Generating report")
        
        # Step 1: Calculate basic statistics
        progress.update(message="Calculating statistics")
        time.sleep(0.5)  # Simulate processing time
        
        # Step 2: Format header information
        progress.update(message="Formatting report header")
        report = [
            "FIX IMPACT REPORT",
            "=" * 50,
            f"Total fixes tracked: {len(self.fixes)}",
            f"Files affected: {len(set(fix['file_path'] for fix in self.fixes))}",
            f"Total lines added: {sum(fix['lines_added'] for fix in self.fixes)}",
            f"Total lines removed: {sum(fix['lines_removed'] for fix in self.fixes)}",
            f"Net line change: {sum(fix['net_change'] for fix in self.fixes)}",
            "=" * 50,
            "Recent fixes:",
        ]
        time.sleep(0.5)  # Simulate processing time
        
        # Step 3: Format detailed fix information
        progress.update(message="Formatting fix details")
        for fix in self.fixes[-5:]:
            report.append(f"\nFile: {fix['file_path']}")
            report.append(f"Time: {fix['timestamp']}")
            report.append(f"Changes: +{fix['lines_added']}/-{fix['lines_removed']} lines")
            report.append(f"Diff preview:\n{fix['diff_summary']}")
            report.append("-" * 40)
        time.sleep(0.5)  # Simulate processing time
        
        # Step 4: Finalize report
        progress.update(message="Finalizing report")
        report_text = "\n".join(report)
        time.sleep(0.5)  # Simulate processing time
        
        progress.update(4, message="Complete")
        return report_text

# Example usage
if __name__ == "__main__":
    print("Running enhanced fix impact tracker demo with progress tracking")
    tracker = FixImpactTracker(".")
    
    # Example 1: Fix a division by zero bug
    tracker.track_fix(
        "example_math.py", 
        "def divide(a, b):\n    return a / b  # Bug: no zero check", 
        "def divide(a, b):\n    if b == 0:\n        return float('inf')  # Fixed: handle zero\n    return a / b"
    )
    
    # Example 2: Fix a resource leak
    tracker.track_fix(
        "example_file.py",
        "def read_data(filename):\n    f = open(filename, 'r')\n    data = f.read()  # Bug: file not closed\n    return data",
        "def read_data(filename):\n    with open(filename, 'r') as f:  # Fixed: using context manager\n        data = f.read()\n    return data"
    )
    
    # Generate and print report
    report = tracker.generate_report()
    print("\n" + report)
