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
