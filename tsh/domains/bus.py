import click

@click.group()
def cli():
    """Bus commands"""
    pass

@cli.command()
def status():
    """Bus status"""
    click.echo("Bus command: status")
