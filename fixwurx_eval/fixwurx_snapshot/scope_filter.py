"""
tooling/scope_filter.py
───────────────────────
*File-scope firewall* for Triangulum-LX.

Goal
────
Reduce the candidate-file universe *before* Observer / Analyst touch the
repository, so that

    • node_modules, build artefacts, logs, etc. are excluded **up-front**.
    • the **initial entropy H₀** (≈ log₂|scope| bits) is clamped, guaranteeing
      a hard upper bound on the “inevitable-solution” attempt count given by

          N_* = ceil(H₀ / g)

      (see the entropy-drain formula in Part-5).

API
───
    sf = ScopeFilter(allow_globs=[...], block_globs=[...],
                     max_entropy_bits=12)          # 2¹² = 4096 files max
    safe_files = sf.filter(repo_root)

No external dependencies (uses only pathlib & fnmatch).
"""

from __future__ import annotations

import fnmatch
import math
import os
from pathlib import Path
from typing import Iterable, List, Sequence, Set


# ───────────────────────────────────────────────────────────────────────────────
# Helper: default block/allow lists
# ───────────────────────────────────────────────────────────────────────────────
_DEFAULT_BLOCK = [
    "node_modules/**",
    "**/__pycache__/**",
    "dist/**",
    "build/**",
    ".git/**",
    ".venv/**",
    "**/*.log",
    "**/*.tmp",
    "**/*.lock",
]

_DEFAULT_ALLOW = ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.json", "**/*.md"]


# ───────────────────────────────────────────────────────────────────────────────
# Core class
# ───────────────────────────────────────────────────────────────────────────────
class ScopeFilter:
    """
    Combine glob allow/block rules with an entropy clamp.

    Parameters
    ----------
    allow_globs  : inclusive patterns (evaluated *after* block list)
    block_globs  : patterns that always exclude
    max_entropy_bits : int
        Upper bound on `log2(|scope|)`.  E.g. 12 → at most 4096 paths survive.
    """

    def __init__(
        self,
        *,
        allow_globs: Sequence[str] | None = None,
        block_globs: Sequence[str] | None = None,
        max_entropy_bits: int = 12,
    ) -> None:
        self.block_globs: List[str] = list(block_globs or _DEFAULT_BLOCK)
        self.allow_globs: List[str] = list(allow_globs or _DEFAULT_ALLOW)
        self.max_entropy_bits: int = max_entropy_bits

    # ..........................................................................
    def filter(self, repo_root: os.PathLike[str]) -> List[Path]:
        """
        Return *allowed* file paths relative to `repo_root`.
        Entropy clamp applied **after** allow/block logic.
        """
        root = Path(repo_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(root)

        # 1) Gather candidate paths
        candidates: List[Path] = [
            p for p in root.rglob("*") if p.is_file()
        ]

        # 2) Block-list filter
        blocked: Set[Path] = {
            p
            for pat in self.block_globs
            for p in candidates
            if fnmatch.fnmatch(p.relative_to(root).as_posix(), pat)
        }
        stage1 = [p for p in candidates if p not in blocked]

        # 3) Allow-list filter (keep only those matching *any* allow glob)
        allowed: List[Path] = [
            p
            for p in stage1
            if any(
                fnmatch.fnmatch(p.relative_to(root).as_posix(), pat)
                for pat in self.allow_globs
            )
        ]

        # 4) Entropy clamp  (truncate deterministically by lexicographic order)
        max_files = 1 << self.max_entropy_bits  # 2^bits
        if len(allowed) > max_files:
            allowed.sort()
            allowed = allowed[:max_files]

        return allowed

    # ..........................................................................
    def entropy_bits(self, candidate_count: int) -> float:
        """Return log₂(count) (0 if count==0)."""
        return math.log2(candidate_count) if candidate_count else 0.0

    # ..........................................................................
    def __repr__(self) -> str:  # noqa: Dunder
        return (
            f"<ScopeFilter allow={len(self.allow_globs)} "
            f"block={len(self.block_globs)} "
            f"max_bits={self.max_entropy_bits}>"
        )
