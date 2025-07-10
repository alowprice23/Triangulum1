import pytest
import os
import shutil
import time
import threading
import multiprocessing
import logging
from pathlib import Path

from triangulum_lx.tooling import fs_ops

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_TEST_DIR = Path("test_fs_ops_temp_dir")


@pytest.fixture(scope="function", autouse=True)
def manage_test_directory():
    """Create and clean up the base test directory for each test function."""
    if BASE_TEST_DIR.exists():
        shutil.rmtree(BASE_TEST_DIR)
    BASE_TEST_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Created test directory: {BASE_TEST_DIR.resolve()}")
    yield
    try:
        shutil.rmtree(BASE_TEST_DIR)
        logger.debug(f"Cleaned up test directory: {BASE_TEST_DIR.resolve()}")
    except Exception as e:
        logger.error(f"Error cleaning up test directory {BASE_TEST_DIR.resolve()}: {e}")


def test_atomic_write_creates_file_with_content_fallback():
    """Test basic atomic_write functionality using the fallback tempfile+rename method."""
    test_file = BASE_TEST_DIR / "test_write_fallback.txt"
    data = b"Fallback test data"
    fs_ops.atomic_write(str(test_file), data, use_otmpfile_if_available=False)
    assert test_file.exists()
    with open(test_file, "rb") as f:
        assert f.read() == data

def test_atomic_write_creates_file_with_content_otmpfile_if_supported():
    """Test basic atomic_write functionality using O_TMPFILE if supported."""
    test_file = BASE_TEST_DIR / "test_write_otmp.txt"
    data = b"O_TMPFILE test data"

    # O_TMPFILE is Linux specific and needs kernel >= 3.11 and supporting FS
    # This test will try O_TMPFILE and gracefully fall back if not supported.
    # The goal is to ensure it works, not to force O_TMPFILE if unavailable.
    try:
        fs_ops.atomic_write(str(test_file), data, use_otmpfile_if_available=True)
        assert test_file.exists()
        with open(test_file, "rb") as f:
            content = f.read()
        assert content == data
        logger.info(f"O_TMPFILE test succeeded for {test_file}")
    except OSError as e:
        # This might happen if O_TMPFILE is tried but fails, and fallback also fails for some reason.
        # Or if there's a genuine problem with the fallback mechanism itself.
        pytest.fail(f"atomic_write (O_TMPFILE or fallback) failed: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during O_TMPFILE test: {e}")


def test_atomic_write_subdirectory_creation():
    """Test atomic_write creates necessary subdirectories."""
    test_file = BASE_TEST_DIR / "sub" / "test_write_subdir.txt"
    data = b"Subdirectory test"
    fs_ops.atomic_write(str(test_file), data)
    assert test_file.exists()
    with open(test_file, "rb") as f:
        assert f.read() == data

def test_atomic_write_overwrite_existing_file():
    """Test atomic_write correctly overwrites an existing file."""
    test_file = BASE_TEST_DIR / "test_overwrite.txt"
    initial_data = b"Initial data"
    new_data = b"New overwritten data"

    fs_ops.atomic_write(str(test_file), initial_data, use_otmpfile_if_available=False) # Fallback for predictability
    assert test_file.exists()
    with open(test_file, "rb") as f:
        assert f.read() == initial_data

    fs_ops.atomic_write(str(test_file), new_data, use_otmpfile_if_available=False) # Fallback
    assert test_file.exists()
    with open(test_file, "rb") as f:
        assert f.read() == new_data

    # Try with O_TMPFILE if available
    fs_ops.atomic_write(str(test_file), initial_data, use_otmpfile_if_available=True)
    assert test_file.exists()
    with open(test_file, "rb") as f:
        assert f.read() == initial_data

    fs_ops.atomic_write(str(test_file), new_data, use_otmpfile_if_available=True)
    assert test_file.exists()
    with open(test_file, "rb") as f:
        assert f.read() == new_data


def test_atomic_rename_file():
    """Test atomic_rename for files."""
    src_file = BASE_TEST_DIR / "src_rename.txt"
    dst_file = BASE_TEST_DIR / "dst_rename.txt"
    data = b"Rename test"

    with open(src_file, "wb") as f:
        f.write(data)

    fs_ops.atomic_rename(str(src_file), str(dst_file))
    assert not src_file.exists()
    assert dst_file.exists()
    with open(dst_file, "rb") as f:
        assert f.read() == data

