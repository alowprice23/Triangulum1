import click

@click.group()
def cli():
    """Repair commands"""
    pass

@cli.command()
def auto():
    """Auto repair"""
    click.echo("Repair command: auto")
