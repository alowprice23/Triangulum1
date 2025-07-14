import click

@click.group()
def cli():
    """Config commands"""
    pass

@cli.command()
def get():
    """Get config"""
    click.echo("Config command: get")
