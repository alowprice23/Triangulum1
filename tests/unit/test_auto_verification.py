import pytest
import os
import json
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

from triangulum_lx.tooling.auto_verification import AutoVerifier
from triangulum_lx.core.fs_state import FileSystemStateCache

@pytest.fixture
def mock_fs_cache():
    """Fixture to provide a mocked FileSystemStateCache instance."""
    cache = MagicMock(spec=FileSystemStateCache)
    cache.exists.return_value = False # Default: file/dir does not exist
    cache.is_dir.return_value = False # Default: path is not a dir
    return cache

@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for tests."""
    project_dir = tmp_path / "auto_verify_project"
    project_dir.mkdir()
    # Create a dummy file for baseline creation
    (project_dir / "sample_file.py").write_text("def hello():\n  print('world')")
    return project_dir

@pytest.fixture
def auto_verifier_instance(temp_project_dir: Path, mock_fs_cache: MagicMock) -> AutoVerifier:
    """Fixture to create an AutoVerifier instance with mocks."""
    verification_subdir = temp_project_dir / ".verification"
    # Ensure that the exists check for verification_subdir itself returns false initially if we want to test its creation

    # Redefine side_effect for this specific test instance if needed for verification_dir creation
    def custom_exists_side_effect(path_str):
        if path_str == str(verification_subdir):
            return False # Simulate it not existing to test creation path
        return True # Other paths (like project_root/sample_file.py) exist

    mock_fs_cache.exists.side_effect = custom_exists_side_effect

    verifier = AutoVerifier(
        project_root=str(temp_project_dir),
        verification_dir=str(verification_subdir),
        fs_cache=mock_fs_cache
    )
    # Reset side_effect if it's too broad after init, or make it more specific
    mock_fs_cache.exists.side_effect = None
    mock_fs_cache.exists.return_value = True # Default to true for subsequent ops unless specified
    return verifier

class TestAutoVerifier:

    def test_init_creates_verification_dir(self, temp_project_dir: Path, mock_fs_cache: MagicMock):
        verification_subdir = temp_project_dir / ".verification_init_test"

        # Simulate verification_dir not existing
        mock_fs_cache.exists.return_value = False
        mock_fs_cache.is_dir.return_value = False # if exists is false, is_dir should also be false

        with patch('pathlib.Path.mkdir') as mock_mkdir:
            verifier = AutoVerifier(
                project_root=str(temp_project_dir),
                verification_dir=str(verification_subdir),
                fs_cache=mock_fs_cache
            )

        mock_fs_cache.exists.assert_called_with(str(verification_subdir))
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_fs_cache.invalidate.assert_called_with(str(verification_subdir))

    def test_create_baseline_atomic_write(self, auto_verifier_instance: AutoVerifier, temp_project_dir: Path, mock_fs_cache: MagicMock):
        """Test create_baseline uses atomic_write for baseline.json."""
        # Mock os.path.getsize and os.path.getmtime as they are called directly
        with patch('os.path.getsize', return_value=100), \
             patch('os.path.getmtime', return_value=time.time()), \
             patch('builtins.open', mock_open(read_data=b"file content")), \
             patch('triangulum_lx.tooling.auto_verification.atomic_write') as mock_atomic_write:

            # Mock fs_cache for files being baselined
            mock_fs_cache.exists.return_value = True # All files exist
            mock_fs_cache.is_file.return_value = True # All paths are files

            auto_verifier_instance.create_baseline(files=["sample_file.py"])

            expected_baseline_path = str(Path(auto_verifier_instance.verification_dir) / "baseline.json")

            # Verify atomic_write call
            found_call = False
            for call_args in mock_atomic_write.call_args_list:
                if call_args[0][0] == expected_baseline_path:
                    # Verify content (simplified check for now)
                    data = json.loads(call_args[0][1].decode('utf-8'))
                    assert "timestamp" in data
                    assert "sample_file.py" in data["files"]
                    found_call = True
                    break
            assert found_call, f"atomic_write not called for {expected_baseline_path}"
            mock_fs_cache.invalidate.assert_called_with(expected_baseline_path)

    def test_verify_fix_atomic_write(self, auto_verifier_instance: AutoVerifier, temp_project_dir: Path, mock_fs_cache: MagicMock):
        """Test verify_fix uses atomic_write for its result file."""
        fix_info = {"file": "sample_file.py", "line": 1, "description": "test fix"}

        # Mock dependent calls within verify_fix
        auto_verifier_instance.baseline_state = {"files":{}} # Ensure baseline exists
        with patch.object(auto_verifier_instance, '_verify_syntax', return_value=True), \
             patch.object(auto_verifier_instance, '_run_tests', return_value={"success": True}), \
             patch.object(auto_verifier_instance, '_check_for_regressions', return_value={"regressions_detected": False}), \
             patch('triangulum_lx.tooling.auto_verification.atomic_write') as mock_atomic_write:

            mock_fs_cache.exists.return_value = True # sample_file.py exists

            auto_verifier_instance.verify_fix(fix_info)

            # Verify atomic_write call (path is dynamic with result_id)
            assert mock_atomic_write.called
            written_path_str = mock_atomic_write.call_args[0][0]
            assert written_path_str.startswith(str(Path(auto_verifier_instance.verification_dir)))
            assert "verification_" in written_path_str
            assert written_path_str.endswith(".json")

            # Verify content (simplified)
            data = json.loads(mock_atomic_write.call_args[0][1].decode('utf-8'))
            assert data["fix_info"]["file"] == "sample_file.py"
            assert data["verified"] is True

            mock_fs_cache.invalidate.assert_called_with(written_path_str)

    # TODO: Add similar tests for:
    # - batch_verify_fixes
    # - create_regression_test (for test script and registry)
    # - run_regression_tests (for results file)
    # - export_verification_report

if __name__ == "__main__":
    pytest.main([__file__])
