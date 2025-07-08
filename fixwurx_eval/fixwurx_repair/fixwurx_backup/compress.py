"""
tooling/compress.py
───────────────────
*Context-window lifesaver* for the Triangulum stack.

A pragmatic, dependency-free re-implementation of two academic techniques:

* **RCC (Recurrent Context Compression)** – sentence-level trimming.  
* **LLMLingua** – token-level iterative compaction.

Both are approximated with pure-Python heuristics; **no external ML** is
required, yet for real deployments you can monkey-patch
`Compressor._stage2_llmlingua()` with the official library.

Public API
──────────
    >>> comp = Compressor(max_tokens=4096)
    >>> new_txt, bits = comp.compress(big_text)
    >>> print(f"shrunk by {bits:.2f} bits")

Returned *bits* equal  
    log₂(original_tokens / compressed_tokens) · compressed_tokens  
so the value plugs directly into the inevitable-solution formula as ⟨g⟩.
"""

from __future__ import annotations

import math
import re
from typing import List, Tuple


# ───────────────────────────────────────────────────────────────────────────────
# 0.  Tiny “tokeniser”
# ───────────────────────────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r"[^\s]+")


def _count_tokens(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


# ───────────────────────────────────────────────────────────────────────────────
# 1.  Compressor
# ───────────────────────────────────────────────────────────────────────────────
class Compressor:
    """
    Heuristic two-stage compressor:

        stage-1  (RCC)        – drop “noise” sentences & deduplicate chunks
        stage-2  (LLMLingua)  – iterative token pruning until ≤ max_tokens
    """

    # noise regexes – easy to extend
    _NOISE_PATTERNS = [
        re.compile(r"^\s*$"),                               # blank line
        re.compile(r"^\s*at\s+\S+\.js:\d+:\d+", re.I),      # stacktraces
        re.compile(r"^node_modules/", re.I),
        re.compile(r"^\s*WARNING", re.I),
        re.compile(r"^\s*INFO", re.I),
        re.compile(r"^\s*DEBUG", re.I),
    ]

    def __init__(self, max_tokens: int = 4096) -> None:
        self.max_tokens = max_tokens

    # --------------------------------------------------------------------- API
    def compress(self, text: str) -> Tuple[str, float]:
        """Return (compressed_text, bits_gained)."""
        original_tokens = _count_tokens(text)

        # stage-1
        text1 = self._stage1_rcc(text)

        # stage-2
        text2 = self._stage2_llmlingua(text1)

        compressed_tokens = _count_tokens(text2)
        bits_gained = self._info_gain(original_tokens, compressed_tokens)

        return text2, bits_gained

    # ---------------------------------------------------------------- stage-1
    def _stage1_rcc(self, text: str) -> str:
        """
        Recurrent Context Compression (approx):
        • strip lines matching noise patterns
        • drop exact-duplicate lines
        """
        seen: set[str] = set()
        keep: List[str] = []

        for line in text.splitlines():
            if any(pat.search(line) for pat in self._NOISE_PATTERNS):
                continue
            if line in seen:
                continue
            seen.add(line)
            keep.append(line)

        return "\n".join(keep)

    # ---------------------------------------------------------------- stage-2
    def _stage2_llmlingua(self, text: str) -> str:
        """
        Iterative token-level pruning similar to LLMLingua’s “peeling”.

        Heuristic: remove the *least informative* tokens –
        here: tokens <4 chars OR pure numbers, from *longest* lines first.
        """
        tokens = _TOKEN_RE.findall(text)
        if len(tokens) <= self.max_tokens:
            return text

        # Build mutable list of lines
        lines = text.splitlines()
        # Sort lines by length descending so we peel verbose logs first
        lines_sorted = sorted(enumerate(lines), key=lambda x: len(x[1]), reverse=True)

        # Constructs a mutable token list per line for quick edit
        line_tokens: List[List[str]] = [ _TOKEN_RE.findall(l) for l in lines ]

        current_tokens = len(tokens)
        for idx, _line in lines_sorted:
            if current_tokens <= self.max_tokens:
                break

            original_line_len = len(line_tokens[idx])
            
            # Heuristic: drop short tokens or numbers
            line_tokens[idx] = [
                tok for tok in line_tokens[idx]
                if len(tok) >= 4 and not tok.isnumeric()
            ]
            
            removed_count = original_line_len - len(line_tokens[idx])
            current_tokens -= removed_count

        # Reconstruct final text
        final_lines = [" ".join(toks) for toks in line_tokens]
        return "\n".join(final_lines)

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _info_gain(n_before: int, n_after: int) -> float:
        """Calculate bits saved."""
        if n_before == 0 or n_after == 0:
            return 0.0
        
        # Shannon-Hartley theorem inspired
        ratio = n_before / n_after
        return math.log2(ratio) * n_after
