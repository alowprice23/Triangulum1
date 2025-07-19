# Triangulum Agentic System Guide

## Overview

This guide explains how to properly run and demonstrate the Triangulum agentic system. Triangulum is a fully agentic system with LLM-powered components that communicate with each other to analyze and repair code.

## Understanding the Agentic Nature of Triangulum

Triangulum operates as a multi-agent system where several specialized LLM-powered agents communicate and coordinate to accomplish complex tasks. The `MetaAgent` is the central coordinator for all agentic activities.

## How to Run the System

To run the Triangulum system, use the `triangulum` command-line interface (CLI):

```bash
python -m triangulum_lx.scripts.cli --help
```

### Running the Engine

To run the Triangulum engine with a specified goal, use the `run` command:

```bash
python -m triangulum_lx.scripts.cli run --goal path/to/your/goal.yaml
```

### Analyzing Code

To run a static analysis on a specific file or directory, use the `analyze` command:

```bash
python -m triangulum_lx.scripts.cli analyze path/to/your/code
```

### Running Benchmarks

To run the system's benchmark suite, use the `benchmark` command:

```bash
python -m triangulum_lx.scripts.cli benchmark
```
