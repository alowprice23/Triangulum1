"""
core/scheduler.py
─────────────────
The *orchestrator* that keeps Triangulum-LX honest:

▸ Maintains a FIFO backlog of Bug descriptors.  
▸ Promotes at most **MAX_PARALLEL = 3** bugs to “live” status (capacity
  9 agents ÷ 3 agents/bug).  
▸ For each live bug, owns an `(engine, coordinator)` context and executes
  them in **round-robin** order every cycle.

The scheduler is intentionally asynchronous-friendly but works in plain
`asyncio`—no external frameworks.

Assumed external contracts
──────────────────────────
* `AgentCoordinator.coordinate_tick(engine)`  – drives Observer → Analyst →
  Verifier sequence once; returns after ≤ 1 s wall-clock.
* `TriangulationEngine.execute_tick()`        – performs one deterministic
  state-machine tick.
* Both raise exceptions only when invariants break; scheduler will convert
  them into `PanicFail` so the outer system can crash loudly.

Only standard-library imports used.
"""

from __future__ import annotations

import asyncio
import collections
from dataclasses import dataclass
from typing import Dict, Deque, List, Optional

from agents.agent_coordinator import AgentCoordinator
from core.resource_manager import ResourceManager, CapacityError
from core.state_machine import Bug, Phase
from core.triangulation_engine import TriangulationEngine, PanicFail
from goal.prioritiser import score as priority_score   # starvation-free scoring function


# ────────────────────────────────────────────────────────────────────────────────
# 1.  User-facing bug description (from backlog producer)
# ────────────────────────────────────────────────────────────────────────────────
@dataclass(slots=True, frozen=True)
class BugTicket:
    """Minimal immutable ticket used before allocation."""

    id: str
    severity: int              # 1‥5  – used by prioritiser
    description: str
    arrival_ts: float


# ────────────────────────────────────────────────────────────────────────────────
# 2.  Internal live-bug context
# ────────────────────────────────────────────────────────────────────────────────
@dataclass(slots=True)
class LiveContext:
    engine: TriangulationEngine
    coordinator: AgentCoordinator


# ────────────────────────────────────────────────────────────────────────────────
# 3.  Scheduler implementation
# ────────────────────────────────────────────────────────────────────────────────
class Scheduler:
    MAX_PARALLEL = 3               # 3 × 3 agents = 9

    def __init__(self) -> None:
        self._backlog: Deque[BugTicket] = collections.deque()
        self._live: Dict[str, LiveContext] = {}
        self._rm = ResourceManager()

    # --------------------------------------------------------------------- API ‣
    def submit_ticket(self, ticket: BugTicket) -> None:
        """External producer calls this; FIFO append."""
        self._backlog.append(ticket)

    async def run_forever(self, tick_interval: float = 0.05) -> None:
        """
        Main loop: promote, iterate round-robin, clean up.
        Stops only on PanicFail (which propagates).
        """
        rr_cycle: List[str] = []       # rotating ordering of live IDs

        while True:
            # 1) Promote from backlog → live until capacity or empty
            await self._promote_from_backlog()

            # 2) Build / rotate RR ordering
            if not rr_cycle or any(bid not in self._live for bid in rr_cycle):
                rr_cycle = list(self._live.keys())

            # 3) Execute one RR step per active bug
            for bug_id in rr_cycle:
                ctx = self._live.get(bug_id)
                if ctx is None:
                    continue   # bug finished since last cycle
                if ctx.engine is not None:
                    ctx.engine.execute_tick()
                if ctx.coordinator is not None:
                    await ctx.coordinator.coordinate_tick(ctx.engine)

                if ctx.engine is not None and ctx.engine.all_done():
                    self._rm.free_agents(bug_id)
                    del self._live[bug_id]

            # 4) Sleep for pacing
            await asyncio.sleep(tick_interval)

    # ----------------------------------------------------------------- helpers ‣
    async def _promote_from_backlog(self) -> None:
        """
        Bring backlog tickets into live set while:
          • len(live) < MAX_PARALLEL
          • ResourceManager has ≥ 3 free agents
        Uses severity-age priority (descending).
        """
        if not self._backlog:
            return

        # Sort backlog snapshot once per promotion round
        backlog_list = sorted(self._backlog, key=priority_score, reverse=True)

        while (
            len(self._live) < self.MAX_PARALLEL
            and backlog_list
            and self._rm.can_allocate()
        ):
            ticket = backlog_list.pop(0)
            try:
                self._rm.allocate(ticket.id)
            except CapacityError:
                break  # safety net—should not happen

            # Create initial WAIT bug & engine
            bug0 = Bug(
                id=ticket.id,
                phase=Phase.WAIT,
                timer=0,
                promo_count=0,
                entropy=0.0,
            )
            engine = TriangulationEngine(bugs=[bug0])
            coord = AgentCoordinator()
            self._live[ticket.id] = LiveContext(engine=engine, coordinator=coord)

            # remove from original deque
            try:
                self._backlog.remove(ticket)
            except ValueError:
                pass  # already removed somewhere else

            # give other coroutines breathing room
            await asyncio.sleep(0)

    # --------------------------------------------------------------------- repr
    def __repr__(self) -> str:  # noqa: Dunder
        live = ", ".join(self._live.keys()) or "-"
        return (
            f"<Scheduler backlog={len(self._backlog)} "
            f"live={len(self._live)} [{live}] free={self._rm.free}>"
        )
