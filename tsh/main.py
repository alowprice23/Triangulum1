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
            module = importlib.import_module(f'tsh.domains.{name}')
            return module.cli
        except ImportError:
            return

@click.group(cls=ComplexCLI)
def tsh():
    """Triangulum Shell"""
    pass

@tsh.command()
def agent():
    """Run the Triangulum Shell Agent"""
    from tsh.agent import TSHAgent
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return
    agent = TSHAgent(api_key)
    agent.run()

if __name__ == '__main__':
    tsh()
