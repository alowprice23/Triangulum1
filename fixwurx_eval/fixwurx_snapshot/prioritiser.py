"""
goal/prioritiser.py
───────────────────
Pure scoring helper: converts an *incoming* `BugTicket` (see `core.scheduler`)
into a single floating-point score suitable for Python’s `sorted(..., reverse=True)`
call.

Mathematical background
───────────────────────
priority  =  α · S_norm  +  β · A_norm

  S_norm = severity / max_severity        ∈ [0, 1]
  A_norm = min(1,  age / AGE_MAX)         ∈ [0, 1]

To guarantee **starvation-freedom** we must ensure that, for sufficiently old
tickets, the age term can dominate any severity difference:

      β > α · (max_sev − 1) / max_sev        ← derived in Part-6 proof

Using max_sev = 5 we choose α = 0.40, β = 0.60  (0.60 > 0.32 ✓).

AGE_MAX (time to reach full age weight) is tunable; 45 s default keeps the
queue responsive in practice while still satisfying the proof.
"""

from __future__ import annotations

import time
from typing import Union

from core.scheduler import BugTicket

# ---------------------------------------------------------------------------
# Tunable constants (can be overridden by optimiser if desired)
# ---------------------------------------------------------------------------
MAX_SEVERITY: int = 5

ALPHA: float = 0.40          # weight on severity   —> α
BETA: float = 0.60           # weight on age        —> β
AGE_MAX: float = 45.0        # seconds until age term saturates to 1.0


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------
def score(ticket: BugTicket) -> float:
    """
    Return a priority score ∈ [0, 1+ε].  Higher = more urgent.
    Stable, monotone in both severity and age (until saturation).

    The scheduler sorts with `reverse=True`, so larger comes first.
    """
    now = time.time()

    # 1. Normalised severity
    s_norm = min(ticket.severity, MAX_SEVERITY) / MAX_SEVERITY

    # 2. Normalised age
    age_sec = max(0.0, now - ticket.arrival_ts)
    a_norm = min(1.0, age_sec / AGE_MAX)

    # 3. Linear combination
    return (ALPHA * s_norm) + (BETA * a_norm)


# ---------------------------------------------------------------------------
# Starvation-freedom sanity check  (defensive; runs once on import)
# ---------------------------------------------------------------------------
if BETA <= ALPHA * (MAX_SEVERITY - 1) / MAX_SEVERITY:
    raise RuntimeError(
        "Priority weights violate starvation-freedom constraint: "
        f"choose BETA > {ALPHA * (MAX_SEVERITY - 1) / MAX_SEVERITY:.3f}"
    )


# ---------------------------------------------------------------------------
# Convenience helper for CLI / debugging
# ---------------------------------------------------------------------------
def explain(ticket: BugTicket) -> str:
    """Return human-readable breakdown for dashboards."""
    s_norm = ticket.severity / MAX_SEVERITY
    age = time.time() - ticket.arrival_ts
    a_norm = min(1, age / AGE_MAX)
    return (
        f"priority={score(ticket):.3f} "
        f"(sev={ticket.severity}→{s_norm:.2f}, age={age:.1f}s→{a_norm:.2f})"
    )


# ---------------------------------------------------------------------------
# Type alias for mypy users who call `score` in key=…
# ---------------------------------------------------------------------------
ScoreType = Union[int, float]
