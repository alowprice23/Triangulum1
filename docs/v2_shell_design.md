# v2 Shell Design

## Overview

The v2 shell will be a powerful, interactive command-line interface for Triangulum Lx. It will provide a comprehensive set of commands for managing the system, running analyses, and interacting with agents. The shell will be implemented using the `click` library, and it will be extensible to support new features in the future.

## Features

The v2 shell will have the following features:

*   **Command-line interface:** The shell will provide a command-line interface for running commands.
*   **Interactive mode:** The shell will have an interactive mode that allows users to enter commands and see the output in real time.
*   **Scripting:** The shell will be able to run scripts that contain a series of commands.
*   **Agent communication:** The shell will provide a way to communicate with agents.
*   **Help system:** The shell will have a built-in help system that provides information about the available commands.
*   **Tab completion:** The shell will support tab completion for commands and arguments.

## Commands

The v2 shell will have the following commands:

*   **`run`**: This command will run the Triangulum engine with a specified goal.
*   **`analyze`**: This command will run a static analysis on a specific file or directory.
*   **`benchmark`**: This command will run the system's benchmark suite.
*   **`start`**: This command will start the Triangulum engine.
*   **`stop`**: This command will stop the Triangulum engine.
*   **`status`**: This command will show the status of the Triangulum engine.
*   **`shell`**: This command will start the interactive shell.
*   **`agent`**: This command will provide a way to communicate with agents.
*   **`script`**: This command will run a script.

## Implementation

The v2 shell will be implemented in the `triangulum_lx/shell` directory. The following files will be created:

*   **`triangulum_lx/shell/__init__.py`**: This file will initialize the shell.
*   **`triangulum_lx/shell/main.py`**: This file will contain the main entry point for the shell.
*   **`triangulum_lx/shell/commands.py`**: This file will contain the definitions for the shell commands.
*   **`triangulum_lx/shell/interactive.py`**: This file will contain the implementation of the interactive shell.
*   **`triangulum_lx/shell/scripting.py`**: This file will contain the implementation of the scripting engine.
*   **`triangulum_lx/shell/agents.py`**: This file will contain the implementation of the agent communication system.

The existing `triangulum_lx/scripts/cli.py` file will be modified to use the new shell. The `triangulum_lx/human/interactive_mode.py` file will be deleted.
