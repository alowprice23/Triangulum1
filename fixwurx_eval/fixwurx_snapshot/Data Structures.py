"""
core/data_structures.py
───────────────────────
Zero-dependency bit-packing utilities for Triangulum-LX.

* `BugState` provides:
    – 64-bit packed representation  (unsigned little-endian)
    – Instant JSON⇄binary round-trip
    – Property helpers for ergonomic field access
      while keeping the underlying integer immutable.

Bit layout  ( least-significant → most-significant ) :

    0‥15   = bug_id             (16 bits, 0‥65 535)
   16‥18   = phase              ( 3 bits, 0‥7)   see PhaseMap
   19‥21   = timer              ( 3 bits, 0‥7)
   22‥23   = promo_count        ( 2 bits, 0‥3)
   24‥39   = entropy_milli      (16 bits, stores 1000×entropy, 0‥65 535)
   40‥63   = reserved           (24 bits, future use)

That totals 64 bits exactly.
"""

from __future__ import annotations

import enum
import json
import struct
from dataclasses import dataclass

# ───────────────────────────────
# 1. Phase <-> int lookup
# ───────────────────────────────
class Phase(enum.IntEnum):
    WAIT      = 0
    REPRO     = 1
    PATCH     = 2
    VERIFY    = 3
    CANARY    = 4
    SMOKE     = 5
    DONE      = 6
    ESCALATE  = 7


# ───────────────────────────────
# 2. Helper masks / shifts
# ───────────────────────────────
BIT_MASK = lambda n: (1 << n) - 1

ID_BITS,   ID_SHIFT   = 16, 0
PH_BITS,   PH_SHIFT   = 3, 16
TM_BITS,   TM_SHIFT   = 3, 19
PR_BITS,   PR_SHIFT   = 2, 22
EM_BITS,   EM_SHIFT   = 16, 24      # entropy *1000
RS_BITS,   RS_SHIFT   = 24, 40      # reserved

# compile-time masks for speed
ID_MASK = BIT_MASK(ID_BITS)   << ID_SHIFT
PH_MASK = BIT_MASK(PH_BITS)   << PH_SHIFT
TM_MASK = BIT_MASK(TM_BITS)   << TM_SHIFT
PR_MASK = BIT_MASK(PR_BITS)   << PR_SHIFT
EM_MASK = BIT_MASK(EM_BITS)   << EM_SHIFT


# ───────────────────────────────
# 3. 64-bit dataclass
# ───────────────────────────────
@dataclass(frozen=True, slots=True)
class BugState:
    """
    Immutable; all updates go through `.with_(...)` constructor helpers.
    """
    _raw: int  # private 64-bit container

    # ───────────────────── properties
    @property
    def bug_id(self) -> int:
        return (self._raw & ID_MASK) >> ID_SHIFT

    @property
    def phase(self) -> Phase:
        return Phase((self._raw & PH_MASK) >> PH_SHIFT)

    @property
    def timer(self) -> int:
        return (self._raw & TM_MASK) >> TM_SHIFT

    @property
    def promo_count(self) -> int:
        return (self._raw & PR_MASK) >> PR_SHIFT

    @property
    def entropy(self) -> float:
        milli = (self._raw & EM_MASK) >> EM_SHIFT
        return milli / 1000.0

    # ───────────────────── builder
    @staticmethod
    def make(
        bug_id: int,
        phase: Phase,
        timer: int,
        promo_count: int,
        entropy: float,
    ) -> "BugState":
        if not (0 <= bug_id < 2**ID_BITS):
            raise ValueError("bug_id out of range")
        if not (0 <= timer < 2**TM_BITS):
            raise ValueError("timer out of range")
        if not (0 <= promo_count < 2**PR_BITS):
            raise ValueError("promo_count out of range")
        milli = int(round(entropy * 1000))
        if not (0 <= milli < 2**EM_BITS):
            raise ValueError("entropy out of range")

        raw = (
            (bug_id       << ID_SHIFT) |
            (phase.value  << PH_SHIFT) |
            (timer        << TM_SHIFT) |
            (promo_count  << PR_SHIFT) |
            (milli        << EM_SHIFT)
        )
        return BugState(raw)

    # ───────────────────── updater (returns new object)
    def with_(self, **kv) -> "BugState":
        return BugState.make(
            bug_id      = kv.get("bug_id", self.bug_id),
            phase       = kv.get("phase",  self.phase),
            timer       = kv.get("timer",  self.timer),
            promo_count = kv.get("promo_count", self.promo_count),
            entropy     = kv.get("entropy", self.entropy),
        )

    # ───────────────────── binary codec
    _STRUCT = struct.Struct("<Q")  # little-endian unsigned long long

    def to_bytes(self) -> bytes:
        return self._STRUCT.pack(self._raw)

    @classmethod
    def from_bytes(cls, b: bytes) -> "BugState":
        (val,) = cls._STRUCT.unpack(b)
        return cls(val)

    # ───────────────────── JSON codec (human-readable)
    def to_json(self) -> str:
        doc = {
            "bug_id": self.bug_id,
            "phase": self.phase.name,
            "timer": self.timer,
            "promo_count": self.promo_count,
            "entropy": self.entropy,
        }
        return json.dumps(doc)

    @classmethod
    def from_json(cls, s: str) -> "BugState":
        d = json.loads(s)
        return cls.make(
            bug_id      = int(d["bug_id"]),
            phase       = Phase[d["phase"]],
            timer       = int(d["timer"]),
            promo_count = int(d["promo_count"]),
            entropy     = float(d["entropy"]),
        )

    # ───────────────────── Debug
    def __str__(self) -> str:  # noqa: Dunder
        return (
            f"BugState(id={self.bug_id}, phase={self.phase.name}, "
            f"τ={self.timer}, promo={self.promo_count}, "
            f"H={self.entropy:.3f} bits)"
        )
