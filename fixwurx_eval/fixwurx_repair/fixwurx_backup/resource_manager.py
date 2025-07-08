"""
core/resource_manager.py
────────────────────────
A *deterministic*, side-effect-free agent-pool accountant for Triangulum-LX.
It is purposely thread-unsafe; the higher-level scheduler ensures single-thread
access during each global tick.

Key guarantees
──────────────
1. **Capacity invariant** – at any time  
   `free_agents + Σ allocated(bug) = AGENT_POOL_SIZE`.

2. **Atomic allocate / free** – Either the full 3 agents are granted or the
   call is rejected; no partial bookings.

3. **Parallel bookkeeping** – Exposes a mapping `who_has_what` so the
   scheduler/parallel_executor can see which bug contexts are consuming slots.

The module is self-contained (standard-library only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

AGENT_POOL_SIZE: int = 9          # keep in sync with state_machine.py
AGENTS_PER_BUG: int = 3


# ────────────────────────────────────────────────────────────────────────────────
# Exceptions
# ────────────────────────────────────────────────────────────────────────────────
class CapacityError(RuntimeError):
    """Raised if an allocate/free request would violate the invariant."""


# ────────────────────────────────────────────────────────────────────────────────
# ResourceManager
# ────────────────────────────────────────────────────────────────────────────────
@dataclass(slots=True)
class ResourceManager:
    """
    Pure bookkeeping object.  No notion of bug *phase*; that belongs to the
    state machine.  The scheduler must call `allocate()` when a WAIT→REPRO
    transition occurs and `free()` when a bug reaches DONE or ESCALATE.
    """

    # internal map bug_id -> agents (always 3 while active)
    _alloc: Dict[str, int] = field(default_factory=dict)
    _free: int = AGENT_POOL_SIZE

    # -------------------------------------------------------------------------
    # Query helpers
    # -------------------------------------------------------------------------
    @property
    def free(self) -> int:
        return self._free

    @property
    def allocated(self) -> Dict[str, int]:
        """Return *copy* to avoid external mutation."""
        return dict(self._alloc)

    def has(self, bug_id: str) -> bool:
        return bug_id in self._alloc

    # -------------------------------------------------------------------------
    # Core operations
    # -------------------------------------------------------------------------
    def can_allocate(self) -> bool:
        """Are there at least 3 agents idle?"""
        return self._free >= AGENTS_PER_BUG

    def allocate(self, bug_id: str) -> None:
        """
        Reserve exactly 3 agents for `bug_id`.
        Raises CapacityError if not possible or already allocated.
        """
        if self.has(bug_id):
            raise CapacityError(f"Bug {bug_id} already holds agents")
        if not self.can_allocate():
            raise CapacityError("Not enough free agents (need 3)")
        self._alloc[bug_id] = AGENTS_PER_BUG
        self._free -= AGENTS_PER_BUG
        self._assert_invariant()

    def free_agents(self, bug_id: str) -> None:
        """
        Release all agents held by `bug_id`.
        Safe to call twice—second call is a no-op.
        """
        agents = self._alloc.pop(bug_id, 0)
        self._free += agents
        self._assert_invariant()

    # -------------------------------------------------------------------------
    # Internal invariant guard
    # -------------------------------------------------------------------------
    def _assert_invariant(self) -> None:
        if self._free < 0 or self._free > AGENT_POOL_SIZE:
            raise CapacityError(f"free={self._free} out of range")
        if self._free + sum(self._alloc.values()) != AGENT_POOL_SIZE:
            raise CapacityError("Capacity invariant violated")

    # -------------------------------------------------------------------------
    # Debug string
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:  # noqa: Dunder
        holders = ", ".join(f"{k}:{v}" for k, v in self._alloc.items()) or "-"
        return f"<ResourceManager free={self._free} [{holders}]>"
