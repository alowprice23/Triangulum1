# Simple demonstration of a fix tracker for Triangulum

class FixImpactTracker:
    def __init__(self, project_path):
        self.project_path = project_path
        self.fixes = []
        
    def track_fix(self, file_path, original_content, fixed_content):
        """Track a fix that was applied to a file"""
        self.fixes.append({
            "file_path": file_path,
            "original_length": len(original_content) if original_content else 0,
            "fixed_length": len(fixed_content) if fixed_content else 0,
            "changed": original_content != fixed_content
        })
        print(f"Tracked fix for {file_path}")
        return True

if __name__ == "__main__":
    print("Running fix impact tracker demo")
    tracker = FixImpactTracker("/path/to/project")
    tracker.track_fix(
        "example.py", 
        "def add(a, b):\n    return a - b  # Bug", 
        "def add(a, b):\n    return a + b  # Fixed"
    )
    print(f"Fixes tracked: {len(tracker.fixes)}")
    for fix in tracker.fixes:
        print(f"File: {fix['file_path']}, Changed: {fix['changed']}")
