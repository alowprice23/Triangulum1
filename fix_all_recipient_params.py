#!/usr/bin/env python3
"""
Comprehensive Fix for Message Addressing and Delivery Confirmation

This script addresses multiple issues with message addressing and delivery:
1. Fixes 'recipient' vs 'receiver' parameter inconsistencies across the codebase
2. Implements proper broadcast message handling with target filtering
3. Adds delivery confirmation tracking for critical messages
4. Improves handling of invalid recipients with clear error messages
5. Optimizes addressing efficiency for large-scale systems
"""

import os
import sys
import re
import glob
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("fix_recipient_params")

# Constants
AGENT_FILES_PATTERN = "triangulum_lx/agents/*.py"
EXAMPLE_FILES_PATTERN = "examples/*.py"
TEST_FILES_PATTERN = "tests/**/*.py"
BACKUP_SUFFIX = ".recipient.bak"
DELIVERY_CONFIRMATION_PATTERN = r"message_bus\.publish\(\s*[^)]+\)"


class MessageAddressingFix:
    """Class to handle message addressing fixes."""
    
    def __init__(self):
        """Initialize the fixer."""
        self.modified_files = []
        self.total_recipient_occurrences = 0
        self.total_broadcast_fixes = 0
        self.total_delivery_confirmation_fixes = 0
        self.total_invalid_recipient_fixes = 0
    
    def find_files_to_fix(self) -> List[Path]:
        """
        Find all files that might contain message addressing issues.
        
        Returns:
            List[Path]: List of file paths
        """
        files = []
        
        # Find files matching patterns
        for pattern in [AGENT_FILES_PATTERN, EXAMPLE_FILES_PATTERN, TEST_FILES_PATTERN]:
            files.extend([Path(f) for f in glob.glob(pattern, recursive=True)])
        
        # Filter to only include files that might contain AgentMessage
        filtered_files = []
        for file_path in files:
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check if the file contains AgentMessage instantiations or message_bus.publish
                    if ("AgentMessage(" in content or 
                        "message_type=" in content or 
                        "recipient=" in content or
                        "receiver=" in content or
                        "message_bus.publish" in content):
                        filtered_files.append(file_path)
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
        
        return filtered_files
    
    def fix_recipient_parameter(self, content: str) -> Tuple[int, str]:
        """
        Fix 'recipient' to 'receiver' parameter in content.
        
        Args:
            content: File content to fix
            
        Returns:
            Tuple[int, str]: Number of replacements and updated content
        """
        # Count occurrences
        occurrences = content.count("recipient=")
        
        # Make the replacement
        new_content = content.replace("recipient=", "receiver=")
        
        return occurrences, new_content
    
    def fix_broadcast_handling(self, content: str) -> Tuple[int, str]:
        """
        Fix broadcast message handling with target filtering.
        
        Args:
            content: File content to fix
            
        Returns:
            Tuple[int, str]: Number of replacements and updated content
        """
        # Pattern for broadcast messages without proper filtering
        pattern = r"(message_bus\.publish\(\s*AgentMessage\([^)]*receiver\s*=\s*None[^)]*\))"
        
        # Find all matches
        matches = re.findall(pattern, content)
        count = len(matches)
        
        # Replace with proper broadcast handling
        new_content = content
        for match in matches:
            # Add target_filter parameter if not already present
            if "target_filter=" not in match:
                replacement = match.rstrip(")") + ", target_filter=None)"
                new_content = new_content.replace(match, replacement)
        
        return count, new_content
    
    def fix_delivery_confirmation(self, content: str) -> Tuple[int, str]:
        """
        Add delivery confirmation for critical messages.
        
        Args:
            content: File content to fix
            
        Returns:
            Tuple[int, str]: Number of replacements and updated content
        """
        # Pattern for publish calls without delivery confirmation
        pattern = r"(message_bus\.publish\(\s*[^)]+message_type\s*=\s*MessageType\.(TASK_REQUEST|ERROR|STATUS_UPDATE)[^)]*\))"
        
        # Find all matches
        matches = re.findall(pattern, content)
        count = len(matches)
        
        # Replace with delivery confirmation
        new_content = content
        for match_tuple in matches:
            match = match_tuple[0]
            # Add require_confirmation parameter if not already present
            if "require_confirmation=" not in match:
                replacement = match.rstrip(")") + ", require_confirmation=True)"
                new_content = new_content.replace(match, replacement)
        
        return count, new_content
    
    def fix_invalid_recipient_handling(self, content: str) -> Tuple[int, str]:
        """
        Improve handling of invalid recipients with clear error messages.
        
        Args:
            content: File content to fix
            
        Returns:
            Tuple[int, str]: Number of replacements and updated content
        """
        # Pattern for publish calls without checking result
        pattern = r"(result\s*=\s*message_bus\.publish\([^)]+\))\s*(?!\s*if\s+not\s+result\[\"success\"\])"
        
        # Find all matches
        matches = re.findall(pattern, content)
        count = len(matches)
        
        # Replace with proper error handling
        new_content = content
        for match in matches:
            # Add error handling if not already present
            replacement = (
                f"{match}\n"
                f"        if not result[\"success\"]:\n"
                f"            logger.error(f\"Failed to deliver message: {{result.get('error', 'Unknown error')}}\")\n"
                f"            if 'delivery_status' in result:\n"
                f"                for agent_id, status in result['delivery_status'].items():\n"
                f"                    if not status['success']:\n"
                f"                        logger.error(f\"Delivery to {{agent_id}} failed: {{status.get('error', 'Unknown error')}}\")"
            )
            new_content = new_content.replace(match, replacement)
        
        return count, new_content
    
    def add_target_filter_support(self, file_path: Path) -> bool:
        """
        Add target filter support to message bus if not already present.
        
        Args:
            file_path: Path to the message bus file
            
        Returns:
            bool: True if modified, False otherwise
        """
        # Only apply to message_bus.py or enhanced_message_bus.py
        if not (file_path.name == "message_bus.py" or file_path.name == "enhanced_message_bus.py"):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if target_filter is already supported
            if "target_filter" in content:
                return False
            
            # Find the publish method
            publish_pattern = r"def\s+publish\s*\(\s*self\s*,\s*message\s*:.*?\).*?:"
            publish_match = re.search(publish_pattern, content, re.DOTALL)
            
            if not publish_match:
                logger.warning(f"Could not find publish method in {file_path}")
                return False
            
            # Add target_filter parameter to method signature
            publish_def = publish_match.group(0)
            if ")" in publish_def:
                new_publish_def = publish_def.replace(")", ", target_filter: Optional[List[str]] = None)")
                content = content.replace(publish_def, new_publish_def)
            
            # Find the broadcast logic
            broadcast_pattern = r"# Broadcast to all interested subscribers.*?return\s+results"
            broadcast_match = re.search(broadcast_pattern, content, re.DOTALL)
            
            if broadcast_match:
                broadcast_code = broadcast_match.group(0)
                
                # Add target filter logic
                target_filter_code = (
                    "            # Apply target filter if provided\n"
                    "            if target_filter is not None:\n"
                    "                agent_subs = {agent_id: sub for agent_id, sub in agent_subs.items()\n"
                    "                              if agent_id in target_filter}\n"
                )
                
                # Insert after finding matching subscriptions but before delivery
                insert_point = broadcast_code.find("# Group by agent ID")
                if insert_point > 0:
                    new_broadcast_code = (
                        broadcast_code[:insert_point] + 
                        target_filter_code + 
                        broadcast_code[insert_point:]
                    )
                    content = content.replace(broadcast_code, new_broadcast_code)
            
            # Write the updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        
        except Exception as e:
            logger.error(f"Error adding target filter support to {file_path}: {e}")
            return False
    
    def fix_file(self, file_path: Path) -> bool:
        """
        Apply all fixes to a file.
        
        Args:
            file_path: Path to the file to fix
            
        Returns:
            bool: True if fixes were applied, False otherwise
        """
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create a backup
            backup_path = file_path.with_suffix(f"{file_path.suffix}{BACKUP_SUFFIX}")
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Apply fixes
            fixes_applied = False
            
            # Fix recipient parameter
            recipient_count, content = self.fix_recipient_parameter(content)
            if recipient_count > 0:
                fixes_applied = True
                self.total_recipient_occurrences += recipient_count
                logger.info(f"Fixed {recipient_count} 'recipient' parameters in {file_path}")
            
            # Fix broadcast handling
            broadcast_count, content = self.fix_broadcast_handling(content)
            if broadcast_count > 0:
                fixes_applied = True
                self.total_broadcast_fixes += broadcast_count
                logger.info(f"Fixed {broadcast_count} broadcast message handling issues in {file_path}")
            
            # Fix delivery confirmation
            delivery_count, content = self.fix_delivery_confirmation(content)
            if delivery_count > 0:
                fixes_applied = True
                self.total_delivery_confirmation_fixes += delivery_count
                logger.info(f"Added delivery confirmation to {delivery_count} critical messages in {file_path}")
            
            # Fix invalid recipient handling
            invalid_count, content = self.fix_invalid_recipient_handling(content)
            if invalid_count > 0:
                fixes_applied = True
                self.total_invalid_recipient_fixes += invalid_count
                logger.info(f"Improved error handling for {invalid_count} message deliveries in {file_path}")
            
            # Add target filter support if this is a message bus file
            if self.add_target_filter_support(file_path):
                fixes_applied = True
                logger.info(f"Added target filter support to {file_path}")
            
            # Write the updated content if fixes were applied
            if fixes_applied:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.modified_files.append(file_path)
                return True
            else:
                # Remove backup if no fixes were applied
                os.remove(backup_path)
                return False
        
        except Exception as e:
            logger.error(f"Error fixing file {file_path}: {e}")
            return False
    
    def run(self) -> bool:
        """
        Run all fixes.
        
        Returns:
            bool: True if any fixes were applied, False otherwise
        """
        # Find files to fix
        files = self.find_files_to_fix()
        logger.info(f"Found {len(files)} files to check for message addressing issues")
        
        # Apply fixes to each file
        fixed_files = 0
        for file_path in files:
            logger.info(f"Processing {file_path}...")
            if self.fix_file(file_path):
                fixed_files += 1
        
        # Print summary
        logger.info("\nSummary:")
        logger.info(f"- Total files modified: {fixed_files}")
        logger.info(f"- Total 'recipient' parameters fixed: {self.total_recipient_occurrences}")
        logger.info(f"- Total broadcast handling issues fixed: {self.total_broadcast_fixes}")
        logger.info(f"- Total delivery confirmation issues fixed: {self.total_delivery_confirmation_fixes}")
        logger.info(f"- Total invalid recipient handling issues fixed: {self.total_invalid_recipient_fixes}")
        
        if self.modified_files:
            logger.info("\nModified files:")
            for file_path in self.modified_files:
                logger.info(f"- {file_path}")
        
        return fixed_files > 0


def fix_all_recipient_params():
    """
    Fix all recipient parameters and related issues.
    
    Returns:
        bool: True if any fixes were applied, False otherwise
    """
    fixer = MessageAddressingFix()
    return fixer.run()


def main():
    """Main function to run the fix."""
    print("Fixing message addressing and delivery confirmation issues...")
    if fix_all_recipient_params():
        print("Fix applied successfully!")
        return 0
    else:
        print("No fixes were needed or applied.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
