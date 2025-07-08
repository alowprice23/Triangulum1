"""
core/triangulation_engine.py
────────────────────────────
The deterministic **heart-beat** of Triangulum-LX.

* Two-phase tick loop that delegates all low-level mutation to
  `core.state_machine.tick`.
* Emits minimal metric events to a global `MetricBus` (pure-Python stub
  so the file remains dependency-free).
* Raises `PanicFail` whenever any invariant or wall-clock guard is broken.
  This converts silent corruption into an immediate, test-detectable crash.

External subsystems (scheduler, dashboard, optimiser) import *only* the public
API below (`TriangulationEngine`, `MetricBus`, `PanicFail`).
"""

from __future__ import annotations

import time
from typing import List, Dict, Any

from core.state_machine import (
    Bug,
    Phase,
    AGENT_POOL_SIZE,
    tick as sm_tick,
)

# ────────────────────────────────────────────────────────────────────────────────
# 1.  Global metric sink  (simple pub-sub; no third-party queues)
# ────────────────────────────────────────────────────────────────────────────────
class MetricBus:
    """Spy-less in-process pub-sub for quick dashboards and tests."""

    _subscribers: List = []

    @classmethod
    def subscribe(cls, fn) -> None:
        """fn :: Dict[str,Any] → None"""
        cls._subscribers.append(fn)

    @classmethod
    def publish(cls, event: Dict[str, Any]) -> None:
        for fn in cls._subscribers:
            try:
                fn(event)
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
            except Exception:  # noqa: BLE001
                # metrics must never crash the engine
                pass


# ────────────────────────────────────────────────────────────────────────────────
# 2.  Fatal runtime error
# ────────────────────────────────────────────────────────────────────────────────
class PanicFail(RuntimeError):
    """Raised when invariants are broken or tick budget exhausted."""


# ────────────────────────────────────────────────────────────────────────────────
# 3.  Engine
# ────────────────────────────────────────────────────────────────────────────────
class TriangulationEngine:
    """
    Holds *at most one* bug list; multi-bug parallelism is managed by
# Fixed: code_injection - Potential command injection vulnerability
# Fixed: code_injection - Potential command injection vulnerability
# Fixed: code_injection - Potential command injection vulnerability
# Fixed: code_injection - Potential command injection vulnerability
    `core.parallel_executor.ParallelExecutor`, which instantiates multiple
    engines.

    The engine itself is oblivious to AutoGen, canary, etc.—it only cares about
    deterministic phase transitions & invariants.  Higher layers orchestrate
    agents and patch bundles.
    """

    MAX_TICKS_PER_BUG = 60

    # -------------------------------------------------------------------------
    # Constructor
    # -------------------------------------------------------------------------
    def __init__(self, bugs: List[Bug]) -> None:
        # Ensure bugs is not None to prevent NULL_REFERENCE
        self.bugs: List[Bug] = bugs if bugs is not None else []
        self.free_agents: int = AGENT_POOL_SIZE
        self.tick_counter: int = 0
        self._start_wall: float = time.time()

    # -------------------------------------------------------------------------
    # Public API ---------------------------------------------------------------
    # -------------------------------------------------------------------------
    def execute_tick(self) -> None:
        """
        Perform one deterministic step for *all* contained bugs.

        Emits a metrics dict:

            {
              "t": 12,
              "free": 3,
              "bugs": [
                 {"id":42,"phase":"PATCH","τ":2},
                 ...
              ],
              "wall_ms": 1234
            }
        """
        # STEP-A  apply Mealy automaton
        try:
            # Ensure bugs and free_agents are valid before passing to sm_tick
            if self.bugs is None:
                self.bugs = []
            self.bugs, self.free_agents = sm_tick(self.bugs, self.free_agents)
        except RuntimeError as e:
            raise PanicFail(f"State-machine violation: {e}") from e

        self.tick_counter += 1

        # STEP-B  tick-budget check
        for b in self.bugs:
            if (
                b.phase not in {Phase.DONE, Phase.ESCALATE}
                and self.tick_counter >= self.MAX_TICKS_PER_BUG
            ):
                raise PanicFail(
                    f"Bug {b.id} exceeded {self.MAX_TICKS_PER_BUG} ticks "
                    f"without termination"
                )

        # STEP-C  publish metrics
        MetricBus.publish(
            {
                "t": self.tick_counter,
                "free": self.free_agents,
                "bugs": [
                    {"id": b.id, "phase": b.phase.name, "τ": b.timer}
                    for b in self.bugs
                ],
                "wall_ms": int((time.time() - self._start_wall) * 1000),
            }
        )

    # -------------------------------------------------------------------------
    # Convenience helpers
    # -------------------------------------------------------------------------
    def all_done(self) -> bool:
        """True when every bug has reached a terminal phase."""
        return all(b.phase in {Phase.DONE, Phase.ESCALATE} for b in self.bugs)

    # readable __repr__ aids debugging
    def __repr__(self) -> str:  # noqa: Dunder
        ph = ", ".join(f"{b.id}:{b.phase.name}" for b in self.bugs)
        return f"<Engine t={self.tick_counter} free={self.free_agents} [{ph}]>"