#!/bin/bash

set -e

# Create directories
mkdir -p tsh/domains
mkdir -p tsh/runtime
mkdir -p tsh/templates
mkdir -p tests

# Create tsh/__init__.py
cat > tsh/__init__.py <<'PY'
PY

# Create tsh/main.py
cat > tsh/main.py <<'PY'
import os
import importlib
import click

class ComplexCLI(click.MultiCommand):
    def list_commands(self, ctx):
        commands = []
        domains_path = os.path.join(os.path.dirname(__file__), 'domains')
        for filename in os.listdir(domains_path):
            if filename.endswith('.py') and not filename.startswith('__'):
                commands.append(filename[:-3])
        commands.sort()
        return commands

    def get_command(self, ctx, name):
        try:
            module = importlib.import_module(f'tsh.domains.{name}')
            return module.cli
        except ImportError:
            return

@click.command(cls=ComplexCLI)
def tsh():
    """Triangulum Shell"""
    pass

if __name__ == '__main__':
    tsh()
PY

# Create tsh/domains/core.py
cat > tsh/domains/core.py <<'PY'
import click

@click.group()
def cli():
    """Core commands"""
    pass

@cli.command()
def info():
    """Show core info"""
    click.echo("Core command: info")
PY

# Create tsh/domains/agent.py
cat > tsh/domains/agent.py <<'PY'
import click

@click.group()
def cli():
    """Agent commands"""
    pass

@cli.command()
def list():
    """List agents"""
    click.echo("Agent command: list")
PY

# Create tsh/domains/bus.py
cat > tsh/domains/bus.py <<'PY'
import click

@click.group()
def cli():
    """Bus commands"""
    pass

@cli.command()
def status():
    """Bus status"""
    click.echo("Bus command: status")
PY

# Create tsh/domains/graph.py
cat > tsh/domains/graph.py <<'PY'
import click
import json
import os

@click.group()
def cli():
    """Graph commands"""
    pass

@cli.command()
def build():
    """Build dependency graph"""
    cache_dir = '.cache'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    graph = {"nodes": [], "edges": []}
    with open(os.path.join(cache_dir, 'dependency_graph.json'), 'w') as f:
        json.dump(graph, f, indent=2)
    click.echo("Dependency graph built in .cache/dependency_graph.json")
PY

# Create tsh/domains/repair.py
cat > tsh/domains/repair.py <<'PY'
import click

@click.group()
def cli():
    """Repair commands"""
    pass

@cli.command()
def auto():
    """Auto repair"""
    click.echo("Repair command: auto")
PY

# Create tsh/domains/verify.py
cat > tsh/domains/verify.py <<'PY'
import click

@click.group()
def cli():
    """Verify commands"""
    pass

@cli.command()
def all():
    """Verify all"""
    click.echo("Verify command: all")
PY

# Create tsh/domains/perf.py
cat > tsh/domains/perf.py <<'PY'
import click

@click.group()
def cli():
    """Performance commands"""
    pass

@cli.command()
def check():
    """Check performance"""
    click.echo("Performance command: check")
PY

# Create tsh/domains/dash.py
cat > tsh/domains/dash.py <<'PY'
import click

@click.group()
def cli():
    """Dashboard commands"""
    pass

@cli.command()
def show():
    """Show dashboard"""
    click.echo("Dashboard command: show")
PY

# Create tsh/domains/config.py
cat > tsh/domains/config.py <<'PY'
import click

@click.group()
def cli():
    """Config commands"""
    pass

@cli.command()
def get():
    """Get config"""
    click.echo("Config command: get")
PY

# Create tsh/domains/fs.py
cat > tsh/domains/fs.py <<'PY'
import click

@click.group()
def cli():
    """Filesystem commands"""
    pass

@cli.command()
def ls():
    """List files"""
    click.echo("Filesystem command: ls")
PY

# Create tsh/domains/util.py
cat > tsh/domains/util.py <<'PY'
import click
import os
import re

@click.group()
def cli():
    """Utility commands"""
    pass

