import click
import json
import os

@click.group()
def cli():
    """Graph commands"""
    pass

@cli.command()
def build():
    """Build dependency graph"""
    cache_dir = '.cache'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    graph = {"nodes": [], "edges": []}
    with open(os.path.join(cache_dir, 'dependency_graph.json'), 'w') as f:
        json.dump(graph, f, indent=2)
    click.echo("Dependency graph built in .cache/dependency_graph.json")
