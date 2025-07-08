"""
Rollback Manager Demo

This demo showcases the capabilities of the enhanced Rollback Manager for
safely managing multi-file changes with transaction support, snapshots,
and recovery points.

Key features demonstrated:
1. Transaction-based file operations
2. Nested transactions with proper isolation
3. Snapshot-based file state tracking
4. Recovery points for system-wide state restoration
5. Hierarchical rollback capabilities
"""

import os
import sys
import time
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the path so we can import triangulum_lx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from triangulum_lx.core.rollback_manager import (
    RollbackManager, SnapshotType, Transaction, RecoveryPoint
)

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
        "file1.txt": "This is the content of file 1.\nIt has multiple lines.\n",
        "file2.txt": "This is the content of file 2.\nIt also has multiple lines.\n",
        "subdir/file3.txt": "This is a file in a subdirectory.\n",
        "subdir/file4.txt": "Another file in the subdirectory.\n",
        "config.json": '{\n  "setting1": "value1",\n  "setting2": 42,\n  "debug": false\n}'
    }
    
    # Create the files
    for rel_path, content in files.items():
        file_path = base_dir / rel_path
        os.makedirs(file_path.parent, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
    
    return files


def modify_file(file_path: Path, new_content: str) -> None:
    """
    Modify a file with new content.
    
    Args:
        file_path: Path to the file
        new_content: New content for the file
    """
    with open(file_path, 'w') as f:
        f.write(new_content)


def read_file(file_path: Path) -> str:
    """
    Read the content of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Content of the file
    """
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"[File not found: {file_path}]"


def print_file_status(base_dir: Path, files: Dict[str, str]) -> None:
    """
    Print the status of all files.
    
    Args:
        base_dir: Base directory for test files
        files: Dictionary mapping file paths to their original content
    """
    logger.info("Current file status:")
    for rel_path, original_content in files.items():
        file_path = base_dir / rel_path
        current_content = read_file(file_path)
        
        if current_content == original_content:
            status = "UNCHANGED"
        elif current_content == f"[File not found: {file_path}]":
            status = "DELETED"
        else:
            status = "MODIFIED"
        
        logger.info(f"  {rel_path}: {status}")
        if status == "MODIFIED":
            logger.info(f"    Original: {original_content.strip()}")
            logger.info(f"    Current:  {current_content.strip()}")


def demo_basic_transactions(base_dir: Path, files: Dict[str, str]) -> None:
    """
    Demonstrate basic transaction functionality.
    
    Args:
        base_dir: Base directory for test files
        files: Dictionary mapping file paths to their original content
    """
    logger.info("\n=== Demonstrating Basic Transactions ===")
    
    # Create a rollback manager
    manager = RollbackManager()
    
    # Modify files within a transaction
    logger.info("Modifying files within a transaction...")
    with manager.transaction("Basic file modifications") as transaction:
        # Take snapshots before modification
        manager.add_file_snapshot(str(base_dir / "file1.txt"))
        manager.add_file_snapshot(str(base_dir / "file2.txt"))
        
        # Modify the files
        modify_file(base_dir / "file1.txt", "Modified content of file 1.\n")
        modify_file(base_dir / "file2.txt", "Modified content of file 2.\n")
        
        # Log transaction details
        logger.info(f"Transaction ID: {transaction.id}")
        logger.info(f"Transaction name: {transaction.name}")
        logger.info(f"Affected files: {transaction.get_affected_files()}")
    
    # Show the modified files
    logger.info("\nFiles after transaction commit:")
    print_file_status(base_dir, files)
    
    # Rollback the transaction
    logger.info("\nRolling back the transaction...")
    manager.rollback_transaction(transaction.id)
    
    # Show the files after rollback
    logger.info("\nFiles after transaction rollback:")
    print_file_status(base_dir, files)


def demo_nested_transactions(base_dir: Path, files: Dict[str, str]) -> None:
    """
    Demonstrate nested transaction functionality.
    
    Args:
        base_dir: Base directory for test files
        files: Dictionary mapping file paths to their original content
    """
    logger.info("\n=== Demonstrating Nested Transactions ===")
    
    # Create a rollback manager
    manager = RollbackManager()
    
    # Outer transaction
    logger.info("Starting outer transaction...")
    with manager.transaction("Outer transaction") as outer_transaction:
        # Take snapshots before modification
        manager.add_file_snapshot(str(base_dir / "file1.txt"))
        
        # Modify file1.txt in the outer transaction
        modify_file(base_dir / "file1.txt", "Modified by outer transaction.\n")
        
        # Inner transaction
        logger.info("Starting inner transaction...")
        with manager.nested_transaction("Inner transaction") as inner_transaction:
            # Take snapshots before modification
            manager.add_file_snapshot(str(base_dir / "file2.txt"))
            manager.add_file_snapshot(str(base_dir / "subdir/file3.txt"))
            
            # Modify files in the inner transaction
            modify_file(base_dir / "file2.txt", "Modified by inner transaction.\n")
            modify_file(base_dir / "subdir/file3.txt", "Modified by inner transaction.\n")
            
            logger.info(f"Inner transaction ID: {inner_transaction.id}")
            logger.info(f"Inner transaction affected files: {inner_transaction.get_affected_files()}")
        
        logger.info("Inner transaction committed.")
        logger.info(f"Outer transaction ID: {outer_transaction.id}")
        logger.info(f"Outer transaction affected files: {outer_transaction.get_affected_files()}")
    
    logger.info("Outer transaction committed.")
    
    # Show the modified files
    logger.info("\nFiles after nested transactions commit:")
    print_file_status(base_dir, files)
    
    # Get active transactions
    active_transactions = manager.get_active_transactions()
    logger.info(f"\nActive transactions: {len(active_transactions)}")
    
    # Rollback the outer transaction (should also rollback inner)
    logger.info("\nRolling back the outer transaction...")
    manager.rollback_transaction(outer_transaction.id)
    
    # Show the files after rollback
    logger.info("\nFiles after transaction rollback:")
    print_file_status(base_dir, files)


def demo_recovery_points(base_dir: Path, files: Dict[str, str]) -> None:
    """
    Demonstrate recovery point functionality.
    
    Args:
        base_dir: Base directory for test files
        files: Dictionary mapping file paths to their original content
    """
    logger.info("\n=== Demonstrating Recovery Points ===")
    
    # Create a rollback manager
    manager = RollbackManager()
    
    # Create an initial recovery point
    logger.info("Creating initial recovery point...")
    
    # First transaction - modify file1.txt
    with manager.transaction("Modify file1") as transaction1:
        manager.add_file_snapshot(str(base_dir / "file1.txt"))
        modify_file(base_dir / "file1.txt", "Modified for recovery point demo (1).\n")
    
    # Create a recovery point after the first change
    recovery_point1 = manager.create_recovery_point("After first modification")
    logger.info(f"Created recovery point: {recovery_point1.id} - {recovery_point1.name}")
    
    # Second transaction - modify file2.txt
    with manager.transaction("Modify file2") as transaction2:
        manager.add_file_snapshot(str(base_dir / "file2.txt"))
        modify_file(base_dir / "file2.txt", "Modified for recovery point demo (2).\n")
    
    # Third transaction - modify file3.txt
    with manager.transaction("Modify file3") as transaction3:
        manager.add_file_snapshot(str(base_dir / "subdir/file3.txt"))
        modify_file(base_dir / "subdir/file3.txt", "Modified for recovery point demo (3).\n")
    
    # Create a recovery point after all changes
    recovery_point2 = manager.create_recovery_point("After all modifications")
    logger.info(f"Created recovery point: {recovery_point2.id} - {recovery_point2.name}")
    
    # Show the modified files
    logger.info("\nFiles after all modifications:")
    print_file_status(base_dir, files)
    
    # Restore to the first recovery point
    logger.info("\nRestoring to first recovery point...")
    manager.restore_recovery_point(recovery_point1.id)
    
    # Show the files after first restore
    logger.info("\nFiles after restoring to first recovery point:")
    print_file_status(base_dir, files)
    
    # Restore to the second recovery point
    logger.info("\nRestoring to second recovery point...")
    manager.restore_recovery_point(recovery_point2.id)
    
    # Show the files after second restore
    logger.info("\nFiles after restoring to second recovery point:")
    print_file_status(base_dir, files)
    
    # List all recovery points
    recovery_points = manager.get_recovery_points()
    logger.info(f"\nAll recovery points ({len(recovery_points)}):")
    for rp in recovery_points:
        logger.info(f"  {rp.id} - {rp.name} - Created: {time.ctime(rp.created_at)}")
        affected_files = rp.get_affected_files(manager.transaction_manager)
        logger.info(f"  Affected files: {affected_files}")


def demo_snapshot_types(base_dir: Path, files: Dict[str, str]) -> None:
    """
    Demonstrate different snapshot types.
    
    Args:
        base_dir: Base directory for test files
        files: Dictionary mapping file paths to their original content
    """
    logger.info("\n=== Demonstrating Snapshot Types ===")
    
    # Create a rollback manager
    manager = RollbackManager()
    
    # Full snapshot
    logger.info("Demonstrating FULL snapshot type...")
    with manager.transaction("Full snapshot demo") as transaction:
        # Take a full snapshot
        manager.add_file_snapshot(
            str(base_dir / "config.json"),
            snapshot_type=SnapshotType.FULL
        )
        
        # Modify the file
        modify_file(
            base_dir / "config.json",
            '{\n  "setting1": "modified",\n  "setting2": 100,\n  "debug": true\n}'
        )
    
    # Show the modified file
    logger.info("\nFile after modification with FULL snapshot:")
    logger.info(read_file(base_dir / "config.json"))
    
    # Rollback
    logger.info("\nRolling back FULL snapshot transaction...")
    manager.rollback_transaction(transaction.id)
    
    # Show the file after rollback
    logger.info("\nFile after rollback:")
    logger.info(read_file(base_dir / "config.json"))
    
    # Metadata snapshot
    logger.info("\nDemonstrating METADATA snapshot type...")
    with manager.transaction("Metadata snapshot demo") as transaction:
        # Take a metadata snapshot
        manager.add_file_snapshot(
            str(base_dir / "file1.txt"),
            snapshot_type=SnapshotType.METADATA
        )
        
        # Change file permissions (this is just a simulation for the demo)
        file_path = base_dir / "file1.txt"
        current_mode = os.stat(file_path).st_mode
        os.chmod(file_path, current_mode | 0o200)  # Add write permission
        
        logger.info(f"Changed permissions on {file_path}")
    
    # Rollback
    logger.info("\nRolling back METADATA snapshot transaction...")
    manager.rollback_transaction(transaction.id)
    
    logger.info("\nPermissions restored to original state")


def demo_error_handling(base_dir: Path, files: Dict[str, str]) -> None:
    """
    Demonstrate error handling in transactions.
    
    Args:
        base_dir: Base directory for test files
        files: Dictionary mapping file paths to their original content
    """
    logger.info("\n=== Demonstrating Error Handling ===")
    
    # Create a rollback manager
    manager = RollbackManager()
    
    # Transaction with an error
    logger.info("Starting transaction that will encounter an error...")
    try:
        with manager.transaction("Error handling demo") as transaction:
            # Take snapshots before modification
            manager.add_file_snapshot(str(base_dir / "file1.txt"))
            manager.add_file_snapshot(str(base_dir / "file2.txt"))
            
            # Modify the files
            modify_file(base_dir / "file1.txt", "Modified before error.\n")
            modify_file(base_dir / "file2.txt", "Modified before error.\n")
            
            # Simulate an error
            logger.info("Simulating an error in the transaction...")
            raise ValueError("Simulated error in transaction")
            
            # This code will not be executed
            modify_file(base_dir / "file1.txt", "This should not be written.\n")
    
    except ValueError as e:
        logger.info(f"Caught error: {e}")
    
    # Show the files after error
    logger.info("\nFiles after transaction with error:")
    print_file_status(base_dir, files)
    
    # The transaction should have been automatically rolled back
    logger.info("\nTransaction should have been automatically rolled back")


def main():
    """Main function for the demo."""
    logger.info("Starting Rollback Manager Demo")
    
    # Create a temporary directory for the demo
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        logger.info(f"Created temporary directory: {base_dir}")
        
        # Create test files
        files = create_test_files(base_dir)
        logger.info(f"Created {len(files)} test files")
        
        # Run the demos
        demo_basic_transactions(base_dir, files)
        demo_nested_transactions(base_dir, files)
        demo_recovery_points(base_dir, files)
        demo_snapshot_types(base_dir, files)
        demo_error_handling(base_dir, files)
        
        # Clean up
        logger.info("\nCleaning up...")
    
    logger.info("Rollback Manager Demo completed")


if __name__ == "__main__":
    main()
