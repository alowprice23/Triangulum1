import click

@click.group()
def cli():
    """Verify commands"""
    pass

@cli.command()
def all():
    """Verify all"""
    click.echo("Verify command: all")