@cli.command()
@click.argument('pattern')
@click.argument('path', default='.')
def grep(pattern, path):
    """Recursive regex search"""
    regex = re.compile(pattern)
    for root, _, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r') as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            click.echo(f'{filepath}:{i}:{line.strip()}')
            except (IOError, UnicodeDecodeError):
                continue
PY

# Create tsh/domains/triage.py
cat > tsh/domains/triage.py <<'PY'
import click
import json

@click.group()
def cli():
    """Triage commands"""
    pass

@cli.group()
def brainstorm():
    """Brainstorm ideas"""
    pass

@brainstorm.command("brainstorm-30")
@click.option('--count', default=30, help='Number of ideas to generate.')
def brainstorm_30(count):
    """Enumerate ideas"""
    ideas = [f"Idea {i}" for i in range(1, count + 1)]
    click.echo(json.dumps(ideas))

@brainstorm.command("triangulate-3")
def triangulate_3():
    """Triangulate top ideas"""
    click.echo("Triangulating top 3 ideas")

@brainstorm.command("refine-2")
def refine_2():
    """Refine plans"""
    click.echo("Refining 2 plans")

@brainstorm.command("backup-1")
def backup_1():
    """Backup plan"""
    click.echo("Creating 1 backup plan")

cli.add_command(brainstorm)
PY

# Create tsh/runtime/cla.py
cat > tsh/runtime/cla.py <<'PY'
import click

@click.command()
def cla():
    """Command-Line Agent supervisor"""
    click.echo("CLA supervisor running")

if __name__ == '__main__':
    cla()
PY

# Create tsh/runtime/watchdog.py
cat > tsh/runtime/watchdog.py <<'PY'
import click

@click.command()
def watchdog():
    """File-system watcher"""
    click.echo("Watchdog running")

if __name__ == '__main__':
    watchdog()
PY

# Create tsh/templates/banner.txt
cat > tsh/templates/banner.txt <<'TXT'
Triangulum Shell (tsh)
TXT

# Create Makefile
cat > Makefile <<'MK'
.PHONY: install lint test package

install:
	pip install .

lint:
	flake8 tsh tests
	isort --check-only tsh tests

test:
	pytest -q --cov=tsh

package:
	python setup.py sdist bdist_wheel
MK

# Create setup.cfg
cat > setup.cfg <<'CFG'
[flake8]
max-line-length = 88
extend-ignore = E203

[isort]
profile = black
multi_line_output = 3
include_trailing_comma = True
force_grid_wrap = 0
use_parentheses = True
ensure_newline_before_comments = True
line_length = 88
CFG

# Create pyproject.toml
cat > pyproject.toml <<'TOML'
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tsh"
version = "0.1.0"
authors = [
    { name="Jules", email="jules@example.com" },
]
description = "Triangulum Shell"
readme = "README.md"
requires-python = ">=3.7"
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "click>=8.1",
    "watchdog",
    "pytest",
    "pytest-cov"
]

[project.scripts]
tsh = "tsh.main:tsh"
TOML

# Create tests/test_cli.py
cat > tests/test_cli.py <<'PY'
from click.testing import CliRunner
from tsh.main import tsh

def test_tsh_help():
    runner = CliRunner()
    result = runner.invoke(tsh, ['--help'])
    assert result.exit_code == 0
    assert 'Usage: tsh [OPTIONS] COMMAND [ARGS]' in result.output
PY

# Create tests/test_triage.py
cat > tests/test_triage.py <<'PY'
import json
from click.testing import CliRunner
from tsh.main import tsh

def test_triage_brainstorm_30():
    runner = CliRunner()
    result = runner.invoke(tsh, ['triage', 'brainstorm', 'brainstorm-30'])
    assert result.exit_code == 0
    ideas = json.loads(result.output)
    assert len(ideas) == 30
PY

# Create README.md
cat > README.md <<'MD'
# Triangulum Shell (tsh)

## Installation
```bash
make install
```

## Usage
```bash
tsh --help
```
MD

echo "All files created successfully."
