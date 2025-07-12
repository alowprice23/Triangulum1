#!/usr/bin/env python3
"""
Repair Planning Test

This script tests the repair planning capabilities of Triangulum by:
1. Loading a file from FixWurx that has known issues
2. Creating a repair plan for one of the issues
3. Validating the repair plan
4. Running a dry-run application of the repair

This allows us to verify Test #5 from the Triangulum Testing Plan.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("repair_planning_test")

# Import repair tools
from triangulum_lx.tooling.repair import (
    RepairTool, FileChange, ConflictType, ConflictResolutionStrategy, RepairStatus
)
from triangulum_lx.core.rollback_manager import RollbackManager

def main():
    """Main function to run the repair planning test."""
    logger.info("Starting Repair Planning Test")
    
    # Define the target file in FixWurx
    fixwurx_dir = "C:/Users/Yusuf/Downloads/FixWurx"
    target_file = os.path.join(fixwurx_dir, "triangulation_engine.py")
    
    # Ensure the file exists
    if not os.path.exists(target_file):
        logger.error(f"Target file not found: {target_file}")
        return 1
    
    # Read the current content
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Successfully read file: {target_file}")
    except Exception as e:
        logger.error(f"Error reading file {target_file}: {e}")
        return 1
    
    # Target the exception handling in MetricBus.publish method
    # This method silently swallows exceptions which is a common anti-pattern
    logger.info("Found issue: Silent exception handling in MetricBus.publish method")
    
    # Identify the lines with the issue
    lines = content.splitlines()
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if "except Exception:" in line and "# noqa: BLE001" in line:
            start_line = i + 1
        if start_line is not None and "pass" in line:
            end_line = i + 1
            break
    
    if not start_line or not end_line:
        logger.error("Could not find the target lines for the exception handling issue")
        return 1
    
    logger.info(f"Found issue on lines {start_line}-{end_line}: {lines[start_line-1:end_line]}")
    
    # Create a RepairTool instance
    rollback_manager = RollbackManager()
    repair_tool = RepairTool(rollback_manager=rollback_manager)
    
    # Create a FileChange for the issue
    original_content = "\n".join(lines[start_line-1:end_line])
    new_content = "            except Exception as e:  # noqa: BLE001\n                # metrics should log errors but never crash the engine\n                print(f\"MetricBus error: {e}\")"
    
    change = FileChange(
        file_path=target_file,
        start_line=start_line,
        end_line=end_line,
        original_content=original_content,
        new_content=new_content,
        change_type="replace",
        metadata={"issue_type": "exception_handling", "severity": "medium"}
    )
    
    # Create a repair plan
    repair_plan = repair_tool.create_repair_plan(
        name="Improve exception handling in MetricBus",
        description="Replace silent exception swallowing with error logging",
        changes=[change],
        metadata={"priority": "medium", "test": "repair_planning_test"}
    )
    
    logger.info(f"Created repair plan: {repair_plan.id}")
    logger.info(f"  Name: {repair_plan.name}")
    logger.info(f"  Description: {repair_plan.description}")
    logger.info(f"  Affected files: {repair_plan.get_affected_files()}")
    
    # Validate the repair plan
    is_valid, messages = repair_tool.validate_consistency(repair_plan)
    logger.info(f"Repair plan validation: {'Valid' if is_valid else 'Invalid'}")
    for message in messages:
        logger.info(f"  {message}")
    
    if not is_valid:
        logger.error("Repair plan validation failed")
        return 1
    
    # Apply the repair in dry-run mode
    logger.info("\nApplying repair in dry-run mode...")
    result = repair_tool.apply_repair(repair_plan.id, dry_run=True)
    
    if result["success"]:
        logger.info("Dry run successful!")
        logger.info(f"  Message: {result['message']}")
        logger.info(f"  Affected files: {result['affected_files']}")
        if "impact_boundary" in result:
            logger.info(f"  Impact boundary: {result['impact_boundary']}")
    else:
        logger.error(f"Dry run failed: {result['message']}")
        return 1
    
    # Get repair status
    status = repair_tool.get_repair_status(repair_plan.id)
    logger.info(f"\nRepair status: {status['status']}")
    
    # Show all repairs
    all_repairs = repair_tool.get_all_repairs()
    logger.info(f"\nTotal repairs planned: {len(all_repairs)}")
    
    for i, repair in enumerate(all_repairs, 1):
        logger.info(f"  Repair #{i}:")
        logger.info(f"    ID: {repair['repair_id']}")
        logger.info(f"    Name: {repair['name']}")
        logger.info(f"    Status: {repair['status']}")
        logger.info(f"    Affected files: {repair['affected_files']}")
    
    logger.info("\nRepair Planning Test completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
