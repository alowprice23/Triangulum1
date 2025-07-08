# Enhanced demonstration of a fix tracker for Triangulum

import json
import os
import datetime
from difflib import unified_diff

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
        """Save fix history to disk"""
        try:
            with open(self.fix_history_file, 'w') as f:
                json.dump(self.fixes, f, indent=2)
            print(f"Saved {len(self.fixes)} fixes to history")
            return True
        except Exception as e:
            print(f"Error saving fix history: {e}")
            return False
        
    def track_fix(self, file_path, original_content, fixed_content):
        """Track a fix that was applied to a file with detailed metrics"""
        # Calculate diff metrics
        diff_lines = list(unified_diff(
            original_content.splitlines(),
            fixed_content.splitlines(),
            lineterm=''
        ))
        
        lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        
        # Create fix record
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
        print(f"Tracked fix for {file_path} (+{lines_added}/-{lines_removed} lines)")
        self._save_history()
        return fix_record
    
    def generate_report(self):
        """Generate a simple report of fixes"""
        if not self.fixes:
            return "No fixes tracked yet."
            
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
        
        # Add the 5 most recent fixes to the report
        for fix in self.fixes[-5:]:
            report.append(f"\nFile: {fix['file_path']}")
            report.append(f"Time: {fix['timestamp']}")
            report.append(f"Changes: +{fix['lines_added']}/-{fix['lines_removed']} lines")
            report.append(f"Diff preview:\n{fix['diff_summary']}")
            report.append("-" * 40)
            
        return "\n".join(report)

# Example usage
if __name__ == "__main__":
    print("Running enhanced fix impact tracker demo")
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
