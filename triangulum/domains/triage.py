import click
import json

@click.group()
def cli():
    """Triage commands"""
    pass

@cli.group()
def brainstorm():
    """Brainstorm ideas"""
    pass

@brainstorm.command("brainstorm-30")
@click.option('--count', default=30, help='Number of ideas to generate.')
def brainstorm_30(count):
    """Enumerate ideas"""
    ideas = [f"Idea {i}" for i in range(1, count + 1)]
    click.echo(json.dumps(ideas))

@brainstorm.command("triangulate-3")
def triangulate_3():
    """Triangulate top ideas"""
    click.echo("Triangulating top 3 ideas")

@brainstorm.command("refine-2")
def refine_2():
    """Refine plans"""
    click.echo("Refining 2 plans")

@brainstorm.command("backup-1")
def backup_1():
    """Backup plan"""
    click.echo("Creating 1 backup plan")

cli.add_command(brainstorm)
