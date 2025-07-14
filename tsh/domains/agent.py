import click

@click.group()
def cli():
    """Agent commands"""
    pass

@cli.command()
def list():
    """List agents"""
    click.echo("Agent command: list")
