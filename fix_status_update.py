#!/usr/bin/env python3
"""
Fix for OrchestratorAgent class - STATUS_UPDATE issue

This script fixes the MessageType.STATUS_UPDATE reference in the OrchestratorAgent class.
In the MessageType enum, the correct value is MessageType.STATUS.
"""

import os
import sys
from pathlib import Path

def fix_message_type():
    """Fix the MessageType.STATUS_UPDATE reference in the OrchestratorAgent class."""
    
    # Path to the orchestrator_agent.py file
    file_path = Path("triangulum_lx/agents/orchestrator_agent.py")
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return False
    
    # Read the file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if the problematic line exists
    if "MessageType.STATUS_UPDATE" not in content:
        print("MessageType.STATUS_UPDATE reference not found in OrchestratorAgent")
        return True
    
    # Replace MessageType.STATUS_UPDATE with MessageType.STATUS
    new_content = content.replace("MessageType.STATUS_UPDATE", "MessageType.STATUS")
    
    # Backup the original file
    backup_path = file_path.with_suffix(".py.status.bak")
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print(f"Created backup: {backup_path}")
    
    # Write the updated content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Updated file: {file_path}")
    print("Fixed MessageType.STATUS_UPDATE reference in OrchestratorAgent class")
    
    return True

def main():
    """Main function to run the fix."""
    print("Fixing MessageType.STATUS_UPDATE reference...")
    if fix_message_type():
        print("Fix applied successfully!")
        return 0
    else:
        print("Failed to apply fix.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
