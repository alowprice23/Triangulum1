import pytest
import os
from pathlib import Path
import shutil

# Expected states for touched_paths_details
EXPECT_PRESENT = "present"
EXPECT_ABSENT = "absent"
EXPECT_PRESENT_DIR = "present_dir"
EXPECT_PRESENT_FILE = "present_file"
# Could add EXPECT_CONTENT_MATCHES, EXPECT_MTIME_CHANGED etc. later if needed

def assert_fs_consistency(touched_paths_details: dict[str, str], base_dir: Path = None):
    """
    Asserts filesystem consistency based on a dictionary of paths and their expected states.

    Args:
        touched_paths_details: A dictionary where keys are file paths (relative to base_dir if provided,
                               otherwise absolute or relative to CWD) and values are expected states
                               (e.g., "present", "absent", "present_dir", "present_file").
        base_dir: Optional. If provided, paths in touched_paths_details are resolved relative to this base.

    Raises:
        AssertionError: If any path does not meet its expected state.
    """
    failures = []
    for path_str, expected_state in touched_paths_details.items():
        path_obj = Path(path_str) if base_dir is None else base_dir / path_str

        if expected_state == EXPECT_PRESENT:
            if not path_obj.exists():
                failures.append(f"Path '{path_obj}' expected to be present, but it is ABSENT.")
        elif expected_state == EXPECT_ABSENT:
            if path_obj.exists():
                failures.append(f"Path '{path_obj}' expected to be absent, but it is PRESENT.")
        elif expected_state == EXPECT_PRESENT_DIR:
            if not path_obj.exists():
                failures.append(f"Path '{path_obj}' expected to be a PRESENT DIRECTORY, but it is ABSENT.")
            elif not path_obj.is_dir():
                failures.append(f"Path '{path_obj}' expected to be a PRESENT DIRECTORY, but it is a FILE.")
        elif expected_state == EXPECT_PRESENT_FILE:
            if not path_obj.exists():
                failures.append(f"Path '{path_obj}' expected to be a PRESENT FILE, but it is ABSENT.")
            elif not path_obj.is_file():
                failures.append(f"Path '{path_obj}' expected to be a PRESENT FILE, but it is a DIRECTORY.")
        else:
            failures.append(f"Unknown expected state '{expected_state}' for path '{path_obj}'.")

    if failures:
        raise AssertionError("Filesystem consistency check failed:\n" + "\n".join(failures))

# --- Tests for assert_fs_consistency ---

BASE_TEST_DIR_CONSISTENCY = Path("_test_fs_consistency_temp_dir_")

@pytest.fixture(scope="function")
def setup_teardown_fs():
    """Create and clean up a test directory for filesystem operations."""
    if BASE_TEST_DIR_CONSISTENCY.exists():
        shutil.rmtree(BASE_TEST_DIR_CONSISTENCY)
    BASE_TEST_DIR_CONSISTENCY.mkdir(parents=True, exist_ok=True)
    yield BASE_TEST_DIR_CONSISTENCY
    try:
        shutil.rmtree(BASE_TEST_DIR_CONSISTENCY)
    except Exception as e:
        print(f"Error cleaning up test directory {BASE_TEST_DIR_CONSISTENCY.resolve()}: {e}")


def test_assert_fs_consistency_all_pass(setup_teardown_fs):
    base_dir = setup_teardown_fs
    file1 = base_dir / "file1.txt"
    dir1 = base_dir / "dir1"
    absent_file = base_dir / "absent_file.txt"

    file1.write_text("content1")
    dir1.mkdir()

    touched_paths = {
        "file1.txt": EXPECT_PRESENT_FILE,
        "dir1": EXPECT_PRESENT_DIR,
        str(absent_file.relative_to(base_dir)): EXPECT_ABSENT # Use relative path for testing
    }

    try:
        assert_fs_consistency(touched_paths, base_dir)
    except AssertionError as e:
        pytest.fail(f"assert_fs_consistency failed unexpectedly: {e}")

def test_assert_fs_consistency_expect_present_is_absent(setup_teardown_fs):
    base_dir = setup_teardown_fs
    touched_paths = {"missing_file.txt": EXPECT_PRESENT}
    with pytest.raises(AssertionError) as excinfo:
        assert_fs_consistency(touched_paths, base_dir)
    assert "Path '" in str(excinfo.value)
    assert "missing_file.txt' expected to be present, but it is ABSENT." in str(excinfo.value)

