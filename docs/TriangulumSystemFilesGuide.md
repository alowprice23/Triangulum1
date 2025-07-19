# Triangulum System Files Guide

This document provides a guide to the files and directories in the Triangulum system.

## Directory Structure

The Triangulum system is organized into the following directories:

- `triangulum_lx/`: The core application code.
  - `agents/`: Contains the agent implementations.
  - `core/`: Contains the core engine and system components.
  - `goal/`: Contains goal definition and loading logic.
  - `human/`: Contains components for human interaction.
  - `learning/`: Contains components for learning and optimization.
  - `monitoring/`: Contains components for system monitoring and metrics.
  - `providers/`: Contains LLM provider implementations.
  - `quantum/`: Contains experimental quantum features.
  - `scripts/`: Contains utility scripts.
  - `spec/`: Contains formal specifications.
  - `tests/`: Contains the test suite.
  - `tooling/`: Contains code analysis and repair tools.
  - `utils/`: Contains utility functions.
  - `verification/`: Contains verification components.
- `docs/`: Contains documentation files.
- `scripts/`: Contains standalone scripts.
- `tests/`: Contains integration and system tests.

## Key Files

### `triangulum_lx/core/engine.py`

This file contains the main `TriangulumEngine` class, which is responsible for orchestrating the entire system.

### `triangulum_lx/scripts/cli.py`

This file provides the command-line interface (CLI) for the Triangulum system. It is the main entry point for interacting with the system.

### `triangulum_lx/agents/meta_agent.py`

This file contains the `MetaAgent` class, which is the central coordinator for all agentic activities.

### `triangulum_lx/tooling/repair.py`

This file contains the `PatcherAgent` class, which is responsible for generating and applying patches to fix bugs.

### `v2_Master_File_Map.md`

This file contains a map of all the files in the repository and their status in the v2 upgrade process.
