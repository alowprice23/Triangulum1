"""
Enhanced Rollback Manager for Triangulum

Provides comprehensive, transaction-based rollback capabilities for multi-file changes,
supporting nested transactions, partial rollbacks, and persistent recovery points.
"""

import json
import subprocess
import pathlib
import hashlib
import time
import threading
import uuid
import tempfile
import datetime
import pickle
import io
import re
from typing import Dict, Any, Optional, List, Union, Set, Tuple, Callable, TypeVar, Generic
from enum import Enum, auto
from dataclasses import dataclass, field
from contextlib import contextmanager
import os
import shutil
import logging
import traceback

# Setup logging
logger = logging.getLogger("triangulum.rollback")

# Type definitions
T = TypeVar('T')
TransactionID = str
FileID = str
SnapshotID = str
RecoveryPointID = str


class RollbackError(Exception):
    """Base exception for rollback errors."""
    pass


class TransactionError(RollbackError):
    """Exception raised for transaction-related errors."""
    pass


class SnapshotError(RollbackError):
    """Exception raised for snapshot-related errors."""
    pass


class RecoveryError(RollbackError):
    """Exception raised for recovery-related errors."""
    pass


class TransactionState(Enum):
    """State of a transaction."""
    ACTIVE = auto()      # Transaction is active and changes can be made
    COMMITTED = auto()   # Transaction has been committed
    ROLLED_BACK = auto() # Transaction has been rolled back
    FAILED = auto()      # Transaction failed and needs cleanup


class SnapshotType(Enum):
    """Type of snapshot."""
    FULL = auto()        # Full snapshot of file content
    DIFF = auto()        # Diff-based snapshot
    METADATA = auto()    # Metadata-only snapshot


