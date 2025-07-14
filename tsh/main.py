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
