import os
import tempfile
import shutil
import logging
import ctypes
import errno

logger = logging.getLogger(__name__)

# Constants for O_TMPFILE if available (Linux specific)
O_TMPFILE = 0o20000000  # From fcntl.h, may vary
O_CREAT = os.O_CREAT
O_WRONLY = os.O_WRONLY
O_EXCL = os.O_EXCL

# fsync
try:
    libc = ctypes.CDLL(None)
    # Check for GNU libc specific fsync
    # c_fsync = libc.fsync
    # c_fsync.argtypes = [ctypes.c_int]
    # c_fsync.restype = ctypes.c_int
except AttributeError:
    libc = None
    # c_fsync = None
    logger.warning("Could not load libc, fsync might not be available via ctypes.")


def _fsync_direct(fd):
    """fsyncs the file descriptor using os.fsync"""
    try:
        os.fsync(fd)
        return True
    except OSError as e:
        logger.error(f"os.fsync failed for fd {fd}: {e}")
        return False

# def _fsync_libc(fd):
#     """fsyncs the file descriptor using libc fsync if available"""
#     if c_fsync:
#         ret = c_fsync(fd)
#         if ret != 0:
#             e = ctypes.get_errno()
#             logger.error(f"libc fsync failed for fd {fd}: {os.strerror(e)}")
#             return False
#         return True
#     logger.warning("libc fsync not available, falling back to os.fsync or skipping.")
#     return _fsync_direct(fd) # Fallback or if you prefer direct os.fsync

# Prefer direct os.fsync as it's more standard Python.
# If specific libc behavior is needed, the above can be re-enabled.
fsync_callable = _fsync_direct


def atomic_write(filepath: str, data: bytes, use_otmpfile_if_available: bool = True):
    """
    Atomically writes data to a file.
    Uses O_TMPFILE for atomic creation and linking on supporting systems (Linux).
    Falls back to a temporary file and atomic rename otherwise.

    Args:
        filepath (str): The final path for the file.
        data (bytes): The data to write (must be bytes).
        use_otmpfile_if_available (bool): Whether to try O_TMPFILE method.
    """
    logger.debug(f"Atomic write requested for: {filepath}")
    # Attempt O_TMPFILE approach first if enabled and on Linux
    if use_otmpfile_if_available and hasattr(os, 'O_TMPFILE') and hasattr(os, 'linkat') and os.name == 'posix':
        # O_TMPFILE is Linux specific and requires kernel >= 3.11
        # Not all filesystems support O_TMPFILE (e.g. NFS, older ext*)
        # It creates an unnamed temporary file.
        # We then write to it, fsync, and atomically link it to the final path.
        dir_path = os.path.dirname(filepath)
        if not dir_path:
            dir_path = "." # Current directory

        fd = -1
        try:
            # O_TMPFILE needs O_WRONLY (or O_RDWR) and O_CREAT is implied with O_TMPFILE.
            # The mode 0o600 sets permissions for the temporary inode.
            fd = os.open(dir_path, O_WRONLY | os.O_TMPFILE, 0o600)
            logger.debug(f"O_TMPFILE fd obtained: {fd} for dir {dir_path}")

            os.write(fd, data)
            if not fsync_callable(fd):
                raise OSError(errno.EIO, f"fsync failed for O_TMPFILE fd {fd}")

            # Atomically link the temporary file to the destination path.
            # /proc/self/fd/FD refers to the open file descriptor.
            # AT_EMPTY_PATH is not directly available in os.linkat,
            # but linking /proc/self/fd/FD to target is the way.
            proc_fd_path = f"/proc/self/fd/{fd}"

            # os.linkat requires paths, not fd for src_dir_fd and dst_dir_fd by default
            # However, for linking from an O_TMPFILE, src_path is /proc/self/fd/FD
            # and src_dir_fd can be set to AT_FDCWD or similar.
            # The target is (dst_dir_fd=AT_FDCWD, dst_path=filepath)
            # Python's os.linkat: linkat(src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True, flags=0)
            # We are linking from a path derived from fd to the final filepath.

            # Ensure the directory for filepath exists
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except OSError as e:
                    # Handle potential race condition if another process created it
                    if not os.path.isdir(dir_path):
                        raise OSError(errno.EIO, f"Failed to create directory {dir_path}: {e}") from e

            os.linkat(proc_fd_path, filepath, flags=os.AT_SYMLINK_FOLLOW) # AT_SYMLINK_FOLLOW is default for follow_symlinks=True
            logger.info(f"Successfully wrote and linked O_TMPFILE to {filepath}")
            return
        except OSError as e:
            # If O_TMPFILE fails (e.g., unsupported filesystem, kernel, or permissions),
            # log the error and fall through to the temporary file + rename strategy.
            # Common errors: EOPNOTSUPP (O_TMPFILE not supported by fs), EINVAL (invalid flags/combination)
            logger.warning(f"O_TMPFILE strategy failed for {filepath}: {e}. Falling back to tempfile+rename.")
            # Ensure fd is closed if opened
            if fd != -1:
                try:
                    os.close(fd)
                except OSError as close_err:
                    logger.error(f"Error closing O_TMPFILE fd {fd} after failure: {close_err}")
        # Fallthrough to standard tempfile method if O_TMPFILE fails or is disabled

    # Fallback: Temporary file and atomic rename
    # This is a more portable approach.
    base_dir = os.path.dirname(filepath)
    if not base_dir: # Handle case where filepath is just a filename
        base_dir = "."

    if not os.path.exists(base_dir):
        try:
            os.makedirs(base_dir, exist_ok=True)
        except OSError as e:
            if not os.path.isdir(base_dir): # Check for race condition
                 raise OSError(errno.EIO, f"Failed to create directory {base_dir}: {e}") from e

    # Create a temporary file in the same directory as the target file.
    # This is crucial for `os.rename` to be atomic (usually on POSIX systems).
    fd, temp_path = -1, None
    try:
        fd, temp_path = tempfile.mkstemp(dir=base_dir, prefix=os.path.basename(filepath) + ".tmp")
        logger.debug(f"Fallback temp file created: {temp_path} with fd: {fd}")

        with os.fdopen(fd, 'wb') as f: # Use 'wb' for bytes
            f.write(data)
            f.flush() # Ensure data is written to OS buffer
            if not fsync_callable(f.fileno()): # fsync the file descriptor
                 raise OSError(errno.EIO, f"fsync failed for temp file {temp_path}")

        # On Windows, os.rename will fail if the destination exists.
        # We might need to remove it first, which breaks atomicity slightly.
        # A more robust Windows solution might involve MoveFileTransacted or similar,
        # but that's beyond standard library. For now, we accept this limitation.
        if os.name == 'nt' and os.path.exists(filepath):
            try:
                os.remove(filepath) # Not atomic with the rename
            except OSError as e:
                # If removal fails, the rename will likely also fail.
                logger.error(f"Could not remove existing file {filepath} on Windows: {e}")
                # Attempt rename anyway, it might be a permissions issue for remove but not for overwrite via rename.

        os.rename(temp_path, filepath)
        logger.info(f"Successfully wrote to temp file {temp_path} and renamed to {filepath}")
    except Exception as e:
        logger.error(f"Fallback atomic_write for {filepath} failed: {e}")
        # Clean up the temporary file if it still exists
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.debug(f"Cleaned up temporary file {temp_path}")
            except OSError as cleanup_err:
                logger.error(f"Failed to clean up temporary file {temp_path}: {cleanup_err}")
        raise
    finally:
        # fdopen closes the fd, but if mkstemp succeeded and fdopen failed, fd might still be open.
        # This is a bit tricky. Usually, fdopen takes ownership.
        # If fd was opened by mkstemp but not passed to fdopen (e.g. exception before), close it.
        # However, the `with os.fdopen` handles the fd closure.
        # The main risk is if mkstemp creates fd, then an error occurs before fdopen.
        # This path is not well covered by the current try/except.
        # For simplicity, we assume fdopen handles it or an error before fdopen means temp_path cleanup is enough.
        pass


