import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple

logger = logging.getLogger(__name__)

# Type aliases
CacheKey = str # Typically normalized absolute path
CacheEntry = Dict[str, Any] # Stores 'type', 'mtime', 'children', 'exists', 'access_time'

class FileSystemStateCache:
    """
    A cache for filesystem state to reduce direct FS operations.
    Explicit invalidation is required after atomic operations.
    """
    def __init__(self, default_ttl: float = 60.0):
        self._cache: Dict[CacheKey, CacheEntry] = {}
        self.default_ttl = default_ttl  # Time-to-live for entries, not strictly enforced without active reaping

        # Stats
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        self._mismatches_detected = 0 # Incremented if an operation finds cache was stale *before* its own invalidation

    def _normalize_path(self, path: Union[str, Path]) -> CacheKey:
        """Normalizes a path to an absolute string representation for use as a cache key."""
        return str(Path(path).resolve())

    def get_stats(self) -> Dict[str, int]:
        """Returns current cache statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "invalidations": self._invalidations,
            "mismatches_detected": self._mismatches_detected,
            "current_size": len(self._cache)
        }

    def _log_stats(self):
        logger.debug(f"Cache stats: Hits={self._hits}, Misses={self._misses}, Size={len(self._cache)}")

    def _get_entry(self, norm_path: CacheKey) -> Optional[CacheEntry]:
        """Retrieves an entry if it exists and is considered valid (e.g., TTL)."""
        entry = self._cache.get(norm_path)
        if not entry: # Truly not in cache
            self._misses += 1
            return None

        # Entry exists, check TTL
        if time.time() - entry.get('cache_time', 0) > self.default_ttl:
            logger.debug(f"TTL expired for cache entry: {norm_path}. Invalidating.")
            self.invalidate(norm_path, internal_ttl_expiry=True) # Avoid double counting invalidation stat
            self._misses += 1 # Count as a miss because data is stale and will be re-fetched by caller
            return None

        self._hits += 1
        return entry

    def _update_entry(self, norm_path: CacheKey, data: Dict[str, Any]):
        """Updates or creates a cache entry."""
        current_time = time.time()
        data['cache_time'] = current_time
        self._cache[norm_path] = data
        self._log_stats()

    def exists(self, path: Union[str, Path]) -> bool:
        """Checks if a path exists, using the cache if possible."""
        norm_path = self._normalize_path(path)
        entry = self._get_entry(norm_path)

        if entry and 'exists' in entry:
            logger.debug(f"Cache hit for exists({path}): {entry['exists']}")
            return entry['exists']

        logger.debug(f"Cache miss for exists({path}). Querying filesystem.")
        actual_exists = Path(path).exists() # Direct FS access
        self._update_entry(norm_path, {'exists': actual_exists, 'type': 'file_or_dir' if actual_exists else None})
        return actual_exists

    def is_dir(self, path: Union[str, Path]) -> bool:
        norm_path = self._normalize_path(path)
        entry = self._get_entry(norm_path)

        if entry and entry.get('exists') and 'type' in entry:
            is_dir_cached = entry['type'] == 'dir'
            logger.debug(f"Cache hit for is_dir({path}): {is_dir_cached}")
            return is_dir_cached

        logger.debug(f"Cache miss for is_dir({path}). Querying filesystem.")
        p_obj = Path(path)
        actual_exists = p_obj.exists()
        actual_is_dir = p_obj.is_dir() if actual_exists else False

        self._update_entry(norm_path, {'exists': actual_exists, 'type': 'dir' if actual_is_dir else ('file' if actual_exists else None)})
        return actual_is_dir

    def is_file(self, path: Union[str, Path]) -> bool:
        norm_path = self._normalize_path(path)
        entry = self._get_entry(norm_path)

        if entry and entry.get('exists') and 'type' in entry:
            is_file_cached = entry['type'] == 'file'
            logger.debug(f"Cache hit for is_file({path}): {is_file_cached}")
            return is_file_cached

        logger.debug(f"Cache miss for is_file({path}). Querying filesystem.")
        p_obj = Path(path)
        actual_exists = p_obj.exists()
        actual_is_file = p_obj.is_file() if actual_exists else False

        self._update_entry(norm_path, {'exists': actual_exists, 'type': 'file' if actual_is_file else ('dir' if actual_exists else None)})
        return actual_is_file


    def get_mtime(self, path: Union[str, Path]) -> Optional[float]:
        """Gets the modification time of a path, using the cache if possible."""
        norm_path = self._normalize_path(path)
        entry = self._get_entry(norm_path)

        if entry and 'mtime' in entry:
            logger.debug(f"Cache hit for get_mtime({path}): {entry['mtime']}")
            return entry['mtime']

        logger.debug(f"Cache miss for get_mtime({path}). Querying filesystem.")
        p_obj = Path(path)
        if p_obj.exists():
            actual_mtime = p_obj.stat().st_mtime
            # Update cache with mtime and existence
            existing_data = self._cache.get(norm_path, {})
            existing_data.update({'exists': True, 'mtime': actual_mtime, 'type': 'file' if p_obj.is_file() else 'dir'})
            self._update_entry(norm_path, existing_data)
            return actual_mtime
        else:
            # Path does not exist, update cache accordingly
            self._update_entry(norm_path, {'exists': False, 'mtime': None, 'type': None})
            return None

    def listdir(self, path: Union[str, Path]) -> Optional[List[str]]:
        """Lists directory contents, using the cache if possible. Returns None if path is not a directory or doesn't exist."""
        norm_path = self._normalize_path(path)
        entry = self._get_entry(norm_path)

        if entry:
            if not entry.get('exists') or entry.get('type') != 'dir':
                logger.debug(f"listdir({path}): Cached as not existing or not a directory.")
                return None # Cached as not a dir or not existing
            if 'children' in entry: # Children are cached
                logger.debug(f"Cache hit for listdir({path}) with {len(entry['children'])} children.")
                return list(entry['children']) # Return a copy

        logger.debug(f"Cache miss for listdir({path}). Querying filesystem.")
        p_obj = Path(path)
        if p_obj.is_dir(): # Direct FS access
            try:
                actual_children = sorted([item.name for item in p_obj.iterdir()])
                # Update cache with children, existence, and type
                existing_data = self._cache.get(norm_path, {})
                existing_data.update({'exists': True, 'type': 'dir', 'children': actual_children, 'mtime': p_obj.stat().st_mtime})
                self._update_entry(norm_path, existing_data)
                return actual_children
            except OSError as e:
                logger.warning(f"Error listing directory {path} on filesystem: {e}")
                # Cache this error state? For now, treat as non-existent/non-dir
                self._update_entry(norm_path, {'exists': False, 'type': None, 'children': None, 'error': str(e)})
                return None
        else: # Not a directory or does not exist
            logger.debug(f"Path {path} is not a directory or does not exist on filesystem.")
            self._update_entry(norm_path, {'exists': p_obj.exists(), 'type': 'file' if p_obj.is_file() else None, 'children': None})
            return None

    def invalidate(self, path: Union[str, Path], recursive: bool = False, internal_ttl_expiry: bool = False):
        """
        Invalidates cache entries for a given path.
        If recursive is True, also invalidates entries for children if path is a directory.
        Also invalidates the parent directory's 'children' and 'mtime' cache.
        """
        norm_path = self._normalize_path(path)

        parent_dir_norm_path = self._normalize_path(Path(path).parent)

        paths_to_invalidate = {norm_path}

        if recursive:
            # This naive recursive invalidation might be slow for deep trees if every child is cached.
            # A more optimized way would be to iterate cache keys that start with norm_path + os.sep.
            # For now, if the entry was a dir with children, add them.
            entry_to_check_children = self._cache.get(norm_path) # Check current cache state
            if entry_to_check_children and entry_to_check_children.get('type') == 'dir' and 'children' in entry_to_check_children:
                for child_name in entry_to_check_children['children']:
                    paths_to_invalidate.add(self._normalize_path(Path(path) / child_name))

        for p_norm in list(paths_to_invalidate): # list() for safe iteration if modifying _cache
            if p_norm in self._cache:
                del self._cache[p_norm]
                if not internal_ttl_expiry: # Avoid double counting if TTL expiry caused this
                    self._invalidations += 1
                logger.debug(f"Invalidated cache for: {p_norm}")

        # Invalidate parent's listdir cache and mtime, as its content/mtime might have changed
        parent_entry = self._cache.get(parent_dir_norm_path)
        if parent_entry:
            updated_parent_entry = parent_entry.copy()
            refreshed_parent = False
            if 'children' in updated_parent_entry:
                del updated_parent_entry['children'] # Force re-fetch of children on next listdir
                refreshed_parent = True
            if 'mtime' in updated_parent_entry:
                del updated_parent_entry['mtime'] # Force re-fetch of mtime
                refreshed_parent = True

            if refreshed_parent:
                 self._cache[parent_dir_norm_path] = updated_parent_entry
                 logger.debug(f"Refreshed parent directory cache for: {parent_dir_norm_path}")
                 if not internal_ttl_expiry:
                     self._invalidations +=1 # Count as an invalidation action

        if not internal_ttl_expiry:
            self._log_stats()

    def check_and_report_mismatch(self, path: Union[str, Path], actual_fs_state: Dict[str, Any]):
        """
        Compares a cached state with actual filesystem state.
        If a mismatch is found, logs it and increments the mismatch counter.
        This is intended to be called by external operations *before* they modify
        a path and *before* they call invalidate() for their own operation.
        """
        norm_path = self._normalize_path(path)
        cached_entry = self._cache.get(norm_path)

        if not cached_entry:
            return # No cached state to compare against

        mismatched = False
        if 'exists' in actual_fs_state and 'exists' in cached_entry:
            if cached_entry['exists'] != actual_fs_state['exists']:
                mismatched = True
                logger.warning(f"Cache MISMATCH for exists({path}): Cached={cached_entry['exists']}, Actual={actual_fs_state['exists']}")

        if not mismatched and actual_fs_state.get('exists') and cached_entry.get('exists'):
            # Only compare mtime if both are believed to exist
            if 'mtime' in actual_fs_state and 'mtime' in cached_entry:
                # Be careful with float precision for mtime
                if cached_entry['mtime'] is not None and actual_fs_state['mtime'] is not None and \
                   abs(cached_entry['mtime'] - actual_fs_state['mtime']) > 0.000001: # Small tolerance
                    mismatched = True
                    logger.warning(f"Cache MISMATCH for mtime({path}): Cached={cached_entry['mtime']}, Actual={actual_fs_state['mtime']}")
            # Not comparing listdir children here, too complex for a simple check.
            # Lisdir mismatch would typically be found if exists/type is wrong, or if a child op fails.

        if mismatched:
            self._mismatches_detected += 1
            logger.error(f"Filesystem state mismatch detected for {path}. Current mismatches: {self._mismatches_detected}")
            # Optionally, auto-invalidate here, but the design implies explicit invalidation by caller.
            # self.invalidate(path)

    def clear(self):
        """Clears the entire cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        # self._mismatches_detected = 0 # debatable whether to reset this on full clear
        logger.info("FileSystemStateCache cleared.")
        self._log_stats()

# Global instance (optional, can be instantiated per component)
# fs_cache_instance = FileSystemStateCache()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    cache = FileSystemStateCache(default_ttl=5) # Short TTL for testing

    # Setup a test directory structure
    test_root = Path("_fs_cache_test_dir_")
    if test_root.exists():
        import shutil
        shutil.rmtree(test_root)
    test_root.mkdir()

    file1 = test_root / "file1.txt"
    dir1 = test_root / "dir1"
    file_in_dir1 = dir1 / "file_in_dir1.txt"

    with open(file1, "w") as f: f.write("content1")
    dir1.mkdir()
    with open(file_in_dir1, "w") as f: f.write("content_in_dir")

    logger.info("--- Initial checks (cache misses) ---")
    logger.info(f"Exists {file1}? {cache.exists(file1)}")
    logger.info(f"IsDir {dir1}? {cache.is_dir(dir1)}")
    logger.info(f"Mtime {file1}: {cache.get_mtime(file1)}")
    logger.info(f"ListDir {dir1}: {cache.listdir(dir1)}")
    logger.info(f"Exists non_existent.txt? {cache.exists(test_root / 'non_existent.txt')}")

    logger.info("\n--- Second checks (cache hits) ---")
    logger.info(f"Exists {file1}? {cache.exists(file1)}")
    logger.info(f"IsDir {dir1}? {cache.is_dir(dir1)}")
    logger.info(f"Mtime {file1}: {cache.get_mtime(file1)}")
    logger.info(f"ListDir {dir1}: {cache.listdir(dir1)}")

    logger.info("\n--- Test invalidation ---")
    cache.invalidate(file1)
    logger.info(f"Mtime {file1} after invalidate: {cache.get_mtime(file1)}") # Should be miss

    # Simulate external modification
    logger.info(f"\n--- Simulating external modification to {file_in_dir1} ---")
    time.sleep(1) # Ensure mtime changes
    with open(file_in_dir1, "w") as f: f.write("new content")

    # Check cache (should be stale if not invalidated)
    cached_mtime_stale = cache.get_mtime(file_in_dir1) # Hit, but stale
    actual_mtime = file_in_dir1.stat().st_mtime
    logger.info(f"Cached Mtime for {file_in_dir1} (stale): {cached_mtime_stale}")
    logger.info(f"Actual Mtime for {file_in_dir1}: {actual_mtime}")

    cache.check_and_report_mismatch(file_in_dir1, {'exists': True, 'mtime': actual_mtime})

    cache.invalidate(file_in_dir1)
    logger.info(f"Mtime for {file_in_dir1} after invalidate: {cache.get_mtime(file_in_dir1)}") # Miss, then update

    logger.info(f"\n--- Testing parent dir invalidation for listdir after new file ---")
    new_file_in_dir1 = dir1 / "another.txt"
    with open(new_file_in_dir1, "w") as f: f.write("hello")
    # listdir for dir1 should now be stale.
    # An operation creating new_file_in_dir1 should call cache.invalidate(new_file_in_dir1)
    # which should also refresh parent dir1's listdir cache.
    cache.invalidate(new_file_in_dir1)
    logger.info(f"ListDir {dir1} after new file and invalidation: {cache.listdir(dir1)}")
    assert "another.txt" in cache.listdir(dir1)

    logger.info("\n--- Testing TTL ---")
    file_ttl = test_root / "ttl_test.txt"
    with open(file_ttl, "w") as f: f.write("ttl")
    logger.info(f"Exists {file_ttl}? {cache.exists(file_ttl)}") # Cache miss, then store
    logger.info(f"Cache entry for {file_ttl}: {cache._cache.get(cache._normalize_path(file_ttl))}")
    logger.info(f"Sleeping for TTL (5s)...")
    time.sleep(6)
    logger.info(f"Exists {file_ttl} after TTL? {cache.exists(file_ttl)}") # Should be miss due to TTL
    assert cache._cache.get(cache._normalize_path(file_ttl)) is None # Entry should be gone or marked stale

    logger.info("\n--- Final Cache Stats ---")
    logger.info(cache.get_stats())

    # Cleanup
    import shutil
    shutil.rmtree(test_root)
    logger.info(f"Cleaned up test directory: {test_root}")