@dataclass
class FileSnapshot:
    """Snapshot of a file's state."""
    file_path: str
    snapshot_type: SnapshotType
    timestamp: float = field(default_factory=time.time)
    content: Optional[bytes] = None
    diff: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize derived fields after instance creation."""
        if self.content is not None and self.checksum is None:
            self.checksum = hashlib.sha256(self.content).hexdigest()
        
        if self.snapshot_type == SnapshotType.FULL and self.content is None:
            # Load content if not provided
            try:
                with open(self.file_path, 'rb') as f:
                    self.content = f.read()
                self.checksum = hashlib.sha256(self.content).hexdigest()
            except FileNotFoundError:
                # File doesn't exist, create an empty snapshot
                self.content = b''
                self.checksum = hashlib.sha256(b'').hexdigest()
                self.metadata['exists'] = False
            except Exception as e:
                logger.error(f"Error creating snapshot for {self.file_path}: {e}")
                raise SnapshotError(f"Failed to create snapshot: {e}")
    
    def restore(self) -> bool:
        """
        Restore the file to the state captured in this snapshot.
        
        Returns:
            bool: True if the restore was successful
        """
        try:
            if self.snapshot_type == SnapshotType.FULL:
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                
                # Write content back to file
                with open(self.file_path, 'wb') as f:
                    f.write(self.content)
                
                return True
            
            elif self.snapshot_type == SnapshotType.DIFF:
                if self.diff is None:
                    logger.error(f"No diff available for {self.file_path}")
                    return False
                
                # Apply reverse diff
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
                    temp.write(self.diff)
                    temp_path = temp.name
                
                try:
                    # Apply the reverse patch
                    apply_proc = subprocess.run(
                        ["git", "apply", "-R", temp_path],
                        text=True,
                        capture_output=True
                    )
                    
                    if apply_proc.returncode != 0:
                        logger.error(f"Failed to apply reverse diff: {apply_proc.stderr}")
                        return False
                    
                    return True
                finally:
                    # Clean up temp file
                    os.unlink(temp_path)
            
            elif self.snapshot_type == SnapshotType.METADATA:
                # Check if file should exist
                if not self.metadata.get('exists', True):
                    # File shouldn't exist, delete it if it does
                    if os.path.exists(self.file_path):
                        os.unlink(self.file_path)
                    return True
                
                # Restore metadata only
                if os.path.exists(self.file_path):
                    # Restore permissions
                    if 'mode' in self.metadata:
                        os.chmod(self.file_path, self.metadata['mode'])
                    
                    # Restore timestamps
                    if 'atime' in self.metadata and 'mtime' in self.metadata:
                        os.utime(self.file_path, (self.metadata['atime'], self.metadata['mtime']))
                    
                    return True
                
                return False
            
            return False
        
        except Exception as e:
            logger.error(f"Error restoring {self.file_path}: {e}")
            return False
    
    def verify(self) -> bool:
        """
        Verify that the file matches this snapshot.
        
        Returns:
            bool: True if the file matches the snapshot
        """
        if not os.path.exists(self.file_path):
            return not self.metadata.get('exists', True)
        
        if self.snapshot_type == SnapshotType.FULL and self.checksum:
            try:
                with open(self.file_path, 'rb') as f:
                    content = f.read()
                current_checksum = hashlib.sha256(content).hexdigest()
                return current_checksum == self.checksum
            except Exception as e:
                logger.error(f"Error verifying {self.file_path}: {e}")
                return False
        
        return True


@dataclass
class Transaction:
    """A transaction representing a group of related file changes."""
    id: TransactionID
    name: str
    parent_id: Optional[TransactionID] = None
    state: TransactionState = TransactionState.ACTIVE
    snapshots: Dict[str, FileSnapshot] = field(default_factory=dict)
    children: List[TransactionID] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    committed_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    
    def add_snapshot(self, snapshot: FileSnapshot) -> None:
        """
        Add a file snapshot to this transaction.
        
        Args:
            snapshot: The file snapshot to add
        """
        if self.state != TransactionState.ACTIVE:
            raise TransactionError(f"Cannot add snapshot to {self.state.name} transaction")
        
        self.snapshots[snapshot.file_path] = snapshot
    
    def commit(self) -> None:
        """Commit this transaction."""
        if self.state != TransactionState.ACTIVE:
            raise TransactionError(f"Cannot commit {self.state.name} transaction")
        
        self.state = TransactionState.COMMITTED
        self.committed_at = time.time()
    
    def rollback(self) -> bool:
        """
        Rollback this transaction.
        
        Returns:
            bool: True if the rollback was successful
        """
        if self.state == TransactionState.ROLLED_BACK:
            logger.warning(f"Transaction {self.id} already rolled back")
            return True
        
        if self.state == TransactionState.COMMITTED:
            logger.warning(f"Rolling back committed transaction {self.id}")
        
        # Rollback in reverse order of creation (LIFO)
        success = True
        for file_path, snapshot in sorted(
            self.snapshots.items(),
            key=lambda x: x[1].timestamp,
            reverse=True
        ):
            if not snapshot.restore():
                logger.error(f"Failed to restore {file_path}")
                success = False
        
        if success:
            self.state = TransactionState.ROLLED_BACK
            self.rolled_back_at = time.time()
        else:
            self.state = TransactionState.FAILED
        
        return success
    
    def get_affected_files(self) -> Set[str]:
        """
        Get the set of files affected by this transaction.
        
        Returns:
            Set of file paths
        """
        return set(self.snapshots.keys())


class TransactionManager:
    """
    Manager for transactions.
    
    This class manages the lifecycle of transactions, including creation,
    committing, and rolling back.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the transaction manager.
        
        Args:
            storage_dir: Directory to store transaction data
        """
        self.storage_dir = storage_dir or os.path.join(tempfile.gettempdir(), "triangulum_transactions")
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.active_transactions: Dict[TransactionID, Transaction] = {}
        self.transaction_history: Dict[TransactionID, Transaction] = {}
        
        # Transaction stack for nested transactions
        self.transaction_stack: List[TransactionID] = []
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Load existing transactions
        self._load_transactions()
    
    def _load_transactions(self) -> None:
        """Load existing transactions from storage."""
        try:
            transaction_dir = os.path.join(self.storage_dir, "transactions")
            if not os.path.exists(transaction_dir):
                os.makedirs(transaction_dir, exist_ok=True)
                return
            
            for filename in os.listdir(transaction_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(transaction_dir, filename), 'r') as f:
                            data = json.load(f)
                        
                        # Create transaction from data
                        transaction_id = data["id"]
                        transaction = Transaction(
                            id=transaction_id,
                            name=data["name"],
                            parent_id=data.get("parent_id"),
                            state=TransactionState[data["state"]],
                            children=data.get("children", []),
                            metadata=data.get("metadata", {}),
                            created_at=data["created_at"],
                            committed_at=data.get("committed_at"),
                            rolled_back_at=data.get("rolled_back_at")
                        )
                        
                        # Load snapshots
                        snapshot_dir = os.path.join(self.storage_dir, "snapshots", transaction_id)
                        if os.path.exists(snapshot_dir):
                            for snapshot_file in os.listdir(snapshot_dir):
                                if snapshot_file.endswith(".pickle"):
                                    try:
                                        with open(os.path.join(snapshot_dir, snapshot_file), 'rb') as f:
                                            snapshot = pickle.load(f)
                                        transaction.snapshots[snapshot.file_path] = snapshot
                                    except Exception as e:
                                        logger.error(f"Error loading snapshot {snapshot_file}: {e}")
                        
                        # Add to appropriate collection
                        if transaction.state == TransactionState.ACTIVE:
                            self.active_transactions[transaction_id] = transaction
                        else:
                            self.transaction_history[transaction_id] = transaction
                    
                    except Exception as e:
                        logger.error(f"Error loading transaction {filename}: {e}")
        
        except Exception as e:
            logger.error(f"Error loading transactions: {e}")
    
    def _save_transaction(self, transaction: Transaction) -> None:
        """
        Save a transaction to storage.
        
        Args:
            transaction: The transaction to save
        """
        try:
            # Create transaction directory
            transaction_dir = os.path.join(self.storage_dir, "transactions")
            os.makedirs(transaction_dir, exist_ok=True)
            
            # Save transaction metadata
            transaction_data = {
                "id": transaction.id,
                "name": transaction.name,
                "parent_id": transaction.parent_id,
                "state": transaction.state.name,
                "children": transaction.children,
                "metadata": transaction.metadata,
                "created_at": transaction.created_at,
                "committed_at": transaction.committed_at,
                "rolled_back_at": transaction.rolled_back_at
            }
            
            with open(os.path.join(transaction_dir, f"{transaction.id}.json"), 'w') as f:
                json.dump(transaction_data, f, indent=2)
            
            # Save snapshots
            snapshot_dir = os.path.join(self.storage_dir, "snapshots", transaction.id)
            os.makedirs(snapshot_dir, exist_ok=True)
            
            for file_path, snapshot in transaction.snapshots.items():
                # Create a safe filename
                safe_name = re.sub(r'[^\w\-_.]', '_', file_path)
                snapshot_path = os.path.join(snapshot_dir, f"{safe_name}.pickle")
                
                with open(snapshot_path, 'wb') as f:
                    pickle.dump(snapshot, f)
        
        except Exception as e:
            logger.error(f"Error saving transaction {transaction.id}: {e}")
            raise TransactionError(f"Failed to save transaction: {e}")
    
    def create_transaction(
        self,
        name: str,
        parent_id: Optional[TransactionID] = None
    ) -> Transaction:
        """
        Create a new transaction.
        
        Args:
            name: Name of the transaction
            parent_id: ID of the parent transaction for nested transactions
            
        Returns:
            The created transaction
        """
        with self.lock:
            # Generate a unique ID
            transaction_id = str(uuid.uuid4())
            
            # Determine parent ID
            if parent_id is None and self.transaction_stack:
                # Use the current transaction as parent if in a nested context
                parent_id = self.transaction_stack[-1]
            
            # Create the transaction
            transaction = Transaction(
                id=transaction_id,
                name=name,
                parent_id=parent_id
            )
            
            # Add to parent's children if applicable
            if parent_id and parent_id in self.active_transactions:
                parent = self.active_transactions[parent_id]
                parent.children.append(transaction_id)
                self._save_transaction(parent)
            
            # Add to active transactions
            self.active_transactions[transaction_id] = transaction
            
            # Save the transaction
            self._save_transaction(transaction)
            
            return transaction
    
    def get_transaction(self, transaction_id: TransactionID) -> Optional[Transaction]:
        """
        Get a transaction by ID.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            The transaction, or None if not found
        """
        with self.lock:
            return (
                self.active_transactions.get(transaction_id) or
                self.transaction_history.get(transaction_id)
            )
    
    def commit_transaction(self, transaction_id: TransactionID) -> bool:
        """
        Commit a transaction.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            bool: True if the commit was successful
        """
        with self.lock:
            transaction = self.active_transactions.get(transaction_id)
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found or not active")
                return False
            
            # Check if all children are committed
            for child_id in transaction.children:
                child = self.get_transaction(child_id)
                if child and child.state != TransactionState.COMMITTED:
                    logger.error(f"Cannot commit transaction with uncommitted child {child_id}")
                    return False
            
            # Commit the transaction
            transaction.commit()
            
            # Move to history
            del self.active_transactions[transaction_id]
            self.transaction_history[transaction_id] = transaction
            
            # Save the transaction
            self._save_transaction(transaction)
            
            # Remove from transaction stack if present
            if transaction_id in self.transaction_stack:
                self.transaction_stack.remove(transaction_id)
            
            return True
    
    def rollback_transaction(self, transaction_id: TransactionID) -> bool:
        """
        Rollback a transaction.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            bool: True if the rollback was successful
        """
        with self.lock:
            transaction = self.active_transactions.get(transaction_id)
            if not transaction:
                # Check history for committed transactions
                transaction = self.transaction_history.get(transaction_id)
                if not transaction:
                    logger.error(f"Transaction {transaction_id} not found")
                    return False
                
                if transaction.state == TransactionState.ROLLED_BACK:
                    logger.warning(f"Transaction {transaction_id} already rolled back")
                    return True
            
            # Rollback children first (in reverse order)
            for child_id in sorted(transaction.children, reverse=True):
                child = self.get_transaction(child_id)
                if child and child.state != TransactionState.ROLLED_BACK:
                    if not self.rollback_transaction(child_id):
                        logger.error(f"Failed to rollback child transaction {child_id}")
                        return False
            
            # Rollback the transaction
            success = transaction.rollback()
            
            # Update collections
            if transaction_id in self.active_transactions:
                del self.active_transactions[transaction_id]
            self.transaction_history[transaction_id] = transaction
            
            # Save the transaction
            self._save_transaction(transaction)
            
            # Remove from transaction stack if present
            if transaction_id in self.transaction_stack:
                self.transaction_stack.remove(transaction_id)
            
            return success
    
    def add_file_snapshot(
        self,
        transaction_id: TransactionID,
        file_path: str,
        snapshot_type: SnapshotType = SnapshotType.FULL
    ) -> Optional[FileSnapshot]:
        """
        Add a file snapshot to a transaction.
        
        Args:
            transaction_id: ID of the transaction
            file_path: Path to the file
            snapshot_type: Type of snapshot to create
            
        Returns:
            The created snapshot, or None if failed
        """
        with self.lock:
            transaction = self.active_transactions.get(transaction_id)
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found or not active")
                return None
            
            try:
                # Create the snapshot
                snapshot = FileSnapshot(
                    file_path=file_path,
                    snapshot_type=snapshot_type
                )
                
                # Add to transaction
                transaction.add_snapshot(snapshot)
                
                # Save the transaction
                self._save_transaction(transaction)
                
                return snapshot
            
            except Exception as e:
                logger.error(f"Error adding snapshot for {file_path}: {e}")
                return None
    
    def get_active_transactions(self) -> List[Transaction]:
        """
        Get all active transactions.
        
        Returns:
            List of active transactions
        """
        with self.lock:
            return list(self.active_transactions.values())
    
    def get_transaction_history(
        self,
        limit: Optional[int] = None,
        state_filter: Optional[TransactionState] = None
    ) -> List[Transaction]:
        """
        Get transaction history.
        
        Args:
            limit: Maximum number of transactions to return
            state_filter: Filter by transaction state
            
        Returns:
            List of transactions
        """
        with self.lock:
            transactions = list(self.transaction_history.values())
            
            # Apply state filter
            if state_filter:
                transactions = [t for t in transactions if t.state == state_filter]
            
            # Sort by creation time (newest first)
            transactions.sort(key=lambda t: t.created_at, reverse=True)
            
            # Apply limit
            if limit:
                transactions = transactions[:limit]
            
            return transactions
    
    def cleanup_old_transactions(self, days_old: int = 30) -> int:
        """
        Clean up old transactions.
        
        Args:
            days_old: Remove transactions older than this many days
            
        Returns:
            int: Number of transactions removed
        """
        with self.lock:
            cutoff = time.time() - (days_old * 24 * 60 * 60)
            to_remove = []
            
            for transaction_id, transaction in self.transaction_history.items():
                if transaction.created_at < cutoff:
                    to_remove.append(transaction_id)
            
            for transaction_id in to_remove:
                # Remove snapshot files
                snapshot_dir = os.path.join(self.storage_dir, "snapshots", transaction_id)
                if os.path.exists(snapshot_dir):
                    shutil.rmtree(snapshot_dir)
                
                # Remove transaction file
                transaction_file = os.path.join(self.storage_dir, "transactions", f"{transaction_id}.json")
                if os.path.exists(transaction_file):
                    os.unlink(transaction_file)
                
                # Remove from history
                del self.transaction_history[transaction_id]
            
            return len(to_remove)
    
    @contextmanager
    def transaction(self, name: str) -> Transaction:
        """
        Context manager for transactions.
        
        Args:
            name: Name of the transaction
            
        Yields:
            The created transaction
        """
        transaction = self.create_transaction(name)
        transaction_id = transaction.id
        
        # Add to transaction stack
        self.transaction_stack.append(transaction_id)
        
        try:
            yield transaction
            # Commit on successful exit
            self.commit_transaction(transaction_id)
        except Exception as e:
            # Rollback on exception
            logger.error(f"Transaction {name} failed: {e}")
            self.rollback_transaction(transaction_id)
            raise
    
    @contextmanager
    def nested_transaction(self, name: str) -> Transaction:
        """
        Context manager for nested transactions.
        
        Args:
            name: Name of the transaction
            
        Yields:
            The created transaction
        """
        if not self.transaction_stack:
            raise TransactionError("No active parent transaction for nested transaction")
        
        parent_id = self.transaction_stack[-1]
        transaction = self.create_transaction(name, parent_id=parent_id)
        transaction_id = transaction.id
        
        # Add to transaction stack
        self.transaction_stack.append(transaction_id)
        
        try:
            yield transaction
            # Commit on successful exit
            self.commit_transaction(transaction_id)
        except Exception as e:
            # Rollback on exception
            logger.error(f"Nested transaction {name} failed: {e}")
            self.rollback_transaction(transaction_id)
            raise


@dataclass
class RecoveryPoint:
    """A recovery point for restoring system state."""
    id: RecoveryPointID
    name: str
    transaction_ids: List[TransactionID]
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_affected_files(self, transaction_manager: TransactionManager) -> Set[str]:
        """
        Get all files affected by this recovery point.
        
        Args:
            transaction_manager: Transaction manager to use
            
        Returns:
            Set of file paths
        """
        affected_files = set()
        
        for transaction_id in self.transaction_ids:
            transaction = transaction_manager.get_transaction(transaction_id)
            if transaction:
                affected_files.update(transaction.get_affected_files())
        
        return affected_files


class RecoveryManager:
    """
    Manager for recovery points.
    
    This class manages recovery points, which are collections of transactions
    that can be rolled back together to restore system state.
    """
    
    def __init__(self, transaction_manager: TransactionManager, storage_dir: Optional[str] = None):
        """
        Initialize the recovery manager.
        
        Args:
            transaction_manager: Transaction manager to use
            storage_dir: Directory to store recovery point data
        """
        self.transaction_manager = transaction_manager
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(transaction_manager.storage_dir),
            "triangulum_recovery_points"
        )
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.recovery_points: Dict[RecoveryPointID, RecoveryPoint] = {}
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Load existing recovery points
        self._load_recovery_points()
    
    def _load_recovery_points(self) -> None:
        """Load existing recovery points from storage."""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.storage_dir, filename), 'r') as f:
                            data = json.load(f)
                        
                        # Create recovery point from data
                        recovery_point_id = data["id"]
                        recovery_point = RecoveryPoint(
                            id=recovery_point_id,
                            name=data["name"],
                            transaction_ids=data["transaction_ids"],
                            created_at=data["created_at"],
                            metadata=data.get("metadata", {})
                        )
                        
                        # Add to collection
                        self.recovery_points[recovery_point_id] = recovery_point
                    
                    except Exception as e:
                        logger.error(f"Error loading recovery point {filename}: {e}")
        
        except Exception as e:
            logger.error(f"Error loading recovery points: {e}")
    
    def _save_recovery_point(self, recovery_point: RecoveryPoint) -> None:
        """
        Save a recovery point to storage.
        
        Args:
            recovery_point: The recovery point to save
        """
        try:
            # Save recovery point data
            recovery_point_data = {
                "id": recovery_point.id,
                "name": recovery_point.name,
                "transaction_ids": recovery_point.transaction_ids,
                "created_at": recovery_point.created_at,
                "metadata": recovery_point.metadata
            }
            
            with open(os.path.join(self.storage_dir, f"{recovery_point.id}.json"), 'w') as f:
                json.dump(recovery_point_data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving recovery point {recovery_point.id}: {e}")
            raise RecoveryError(f"Failed to save recovery point: {e}")
    
    def create_recovery_point(
        self,
        name: str,
        transaction_ids: Optional[List[TransactionID]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RecoveryPoint:
        """
        Create a new recovery point.
        
        Args:
            name: Name of the recovery point
            transaction_ids: IDs of transactions to include
            metadata: Additional metadata for the recovery point
            
        Returns:
            The created recovery point
        """
        with self.lock:
            # Generate a unique ID
            recovery_point_id = str(uuid.uuid4())
            
            # Use active transactions if none specified
            if transaction_ids is None:
                transaction_ids = [
                    t.id for t in self.transaction_manager.get_active_transactions()
                ]
            
            # Create the recovery point
            recovery_point = RecoveryPoint(
                id=recovery_point_id,
                name=name,
                transaction_ids=transaction_ids,
                metadata=metadata or {}
            )
            
            # Add to collection
            self.recovery_points[recovery_point_id] = recovery_point
            
            # Save the recovery point
            self._save_recovery_point(recovery_point)
            
            return recovery_point
    
    def get_recovery_point(self, recovery_point_id: RecoveryPointID) -> Optional[RecoveryPoint]:
        """
        Get a recovery point by ID.
        
        Args:
            recovery_point_id: ID of the recovery point
            
        Returns:
            The recovery point, or None if not found
        """
        with self.lock:
            return self.recovery_points.get(recovery_point_id)
    
    def restore_recovery_point(self, recovery_point_id: RecoveryPointID) -> bool:
        """
        Restore system state to a recovery point.
        
        Args:
            recovery_point_id: ID of the recovery point
            
        Returns:
            bool: True if the restore was successful
        """
        with self.lock:
            recovery_point = self.recovery_points.get(recovery_point_id)
            if not recovery_point:
                logger.error(f"Recovery point {recovery_point_id} not found")
                return False
            
            # Rollback all transactions in reverse order of creation
            transactions = []
            for transaction_id in recovery_point.transaction_ids:
                transaction = self.transaction_manager.get_transaction(transaction_id)
                if transaction:
                    transactions.append(transaction)
            
            # Sort by creation time (newest first)
            transactions.sort(key=lambda t: t.created_at, reverse=True)
            
            # Rollback each transaction
            success = True
            for transaction in transactions:
                if not self.transaction_manager.rollback_transaction(transaction.id):
                    logger.error(f"Failed to rollback transaction {transaction.id}")
                    success = False
            
            return success
    
    def get_recovery_points(
        self,
        limit: Optional[int] = None
    ) -> List[RecoveryPoint]:
        """
        Get all recovery points.
        
        Args:
            limit: Maximum number of recovery points to return
            
        Returns:
            List of recovery points
        """
        with self.lock:
            recovery_points = list(self.recovery_points.values())
            
            # Sort by creation time (newest first)
            recovery_points.sort(key=lambda rp: rp.created_at, reverse=True)
            
            # Apply limit
            if limit:
                recovery_points = recovery_points[:limit]
            
            return recovery_points
    
    def delete_recovery_point(self, recovery_point_id: RecoveryPointID) -> bool:
        """
        Delete a recovery point.
        
        Args:
            recovery_point_id: ID of the recovery point
            
        Returns:
            bool: True if the recovery point was deleted
        """
        with self.lock:
            if recovery_point_id not in self.recovery_points:
                logger.error(f"Recovery point {recovery_point_id} not found")
                return False
            
            # Remove from collection
            del self.recovery_points[recovery_point_id]
            
            # Remove file
            recovery_point_file = os.path.join(self.storage_dir, f"{recovery_point_id}.json")
            if os.path.exists(recovery_point_file):
                os.unlink(recovery_point_file)
            
            return True
    
    def cleanup_old_recovery_points(self, days_old: int = 30) -> int:
        """
        Clean up old recovery points.
        
        Args:
            days_old: Remove recovery points older than this many days
            
        Returns:
            int: Number of recovery points removed
        """
        with self.lock:
            cutoff = time.time() - (days_old * 24 * 60 * 60)
            to_remove = []
            
            for recovery_point_id, recovery_point in self.recovery_points.items():
                if recovery_point.created_at < cutoff:
                    to_remove.append(recovery_point_id)
            
            for recovery_point_id in to_remove:
                self.delete_recovery_point(recovery_point_id)
            
            return len(to_remove)


class RollbackManager:
    """
    Enhanced rollback manager for Triangulum.
    
    This class provides a high-level interface for managing file changes
    with transaction support, snapshots, and recovery points.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the rollback manager.
        
        Args:
            storage_dir: Directory to store rollback data
        """
        self.storage_dir = storage_dir or os.path.join(tempfile.gettempdir(), "triangulum_rollback")
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Initialize transaction manager
        self.transaction_manager = TransactionManager(
            storage_dir=os.path.join(self.storage_dir, "transactions")
        )
        
        # Initialize recovery manager
        self.recovery_manager = RecoveryManager(
            transaction_manager=self.transaction_manager,
            storage_dir=os.path.join(self.storage_dir, "recovery_points")
        )
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
    @contextmanager
    def transaction(self, name: str) -> Transaction:
        """
        Context manager for transactions.
        
        Args:
            name: Name of the transaction
            
        Yields:
            The created transaction
        """
        with self.transaction_manager.transaction(name) as transaction:
            yield transaction
    
    @contextmanager
    def nested_transaction(self, name: str) -> Transaction:
        """
        Context manager for nested transactions.
        
        Args:
            name: Name of the transaction
            
        Yields:
            The created transaction
        """
        with self.transaction_manager.nested_transaction(name) as transaction:
            yield transaction
    
    def create_recovery_point(
        self,
        name: str,
        transaction_ids: Optional[List[TransactionID]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RecoveryPoint:
        """
        Create a new recovery point.
        
        Args:
            name: Name of the recovery point
            transaction_ids: IDs of transactions to include
            metadata: Additional metadata for the recovery point
            
        Returns:
            The created recovery point
        """
        return self.recovery_manager.create_recovery_point(
            name=name,
            transaction_ids=transaction_ids,
            metadata=metadata
        )
    
    def restore_recovery_point(self, recovery_point_id: RecoveryPointID) -> bool:
        """
        Restore system state to a recovery point.
        
        Args:
            recovery_point_id: ID of the recovery point
            
        Returns:
            bool: True if the restore was successful
        """
        return self.recovery_manager.restore_recovery_point(recovery_point_id)
    
    def add_file_snapshot(
        self,
        file_path: str,
        transaction_id: Optional[TransactionID] = None,
        snapshot_type: SnapshotType = SnapshotType.FULL
    ) -> Optional[FileSnapshot]:
        """
        Add a file snapshot to the current or specified transaction.
        
        Args:
            file_path: Path to the file
            transaction_id: ID of the transaction, or None for current
            snapshot_type: Type of snapshot to create
            
        Returns:
            The created snapshot, or None if failed
        """
        with self.lock:
            # Use current transaction if none specified
            if transaction_id is None:
                if not self.transaction_manager.transaction_stack:
                    logger.error("No active transaction")
                    return None
                
                transaction_id = self.transaction_manager.transaction_stack[-1]
            
            return self.transaction_manager.add_file_snapshot(
                transaction_id=transaction_id,
                file_path=file_path,
                snapshot_type=snapshot_type
            )
    
    def rollback_transaction(self, transaction_id: TransactionID) -> bool:
        """
        Rollback a transaction.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            bool: True if the rollback was successful
        """
        return self.transaction_manager.rollback_transaction(transaction_id)
    
    def get_active_transactions(self) -> List[Transaction]:
        """
        Get all active transactions.
        
        Returns:
            List of active transactions
        """
        return self.transaction_manager.get_active_transactions()
    
    def get_recovery_points(self, limit: Optional[int] = None) -> List[RecoveryPoint]:
        """
        Get all recovery points.
        
        Returns:
            List of recovery points
        """
        return self.recovery_manager.get_recovery_points(limit=limit)
    
    def cleanup(self, days_old: int = 30) -> Tuple[int, int]:
        """
        Clean up old transactions and recovery points.
        
        Args:
            days_old: Remove items older than this many days
            
        Returns:
            Tuple of (transactions_removed, recovery_points_removed)
        """
        transactions_removed = self.transaction_manager.cleanup_old_transactions(days_old)
        recovery_points_removed = self.recovery_manager.cleanup_old_recovery_points(days_old)
        
        return (transactions_removed, recovery_points_removed)


# Legacy API compatibility
def save_patch_record(bug_id: str, bundle_path: Union[str, pathlib.Path]) -> bool:
    """
    Save a record of a patch bundle for possible future rollback.
    
    Args:
        bug_id: Unique identifier for the bug
        bundle_path: Path to the patch bundle file
        
    Returns:
        bool: True if the record was saved successfully
    """
    logger.warning("Using legacy save_patch_record API, consider upgrading to RollbackManager")
    
    bundle_path = pathlib.Path(bundle_path)
    if not bundle_path.exists():
        logger.error(f"Bundle file does not exist: {bundle_path}")
        return False
    
    try:
        # Create a rollback manager
        manager = RollbackManager()
        
        # Create a transaction
        with manager.transaction(f"Legacy patch for bug {bug_id}") as transaction:
            # Store metadata about the bundle
            transaction.metadata["bug_id"] = bug_id
            transaction.metadata["bundle_path"] = str(bundle_path.absolute())
            
            # Extract the patch diff from the bundle
            extract_proc = subprocess.run(
                ["tar", "-xOf", str(bundle_path), "patch.diff"],
                text=True, 
                capture_output=True
            )
            
            if extract_proc.returncode != 0:
                logger.error(f"Failed to extract patch diff: {extract_proc.stderr}")
                return False
            
            patch_diff = extract_proc.stdout
            transaction.metadata["patch_diff"] = patch_diff
        
        # Create a recovery point
        manager.create_recovery_point(f"Legacy patch for bug {bug_id}")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to save patch record: {e}")
        return False


def rollback_patch(bug_id: str) -> bool:
    """
    Rollback a patch for a specific bug.
    
    Args:
        bug_id: Unique identifier for the bug
        
    Returns:
        bool: True if the rollback was successful
    """
    logger.warning("Using legacy rollback_patch API, consider upgrading to RollbackManager")
    
    try:
        # Create a rollback manager
        manager = RollbackManager()
        
        # Find recovery points with matching bug_id
        recovery_points = manager.get_recovery_points()
        matching_points = []
        
        for rp in recovery_points:
            for transaction_id in rp.transaction_ids:
                transaction = manager.transaction_manager.get_transaction(transaction_id)
                if transaction and transaction.metadata.get("bug_id") == bug_id:
                    matching_points.append(rp)
                    break
        
        if not matching_points:
            logger.error(f"No recovery point found for bug {bug_id}")
            return False
        
        # Use the most recent recovery point
        recovery_point = sorted(matching_points, key=lambda rp: rp.created_at, reverse=True)[0]
        
        # Restore the recovery point
        return manager.restore_recovery_point(recovery_point.id)
    
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False


def list_patches() -> List[Dict[str, Any]]:
    """
    List all patches that can be rolled back.
    
    Returns:
        List of patch records with bug_id and bundle_path
    """
    logger.warning("Using legacy list_patches API, consider upgrading to RollbackManager")
    
    try:
        # Create a rollback manager
        manager = RollbackManager()
        
        # Find transactions with bug_id metadata
        result = []
        
        for rp in manager.get_recovery_points():
            for transaction_id in rp.transaction_ids:
                transaction = manager.transaction_manager.get_transaction(transaction_id)
                if transaction and "bug_id" in transaction.metadata:
                    result.append({
                        "bug_id": transaction.metadata["bug_id"],
                        "bundle_path": transaction.metadata.get("bundle_path", "Unknown"),
                        "recovery_point_id": rp.id,
                        "created_at": transaction.created_at
                    })
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to list patches: {e}")
        return []


def clean_patches(days_old: int = 30) -> int:
    """
    Clean up old patch bundles that are no longer needed.
    
    Args:
        days_old: Remove bundles older than this many days
        
    Returns:
        int: Number of bundles removed
    """
    logger.warning("Using legacy clean_patches API, consider upgrading to RollbackManager")
    
    try:
        # Create a rollback manager
        manager = RollbackManager()
        
        # Clean up old transactions and recovery points
        transactions_removed, _ = manager.cleanup(days_old)
        
        return transactions_removed
    
    except Exception as e:
        logger.error(f"Failed to clean patches: {e}")
        return 0
