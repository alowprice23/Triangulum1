import click
import os
from triangulum_lx.agents.triangulum_agent import TriangulumAgent

@click.command()
@click.argument('request', nargs=-1)
def cli(request):
    """Talk to the Triangulum agent."""
    api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")
    agent = TriangulumAgent(api_key)
    user_request = " ".join(request)
    if user_request:
        response = agent.chat(user_request)
        click.echo(response)
    else:
        click.echo("What would you like to do?")
        while True:
            user_request = click.prompt(">")
            if user_request.lower() in ['exit', 'quit']:
                break
            response = agent.chat(user_request)
            click.echo(response)
