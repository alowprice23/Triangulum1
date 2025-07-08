"""
core/rollback_manager.py
────────────────────────
Loss-less, atomic rollback layer.

High-level contract
───────────────────
1. **Every successful patch application** ▫ stores the *reverse diff* in
   `.triangulum/rollback/{bug_id}.patch`.  (Store once; overwrite forbidden.)
2. **rollback_patch(bug_id)** ▫ applies that reverse diff with
   `git apply -R`, restoring the work-tree exactly to the pre-patch SHA.
3. **Atomicity** ▫ two-step algorithm  
      a) `git apply --check -R patch`   → verify clean-apply  
      b) `git apply        -R patch`    → mutate work-tree  
      c) if any step fails → work-tree unchanged, function raises `RollbackError`.

No third-party dependencies—only `subprocess` and `pathlib`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict

# ------------------------------------------------------------------------------
ROLLBACK_DIR = Path(".triangulum") / "rollback"
ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = ROLLBACK_DIR / "registry.json"  # maps bug-id → patch filename


# ───────────────────────────────────────────────────────────────────────────────
# Exceptions
# ───────────────────────────────────────────────────────────────────────────────
class RollbackError(RuntimeError):
    """Raised if registry missing, git apply fails, or path tampered."""


# ───────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ───────────────────────────────────────────────────────────────────────────────
def _load_registry() -> Dict[str, str]:
    if REGISTRY_FILE.exists():
        with REGISTRY_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _save_registry(reg: Dict[str, str]) -> None:
    with REGISTRY_FILE.open("w", encoding="utf-8") as fh:
        json.dump(reg, fh, indent=2)


# ───────────────────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────────────────
def register_patch(bug_id: str, forward_diff: str) -> Path:
    """
    Called by the Analyst / patch bundle code **once** after a unit-green fix.
    Stores the *forward diff* so the reverse diff can be generated when needed.
    Returns the patch file path.
    """
    dest = ROLLBACK_DIR / f"{bug_id}.patch"
    if dest.exists():
        raise RollbackError(f"Patch for bug {bug_id} already registered")

    dest.write_text(forward_diff, encoding="utf-8")

    # update registry
    reg = _load_registry()
    reg[bug_id] = dest.name
    _save_registry(reg)
    return dest


def rollback_patch(bug_id: str) -> None:
    """
    Atomically restore pre-patch state for `bug_id`.

    Raises RollbackError if:
        • no patch registered,
        • reverse apply fails,
        • git not available.
    """
    reg = _load_registry()
    patch_name = reg.get(bug_id)
    if patch_name is None:
        raise RollbackError(f"No patch recorded for bug {bug_id}")

    patch_path = ROLLBACK_DIR / patch_name
    if not patch_path.exists():
        raise RollbackError(f"Patch file missing: {patch_path}")

    # 1) dry-run check
    _git_apply(["--check", "-R", str(patch_path)])

    # 2) real revert (atomic at filesystem level—either succeeds or git exits non-zero)
    _git_apply(["-R", str(patch_path)])

    # 3) cleanup registry (idempotent)
    reg.pop(bug_id, None)
    _save_registry(reg)


# ───────────────────────────────────────────────────────────────────────────────
# CLI hook
# ───────────────────────────────────────────────────────────────────────────────
def main() -> None:
    """
    Minimal CLI entry (invoked via `python -m core.rollback_manager BUG-123`)
    so operators can roll back without importing Python.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Rollback a Triangulum patch")
    parser.add_argument("bug_id", help="Bug identifier to revert")
    args = parser.parse_args()

    try:
        rollback_patch(args.bug_id)
        print(f"✓ Rolled back patch for {args.bug_id}")
    except RollbackError as e:
        print(f"✗ Rollback failed: {e}")
        raise SystemExit(1) from e


# ───────────────────────────────────────────────────────────────────────────────
# Git helper
# ───────────────────────────────────────────────────────────────────────────────
def _git_apply(extra_args: list[str]) -> None:
    cmd = ["git", "apply", "--whitespace=nowarn"] + extra_args
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RollbackError(
            f"`{' '.join(cmd)}` failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )


# ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
