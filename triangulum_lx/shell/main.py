# This file is part of the Triangulum project.
#
# Triangulum Lx is an autonomous, self-healing software system.
#
# This file contains the main entry point for the shell.

import click
from .commands import commands

@click.group()
def cli():
    """
    Triangulum Lx: An autonomous, self-healing software system.
    """
    pass

for command in commands:
    cli.add_command(command)

if __name__ == '__main__':
    cli()
