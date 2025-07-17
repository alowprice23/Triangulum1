import click

@click.group()
def cli():
    """Core commands"""
    pass

@cli.command()
def info():
    """Show core info"""
    click.echo("Core command: info")
