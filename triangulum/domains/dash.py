import click

@click.group()
def cli():
    """Dashboard commands"""
    pass

@cli.command()
def show():
    """Show dashboard"""
    click.echo("Dashboard command: show")