def test_assert_fs_consistency_expect_absent_is_present(setup_teardown_fs):
    base_dir = setup_teardown_fs
    present_file = base_dir / "present_file.txt"
    present_file.write_text("exists")

    touched_paths = {"present_file.txt": EXPECT_ABSENT}
    with pytest.raises(AssertionError) as excinfo:
        assert_fs_consistency(touched_paths, base_dir)
    assert "present_file.txt' expected to be absent, but it is PRESENT." in str(excinfo.value)

def test_assert_fs_consistency_expect_dir_is_file(setup_teardown_fs):
    base_dir = setup_teardown_fs
    file_as_dir = base_dir / "file_as_dir.txt"
    file_as_dir.write_text("i am a file")

    touched_paths = {"file_as_dir.txt": EXPECT_PRESENT_DIR}
    with pytest.raises(AssertionError) as excinfo:
        assert_fs_consistency(touched_paths, base_dir)
    assert "file_as_dir.txt' expected to be a PRESENT DIRECTORY, but it is a FILE." in str(excinfo.value)

def test_assert_fs_consistency_expect_file_is_dir(setup_teardown_fs):
    base_dir = setup_teardown_fs
    dir_as_file = base_dir / "dir_as_file"
    dir_as_file.mkdir()

    touched_paths = {"dir_as_file": EXPECT_PRESENT_FILE}
    with pytest.raises(AssertionError) as excinfo:
        assert_fs_consistency(touched_paths, base_dir)
    assert "dir_as_file' expected to be a PRESENT FILE, but it is a DIRECTORY." in str(excinfo.value)

def test_assert_fs_consistency_expect_present_file_is_absent(setup_teardown_fs):
    base_dir = setup_teardown_fs
    touched_paths = {"missing_file.txt": EXPECT_PRESENT_FILE}
    with pytest.raises(AssertionError) as excinfo:
        assert_fs_consistency(touched_paths, base_dir)
    assert "missing_file.txt' expected to be a PRESENT FILE, but it is ABSENT." in str(excinfo.value)

def test_assert_fs_consistency_expect_present_dir_is_absent(setup_teardown_fs):
    base_dir = setup_teardown_fs
    touched_paths = {"missing_dir": EXPECT_PRESENT_DIR}
    with pytest.raises(AssertionError) as excinfo:
        assert_fs_consistency(touched_paths, base_dir)
    assert "missing_dir' expected to be a PRESENT DIRECTORY, but it is ABSENT." in str(excinfo.value)

def test_assert_fs_consistency_multiple_failures(setup_teardown_fs):
    base_dir = setup_teardown_fs
    file1 = base_dir / "file1.txt" # Exists, but will be expected absent
    file1.write_text("content")

    touched_paths = {
        "file1.txt": EXPECT_ABSENT,
        "missing_file.txt": EXPECT_PRESENT
    }
    with pytest.raises(AssertionError) as excinfo:
        assert_fs_consistency(touched_paths, base_dir)
    assert "file1.txt' expected to be absent, but it is PRESENT." in str(excinfo.value)
    assert "missing_file.txt' expected to be present, but it is ABSENT." in str(excinfo.value)

def test_assert_fs_consistency_unknown_state(setup_teardown_fs):
    base_dir = setup_teardown_fs
    touched_paths = {"some_file.txt": "EXPECT_FLUMMOXED"}
    with pytest.raises(AssertionError) as excinfo:
        assert_fs_consistency(touched_paths, base_dir)
    assert "Unknown expected state 'EXPECT_FLUMMOXED' for path" in str(excinfo.value)
    assert "some_file.txt" in str(excinfo.value)

def test_assert_fs_consistency_no_base_dir_absolute_paths(setup_teardown_fs):
    # This test relies on creating files in the current working directory or a known absolute path.
    # For simplicity, we'll use the setup_teardown_fs which gives us a temporary base_dir,
    # and then we'll construct absolute paths to items within it.
    temp_base = setup_teardown_fs

    abs_file = temp_base / "abs_file.txt"
    abs_dir = temp_base / "abs_dir"

    abs_file.write_text("abs content")
    abs_dir.mkdir()

    touched_paths_abs = {
        str(abs_file): EXPECT_PRESENT_FILE,
        str(abs_dir): EXPECT_PRESENT_DIR
    }
    try:
        assert_fs_consistency(touched_paths_abs) # No base_dir, paths are absolute
    except AssertionError as e:
        pytest.fail(f"assert_fs_consistency failed with absolute paths: {e}")

    # Test failure with absolute path
    touched_paths_abs_fail = {str(abs_file): EXPECT_ABSENT}
    with pytest.raises(AssertionError):
        assert_fs_consistency(touched_paths_abs_fail)


if __name__ == "__main__":
    # For running specific tests manually, e.g.:
    # pytest tests/fs/test_consistency.py -k "test_assert_fs_consistency_all_pass"
    pytest.main([__file__])
