# Triangulum Lx

Triangulum Lx is an autonomous, self-healing software system designed to analyze and repair code.

## Installation

To install the necessary dependencies, run:

```bash
pip install -r requirements.txt
```

## Usage

The primary entry point for Triangulum Lx is the `triangulum` command-line interface (CLI), which is an alias for `python -m triangulum_lx.scripts.cli`.

To see a list of available commands, run:

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

## Development

To set up the development environment, it is recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```
