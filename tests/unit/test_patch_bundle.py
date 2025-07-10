import pytest
import os
import tarfile
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from triangulum_lx.tooling.patch_bundle import PatchBundle, create_bundle, apply_bundle, revert_bundle
from triangulum_lx.core.fs_state import FileSystemStateCache # For spec in mock

# Helper to create a dummy repo root for tests
@pytest.fixture
def temp_repo_root(tmp_path: Path) -> Path:
    """Create a temporary directory to act as a repo root."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / "patches").mkdir() # Ensure 'patches' subdir exists where bundles are saved
    return repo_dir

@pytest.fixture
def mock_fs_cache():
    """Fixture to provide a mocked FileSystemStateCache instance."""
    return MagicMock(spec=FileSystemStateCache)

class TestPatchBundle:

    def test_create_bundle_atomic_operations(self, temp_repo_root: Path, mock_fs_cache: MagicMock):
        """Test that create() uses atomic_write for temp files and atomic_rename for the bundle."""
        bug_id = "BUG-001"
        patch_diff_content = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
        label = "test_label"

        bundle = PatchBundle(bug_id, patch_diff_content, repo_root=temp_repo_root, label=label, fs_cache=mock_fs_cache)

        with patch('triangulum_lx.tooling.patch_bundle.atomic_write') as mock_atomic_write, \
             patch('triangulum_lx.tooling.patch_bundle.atomic_rename') as mock_atomic_rename, \
             patch('tarfile.open') as mock_tarfile_open:

            # Mock tarfile context manager
            mock_tar = MagicMock()
            mock_tarfile_open.return_value.__enter__.return_value = mock_tar

            created_bundle_path = bundle.create()

            assert created_bundle_path is not None
            assert str(created_bundle_path).startswith(str(temp_repo_root / "patches"))
            assert str(created_bundle_path).endswith(".tar.gz")

            # Check atomic_write for patch.diff and manifest.json
            # Path objects for temp files are created inside bundle.create() using tempfile.TemporaryDirectory
            # So, we can't easily assert exact paths, but we can check calls.
            # We expect two calls to atomic_write for patch.diff and manifest.json
            # Their paths will be within a temporary directory.

            # Check atomic_write calls (content check is more robust than path)
            written_content_for_diff = None
            written_content_for_manifest = None

            for acall in mock_atomic_write.call_args_list:
                args, _ = acall
                written_data_bytes = args[1]
                if patch_diff_content.encode('utf-8') == written_data_bytes:
                    written_content_for_diff = written_data_bytes

                try: # Manifest content will be JSON
                    decoded_manifest = json.loads(written_data_bytes.decode('utf-8'))
                    if decoded_manifest.get("bug_id") == bug_id and decoded_manifest.get("patch_hash") == bundle.patch_hash:
                        written_content_for_manifest = written_data_bytes
                except json.JSONDecodeError:
                    pass

            assert written_content_for_diff is not None, "atomic_write was not called with patch_diff content"
            assert written_content_for_manifest is not None, "atomic_write was not called with manifest content"

            # Check tarfile.open (for the temporary tarball)
            # The first argument to tarfile.open will be the temporary tar path.
            assert str(mock_tarfile_open.call_args[0][0]).endswith(".tar.gz") # Convert Path to str

            # Check atomic_rename for moving temp tarball to final path
            mock_atomic_rename.assert_called_once()
            assert mock_atomic_rename.call_args[0][1] == str(created_bundle_path) # Target of rename

            # Check cache invalidation for the final bundle path
            mock_fs_cache.invalidate.assert_called_with(str(created_bundle_path))

    def test_apply_invalidates_cache(self, temp_repo_root: Path, mock_fs_cache: MagicMock):
        """Test that apply() calls _invalidate_cache_for_patch_files."""
        patch_diff = "--- a/file1.txt\n+++ b/file1.txt\n@@ -1 +1 @@\n-a\n+b\n"
        bundle = PatchBundle("BUG-002", patch_diff, repo_root=temp_repo_root, fs_cache=mock_fs_cache)

        # Mock subprocess.run for git apply
        mock_subproc_run = MagicMock()
        mock_subproc_run.return_value.returncode = 0

        with patch('subprocess.run', mock_subproc_run), \
             patch.object(bundle, '_invalidate_cache_for_patch_files') as mock_invalidate_helper:

            bundle.apply()
            mock_invalidate_helper.assert_called_once()

    def test_revert_invalidates_cache(self, temp_repo_root: Path, mock_fs_cache: MagicMock):
        """Test that revert() calls _invalidate_cache_for_patch_files."""
        patch_diff = "--- a/file1.txt\n+++ b/file1.txt\n@@ -1 +1 @@\n-a\n+b\n"
        bundle = PatchBundle("BUG-003", patch_diff, repo_root=temp_repo_root, fs_cache=mock_fs_cache)

        mock_subproc_run = MagicMock()
        mock_subproc_run.return_value.returncode = 0

        with patch('subprocess.run', mock_subproc_run), \
             patch.object(bundle, '_invalidate_cache_for_patch_files') as mock_invalidate_helper:

            bundle.revert()
            mock_invalidate_helper.assert_called_once()

    def test_invalidate_cache_for_patch_files_method(self, temp_repo_root: Path, mock_fs_cache: MagicMock):
        """Test the _invalidate_cache_for_patch_files method directly."""
        diff_content = (
            "--- a/path/to/file1.py\n"
            "+++ b/path/to/file1.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old_line\n"
            "+new_line\n"
            "--- a/another/file2.txt\n"
            "+++ b/another/file2.txt\n"
            "@@ -1,0 +1,1 @@\n"
            "+new content here\n"
            "--- a/dev/null\n" # Should be ignored
            "+++ b/some_new_file.json\n"
        )
        bundle = PatchBundle("BUG-004", diff_content, repo_root=temp_repo_root, fs_cache=mock_fs_cache)
        bundle._invalidate_cache_for_patch_files()

        expected_calls = [
            call(str((temp_repo_root / "path/to/file1.py").resolve())),
            call(str((temp_repo_root / "another/file2.txt").resolve())),
            call(str((temp_repo_root / "some_new_file.json").resolve())),
        ]
        mock_fs_cache.invalidate.assert_has_calls(expected_calls, any_order=True)
        # Check that /dev/null was not included
        for actual_call in mock_fs_cache.invalidate.call_args_list:
            assert "dev/null" not in actual_call[0][0]

        # Ensure it was called for the correct number of actual files
        # The set of affected files is 3 (file1.py, file2.txt, some_new_file.json)
        assert mock_fs_cache.invalidate.call_count == 3


# Basic tests for helper functions if needed, though they primarily use PatchBundle class
def test_create_bundle_calls_patch_bundle_create(tmp_path: Path, mock_fs_cache: MagicMock):
    with patch('triangulum_lx.tooling.patch_bundle.PatchBundle.create') as mock_pb_create, \
         patch('triangulum_lx.tooling.patch_bundle.PatchBundle.__init__') as mock_pb_init:
        mock_pb_init.return_value = None # PatchBundle __init__ returns None

        # Need to ensure the PatchBundle instance created *inside* create_bundle
        # uses the mock_fs_cache. This requires create_bundle to accept fs_cache.
        # For now, this test is limited.
        # A better way would be to mock PatchBundle class itself.

        patch_diff = "diff"
        bug_id = "BUG-H01"
        repo_root = str(tmp_path)

        # To properly test create_bundle passing fs_cache to PatchBundle,
        # create_bundle itself would need to accept fs_cache.
        # Let's assume for now it creates its own or gets one from a global context.
        # This test primarily checks if PatchBundle.create is called.

        create_bundle(patch_diff, bug_id, repo_root, label="test")
        mock_pb_create.assert_called_once()

# apply_bundle and revert_bundle mostly call PatchBundle.from_bundle and then apply/revert.
# Testing them would involve mocking PatchBundle.from_bundle and the instance methods.
# This is okay for now, as the core logic is in the PatchBundle class tests.

if __name__ == "__main__":
    pytest.main([__file__])
