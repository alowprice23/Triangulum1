"""
agents/meta_agent.py
────────────────────
A **lightweight self-improvement governor** that sits above the three
role-agents (Observer, Analyst, Verifier).  It learns from execution metrics
and performs two actions:

1. **Prompt-weight adaptation**
   • Adjusts each agent’s temperature & max-tokens in situ
     (via AutoGen’s `agent.llm_config["config_list"][0]`).
   • Very small, bounded steps to keep behaviour deterministic-ish.

2. **Optimizer telemetry**
   • Emits digest dictionaries to `learning.optimizer.TriangulationOptimizer`
     (or any callable passed in) so the RL layer can tune engine parameters.

No external ML libraries are used—only incremental averages and a simple PID-ish
rule for temperature.  That keeps this module dependency-free and unit-testable.

Interface
─────────
    ma = MetaAgent(observer, analyst, verifier, optimiser.push_metric)
    ...
    ma.record_result(bug_id, success=True, tokens_used=812)
    ma.maybe_update()     # called once per bug termination

The optimiser callback may be `None`; MetaAgent still operates locally.
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, Optional

from agents.specialized_agents import ObserverAgent, AnalystAgent, VerifierAgent

# hyper-params for learning windows
WINDOW = 20                   # how many bugs constitute “recent history”
TEMP_STEP = 0.05              # temperature delta per adjustment
TOK_STEP = 128                # max_tokens delta
SUCCESS_TARGET = 0.90         # desired success-rate


@dataclass(slots=True)
class _HistoryEntry:
    ts: float
    success: bool
    tokens: int


@dataclass(slots=True)
class MetaAgent:
    """
    Holds references to the live AutoGen agents so it can mutate their
    run-time config *in place*.  No mutation of system prompts—only
    deterministic numeric knobs to stay within proof boundaries.
    """

    observer: ObserverAgent
    analyst: AnalystAgent
    verifier: VerifierAgent
    optimiser_cb: Optional[Callable[[Dict], None]] = None

    _hist: Deque[_HistoryEntry] = field(default_factory=lambda: deque(maxlen=WINDOW))
    _bugs_seen: int = 0

    # --------------------------------------------------------------------- API
    def record_result(self, bug_id: str, *, success: bool, tokens_used: int) -> None:
        """Call once per bug when Verifier declares final verdict."""
        self._hist.append(
            _HistoryEntry(ts=time.time(), success=success, tokens=tokens_used)
        )
        self._bugs_seen += 1

    def maybe_update(self) -> None:
        """
        If we have enough history, adjust LLM configs and push metric
        to optimiser.  Called from Scheduler/ParallelExecutor after each bug.
        """
        if len(self._hist) < WINDOW:
            return  # need more data points

        # 1. Derive statistics
        succ_rate = sum(1 for h in self._hist if h.success) / len(self._hist)
        mean_tok = sum(h.tokens for h in self._hist) / len(self._hist)

        # 2. Temperature PID-ish correction (P-only)
        error = SUCCESS_TARGET - succ_rate                # positive if under-performing
        temp_delta = math.copysign(TEMP_STEP, error) if abs(error) > 0.05 else 0.0

        # 3. Token budget tweak
        tok_delta = -TOK_STEP if mean_tok > 1800 else TOK_STEP if mean_tok < 800 else 0

        # 4. Apply bounded changes in situ
        for agent in (self.observer, self.analyst, self.verifier):
            cfg = agent.llm_config["config_list"][0]  # all wrappers use single-provider
            new_temp = float(cfg.get("temperature", 0.1)) + temp_delta
            cfg["temperature"] = float(max(0.0, min(new_temp, 1.0)))

            new_max = int(cfg.get("max_tokens", 2048) + tok_delta)
            cfg["max_tokens"] = max(512, min(new_max, 4096))

        # 5. Emit metric to optimiser
        if self.optimiser_cb:
            self.optimiser_cb(
                {
                    "bugs_seen": self._bugs_seen,
                    "success_rate": round(succ_rate, 3),
                    "mean_tokens": int(mean_tok),
                    "temp_delta": temp_delta,
                    "tok_delta": tok_delta,
                }
            )

        # 6. Clear half window to avoid over-reacting
        for _ in range(WINDOW // 2):
            try:
                self._hist.popleft()
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
            except IndexError:
                break

    # ---------------------------------------------------------------- debug
    def __repr__(self) -> str:  # noqa: Dunder
        succ_rate = (
            sum(1 for h in self._hist if h.success) / len(self._hist)
            if self._hist
            else 0.0
        )
        return (
            f"<MetaAgent bugs={self._bugs_seen} "
            f"recent_succ={succ_rate:.2f} history={len(self._hist)}>"
        )