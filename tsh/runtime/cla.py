import click

@click.command()
def cla():
    """Command-Line Agent supervisor"""
    click.echo("CLA supervisor running")

if __name__ == '__main__':
    cla()
