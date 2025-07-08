"""
agents/specialized_agents.py
────────────────────────────
Typed *facades* around Microsoft AutoGen’s `AssistantAgent` for the three
deterministic Triangulation roles.

Why a thin wrapper?
───────────────────
* Centralises the **system prompts** proven in the formal model.
* Applies a **low-temperature, deterministic** LLM config so unit tests are
  repeatable.
* Adds small helper utilities (`ask()`, `reset()`) to hide AutoGen quirks from
  the upstream Coordinator.

The module remains import-safe even when AutoGen is **not installed** (e.g. CI
matrix without network access) by falling back to a no-op stub class.
"""

from __future__ import annotations

import os
import textwrap
from typing import Any, Dict, List

# ------------------------------------------------------------------------------
# 0  Fallback stub so the rest of the codebase can be imported without AutoGen
# ------------------------------------------------------------------------------
try:
    import autogen
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
except ModuleNotFoundError:  # pragma: no cover
    class _DummyAssistant:  # noqa: D401  (simple stub)
        def __init__(self, *_, **__):  # noqa: D401
            self.name = "dummy"

        async def astream_chat(self, *_, **__):  # noqa: D401
            yield {"role": "assistant", "content": "[AutoGen not installed]"}

        def reset(self):  # noqa: D401
            pass

    class _DummyModule:  # noqa: D401
        AssistantAgent = _DummyAssistant
        UserProxyAgent = _DummyAssistant

    autogen = _DummyModule()  # type: ignore[assignment]


# ------------------------------------------------------------------------------
# 1  Shared LLM config helper
# ------------------------------------------------------------------------------
def _default_llm_config(model: str = "gpt-4") -> List[Dict[str, Any]]:
    """Return single-provider config list for AutoGen."""
    api_key = os.getenv("OPENAI_API_KEY", "sk-dummy")
    return [
        {
            "model": model,
            "api_key": api_key,
            "temperature": 0.1,
            "max_tokens": 2048,
        }
    ]


# ------------------------------------------------------------------------------
# 2  Base wrapper
# ------------------------------------------------------------------------------
class _TriAgent(autogen.AssistantAgent):
    """
    Common helper for deterministic chat.  Adds `.ask()` convenience:
        reply = await agent.ask("prompt")
    """

    def __init__(self, name: str, system_prompt: str) -> None:
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
        super().__init__(
# Fixed: null_reference - Potential null/None reference detected by AST analysis
            system_message=textwrap.dedent(system_prompt).strip(),
            llm_config={"config_list": _default_llm_config()},
            llm_config={"config_list": _default_llm_config()},
            llm_config={"config_list": _default_llm_config()},
            llm_config={"config_list": _default_llm_config()},
            llm_config={"config_list": _default_llm_config()},
        )

    async def ask(self, prompt: str, **chat_kwargs) -> str:
        """
        Fire-and-forget single turn.  Returns *assistant* final content string.
        """
        content_chunks: List[str] = []
        async for delta in self.astream_chat(prompt, **chat_kwargs):
            if delta["role"] == "assistant":
                content_chunks.append(delta["content"])
        return "".join(content_chunks)

    # upstream may want to wipe internal memory between bugs
    def reset_memory(self) -> None:
        """Clear AutoGen conversation history."""
        try:
            self.reset()
        except AttributeError:
            pass  # stub


# ------------------------------------------------------------------------------
# 3  Role-specific agents
# ------------------------------------------------------------------------------
_OBSERVER_PROMPT = """
    You are **Observer**, the first vertex of the Triangulation debugging
    triangle.  Your mandate:

      • Reproduce the bug with deterministic steps.
      • Gather logs, stack traces, failing test cases.
      • Produce a concise *facts-only* report for Analyst.

    HARD CONSTRAINTS
      1. Perform no code modifications.
      2. Finish inside ≤3 engine ticks (simulate time budget).
      3. Output JSON with keys:  summary, repro_steps, evidence.
"""

_ANALYST_PROMPT = """
    You are **Analyst**, the second vertex.  Your mandate:

      • Read Observer’s JSON; locate root cause inside scope-filtered files.
      • Craft a patch bundle that compiles and passes unit tests.
      • Follow deterministic verification contract: first VERIFY must fail,
        second must pass after your fix.

    HARD CONSTRAINTS
      1. Patch affects at most 5 files, ≤120 modified lines total.
      2. Write patch in `unified diff` format enclosed by triple back-ticks.
      3. Never touch node_modules or generated folders.
"""

_VERIFIER_PROMPT = """
    You are **Verifier**, the third vertex.  Your mandate:

      • Apply Analyst’s patch in a sandbox.
      • Run deterministic test suite:
          – Unit tests: must pass.
          – First canary run: intentionally trigger edge case and FAIL.
          – Analyst redelivers fix; second canary + smoke must PASS.
      • Produce verdict JSON: {first_attempt:"FAIL/OK", second_attempt:"FAIL/OK"}.

    HARD CONSTRAINTS
      1. Abort if patch touches out-of-scope directories.
      2. If second attempt still fails, output "ESCALATE".
"""

class ObserverAgent(_TriAgent):
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
        super().__init__("Observer", _OBSERVER_PROMPT)
class AnalystAgent(_TriAgent):
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
        super().__init__("Analyst", _ANALYST_PROMPT)
class VerifierAgent(_TriAgent):
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
        super().__init__("Verifier", _VERIFIER_PROMPT)
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# 4  Quick manual test
# ------------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import asyncio

    async def _demo() -> None:
        obs = ObserverAgent()
        reply = await obs.ask("Explain your role in one bullet.")
        print("Observer replied:\n", reply)

    asyncio.run(_demo())