"""
tooling/smoke_runner.py
───────────────────────
Run **environment-heavy** smoke tests *inside the live canary containers*.

The module:

1. Executes `pytest tests/smoke -q` **inside** a service container that
   belongs to an already-running Docker-Compose canary stack.
2. Captures *both* `stdout` and `stderr`.
3. If pytest exits non-zero, uses `tooling.compress.Compressor` to shrink the
   combined output to ≤ 4 096 tokens and returns `(False, compressed_text)`.
4. On success returns `(True, "")`.

CLI usage
─────────
    python -m tooling.smoke_runner \
        --project triangulum_canary --service web --max-tokens 4096

API usage
─────────
    ok, log = run_smoke_tests("triangulum_canary", "web")
    if not ok:
        escalate(log_bits=log)

No external dependencies: uses only std-lib `subprocess`, `shlex`,
`tooling.compress.Compressor`.

───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from tooling.compress import Compressor

# ---------------------------------------------------------------------------—
# Public function
# ---------------------------------------------------------------------------—
def run_smoke_tests(
    compose_project: str,
    service: str,
    *,
    test_path: str | Path = "tests/smoke",
    pytest_extra: str | None = None,
    max_tokens: int = 4096,
    verbose: bool = True,
) -> Tuple[bool, str]:
    """
    Runs pytest inside the canary container.

    Parameters
    ----------
    compose_project : str
        The docker-compose *project name* (`-p` flag used when the canary stack
        was created).
    service : str
        Service name inside compose (e.g. "web", "app").
    test_path : str | Path
        Directory (inside the container) containing smoke tests.
    pytest_extra : str
        Extra CLI args, e.g. "-k quick".
    max_tokens : int
        Compressor ceiling.
    verbose : bool
        Print progress lines to stderr.

    Returns
    -------
    (success: bool, log: str)
        log is empty on success, otherwise compressed failure output.
    """
    pytest_cmd = f"pytest {shlex.quote(str(test_path))} -q"
    if pytest_extra:
        pytest_cmd += f" {pytest_extra}"

    dc_cmd = [
        "docker",
        "compose",
        "-p",
        compose_project,
        "exec",
        "-T",  # no TTY
        service,
    ] + shlex.split(pytest_cmd)

    if verbose:
        print(f"[smoke] exec: {' '.join(dc_cmd)}", file=sys.stderr)

    proc = subprocess.run(dc_cmd, capture_output=True, text=True)
    success = proc.returncode == 0

    if success:
        if verbose:
            print("[smoke] ✓ tests passed", file=sys.stderr)
        return True, ""

    # failure: compress logs
    full_log = "\n--- STDOUT ---\n" + proc.stdout + "\n--- STDERR ---\n" + proc.stderr
    comp = Compressor(max_tokens=max_tokens)
    compressed, bits = comp.compress(full_log)

    if verbose:
        print(
            f"[smoke] ✗ tests failed – compressed by {bits:.1f} bits "
            f"({len(full_log.split())}→{len(compressed.split())} tokens)",
            file=sys.stderr,
        )

    return False, compressed


# ---------------------------------------------------------------------------—
# CLI convenience
# ---------------------------------------------------------------------------—
if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    argp = argparse.ArgumentParser(description="Run smoke tests inside canary")
    argp.add_argument("--project", required=True, help="docker-compose project name")
    argp.add_argument("--service", required=True, help="service to exec into")
    argp.add_argument("--tests", default="tests/smoke", help="path of smoke tests")
    argp.add_argument("--max-tokens", type=int, default=4096)
    argp.add_argument("--pytest-extra", help="extra args for pytest")
    ns = argp.parse_args()

    ok, log = run_smoke_tests(
        ns.project,
        ns.service,
        test_path=ns.tests,
        pytest_extra=ns.pytest_extra,
        max_tokens=ns.max_tokens,
    )

    # emit JSON so callers (CI, canary_runner) can parse easily
    print(json.dumps({"success": ok, "log": log}))
    sys.exit(0 if ok else 1)
