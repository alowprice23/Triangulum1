"""
Repair Tool Demo

This demo showcases the capabilities of the enhanced Repair Tool for
safely applying coordinated fixes across multiple files with transaction
support, conflict detection, and rollback capabilities.

Key features demonstrated:
1. Transaction-based multi-file updates
2. Conflict detection between repairs
3. Consistency validation for cross-file changes
4. Repair planning and sequencing
5. Failure recovery mechanisms
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.tooling.repair import (
    RepairTool, FileChange, ConflictType, ConflictResolutionStrategy, RepairStatus
)
from triangulum_lx.core.rollback_manager import RollbackManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_files(base_dir: Path) -> Dict[str, str]:
    """
    Create test files for the demo.
    
    Args:
        base_dir: Base directory for test files
        
    Returns:
        Dictionary mapping file paths to their content
    """
    files = {
        "main.py": """
def calculate_total(items):
    \"\"\"Calculate the total price of items.\"\"\"
    total = 0
    for item in items:
        # Bug: No check for None or missing price
        total += item['price']
    return total

def apply_discount(total, discount_percent):
    \"\"\"Apply a discount to the total.\"\"\"
    # Bug: No validation for negative or excessive discount
    discount = total * (discount_percent / 100)
    return total - discount

def format_currency(amount):
    \"\"\"Format amount as currency.\"\"\"
    # Bug: No handling for negative amounts
    return f"${amount:.2f}"

def process_order(items, discount_percent=0):
    \"\"\"Process an order with optional discount.\"\"\"
    total = calculate_total(items)
    if discount_percent > 0:
        total = apply_discount(total, discount_percent)
    return format_currency(total)
""",
        "utils.py": """
def validate_item(item):
    \"\"\"Validate an item dictionary.\"\"\"
    # Bug: Incomplete validation
    return 'name' in item

def log_transaction(order_id, total):
    \"\"\"Log a transaction.\"\"\"
    # Bug: No validation for order_id
    with open('transactions.log', 'a') as f:
        f.write(f"{order_id}: {total}\\n")

def calculate_tax(amount, tax_rate=0.1):
    \"\"\"Calculate tax for an amount.\"\"\"
    # Bug: No validation for negative amounts
    return amount * tax_rate
""",
        "test_main.py": """
import unittest
from main import calculate_total, apply_discount, format_currency, process_order

class TestOrderFunctions(unittest.TestCase):
    def test_calculate_total(self):
        items = [{'name': 'Item 1', 'price': 10}, {'name': 'Item 2', 'price': 20}]
        self.assertEqual(calculate_total(items), 30)
    
    def test_apply_discount(self):
        self.assertEqual(apply_discount(100, 10), 90)
    
    def test_format_currency(self):
        self.assertEqual(format_currency(99.99), "$99.99")
    
    def test_process_order(self):
        items = [{'name': 'Item 1', 'price': 10}, {'name': 'Item 2', 'price': 20}]
        self.assertEqual(process_order(items), "$30.00")
        self.assertEqual(process_order(items, 10), "$27.00")

if __name__ == '__main__':
    unittest.main()
