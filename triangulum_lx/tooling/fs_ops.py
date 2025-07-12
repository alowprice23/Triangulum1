import warnings
from triangulum_lx.utils.file_ops import atomic_write, atomic_rename, atomic_delete

warnings.warn(
    "The 'triangulum_lx.tooling.fs_ops' module is deprecated and will be removed. "
    "Please import from 'triangulum_lx.utils.file_ops' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
__all__ = ["atomic_write", "atomic_rename", "atomic_delete"]
