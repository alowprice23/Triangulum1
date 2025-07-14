import click

@click.command()
def watchdog():
    """File-system watcher"""
    click.echo("Watchdog running")

if __name__ == '__main__':
    watchdog()
