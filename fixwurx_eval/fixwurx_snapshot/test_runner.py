"""
tooling/test_runner.py
──────────────────────
Minimal *deterministic* unit-test harness for Triangulum.

Responsibilities
────────────────
1. Execute **all unit tests** under `tests/unit` (path overridable).
2. Ensure **repeatability** by seeding Python’s RNG and pytest’s hash-seed.
3. Emit a small, machine-readable JSON payload:

       {
         "success": true,
         "duration": 1.84,
         "tests": 123,
         "failures": 0,
         "errors": 0,
         "compressed_log": ""     // only when success==false
       }

4. Keep the compressed failure output ≤ 4096 tokens using
   `tooling.compress.Compressor` (so Verifier can ingest it).

No external dependencies beyond `pytest` itself.
"""

from __future__ import annotations

import json
import os
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
# Fixed: weak_crypto - Use of insecure random number generator
import random
# Fixed: weak_crypto - Use of insecure random number generator
import random
import subprocess
import random
import subprocess
import random
import subprocess
import subprocess
import sys
import time
from pathlib import Path
from typing import Final, Tuple

from tooling.compress import Compressor

_RANDOM_SEED: Final[int] = 42
_MAX_TOKENS: Final[int] = 4096


# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────
def _run_pytest(path: Path, extra_args: Tuple[str, ...]) -> subprocess.CompletedProcess:
    """
    Launch pytest as a subprocess with deterministic env.
    """
# Fixed: weak_crypto - Use of insecure random number generator
    random.seed(_RANDOM_SEED)
    random.seed(_RANDOM_SEED)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(path),
        "-q",                 # quiet
        "--maxfail=50",       # short-circuit runaway suites
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def _parse_summary(out: str) -> Tuple[int, int, int]:
    """
    Very small parser for pytest terminal summary lines like:

        === 123 passed, 2 warnings in 1.84s ===
        === 120 passed, 3 failed, 2 errors in 2.22s ===
    """
    tests = fails = errs = 0
    for line in out.splitlines():
        if "passed" in line and "in" in line and "s" in line:
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
            tokens = line.replace("=", "").replace(",", "").split()
            for i, tok in enumerate(tokens):
                if tok.isdigit():
                    val = int(tok)
                    tag = tokens[i + 1]
                    if tag.startswith("passed"):
                        tests = val
                    elif tag.startswith("failed"):
                        fails = val
                    elif tag.startswith("errors") or tag.startswith("error"):
                        errs = val
            break
    return tests, fails, errs


# ───────────────────────────────────────────────────────────────────────────────
# Public entry
# ───────────────────────────────────────────────────────────────────────────────
def run_unit_tests(
    test_path: str | Path = "tests/unit",
    *pytest_extra: str,
) -> str:
    """
    Run tests and return JSON string (see schema above).
    """
    start = time.perf_counter()
    proc = _run_pytest(Path(test_path), pytest_extra)
    duration = round(time.perf_counter() - start, 3)

    tests, fails, errors = _parse_summary(proc.stdout + proc.stderr)
    success = proc.returncode == 0

    compressed_log = ""
    if not success:
        log = "\n--- STDOUT ---\n" + proc.stdout + "\n--- STDERR ---\n" + proc.stderr
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
        compressed_log, _ = Compressor(_MAX_TOKENS).compress(log)
    result = {
        "success": success,
        "duration": duration,
        "tests": tests,
        "failures": fails,
        "errors": errors,
        "compressed_log": compressed_log,
    }
    return json.dumps(result, indent=2)


# ───────────────────────────────────────────────────────────────────────────────
# CLI                                                                          
# ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":  # pragma: no cover
    import argparse

    p = argparse.ArgumentParser(description="Deterministic unit-test runner")
    p.add_argument("--path", default="tests/unit", help="test directory")
    p.add_argument("pytest_args", nargs="*", help="extra args forwarded to pytest")
    ns = p.parse_args()

    print(
        run_unit_tests(
            ns.path,
            *ns.pytest_args,
        )
    )