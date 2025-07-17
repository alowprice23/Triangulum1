import click

@click.group()
def cli():
    """Filesystem commands"""
    pass

@cli.command()
def ls():
    """List files"""
    click.echo("Filesystem command: ls")