"""
    }
    
    # Create the files
    for rel_path, content in files.items():
        file_path = base_dir / rel_path
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
    
    return files


def demo_basic_repair(repair_tool: RepairTool, base_dir: Path):
    """
    Demonstrate basic repair functionality.
    
    Args:
        repair_tool: RepairTool instance
        base_dir: Base directory for test files
    """
    logger.info("\n\n===== DEMONSTRATING BASIC REPAIR =====")
    
    # Create a repair plan for the calculate_total function
    main_file = str(base_dir / "main.py")
    
    # Read the current content
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Create a file change to fix the bug in calculate_total
    change = FileChange(
        file_path=main_file,
        start_line=5,  # Line with the bug
        end_line=6,    # End line of the bug
        original_content="        # Bug: No check for None or missing price\n        total += item['price']",
        new_content="        # Fixed: Added check for None or missing price\n        total += item.get('price', 0)",
        change_type="replace",
        metadata={"bug_type": "null_pointer", "severity": "high"}
    )
    
    # Create a repair plan
    repair_plan = repair_tool.create_repair_plan(
        name="Fix calculate_total null pointer bug",
        description="Add null check for item price to prevent KeyError",
        changes=[change],
        metadata={"priority": "high", "issue_id": "ISSUE-123"}
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
    
    # Apply the repair
    logger.info("\nApplying repair...")
    result = repair_tool.apply_repair(repair_plan.id)
    
    if result["success"]:
        logger.info("Repair applied successfully!")
        logger.info(f"  Message: {result['message']}")
        logger.info(f"  Affected files: {result['affected_files']}")
        
        # Show the changes
        logger.info("\nChanges made:")
        with open(main_file, 'r') as f:
            new_content = f.read()
        
        # Find the fixed lines
        old_lines = content.splitlines()
        new_lines = new_content.splitlines()
        
        for i in range(max(len(old_lines), len(new_lines))):
            if i < len(old_lines) and i < len(new_lines) and old_lines[i] != new_lines[i]:
                logger.info(f"  Line {i+1} changed:")
                logger.info(f"    Old: {old_lines[i]}")
                logger.info(f"    New: {new_lines[i]}")
    else:
        logger.error(f"Repair failed: {result['message']}")
    
    # Get repair status
    status = repair_tool.get_repair_status(repair_plan.id)
    logger.info(f"\nRepair status: {status['status']}")
    
    return repair_plan


def demo_multi_file_repair(repair_tool: RepairTool, base_dir: Path):
    """
    Demonstrate multi-file repair functionality.
    
    Args:
        repair_tool: RepairTool instance
        base_dir: Base directory for test files
    """
    logger.info("\n\n===== DEMONSTRATING MULTI-FILE REPAIR =====")
    
    # Create a repair plan that affects multiple files
    main_file = str(base_dir / "main.py")
    utils_file = str(base_dir / "utils.py")
    
    # Read the current content
    with open(main_file, 'r') as f:
        main_content = f.read()
    
    with open(utils_file, 'r') as f:
        utils_content = f.read()
    
    # Create file changes
    changes = [
        # Fix apply_discount in main.py
        FileChange(
            file_path=main_file,
            start_line=10,
            end_line=12,
            original_content="    # Bug: No validation for negative or excessive discount\n    discount = total * (discount_percent / 100)\n    return total - discount",
            new_content="    # Fixed: Added validation for discount percentage\n    discount_percent = max(0, min(discount_percent, 100))  # Clamp between 0-100\n    discount = total * (discount_percent / 100)\n    return total - discount",
            change_type="replace",
            metadata={"bug_type": "input_validation", "severity": "medium"}
        ),
        # Fix calculate_tax in utils.py
        FileChange(
            file_path=utils_file,
            start_line=14,
            end_line=15,
            original_content="    # Bug: No validation for negative amounts\n    return amount * tax_rate",
            new_content="    # Fixed: Added validation for negative amounts\n    amount = max(0, amount)  # Ensure non-negative\n    return amount * tax_rate",
            change_type="replace",
            metadata={"bug_type": "input_validation", "severity": "medium"}
        )
    ]
    
    # Create a repair plan
    repair_plan = repair_tool.create_repair_plan(
        name="Fix input validation bugs",
        description="Add proper input validation to prevent invalid calculations",
        changes=changes,
        metadata={"priority": "medium", "issue_id": "ISSUE-456"}
    )
    
    logger.info(f"Created multi-file repair plan: {repair_plan.id}")
    logger.info(f"  Name: {repair_plan.name}")
    logger.info(f"  Description: {repair_plan.description}")
    logger.info(f"  Affected files: {repair_plan.get_affected_files()}")
    
    # Validate the repair plan
    is_valid, messages = repair_tool.validate_consistency(repair_plan)
    logger.info(f"Repair plan validation: {'Valid' if is_valid else 'Invalid'}")
    for message in messages:
        logger.info(f"  {message}")
    
    # Apply the repair
    logger.info("\nApplying multi-file repair...")
    result = repair_tool.apply_repair(repair_plan.id)
    
    if result["success"]:
        logger.info("Multi-file repair applied successfully!")
        logger.info(f"  Message: {result['message']}")
        logger.info(f"  Affected files: {result['affected_files']}")
        
        # Show the changes
        logger.info("\nChanges made to main.py:")
        with open(main_file, 'r') as f:
            new_main_content = f.read()
        
        # Find the fixed lines in main.py
        old_lines = main_content.splitlines()
        new_lines = new_main_content.splitlines()
        
        for i in range(max(len(old_lines), len(new_lines))):
            if i < len(old_lines) and i < len(new_lines) and old_lines[i] != new_lines[i]:
                logger.info(f"  Line {i+1} changed:")
                logger.info(f"    Old: {old_lines[i]}")
                logger.info(f"    New: {new_lines[i]}")
        
        logger.info("\nChanges made to utils.py:")
        with open(utils_file, 'r') as f:
            new_utils_content = f.read()
        
        # Find the fixed lines in utils.py
        old_lines = utils_content.splitlines()
        new_lines = new_utils_content.splitlines()
        
        for i in range(max(len(old_lines), len(new_lines))):
            if i < len(old_lines) and i < len(new_lines) and old_lines[i] != new_lines[i]:
                logger.info(f"  Line {i+1} changed:")
                logger.info(f"    Old: {old_lines[i]}")
                logger.info(f"    New: {new_lines[i]}")
    else:
        logger.error(f"Multi-file repair failed: {result['message']}")
    
    return repair_plan


def demo_conflict_detection(repair_tool: RepairTool, base_dir: Path):
    """
    Demonstrate conflict detection between repairs.
    
    Args:
        repair_tool: RepairTool instance
        base_dir: Base directory for test files
    """
    logger.info("\n\n===== DEMONSTRATING CONFLICT DETECTION =====")
    
    main_file = str(base_dir / "main.py")
    
    # Create two conflicting repair plans
    
    # First repair plan
    change1 = FileChange(
        file_path=main_file,
        start_line=15,
        end_line=16,
        original_content="    # Bug: No handling for negative amounts\n    return f\"${amount:.2f}\"",
        new_content="    # Fixed: Added handling for negative amounts (approach 1)\n    return f\"${max(0, amount):.2f}\"",
        change_type="replace",
        metadata={"bug_type": "input_validation", "severity": "medium"}
    )
    
    repair_plan1 = repair_tool.create_repair_plan(
        name="Fix format_currency (approach 1)",
        description="Handle negative amounts by clamping to zero",
        changes=[change1],
        metadata={"priority": "medium", "issue_id": "ISSUE-789"}
    )
    
    # Second repair plan (conflicting with the first)
    change2 = FileChange(
        file_path=main_file,
        start_line=15,
        end_line=16,
        original_content="    # Bug: No handling for negative amounts\n    return f\"${amount:.2f}\"",
        new_content="    # Fixed: Added handling for negative amounts (approach 2)\n    prefix = '-' if amount < 0 else ''\n    return f\"{prefix}${abs(amount):.2f}\"",
        change_type="replace",
        metadata={"bug_type": "input_validation", "severity": "medium"}
    )
    
    repair_plan2 = repair_tool.create_repair_plan(
        name="Fix format_currency (approach 2)",
        description="Handle negative amounts with a negative sign prefix",
        changes=[change2],
        metadata={"priority": "medium", "issue_id": "ISSUE-790"}
    )
    
    logger.info(f"Created two potentially conflicting repair plans:")
    logger.info(f"  Plan 1: {repair_plan1.id} - {repair_plan1.name}")
    logger.info(f"  Plan 2: {repair_plan2.id} - {repair_plan2.name}")
    
    # Detect conflicts
    conflicts = repair_tool.detect_conflicts(repair_plan1.id, repair_plan2.id)
    
    if conflicts:
        logger.info(f"\nDetected {len(conflicts)} conflicts:")
        for i, (change1, change2, conflict_type) in enumerate(conflicts, 1):
            logger.info(f"  Conflict #{i}:")
            logger.info(f"    Type: {conflict_type.name}")
            logger.info(f"    File: {change1.file_path}")
            logger.info(f"    Lines: {change1.start_line}-{change1.end_line}")
            logger.info(f"    Change 1: {change1.new_content.splitlines()[0]}")
            logger.info(f"    Change 2: {change2.new_content.splitlines()[0]}")
        
        # Resolve conflicts
        logger.info("\nResolving conflicts using PRIORITIZE_FIRST strategy...")
        resolved_changes = repair_tool.resolve_conflicts(
            conflicts, ConflictResolutionStrategy.PRIORITIZE_FIRST
        )
        
        logger.info(f"Resolved to {len(resolved_changes)} changes")
        
        # Apply the first repair plan
        logger.info("\nApplying first repair plan...")
        result = repair_tool.apply_repair(repair_plan1.id)
        
        if result["success"]:
            logger.info("First repair plan applied successfully!")
            
            # Try to apply the second repair plan (should fail or be rejected)
            logger.info("\nAttempting to apply second repair plan (should detect conflict)...")
            result2 = repair_tool.apply_repair(repair_plan2.id)
            
            if not result2["success"]:
                logger.info("Second repair correctly rejected due to conflict!")
                logger.info(f"  Message: {result2['message']}")
            else:
                logger.warning("Second repair unexpectedly succeeded despite conflict!")
        else:
            logger.error(f"First repair failed: {result['message']}")
    else:
        logger.warning("No conflicts detected between the repair plans (unexpected)")
    
    return repair_plan1, repair_plan2


def demo_rollback(repair_tool: RepairTool, base_dir: Path, repair_plan_id: str):
    """
    Demonstrate rollback functionality.
    
    Args:
        repair_tool: RepairTool instance
        base_dir: Base directory for test files
        repair_plan_id: ID of the repair plan to roll back
    """
    logger.info("\n\n===== DEMONSTRATING ROLLBACK =====")
    
    # Get the repair plan
    repair_plan = repair_tool.get_repair_plan(repair_plan_id)
    if not repair_plan:
        logger.error(f"Repair plan {repair_plan_id} not found")
        return
    
    logger.info(f"Rolling back repair plan: {repair_plan.id}")
    logger.info(f"  Name: {repair_plan.name}")
    logger.info(f"  Status: {repair_plan.status.name}")
    logger.info(f"  Affected files: {repair_plan.get_affected_files()}")
    
    # Save current content for comparison
    affected_files = repair_plan.get_affected_files()
    current_content = {}
    for file_path in affected_files:
        with open(file_path, 'r') as f:
            current_content[file_path] = f.read()
    
    # Roll back the repair
    result = repair_tool.rollback_repair(repair_plan_id)
    
    if result["success"]:
        logger.info("Repair successfully rolled back!")
        logger.info(f"  Message: {result['message']}")
        
        # Show the changes
        logger.info("\nChanges after rollback:")
        for file_path in affected_files:
            with open(file_path, 'r') as f:
                new_content = f.read()
            
            if current_content[file_path] != new_content:
                logger.info(f"  File {file_path} was restored to its original state")
                
                # Show a diff of a few lines
                old_lines = current_content[file_path].splitlines()
                new_lines = new_content.splitlines()
                
                for i in range(max(len(old_lines), len(new_lines))):
                    if i < len(old_lines) and i < len(new_lines) and old_lines[i] != new_lines[i]:
                        logger.info(f"    Line {i+1} changed:")
                        logger.info(f"      Before rollback: {old_lines[i]}")
                        logger.info(f"      After rollback: {new_lines[i]}")
            else:
                logger.warning(f"  File {file_path} was not changed by rollback")
    else:
        logger.error(f"Rollback failed: {result['message']}")


def demo_repair_verification(repair_tool: RepairTool, base_dir: Path):
    """
    Demonstrate repair verification functionality.
    
    Args:
        repair_tool: RepairTool instance
        base_dir: Base directory for test files
    """
    logger.info("\n\n===== DEMONSTRATING REPAIR VERIFICATION =====")
    
    # Create a repair plan that fixes a bug but should pass tests
    main_file = str(base_dir / "main.py")
    
    # Read the current content
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Create a file change to fix the format_currency function
    change = FileChange(
        file_path=main_file,
        start_line=15,
        end_line=16,
        original_content="    # Bug: No handling for negative amounts\n    return f\"${amount:.2f}\"",
        new_content="    # Fixed: Added handling for negative amounts\n    return f\"${abs(amount):.2f}\"",
        change_type="replace",
        metadata={"bug_type": "input_validation", "severity": "medium"}
    )
    
    # Create a repair plan
    repair_plan = repair_tool.create_repair_plan(
        name="Fix format_currency function",
        description="Handle negative amounts properly",
        changes=[change],
        metadata={"priority": "medium", "issue_id": "ISSUE-999"}
    )
    
    logger.info(f"Created repair plan: {repair_plan.id}")
    logger.info(f"  Name: {repair_plan.name}")
    logger.info(f"  Description: {repair_plan.description}")
    
    # Apply the repair
    logger.info("\nApplying repair...")
    result = repair_tool.apply_repair(repair_plan.id)
    
    if result["success"]:
        logger.info("Repair applied successfully!")
        
        # Verify the repair by running tests
        logger.info("\nVerifying repair by running tests...")
        
        # In a real scenario, we would use repair_tool.verify_repair(repair_plan.id)
        # But for this demo, we'll run the tests directly
        
        test_file = str(base_dir / "test_main.py")
        
        # Run the tests
        import unittest
        import subprocess
        
        logger.info(f"Running tests from {test_file}...")
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Tests passed! Repair is verified.")
            logger.info(f"Test output:\n{result.stdout}")
        else:
            logger.error("Tests failed! Repair needs adjustment.")
            logger.error(f"Test output:\n{result.stdout}")
            logger.error(f"Test errors:\n{result.stderr}")
            
            # Roll back the repair
            logger.info("\nRolling back the failed repair...")
            rollback_result = repair_tool.rollback_repair(repair_plan.id)
            
            if rollback_result["success"]:
                logger.info("Repair successfully rolled back after test failure")
            else:
                logger.error(f"Rollback failed: {rollback_result['message']}")
    else:
        logger.error(f"Repair failed to apply: {result['message']}")
    
    return repair_plan


def main():
    """Main function for the demo."""
    logger.info("Starting Repair Tool Demo")
    
    # Create a temporary directory for the demo
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        logger.info(f"Created temporary directory: {base_dir}")
        
        # Create test files
        files = create_test_files(base_dir)
        logger.info(f"Created {len(files)} test files")
        
        # Create a rollback manager
        rollback_manager = RollbackManager()
        
        # Create a repair tool
        repair_tool = RepairTool(rollback_manager=rollback_manager)
        
        # Run the demos
        repair_plan1 = demo_basic_repair(repair_tool, base_dir)
        repair_plan2 = demo_multi_file_repair(repair_tool, base_dir)
        conflict_plans = demo_conflict_detection(repair_tool, base_dir)
        demo_rollback(repair_tool, base_dir, repair_plan2.id)
        verification_plan = demo_repair_verification(repair_tool, base_dir)
        
        # Show all repairs
        logger.info("\n\n===== ALL REPAIRS =====")
        all_repairs = repair_tool.get_all_repairs()
        logger.info(f"Total repairs: {len(all_repairs)}")
        
        for i, repair in enumerate(all_repairs, 1):
            logger.info(f"  Repair #{i}:")
            logger.info(f"    ID: {repair['repair_id']}")
            logger.info(f"    Name: {repair['name']}")
            logger.info(f"    Status: {repair['status']}")
            logger.info(f"    Affected files: {repair['affected_files']}")
        
        # Clean up
        logger.info("\nCleaning up...")
    
    logger.info("Repair Tool Demo completed")


if __name__ == "__main__":
    main()