def test_atomic_rename_overwrite_existing_file():
    """Test atomic_rename overwrites an existing destination file."""
    src_file = BASE_TEST_DIR / "src_rename_overwrite.txt"
    dst_file = BASE_TEST_DIR / "dst_rename_overwrite.txt"
    src_data = b"Source data for overwrite"
    dst_initial_data = b"Initial destination data"

    with open(src_file, "wb") as f:
        f.write(src_data)
    with open(dst_file, "wb") as f:
        f.write(dst_initial_data)

    fs_ops.atomic_rename(str(src_file), str(dst_file))
    assert not src_file.exists()
    assert dst_file.exists()
    with open(dst_file, "rb") as f:
        assert f.read() == src_data


def test_atomic_rename_to_subdirectory():
    """Test atomic_rename when the destination is in a new subdirectory."""
    src_file = BASE_TEST_DIR / "src_rename_subdir.txt"
    dst_dir = BASE_TEST_DIR / "new_subdir_for_rename"
    dst_file = dst_dir / "dst_rename_subdir.txt"
    data = b"Rename to subdir test"

    with open(src_file, "wb") as f:
        f.write(data)

    # The fs_ops.atomic_rename function should create dst_dir if it doesn't exist
    fs_ops.atomic_rename(str(src_file), str(dst_file))
    assert not src_file.exists()
    assert dst_dir.exists()
    assert dst_dir.is_dir()
    assert dst_file.exists()
    with open(dst_file, "rb") as f:
        assert f.read() == data


def test_atomic_delete_file():
    """Test atomic_delete for files."""
    test_file = BASE_TEST_DIR / "test_delete.txt"
    with open(test_file, "wb") as f:
        f.write(b"Delete test")

    assert test_file.exists()
    fs_ops.atomic_delete(str(test_file))
    assert not test_file.exists()

def test_atomic_delete_non_existent_file():
    """Test atomic_delete for a non-existent file (should not raise error)."""
    test_file = BASE_TEST_DIR / "non_existent_for_delete.txt"
    try:
        fs_ops.atomic_delete(str(test_file))
    except Exception as e:
        pytest.fail(f"atomic_delete raised an exception for non-existent file: {e}")
    assert not test_file.exists()


def test_atomic_delete_is_a_directory_error():
    """Test atomic_delete raises IsADirectoryError when trying to delete a directory."""
    test_dir = BASE_TEST_DIR / "dir_to_delete_with_file_func"
    test_dir.mkdir()

    assert test_dir.is_dir()
    with pytest.raises(IsADirectoryError):
        fs_ops.atomic_delete(str(test_dir))
    assert test_dir.exists() # Should still exist


# --- Parallel writing test ---
NUM_PARALLEL_WRITES = 100 # Reduced from 1000 for faster CI, can be increased for local stress testing
FILE_CONTENT_TEMPLATE = "Parallel write test data for file {}"

def worker_task_atomic_write(file_idx, base_dir, use_otmpfile):
    """Target function for processes/threads to perform atomic write."""
    file_path = base_dir / f"parallel_file_{file_idx}.txt"
    data = FILE_CONTENT_TEMPLATE.format(file_idx).encode('utf-8')
    try:
        fs_ops.atomic_write(str(file_path), data, use_otmpfile_if_available=use_otmpfile)
        # Verify immediately after write, if possible, though primary verification is done by main thread
        with open(file_path, "rb") as f:
            if f.read() != data:
                return (file_idx, False, "Read content mismatch immediately after write")
        return (file_idx, True, None)
    except Exception as e:
        logger.error(f"Error in worker {file_idx} writing to {file_path}: {e}", exc_info=True)
        return (file_idx, False, str(e))


