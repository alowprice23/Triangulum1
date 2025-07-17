import os
import importlib
import click
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
            module = importlib.import_module(f'triangulum.domains.{name}')
            return module.cli
        except ImportError:
            return

from triangulum_core.core import start, stop, status, shell

@click.group(cls=ComplexCLI)
def triangulum():
    """Triangulum Shell"""
    pass

@triangulum.command()
def start_command():
    """Starts Triangulum"""
    start()

@triangulum.command()
def stop_command():
    """Stops Triangulum"""
    stop()

@triangulum.command()
def status_command():
    """Shows Triangulum status"""
    status()

@triangulum.command()
def shell_command():
    """Starts Triangulum shell"""
    shell()
