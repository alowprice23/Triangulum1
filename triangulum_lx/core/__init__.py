"""Core components of the Triangulum system."""

# ---------------------------------------------------------------------------
# 1.  First create the lazy alias **before** importing any sibling modules.
#     This ensures the name `TriangulumEngine` is already present in
#     triangulum_lx.core's namespace even while the package is still
#     initialising, preventing the classic circular-import trap.
# ---------------------------------------------------------------------------

def get_triangulum_engine():
    """Return the real `TriangulumEngine` class (imported lazily).

    Importing here, inside the function body, defers the dependency on
    `triangulum_lx.engine` until the first time the alias is actually used,
    completely sidestepping circular-import issues.
    """
    from .engine import TriangulumEngine  # local import – executed on demand
    return TriangulumEngine


def TriangulumEngine(*args, **kwargs):
    """Backward-compatibility alias for `TriangulumEngine`.

    Acts like a constructor that forwards all arguments to the real engine
    class.  Keeping this as a *function* (not a class) preserves historical
    behaviour while still allowing static type-checkers to treat it as a
    callable returning a `TriangulumEngine` instance.
    """
    engine_cls = get_triangulum_engine()
    return engine_cls(*args, **kwargs)


# ---------------------------------------------------------------------------
# 2.  Now it is safe to import the rest of the public API.
# ---------------------------------------------------------------------------

from .state import Phase, BugState
from .transition import step
from .monitor import EngineMonitor
from .parallel_executor import ParallelExecutor, TaskContext as BugContext
from .rollback_manager import (
    rollback_patch,
    save_patch_record,
    list_patches,
    clean_patches,
)
from .entropy_explainer import (
    humanise,
    get_entropy_status,
    explain_verification_result,
    format_entropy_chart,
)

# ---------------------------------------------------------------------------
# 3.  Re-export public symbols.
# ---------------------------------------------------------------------------

__all__ = [
    "Phase",
    "BugState",
    "step",
    "TriangulumEngine",
    "EngineMonitor",
    "ParallelExecutor",
    "BugContext",  # Actually TaskContext
    "rollback_patch",
    "save_patch_record",
    "list_patches",
    "clean_patches",
    "humanise",
    "get_entropy_status",
    "explain_verification_result",
    "format_entropy_chart",
    "get_triangulum_engine",
]
