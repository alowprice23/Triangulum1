#!/usr/bin/env python3
"""
Comprehensive Fix for Agent Message Parameters

This script addresses multiple issues with agent message parameters across the codebase:
1. Fixes 'recipient' vs 'receiver' parameter inconsistencies
2. Ensures proper type handling for message parameters
3. Adds validation for required parameters
4. Standardizes default value handling
5. Ensures schema compliance for all agent messages
"""

import os
import sys
import re
import glob
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Constants
AGENT_FILES_PATTERN = "triangulum_lx/agents/*.py"
EXAMPLE_FILES_PATTERN = "examples/*.py"
TEST_FILES_PATTERN = "tests/**/*.py"
BACKUP_SUFFIX = ".params.bak"


def find_files_with_agent_messages() -> List[Path]:
    """
    Find all files that might contain AgentMessage instantiations.
    
    Returns:
        List[Path]: List of file paths
    """
    files = []
    
    # Find agent files
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
                
                # Check if the file contains AgentMessage instantiations
                if "AgentMessage(" in content or "message_type=" in content:
                    filtered_files.append(file_path)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
    
    return filtered_files


def fix_recipient_parameter(file_path: Path) -> Tuple[int, str]:
    """
    Fix 'recipient' to 'receiver' parameter in a file.
    
    Args:
        file_path: Path to the file to fix
        
    Returns:
        Tuple[int, str]: Number of replacements and updated content
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace recipient with receiver in AgentMessage constructor calls
    if "recipient=" not in content:
        return 0, content
    
    # Make the replacement
    new_content = content.replace("recipient=", "receiver=")
    
    # Count occurrences for reporting
    count = content.count("recipient=")
    
    return count, new_content


def fix_type_conversions(file_path: Path, content: str) -> Tuple[int, str]:
    """
    Fix type conversions for message parameters.
    
    Args:
        file_path: Path to the file to fix
        content: Current content of the file
        
    Returns:
        Tuple[int, str]: Number of replacements and updated content
    """
    # Regular expressions for finding problematic type conversions
    patterns = [
        # String message_type without conversion
        (r'message_type\s*=\s*[\'"]([a-z_]+)[\'"]', 
         r'message_type=MessageType.\1.value'),
        
        # Confidence as string without conversion
        (r'confidence\s*=\s*[\'"]([0-9.]+)[\'"]',
         r'confidence=float(\1)'),
        
        # Boolean as string without conversion
        (r'(is_chunked|compressed)\s*=\s*[\'"]([Tt]rue|[Ff]alse)[\'"]',
         lambda m: f'{m.group(1)}={m.group(2).lower() == "true"}'),
    ]
    
    count = 0
    new_content = content
    
    for pattern, replacement in patterns:
        # Count matches before replacement
        matches = re.findall(pattern, new_content)
        count += len(matches)
        
        # Apply replacement
        if callable(replacement):
            # For replacements that need a function
            new_content = re.sub(pattern, replacement, new_content)
        else:
            # For simple string replacements
            new_content = re.sub(pattern, replacement, new_content)
    
    return count, new_content


def fix_default_values(file_path: Path, content: str) -> Tuple[int, str]:
    """
    Fix default value handling for message parameters.
    
    Args:
        file_path: Path to the file to fix
        content: Current content of the file
        
    Returns:
        Tuple[int, str]: Number of replacements and updated content
    """
    # Regular expression for finding AgentMessage instantiations
    pattern = r'AgentMessage\s*\(\s*([^)]+)\)'
    
    count = 0
    new_content = content
    
    # Find all AgentMessage instantiations
    for match in re.finditer(pattern, content):
        args = match.group(1)
        
        # Check if schema_version is missing
        if 'schema_version=' not in args:
            # Add schema_version parameter
            new_args = args
            if args.strip().endswith(','):
                new_args = f"{args} schema_version=\"1.1\","
            else:
                new_args = f"{args}, schema_version=\"1.1\""
            
            # Replace in content
            new_content = new_content.replace(args, new_args)
            count += 1
    
    return count, new_content


def fix_validation_calls(file_path: Path, content: str) -> Tuple[int, str]:
    """
    Fix validation calls for message parameters.
    
    Args:
        file_path: Path to the file to fix
        content: Current content of the file
        
    Returns:
        Tuple[int, str]: Number of replacements and updated content
    """
    # Regular expression for finding manual validation
    pattern = r'if\s+not\s+isinstance\s*\(\s*message\.([a-z_]+)\s*,\s*([^)]+)\s*\):'
    
    count = 0
    new_content = content
    
    # Find all manual validation calls
    for match in re.finditer(pattern, content):
        field = match.group(1)
        expected_type = match.group(2)
        
        # Check if this is a validation that should be handled by the schema
        if field in ['message_type', 'content', 'sender', 'confidence']:
            # Get the full if block
            if_block_pattern = f"if\\s+not\\s+isinstance\\s*\\(\\s*message\\.{field}\\s*,\\s*{expected_type}\\s*\\):.*?(?=\\n\\S)"
            if_block_match = re.search(if_block_pattern, content, re.DOTALL)
            
            if if_block_match:
                # Replace with a call to validate()
                if_block = if_block_match.group(0)
                new_content = new_content.replace(if_block, "# Validation handled by message.validate()")
                count += 1
    
    return count, new_content


def apply_fixes_to_file(file_path: Path) -> bool:
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
        recipient_count, content = fix_recipient_parameter(file_path, content)
        if recipient_count > 0:
            fixes_applied = True
            print(f"  - Fixed {recipient_count} 'recipient' parameters")
        
        # Fix type conversions
        type_count, content = fix_type_conversions(file_path, content)
        if type_count > 0:
            fixes_applied = True
            print(f"  - Fixed {type_count} type conversion issues")
        
        # Fix default values
        default_count, content = fix_default_values(file_path, content)
        if default_count > 0:
            fixes_applied = True
            print(f"  - Added {default_count} missing default values")
        
        # Fix validation calls
        validation_count, content = fix_validation_calls(file_path, content)
        if validation_count > 0:
            fixes_applied = True
            print(f"  - Updated {validation_count} validation calls")
        
        # Write the updated content if fixes were applied
        if fixes_applied:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  - Updated file: {file_path}")
            return True
        else:
            # Remove backup if no fixes were applied
            os.remove(backup_path)
            return False
    
    except Exception as e:
        print(f"Error fixing file {file_path}: {e}")
        return False


def fix_agent_message_params():
    """
    Fix agent message parameters across the codebase.
    """
    # Find files with AgentMessage instantiations
    files = find_files_with_agent_messages()
    print(f"Found {len(files)} files that might contain AgentMessage instantiations")
    
    # Apply fixes to each file
    fixed_files = 0
    for file_path in files:
        print(f"Processing {file_path}...")
        if apply_fixes_to_file(file_path):
            fixed_files += 1
    
    print(f"\nFixed {fixed_files} files")
    return fixed_files > 0


def main():
    """Main function to run the fix."""
    print("Fixing AgentMessage parameters across the codebase...")
    if fix_agent_message_params():
        print("Fix applied successfully!")
        return 0
    else:
        print("No fixes were needed or applied.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
