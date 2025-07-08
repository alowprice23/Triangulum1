"""
core/state_machine.py
─────────────────────
Pure, side-effect-free Mealy automaton for one Triangulum-LX tick.

External modules (scheduler, coordinator, optimiser, etc.) build on this file
but **never** mutate the dataclasses it returns; they always work with fresh
copies to preserve functional-style reasoning and to keep the TLC proofs valid.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from typing import List, Tuple

# ────────────────────────────────────────────────────────────────────────────────
# 1.  Constants that appear in invariants & proofs
# ────────────────────────────────────────────────────────────────────────────────
AGENT_POOL_SIZE: int = 9          # |A|
AGENTS_PER_BUG: int = 3           # exactly 3 consumed while active
TIMER_MIN: int = 0
TIMER_MAX: int = 4               # chosen so 60-tick guarantee holds
PROMOTION_LIMIT: int = 2          # ≤2 canary/smoke attempts
TICKS_PER_PHASE: int = 3          # timer_default; optimiser may tune 2–4

# ────────────────────────────────────────────────────────────────────────────────
# 2.  Phase enumeration (Σ)
# ────────────────────────────────────────────────────────────────────────────────
class Phase(str, enum.Enum):
    WAIT      = "WAIT"
    REPRO     = "REPRO"
    PATCH     = "PATCH"
    VERIFY    = "VERIFY"
    CANARY    = "CANARY"
    SMOKE     = "SMOKE"
    DONE      = "DONE"
    ESCALATE  = "ESCALATE"

    # Helper predicates
    @property
    def active(self) -> bool:
        """Consumes agents?"""
        return self in {Phase.REPRO, Phase.PATCH, Phase.VERIFY}

    @property
    def timed(self) -> bool:
        """Phase subject to countdown timer?"""
        return self.active


# ────────────────────────────────────────────────────────────────────────────────
# 3.  Single-bug immutable state tuple
# ────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Bug:
    id: str
    phase: Phase
    timer: int = 0                      # 0 means ready for next transition
    promo_count: int = 0                # promotion attempts so far
    entropy_bits: float = 0.0           # bookkeeping, updated by monitor

    # ——— Derived helpers ——————————————————————————————
    def needs_alloc(self) -> bool:
        """WAIT bug is eligible for allocation if it has no agents yet."""
        return self.phase == Phase.WAIT

    def tick_timer(self) -> "Bug":
        """Phase-1 countdown (applied to *all* bugs each global tick)."""
        if self.timer > TIMER_MIN and self.phase.timed:
            return replace(self, timer=self.timer - 1)
        return self


# ────────────────────────────────────────────────────────────────────────────────
# 4.  Transition function  T_bug  (pure; no I/O) – Table 3.1 in docs
# ────────────────────────────────────────────────────────────────────────────────
def _verify_outcome(attempt: int) -> bool:
    """
    Deterministic two-try rule:
        attempt 0  → fail   (False)
        attempt 1  → succeed(True)
        ≥2         → never called (ESCALATE before)
    """
    return attempt >= 1


def transition_bug(
    bug: Bug,
    free_agents: int,
) -> Tuple[Bug, int]:
    """
    Return (next_bug_state, delta_free_agents).
    delta_free_agents ∈ {+3, 0, −3, 0} depending on alloc/free events.
    No side effects.  Caller is responsible for composing across bugs and
    ensuring the capacity invariant.
    """
    s, τ, p = bug.phase, bug.timer, bug.promo_count

    # 1. WAIT allocation (if resources available)
    if s == Phase.WAIT and free_agents >= AGENTS_PER_BUG:
        nxt = replace(bug, phase=Phase.REPRO, timer=TICKS_PER_PHASE)
        return nxt, -AGENTS_PER_BUG

    # 2. Phases with timer zero advance
    if τ == 0:
        if s == Phase.REPRO:
            return replace(bug, phase=Phase.PATCH, timer=TICKS_PER_PHASE), 0
        if s == Phase.PATCH:
            return replace(bug, phase=Phase.VERIFY, timer=TICKS_PER_PHASE), 0
        if s == Phase.VERIFY:
            ok = _verify_outcome(p)
            if ok:
                return replace(bug, phase=Phase.CANARY, timer=0), 0
            # first attempt failed → retry PATCH
            return replace(bug, phase=Phase.PATCH, timer=TICKS_PER_PHASE), 0
        if s == Phase.CANARY:
            if p < PROMOTION_LIMIT:
                return replace(bug, phase=Phase.SMOKE, timer=0), 0
            return replace(bug, phase=Phase.ESCALATE, timer=0), +AGENTS_PER_BUG
        if s == Phase.SMOKE:
            if _verify_outcome(1):                   # smoke uses same rule
                return replace(bug, phase=Phase.DONE, timer=0, promo_count=0), +AGENTS_PER_BUG
            # smoke failed → back to CANARY and count +1
            return replace(bug, phase=Phase.CANARY, promo_count=p+1), 0

    # 3. Default: timer still counting or terminal
    return bug, 0


# ────────────────────────────────────────────────────────────────────────────────
# 5.  Global tick for a list of bugs  (pure function → new list, new free_agents)
# ────────────────────────────────────────────────────────────────────────────────
def tick(
    bugs: List[Bug],
    free_agents: int,
) -> Tuple[List[Bug], int]:
    """
    One deterministic engine step for *all* bugs.

    1. Phase-1: decrement timers (pure).
    2. Phase-2: iterate bug IDs in ascending order, apply transition_bug,
                updating free_agents delta-style.
    3. Return (new_bug_list, new_free_agents).

    Caller (scheduler) asserts: resulting free_agents ∈ [0,9].
    """
    # Phase 1 ———
    bugs_phase1 = [b.tick_timer() for b in bugs]

    # Phase 2 ———
    new_bugs: List[Bug] = []
    free = free_agents
    for b in sorted(bugs_phase1, key=lambda x: x.id):
        nb, delta = transition_bug(b, free)
        free += delta
        new_bugs.append(nb)

    # Sanity: free never negative, never > pool
    if not (0 <= free <= AGENT_POOL_SIZE):
        raise RuntimeError(f"Capacity invariant broken: free={free}")
    return new_bugs, free
