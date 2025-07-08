#!/usr/bin/env python3
"""
Deploy Triangulum Fix

This script copies the fixed triangulum_enhancements.py file to the Triangulum - Backtesting folder
and applies the necessary fixes to resolve the unterminated string issue.
"""

import os
import sys
import shutil
import time
from pathlib import Path

class ProgressBar:
    def __init__(self, total, description="Progress"):
        self.total = total
        self.current = 0
        self.description = description
        self.bar_length = 30
    
    def update(self, step=1, message=None):
        self.current += step
        percentage = min(100, int(100 * self.current / self.total))
        filled_length = int(self.bar_length * percentage / 100)
        bar = "█" * filled_length + "░" * (self.bar_length - filled_length)
        msg = f" | {message}" if message else ""
        sys.stdout.write(f"\r{self.description}: {percentage}% {bar}{msg}")
        sys.stdout.flush()
        
        if self.current >= self.total:
            print()

def deploy_fix():
    # Define paths
    source_dir = Path(".")
    target_dir = Path("../Triangulum - Backtesting")
    
    # Check if target directory exists
    if not target_dir.exists():
        print(f"Error: Target directory '{target_dir}' not found")
        return False
    
    # Define progress bar
    progress = ProgressBar(5, "Deploying fix")
    
    # Step 1: Check source files exist
    progress.update(1, "Checking source files")
    if not (source_dir / "triangulum_backtesting_fix.py").exists():
        print(f"\nError: Source file 'triangulum_backtesting_fix.py' not found")
        return False
    time.sleep(0.3)  # Simulate operation time
    
    # Step 2: Create backup of original file
    progress.update(1, "Creating backup")
    target_file = target_dir / "triangulum_enhancements.py"
    backup_file = target_dir / "triangulum_enhancements.py.bak"
    
    if target_file.exists():
        try:
            shutil.copy2(target_file, backup_file)
        except Exception as e:
            print(f"\nError creating backup: {e}")
            return False
    time.sleep(0.3)  # Simulate operation time
    
    # Step 3: Copy fixed file
    progress.update(1, "Copying fixed file")
    try:
        shutil.copy2(source_dir / "triangulum_backtesting_fix.py", target_dir / "triangulum_enhancements_fixed.py")
    except Exception as e:
        print(f"\nError copying fixed file: {e}")
        return False
    time.sleep(0.3)  # Simulate operation time
    
    # Step 4: Create fix script in target directory
    progress.update(1, "Creating fix application script")
    fix_script_path = target_dir / "apply_enhancements_fix.py"
    with open(fix_script_path, 'w') as f:
        f.write("""#!/usr/bin/env python3
\"\"\"
Apply the fix to triangulum_enhancements.py
\"\"\"
import os
import shutil

def apply_fix():
    print("Applying fix to triangulum_enhancements.py...")
    
    # Check if the fixed file exists
    if not os.path.exists("triangulum_enhancements_fixed.py"):
        print("Error: Fixed file 'triangulum_enhancements_fixed.py' not found")
        return False
    
    # Back up the original file if not already done
    if not os.path.exists("triangulum_enhancements.py.bak"):
        try:
            shutil.copy2("triangulum_enhancements.py", "triangulum_enhancements.py.bak")
            print("Created backup of original file")
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    # Replace the original file with the fixed version
    try:
        shutil.copy2("triangulum_enhancements_fixed.py", "triangulum_enhancements.py")
        print("Successfully applied fix!")
        return True
    except Exception as e:
        print(f"Error applying fix: {e}")
        return False

if __name__ == "__main__":
    if apply_fix():
        print("\\nThe fix has been applied successfully!")
        print("You can now run the enhanced version with: python triangulum_enhancements.py apply")
    else:
        print("\\nFailed to apply the fix. Please check the error messages above.")
""")
    time.sleep(0.3)  # Simulate operation time
    
    # Step 5: Copy fix tracker to destination
    progress.update(1, "Copying fix tracker implementations")
    
    # Create necessary directories
    os.makedirs(target_dir / "triangulum_lx" / "tooling", exist_ok=True)
    
    # Copy fix impact tracker implementation
    if (source_dir / "fix_demo_progress.py").exists():
        try:
            shutil.copy2(source_dir / "fix_demo_progress.py", target_dir / "fix_tracker_enhanced.py")
        except Exception as e:
            print(f"\nWarning: Could not copy fix tracker: {e}")
    
    # Copy fix_history.json if it exists
    if (source_dir / "fix_history.json").exists():
        try:
            shutil.copy2(source_dir / "fix_history.json", target_dir)
        except Exception as e:
            print(f"\nWarning: Could not copy fix history: {e}")
    
    # Update progress one final time
    progress.update(0, "Complete")
    
    print("\nFix deployment complete! To apply the fix in the target directory:")
    print(f"1. Navigate to '{target_dir}'")
    print("2. Run: python apply_enhancements_fix.py")
    print("\nAfter applying the fix, you can run the enhanced version with:")
    print("python triangulum_enhancements.py apply")
    
    return True

if __name__ == "__main__":
    print("Deploying Triangulum fix to 'Triangulum - Backtesting' folder...\n")
    deploy_fix()
