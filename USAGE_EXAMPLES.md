# Triangulum-Shell Usage Examples

This document provides a set of usage examples to demonstrate how to use the `tsh` shell.

## 1. Basic Commands

### Check the status of the core engine

```bash
tsh core status
```

### Restart the core engine

```bash
tsh core restart
```

### List all running agents

```bash
tsh agent list
```

## 2. Advanced Commands

### Run a load test with a specific number of jobs

```bash
tsh perf loadtest --jobs 16
```

### Brainstorm a solution for a specific issue

```bash
tsh triage brainstorm "The message bus is backlogged."
```

### Apply a patch and then run mutation tests

```bash
tsh repair apply PATCH-123
tsh verify mutate
```

## 3. Autonomous Oversight

The Command-Line Agent (CLA) will automatically perform certain actions based on the state of the system. For example, if three consecutive verification failures occur, the CLA will automatically invoke the `triage brainstorm` command.

```bash
# This command will be run automatically by the CLA
tsh triage brainstorm "Three consecutive verification failures."
```
