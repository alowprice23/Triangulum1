#!/usr/bin/env python3
"""
Fix for MessageBus class - register_handler method

This script adds a register_handler method to the MessageBus class to make it
compatible with the OrchestratorAgent which expects this method.
"""

import os
import sys
from pathlib import Path

def fix_message_bus():
    """Add a register_handler method to the MessageBus class."""
    
    # Path to the message_bus.py file
    file_path = Path("triangulum_lx/agents/message_bus.py")
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return False
    
    # Read the file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if the method already exists
    if "def register_handler" in content:
        print("register_handler method already exists in MessageBus")
        return True
    
    # Find the position to insert the new method
    # Insert after the clear_conversation method
    insertion_point = content.rfind("    def clear_conversation(self, conversation_id: str) -> None:")
    
    if insertion_point == -1:
        print("Error: Could not find insertion point")
        return False
    
    # Find the end of the clear_conversation method
    end_of_method = content.find("\n\n", insertion_point)
    if end_of_method == -1:
        end_of_method = len(content)
    
    # Create the register_handler method
    new_method = """
    
    def register_handler(self, 
                         handler_id: str, 
                         message_type: MessageType, 
                         callback: Callable[[AgentMessage], None]) -> None:
        \"\"\"
        Register a handler for a specific message type.
        
        This is a compatibility method for the OrchestratorAgent.
        It maps to the subscribe method with a specific message type.
        
        Args:
            handler_id: ID of the handler (agent)
            message_type: Type of message to handle
            callback: Function to call when a message is received
        \"\"\"
        # Simply map to subscribe with a single message type
        self.subscribe(
            agent_id=handler_id,
            callback=callback,
            message_types=[message_type]
        )
        logger.debug(f"Registered handler {handler_id} for message type {message_type}")"""
    
    # Insert the new method
    new_content = content[:end_of_method] + new_method + content[end_of_method:]
    
    # Backup the original file
    backup_path = file_path.with_suffix(".py.handler.bak")
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print(f"Created backup: {backup_path}")
    
    # Write the updated content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Updated file: {file_path}")
    print("Added register_handler method to MessageBus class")
    
    return True

def main():
    """Main function to run the fix."""
    print("Adding register_handler method to MessageBus class...")
    if fix_message_bus():
        print("Fix applied successfully!")
        return 0
    else:
        print("Failed to apply fix.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
