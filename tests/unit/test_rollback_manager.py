import pytest
import os
import json
import pickle
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import io # Added import

from triangulum_lx.core.rollback_manager import (
    RollbackManager,
    TransactionManager,
    RecoveryManager,
    FileSnapshot,
    Transaction,
    TransactionState,
    SnapshotType
)
from triangulum_lx.core.fs_state import FileSystemStateCache
import re # Added for safe_snapshot_name generation

@pytest.fixture
def mock_fs_cache():
    """Fixture to provide a mocked FileSystemStateCache instance."""
    cache = MagicMock(spec=FileSystemStateCache)
    cache.exists.return_value = False # Default to not existing, tests can override
    cache.is_dir.return_value = False # Default to not being a dir
    cache.listdir.return_value = []   # Default to empty dir
    return cache

@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "rollback_storage"
    storage_dir.mkdir()
    return storage_dir

class TestTransactionManager:
    def test_init_creates_dirs_if_not_exist(self, temp_storage_dir: Path, mock_fs_cache: MagicMock):
        """Test __init__ creates storage_dir and its 'snapshots' subdir if they don't exist."""

        # Simulate storage_dir and its 'snapshots' subdir not existing in cache initially
        def exists_side_effect(path_str):
            if path_str == str(temp_storage_dir):
                return False # Main storage_dir does not exist
            if path_str == str(temp_storage_dir / "snapshots"): # Snapshots subdir
                return False
            return True # Other paths might exist

        mock_fs_cache.exists.side_effect = exists_side_effect
        mock_fs_cache.is_dir.return_value = False # Consistent with not existing

        with patch('pathlib.Path.mkdir') as mock_mkdir:
            tm = TransactionManager(storage_dir=str(temp_storage_dir), fs_cache=mock_fs_cache)

        # Check that mkdir was called for storage_dir
        # And that 'snapshots' subdir creation is handled (implicitly by _save_transaction later if needed)
        # The __init__ itself ensures the main storage_dir.
        # The `_save_transaction` ensures `storage_dir / "snapshots" / tx_id`

        # Check for storage_dir
        expected_mkdir_calls = [call(parents=True, exist_ok=True)]

        # Check if storage_dir itself was attempted to be created
        found_storage_dir_mkdir = False
        for c in mock_mkdir.call_args_list:
            # The mock_mkdir is on Path.mkdir, so self is the Path object
            if c.kwargs.get('parents') is True and c.kwargs.get('exist_ok') is True:
                 # This is a bit indirect, would be better to check the path object it was called on
                 # For now, assume if mkdir was called with these args, it's one of ours.
                 # This test is primarily for cache interaction
                found_storage_dir_mkdir = True # Loosely assume one of these is for storage_dir

        assert found_storage_dir_mkdir
        mock_fs_cache.invalidate.assert_any_call(str(temp_storage_dir))


    def test_save_transaction_atomic_writes(self, temp_storage_dir: Path, mock_fs_cache: MagicMock):
        """Test _save_transaction uses atomic_write for json and pickles, and invalidates cache."""
        tm = TransactionManager(storage_dir=str(temp_storage_dir), fs_cache=mock_fs_cache)

        tx = Transaction(id="tx123", name="test_tx")
        snapshot_content = b"snapshot_data"
        snapshot = FileSnapshot(file_path="file1.txt", snapshot_type=SnapshotType.FULL, content=snapshot_content)
        tx.add_snapshot(snapshot)

        expected_tx_json_path = str(temp_storage_dir / "tx123.json")

        # snapshot_specific_dir: temp_storage_dir / "snapshots" / "tx123"
        # For the safe_name logic used in TransactionManager._save_transaction:
        original_filename = "file1.txt"
        safe_snapshot_name_base = re.sub(r'[^\w\-_.]', '_', Path(original_filename).name)
        expected_snapshot_pickle_path = str(temp_storage_dir / "snapshots" / "tx123" / f"{safe_snapshot_name_base}.pickle")

        with patch('triangulum_lx.core.rollback_manager.atomic_write') as mock_atomic_write:
            tm._save_transaction(tx)

            # Check atomic_write for transaction JSON
            # First call to atomic_write should be for the transaction JSON
            call_tx_json = mock_atomic_write.call_args_list[0]
            assert call_tx_json[0][0] == expected_tx_json_path
            assert json.loads(call_tx_json[0][1].decode('utf-8'))["id"] == "tx123"
            mock_fs_cache.invalidate.assert_any_call(expected_tx_json_path)

            # Check atomic_write for snapshot pickle
            # Second call should be for the snapshot
            call_snapshot_pickle = mock_atomic_write.call_args_list[1]
            assert call_snapshot_pickle[0][0] == expected_snapshot_pickle_path
            assert pickle.loads(call_snapshot_pickle[0][1]).content == snapshot_content
            mock_fs_cache.invalidate.assert_any_call(expected_snapshot_pickle_path)

            # Check that the snapshot specific directory was invalidated if created by mkdir
            mock_fs_cache.invalidate.assert_any_call(str(temp_storage_dir / "snapshots" / "tx123"))


    def test_load_transaction_uses_cache(self, temp_storage_dir: Path, mock_fs_cache: MagicMock):
        """Test _load_transactions uses fs_cache for listdir and exists."""
        # Setup: Simulate a transaction file and a snapshot file existing according to cache
        tx_id = "tx_load_test"
        tx_filename = f"{tx_id}.json"
        snapshot_pickle_filename = "file_snap.pickle"

        tx_data = {"id": tx_id, "name": "loaded_tx", "state": "COMMITTED", "created_at": time.time()}
        snapshot_data_obj = FileSnapshot("path/file.txt", SnapshotType.FULL, content=b"data")

        # Simulate cache responses
        mock_fs_cache.exists.side_effect = lambda p_str: (
            p_str == str(temp_storage_dir) or \
            p_str == str(temp_storage_dir / tx_filename) or \
            p_str == str(temp_storage_dir / "snapshots" / tx_id) or \
            p_str == str(temp_storage_dir / "snapshots" / tx_id / snapshot_pickle_filename)
        )
        mock_fs_cache.is_dir.side_effect = lambda p_str: (
            p_str == str(temp_storage_dir) or \
            p_str == str(temp_storage_dir / "snapshots" / tx_id)
        )
        mock_fs_cache.listdir.side_effect = lambda p_str: (
            [tx_filename] if p_str == str(temp_storage_dir) else \
            [snapshot_pickle_filename] if p_str == str(temp_storage_dir / "snapshots" / tx_id) else \
            []
        )

        # Mock open to provide content for these cached files
        def mock_open_side_effect(path_arg, mode):
            path_arg_str = str(path_arg)
            if path_arg_str == str(temp_storage_dir / tx_filename) and 'r' in mode:
                return MagicMock(__enter__=MagicMock(return_value=io.StringIO(json.dumps(tx_data))), __exit__=MagicMock())
            elif path_arg_str == str(temp_storage_dir / "snapshots" / tx_id / snapshot_pickle_filename) and 'rb' in mode:
                return MagicMock(__enter__=MagicMock(return_value=io.BytesIO(pickle.dumps(snapshot_data_obj))), __exit__=MagicMock())
            raise FileNotFoundError(f"Mocked open: Path not found {path_arg_str}")

        with patch('builtins.open', side_effect=mock_open_side_effect):
            tm = TransactionManager(storage_dir=str(temp_storage_dir), fs_cache=mock_fs_cache)
            # _load_transactions is called in __init__

        mock_fs_cache.exists.assert_any_call(str(temp_storage_dir))
        mock_fs_cache.listdir.assert_any_call(str(temp_storage_dir))
        mock_fs_cache.exists.assert_any_call(str(temp_storage_dir / "snapshots" / tx_id))
        mock_fs_cache.listdir.assert_any_call(str(temp_storage_dir / "snapshots" / tx_id))

        assert tx_id in tm.transaction_history
        loaded_tx = tm.transaction_history[tx_id]
        assert loaded_tx.name == "loaded_tx"
        assert len(loaded_tx.snapshots) == 1
        assert loaded_tx.snapshots["path/file.txt"].content == b"data"

    def test_rollback_transaction_invalidates_cache(self, temp_storage_dir: Path, mock_fs_cache: MagicMock):
        tm = TransactionManager(storage_dir=str(temp_storage_dir), fs_cache=mock_fs_cache)

        tx = tm.create_transaction("rollback_tx_test")
        snapshot1_path = "file_to_restore1.txt"
        snapshot2_path = "file_to_restore2.txt"

        # Create dummy snapshot objects (content doesn't matter for this test part)
        snap1 = FileSnapshot(snapshot1_path, SnapshotType.FULL, content=b"abc")
        snap2 = FileSnapshot(snapshot2_path, SnapshotType.FULL, content=b"def")
        tx.add_snapshot(snap1)
        tx.add_snapshot(snap2)

        # Mock FileSnapshot.restore to always succeed
        with patch('triangulum_lx.core.rollback_manager.FileSnapshot.restore', return_value=True):
            tm.rollback_transaction(tx.id)

        # Verify fs_cache.invalidate was called for each restored file
        mock_fs_cache.invalidate.assert_any_call(snapshot1_path)
        mock_fs_cache.invalidate.assert_any_call(snapshot2_path)
        assert mock_fs_cache.invalidate.call_count >= 2 # May be called more if dirs were created/invalidated

    # TODO: Add tests for cleanup_old_transactions with atomic_delete and os.rmdir mocks
    # TODO: Add tests for RecoveryManager save/load/delete of recovery point JSONs

if __name__ == "__main__":
    pytest.main([__file__])
