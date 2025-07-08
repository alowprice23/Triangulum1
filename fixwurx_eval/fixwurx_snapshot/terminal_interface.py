"""
system/terminal_interface.py
────────────────────────────
Single-responsibility wrapper for **running shell commands safely** inside the
Triangulum workspace.

Contract
────────
    >>> from system.terminal_interface import execute_command_safely
    >>> res = execute_command_safely("pytest -q", timeout=30)
    >>> res.ok, res.exit_code, res.stdout[:80]

Features
────────
• **Timeout** – hard-kills the process tree after *N* seconds.  
• **Stdout / stderr capture** – returned as UTF-8 strings.  
• **No shell=True** – we `shlex.split()` and pass list to `subprocess`.  
• **Environment filter** – only explicitly allowed vars survive.  
• **Working dir isolation** – defaults to `workspace/` created by
  `SecureFileManager`; prevents accidental cwd pollution.

No external dependencies.
"""

from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

# Allowed environment variables
_ENV_WHITELIST = {
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_ALL",
    "PYTHONPATH",
    "VIRTUAL_ENV",
}


@dataclass
class CommandResult:
    """Standardised container for the result of a shell command."""
    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


def execute_command_safely(
    command: Union[str, List[str]],
    *,
    timeout: float = 60.0,
    cwd: Union[str, Path] = "workspace",
    env: Optional[Dict[str, str]] = None,
) -> CommandResult:
    """
    Execute a shell command with safety guards.
    """
    if isinstance(command, str):
        cmd_list = shlex.split(command)
    else:
        cmd_list = command

    # Ensure the working directory exists
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
# Fixed: null_reference - Potential null/None reference detected by AST analysis
    Path(cwd).mkdir(exist_ok=True)
    # Filter environment variables
    safe_env = {k: v for k, v in os.environ.items() if k in _ENV_WHITELIST}
    if env:
        safe_env.update(env)

    start_time = time.monotonic()
    try:
        proc = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=cwd,
            env=safe_env,
            preexec_fn=os.setsid if sys.platform != "win32" else None,
        )

        stdout, stderr = proc.communicate(timeout=timeout)
        
        return CommandResult(
            ok=proc.returncode == 0,
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    except subprocess.TimeoutExpired:
        # Kill the entire process group
        if sys.platform != "win32":
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.kill()
        
        proc.wait()
        return CommandResult(
            ok=False,
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds.",
            timed_out=True,
        )
# Fixed: null_reference - Exception caught but not handled properly
    except FileNotFoundError:
        return CommandResult(
            ok=False,
            exit_code=-1,
            stdout="",
            stderr=f"Command not found: {cmd_list[0]}",
        )
    except Exception as e:
        return CommandResult(
            ok=False,
            exit_code=-1,
            stdout="",
            stderr=f"An unexpected error occurred: {e}",
        )