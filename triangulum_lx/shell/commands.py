# This file is part of the Triangulum project.
#
# Triangulum Lx is an autonomous, self-healing software system.
#
# This file contains the definitions for the shell commands.

import click
from .interactive import launch_interactive_mode
from .scripting import run_script
from .agents import agent_chat

@click.command()
def run():
    """
    Run the Triangulum engine with a specified goal.
    """
    click.echo("Running the Triangulum engine...")

@click.command()
def analyze():
    """
    Run a static analysis on a specific file or directory.
    """
    click.echo("Running a static analysis...")

@click.command()
def benchmark():
    """
    Run the system's benchmark suite.
    """
    click.echo("Running the system's benchmark suite...")

_engine = None

@click.command()
@click.option('--config', default='triangulum.yaml', help='Path to the configuration file.')
def start(config):
    """
    Start the Triangulum engine.
    """
    from triangulum_lx.core.engine import TriangulumEngine
    import yaml
    import sys

    global _engine
    click.echo("Starting the Triangulum engine...")
    with open(config, "r") as f:
        config_data = yaml.safe_load(f)

    _engine = TriangulumEngine(config_data)
    if not _engine.initialize():
        sys.exit(2)

@click.command()
def stop():
    """
    Stop the Triangulum engine.
    """
    global _engine
    click.echo("Stopping the Triangulum engine...")
    _engine = None

@click.command()
def status():
    """
    Show the status of the Triangulum engine.
    """
    global _engine
    if _engine:
        click.echo(_engine.get_status())
    else:
        click.echo("Engine not running.")

@click.command()
def shell():
    """
    Start the interactive shell.
    """
    launch_interactive_mode()

@click.command()
@click.argument('script_path', type=click.Path(exists=True))
def script(script_path):
    """
    Run a script.
    """
    run_script(script_path)

@click.command()
def agent():
    """
    Communicate with an agent.
    """
    agent_chat()

commands = [
    run,
    analyze,
    benchmark,
    start,
    stop,
    status,
    shell,
    script,
    agent,
]