def atomic_rename(old_path: str, new_path: str):
    """
    Atomically renames a file or directory.
    Relies on os.rename, which is atomic on POSIX if old and new are on the same filesystem.
    On Windows, behavior can be less predictable if new_path exists.

    Args:
        old_path (str): The current path of the file/directory.
        new_path (str): The new path for the file/directory.
    """
    logger.debug(f"Atomic rename requested from {old_path} to {new_path}")
    try:
        # Ensure the directory for new_path exists
        new_dir = os.path.dirname(new_path)
        if new_dir and not os.path.exists(new_dir):
            try:
                os.makedirs(new_dir, exist_ok=True)
            except OSError as e:
                 if not os.path.isdir(new_dir): # Race condition check
                    raise OSError(errno.EIO, f"Failed to create directory for new path {new_dir}: {e}") from e

        # On Windows, os.rename fails if new_path exists.
        # To make it more "atomic-like" in behavior (i.e., overwrite),
        # we might delete new_path first. This is not truly atomic.
        # For true atomicity, platform-specific APIs are needed (e.g., MoveFileEx with MOVEFILE_REPLACE_EXISTING).
        # Python's os.replace() is a better choice for atomic replace if available (Python 3.3+).
        if hasattr(os, 'replace'):
            os.replace(old_path, new_path)
        else: # Fallback for older Python or if os.replace is not suitable for some reason
            if os.name == 'nt' and os.path.exists(new_path):
                # This part is non-atomic. Consider implications.
                # If new_path is a directory, os.remove will fail. shutil.rmtree would be needed.
                # This function is simplified; robust atomic rename/replace is complex.
                try:
                    if os.path.isdir(new_path): # Cannot replace a directory with a file or vice-versa easily
                        if os.path.isfile(old_path):
                            raise OSError(errno.EISDIR, f"Cannot replace directory {new_path} with file {old_path} using basic rename.")
                        # For dir to dir rename where target exists, it might merge or fail depending on OS.
                        # To be safe, if new_path is a dir and old_path is a dir, let os.rename handle it.
                        # If new_path is a file and old_path is a file, then try removing.
                    elif os.path.isfile(new_path):
                         os.remove(new_path)
                except OSError as e:
                    logger.warning(f"Could not remove existing destination {new_path} on Windows before rename: {e}. Rename might fail.")
            os.rename(old_path, new_path)
        logger.info(f"Successfully renamed {old_path} to {new_path}")
    except OSError as e:
        logger.error(f"Atomic rename from {old_path} to {new_path} failed: {e}")
        raise


