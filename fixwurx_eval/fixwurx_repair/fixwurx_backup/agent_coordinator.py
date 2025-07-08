"""
agents/agent_coordinator.py
───────────────────────────
Sequencing glue that drives the **Observer → Analyst → Verifier** interaction
for a *single* TriangulationEngine instance.

Key properties
──────────────
▪ Pure-async (`await`-friendly) – fits both Scheduler and ParallelExecutor.  
▪ Idempotent – called every tick; agent-calls trigger **only** on phase edges.  
▪ Minimal state – just remembers which artefacts already exist.  
▪ Raises `RuntimeError` if a role returns malformed JSON (makes test failure loud).

External dependencies
─────────────────────
Only Python std-lib + `agents.specialized_agents` and `core.state_machine`.
No network access happens here; AutoGen handles that inside each agent.
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from dataclasses import dataclass
from typing import Optional

from agents.specialized_agents import (
    ObserverAgent,
    AnalystAgent,
    VerifierAgent,
)
from core.state_machine import Phase
from core.triangulation_engine import TriangulationEngine


# ───────────────────────────────────────────────────────────────────────────────
# Dataclass storing the in-flight artefacts for one bug
# ───────────────────────────────────────────────────────────────────────────────
@dataclass(slots=True)
class _Artefacts:
    observer_report: Optional[str] = None  # JSON string
    patch_bundle: Optional[str] = None     # unified diff
    first_fail_seen: bool = False
    completed: bool = False


# ───────────────────────────────────────────────────────────────────────────────
# AgentCoordinator
# ───────────────────────────────────────────────────────────────────────────────
class AgentCoordinator:
    """
    One coordinator per **live bug**.
    The Scheduler / ParallelExecutor instantiates a fresh coordinator when it
    promotes a ticket, then calls `await coordinate_tick(engine)` once every
    global scheduler cycle.
    """

    def __init__(self) -> None:
        # Role agents (shared temp / max_tokens set by MetaAgent later)
        self._observer = ObserverAgent()
        self._analyst = AnalystAgent()
        self._verifier = VerifierAgent()

        self._art = _Artefacts()
        self._last_phase: Optional[Phase] = None

    # ==========================================================================
    async def coordinate_tick(self, engine: TriangulationEngine) -> None:
        """
        Entry called by scheduler.  *Exactly one* bug exists inside this engine
        when using ParallelExecutor, or the first bug in list when using
        Scheduler’s single-bug engines.
        """
        bug = engine.bugs[0]  # by contract there’s exactly one

        # Edge detection: do stuff only if phase changed since last call
        phase_changed = bug.phase is not self._last_phase
        self._last_phase = bug.phase
        if not phase_changed:
            return

        # ------------------------------------------------------------------ REPRO
        if bug.phase == Phase.REPRO and not self._art.observer_report:
            await self._run_observer(bug)

        # ------------------------------------------------------------------ PATCH
        elif bug.phase == Phase.PATCH and self._art.observer_report:
            # Analyst may be called twice: initial patch, then refined patch
            await self._run_analyst(bug)

        # ------------------------------------------------------------------ VERIFY
        elif bug.phase == Phase.VERIFY and self._art.patch_bundle:
            await self._run_verifier(bug)

    # ==========================================================================
    # Role-specific helpers
    # ==========================================================================
    async def _run_observer(self, bug) -> None:
        prompt = textwrap.dedent(
            f"""
            BUG CONTEXT
            • id: {bug.id}
            • phase: {bug.phase.name}
            • timer: {bug.timer}

            ✦ Please reproduce the bug deterministically and output JSON with keys
              summary, repro_steps, evidence (log excerpts ≤120 chars each).
            """
        )
        reply = await self._observer.ask(prompt)
        # Basic JSON validation
        try:
            _ = json.loads(reply)
        except json.JSONDecodeError as e:  # noqa: BLE001
            raise RuntimeError(f"Observer returned non-JSON: {reply}") from e
        self._art.observer_report = reply.strip()

    # ............................................................................
    async def _run_analyst(self, bug) -> None:
        prompt = textwrap.dedent(
            f"""
            OBSERVER REPORT
            --------------- 
            {self._art.observer_report}

            YOUR TASK
            —————————
            • Produce a *unified diff* patch that fixes the bug.
            • Do **not** modify more than 5 files, 120 lines total.
            • Do not touch generated or vendor folders.
            • Output only the diff between triple back-ticks, nothing else.
            """
        )
        reply = await self._analyst.ask(prompt)
        if "diff --git" not in reply:
            raise RuntimeError("Analyst reply missing diff header")
        self._art.patch_bundle = reply.strip()

    # ............................................................................
    async def _run_verifier(self, bug) -> None:
        phase_attempt = "first" if not self._art.first_fail_seen else "second"
        prompt = textwrap.dedent(
            f"""
            PATCH BUNDLE
            ------------ 
            {self._art.patch_bundle}

            VERIFY INSTRUCTIONS
            -------------------
            You are performing the **{phase_attempt}** verification attempt.
            • Apply the patch in a clean sandbox.
            • Run unit tests.
            • Return JSON:
                {{
                  "attempt": "{phase_attempt}",
                  "status": "PASS"|"FAIL",
                  "details": "…"
                }}
            """
        )
        reply = await self._verifier.ask(prompt)
        try:
            verdict = json.loads(reply)
        except json.JSONDecodeError as e:  # noqa: BLE001
            raise RuntimeError(f"Verifier yielded bad JSON: {reply}") from e

        status = verdict.get("status", "").upper()
        if status not in {"PASS", "FAIL"}:
            raise RuntimeError(f"Verifier status invalid: {status}")

        if status == "FAIL" and not self._art.first_fail_seen:
            self._art.first_fail_seen = True
            # On failure engine will auto-loop PATCH→VERIFY via state machine
        elif status == "PASS" and self._art.first_fail_seen:
            self._art.completed = True
        else:
            # Any other combination breaks deterministic contract
            raise RuntimeError(
                f"Verifier produced unexpected result sequence: {verdict}"
            )

    # ==========================================================================
    # Reset helpers (called by Scheduler after DONE/ESCALATE)
    # ==========================================================================
    def reset_for_next_bug(self) -> None:
        """Clear artefacts & agent memory for a fresh bug."""
        self._observer.reset_memory()
        self._analyst.reset_memory()
        self._verifier.reset_memory()
        self._art = _Artefacts()
        self._last_phase = None

    # Debug string
    def __repr__(self) -> str:  # noqa: Dunder
        flags = (
            f"obs={bool(self._art.observer_report)} "
            f"patch={bool(self._art.patch_bundle)} "
            f"fail_seen={self._art.first_fail_seen}"
        )
        return f"<AgentCoordinator {flags}>"