@pytest.mark.parametrize("use_otmpfile_param", [True, False])
def test_parallel_atomic_writes_no_stale_reads(use_otmpfile_param):
    """
    Tests that writing many files in parallel using atomic_write does not result in
    stale reads or corrupted files.
    This test uses multiprocessing for true parallelism.
    """
    parallel_dir = BASE_TEST_DIR / f"parallel_writes_otmpfile_{use_otmpfile_param}"
    parallel_dir.mkdir(exist_ok=True)

    processes = []
    # Using a manager for results queue if more complex state needed, but simple list of results is fine too.
    # For this, we'll collect results after join.
    # Can also use multiprocessing.Pool

    pool = multiprocessing.Pool(processes=min(multiprocessing.cpu_count(), NUM_PARALLEL_WRITES // 10 + 1))
    results_async = [
        pool.apply_async(worker_task_atomic_write, (i, parallel_dir, use_otmpfile_param))
        for i in range(NUM_PARALLEL_WRITES)
    ]
    pool.close()
    pool.join()

    failures = []
    for i, res_async in enumerate(results_async):
        try:
            file_idx, success, error_msg = res_async.get(timeout=10) # Get result from worker
            if not success:
                failures.append(f"Worker {file_idx} failed: {error_msg}")
        except multiprocessing.TimeoutError:
            failures.append(f"Worker for file {i} timed out.")
        except Exception as e:
            failures.append(f"Could not get result for worker {i}: {e}")


    # After all processes complete, verify all files
    for i in range(NUM_PARALLEL_WRITES):
        file_path = parallel_dir / f"parallel_file_{i}.txt"
        expected_data = FILE_CONTENT_TEMPLATE.format(i).encode('utf-8')
        if not file_path.exists():
            failures.append(f"File {file_path} does not exist after parallel writes.")
            continue
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            if content != expected_data:
                failures.append(
                    f"Content mismatch for {file_path}. "
                    f"Expected: '{expected_data.decode()}', Got: '{content.decode()}'"
                )
        except Exception as e:
            failures.append(f"Error reading file {file_path} after parallel writes: {e}")

    if failures:
        logger.error("Parallel write test failures:\n" + "\n".join(failures))
        pytest.fail(f"{len(failures)} failures in parallel atomic write test. See logs for details.")

    logger.info(f"Parallel atomic write test with use_otmpfile={use_otmpfile_param} completed successfully for {NUM_PARALLEL_WRITES} files.")


# It might be good to also have a threading-based parallel test,
# as O_TMPFILE issues might behave differently with threads vs processes due to /proc/self/fd.
# However, the prompt implies "parallel" meaning concurrent processes.

def test_fsync_mocked(mocker):
    """Test that fsync is called by atomic_write."""
    mock_os_fsync = mocker.patch("os.fsync")
    # If using libc directly: mock_libc_fsync = mocker.patch("triangulum_lx.tooling.fs_ops.c_fsync")

    test_file = BASE_TEST_DIR / "test_fsync.txt"
    data = b"fsync test"

    # Test with fallback (tempfile + rename)
    fs_ops.atomic_write(str(test_file), data, use_otmpfile_if_available=False)
    mock_os_fsync.assert_called() # Should be called on the temp file descriptor
    # If also testing O_TMPFILE path, would need to ensure it's called there too.
    # This is tricky because O_TMPFILE path might not be taken.
    # For now, testing fsync on fallback is sufficient to show integration.

    # Reset mock for another call if testing O_TMPFILE path separately
    mock_os_fsync.reset_mock()
    if fs_ops.os.name == 'posix' and hasattr(fs_ops.os, 'O_TMPFILE') and hasattr(fs_ops.os, 'linkat'):
        # Only attempt if O_TMPFILE path is likely
        try:
            fs_ops.atomic_write(str(test_file), data, use_otmpfile_if_available=True)
            # If O_TMPFILE path was taken, fsync should have been called.
            # If it fell back, it would also be called.
            # This assertion is a bit weak if O_TMPFILE is not supported on test runner.
            mock_os_fsync.assert_called()
        except OSError as e:
            # If O_TMPFILE fails and fallback runs, fsync is still called.
            # If O_TMPFILE fails so catastrophically that fsync is not reached in fallback,
            # that's a different issue.
            logger.warning(f"OSError during O_TMPFILE fsync test, fsync might have been called in fallback: {e}")
            if mock_os_fsync.called:
                logger.info("fsync was called (likely in fallback after O_TMPFILE error)")
            else:
                # This case would be a problem.
                logger.error("fsync was NOT called after O_TMPFILE error and fallback attempt.")
                # We expect fsync to be called even if O_TMPFILE fails and it falls back
                mock_os_fsync.assert_called()
        except Exception: # Catch any other unexpected error
            mock_os_fsync.assert_called() # Still expect fsync if fallback runs

if __name__ == '__main__':
    # Example of running a specific test, e.g., during development
    # Remember to set up PYTHONPATH if running directly and triangulum_lx is not installed
    # pytest.main([__file__, "-k", "test_parallel_atomic_writes_no_stale_reads and not use_otmpfile_param"])
    pytest.main([__file__])
