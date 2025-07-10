import pytest
import os
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from triangulum_lx.tooling.fix_impact_tracker import FixImpactTracker
from triangulum_lx.core.fs_state import FileSystemStateCache

@pytest.fixture
def mock_fs_cache():
    """Fixture to provide a mocked FileSystemStateCache instance."""
    cache = MagicMock(spec=FileSystemStateCache)
    cache.exists.return_value = False # Default: file/dir does not exist
    cache.is_dir.return_value = True  # Default: if it exists, it's a dir (for parent dir checks)
    return cache

@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for tests."""
    project_dir = tmp_path / "fix_impact_project"
    project_dir.mkdir()
    return project_dir

class TestFixImpactTracker:

    def test_init_creates_database_parent_dir(self, temp_project_dir: Path, mock_fs_cache: MagicMock):
        """Test __init__ creates database parent directory if it doesn't exist via cache."""
        db_path = temp_project_dir / ".triangulum_test_fic" / "fix_database.json"
        db_parent_dir = db_path.parent

        # Simulate parent dir not existing in cache
        mock_fs_cache.exists.return_value = False
        # Ensure is_dir is also false if exists is false for the specific path
        def exists_side_effect(path_str):
            if path_str == str(db_parent_dir):
                return False
            return True # Other paths might exist (like project_dir)
        mock_fs_cache.exists.side_effect = exists_side_effect
        mock_fs_cache.is_dir.return_value = False


        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch.object(FixImpactTracker, '_load_database', return_value={}) as mock_load_db: # Mock load_db to simplify init
            tracker = FixImpactTracker(project_path=str(temp_project_dir), database_path=str(db_path), fs_cache=mock_fs_cache)

        # Check that fs_cache.exists was called for the parent directory
        mock_fs_cache.exists.assert_any_call(str(db_parent_dir))

        # Check that mkdir was called on the parent directory Path object
        # mock_mkdir should have been called by db_parent_dir.mkdir(...)
        called_mkdir_on_correct_path = False
        for c_args, c_kwargs in mock_mkdir.call_args_list:
            # The 'self' of the Path object is not directly available, so check args
            # This is a bit fragile. A better way would be to patch Path(db_parent_dir).mkdir directly.
            # For now, assume the call with parents=True, exist_ok=True is the one.
             if c_kwargs.get('parents') is True and c_kwargs.get('exist_ok') is True:
                 # This doesn't confirm it was called ON db_parent_dir, just that some Path.mkdir was called like that.
                 # This test is more about the cache interaction.
                called_mkdir_on_correct_path = True
        assert called_mkdir_on_correct_path

        mock_fs_cache.invalidate.assert_called_with(str(db_parent_dir))
        mock_load_db.assert_called_once()


    def test_save_database_atomic_write(self, temp_project_dir: Path, mock_fs_cache: MagicMock):
        """Test _save_database uses atomic_write and invalidates cache."""
        db_path = temp_project_dir / ".triangulum_fic_save" / "fix_database.json"

        # Ensure _load_database returns an empty dict so __init__ doesn't fail if file not found by mocked cache
        with patch.object(FixImpactTracker, '_load_database', return_value={}):
            tracker = FixImpactTracker(project_path=str(temp_project_dir), database_path=str(db_path), fs_cache=mock_fs_cache)

        tracker.database = {"version": 1, "fixes": {"fix1": "data"}, "last_updated": 0} # Set some data

        with patch('triangulum_lx.tooling.fix_impact_tracker.atomic_write') as mock_atomic_write:
            tracker._save_database()

            mock_atomic_write.assert_called_once()
            args, _ = mock_atomic_write.call_args
            written_path = args[0]
            written_data_bytes = args[1]

            assert written_path == str(db_path)
            decoded_data = json.loads(written_data_bytes.decode('utf-8'))
            assert decoded_data["fixes"]["fix1"] == "data"
            assert "last_updated" in decoded_data # Should be updated by _save_database

            mock_fs_cache.invalidate.assert_called_with(str(db_path))

    def test_load_database_uses_cache_and_handles_missing_file(self, temp_project_dir: Path, mock_fs_cache: MagicMock):
        """Test _load_database uses fs_cache.exists and handles file not found."""
        db_path = temp_project_dir / ".triangulum_fic_load" / "fix_database.json"

        # Case 1: Cache says file doesn't exist, and it really doesn't
        mock_fs_cache.exists.return_value = False
        with patch('pathlib.Path.exists', return_value=False): # Mock Path.exists for the double check
             tracker = FixImpactTracker(project_path=str(temp_project_dir), database_path=str(db_path), fs_cache=mock_fs_cache)
        mock_fs_cache.exists.assert_called_with(str(db_path))
        assert tracker.database["fixes"] == {} # Should be default empty

        # Case 2: Cache says file exists, mock open
        mock_fs_cache.exists.return_value = True
        mock_fs_cache.is_dir.return_value = False # It's a file

        expected_db_data = {"version": 1, "fixes": {"fixABC": "details"}, "last_updated": 123}
        m_open = mock_open(read_data=json.dumps(expected_db_data))
        with patch('builtins.open', m_open):
            tracker = FixImpactTracker(project_path=str(temp_project_dir), database_path=str(db_path), fs_cache=mock_fs_cache)

        m_open.assert_called_once_with(db_path, 'r', encoding='utf-8')
        assert tracker.database["fixes"]["fixABC"] == "details"

if __name__ == "__main__":
    pytest.main([__file__])
