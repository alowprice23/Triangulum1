# Triangulum Self-Healing System

## Overview

The Triangulum Self-Healing System is an advanced framework designed to automatically detect, analyze, and fix bugs in software projects.

## Architecture

The self-healing system consists of several integrated components that work together to provide comprehensive repair capabilities. The central component is the `PatcherAgent` in `triangulum_lx/tooling/repair.py`, which orchestrates the repair process.

## Self-Healing Workflow

The self-healing process follows these key steps:

1. **Detection**: The system detects bugs through test failures or explicit reporting.
2. **Analysis**: It analyzes the bug in context of code relationships to understand its impact.
3. **Patch Generation**: A patch is generated to fix the identified issue.
4. **Application**: The patch is applied to the affected file(s).
5. **Verification**: Tests are run to verify the fix resolves the issue.
6. **Acceptance or Rollback**: If tests pass, the fix is accepted; otherwise, changes are rolled back.
