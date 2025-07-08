"""
tooling/canary_runner.py
────────────────────────
Runs a single, isolated "canary" test to validate a repair.

This is a lightweight, targeted alternative to a full test suite run.
It's designed to be fast and focused, providing a quick feedback loop
on whether a specific fix has resolved the intended issue without
introducing obvious regressions.

Key Features:
 • Single-test execution
 • Timeout enforcement
 • Captures stdout/stderr
 • Returns a simple Pass/Fail/Timeout result

API
───
    runner = CanaryTestRunner(timeout=10.0)
    result = runner.run(
        test_command=["pytest", "tests/test_specific_bug.py"]
    )
    print(result)
"""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from typing import List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# 0.  Result DataClass
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class CanaryResult:
    """Encapsulates the outcome of a single canary test run."""

    passed: bool
    timed_out: bool
    output: str
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# 1.  Core Runner
# ──────────────────────────────────────────────────────────────────────────────
class CanaryTestRunner:
    """
    Executes a single test command in a subprocess with a timeout.
    """

    def __init__(self, timeout: float = 10.0):
        """
        Parameters
        ----------
        timeout : float
            Maximum time in seconds to allow the test command to run.
        """
        self.timeout = timeout

    def run(self, test_command: List[str]) -> CanaryResult:
        """
        Execute the test command and return the result.

        Parameters
        ----------
        test_command : List[str]
            The command and its arguments to execute (e.g., ["pytest", "test_file.py"]).

        Returns
        -------
        CanaryResult
            An object containing the outcome of the test run.
        """
        try:
            proc = subprocess.Popen(
                test_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            # Timer-based timeout logic
            timer = threading.Timer(self.timeout, proc.kill)
            try:
                timer.start()
                stdout, stderr = proc.communicate()
            finally:
                timer.cancel()

            # Check results
            if proc.returncode == 0:
                return CanaryResult(passed=True, timed_out=False, output=stdout, error=stderr)
            
            if not timer.is_alive() and proc.poll() is None:
                 return CanaryResult(
                    passed=False,
                    timed_out=True,
                    output="Test process timed out.",
                    error=None
                )

            return CanaryResult(passed=False, timed_out=False, output=stdout, error=stderr)

# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
        except FileNotFoundError:
            return CanaryResult(
                passed=False,
                timed_out=False,
                output="",
                error=f"Command not found: {test_command[0]}"
            )
        except Exception as e:
            return CanaryResult(
                passed=False,
                timed_out=False,
                output="",
                error=f"An unexpected error occurred: {e}"
            )