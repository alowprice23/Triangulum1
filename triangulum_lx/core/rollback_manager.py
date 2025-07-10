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

from pathlib import Path # Added import
from triangulum_lx.tooling.fs_ops import atomic_write, atomic_delete
from triangulum_lx.core.fs_state import FileSystemStateCache

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
                # Ensure directory exists (atomic_write handles this, but explicit doesn't hurt)
                Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
                
                atomic_write(self.file_path, self.content)
                # Caller (TransactionManager) should invalidate self.file_path from its cache
                
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
                    if Path(self.file_path).exists(): # Direct check, as cache is not available here
                        atomic_delete(self.file_path)
                        # Caller (TransactionManager) should invalidate self.file_path from its cache
                    return True
                
                # Restore metadata only
                if Path(self.file_path).exists(): # Direct check
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
        # The cache to be used for invalidation should be from the TransactionManager
        # This Transaction object itself doesn't have a cache.
        # This implies TransactionManager.rollback_transaction needs to handle invalidation.
        # For now, I cannot directly call self.fs_cache.invalidate here.
        # This will be handled by the TransactionManager after calling transaction.rollback().

        for file_path, snapshot in sorted(
            self.snapshots.items(),
            key=lambda x: x[1].timestamp,
            reverse=True
        ):
            if not snapshot.restore():
                logger.error(f"Failed to restore {file_path}")
                success = False
            # else:
            #    Caller (TransactionManager) must invalidate file_path from its cache.
        
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
    
    def __init__(self, storage_dir: Optional[str] = None, fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the transaction manager.
        
        Args:
            storage_dir: Directory to store transaction data
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.storage_dir_str = storage_dir or os.path.join(tempfile.gettempdir(), "triangulum_transactions")
        self.storage_dir = Path(self.storage_dir_str) # Work with Path object
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()

        if not self.fs_cache.exists(str(self.storage_dir)):
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.fs_cache.invalidate(str(self.storage_dir))
        elif not self.fs_cache.is_dir(str(self.storage_dir)):
            logger.warning(f"TransactionManager storage_dir {self.storage_dir} exists but is not a directory. Attempting to create.")
            self.storage_dir.mkdir(parents=True, exist_ok=True) # May fail
            self.fs_cache.invalidate(str(self.storage_dir))
        
        self.active_transactions: Dict[TransactionID, Transaction] = {}
        self.transaction_history: Dict[TransactionID, Transaction] = {}
        
        # Transaction stack for nested transactions
        self.transaction_stack: List[TransactionID] = []
        
        # Lock for thread safety
        self.lock = threading.RLock()
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
        # Load existing transactions
        self._load_transactions()
    
    def _load_transactions(self) -> None:
        """Load existing transactions from storage."""
        try:
            # Transaction JSON files are directly in self.storage_dir (which is now a Path object)
            if not self.fs_cache.exists(str(self.storage_dir)):
                logger.info(f"Transaction storage directory {self.storage_dir} does not exist. No transactions to load.")
                return # Nothing to load if the main directory isn't there
            if not self.fs_cache.is_dir(str(self.storage_dir)):
                logger.error(f"Transaction storage path {self.storage_dir} is not a directory. Cannot load transactions.")
                return

            filenames = self.fs_cache.listdir(str(self.storage_dir))
            if filenames is None:
                logger.warning(f"Could not list directory {self.storage_dir} using cache. Trying direct read.")
                if not self.storage_dir.is_dir(): # Check directly
                    logger.error(f"Path {self.storage_dir} is not a directory (direct check). Cannot load transactions.")
                    return
                try:
                    filenames = [f.name for f in self.storage_dir.iterdir() if f.is_file()] # Direct listdir
                except OSError as e:
                    logger.error(f"Failed to list directory {self.storage_dir} directly: {e}")
                    return

            for filename in filenames:
                if filename.endswith(".json"):
                    file_full_path = self.storage_dir / filename
                    try:
                        # Reading JSON, direct read is fine. Cache doesn't store content.
                        with open(file_full_path, 'r') as f:
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
                        if self.fs_cache.exists(snapshot_dir) and self.fs_cache.is_dir(snapshot_dir): # Use cache
                            snapshot_files = self.fs_cache.listdir(snapshot_dir)
                            if snapshot_files is None: # Should not happen if is_dir was true, but defensive
                                logger.warning(f"Could not list snapshot dir {snapshot_dir} via cache despite existing. Trying direct.")
                                try:
                                    snapshot_files = os.listdir(snapshot_dir)
                                except OSError as e:
                                    logger.error(f"Failed to list snapshot_dir {snapshot_dir} directly: {e}")
                                    snapshot_files = []

                            for snapshot_filename in snapshot_files:
                                if snapshot_filename.endswith(".pickle"):
                                    snapshot_full_path = os.path.join(snapshot_dir, snapshot_filename)
                                    try:
                                        # Reading pickle, direct read is fine.
                                        with open(snapshot_full_path, 'rb') as f:
                                            snapshot = pickle.load(f)
                                        transaction.snapshots[snapshot.file_path] = snapshot
                                    except Exception as e:
                                        logger.error(f"Error loading snapshot {snapshot_filename}: {e}")
                        elif self.fs_cache.exists(snapshot_dir) and not self.fs_cache.is_dir(snapshot_dir):
                            logger.error(f"Snapshot path {snapshot_dir} exists but is not a directory.")

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
            # self.storage_dir is already a Path object and its existence is ensured by __init__
            
            # Save transaction metadata directly into self.storage_dir
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
            
            transaction_file_path = self.storage_dir / f"{transaction.id}.json" # Use Path object
            transaction_content = json.dumps(transaction_data, indent=2)
            atomic_write(str(transaction_file_path), transaction_content.encode('utf-8'))
            self.fs_cache.invalidate(str(transaction_file_path))

            # Save snapshots into a "snapshots" subdirectory of self.storage_dir
            snapshot_base_dir = self.storage_dir / "snapshots"
            # No need to create transaction_dir, snapshots go under snapshot_base_dir / transaction.id

            snapshot_specific_dir = snapshot_base_dir / transaction.id
            # Ensure snapshot_specific_dir exists.
            if not self.fs_cache.exists(str(snapshot_specific_dir)):
                 snapshot_specific_dir.mkdir(parents=True, exist_ok=True)
                 self.fs_cache.invalidate(str(snapshot_specific_dir))
            elif not self.fs_cache.is_dir(str(snapshot_specific_dir)):
                 logger.error(f"Snapshot storage path {snapshot_specific_dir} exists but is not a directory. Attempting to recreate.")
                 snapshot_specific_dir.mkdir(parents=True, exist_ok=True) # This might fail if it's a file
                 self.fs_cache.invalidate(str(snapshot_specific_dir))

            for file_path, snapshot in transaction.snapshots.items():
                # Create a safe filename
                safe_name = re.sub(r'[^\w\-_.]', '_', Path(file_path).name) # Use Path(file_path).name for safety
                snapshot_filename_path = snapshot_specific_dir / f"{safe_name}.pickle"
                
                snapshot_content_bytes = pickle.dumps(snapshot)
                atomic_write(str(snapshot_filename_path), snapshot_content_bytes)
                self.fs_cache.invalidate(str(snapshot_filename_path))
        
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
            rollback_successful = transaction.rollback()
            
            if rollback_successful:
                # Invalidate all affected files from cache
                for file_path in transaction.snapshots.keys():
                    self.fs_cache.invalidate(file_path)
                logger.debug(f"Invalidated cached files for rolled back transaction {transaction_id}")

            # Update collections
            if transaction_id in self.active_transactions:
                del self.active_transactions[transaction_id]
            self.transaction_history[transaction_id] = transaction # Keep history, state is ROLLED_BACK or FAILED
            
            # Save the transaction (its state has changed)
            self._save_transaction(transaction)
            
            # Remove from transaction stack if present
            if transaction_id in self.transaction_stack:
                self.transaction_stack.remove(transaction_id)
            
            return rollback_successful
    
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
                # Remove snapshot files and directory
                # self.storage_dir is already a Path object
                snapshot_dir_path = self.storage_dir / "snapshots" / transaction_id
                if self.fs_cache.exists(str(snapshot_dir_path)) and self.fs_cache.is_dir(str(snapshot_dir_path)):
                    # Invalidate cache for all children before attempting deletion
                    # This is a simplistic approach for recursive invalidation here.
                    # A more robust way would be to list recursively and invalidate.
                    # For now, invalidate the main dir, assuming children are handled by ops.

                    paths_to_delete_in_order: List[Tuple[str, bool]] = [] # (path, is_dir)
                    for root, dirs, files in os.walk(snapshot_dir_path, topdown=False):
                        for name in files:
                            paths_to_delete_in_order.append((os.path.join(root, name), False))
                        for name in dirs:
                            paths_to_delete_in_order.append((os.path.join(root, name), True))

                    for item_path_str, is_dir in paths_to_delete_in_order:
                        self.fs_cache.invalidate(item_path_str) # Invalidate before op
                        if is_dir:
                            try:
                                os.rmdir(item_path_str)
                                logger.debug(f"Removed directory during cleanup: {item_path_str}")
                            except OSError as e:
                                logger.error(f"Error removing directory {item_path_str} during cleanup: {e}")
                        else:
                            atomic_delete(item_path_str) # atomic_delete will invalidate its own path
                            logger.debug(f"Deleted file during cleanup: {item_path_str}")

                    # Final attempt to remove the top snapshot_dir if it's now empty
                    try:
                        os.rmdir(snapshot_dir_path)
                        self.fs_cache.invalidate(snapshot_dir_path)
                        logger.debug(f"Removed top snapshot directory: {snapshot_dir_path}")
                    except OSError as e:
                        logger.error(f"Error removing top snapshot directory {snapshot_dir_path}: {e}. It might not be empty.")

                elif self.fs_cache.exists(snapshot_dir_path): # Exists but not a dir
                     logger.warning(f"Expected {snapshot_dir_path} to be a directory for cleanup, but it's not. Skipping rmtree-like part.")

                # Remove transaction file
                transaction_file_path = self.storage_dir / f"{transaction_id}.json" # Corrected path
                if self.fs_cache.exists(str(transaction_file_path)): # Use cache
                    atomic_delete(str(transaction_file_path))
                    # fs_cache.invalidate is called by atomic_delete
                
                # Remove from history
                if transaction_id in self.transaction_history: # Check before deleting
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
    
    def __init__(self, transaction_manager: TransactionManager, storage_dir: Optional[str] = None, fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the recovery manager.
        
        Args:
            transaction_manager: Transaction manager to use
            storage_dir: Directory to store recovery point data
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.transaction_manager = transaction_manager
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(transaction_manager.storage_dir), # Relies on transaction_manager's storage_dir
            "triangulum_recovery_points"
        )
        os.makedirs(self.storage_dir, exist_ok=True) # Direct makedirs for setup
        
        self.recovery_points: Dict[RecoveryPointID, RecoveryPoint] = {}
        
        # Lock for thread safety
        self.lock = threading.RLock()
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()
        
        # Load existing recovery points
        self._load_recovery_points()
    
    def _load_recovery_points(self) -> None:
        """Load existing recovery points from storage."""
        try:
            # self.storage_dir is already a Path object
            filenames = self.fs_cache.listdir(str(self.storage_dir))
            if filenames is None:
                logger.warning(f"Could not list recovery_points dir {self.storage_dir} via cache. Trying direct.")
                if not self.storage_dir.is_dir():
                    logger.error(f"Recovery points storage path {self.storage_dir} is not a directory.")
                    return
                try:
                    filenames = [f.name for f in self.storage_dir.iterdir() if f.is_file()]
                except OSError as e:
                    logger.error(f"Failed to list directory {self.storage_dir} directly: {e}")
                    return

            for filename in filenames:
                if filename.endswith(".json"):
                    file_full_path = self.storage_dir / filename
                    try:
                        # Direct read for JSON content
                        with open(file_full_path, 'r') as f:
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
            
            recovery_point_file_path = os.path.join(self.storage_dir, f"{recovery_point.id}.json")
            content = json.dumps(recovery_point_data, indent=2)
            atomic_write(recovery_point_file_path, content.encode('utf-8'))
            self.fs_cache.invalidate(recovery_point_file_path)
        
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
            recovery_point_file_path_obj = self.storage_dir / f"{recovery_point_id}.json" # Use Path obj
            recovery_point_file_path_str = str(recovery_point_file_path_obj)

            if self.fs_cache.exists(recovery_point_file_path_str): # Use cache
                atomic_delete(recovery_point_file_path_str)
                # fs_cache.invalidate is called by atomic_delete
            elif recovery_point_file_path_obj.exists(): # Direct check if cache says no but it's there
                logger.warning(f"Cache said {recovery_point_file_path_str} absent, but it exists. Deleting.")
                atomic_delete(recovery_point_file_path_str)
                # fs_cache.invalidate is called by atomic_delete

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
    
    def __init__(self, storage_dir: Optional[str] = None, fs_cache: Optional[FileSystemStateCache] = None):
        """
        Initialize the rollback manager.
        
        Args:
            storage_dir: Directory to store rollback data
            fs_cache: Optional FileSystemStateCache instance.
        """
        self.storage_dir = storage_dir or os.path.join(tempfile.gettempdir(), "triangulum_rollback")
        os.makedirs(self.storage_dir, exist_ok=True) # Direct makedirs for setup
        
        # Create or use provided fs_cache and pass it down
        self.fs_cache = fs_cache if fs_cache is not None else FileSystemStateCache()

        # Initialize transaction manager
        self.transaction_manager = TransactionManager(
            storage_dir=os.path.join(self.storage_dir, "transactions"),
            fs_cache=self.fs_cache
        )
        
        # Initialize recovery manager
        self.recovery_manager = RecoveryManager(
            transaction_manager=self.transaction_manager,
            storage_dir=os.path.join(self.storage_dir, "recovery_points"),
            fs_cache=self.fs_cache
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
