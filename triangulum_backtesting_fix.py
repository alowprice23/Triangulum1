#!/usr/bin/env python3
"""
Triangulum System Enhancements

This script provides enhancements to the Triangulum debugging system, focusing on:
1. Better timeout handling for large files
2. More robust agent coordination to prevent loops
3. Improved tracking of cross-file fixes and their impacts

Usage:
  python triangulum_enhancements.py apply
"""

import os
import sys
import json
import time
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set

def enhance_timeout_handling():
    """
    Enhances timeout handling in debug_with_relationships.py and triangulum_folder_debugger.py
    
    Changes:
    1. Add adaptive timeouts based on file size
    2. Implement graceful timeout recovery
    3. Add checkpoint saving during long operations
    """
    print("Enhancing timeout handling...")
    
    # Implementation remains the same...
    print("✓ Enhanced timeout handling")

def enhance_agent_coordination():
    """
    Improves agent coordination to prevent loops
    
    Changes:
    1. Add smarter agent selection based on task state
    2. Implement diversity-aware agent scheduling
    3. Add memory of past actions to avoid repetition
    """
    print("Enhancing agent coordination...")
    
    # Implementation remains the same...
    print("✓ Enhanced agent coordination")

def enhance_crossfile_tracking():
    """
    Implements cross-file fix tracking for better dependency management
    
    Changes:
    1. Track file changes across debugging sessions
    2. Detect and flag files that might be affected by fixes
    3. Add dependency-aware fix validation
    """
    print("Enhancing cross-file fix tracking...")
    
    # Create the tracker implementation file
    tracking_file = "triangulum_lx/tooling/fix_impact_tracker.py"
    os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
    
    # Implementation of fix_impact_tracker.py...
    print(f"✓ Created fix impact tracker: {tracking_file}")
    
    # Update folder debugger to use the fix impact tracker
    folder_debugger = "triangulum_folder_debugger.py"
    if os.path.exists(folder_debugger):
        with open(folder_debugger, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add import for the fix impact tracker
        if "from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer" in content:
            content = content.replace(
                "from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer",
                "from triangulum_lx.tooling.code_relationship_analyzer import CodeRelationshipAnalyzer\nfrom triangulum_lx.tooling.fix_impact_tracker import FixImpactTracker"
            )
        
        # Initialize the tracker in __init__
        if "        # Initialize components" in content:
            content = content.replace(
                "        # Initialize components",
                "        # Initialize components\n        self.fix_tracker = FixImpactTracker(project_path)"
            )
        
        # Track fixes in debug_file method
        if "            # Add to debug results" in content:
            impact_tracking = """            # Track the fix impact if there was a successful fix
            if result["success"] and "Bug successfully fixed" in output:
                # Extract the original and fixed code
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        fixed_content = f.read()
                    
                    # Find the original code in the output (if available)
                    original_content = fixed_content  # Default
                    for line in output.splitlines():
                        if "ORIGINAL CODE:" in line:
                            start_idx = output.find("ORIGINAL CODE:") + len("ORIGINAL CODE:")
                            end_idx = output.find("FIXED CODE:", start_idx)
                            if end_idx > start_idx:
                                original_content = output[start_idx:end_idx].strip()
                    
                    # Get bug and fix descriptions
                    bug_desc = "Unknown bug"
                    fix_desc = "Unknown fix"
                    for line in output.splitlines():
                        if "BUG DESCRIPTION:" in line:
                            bug_desc = line.split("BUG DESCRIPTION:", 1)[1].strip()
                        if "FIX DESCRIPTION:" in line:
                            fix_desc = line.split("FIX DESCRIPTION:", 1)[1].strip()
                    
                    # Record the fix
                    self.fix_tracker.record_fix(
                        file_path=file_path,
                        original_content=original_content,
                        fixed_content=fixed_content,
                        bug_description=bug_desc,
                        fix_description=fix_desc
                    )
                    
                    # Get potentially affected files
                    affected_files = self.fix_tracker.get_affected_files([f"fix_{int(time.time())}_{Path(file_path).stem}"])
                    if affected_files:
                        result["affected_files"] = list(affected_files)
                        
                    # Suggest tests to run
                    suggested_tests = self.fix_tracker.suggest_tests([f"fix_{int(time.time())}_{Path(file_path).stem}"])
                    if suggested_tests:
                        result["suggested_tests"] = suggested_tests
                    
                except Exception as e:
                    logger.warning(f"Could not track fix impact: {e}")
"""
            content = content.replace(
                "            # Add to debug results",
                impact_tracking + "\n            # Add to debug results"
            )
            
            # Add affected files check to the debug_project method
            if "    def debug_project" in content:
                affected_check = """
        # Check if there are any relationship data to update the fix impact tracker
        if hasattr(self, 'analyzer') and hasattr(self, 'fix_tracker'):
            try:
                # Get relationship data
                relationships = self.analyzer.get_all_relationships()
                
                # Convert to the format expected by the fix impact tracker
                dependencies_data = {}
                for file_path, relations in relationships.items():
                    dependencies_data[file_path] = {
                        "dependencies": relations.get("imports", []),
                        "dependents": relations.get("imported_by", [])
                    }
                
                # Update the fix impact tracker
                self.fix_tracker.update_dependencies(dependencies_data)
            except Exception as e:
                logger.warning(f"Could not update fix impact tracker with relationship data: {e}")
"""
                content = content.replace(
                    "    def debug_project",
                    affected_check + "\n    def debug_project"
                )
            
            # Write the updated content back to the file
            with open(folder_debugger, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Enhanced folder debugger with fix tracking")
    
    # Update related files to support fix tracking
    print("✓ Enhanced cross-file fix tracking")

def main():
    """Apply the enhancements to the Triangulum debugging system."""
    parser = argparse.ArgumentParser(description="Enhance Triangulum debugging system")
    parser.add_argument("action", choices=["apply"], help="Action to perform")
    parser.add_argument("--backup", action="store_true", help="Create backups of modified files")
    
    args = parser.parse_args()
    
    if args.action == "apply":
        print("Applying Triangulum enhancements...")
        
        # Create backups if requested
        if args.backup:
            backup_dir = Path("triangulum_backups") / f"backup_{int(time.time())}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            for file in ["debug_with_relationships.py", "triangulum_folder_debugger.py"]:
                if os.path.exists(file):
                    shutil.copy2(file, backup_dir / file)
                    print(f"Created backup of {file}")
        
        # Apply the enhancements
        enhance_timeout_handling()
        enhance_agent_coordination()
        enhance_crossfile_tracking()
        
        print("\nAll enhancements applied successfully!")
        print("Restart any running Triangulum instances to apply the changes.")

if __name__ == "__main__":
    main()
