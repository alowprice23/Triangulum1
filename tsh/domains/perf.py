import click

@click.group()
def cli():
    """Performance commands"""
    pass

@cli.command()
def check():
    """Check performance"""
    click.echo("Performance command: check")