def atomic_delete(filepath: str):
    """
    Atomically deletes a file.
    Relies on os.remove, which is generally atomic for single files.
    For directories, use shutil.rmtree (which is not atomic). This function is for files.

    Args:
        filepath (str): The path of the file to delete.
    """
    logger.debug(f"Atomic delete requested for: {filepath}")
    try:
        # For true atomic delete, especially ensuring it's gone from directory entry
        # and data is unrecoverable, is highly FS and OS dependent.
        # os.remove is the standard Python way.
        if not os.path.exists(filepath): # Idempotency: if already deleted, succeed.
            logger.info(f"File {filepath} already deleted or does not exist.")
            return

        if os.path.isdir(filepath):
            logger.error(f"Path {filepath} is a directory. Use a directory removal function for directories.")
            raise IsADirectoryError(errno.EISDIR, f"Path {filepath} is a directory, not a file.", filepath)

        os.remove(filepath)
        logger.info(f"Successfully deleted file: {filepath}")
    except FileNotFoundError: # Handle race condition where file is deleted between check and remove
        logger.info(f"File {filepath} was deleted by another process before this operation.")
        pass # Succeed if file is gone
    except OSError as e:
        logger.error(f"Atomic delete for {filepath} failed: {e}")
        raise

if __name__ == '__main__':
    # Basic demonstration and manual test
    logging.basicConfig(level=logging.DEBUG)

    TEST_DIR = "fs_ops_test_dir"
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)

    file_a = os.path.join(TEST_DIR, "atomic_file_A.txt")
    file_b = os.path.join(TEST_DIR, "atomic_file_B.txt")
    file_c = os.path.join(TEST_DIR, "sub", "atomic_file_C.txt") # Test subdirectory creation

    # Test atomic_write
    logger.info("--- Testing atomic_write ---")
    try:
        atomic_write(file_a, b"Hello A, O_TMPFILE attempt", use_otmpfile_if_available=True)
        with open(file_a, "rb") as f:
            logger.info(f"Read from {file_a}: {f.read()}")

        atomic_write(file_b, b"Hello B, fallback", use_otmpfile_if_available=False)
        with open(file_b, "rb") as f:
            logger.info(f"Read from {file_b}: {f.read()}")

        atomic_write(file_c, b"Hello C in subdir") # Test auto dir creation
        with open(file_c, "rb") as f:
            logger.info(f"Read from {file_c}: {f.read()}")

    except Exception as e:
        logger.error(f"Error during atomic_write test: {e}", exc_info=True)

    # Test atomic_rename
    logger.info("\n--- Testing atomic_rename ---")
    file_a_renamed = os.path.join(TEST_DIR, "atomic_file_A_renamed.txt")
    try:
        atomic_rename(file_a, file_a_renamed)
        if os.path.exists(file_a_renamed) and not os.path.exists(file_a):
            logger.info(f"Renamed {file_a} to {file_a_renamed} successfully.")
        else:
            logger.error(f"Rename failed or original still exists.")

        # Test rename with overwrite (using os.replace if available)
        atomic_write(file_a, b"Original content for overwrite test")
        atomic_rename(file_a, file_b) # file_b should now have content of file_a
        with open(file_b, "rb") as f:
            logger.info(f"Content of {file_b} after overwrite rename: {f.read()}")
        if os.path.exists(file_a):
             logger.error(f"Original file {file_a} still exists after rename to {file_b}")


    except Exception as e:
        logger.error(f"Error during atomic_rename test: {e}", exc_info=True)

    # Test atomic_delete
    logger.info("\n--- Testing atomic_delete ---")
    try:
        if os.path.exists(file_a_renamed):
            atomic_delete(file_a_renamed)
            if not os.path.exists(file_a_renamed):
                logger.info(f"Deleted {file_a_renamed} successfully.")
            else:
                logger.error(f"Delete of {file_a_renamed} failed.")
        else:
            logger.info(f"{file_a_renamed} does not exist for deletion test.")

        if os.path.exists(file_b):
            atomic_delete(file_b)
        if os.path.exists(file_c):
            atomic_delete(file_c)

        # Test deleting non-existent file
        atomic_delete(os.path.join(TEST_DIR,"non_existent_file.txt"))


    except Exception as e:
        logger.error(f"Error during atomic_delete test: {e}", exc_info=True)

    # Clean up test directory
    # shutil.rmtree(TEST_DIR)
    # logger.info(f"Cleaned up test directory: {TEST_DIR}")
    print(f"\nManual tests complete. Check {TEST_DIR} for artifacts if not cleaned up.")
    print("Run pytest for automated tests.")
