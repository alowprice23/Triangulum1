import pytest
import os
import time
import shutil
from pathlib import Path
import logging

from triangulum_lx.core.fs_state import FileSystemStateCache

logger = logging.getLogger(__name__)
BASE_TEST_DIR = Path("_test_fs_state_temp_dir_")

@pytest.fixture(scope="function")
def cache_and_basedir():
    """Fixture to provide a FileSystemStateCache instance and a clean test directory."""
    if BASE_TEST_DIR.exists():
        shutil.rmtree(BASE_TEST_DIR)
    BASE_TEST_DIR.mkdir(parents=True, exist_ok=True)

    cache = FileSystemStateCache(default_ttl=60) # Reasonably long TTL for most tests

    # Create some initial structure
    (BASE_TEST_DIR / "file_A.txt").write_text("content A")
    (BASE_TEST_DIR / "dir_B").mkdir()
    (BASE_TEST_DIR / "dir_B" / "file_B_1.txt").write_text("content B1")

    yield cache, BASE_TEST_DIR

    try:
        shutil.rmtree(BASE_TEST_DIR)
    except Exception as e:
        logger.error(f"Error cleaning up test directory {BASE_TEST_DIR.resolve()}: {e}")

def test_cache_exists_miss_and_hit(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    file_a = base_dir / "file_A.txt"
    non_existent_file = base_dir / "non_existent.txt"

    # Initial miss for file_A
    stats_before = cache.get_stats()
    assert cache.exists(file_a) is True
    stats_after = cache.get_stats()
    assert stats_after["misses"] == stats_before["misses"] + 1
    assert stats_after["current_size"] > stats_before["current_size"]

    # Hit for file_A
    stats_before_hit = cache.get_stats()
    assert cache.exists(file_a) is True
    stats_after_hit = cache.get_stats()
    assert stats_after_hit["hits"] == stats_before_hit["hits"] + 1
    assert stats_after_hit["misses"] == stats_before_hit["misses"] # No new misses

    # Miss for non_existent_file
    stats_before_non = cache.get_stats()
    assert cache.exists(non_existent_file) is False
    stats_after_non = cache.get_stats()
    assert stats_after_non["misses"] == stats_before_non["misses"] + 1

    # Hit for non_existent_file
    stats_before_non_hit = cache.get_stats()
    assert cache.exists(non_existent_file) is False
    stats_after_non_hit = cache.get_stats()
    assert stats_after_non_hit["hits"] == stats_before_non_hit["hits"] + 1


def test_cache_is_dir_miss_and_hit(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    dir_b = base_dir / "dir_B"
    file_a = base_dir / "file_A.txt"

    # Miss for dir_B
    assert cache.is_dir(dir_b) is True
    # Hit for dir_B
    stats_before = cache.get_stats()
    assert cache.is_dir(dir_b) is True
    assert cache.get_stats()["hits"] == stats_before["hits"] + 1

    # Miss for file_A (checking is_dir)
    assert cache.is_dir(file_a) is False
    # Hit for file_A
    stats_before = cache.get_stats()
    assert cache.is_dir(file_a) is False
    assert cache.get_stats()["hits"] == stats_before["hits"] + 1

def test_cache_is_file_miss_and_hit(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    file_a = base_dir / "file_A.txt"
    dir_b = base_dir / "dir_B"

    # Miss for file_a
    assert cache.is_file(file_a) is True
    # Hit for file_a
    stats_before = cache.get_stats()
    assert cache.is_file(file_a) is True
    assert cache.get_stats()["hits"] == stats_before["hits"] + 1

    # Miss for dir_b (checking is_file)
    assert cache.is_file(dir_b) is False
    # Hit for dir_b
    stats_before = cache.get_stats()
    assert cache.is_file(dir_b) is False
    assert cache.get_stats()["hits"] == stats_before["hits"] + 1


def test_cache_get_mtime_miss_and_hit(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    file_a = base_dir / "file_A.txt"

    # Miss
    mtime1 = cache.get_mtime(file_a)
    assert mtime1 is not None
    actual_mtime = file_a.stat().st_mtime
    assert abs(mtime1 - actual_mtime) < 0.000001

    # Hit
    stats_before = cache.get_stats()
    mtime2 = cache.get_mtime(file_a)
    assert cache.get_stats()["hits"] == stats_before["hits"] + 1
    assert mtime2 == mtime1

    # Non-existent file
    assert cache.get_mtime(base_dir / "non_existent.txt") is None

def test_cache_listdir_miss_and_hit(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    dir_b = base_dir / "dir_B"
    file_a = base_dir / "file_A.txt"

    # Miss for dir_B
    children1 = cache.listdir(dir_b)
    assert sorted(children1) == sorted(["file_B_1.txt"])

    # Hit for dir_B
    stats_before = cache.get_stats()
    children2 = cache.listdir(dir_b)
    assert cache.get_stats()["hits"] == stats_before["hits"] + 1
    assert children1 == children2 # Order should be preserved by cache if sorted initially

    # Listdir on a file
    assert cache.listdir(file_a) is None
    # Listdir on non-existent path
    assert cache.listdir(base_dir / "non_existent_dir") is None

def test_cache_invalidation_simple(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    file_a = base_dir / "file_A.txt"

    # Populate cache
    cache.exists(file_a)
    cache.get_mtime(file_a)

    # Invalidate
    stats_before_invalidate = cache.get_stats()
    cache.invalidate(file_a)
    assert cache.get_stats()["invalidations"] >= stats_before_invalidate["invalidations"] + 1 # May invalidate parent too

    # Check for misses again
    stats_before_miss = cache.get_stats()
    cache.exists(file_a) # Should be a miss
    assert cache.get_stats()["misses"] == stats_before_miss["misses"] + 1

    # After the miss for exists(), the entry is re-populated.
    # get_mtime() will find the entry (a hit for _get_entry),
    # then fetch mtime if not present, but not count as another entry miss.
    cache.get_mtime(file_a)
    assert cache.get_stats()["misses"] == stats_before_miss["misses"] + 1


def test_cache_invalidation_affects_parent_listdir(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    dir_b = base_dir / "dir_B"
    file_b_1 = dir_b / "file_B_1.txt"
    file_b_2_path = dir_b / "file_B_2.txt"

    # Populate cache for dir_B and its initial child
    original_children = cache.listdir(dir_b)
    assert "file_B_1.txt" in original_children
    assert "file_B_2.txt" not in original_children

    # Simulate creating a new file and invalidating it
    file_b_2_path.write_text("content B2")
    cache.invalidate(file_b_2_path) # This should also make parent dir_B's listdir stale

    # Now listdir for dir_B should be a miss and re-fetch
    stats_before = cache.get_stats()
    new_children = cache.listdir(dir_b)
    # The listdir itself is a hit on the parent *entry* but its *children* list was cleared.
    # So it re-scans. This logic is subtle. The primary check is content.
    # The 'misses' count might not increment if parent dir_B entry itself wasn't fully removed.
    # What's important is that the content is up-to-date.

    assert "file_B_1.txt" in new_children
    assert "file_B_2.txt" in new_children
    assert len(new_children) == 2


def test_cache_ttl_expiry(cache_and_basedir):
    # Shorter TTL for this test
    cache = FileSystemStateCache(default_ttl=0.1)
    _, base_dir = cache_and_basedir # Get base_dir from original fixture

    file_for_ttl = base_dir / "ttl_file.txt"
    file_for_ttl.write_text("ttl content")

    # Populate cache
    assert cache.exists(file_for_ttl) is True
    norm_path = cache._normalize_path(file_for_ttl)
    assert norm_path in cache._cache # Check it's actually cached

    # Wait for TTL to expire
    time.sleep(0.2)

    # Access again, should be a miss due to TTL
    stats_before = cache.get_stats()
    assert cache.exists(file_for_ttl) is True # Still exists on FS
    stats_after = cache.get_stats()

    # Entry should have been internally invalidated by TTL, then re-fetched.
    # So, one "miss" (or rather, a re-fetch after TTL expiry).
    # The internal _get_entry invalidates, then the exists() method re-populates.
    # Hits shouldn't increase, misses should.
    assert stats_after["misses"] == stats_before["misses"] + 1
    assert norm_path in cache._cache # Re-cached

def test_clear_cache(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    file_a = base_dir / "file_A.txt"
    dir_b = base_dir / "dir_B"

    # Populate
    cache.exists(file_a)
    cache.listdir(dir_b)
    assert cache.get_stats()["current_size"] > 0

    cache.clear()
    stats = cache.get_stats()
    assert stats["current_size"] == 0
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    # Invalidation count might or might not be reset based on interpretation, current impl doesn't reset fully.

def test_mismatch_detection(cache_and_basedir):
    cache, base_dir = cache_and_basedir
    file_a = base_dir / "file_A.txt"

    # Populate cache
    original_mtime = cache.get_mtime(file_a)
    assert original_mtime is not None

    # Simulate external modification
    time.sleep(0.01) # Ensure mtime can change
    file_a.write_text("new content A")
    actual_new_mtime = file_a.stat().st_mtime
    assert actual_new_mtime != original_mtime

    # Check for mismatch
    stats_before = cache.get_stats()
    cache.check_and_report_mismatch(file_a, {'exists': True, 'mtime': actual_new_mtime})
    stats_after = cache.get_stats()
    assert stats_after["mismatches_detected"] == stats_before["mismatches_detected"] + 1

    # Mismatch for existence
    file_to_delete = base_dir / "delete_me.txt"
    file_to_delete.write_text("delete content")
    cache.exists(file_to_delete) # Cache it as existing

    file_to_delete.unlink() # External delete

    stats_before_del = cache.get_stats()
    cache.check_and_report_mismatch(file_to_delete, {'exists': False, 'mtime': None})
    stats_after_del = cache.get_stats()
    assert stats_after_del["mismatches_detected"] == stats_before_del["mismatches_detected"] + 1


def test_stress_operations_mismatch_counter(cache_and_basedir):
    """
    Performs a series of operations that should ideally not lead to mismatches
    if invalidation is done correctly by the (simulated) calling code.
    This test doesn't use external modification to check mismatch counter robustness.
    It checks that the mismatch counter *remains* 0 if cache is used correctly.
    """
    cache, base_dir = cache_and_basedir

    num_ops = 50
    current_files = set()

    for i in range(num_ops):
        op_type = i % 4
        file_path = base_dir / f"stress_file_{i}.txt"
        dir_path = base_dir / f"stress_dir_{i}"

        if op_type == 0: # Create file
            if not cache.exists(file_path): # Check before op
                file_path.write_text(f"stress content {i}")
                cache.invalidate(file_path) # Invalidate after op
                assert cache.exists(file_path) is True # Verify after invalidation
                current_files.add(str(file_path))
        elif op_type == 1: # Modify file
            if str(file_path) in current_files and cache.exists(file_path):
                # Before modification, check for external changes (simulated)
                # For this test, assume no external changes, so check_and_report_mismatch shouldn't find any.
                fs_stat = file_path.stat()
                cache.check_and_report_mismatch(file_path, {'exists': True, 'mtime': fs_stat.st_mtime})

                file_path.write_text(f"new stress content {i}")
                cache.invalidate(file_path)
                new_mtime = cache.get_mtime(file_path)
                assert new_mtime is not None
                assert abs(new_mtime - file_path.stat().st_mtime) < 0.00001
        elif op_type == 2: # Delete file
            if str(file_path) in current_files and cache.exists(file_path):
                file_path.unlink()
                cache.invalidate(file_path)
                assert cache.exists(file_path) is False
                current_files.remove(str(file_path))
        elif op_type == 3: # List dir (read op)
            cache.listdir(base_dir) # Just access, no invalidation needed by this op itself

    assert cache.get_stats()["mismatches_detected"] == 0, "Mismatch counter should be 0 with correct usage."
    cache.clear()
    assert cache.get_stats()["mismatches_detected"] == 0 # Ensure clear doesn't change it, or it's reset.

# Further tests could include:
# - Recursive invalidation scenarios.
# - More complex interactions with parent/child directory invalidations.
# - Behavior with symlinks (though current normalize_path resolves them).
# - Thread-safety if the cache instance is shared (current impl. is not thread-safe).
# - Memory usage for very large numbers of cached entries (out of scope for unit tests).
# - Test error handling in listdir for permission denied.
# - Test behavior if filesystem is very slow (mocking time.time and os calls).
# - Test interaction between TTL expiry and explicit invalidation.
# - Test normalize_path with various inputs ('.', '..', symlinks etc.)
# - Test that check_and_report_mismatch does NOT increment if states are identical.
# - Test that invalidating a non-cached path does not error and affects stats minimally.
# - Test invalidating a directory also clears its mtime and children list, not just the entry itself.
# - Test that cache.listdir() on a path that exists but is a file correctly returns None and caches it as a file.
# - Test that cache.listdir() on a path that does not exist returns None and caches it as non-existent.
# - Test that cache.get_mtime() on a directory returns its mtime.

if __name__ == "__main__":
    pytest.main([__file__])
