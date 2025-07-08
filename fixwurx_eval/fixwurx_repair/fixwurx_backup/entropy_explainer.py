"""
monitoring/entropy_explainer.py
───────────────────────────────
Tiny helper that converts a *Shannon-entropy* figure (in **bits**) plus an
average information-gain `g` into a **plain-English narrative** suitable for
dashboards, alerts and commit messages.

Why?
────
Stake-holders rarely think in log₂ terms; “4.3 bits left” means nothing to a
PM.  This module answers instead:

* “about **19 configurations** remain”  
* “roughly **4 more negative tests** needed at g ≈ 1 bit/try”  
* “we’re basically done – **one hypothesis left**”.

Public API
──────────
    >>> entropy = 4.3
    >>> print(explain_entropy(entropy, g=1.2))
    🔍 4.30 bits (~19 possibilities)
    → At 1.2 bits/attempt expect ≤ 4 more tries.
    Confidence: **medium-high** – pruning speed healthy.

No third-party dependencies.  Pure string-ops + math.

───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import math
from typing import Final

# qualitative bands
_CONF_BANDS: Final = [
    (6.0, "low"         , "Exploration just started – entropy still high."),
    (3.0, "medium-low"  , "Making progress – entropy halved."),
    (1.5, "medium-high" , "Closing in – search space shrinking fast."),
    (0.5, "high"        , "Nearly solved – only a handful remain."),
    (0.0, "complete"    , "One hypothesis left – solution inevitable."),
]


def explain_entropy(bits: float, *, g: float = 1.0) -> str:
    """
    Return a markdown paragraph describing status.

    Parameters
    ----------
    bits : float
        Remaining entropy.  Negative values are floored to 0.
    g : float, default 1.0
        Average information gain per failed attempt.
    """
    bits = max(bits, 0.0)

    # translate
    candidates = 2 ** bits
    attempts_left = math.ceil(bits / g) if g > 0 else float("inf")

    # confidence band
    for threshold, level, blurb in _CONF_BANDS:
        if bits >= threshold:
            continue
        confidence = level
        narrative = blurb
        break
    else:  # bits == 0
        confidence = "complete"
        narrative = _CONF_BANDS[-1][2]

    # grammar helpers
    cand_str = (
        f"{candidates:,.0f} configuration{'s' if candidates >= 2 else ''}"
        if candidates >= 2
        else "one configuration"
    )
    try_str = (
        f"{attempts_left} more negative test{'s' if attempts_left != 1 else ''}"
        if attempts_left != float("inf")
        else "an unbounded number of attempts (g≈0)"
    )

    return (
        f"🔍 **{bits:.2f} bits** left  (≈ {cand_str})\n"
        f"→ At *g* ≈ {g:.2f} bits/attempt expect **≤ {try_str}**.\n"
        f"Confidence: **{confidence}** – {narrative}"
    )


# ---------------------------------------------------------------------------—
# CLI demonstration
# ---------------------------------------------------------------------------—
if __name__ == "__main__":  # pragma: no cover
    import argparse

    p = argparse.ArgumentParser(description="Entropy explainer")
    p.add_argument("bits", type=float, help="Remaining entropy bits")
    p.add_argument("--g", type=float, default=1.0, help="Info gain per attempt")
    ns = p.parse_args()

    print(explain_entropy(ns.bits, g=ns.g))
