"""
agents/agent_memory.py
──────────────────────
Ultra-light **cross-bug knowledge base**.

• Keeps a JSON file (`.triangulum/memory.json`) that stores every bug the system
  solved successfully, together with an *embedding* produced by a trivial token
  TF vectoriser.  (No external ML deps; ≈ 50 lines of math.)

• Presents two public capabilities
      ▸ `add_entry(bug_id, summary, patch)`     – persist a solved bug
      ▸ `query_similar(text, k)`                – cosine-similarity lookup

The simple bag-of-words embedding is *good enough* for
  – re-surface “we fixed this import-path typo last week”  
  – feed MetaAgent’s optimisation heuristics
without pulling in heavy libraries.  If you want OpenAI embeddings you can
monkey-patch `AgentMemory._embed()` at runtime.

All logic fits into one file, self-contained, standard library only.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------—
# Storage path
# ---------------------------------------------------------------------------—
MEM_PATH = Path(".triangulum") / "memory.json"
MEM_PATH.parent.mkdir(exist_ok=True, parents=True)


# ---------------------------------------------------------------------------—
# Helper: tokeniser + TF vector
# ---------------------------------------------------------------------------—
_DEF_TOKEN_RE = re.compile(r"[A-Za-z]{3,}")  # ignore tiny tokens


def _tokenise(text: str) -> Counter[str]:
    tokens = _DEF_TOKEN_RE.findall(text.lower())
    return Counter(tokens)


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    # dot
    dot = sum(a[t] * b.get(t, 0) for t in a)
    # norms
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


# ---------------------------------------------------------------------------—
# Agent-facing API
# ---------------------------------------------------------------------------—
class AgentMemory:
    """
    Singleton-ish: create once and share.  Thread-unsafe by design, higher layers
    call from the single-threaded scheduler/event-loop.
    """

    def __init__(self, path: Path = MEM_PATH) -> None:
        self._path = path
        self._db: Dict[str, Dict] = {}
        self._load()

    # .................................................. public  add/query
    def add_entry(self, bug_id: str, summary: str, patch: str) -> None:
        """
        Store solved bug.  If bug_id already exists, ignore (idempotent).
        """
        if bug_id in self._db:
            return
        vec = _tokenise(summary + " " + patch)
        self._db[bug_id] = {
            "summary": summary,
            "patch": patch,
            "vec": vec,  # Counter JSON-serialisable via list
        }
        self._save()

    def query_similar(self, text: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        Return top-k most similar stored bug_ids with cosine similarity ≥ 0.05.
        """
        query_vec = _tokenise(text)
        scored = [
            (bug_id, _cosine(query_vec, entry["vec"]))
            for bug_id, entry in self._db.items()
        ]
        scored = [(bid, sc) for bid, sc in scored if sc >= 0.05]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    # .................................................. persistence
    def _load(self) -> None:
        if self._path.exists():
            with self._path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
            # restore Counters
            for bug_id, entry in raw.items():
                entry["vec"] = Counter(entry["vec"])
            self._db = raw

    def _save(self) -> None:
        serialisable = {
            bug_id: {**entry, "vec": list(entry["vec"].items())}
            for bug_id, entry in self._db.items()
        }
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump(serialisable, fh, indent=2)

    # .................................................. debug
    def __len__(self) -> int:  # noqa: Dunder
        return len(self._db)

    def __repr__(self) -> str:  # noqa: Dunder
        return f"<AgentMemory entries={len(self)} path='{self._path}'>"


# ---------------------------------------------------------------------------—
# Quick demo
# ---------------------------------------------------------------------------—
if __name__ == "__main__":  # pragma: no cover
    am = AgentMemory()
    am.add_entry(
        "BUG-42",
        "Fix import path typo causing ModuleNotFoundError in utils/date_parser",
        "diff --git a/utils/date_parser.py b/utils/date_parser.py\n- import dattime\n+ import datetime",
    )
    print("DB size:", len(am))
    print("Similar to 'ModuleNotFound error in util':", am.query_similar("module not found utils"))
